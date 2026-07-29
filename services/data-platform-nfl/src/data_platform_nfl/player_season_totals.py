"""Real, permanent generator for the player season-total artifact CSVs
(`player_regular_season_totals.csv` / `player_playoff_totals.csv`) consumed
directly by the live web app (see apps/web/lib/nfl-preseason-artifacts.ts).

Replaces the prior undocumented approach in scripts/nfl/simulate_2026_season.py,
which simply `shutil.copy`'d these two files forward from whatever the oldest
existing data/ops bundle happened to contain -- meaning they silently froze at
whatever methodology produced them (a flat `games_projected=18` for every
regular-season player, and `games_projected=4` for every playoff player,
neither reflecting real per-week variation), and were never regenerated after
this session's player-projection pipeline fixes (nfl_dp_player_usage_weekly /
nfl_player_projection_features_weekly / rookie baselines).

This module is DB-only (reads nfl_player_projection_baselines and
nfl_dp_schedules, both plain tables -- no model-service Python imports
required), so it lives here rather than in services/model-service, matching
the service-boundary convention used by preseason_hydration.py and
rookie_baselines.py: model-service owns *producing* the weekly baseline rows
(materialize_nfl_player_baseline_projections), this module owns *aggregating*
already-materialized rows into a season-total shape.

Regular season methodology
---------------------------
For every player, across every week that player's team has a REAL scheduled
game that season (see `_real_game_weeks_by_team`, keyed off game_id being
non-empty on the weekly baseline row -- bye weeks leave game_id blank, see
nfl_player_projection_features_weekly's `source <> ` guarded ingestion):
  - `*_yards_total` / `*_tds_total` = sum of that week's `*_mean` projection.
    Summing per-week means is the statistically correct way to build an
    expected season total from a set of per-week expected values (linearity
    of expectation) -- no distributional assumption beyond independence
    across weeks is required.
  - `games_projected` = COUNT of real weeks with a row for that player (NOT a
    hardcoded constant). A player whose team has a bye some week, or who is
    being projected mid-season with fewer remaining weeks, naturally gets a
    smaller count.
  - `anytime_td_prob` = 1 - PRODUCT_w(1 - anytime_td_prob_w): the probability
    the player scores a TD in AT LEAST ONE of their real games this season,
    assuming independence across weeks. This is the deliberate choice over
    the alternative "expected total TD-scoring games" (= sum of weekly
    rush_tds_mean+rec_tds_mean, which is already redundant with the
    rush_tds_total/rec_tds_total columns two columns over) because the field
    is literally named `anytime_td_prob` -- callers (including the web app)
    reasonably expect a bounded [0, 1] probability, not a raw expected count
    that can exceed 1.0 for a bell-cow RB/WR over a full season. Summing the
    means already gives you the "expected TD count" number via
    rush_tds_total + rec_tds_total; this field intentionally preserves
    probability semantics instead of duplicating that.

Playoff methodology
--------------------
There is no real playoff schedule to project against. Instead:
  - Compute each player's REGULAR-SEASON per-game rate (season total / real
    games played, from the exact same aggregation above) as the basis rate --
    a team's playoff-week usage pattern for a given player is assumed to look
    like their season-average usage, which is the same assumption the task
    explicitly sanctions ("a team's playoff roster/usage doesn't fundamentally
    change"). Using the season AVERAGE per-game rate rather than picking one
    arbitrary regular-season week is a deliberate refinement: it is a smoothed
    read on the player's role that already nets out any single bye-adjacent
    or blowout-distorted week.
  - Multiply by that player's team's EXPECTED number of playoff games, which
    should be the real Monte-Carlo-derived value from
    scripts/nfl/simulate_2026_season.py's 50,000-replicate bracket sim (each
    replicate already resolves exactly how many playoff games a team plays --
    0 if eliminated in the regular season, up through 4 for a Super Bowl
    winner -- see `total_playoff_games_played` counter added to that script).
    If that per-team dict isn't available (e.g. this module used standalone
    without the simulator wired in), `FALLBACK_EXPECTED_GAMES_GIVEN_APPEARANCE`
    provides a documented, derived (not guessed) fallback -- see its
    docstring for the bracket-structure derivation.
  - `anytime_td_prob` for playoffs re-applies the same "at least one game"
    formula, but over a fractional/expected number of games: using each
    player's regular-season AVERAGE (not summed) weekly anytime_td_prob as a
    per-game rate p, playoff anytime_td_prob = 1 - (1-p)^expected_games. This
    is the continuous generalization of the regular-season formula (valid for
    non-integer "games" because it's already an expectation calculation, not
    a per-game simulation) and collapses to the same formula if
    expected_games happened to be a whole number of certain playoff games.
"""

from __future__ import annotations

import csv
import json
import os
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import text

CSV_FIELDNAMES: List[str] = [
    "season",
    "player_key",
    "player_name",
    "team",
    "position",
    "games_projected",
    "pass_yards_total",
    "rush_yards_total",
    "receiving_yards_total",
    "receptions_total",
    "pass_tds_total",
    "rush_tds_total",
    "rec_tds_total",
    "anytime_td_prob",
]

_WEEKLY_STAT_KEYS = (
    "pass_yards_mean",
    "rush_yards_mean",
    "receiving_yards_mean",
    "receptions_mean",
    "pass_tds_mean",
    "rush_tds_mean",
    "rec_tds_mean",
)

# Derivation: the current 7-seeds-per-conference (14-team) playoff bracket
# plays 6 wildcard-round games + 4 divisional-round games + 2 conference
# championship games + 1 Super Bowl = 13 games total, i.e. 26 team-game
# appearances (each game has 2 participating teams). Spread evenly across
# the 14 teams that make the playoffs in any given season, that is
# 26 / 14 ~= 1.857 games per playoff appearance on average. This is an
# unweighted average across all seeds (a bye-week #1 seed plays fewer early
# games but survives longer on average, a 7-seed usually plays exactly one
# game and exits) -- a real per-team estimate (from the season Monte Carlo,
# see scripts/nfl/simulate_2026_season.py's total_playoff_games_played
# counter) is always preferred over this leaguewide constant when available.
FALLBACK_EXPECTED_GAMES_GIVEN_APPEARANCE = 26.0 / 14.0

# Season-total QB room lock — mirrors model-service compute_qb_starter_shares
# winner-take-most template. Applied at aggregation time so hub CSVs can be
# regenerated without a full 100k season MC re-run. Leakage-safe signals only:
# week-1 depth chart + prior-season pass attempts (never same-season results).
_QB_PRIMARY_SHARE = 0.92
_QB_SECONDARY_SHARE = 0.06
_QB_TERTIARY_SHARE = 0.02

# Skill prior-anchor calibration (RB rush / WR+TE receiving). Leakage-safe:
# REG weeks 1–18 from seasons strictly before the projection season only.
# Upward-only blend toward max prior YPG × games_projected — corrects
# compressed elite ceilings without cutting publish floors.
_SKILL_PRIOR_MIN_GAMES = 8
_SKILL_PRIOR_LOOKBACK_SEASONS = 2


def aggregate_weekly_projection_rows(weekly_rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Pure aggregation: turn a player's list of real-week baseline rows into
    one season-total dict. Each item of `weekly_rows` must provide the keys in
    `_WEEKLY_STAT_KEYS` plus `anytime_td_prob` (all as floats/None).

    Returns the season-shaped numeric fields only (games_projected plus the
    8 `*_total` / `anytime_td_prob` fields) -- identity fields (player_name,
    team, position, player_key) are attached by the caller since they don't
    require any statistical aggregation.
    """
    rows = list(weekly_rows)
    games_projected = len(rows)

    def _sum(key: str) -> float:
        return round(sum(float(row.get(key) or 0.0) for row in rows), 3)

    prob_survives_tdless = 1.0
    for row in rows:
        p = max(0.0, min(1.0, float(row.get("anytime_td_prob") or 0.0)))
        prob_survives_tdless *= (1.0 - p)
    season_anytime_td_prob = round(1.0 - prob_survives_tdless, 4)

    return {
        "games_projected": games_projected,
        "pass_yards_total": _sum("pass_yards_mean"),
        "rush_yards_total": _sum("rush_yards_mean"),
        "receiving_yards_total": _sum("receiving_yards_mean"),
        "receptions_total": _sum("receptions_mean"),
        "pass_tds_total": _sum("pass_tds_mean"),
        "rush_tds_total": _sum("rush_tds_mean"),
        "rec_tds_total": _sum("rec_tds_mean"),
        "anytime_td_prob": season_anytime_td_prob,
    }


def _fetch_real_weekly_rows(
    session: Any, *, season: int, model_version: str, weeks: Optional[List[int]] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """Returns {player_key: [weekly_row_dict, ...]} for every REAL game week
    (game_id present -- bye weeks leave it blank, see module docstring),
    ordered by week. player_key is `player_uid` when resolved, else falls
    back to `team:player_id` so no player is silently dropped even if
    identity resolution hasn't run for them yet.
    """
    week_filter = "AND week = ANY(:weeks)" if weeks else ""
    params: Dict[str, Any] = {"season": int(season), "model_version": model_version}
    if weeks:
        params["weeks"] = list(weeks)
    rows = session.execute(
        text(
            f"""
            SELECT
              week, team, player_id, player_uid, player_name, position, game_id,
              pass_yards_mean, rush_yards_mean, receiving_yards_mean, receptions_mean,
              pass_tds_mean, rush_tds_mean, rec_tds_mean, anytime_td_prob
            FROM nfl_player_projection_baselines
            WHERE season = :season
              AND model_version = :model_version
              AND game_id IS NOT NULL AND game_id <> ''
              {week_filter}
            ORDER BY week
            """
        ),
        params,
    ).mappings().all()

    by_player: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        player_key = str(row["player_uid"]) if row["player_uid"] is not None else f"{row['team']}:{row['player_id']}"
        by_player.setdefault(player_key, []).append(dict(row))
    return by_player


def _qb_depth_score(depth_order: Optional[float]) -> float:
    if depth_order is None:
        return 0.15
    d = float(depth_order)
    if d <= 1.0:
        return 1.0
    if d <= 2.0:
        return 0.35
    if d <= 3.0:
        return 0.12
    return 0.04


def _allocate_qb_winner_take_most(ranked_keys: List[str]) -> Dict[str, float]:
    out: Dict[str, float] = {key: 0.0 for key in ranked_keys}
    if not ranked_keys:
        return out
    if len(ranked_keys) == 1:
        out[ranked_keys[0]] = 1.0
        return out
    out[ranked_keys[0]] = _QB_PRIMARY_SHARE
    out[ranked_keys[1]] = _QB_SECONDARY_SHARE
    if len(ranked_keys) == 2:
        out[ranked_keys[0]] = _QB_PRIMARY_SHARE + _QB_TERTIARY_SHARE
        return out
    residual = _QB_TERTIARY_SHARE
    others = ranked_keys[2:]
    each = residual / len(others)
    for key in others:
        out[key] = each
    return out


def designate_qb_starter_shares(
    *,
    player_ids: List[str],
    depth_orders: Dict[str, float],
    prior_attempts: Dict[str, float],
) -> Dict[str, float]:
    """Leakage-safe QB1 designation shares for one team room.

    Scoring mirrors `compute_qb_starter_shares` in nfl_player_projection_engine:
    prior-season attempts + week-1 depth beat inflated backup baselines.
    """
    keys = [str(pid) for pid in player_ids if pid]
    if not keys:
        return {}
    if len(keys) == 1:
        return {keys[0]: 1.0}

    prior_total = sum(float(prior_attempts.get(k) or 0.0) for k in keys)
    has_prior = prior_total > 0.0
    has_depth = any(k in depth_orders for k in keys)
    if not has_prior and not has_depth:
        # No signal — leave equal full share; caller should not invent an order.
        return {k: 1.0 for k in keys}

    scores: Dict[str, float] = {}
    for k in keys:
        prior_share = float(prior_attempts.get(k) or 0.0) / prior_total if prior_total > 0.0 else 0.0
        depth_score = _qb_depth_score(depth_orders.get(k) if k in depth_orders else None)
        if has_prior:
            scores[k] = (0.55 * prior_share) + (0.45 * depth_score)
        else:
            scores[k] = depth_score
    if has_prior:
        ordered = sorted(((float(prior_attempts.get(k) or 0.0), k) for k in keys), reverse=True)
        top_att, top_key = ordered[0]
        second_att = ordered[1][0] if len(ordered) > 1 else 0.0
        if top_att >= 120.0 and top_att >= (1.2 * max(second_att, 1.0)):
            scores[top_key] = scores.get(top_key, 0.0) + 0.22
    ranked = sorted(
        keys,
        key=lambda k: (-scores[k], float(depth_orders.get(k, 99.0) or 99.0), str(k)),
    )
    return _allocate_qb_winner_take_most(ranked)


def apply_qb_starter_volume_lock(
    rows: List[Dict[str, Any]],
    *,
    depth_by_team: Dict[str, Dict[str, float]],
    prior_attempts_by_team: Dict[str, Dict[str, float]],
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Scale QB pass(/rush) season totals to one starter-level volume per team.

    Root failure: weekly baselines still emit near-starter `pass_yards_mean` for
    backups (Flacco 3845 vs Burrow 2290) even when week-1 depth correctly lists
    the starter. Lock at season-total layer so hub regen does not need a full MC.

    Method: designate shares via depth + prior attempts; take the room's max
    pass-yard total as the "full-rate" unit; assign starter = full_rate and
    backups = full_rate * (share / primary_share). Scale pass_tds with the same
    factor; scale QB rush yards for non-primaries the same way (backup rush
    from spot-start baselines is also inflated).
    """
    by_team: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        if str(row.get("position") or "").upper() != "QB":
            continue
        by_team.setdefault(str(row.get("team") or ""), []).append(row)

    audit_rooms: List[Dict[str, Any]] = []
    for team, room in by_team.items():
        if len(room) < 2:
            continue
        id_to_row: Dict[str, Dict[str, Any]] = {}
        for r in room:
            pid = str(r.get("player_id") or "")
            if not pid:
                # Fallback key used when uid missing: "TEAM:player_id"
                key = str(r.get("player_key") or "")
                pid = key.split(":", 1)[-1] if ":" in key else key
            if pid:
                id_to_row[pid] = r
        if len(id_to_row) < 2:
            continue
        depths = depth_by_team.get(team) or {}
        priors = prior_attempts_by_team.get(team) or {}
        shares = designate_qb_starter_shares(
            player_ids=list(id_to_row.keys()),
            depth_orders=depths,
            prior_attempts=priors,
        )
        if not shares or all(abs(float(v) - 1.0) < 1e-9 for v in shares.values()):
            audit_rooms.append(
                {
                    "team": team,
                    "status": "skipped_no_decisive_signal",
                    "qbs": [
                        {
                            "player_name": r.get("player_name"),
                            "player_id": pid,
                            "pass_yards_before": float(r.get("pass_yards_total") or 0.0),
                        }
                        for pid, r in id_to_row.items()
                    ],
                }
            )
            continue
        primary_share = max(float(v) for v in shares.values()) or _QB_PRIMARY_SHARE
        full_rate = max(float(r.get("pass_yards_total") or 0.0) for r in id_to_row.values())
        if full_rate <= 0.0:
            continue
        room_audit: List[Dict[str, Any]] = []
        for pid, r in id_to_row.items():
            share = float(shares.get(pid) or 0.0)
            factor = share / primary_share if primary_share > 0 else 0.0
            before = float(r.get("pass_yards_total") or 0.0)
            after = round(full_rate * factor, 3)
            scale = (after / before) if before > 1e-9 else 0.0
            r["pass_yards_total"] = after
            r["pass_tds_total"] = round(float(r.get("pass_tds_total") or 0.0) * scale, 3)
            # Backup rush from spot-start baselines is similarly inflated.
            if factor < 0.99:
                r["rush_yards_total"] = round(float(r.get("rush_yards_total") or 0.0) * factor, 3)
                r["rush_tds_total"] = round(float(r.get("rush_tds_total") or 0.0) * factor, 3)
            room_audit.append(
                {
                    "player_name": r.get("player_name"),
                    "player_id": pid,
                    "share": round(share, 4),
                    "pass_yards_before": round(before, 1),
                    "pass_yards_after": after,
                    "is_primary": share >= primary_share - 1e-9,
                }
            )
        audit_rooms.append(
            {
                "team": team,
                "status": "locked",
                "full_rate_pass_yards": round(full_rate, 1),
                "qbs": room_audit,
            }
        )

    rows.sort(
        key=lambda r: (
            -(
                float(r.get("pass_yards_total") or 0.0)
                + float(r.get("rush_yards_total") or 0.0)
                + float(r.get("receiving_yards_total") or 0.0)
            ),
            str(r.get("player_name") or ""),
        )
    )
    locked_n = sum(1 for a in audit_rooms if a.get("status") == "locked")
    return rows, {
        "teams_locked": locked_n,
        "rooms": audit_rooms,
        "method": "depth_week1_plus_prior_attempts_winner_take_most",
        "primary_share": _QB_PRIMARY_SHARE,
        "secondary_share": _QB_SECONDARY_SHARE,
    }


def fetch_qb_room_lock_signals(
    session: Any, *, season: int
) -> tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, float]]]:
    """Load leakage-safe designation inputs: week-1 depth + prior-season attempts."""
    depth_by_team: Dict[str, Dict[str, float]] = {}
    # Prefer inferred weekly depth (has depth_order + depth_slot). Fall back to
    # official depth_team when inferred missing for a team.
    inferred = session.execute(
        text(
            """
            SELECT team, player_id, depth_order
            FROM nfl_dp_depth_chart_weekly
            WHERE season = :season AND week = 1 AND upper(position) = 'QB'
              AND player_id IS NOT NULL AND player_id <> ''
            """
        ),
        {"season": int(season)},
    ).mappings().all()
    for row in inferred:
        team = str(row["team"] or "")
        pid = str(row["player_id"] or "")
        if not team or not pid:
            continue
        depth_by_team.setdefault(team, {})[pid] = float(row["depth_order"] or 99.0)

    if not depth_by_team:
        official = session.execute(
            text(
                """
                SELECT DISTINCT ON (team, player_id)
                  team, player_id, depth_team
                FROM nfl_dp_official_depth_charts
                WHERE season = :season AND upper(position) LIKE '%%QB%%'
                  AND player_id IS NOT NULL AND player_id <> ''
                ORDER BY team, player_id, week ASC
                """
            ),
            {"season": int(season)},
        ).mappings().all()
        for row in official:
            team = str(row["team"] or "")
            pid = str(row["player_id"] or "")
            if not team or not pid:
                continue
            depth_by_team.setdefault(team, {})[pid] = float(row["depth_team"] or 99.0)

    prior_by_team: Dict[str, Dict[str, float]] = {}
    prior_season = int(season) - 1
    prior_rows = session.execute(
        text(
            """
            SELECT team, player_id, SUM(COALESCE(pass_attempts, 0))::float AS att
            FROM nfl_dp_player_usage_weekly
            WHERE season = :prior_season AND upper(position) = 'QB'
              AND player_id IS NOT NULL AND player_id <> ''
            GROUP BY team, player_id
            """
        ),
        {"prior_season": prior_season},
    ).mappings().all()
    for row in prior_rows:
        team = str(row["team"] or "")
        pid = str(row["player_id"] or "")
        if not team or not pid:
            continue
        prior_by_team.setdefault(team, {})[pid] = float(row["att"] or 0.0)
    return depth_by_team, prior_by_team


def _skill_prior_blend_weight(prior_season_yards: float, *, kind: str) -> float:
    """Higher weight for established volume leaders; 0 below meaningful floors."""
    y = float(prior_season_yards or 0.0)
    if kind == "rush":
        if y >= 1200.0:
            return 0.55
        if y >= 800.0:
            return 0.40
        if y >= 500.0:
            return 0.25
        return 0.0
    # receiving
    if y >= 1200.0:
        return 0.55
    if y >= 900.0:
        return 0.45
    if y >= 600.0:
        return 0.30
    return 0.0


def fetch_skill_prior_anchors(session: Any, *, season: int) -> Dict[str, Dict[str, float]]:
    """Per-player max REG YPG (rush / receiving) over the prior lookback window.

    Leakage-safe: seasons in [season-lookback, season-1], weeks 1–18 only.
    Requires `_SKILL_PRIOR_MIN_GAMES` involvement games in that season row.
    Keyed by GSIS `player_id` (same id used on baseline rows).
    """
    lookback = int(_SKILL_PRIOR_LOOKBACK_SEASONS)
    seasons = [int(season) - i for i in range(1, lookback + 1) if int(season) - i >= 2000]
    if not seasons:
        return {}
    rows = session.execute(
        text(
            """
            SELECT season, player_id,
                   COUNT(*) FILTER (
                     WHERE COALESCE(rush_attempts, 0) > 0
                        OR COALESCE(targets, 0) > 0
                        OR COALESCE(rush_yards, 0) > 0
                        OR COALESCE(receiving_yards, 0) > 0
                   ) AS games,
                   SUM(COALESCE(rush_yards, 0))::float AS rush,
                   SUM(COALESCE(receiving_yards, 0))::float AS rec,
                   SUM(COALESCE(receptions, 0))::float AS receptions
            FROM nfl_dp_player_usage_weekly
            WHERE season = ANY(:seasons)
              AND week BETWEEN 1 AND 18
              AND upper(position) IN ('RB', 'WR', 'TE')
              AND player_id IS NOT NULL AND player_id <> ''
            GROUP BY season, player_id
            """
        ),
        {"seasons": seasons},
    ).mappings().all()

    anchors: Dict[str, Dict[str, float]] = {}
    for row in rows:
        games = int(row["games"] or 0)
        if games < _SKILL_PRIOR_MIN_GAMES:
            continue
        pid = str(row["player_id"])
        rush_ypg = float(row["rush"] or 0.0) / games
        rec_ypg = float(row["rec"] or 0.0) / games
        rec_gpg = float(row["receptions"] or 0.0) / games
        cur = anchors.setdefault(
            pid,
            {
                "rush_ypg": 0.0,
                "rec_ypg": 0.0,
                "rec_gpg": 0.0,
                "rush_games": 0.0,
                "rec_games": 0.0,
            },
        )
        if rush_ypg > float(cur["rush_ypg"]):
            cur["rush_ypg"] = rush_ypg
            cur["rush_games"] = float(games)
        if rec_ypg > float(cur["rec_ypg"]):
            cur["rec_ypg"] = rec_ypg
            cur["rec_games"] = float(games)
            cur["rec_gpg"] = rec_gpg
    return anchors


def apply_skill_prior_anchor_calibration(
    rows: List[Dict[str, Any]],
    *,
    anchors_by_player_id: Dict[str, Dict[str, float]],
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Upward-only blend of RB rush / WR+TE receiving toward prior YPG anchors.

    Root failure: weekly baselines compress elites (low WR role_confidence,
    soft talent factors) so season sums undershoot historical leader floors
    (rush ≥1400, rec ≥1300, 3× WR ≥1200) even when games_projected=17.

    Method: for each player with a leakage-safe prior REG sample (≥8 games),
    anchor = max_prior_ypg × games_projected. If model total < anchor, blend
    toward the anchor with volume-tiered weight. Scale related counting stats
    (TDs, receptions) by the same factor. Never pulls yards down.
    """
    adjusted: List[Dict[str, Any]] = []
    for row in rows:
        pos = str(row.get("position") or "").upper()
        pid = str(row.get("player_id") or "")
        if not pid:
            key = str(row.get("player_key") or "")
            # Fallback when uid-keyed: "TEAM:gsis" — take trailing segment.
            pid = key.split(":", 1)[-1] if ":" in key else ""
        anchor = anchors_by_player_id.get(pid) if pid else None
        if not anchor:
            continue
        games = float(row.get("games_projected") or 0.0)
        if games <= 0.0:
            continue

        if pos == "RB" and float(anchor.get("rush_ypg") or 0.0) > 0.0:
            prior_games = float(anchor.get("rush_games") or 0.0)
            prior_abs = float(anchor["rush_ypg"]) * prior_games
            target = float(anchor["rush_ypg"]) * games
            weight = _skill_prior_blend_weight(prior_abs, kind="rush")
            before = float(row.get("rush_yards_total") or 0.0)
            if weight > 0.0 and before + 1e-9 < target:
                after = (1.0 - weight) * before + weight * target
                scale = after / before if before > 1e-9 else 0.0
                row["rush_yards_total"] = round(after, 3)
                row["rush_tds_total"] = round(float(row.get("rush_tds_total") or 0.0) * scale, 3)
                adjusted.append(
                    {
                        "stat": "rush",
                        "player_name": row.get("player_name"),
                        "player_id": pid,
                        "team": row.get("team"),
                        "position": pos,
                        "before": round(before, 1),
                        "after": round(after, 1),
                        "anchor": round(target, 1),
                        "prior_season_yards": round(prior_abs, 1),
                        "blend_weight": weight,
                    }
                )

        if pos in {"WR", "TE"} and float(anchor.get("rec_ypg") or 0.0) > 0.0:
            prior_games = float(anchor.get("rec_games") or 0.0)
            prior_abs = float(anchor["rec_ypg"]) * prior_games
            target = float(anchor["rec_ypg"]) * games
            weight = _skill_prior_blend_weight(prior_abs, kind="rec")
            before = float(row.get("receiving_yards_total") or 0.0)
            if weight > 0.0 and before + 1e-9 < target:
                after = (1.0 - weight) * before + weight * target
                scale = after / before if before > 1e-9 else 0.0
                row["receiving_yards_total"] = round(after, 3)
                row["rec_tds_total"] = round(float(row.get("rec_tds_total") or 0.0) * scale, 3)
                # Prefer prior catch rate when scaling receptions; else yards scale.
                prior_rec_gpg = float(anchor.get("rec_gpg") or 0.0)
                if prior_rec_gpg > 0.0 and scale > 0.0:
                    # Blend receptions toward prior gpg × games with same weight.
                    before_rec = float(row.get("receptions_total") or 0.0)
                    rec_target = prior_rec_gpg * games
                    if before_rec + 1e-9 < rec_target:
                        row["receptions_total"] = round(
                            (1.0 - weight) * before_rec + weight * rec_target, 3
                        )
                    else:
                        row["receptions_total"] = round(before_rec * scale, 3)
                else:
                    row["receptions_total"] = round(
                        float(row.get("receptions_total") or 0.0) * scale, 3
                    )
                adjusted.append(
                    {
                        "stat": "receiving",
                        "player_name": row.get("player_name"),
                        "player_id": pid,
                        "team": row.get("team"),
                        "position": pos,
                        "before": round(before, 1),
                        "after": round(after, 1),
                        "anchor": round(target, 1),
                        "prior_season_yards": round(prior_abs, 1),
                        "blend_weight": weight,
                    }
                )

    rows.sort(
        key=lambda r: (
            -(
                float(r.get("pass_yards_total") or 0.0)
                + float(r.get("rush_yards_total") or 0.0)
                + float(r.get("receiving_yards_total") or 0.0)
            ),
            str(r.get("player_name") or ""),
        )
    )
    adjusted.sort(key=lambda a: -float(a.get("after") or 0.0))
    return rows, {
        "applied": True,
        "method": "prior_reg_ypg_upward_blend_max_lookback2",
        "min_prior_games": _SKILL_PRIOR_MIN_GAMES,
        "lookback_seasons": _SKILL_PRIOR_LOOKBACK_SEASONS,
        "players_adjusted": len(adjusted),
        "top_adjustments": adjusted[:25],
    }


def generate_player_regular_season_totals(
    session: Any,
    *,
    season: int,
    model_version: str = "nfl-player-v1",
    apply_qb_lock: bool = True,
    apply_skill_prior: bool = True,
) -> tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    """Season-total rows for every player with at least one real regular-season
    weekly projection, in `CSV_FIELDNAMES` shape.

    Returns (rows, qb_lock_audit, skill_prior_audit).
    """
    by_player = _fetch_real_weekly_rows(session, season=season, model_version=model_version)

    output_rows: List[Dict[str, Any]] = []
    for player_key, weekly_rows in by_player.items():
        latest = weekly_rows[-1]
        totals = aggregate_weekly_projection_rows(weekly_rows)
        output_rows.append(
            {
                "season": season,
                "player_key": player_key,
                "player_id": latest.get("player_id"),
                "player_name": latest["player_name"],
                "team": latest["team"],
                "position": latest["position"],
                **totals,
            }
        )
    lock_audit: Dict[str, Any] = {"applied": False, "teams_locked": 0, "rooms": []}
    if apply_qb_lock:
        depth_by_team, prior_by_team = fetch_qb_room_lock_signals(session, season=season)
        output_rows, lock_audit = apply_qb_starter_volume_lock(
            output_rows,
            depth_by_team=depth_by_team,
            prior_attempts_by_team=prior_by_team,
        )
        lock_audit["applied"] = True

    skill_audit: Dict[str, Any] = {"applied": False, "players_adjusted": 0}
    if apply_skill_prior:
        anchors = fetch_skill_prior_anchors(session, season=season)
        output_rows, skill_audit = apply_skill_prior_anchor_calibration(
            output_rows, anchors_by_player_id=anchors
        )
        skill_audit["anchors_loaded"] = len(anchors)
    elif not apply_qb_lock:
        output_rows.sort(
            key=lambda r: (
                -(
                    float(r.get("pass_yards_total") or 0.0)
                    + float(r.get("rush_yards_total") or 0.0)
                    + float(r.get("receiving_yards_total") or 0.0)
                ),
                str(r.get("player_name") or ""),
            )
        )
    return output_rows, lock_audit, skill_audit


def evaluate_season_skill_leader_quality(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Publish gates for rush / receiving season totals (alongside pass)."""
    rush = sorted(rows, key=lambda r: float(r.get("rush_yards_total") or 0.0), reverse=True)
    rec = sorted(
        [r for r in rows if str(r.get("position") or "").upper() in {"WR", "TE"}],
        key=lambda r: float(r.get("receiving_yards_total") or 0.0),
        reverse=True,
    )
    top_rush = rush[0] if rush else None
    top_rec = rec[0] if rec else None
    top_rush_yd = float(top_rush["rush_yards_total"]) if top_rush else 0.0
    top_rec_yd = float(top_rec["receiving_yards_total"]) if top_rec else 0.0
    wr_1200 = sum(
        1
        for r in rows
        if str(r.get("position") or "").upper() == "WR" and float(r.get("receiving_yards_total") or 0.0) >= 1200.0
    )
    rb_1400 = sum(
        1
        for r in rows
        if str(r.get("position") or "").upper() == "RB" and float(r.get("rush_yards_total") or 0.0) >= 1400.0
    )
    dual_rb_rooms: List[Dict[str, Any]] = []
    by_team: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        if str(row.get("position") or "").upper() != "RB":
            continue
        by_team.setdefault(str(row.get("team") or ""), []).append(row)
    for team, room in by_team.items():
        above = sorted(
            [r for r in room if float(r.get("rush_yards_total") or 0.0) >= 1000.0],
            key=lambda r: float(r.get("rush_yards_total") or 0.0),
            reverse=True,
        )
        if len(above) >= 2:
            dual_rb_rooms.append(
                {
                    "team": team,
                    "rbs": [
                        {
                            "player_name": r.get("player_name"),
                            "rush_yards_total": round(float(r.get("rush_yards_total") or 0.0), 1),
                        }
                        for r in above[:3]
                    ],
                }
            )
    return {
        "top_rusher": {
            "player_name": (top_rush or {}).get("player_name"),
            "pass_yards_total": None,
            "rush_yards_total": round(top_rush_yd, 1),
        },
        "top_receiver": {
            "player_name": (top_rec or {}).get("player_name"),
            "receiving_yards_total": round(top_rec_yd, 1),
        },
        "top_rusher_yards_gte_1400": top_rush_yd >= 1400.0,
        "top_receiver_yards_gte_1300": top_rec_yd >= 1300.0,
        "wr_with_1200_plus_count": wr_1200,
        "rb_with_1400_plus_count": rb_1400,
        "dual_1000_yard_rb_rooms": dual_rb_rooms,
        "dual_1000_yard_rb_rooms_count": len(dual_rb_rooms),
        # Soft desk signal: dual 1000+ rooms can be real committees; not a hard fail.
        "publish_ready_skill": bool(top_rush_yd >= 1400.0 and top_rec_yd >= 1300.0 and wr_1200 >= 3),
    }


def evaluate_season_pass_leader_quality(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Enterprise publish gate for season pass-yard totals.

    Catches the failure modes that made the board unusable for a paid desk:
    bridge QBs leading the league, compressed ~3.1k ceilings, and dual
    full-starter rooms (Burrow+Flacco both ~3k).
    """
    qbs = [r for r in rows if str(r.get("position") or "").upper() == "QB"]
    ranked = sorted(qbs, key=lambda r: float(r.get("pass_yards_total") or 0.0), reverse=True)
    top = ranked[0] if ranked else None
    top_yards = float(top["pass_yards_total"]) if top else 0.0
    top_name = str(top.get("player_name") or "") if top else ""

    dual_rooms: List[Dict[str, Any]] = []
    by_team: Dict[str, List[Dict[str, Any]]] = {}
    for row in qbs:
        by_team.setdefault(str(row.get("team") or ""), []).append(row)
    for team, room in by_team.items():
        above = sorted(
            [r for r in room if float(r.get("pass_yards_total") or 0.0) >= 1800.0],
            key=lambda r: float(r.get("pass_yards_total") or 0.0),
            reverse=True,
        )
        if len(above) >= 2:
            dual_rooms.append(
                {
                    "team": team,
                    "qbs": [
                        {"player_name": r.get("player_name"), "pass_yards_total": float(r.get("pass_yards_total") or 0.0)}
                        for r in above[:3]
                    ],
                }
            )

    # Real NFL recent leaders land ~4.2k-5.0k; a usable model should put #1
    # above ~3.8k and keep bridge/committee artifacts out of the top slot.
    bridge_markers = ("brissett", "minshew", "flacco", "wentz", "bridgewater", "foles")
    top_is_bridge = any(m in top_name.lower() for m in bridge_markers)
    checks = {
        "top_passer": {"player_name": top_name, "pass_yards_total": round(top_yards, 1)},
        "top_passer_yards_gte_3800": top_yards >= 3800.0,
        "top_passer_not_bridge_marker": not top_is_bridge,
        "dual_full_volume_qb_rooms": dual_rooms,
        "dual_full_volume_qb_rooms_count": len(dual_rooms),
        "no_dual_full_volume_qb_rooms": len(dual_rooms) == 0,
        "publish_ready": bool(
            top_yards >= 3800.0 and (not top_is_bridge) and len(dual_rooms) == 0
        ),
    }
    return checks


def generate_player_playoff_totals_from_regular(
    regular_rows: List[Dict[str, Any]],
    *,
    expected_playoff_games_by_team: Dict[str, float],
) -> List[Dict[str, Any]]:
    """Playoff totals from (possibly QB-locked) regular-season rates.

    Prefer this over re-aggregating weekly baselines so the season-total QB
    lock carries into playoff CSVs without a second designation pass.
    """
    output_rows: List[Dict[str, Any]] = []
    for row in regular_rows:
        team = str(row.get("team") or "")
        expected_games = float(expected_playoff_games_by_team.get(team, 0.0))
        real_games = float(row.get("games_projected") or 0.0)
        if real_games <= 0.0 or expected_games <= 0.0:
            pass_ypg = rush_ypg = rec_ypg = rec_g = pass_tdg = rush_tdg = rec_tdg = 0.0
            mean_p = 0.0
        else:
            pass_ypg = float(row.get("pass_yards_total") or 0.0) / real_games
            rush_ypg = float(row.get("rush_yards_total") or 0.0) / real_games
            rec_ypg = float(row.get("receiving_yards_total") or 0.0) / real_games
            rec_g = float(row.get("receptions_total") or 0.0) / real_games
            pass_tdg = float(row.get("pass_tds_total") or 0.0) / real_games
            rush_tdg = float(row.get("rush_tds_total") or 0.0) / real_games
            rec_tdg = float(row.get("rec_tds_total") or 0.0) / real_games
            # Invert the season anytime formula to a per-game rate when possible.
            season_p = max(0.0, min(1.0, float(row.get("anytime_td_prob") or 0.0)))
            mean_p = 1.0 - ((1.0 - season_p) ** (1.0 / real_games)) if season_p < 1.0 else 1.0
        playoff_anytime = round(1.0 - (1.0 - mean_p) ** expected_games, 4)
        output_rows.append(
            {
                "season": row.get("season"),
                "player_key": row.get("player_key"),
                "player_name": row.get("player_name"),
                "team": team,
                "position": row.get("position"),
                "games_projected": round(expected_games, 4),
                "pass_yards_total": round(pass_ypg * expected_games, 3),
                "rush_yards_total": round(rush_ypg * expected_games, 3),
                "receiving_yards_total": round(rec_ypg * expected_games, 3),
                "receptions_total": round(rec_g * expected_games, 3),
                "pass_tds_total": round(pass_tdg * expected_games, 3),
                "rush_tds_total": round(rush_tdg * expected_games, 3),
                "rec_tds_total": round(rec_tdg * expected_games, 3),
                "anytime_td_prob": playoff_anytime,
            }
        )
    output_rows.sort(
        key=lambda r: (
            -(
                float(r.get("pass_yards_total") or 0.0)
                + float(r.get("rush_yards_total") or 0.0)
                + float(r.get("receiving_yards_total") or 0.0)
            ),
            str(r.get("player_name") or ""),
        )
    )
    return output_rows


def generate_player_playoff_totals(
    session: Any,
    *,
    season: int,
    expected_playoff_games_by_team: Dict[str, float],
    model_version: str = "nfl-player-v1",
    regular_rows: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Expectation-weighted playoff season-total rows (see module docstring).

    When `regular_rows` is provided (preferred), rates are taken from those
    season totals so QB starter locks propagate. Otherwise falls back to
    weekly baseline aggregation (legacy path).
    """
    if regular_rows is not None:
        return generate_player_playoff_totals_from_regular(
            regular_rows,
            expected_playoff_games_by_team=expected_playoff_games_by_team,
        )

    by_player = _fetch_real_weekly_rows(session, season=season, model_version=model_version)

    output_rows: List[Dict[str, Any]] = []
    for player_key, weekly_rows in by_player.items():
        latest = weekly_rows[-1]
        team = latest["team"]
        expected_games = float(expected_playoff_games_by_team.get(team, 0.0))
        real_games_played = len(weekly_rows)
        if real_games_played == 0 or expected_games <= 0.0:
            per_game = {key: 0.0 for key in _WEEKLY_STAT_KEYS}
            mean_weekly_anytime_td_prob = 0.0
        else:
            season_totals = aggregate_weekly_projection_rows(weekly_rows)
            per_game = {
                "pass_yards_mean": season_totals["pass_yards_total"] / real_games_played,
                "rush_yards_mean": season_totals["rush_yards_total"] / real_games_played,
                "receiving_yards_mean": season_totals["receiving_yards_total"] / real_games_played,
                "receptions_mean": season_totals["receptions_total"] / real_games_played,
                "pass_tds_mean": season_totals["pass_tds_total"] / real_games_played,
                "rush_tds_mean": season_totals["rush_tds_total"] / real_games_played,
                "rec_tds_mean": season_totals["rec_tds_total"] / real_games_played,
            }
            mean_weekly_anytime_td_prob = sum(
                max(0.0, min(1.0, float(r.get("anytime_td_prob") or 0.0))) for r in weekly_rows
            ) / real_games_played

        playoff_anytime_td_prob = round(1.0 - (1.0 - mean_weekly_anytime_td_prob) ** expected_games, 4)
        output_rows.append(
            {
                "season": season,
                "player_key": player_key,
                "player_name": latest["player_name"],
                "team": team,
                "position": latest["position"],
                "games_projected": round(expected_games, 4),
                "pass_yards_total": round(per_game["pass_yards_mean"] * expected_games, 3),
                "rush_yards_total": round(per_game["rush_yards_mean"] * expected_games, 3),
                "receiving_yards_total": round(per_game["receiving_yards_mean"] * expected_games, 3),
                "receptions_total": round(per_game["receptions_mean"] * expected_games, 3),
                "pass_tds_total": round(per_game["pass_tds_mean"] * expected_games, 3),
                "rush_tds_total": round(per_game["rush_tds_mean"] * expected_games, 3),
                "rec_tds_total": round(per_game["rec_tds_mean"] * expected_games, 3),
                "anytime_td_prob": playoff_anytime_td_prob,
            }
        )
    output_rows.sort(key=lambda r: (-r["pass_yards_total"] - r["rush_yards_total"] - r["receiving_yards_total"], r["player_name"]))
    return output_rows


def write_player_totals_csv(rows: List[Dict[str, Any]], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in CSV_FIELDNAMES})


def generate_and_write_player_season_totals(
    session: Any,
    *,
    season: int,
    out_dir: str,
    expected_playoff_games_by_team: Dict[str, float],
    model_version: str = "nfl-player-v1",
) -> Dict[str, Any]:
    """The single entry point called from scripts/nfl/simulate_2026_season.py.
    Writes both CSVs directly into `out_dir` and returns a small summary dict
    suitable for embedding in that script's run_summary.json."""
    regular_rows, qb_lock_audit, skill_prior_audit = generate_player_regular_season_totals(
        session,
        season=season,
        model_version=model_version,
        apply_qb_lock=True,
        apply_skill_prior=True,
    )
    playoff_rows = generate_player_playoff_totals(
        session,
        season=season,
        expected_playoff_games_by_team=expected_playoff_games_by_team,
        model_version=model_version,
        regular_rows=regular_rows,
    )
    write_player_totals_csv(regular_rows, os.path.join(out_dir, "player_regular_season_totals.csv"))
    write_player_totals_csv(playoff_rows, os.path.join(out_dir, "player_playoff_totals.csv"))
    pass_quality = evaluate_season_pass_leader_quality(regular_rows)
    skill_quality = evaluate_season_skill_leader_quality(regular_rows)
    quality = {
        "pass": pass_quality,
        "skill": skill_quality,
        "qb_starter_lock": qb_lock_audit,
        "skill_prior_anchor": {
            "applied": skill_prior_audit.get("applied"),
            "method": skill_prior_audit.get("method"),
            "players_adjusted": skill_prior_audit.get("players_adjusted"),
            "anchors_loaded": skill_prior_audit.get("anchors_loaded"),
            "top_adjustments": skill_prior_audit.get("top_adjustments"),
        },
    }
    quality_path = os.path.join(out_dir, "player_season_pass_quality.json")
    with open(quality_path, "w") as fh:
        json.dump(quality, fh, indent=2, sort_keys=True)
    games_projected_values = sorted({r["games_projected"] for r in regular_rows})
    publish_ready = bool(pass_quality.get("publish_ready")) and bool(skill_quality.get("publish_ready_skill"))
    return {
        "status": "ok",
        "season": season,
        "model_version": model_version,
        "regular_season_player_rows": len(regular_rows),
        "playoff_player_rows": len(playoff_rows),
        "distinct_games_projected_values": games_projected_values,
        "pass_leader_quality": pass_quality,
        "skill_leader_quality": skill_quality,
        "qb_starter_lock": {
            "applied": qb_lock_audit.get("applied"),
            "teams_locked": qb_lock_audit.get("teams_locked"),
            "method": qb_lock_audit.get("method"),
        },
        "skill_prior_anchor": {
            "applied": skill_prior_audit.get("applied"),
            "method": skill_prior_audit.get("method"),
            "players_adjusted": skill_prior_audit.get("players_adjusted"),
            "anchors_loaded": skill_prior_audit.get("anchors_loaded"),
        },
        "publish_ready": publish_ready,
    }
