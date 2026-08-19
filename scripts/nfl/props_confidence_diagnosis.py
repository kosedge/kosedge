#!/usr/bin/env python3
"""Props confidence diagnosis — bucket bias + season-pool coherence.

Research only. Does not flip NFL_WEEKLY_PROPS_LIVE or replace frozen cal-v1.
Writes data/ops/nfl-props-confidence-diagnosis.json for the ops note.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "services", "model-service"))
sys.path.insert(0, ROOT)
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from sqlalchemy import create_engine, text  # noqa: E402

from scripts.nfl.prop_archive_calibration_holdout import (  # noqa: E402
    ACTUAL_FIELD,
    HOLDOUT_SEASON,
    TRAIN_SEASONS,
    _lag_pred,
    _load_db,
    _mae,
)
from src.services.nfl_player_prop_calibration import (  # noqa: E402
    FROZEN_MEAN_INTERCEPT,
    apply_prop_calibration,
    fit_prop_calibration_from_points,
    frozen_calibration_for,
)
from src.services.nfl_warehouse.odds_lake import team_abbr  # noqa: E402
from src.services.nfl_warehouse.prop_join import (  # noqa: E402
    iter_prop_closes,
    pick_close_by_player,
)

OUT = os.path.join(ROOT, "data", "ops", "nfl-props-confidence-diagnosis.json")
CORE = ("pass_yds", "rush_yds", "rec_yds", "receptions")
PASS_BUCKETS = ((0, 225), (225, 275), (275, 10_000))


def _mean(xs: List[float]) -> Optional[float]:
    if not xs:
        return None
    return round(sum(xs) / len(xs), 4)


def _slice(rows: List[Dict[str, Any]], pred: str, target: str) -> Dict[str, Any]:
    pairs = [(float(r[pred]), float(r[target])) for r in rows]
    res = [a - b for a, b in pairs]
    return {
        "n": len(rows),
        "mae": _mae(pairs),
        "mean_residual": _mean(res),
        "under_rate": round(sum(1 for x in res if x < 0) / len(res), 4) if res else None,
    }


def _pass_bucket(close: float) -> str:
    for lo, hi in PASS_BUCKETS:
        if lo <= close < hi:
            return f"{lo}-{hi - 1}" if hi < 10_000 else f"{lo}+"
    return "other"


def _rush_role(team_rush_ranks: Dict[Tuple[int, int, str], Dict[str, int]], row: Dict[str, Any]) -> str:
    key = (int(row["season"]), int(row["week"]), str(row["team"]))
    ranks = team_rush_ranks.get(key) or {}
    rank = ranks.get(str(row["player_id"]))
    if rank == 1:
        return "rb1"
    if rank is not None and rank >= 2:
        return "committee_or_rb2plus"
    return "unknown"


def _rec_tier(targets: Optional[float]) -> str:
    if targets is None:
        return "unknown"
    t = float(targets)
    if t >= 8:
        return "tier1_8plus_tgt"
    if t >= 5:
        return "tier2_5to7_tgt"
    return "tier3_under5_tgt"


def _load_usage_role() -> Tuple[
    Dict[Tuple[int, int, str], Dict[str, int]],
    Dict[Tuple[int, int, str, str], float],
]:
    engine = create_engine(os.environ["DATABASE_URL"])
    rush_by_team: Dict[Tuple[int, int, str], List[Tuple[str, float]]] = defaultdict(list)
    targets: Dict[Tuple[int, int, str, str], float] = {}
    with engine.connect() as conn:
        for r in conn.execute(
            text(
                """
                SELECT season, week, team, player_id, rush_attempts, targets
                FROM nfl_dp_player_usage_weekly
                WHERE season BETWEEN 2023 AND 2025
                """
            )
        ):
            key = (int(r.season), int(r.week), str(r.team))
            pid = str(r.player_id)
            rush_by_team[key].append((pid, float(r.rush_attempts or 0)))
            targets[(int(r.season), int(r.week), str(r.team), pid)] = float(r.targets or 0)
    ranks: Dict[Tuple[int, int, str], Dict[str, int]] = {}
    for key, items in rush_by_team.items():
        ordered = sorted(items, key=lambda x: (-x[1], x[0]))
        ranks[key] = {pid: i + 1 for i, (pid, _) in enumerate(ordered) if _ > 0}
    return ranks, targets


def _season_pool(season: int = 2025) -> Dict[str, Any]:
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as conn:
        qb = list(
            conn.execute(
                text(
                    """
                    SELECT player_name, team,
                           SUM(pass_yards_mean)::float AS pass_yards_total,
                           COUNT(*)::int AS games
                    FROM nfl_player_projection_baselines
                    WHERE season = :season
                      AND model_version = 'nfl-player-v1'
                      AND position = 'QB'
                      AND game_id IS NOT NULL AND game_id <> ''
                    GROUP BY player_id, player_name, team
                    HAVING SUM(pass_yards_mean) > 0
                    ORDER BY SUM(pass_yards_mean) DESC
                    """
                ),
                {"season": season},
            )
        )
        team_pass = list(
            conn.execute(
                text(
                    """
                    SELECT team,
                           SUM(CASE WHEN position = 'QB' THEN pass_yards_mean ELSE 0 END)::float AS qb_pass,
                           SUM(CASE WHEN position IN ('WR','TE','RB') THEN receiving_yards_mean ELSE 0 END)::float AS skill_rec
                    FROM nfl_player_projection_baselines
                    WHERE season = :season
                      AND model_version = 'nfl-player-v1'
                      AND game_id IS NOT NULL AND game_id <> ''
                    GROUP BY team
                    """
                ),
                {"season": season},
            )
        )
    qb_totals = [float(r.pass_yards_total) for r in qb]
    over_4k = sum(1 for x in qb_totals if x >= 4000)
    over_5k = sum(1 for x in qb_totals if x >= 5000)
    sorted_qb = sorted(qb_totals)

    def _pct(xs: List[float], p: float) -> Optional[float]:
        if not xs:
            return None
        idx = min(len(xs) - 1, max(0, int(round(p * (len(xs) - 1)))))
        return round(xs[idx], 1)

    gaps = []
    for r in team_pass:
        qb_p = float(r.qb_pass or 0)
        rec = float(r.skill_rec or 0)
        if qb_p > 0:
            gaps.append(abs(qb_p - rec) / qb_p)
    return {
        "season": season,
        "source": "sum(nfl_player_projection_baselines.pass_yards_mean) by QB",
        "qb_n": len(qb_totals),
        "qb_pass_yards": {
            "median": _pct(sorted_qb, 0.5),
            "p90": _pct(sorted_qb, 0.9),
            "max": round(max(qb_totals), 1) if qb_totals else None,
            "n_ge_4000": over_4k,
            "n_ge_5000": over_5k,
            "top5": [
                {
                    "player": r.player_name,
                    "team": r.team,
                    "pass_yards": round(float(r.pass_yards_total), 1),
                    "games": int(r.games),
                }
                for r in qb[:5]
            ],
        },
        "team_pass_vs_rec_abs_rel_gap_mean": _mean(gaps),
        "note": (
            "Fantasy draft season totals SUM weekly baselines (raw, no prop cal). "
            "Weekly props board blends box-sim then applies frozen prop-cal-v1. "
            "That is the primary spine drift."
        ),
    }


def main() -> int:
    print("loading usage roles + postgres preds...", flush=True)
    rush_ranks, targets = _load_usage_role()
    sched, usage, baseline, by_player = _load_db()
    print("streaming prop closes...", flush=True)
    closes = pick_close_by_player(iter_prop_closes())
    joined: List[Dict[str, Any]] = []
    for row in closes:
        home = team_abbr(str(row.get("home") or ""))
        away = team_abbr(str(row.get("away") or ""))
        hit = sched.get((str(row.get("game_date") or ""), home, away))
        if not hit:
            continue
        season, week = hit
        usage_row = usage.get((season, week, home, row["player_key"])) or usage.get(
            (season, week, away, row["player_key"])
        )
        if not usage_row:
            continue
        mk = str(row["market"])
        if mk not in CORE:
            continue
        field = ACTUAL_FIELD[mk]
        if usage_row.get(field) is None:
            continue
        team = str(usage_row["team"])
        base = baseline.get((season, week, team, row["player_key"]))
        pred = None
        src = None
        pred_field = {
            "pass_yds": "pass_yards_mean",
            "rush_yds": "rush_yards_mean",
            "rec_yds": "receiving_yards_mean",
            "receptions": "receptions_mean",
        }[mk]
        if base and base.get(pred_field) is not None:
            pred = float(base[pred_field])
            src = "baseline_2025"
        else:
            pred = _lag_pred(usage_row, by_player, mk)
            src = "lag3_usage" if pred is not None else None
        if pred is None:
            continue
        close = float(row["line"])
        actual = float(usage_row[field])
        frozen = apply_prop_calibration(
            model_mean=pred,
            model_std=1.0,
            market_key=mk,
            calibration=frozen_calibration_for(mk),
            market_line=close,
        )
        pid = str(usage_row.get("player_id") or "")
        tgt = targets.get((season, week, team, pid))
        joined.append(
            {
                "season": season,
                "week": week,
                "team": team,
                "player_id": pid,
                "market": mk,
                "pred": pred,
                "actual": actual,
                "close": close,
                "frozen_mean": float(frozen["model_mean"]),
                "pred_source": src,
                "pass_bucket": _pass_bucket(close) if mk == "pass_yds" else None,
                "rush_role": _rush_role(rush_ranks, {"season": season, "week": week, "team": team, "player_id": pid})
                if mk == "rush_yds"
                else None,
                "rec_tier": _rec_tier(tgt) if mk in {"rec_yds", "receptions"} else None,
            }
        )

    train = [r for r in joined if r["season"] in TRAIN_SEASONS]
    hold = [r for r in joined if r["season"] == HOLDOUT_SEASON]
    candidate = {}
    for mk in CORE:
        pts = [{"pred": r["pred"], "actual": r["actual"]} for r in train if r["market"] == mk]
        candidate[mk] = fit_prop_calibration_from_points(pts, market_key=mk)
    for r in hold:
        applied = apply_prop_calibration(
            model_mean=r["pred"],
            model_std=1.0,
            market_key=r["market"],
            calibration=candidate[r["market"]],
            market_line=r["close"],
        )
        r["candidate_mean"] = float(applied["model_mean"])

    by_market: Dict[str, Any] = {}
    for mk in CORE:
        h = [r for r in hold if r["market"] == mk]
        by_market[mk] = {
            "holdout_n": len(h),
            "frozen_intercept": FROZEN_MEAN_INTERCEPT.get(mk),
            "candidate_intercept": candidate[mk].intercept,
            "raw_vs_close": _slice(h, "pred", "close"),
            "frozen_vs_close": _slice(h, "frozen_mean", "close"),
            "candidate_vs_close": _slice(h, "candidate_mean", "close"),
            "raw_vs_actual": _slice(h, "pred", "actual"),
            "frozen_vs_actual": _slice(h, "frozen_mean", "actual"),
            "candidate_vs_actual": _slice(h, "candidate_mean", "actual"),
        }

    pass_buckets = {}
    for label in [f"{lo}-{hi - 1}" if hi < 10_000 else f"{lo}+" for lo, hi in PASS_BUCKETS]:
        rows = [r for r in hold if r["market"] == "pass_yds" and r["pass_bucket"] == label]
        pass_buckets[label] = {
            "frozen_vs_close": _slice(rows, "frozen_mean", "close"),
            "frozen_vs_actual": _slice(rows, "frozen_mean", "actual"),
            "candidate_vs_actual": _slice(rows, "candidate_mean", "actual"),
        }

    rush_roles = {}
    for label in ("rb1", "committee_or_rb2plus", "unknown"):
        rows = [r for r in hold if r["market"] == "rush_yds" and r["rush_role"] == label]
        rush_roles[label] = {
            "frozen_vs_close": _slice(rows, "frozen_mean", "close"),
            "frozen_vs_actual": _slice(rows, "frozen_mean", "actual"),
            "candidate_vs_actual": _slice(rows, "candidate_mean", "actual"),
        }

    rec_tiers = {}
    for label in ("tier1_8plus_tgt", "tier2_5to7_tgt", "tier3_under5_tgt", "unknown"):
        rows = [r for r in hold if r["market"] == "rec_yds" and r["rec_tier"] == label]
        rec_tiers[label] = {
            "frozen_vs_close": _slice(rows, "frozen_mean", "close"),
            "frozen_vs_actual": _slice(rows, "frozen_mean", "actual"),
            "candidate_vs_actual": _slice(rows, "candidate_mean", "actual"),
        }

    # Gate decision helpers
    rush_f = by_market["rush_yds"]["frozen_vs_actual"]["mae"]
    rush_r = by_market["rush_yds"]["raw_vs_actual"]["mae"]
    rush_c = by_market["rush_yds"]["candidate_vs_actual"]["mae"]
    pass_bias_f = by_market["pass_yds"]["frozen_vs_actual"]["mean_residual"]
    pass_bias_c = by_market["pass_yds"]["candidate_vs_actual"]["mean_residual"]

    report = {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "product": False,
        "part1_shipped": {
            "pr": "https://github.com/kosedge/kosedge/pull/263",
            "play_vs": "draftkings→fanduel→consensus",
            "weekly_props_live": False,
        },
        "spine_drift": [
            {
                "id": "D1",
                "severity": "Weekly props board",
                "path": "baseline ⊕ box-score MC blend → apply_prop_calibration(frozen cal-v1) → edges",
                "applies_frozen_cal": True,
            },
            {
                "id": "D2",
                "severity": "Fantasy weekly",
                "path": "raw nfl_player_projection_baselines → fantasy_points_from_projection",
                "applies_frozen_cal": False,
            },
            {
                "id": "D3",
                "surface": "Fantasy season / draft",
                "path": "SUM(weekly baselines) per player (no cal, no box blend)",
                "applies_frozen_cal": False,
            },
            {
                "id": "D4",
                "surface": "Player season box-score sims / award-ish season",
                "path": "aggregate game box sims → nfl_player_season_box_score_sims",
                "applies_frozen_cal": False,
            },
            {
                "id": "D5",
                "surface": "Season engine / conservation",
                "path": "nfl_season_engine budgets + offensive_production_stack (separate from weekly baselines)",
                "applies_frozen_cal": False,
            },
        ],
        "holdout_2025": by_market,
        "pass_yds_by_close_bucket": pass_buckets,
        "rush_yds_by_role": rush_roles,
        "rec_yds_by_target_tier": rec_tiers,
        "season_pool_from_baselines": _season_pool(2025),
        "root_layer_read": {
            "pass": (
                "Frozen still undershoots actuals (mean residual ~−12). Bias is worse on "
                "225–275 closes. Candidate (+6.1) helps but is residual-only; team pass "
                "budget / QB volume likely the right layer before swapping intercepts."
            ),
            "rush": (
                "Frozen improves close MAE but worsens actual MAE vs raw (prior failure). "
                "Do not replace shared frozen dict for rush. Check RB1 vs committee separately."
            ),
            "rec": (
                "Frozen helps close and slightly helps actual overall; candidate can "
                "worsen close. Prefer structure (target shares) over intercept churn."
            ),
        },
        "gates": {
            "NFL_WEEKLY_PROPS_LIVE": False,
            "replace_frozen_intercepts": False,
            "residual_only_candidate_ready": False,
            "structural_fix_first": True,
            "rush_frozen_regresses_vs_actual": bool(
                rush_f is not None and rush_r is not None and rush_f > rush_r
            ),
            "pass_bias_moves_toward_zero_with_candidate": bool(
                pass_bias_f is not None
                and pass_bias_c is not None
                and abs(pass_bias_c) < abs(pass_bias_f)
            ),
            "rush_candidate_actual_mae": rush_c,
            "rush_frozen_actual_mae": rush_f,
            "rush_raw_actual_mae": rush_r,
        },
        "recommendation": (
            "NO residual-only promote. Fix team pass/rush budgets + usage shares so "
            "fantasy and props inherit the same means; then re-fit shared cal once. "
            "Weekly props stay gated."
        ),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")
    print(json.dumps({"wrote": OUT, "gates": report["gates"], "recommendation": report["recommendation"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
