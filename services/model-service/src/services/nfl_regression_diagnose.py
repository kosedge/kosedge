"""NFL projected-points regression diagnostics (investigation only).

Does not rematerialize, does not change scoring coefficients, and does not
publish. Used to compare the live July-31 fair stamps against:

- packaged 2025 EPA priors (what ``run_nfl_market_simulations`` prefers)
- ESPN W-L record buckets written into ``nfl_game_context`` by
  ``pull_nfl_context_snapshot`` (what ``POST /nfl/simulations/{id}`` still
  multiplies in)

See ``data/ops/nfl-regression-investigate-20260915.md``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from src.services.nfl_data import team_strength_from_record
from src.services.nfl_handicapping_framework import (
    NFL_HANDICAPPING_FRAMEWORK_VERSION,
    compute_nfl_projection_decomposition,
    get_nfl_handicapping_config,
)

PACKAGED_EPA_PRIORS_2026 = (
    Path(__file__).resolve().parent
    / "nfl_season_engine"
    / "data"
    / "nfl_team_epa_priors_2026.json"
)

# Live Railway fair-lines (model-service GET /nfl/fair-lines) captured
# 2026-09-15T18:01:54Z. All projection_created_at = 2026-07-31.
# SHA256 of full payloads: see data/ops/nfl-regression-live-stamps-20260915.json
FOCUS_MATCHUPS: Tuple[Dict[str, Any], ...] = (
    {
        "key": "DET@BUF",
        "week": 2,
        "away": "DET",
        "home": "BUF",
        "home_record_after_w1": "1-0",
        "away_record_after_w1": "1-0",
        "live_model_spread_home": -3.83,
        "live_kei_spread_home": -3.42,
        "live_model_total": 44.46,
        "live_kei_total": 49.14,
        "live_market_spread_home": -4.5,
        "live_market_total": 53.5,
        "projection_created_at": "2026-07-31T06:05:43.780295Z",
    },
    {
        "key": "CAR@ATL",
        "week": 2,
        "away": "CAR",
        "home": "ATL",
        "home_record_after_w1": "0-1",
        "away_record_after_w1": "0-1",
        "live_model_spread_home": -2.77,
        "live_kei_spread_home": -2.14,
        "live_model_total": 43.7,
        "live_kei_total": 44.2,
        "live_market_spread_home": 2.5,
        "live_market_total": 43.5,
        "projection_created_at": "2026-07-31T06:05:49.683218Z",
    },
    {
        "key": "ATL@PIT",
        "week": 1,
        "away": "ATL",
        "home": "PIT",
        "home_record_after_w1": "1-0",
        "away_record_after_w1": "0-1",
        "live_model_spread_home": -2.75,
        "live_kei_spread_home": -2.79,
        "live_model_total": 43.49,
        "live_kei_total": 43.15,
        "actual_away": 13,
        "actual_home": 20,
        "projection_created_at": "2026-07-31T06:05:32.986988Z",
    },
    {
        "key": "CHI@CAR",
        "week": 1,
        "away": "CHI",
        "home": "CAR",
        "home_record_after_w1": "0-1",
        "away_record_after_w1": "1-0",
        "live_model_spread_home": 0.72,
        "live_kei_spread_home": 2.05,
        "live_model_total": 44.29,
        "live_kei_total": 45.53,
        "actual_away": 59,
        "actual_home": 37,
        "projection_created_at": "2026-07-31T06:05:32.806190Z",
    },
)

# Scoring-equation lock (do not "fix" residuals by editing these).
LOCKED_SCORING = {
    "framework_version": NFL_HANDICAPPING_FRAMEWORK_VERSION,
    "base_total_points": 45.3,
    "home_field_points": 1.05,
    "base_efficiency_max_total_points": 5.0,
    "base_efficiency_max_margin_points": 6.5,
    "base_efficiency_total_weight": 10.5,
    "base_efficiency_margin_weight": 16.0,
}


def load_packaged_epa_priors(path: Optional[Path] = None) -> Dict[str, Dict[str, float]]:
    payload = json.loads((path or PACKAGED_EPA_PRIORS_2026).read_text(encoding="utf-8"))
    teams = payload.get("teams") if isinstance(payload, dict) else {}
    out: Dict[str, Dict[str, float]] = {}
    if not isinstance(teams, dict):
        return out
    for raw_team, row in teams.items():
        if not isinstance(row, dict):
            continue
        team = str(raw_team).strip().upper()
        if team == "LA":
            team = "LAR"
        off = row.get("offense_index")
        deff = row.get("defense_index")
        if off is None or deff is None:
            continue
        out[team] = {
            "offense_index": float(off),
            "defense_index": float(deff),
            "as_of": str(payload.get("as_of") or ""),
            "source": str(payload.get("source") or "packaged_epa_prior"),
        }
    if "LAR" in out and "LA" not in out:
        out["LA"] = dict(out["LAR"])
    return out


def record_indices(record_summary: str) -> Tuple[float, float]:
    return team_strength_from_record(record_summary)


def looks_like_week1_record_bucket(
    *,
    offense_index: float,
    defense_index: float,
    record_summary: str,
    atol: float = 0.015,
) -> bool:
    """True when context indices match ``team_strength_from_record`` for that record."""
    exp_off, exp_def = record_indices(record_summary)
    return abs(float(offense_index) - exp_off) <= atol and abs(float(defense_index) - exp_def) <= atol


def classify_strength_source(
    *,
    offense_index: float,
    defense_index: float,
    record_summary: Optional[str],
    epa: Optional[Mapping[str, float]] = None,
    atol: float = 0.015,
) -> str:
    if record_summary and looks_like_week1_record_bucket(
        offense_index=offense_index,
        defense_index=defense_index,
        record_summary=record_summary,
        atol=atol,
    ):
        return "espn_win_loss_record"
    if epa is not None:
        epa_off = float(epa.get("offense_index") or 0.0)
        epa_def = float(epa.get("defense_index") or 0.0)
        if abs(offense_index - epa_off) <= atol and abs(defense_index - epa_def) <= atol:
            return "packaged_epa_prior"
    return "other_or_blended"


def decompose_matchup(
    *,
    home: str,
    away: str,
    offense_index_home: float,
    offense_index_away: float,
    defense_index_home: float,
    defense_index_away: float,
    rest_days_home: float = 7.0,
    rest_days_away: float = 7.0,
    strength_source: str,
) -> Dict[str, Any]:
    decomp = compute_nfl_projection_decomposition(
        offense_index_home=float(offense_index_home),
        offense_index_away=float(offense_index_away),
        defense_index_home=float(defense_index_home),
        defense_index_away=float(defense_index_away),
        rest_days_home=float(rest_days_home),
        rest_days_away=float(rest_days_away),
        matchup_adjustments={},
        totals_adjustments={},
        injury_nowcast_impact_home=None,
        injury_nowcast_impact_away=None,
        injury_nowcast_freshness_home_hours=None,
        injury_nowcast_freshness_away_hours=None,
        injury_nowcast_confidence_home=None,
        injury_nowcast_confidence_away=None,
        injury_nowcast_offense_multiplier_home=None,
        injury_nowcast_offense_multiplier_away=None,
        injury_nowcast_defense_multiplier_home=None,
        injury_nowcast_defense_multiplier_away=None,
    )
    factors = decomp.get("factor_contributions") if isinstance(decomp.get("factor_contributions"), dict) else {}
    components = {
        name: {
            "margin_points": float((item or {}).get("margin_points") or 0.0),
            "total_points": float((item or {}).get("total_points") or 0.0),
        }
        for name, item in factors.items()
        if isinstance(item, dict)
    }
    return {
        "home": home,
        "away": away,
        "strength_source": strength_source,
        "offense_index_home": round(float(offense_index_home), 6),
        "offense_index_away": round(float(offense_index_away), 6),
        "defense_index_home": round(float(defense_index_home), 6),
        "defense_index_away": round(float(defense_index_away), 6),
        "predicted_margin": decomp.get("predicted_margin"),
        "predicted_total": decomp.get("predicted_total"),
        "expected_home_points": decomp.get("expected_home_points"),
        "expected_away_points": decomp.get("expected_away_points"),
        "spread_home": (
            round(-float(decomp["predicted_margin"]), 4)
            if decomp.get("predicted_margin") is not None
            else None
        ),
        "components": components,
    }


def replay_focus_matchups(
    priors: Optional[Mapping[str, Mapping[str, float]]] = None,
    matchups: Optional[Iterable[Mapping[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    epa = dict(priors or load_packaged_epa_priors())
    rows: List[Dict[str, Any]] = []
    for game in matchups or FOCUS_MATCHUPS:
        home = str(game["home"])
        away = str(game["away"])
        home_epa = epa.get(home) or epa.get("LA" if home == "LAR" else home) or {}
        away_epa = epa.get(away) or {}
        if not home_epa or not away_epa:
            raise KeyError(f"missing packaged EPA prior for {away}@{home}")
        epa_row = decompose_matchup(
            home=home,
            away=away,
            offense_index_home=float(home_epa["offense_index"]),
            offense_index_away=float(away_epa["offense_index"]),
            defense_index_home=float(home_epa["defense_index"]),
            defense_index_away=float(away_epa["defense_index"]),
            strength_source="packaged_epa_prior",
        )
        rec_h = record_indices(str(game["home_record_after_w1"]))
        rec_a = record_indices(str(game["away_record_after_w1"]))
        rec_row = decompose_matchup(
            home=home,
            away=away,
            offense_index_home=rec_h[0],
            offense_index_away=rec_a[0],
            defense_index_home=rec_h[1],
            defense_index_away=rec_a[1],
            strength_source="espn_win_loss_record",
        )
        live_spread = game.get("live_model_spread_home")
        epa_spread = epa_row.get("spread_home")
        rec_spread = rec_row.get("spread_home")
        rows.append(
            {
                "key": game["key"],
                "week": game.get("week"),
                "live": {
                    "model_spread_home": live_spread,
                    "kei_spread_home": game.get("live_kei_spread_home"),
                    "model_total": game.get("live_model_total"),
                    "kei_total": game.get("live_kei_total"),
                    "projection_created_at": game.get("projection_created_at"),
                },
                "actual": (
                    {
                        "away": game.get("actual_away"),
                        "home": game.get("actual_home"),
                        "total": (
                            float(game["actual_away"]) + float(game["actual_home"])
                            if game.get("actual_away") is not None
                            and game.get("actual_home") is not None
                            else None
                        ),
                    }
                    if game.get("actual_away") is not None
                    else None
                ),
                "epa": epa_row,
                "record": rec_row,
                "deltas": {
                    "epa_spread_minus_live_model": (
                        None
                        if epa_spread is None or live_spread is None
                        else round(float(epa_spread) - float(live_spread), 4)
                    ),
                    "record_spread_minus_live_model": (
                        None
                        if rec_spread is None or live_spread is None
                        else round(float(rec_spread) - float(live_spread), 4)
                    ),
                    "record_spread_minus_epa_spread": (
                        None
                        if rec_spread is None or epa_spread is None
                        else round(float(rec_spread) - float(epa_spread), 4)
                    ),
                    "epa_total_minus_live_model": (
                        None
                        if epa_row.get("predicted_total") is None or game.get("live_model_total") is None
                        else round(float(epa_row["predicted_total"]) - float(game["live_model_total"]), 4)
                    ),
                },
            }
        )
    return rows


def locked_scoring_snapshot() -> Dict[str, Any]:
    cfg = get_nfl_handicapping_config()
    priors = cfg["priors"]
    base_eff = cfg["factors"]["base_efficiency"]
    hfa = cfg["factors"]["home_field_advantage"]
    return {
        "framework_version": cfg["framework_version"],
        "base_total_points": float(priors["base_total_points"]),
        "home_field_points": float(priors["home_field_points"]),
        "base_efficiency_max_total_points": float(base_eff["max_total_points"]),
        "base_efficiency_max_margin_points": float(base_eff["max_margin_points"]),
        "base_efficiency_total_weight": float(base_eff["total_weight"]),
        "base_efficiency_margin_weight": float(base_eff["margin_weight"]),
        "hfa_margin_points": float(hfa["margin_points"]),
    }
