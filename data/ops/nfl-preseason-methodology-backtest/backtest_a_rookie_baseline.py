"""Backtest A: rookie usage draft-tier baseline, walk-forward, no leakage.

Read-only analysis script. Does NOT write to any production table. Replicates
the exact bucketing/averaging logic of
services/data-platform-nfl/src/data_platform_nfl/rookie_baselines.py
(compute_rookie_usage_baselines + get_rookie_baseline fallback), but with an
explicit through_season cutoff strictly BEFORE each target season, then scores
that walk-forward baseline against real observed rookie usage in the target
season.

Usage: DATABASE_URL=postgresql://user:pass@host:port/db python3 backtest_a_rookie_baseline.py
"""

from __future__ import annotations

import json
import os
import statistics
from collections import defaultdict

import psycopg

DATABASE_URL = os.environ.get(
    "DATABASE_URL_PLAIN",
    "postgresql://ryankos:postgres@127.0.0.1:5432/kosedge",
)

TARGET_SEASONS = [2019, 2020, 2021, 2022, 2023, 2024]
SKILL_OFFENSE_POSITIONS = {"QB", "RB", "WR", "TE", "FB", "HB"}
MIN_SAMPLE_PLAYERS = 3
RECENCY_DECAY = float(os.environ.get("RECENCY_DECAY", "1.0"))  # 1.0 = unweighted (original), <1.0 = recency-weighted

DRAFT_TIERS = [
    ("R1_top10", 1, 10),
    ("R1_11_32", 11, 32),
    ("R2_R3", 33, 96),
    ("R4_R5", 97, 172),
    ("R6_R7", 173, 300),
]
UNDRAFTED_TIER = "UDFA"


def draft_tier_for_pick(pick: int | None) -> str:
    if pick is None:
        return UNDRAFTED_TIER
    for tier, lo, hi in DRAFT_TIERS:
        if lo <= pick <= hi:
            return tier
    return UNDRAFTED_TIER


def build_baseline(conn, *, through_season: int) -> dict[tuple[str, str], dict]:
    """Exact replica of compute_rookie_usage_baselines(), scoped to through_season."""
    rows = conn.execute(
        """
        SELECT
          u.player_id,
          r.position,
          r.draft_number,
          u.season,
          COUNT(DISTINCT u.week) AS games_played,
          SUM(u.involvement_plays)::numeric AS involvement_plays,
          SUM(u.targets)::numeric AS targets,
          SUM(u.rush_attempts)::numeric AS rush_attempts,
          SUM(u.red_zone_targets)::numeric AS red_zone_targets,
          SUM(u.red_zone_carries)::numeric AS red_zone_carries
        FROM nfl_dp_rosters r
        JOIN nfl_dp_player_usage_weekly u
          ON u.player_id = r.player_id
          AND u.season = r.rookie_year
        WHERE r.rookie_year IS NOT NULL
          AND r.rookie_year = r.season
          AND r.rookie_year <= %(through_season)s
          AND u.games_played > 0
        GROUP BY u.player_id, r.position, r.draft_number, u.season
        HAVING COUNT(DISTINCT u.week) > 0
        """,
        {"through_season": through_season},
    ).fetchall()

    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for player_id, position, draft_number, season, games, invp, tgt, rush, rzt, rzc in rows:
        games = float(games or 0)
        if games <= 0:
            continue
        position = (position or "UNK").upper()
        tier = draft_tier_for_pick(draft_number)
        buckets[(position, tier)].append(
            {
                "player_id": player_id,
                "season": int(season),
                "involvement_plays": float(invp or 0) / games,
                "targets": float(tgt or 0) / games,
                "rush_attempts": float(rush or 0) / games,
                "red_zone_targets": float(rzt or 0) / games,
                "red_zone_carries": float(rzc or 0) / games,
            }
        )

    baseline: dict[tuple[str, str], dict] = {}
    for key, samples in buckets.items():
        n_players = len({s["player_id"] for s in samples})
        if n_players < MIN_SAMPLE_PLAYERS:
            continue
        n = len(samples)
        weights = [RECENCY_DECAY ** max(0, through_season - s["season"]) for s in samples]
        total_w = sum(weights)

        def wavg(field: str) -> float:
            return sum(s[field] * w for s, w in zip(samples, weights)) / total_w

        baseline[key] = {
            "sample_players": n_players,
            "sample_player_seasons": n,
            "involvement_plays": wavg("involvement_plays"),
            "targets": wavg("targets"),
            "rush_attempts": wavg("rush_attempts"),
            "red_zone_targets": wavg("red_zone_targets"),
            "red_zone_carries": wavg("red_zone_carries"),
        }
    return baseline


def get_baseline_for(baseline: dict[tuple[str, str], dict], *, position: str, tier: str) -> dict | None:
    position = position.upper()
    if position not in SKILL_OFFENSE_POSITIONS:
        return None
    row = baseline.get((position, tier))
    if row is not None:
        return row
    # replicate get_rookie_baseline's cross-position-same-tier fallback,
    # picking the candidate with the largest sample_players like the SQL
    # ORDER BY sample_players DESC LIMIT 1.
    candidates = [
        (key, val) for key, val in baseline.items() if key[1] == tier and key[0] in SKILL_OFFENSE_POSITIONS
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda kv: kv[1]["sample_players"], reverse=True)
    return candidates[0][1]


def get_real_rookies(conn, *, season: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
          u.player_id,
          r.position,
          r.draft_number,
          COUNT(DISTINCT u.week) AS games_played,
          SUM(u.involvement_plays)::numeric AS involvement_plays,
          SUM(u.targets)::numeric AS targets,
          SUM(u.rush_attempts)::numeric AS rush_attempts,
          SUM(u.red_zone_targets)::numeric AS red_zone_targets,
          SUM(u.red_zone_carries)::numeric AS red_zone_carries
        FROM nfl_dp_rosters r
        JOIN nfl_dp_player_usage_weekly u
          ON u.player_id = r.player_id
          AND u.season = r.rookie_year
          AND u.source = 'pbp_aggregation'
        WHERE r.rookie_year IS NOT NULL
          AND r.rookie_year = r.season
          AND r.rookie_year = %(season)s
          AND r.position = ANY(%(positions)s)
          AND r.draft_number IS NOT NULL
          AND u.games_played > 0
        GROUP BY u.player_id, r.position, r.draft_number
        HAVING COUNT(DISTINCT u.week) > 0
        """,
        {"season": season, "positions": list(SKILL_OFFENSE_POSITIONS)},
    ).fetchall()

    out = []
    for player_id, position, draft_number, games, invp, tgt, rush, rzt, rzc in rows:
        games = float(games or 0)
        if games <= 0:
            continue
        out.append(
            {
                "player_id": player_id,
                "position": (position or "UNK").upper(),
                "draft_number": draft_number,
                "tier": draft_tier_for_pick(draft_number),
                "games": games,
                "actual_involvement_plays": float(invp or 0) / games,
                "actual_targets": float(tgt or 0) / games,
                "actual_rush_attempts": float(rush or 0) / games,
                "actual_touches": (float(tgt or 0) + float(rush or 0)) / games,
                "actual_red_zone_targets": float(rzt or 0) / games,
                "actual_red_zone_carries": float(rzc or 0) / games,
            }
        )
    return out


def mae(errors: list[float]) -> float:
    return statistics.mean(abs(e) for e in errors) if errors else float("nan")


def bias(errors: list[float]) -> float:
    return statistics.mean(errors) if errors else float("nan")


def main() -> None:
    conn = psycopg.connect(DATABASE_URL, autocommit=True)

    records = []  # one row per (season, player)
    skipped_no_baseline = 0

    for season in TARGET_SEASONS:
        baseline = build_baseline(conn, through_season=season - 1)
        rookies = get_real_rookies(conn, season=season)
        for rk in rookies:
            b = get_baseline_for(baseline, position=rk["position"], tier=rk["tier"])
            if b is None:
                skipped_no_baseline += 1
                pred = {
                    "involvement_plays": 0.0,
                    "targets": 0.0,
                    "rush_attempts": 0.0,
                    "red_zone_targets": 0.0,
                    "red_zone_carries": 0.0,
                }
                had_baseline = False
            else:
                pred = b
                had_baseline = True
            pred_touches = pred["targets"] + pred["rush_attempts"]
            records.append(
                {
                    **rk,
                    "season": season,
                    "had_baseline": had_baseline,
                    "pred_involvement_plays": pred["involvement_plays"],
                    "pred_touches": pred_touches,
                }
            )

    print(f"Total scored rookie-seasons: {len(records)}")
    print(f"Rookie-seasons with NO baseline available at all (fell back to 0): {skipped_no_baseline}")
    print()

    def summarize(group_key_fn, label):
        groups = defaultdict(list)
        for r in records:
            groups[group_key_fn(r)].append(r)
        print(f"=== Breakdown by {label} (pooled across seasons {TARGET_SEASONS[0]}-{TARGET_SEASONS[-1]}) ===")
        header = (
            f"{'group':<14} {'n':>5} | "
            f"{'base_MAE_inv':>13} {'base_bias_inv':>14} | "
            f"{'zero_MAE_inv':>13} {'zero_bias_inv':>14} | "
            f"{'base_MAE_tch':>13} {'base_bias_tch':>14} | "
            f"{'zero_MAE_tch':>13} {'zero_bias_tch':>14} | "
            f"{'actual_avg_inv':>14} {'actual_avg_tch':>14}"
        )
        print(header)
        for key in sorted(groups.keys()):
            rows = groups[key]
            base_err_inv = [r["pred_involvement_plays"] - r["actual_involvement_plays"] for r in rows]
            zero_err_inv = [0.0 - r["actual_involvement_plays"] for r in rows]
            base_err_tch = [r["pred_touches"] - r["actual_touches"] for r in rows]
            zero_err_tch = [0.0 - r["actual_touches"] for r in rows]
            actual_avg_inv = statistics.mean(r["actual_involvement_plays"] for r in rows)
            actual_avg_tch = statistics.mean(r["actual_touches"] for r in rows)
            print(
                f"{str(key):<14} {len(rows):>5} | "
                f"{mae(base_err_inv):>13.2f} {bias(base_err_inv):>14.2f} | "
                f"{mae(zero_err_inv):>13.2f} {bias(zero_err_inv):>14.2f} | "
                f"{mae(base_err_tch):>13.2f} {bias(base_err_tch):>14.2f} | "
                f"{mae(zero_err_tch):>13.2f} {bias(zero_err_tch):>14.2f} | "
                f"{actual_avg_inv:>14.2f} {actual_avg_tch:>14.2f}"
            )
        print()

    summarize(lambda r: r["position"], "position")
    summarize(lambda r: r["tier"], "draft tier")
    summarize(lambda r: (r["position"], r["tier"]), "position x tier")
    summarize(lambda r: r["season"], "season")

    print("=== OVERALL POOLED ===")
    base_err_inv = [r["pred_involvement_plays"] - r["actual_involvement_plays"] for r in records]
    zero_err_inv = [0.0 - r["actual_involvement_plays"] for r in records]
    base_err_tch = [r["pred_touches"] - r["actual_touches"] for r in records]
    zero_err_tch = [0.0 - r["actual_touches"] for r in records]
    print(f"n = {len(records)}")
    print(f"involvement_plays: baseline MAE={mae(base_err_inv):.3f} bias={bias(base_err_inv):.3f} | zero MAE={mae(zero_err_inv):.3f} bias={bias(zero_err_inv):.3f}")
    print(f"touches (targets+rush): baseline MAE={mae(base_err_tch):.3f} bias={bias(base_err_tch):.3f} | zero MAE={mae(zero_err_tch):.3f} bias={bias(zero_err_tch):.3f}")

    # Signed % bias by position, for touches (pred vs actual), useful for
    # "systematically over/under-projects position X by Y%" style findings.
    print()
    print("=== Signed relative bias by position (touches): mean(pred-actual)/mean(actual) ===")
    pos_groups = defaultdict(list)
    for r in records:
        pos_groups[r["position"]].append(r)
    for pos in sorted(pos_groups.keys()):
        rows = pos_groups[pos]
        mean_actual = statistics.mean(r["actual_touches"] for r in rows)
        mean_pred = statistics.mean(r["pred_touches"] for r in rows)
        rel = (mean_pred - mean_actual) / mean_actual * 100 if mean_actual else float("nan")
        print(f"{pos:<5} n={len(rows):>4}  mean_actual_touches={mean_actual:6.2f}  mean_pred_touches={mean_pred:6.2f}  rel_bias={rel:+.1f}%")

    with open(
        "/Users/ryankos/kosedge/data/ops/nfl-preseason-methodology-backtest/backtest_a_records.json",
        "w",
    ) as f:
        json.dump(records, f, indent=2, default=str)


if __name__ == "__main__":
    main()
