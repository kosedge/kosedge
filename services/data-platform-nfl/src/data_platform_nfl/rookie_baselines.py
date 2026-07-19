"""Historical rookie-year usage baselines, by position + draft-capital tier.

Rookies enter every season with zero rows in nfl_dp_player_usage_weekly --
there is no "prior season" to average, unlike returning veterans. Left
alone, this means rookies are silently absent from
nfl_player_projection_features_weekly (which joins directly off usage_weekly)
and therefore invisible to every downstream player prop / fantasy
projection. That's a much bigger problem than the recency-bias fix applied
to veterans in preseason_hydration.py -- it's a hard blind spot, not just a
noisy number.

The fix: build a real, backtestable prior from actual history. For every
rookie season 2013-present (nfl_dp_rosters.rookie_year == season), join to
that player's actual nfl_dp_player_usage_weekly production that year and
average per-game usage by (position, draft-capital tier). Draft capital
(nfl_dp_rosters.draft_number, sourced directly from nflreadpy's
load_rosters()) is the single strongest predictor of Year-1 opportunity --
stronger than any college-production signal we could realistically ingest
this week -- so it is the primary bucketing key. Undrafted players get their
own tier rather than being dropped.

This intentionally does NOT touch college production, combine measurables,
or scheme fit. Those are real phase-2 signals (see conversation notes on
cfbfastR/CollegeFootballData.com) layered on top of this baseline later, not
a replacement for having a baseline at all.
"""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import text

from .db import SessionLocal

DRAFT_TIERS: List[tuple[str, int, int]] = [
    ("R1_top10", 1, 10),
    ("R1_11_32", 11, 32),
    ("R2_R3", 33, 96),
    ("R4_R5", 97, 172),
    ("R6_R7", 173, 300),
]
UNDRAFTED_TIER = "UDFA"

# nfl_dp_player_usage_weekly only tracks ball-carrying/passing involvement
# (targets, rush attempts, dropbacks, etc). It has no meaningful signal for
# offensive line, defense, or special teams -- there is nothing to
# translate from college for those positions in *this* table. Only these
# positions get the cross-position same-draft-tier fallback in
# get_rookie_baseline; anything else gets an explicit all-zero baseline
# (present in the table for downstream joins, but never borrows another
# position's shape).
SKILL_OFFENSE_POSITIONS = {"QB", "RB", "WR", "TE", "FB", "HB"}
_ZERO_BASELINE = {
    "avg_involvement_plays_per_game": 0.0,
    "avg_targets_per_game": 0.0,
    "avg_receptions_per_game": 0.0,
    "avg_receiving_yards_per_game": 0.0,
    "avg_rush_attempts_per_game": 0.0,
    "avg_rush_yards_per_game": 0.0,
    "avg_red_zone_targets_per_game": 0.0,
    "avg_red_zone_carries_per_game": 0.0,
    "avg_qb_dropbacks_per_game": 0.0,
    "avg_success_rate": None,
}


def draft_tier_for_pick(draft_number: int | None) -> str:
    if draft_number is None:
        return UNDRAFTED_TIER
    for tier, lo, hi in DRAFT_TIERS:
        if lo <= draft_number <= hi:
            return tier
    return UNDRAFTED_TIER


DEFAULT_RECENCY_DECAY = 0.85
"""Per-season exponential decay applied when averaging historical rookie
classes into a baseline (weight = decay ** (through_season - class_season)).

A walk-forward backtest (2019-2024 draft classes, see
data/ops/nfl-preseason-methodology-backtest-report.md) found the unweighted
2013-present average of rookie RB touches was increasingly over-projecting
real usage in the two most recent classes (+31%, +30%) -- consistent with
the real, well-documented league-wide shift toward committee/timeshare RB
backfields, which an unweighted 13-year mean cannot track. Recency-weighting
lets the baseline follow that drift while still using the full historical
sample (older classes still contribute, just with less influence) rather
than throwing away data with a hard cutoff window.

0.85 was chosen by re-running that same backtest with several decay values
(and, separately, several hard rolling-window lengths) and comparing the
resulting RB bias: it materially reduces the 2023/2024 over-projection
(+31%/+30% at decay=1.0 down toward the high teens/low twenties %) without
starving the thinnest draft-tier buckets of sample the way an aggressive
decay or a short hard window does. It does not fully eliminate the
over-projection -- some of that residual is plausibly small-sample noise in
individual rookie classes (n=15-18 RBs/season) rather than pure trend, so
this is a deliberate partial correction, not a claim of a perfectly tracked
trend. Re-check this value if a future season's backtest shows the bias
growing rather than shrinking.
"""


def compute_rookie_usage_baselines(
    *,
    through_season: int | None = None,
    min_sample_players: int = 3,
    recency_decay: float = DEFAULT_RECENCY_DECAY,
) -> Dict[str, Any]:
    """Recompute nfl_dp_rookie_usage_baselines from real rookie-season history.

    Safe to re-run every offseason once a new rookie class has a completed
    season of real usage data -- it fully replaces the table's contents
    (small, derived, no manual edits live here).
    """
    session = SessionLocal()
    try:
        rookie_rows = session.execute(
            text(
                """
                SELECT
                  u.player_id,
                  r.position,
                  r.draft_number,
                  u.season,
                  COUNT(DISTINCT u.week) AS games_played,
                  SUM(u.involvement_plays)::numeric AS involvement_plays,
                  SUM(u.targets)::numeric AS targets,
                  SUM(u.receptions)::numeric AS receptions,
                  SUM(u.receiving_yards)::numeric AS receiving_yards,
                  SUM(u.rush_attempts)::numeric AS rush_attempts,
                  SUM(u.rush_yards)::numeric AS rush_yards,
                  SUM(u.red_zone_targets)::numeric AS red_zone_targets,
                  SUM(u.red_zone_carries)::numeric AS red_zone_carries,
                  SUM(u.qb_dropbacks)::numeric AS qb_dropbacks,
                  AVG(u.success_rate) AS success_rate
                FROM nfl_dp_rosters r
                JOIN nfl_dp_player_usage_weekly u
                  ON u.player_id = r.player_id
                  AND u.season = r.rookie_year
                WHERE r.rookie_year IS NOT NULL
                  AND r.rookie_year = r.season
                  AND (CAST(:through_season AS int) IS NULL OR r.rookie_year <= CAST(:through_season AS int))
                  AND u.games_played > 0
                GROUP BY u.player_id, r.position, r.draft_number, u.season
                HAVING COUNT(DISTINCT u.week) > 0
                """
            ),
            {"through_season": through_season},
        ).mappings().all()

        buckets: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
        for row in rookie_rows:
            position = (row["position"] or "UNK").upper()
            tier = draft_tier_for_pick(row["draft_number"])
            key = (position, tier)
            games = float(row["games_played"] or 0)
            if games <= 0:
                continue
            buckets.setdefault(key, []).append(
                {
                    "season": int(row["season"]),
                    "games": games,
                    "involvement_plays": float(row["involvement_plays"] or 0) / games,
                    "targets": float(row["targets"] or 0) / games,
                    "receptions": float(row["receptions"] or 0) / games,
                    "receiving_yards": float(row["receiving_yards"] or 0) / games,
                    "rush_attempts": float(row["rush_attempts"] or 0) / games,
                    "rush_yards": float(row["rush_yards"] or 0) / games,
                    "red_zone_targets": float(row["red_zone_targets"] or 0) / games,
                    "red_zone_carries": float(row["red_zone_carries"] or 0) / games,
                    "qb_dropbacks": float(row["qb_dropbacks"] or 0) / games,
                    "success_rate": float(row["success_rate"]) if row["success_rate"] is not None else None,
                    "player_id": row["player_id"],
                }
            )

        max_season = through_season
        if max_season is None:
            max_season = session.execute(text("SELECT COALESCE(MAX(rookie_year), 0) FROM nfl_dp_rosters")).scalar_one()

        def _weight(sample: Dict[str, Any]) -> float:
            return float(recency_decay) ** max(0, int(max_season) - sample["season"])

        def _weighted_avg(samples: List[Dict[str, Any]], weights: List[float], key: str) -> float:
            total_w = sum(weights)
            if total_w <= 0:
                return 0.0
            return sum(s[key] * w for s, w in zip(samples, weights)) / total_w

        session.execute(text("DELETE FROM nfl_dp_rookie_usage_baselines"))
        written = 0
        for (position, tier), samples in buckets.items():
            n_players = len({s["player_id"] for s in samples})
            if n_players < min_sample_players:
                continue
            n = len(samples)
            weights = [_weight(s) for s in samples]
            success_pairs = [(s["success_rate"], w) for s, w in zip(samples, weights) if s["success_rate"] is not None]
            session.execute(
                text(
                    """
                    INSERT INTO nfl_dp_rookie_usage_baselines (
                      position, draft_tier, sample_players, sample_player_weeks,
                      avg_games_played, avg_involvement_plays_per_game, avg_targets_per_game,
                      avg_receptions_per_game, avg_receiving_yards_per_game,
                      avg_rush_attempts_per_game, avg_rush_yards_per_game,
                      avg_red_zone_targets_per_game, avg_red_zone_carries_per_game,
                      avg_qb_dropbacks_per_game, avg_success_rate,
                      computed_through_season, computed_at
                    ) VALUES (
                      :position, :draft_tier, :sample_players, :sample_player_weeks,
                      :avg_games_played, :avg_involvement_plays_per_game, :avg_targets_per_game,
                      :avg_receptions_per_game, :avg_receiving_yards_per_game,
                      :avg_rush_attempts_per_game, :avg_rush_yards_per_game,
                      :avg_red_zone_targets_per_game, :avg_red_zone_carries_per_game,
                      :avg_qb_dropbacks_per_game, :avg_success_rate,
                      :computed_through_season, NOW()
                    )
                    """
                ),
                {
                    "position": position,
                    "draft_tier": tier,
                    "sample_players": n_players,
                    "sample_player_weeks": n,
                    "avg_games_played": _weighted_avg(samples, weights, "games"),
                    "avg_involvement_plays_per_game": _weighted_avg(samples, weights, "involvement_plays"),
                    "avg_targets_per_game": _weighted_avg(samples, weights, "targets"),
                    "avg_receptions_per_game": _weighted_avg(samples, weights, "receptions"),
                    "avg_receiving_yards_per_game": _weighted_avg(samples, weights, "receiving_yards"),
                    "avg_rush_attempts_per_game": _weighted_avg(samples, weights, "rush_attempts"),
                    "avg_rush_yards_per_game": _weighted_avg(samples, weights, "rush_yards"),
                    "avg_red_zone_targets_per_game": _weighted_avg(samples, weights, "red_zone_targets"),
                    "avg_red_zone_carries_per_game": _weighted_avg(samples, weights, "red_zone_carries"),
                    "avg_qb_dropbacks_per_game": _weighted_avg(samples, weights, "qb_dropbacks"),
                    "avg_success_rate": (
                        (sum(sr * w for sr, w in success_pairs) / sum(w for _, w in success_pairs))
                        if success_pairs
                        else None
                    ),
                    "computed_through_season": max_season,
                },
            )
            written += 1
        session.commit()
        return {
            "status": "ok",
            "through_season": max_season,
            "buckets_written": written,
            "buckets_skipped_low_sample": len(buckets) - written,
            "total_rookie_player_seasons": len({r["player_id"] for r in rookie_rows}),
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_rookie_baseline(session: Any, *, position: str, draft_number: int | None) -> Dict[str, Any] | None:
    tier = draft_tier_for_pick(draft_number)
    position_norm = (position or "UNK").upper()

    if position_norm not in SKILL_OFFENSE_POSITIONS:
        return dict(_ZERO_BASELINE)

    row = session.execute(
        text(
            "SELECT * FROM nfl_dp_rookie_usage_baselines WHERE position = :position AND draft_tier = :tier"
        ),
        {"position": position_norm, "tier": tier},
    ).mappings().first()
    if row is not None:
        return dict(row)
    # Fall back to the same draft tier across other SKILL offense positions
    # only (never defense/OL/ST) if this exact position+tier combo had too
    # few historical samples.
    row = session.execute(
        text(
            """
            SELECT * FROM nfl_dp_rookie_usage_baselines
            WHERE draft_tier = :tier AND position = ANY(:skill_positions)
            ORDER BY sample_players DESC
            LIMIT 1
            """
        ),
        {"tier": tier, "skill_positions": list(SKILL_OFFENSE_POSITIONS)},
    ).mappings().first()
    return dict(row) if row is not None else dict(_ZERO_BASELINE)
