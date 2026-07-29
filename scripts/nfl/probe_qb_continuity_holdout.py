#!/usr/bin/env python3
"""Leakage-safe QB continuity feature probe vs active schema v3.

Builds week-lagged primary-passer change flags from nfl_dp_player_game_stats
(attempts) — known before kickoff of week W because they use weeks ≤ W−1.

Compares chronological holdout of v3 FEATURE_KEYS vs v3+QB experimental keys.
Does NOT import src.tasks (slow Celery module). Does NOT write an active fit.

Writes:
  data/ops/nfl-qb-continuity-holdout-probe.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge"
)

import numpy as np  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from src.services import nfl_supervised_retrain as supervised_mod  # noqa: E402
from src.services.nfl_injury_nowcast import compute_team_week_injury_severity  # noqa: E402
from src.services.nfl_supervised_retrain import (  # noqa: E402
    FEATURE_KEYS,
    fit_nfl_supervised_models,
)

OUT = ROOT / "data" / "ops" / "nfl-qb-continuity-holdout-probe.json"

QB_KEYS = (
    "home_qb_changed_entering",
    "away_qb_changed_entering",
    "diff_qb_changed_entering",
    "home_qb_starts_streak",
    "away_qb_starts_streak",
    "diff_qb_starts_streak",
)

NFL_TEAM_DIVISION: Dict[str, str] = {
    "BUF": "AFC_EAST", "MIA": "AFC_EAST", "NE": "AFC_EAST", "NYJ": "AFC_EAST",
    "BAL": "AFC_NORTH", "CIN": "AFC_NORTH", "CLE": "AFC_NORTH", "PIT": "AFC_NORTH",
    "HOU": "AFC_SOUTH", "IND": "AFC_SOUTH", "JAX": "AFC_SOUTH", "TEN": "AFC_SOUTH",
    "DEN": "AFC_WEST", "KC": "AFC_WEST", "LV": "AFC_WEST", "LAC": "AFC_WEST",
    "DAL": "NFC_EAST", "NYG": "NFC_EAST", "PHI": "NFC_EAST", "WAS": "NFC_EAST",
    "CHI": "NFC_NORTH", "DET": "NFC_NORTH", "GB": "NFC_NORTH", "MIN": "NFC_NORTH",
    "ATL": "NFC_SOUTH", "CAR": "NFC_SOUTH", "NO": "NFC_SOUTH", "TB": "NFC_SOUTH",
    "ARI": "NFC_WEST", "LA": "NFC_WEST", "SEA": "NFC_WEST", "SF": "NFC_WEST",
}


def _stub_perm(estimator, X, y, **kwargs):
    class _Stub:
        importances_mean = np.zeros(int(getattr(X, "shape", [0, 0])[1] or 0), dtype=float)

    return _Stub()


supervised_mod.permutation_importance = _stub_perm  # type: ignore[attr-defined]


def _db_url() -> str:
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def _primary_passer_by_team_week(conn) -> Dict[Tuple[int, int, str], str]:
    rows = conn.execute(
        text(
            """
            SELECT season, week,
                   COALESCE(team, metrics->>'team') AS team,
                   player_id,
                   COALESCE((metrics->>'attempts')::int, 0) AS attempts
            FROM nfl_dp_player_game_stats
            WHERE season BETWEEN 2018 AND 2025
              AND COALESCE((metrics->>'attempts')::int, 0) > 0
            """
        )
    ).mappings()
    best: Dict[Tuple[int, int, str], Tuple[int, str]] = {}
    for r in rows:
        team = str(r["team"] or "").upper()
        if not team or not r["player_id"]:
            continue
        key = (int(r["season"]), int(r["week"]), team)
        att = int(r["attempts"] or 0)
        cur = best.get(key)
        if cur is None or att > cur[0]:
            best[key] = (att, str(r["player_id"]))
    return {k: v[1] for k, v in best.items()}


def _entering_features(
    passer: Dict[Tuple[int, int, str], str],
    season: int,
    week: int,
    team: str,
) -> Tuple[Optional[float], Optional[float]]:
    team = team.upper()
    prior_weeks = sorted(w for (s, w, t) in passer if s == season and t == team and w < week)
    if len(prior_weeks) < 1:
        return None, None
    last_w = prior_weeks[-1]
    last_qb = passer[(season, last_w, team)]
    streak = 1.0
    for w in reversed(prior_weeks[:-1]):
        if passer[(season, w, team)] == last_qb:
            streak += 1.0
            if streak >= 8:
                break
        else:
            break
    if len(prior_weeks) < 2:
        return 0.0, streak
    prev_qb = passer[(season, prior_weeks[-2], team)]
    changed = 1.0 if last_qb != prev_qb else 0.0
    return changed, streak


def _fetch_injury_severity(conn, start_season: int, end_season: int) -> Dict[Tuple[int, int, str], Dict[str, float]]:
    rows = conn.execute(
        text(
            """
            SELECT i.season, i.week, i.team, i.report_status, i.practice_status, i.injury, r.position
            FROM nfl_dp_injuries i
            LEFT JOIN nfl_dp_rosters r
              ON r.season = i.season AND r.team = i.team AND r.player_id = i.player_id
            WHERE i.season BETWEEN :start_season AND :end_season
            """
        ),
        {"start_season": start_season, "end_season": end_season},
    ).mappings()
    grouped: Dict[Tuple[int, int, str], List[Dict[str, Any]]] = {}
    for row in rows:
        key = (int(row["season"]), int(row["week"]), str(row["team"]))
        grouped.setdefault(key, []).append(dict(row))
    return {k: compute_team_week_injury_severity(v) for k, v in grouped.items()}


def _fetch_training_rows(conn, start_season: int, end_season: int) -> List[Dict[str, Any]]:
    rows = list(
        conn.execute(
            text(
                """
                WITH team_games AS (
                  SELECT DISTINCT season, home_team AS team, game_date FROM nfl_dp_schedules
                  WHERE season BETWEEN :start_season AND :end_season
                  UNION
                  SELECT DISTINCT season, away_team AS team, game_date FROM nfl_dp_schedules
                  WHERE season BETWEEN :start_season AND :end_season
                ),
                rest AS (
                  SELECT season, team, game_date,
                    (game_date - LAG(game_date) OVER (PARTITION BY season, team ORDER BY game_date)) AS rest_days
                  FROM team_games
                )
                SELECT
                  mf.season, mf.week, mf.game_id,
                  mf.home_off_epa_5g, mf.away_off_epa_5g,
                  mf.home_def_epa_allowed_5g, mf.away_def_epa_allowed_5g,
                  mf.home_pressure_allowed_5g, mf.away_pressure_allowed_5g,
                  mf.home_pressure_generated_5g, mf.away_pressure_generated_5g,
                  mf.home_pass_rate_5g, mf.away_pass_rate_5g,
                  mf.home_early_down_pass_rate_5g, mf.away_early_down_pass_rate_5g,
                  mf.home_red_zone_td_rate_5g, mf.away_red_zone_td_rate_5g,
                  mf.home_success_offense_5g, mf.away_success_offense_5g,
                  mf.home_success_defense_allowed_5g, mf.away_success_defense_allowed_5g,
                  mf.diff_off_epa_5g, mf.diff_def_epa_allowed_5g,
                  mf.diff_pressure_generated_5g, mf.diff_pressure_allowed_5g,
                  mf.diff_red_zone_td_rate_5g,
                  (
                    (COALESCE(mf.home_success_offense_5g, 0.0) - COALESCE(mf.away_success_offense_5g, 0.0))
                    + (COALESCE(mf.away_success_defense_allowed_5g, 0.0) - COALESCE(mf.home_success_defense_allowed_5g, 0.0))
                  ) / 2.0 AS diff_success_rate_5g,
                  mf.home_kav_offense_5g, mf.away_kav_offense_5g,
                  mf.home_kav_defense_5g, mf.away_kav_defense_5g,
                  mf.home_kav_net_5g, mf.away_kav_net_5g,
                  CASE WHEN mf.home_kav_net_5g IS NULL OR mf.away_kav_net_5g IS NULL THEN NULL
                       ELSE mf.home_kav_net_5g - mf.away_kav_net_5g END AS diff_kav_net_5g,
                  sch.home_team, sch.away_team, sch.roof, sch.surface,
                  home_rest.rest_days AS home_rest_days,
                  away_rest.rest_days AS away_rest_days,
                  sch.home_score, sch.away_score,
                  (sch.home_score > sch.away_score) AS home_team_won,
                  (sch.home_score + sch.away_score) AS final_total_points
                FROM nfl_dp_matchup_features_weekly mf
                JOIN nfl_dp_schedules sch
                  ON sch.season = mf.season AND sch.game_id = mf.game_id
                LEFT JOIN rest home_rest
                  ON home_rest.season = sch.season AND home_rest.team = sch.home_team
                 AND home_rest.game_date = sch.game_date
                LEFT JOIN rest away_rest
                  ON away_rest.season = sch.season AND away_rest.team = sch.away_team
                 AND away_rest.game_date = sch.game_date
                WHERE mf.season BETWEEN :start_season AND :end_season
                  AND sch.home_score IS NOT NULL AND sch.away_score IS NOT NULL
                ORDER BY mf.season, mf.week, mf.game_id
                """
            ),
            {"start_season": start_season, "end_season": end_season},
        ).mappings()
    )
    injury = _fetch_injury_severity(conn, start_season, end_season)
    out: List[Dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        season = int(r["season"])
        week = int(r["week"])
        home_team = str(r["home_team"])
        away_team = str(r["away_team"])
        home_inj = injury.get((season, week, home_team), {})
        away_inj = injury.get((season, week, away_team), {})
        roof = str(r.get("roof") or "").lower()
        surface = str(r.get("surface") or "").lower()
        r["home_injury_impact"] = home_inj.get("impact_score", 0.0)
        r["away_injury_impact"] = away_inj.get("impact_score", 0.0)
        r["diff_injury_impact"] = r["home_injury_impact"] - r["away_injury_impact"]
        r["home_rest_days"] = float(r["home_rest_days"]) if r.get("home_rest_days") is not None else 7.0
        r["away_rest_days"] = float(r["away_rest_days"]) if r.get("away_rest_days") is not None else 7.0
        r["diff_rest_days"] = r["home_rest_days"] - r["away_rest_days"]
        r["roof_dome"] = 1.0 if roof in {"dome", "closed"} else 0.0
        r["surface_turf"] = 1.0 if "turf" in surface else 0.0
        home_div = NFL_TEAM_DIVISION.get(home_team)
        away_div = NFL_TEAM_DIVISION.get(away_team)
        r["is_divisional_game"] = 1.0 if (home_div and home_div == away_div) else 0.0
        out.append(r)
    return out


def main() -> int:
    t0 = time.time()
    print("loading rows…", flush=True)
    engine = create_engine(_db_url())
    with engine.connect() as conn:
        passer = _primary_passer_by_team_week(conn)
        print(f"passer keys={len(passer)}", flush=True)
        rows = _fetch_training_rows(conn, 2013, 2025)
    print(f"training rows={len(rows)} elapsed={time.time()-t0:.1f}s", flush=True)

    covered = 0
    for row in rows:
        season = int(row["season"])
        week = int(row["week"])
        home = str(row["home_team"])
        away = str(row["away_team"])
        hc, hs = _entering_features(passer, season, week, home)
        ac, as_ = _entering_features(passer, season, week, away)
        row["home_qb_changed_entering"] = hc
        row["away_qb_changed_entering"] = ac
        row["diff_qb_changed_entering"] = None if hc is None or ac is None else hc - ac
        row["home_qb_starts_streak"] = hs
        row["away_qb_starts_streak"] = as_
        row["diff_qb_starts_streak"] = None if hs is None or as_ is None else hs - as_
        if hc is not None and ac is not None:
            covered += 1

    keys_v3 = tuple(FEATURE_KEYS)
    keys_v3b = keys_v3 + QB_KEYS
    print("fitting v3…", flush=True)
    fit_v3 = fit_nfl_supervised_models(rows, feature_keys=keys_v3)
    print("fitting v3+qb…", flush=True)
    fit_v3b = fit_nfl_supervised_models(rows, feature_keys=keys_v3b)
    m3 = fit_v3["metrics"]
    m3b = fit_v3b["metrics"]

    def _delta(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None:
            return None
        return float(b) - float(a)

    deltas = {
        "test_brier": _delta(m3.get("test_brier"), m3b.get("test_brier")),
        "test_margin_mae": _delta(m3.get("test_margin_mae"), m3b.get("test_margin_mae")),
        "test_total_mae": _delta(m3.get("test_total_mae"), m3b.get("test_total_mae")),
    }
    improves = (
        deltas["test_brier"] is not None
        and deltas["test_margin_mae"] is not None
        and deltas["test_brier"] < -1e-4
        and deltas["test_margin_mae"] < -0.01
    )
    regresses = (
        (deltas["test_brier"] is not None and deltas["test_brier"] > 1e-4)
        or (deltas["test_margin_mae"] is not None and deltas["test_margin_mae"] > 0.01)
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(time.time() - t0, 1),
        "leakage_rule": "QB features use only prior weeks' primary passer (max attempts); never same-week outcome stats",
        "coverage": {
            "training_rows": len(rows),
            "rows_with_both_qb_features": covered,
            "passer_keys": len(passer),
            "note": "player_game_stats attempts coverage ~2022–2025; earlier seasons mostly NaN (HGB-native)",
        },
        "feature_keys_experimental": list(QB_KEYS),
        "v3_metrics": m3,
        "v3_plus_qb_metrics": m3b,
        "deltas_v3b_minus_v3": deltas,
        "promote": bool(improves and not regresses),
        "decision": (
            "PROMOTE"
            if improves and not regresses
            else "REJECT — holdout does not clear improve bar (or regresses)"
        ),
        "active_fit_unchanged": True,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(
        json.dumps(
            {k: report[k] for k in ("decision", "deltas_v3b_minus_v3", "coverage", "elapsed_sec")},
            indent=2,
        ),
        flush=True,
    )
    print(f"wrote {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
