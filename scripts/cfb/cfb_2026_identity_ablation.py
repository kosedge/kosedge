#!/usr/bin/env python3
"""2026 identity ablation — what creates live totals inflation.

Research only. Does not fit λ, does not touch 2025 hist residuals,
does not change production math / kill switch / PLAY.

Variants (same frozen formula, same W1/W2 confirmatory books):
  frozen          — live roster + live SP+ carry
  roster_league   — league-avg roster/QB/units, keep SP+
  efficiency_league — keep roster, league-avg efficiency
  both_league     — hist-cal-style identity (control)

Usage:
  PYTHONPATH=services/model-service python3 scripts/cfb/cfb_2026_identity_ablation.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
sys.path.insert(0, str(MS))
sys.path.insert(0, str(ROOT / "scripts" / "cfb"))

from src.services.cfb_season_engine import (  # noqa: E402
    project_game_preview,
    resolve_season_universe,
)
from src.services.cfb_season_engine.historical_calibration import (  # noqa: E402
    build_historical_proxy_state,
)
from src.services.cfb_season_engine.efficiency import build_efficiency_profile  # noqa: E402
from src.services.cfb_season_engine.fbs_universe import official_fbs_codes  # noqa: E402
from src.services.cfb_season_engine.power_sot import (  # noqa: E402
    sit_missing_power_from_sot_rows,
)
from src.services.cfb_season_engine.team_projection import (  # noqa: E402
    compose_team_projection,
    project_game_to_dict,
)
from src.services.cfb_season_engine.totals_guard_holdout import (  # noqa: E402
    matchup_inflation_on_sum,
)
from src.services.cfb_season_engine import priors as P  # noqa: E402
from cfb_model_total_diagnostic import (  # noqa: E402
    attach_odds,
    load_w1_card,
    slim_from_espn,
    _f,
    _mean,
    _mae,
    _median,
    _rmse,
)

OFFICIAL = MS / "src/services/cfb_season_engine/data/cfb_official_schedule_2026.json"
POWER = MS / "src/services/cfb_season_engine/data/cfb_power_sot_2026.json"
W2_ODDS = ROOT / "data/ops/cfb-w2-espn-scoreboard-odds-20260911.json"
OUT = ROOT / "data/ops/cfb-2026-identity-ablation-20260911.json"


def _league_efficiency(code: str):
    """Explicit 50s — build_efficiency_profile(None) would reload packaged SP+."""
    return build_efficiency_profile(
        code,
        {
            "off_eff": 50.0,
            "def_eff": 50.0,
            "success_off": 50.0,
            "success_def": 50.0,
            "explosiveness": 50.0,
            "sp_plus": 0.0,
            "fidelity": "placeholder",
            "source": "ablation_explicit_league_50",
            "notes": "Research ablation only. Not a silent official-FBS fill.",
        },
    )


def _project(universe, home: str, away: str, week: int, neutral: bool) -> Dict[str, Any]:
    return project_game_to_dict(
        project_game_preview(
            universe,
            home_team=home,
            away_team=away,
            week=week,
            season=2026,
            neutral_site=neutral,
        )
    )


def main() -> int:
    universe, meta = resolve_season_universe(
        season=2026, as_of_week=1, demo=True, session=None
    )
    official = json.loads(OFFICIAL.read_text(encoding="utf-8"))
    fbs = official_fbs_codes()
    required = set()
    for raw in official.get("games") or []:
        if int(raw.get("week") or -1) not in (1, 2):
            continue
        for side in (raw.get("home"), raw.get("away")):
            code = str(side or "").upper()
            if code in fbs:
                required.add(code)
    sit_missing_power_from_sot_rows(
        universe,
        json.loads(POWER.read_text(encoding="utf-8")).get("teams") or [],
        required=sorted(required),
        context="cfb_2026_identity_ablation",
    )

    # Snapshot live states so we can swap in/out.
    live_states = {c: universe.teams[c] for c in universe.teams}

    w2 = slim_from_espn(W2_ODDS)
    w1 = load_w1_card()

    variants = ("frozen", "roster_league", "efficiency_league", "both_league")
    buckets: Dict[str, List[Dict[str, Any]]] = {v: [] for v in variants}

    for raw in official.get("games") or []:
        week = int(raw.get("week") or -1)
        if week not in (1, 2):
            continue
        home = str(raw.get("home") or "").upper()
        away = str(raw.get("away") or "").upper()
        if raw.get("fcs_home") or raw.get("fcs_away"):
            continue
        if home not in live_states or away not in live_states:
            continue
        market_total = None
        pair = f"{away}@{home}"
        if week == 2:
            odds = attach_odds(
                {
                    "home": home,
                    "away": away,
                    "home_name": raw.get("home_name"),
                    "away_name": raw.get("away_name"),
                },
                w2["by_key"],
            )
            if odds:
                market_total = _f(odds.get("best_total"))
        else:
            market_total = (w1.get(pair) or {}).get("market_total")
        if market_total is None:
            continue

        for variant in variants:
            if variant == "frozen":
                universe.teams[home] = live_states[home]
                universe.teams[away] = live_states[away]
            elif variant == "roster_league":
                universe.teams[home] = build_historical_proxy_state(
                    home,
                    live_states[home].efficiency,
                    home_field_payload=_hfa(live_states[home]),
                )
                universe.teams[away] = build_historical_proxy_state(
                    away,
                    live_states[away].efficiency,
                    home_field_payload=_hfa(live_states[away]),
                )
            elif variant == "efficiency_league":
                universe.teams[home] = compose_team_projection(
                    home,
                    live_states[home].roster,
                    live_states[home].qb,
                    live_states[home].groups,
                    efficiency=_league_efficiency(home),
                    home_field=live_states[home].home_field,
                    coaching=live_states[home].coaching,
                )
                universe.teams[away] = compose_team_projection(
                    away,
                    live_states[away].roster,
                    live_states[away].qb,
                    live_states[away].groups,
                    efficiency=_league_efficiency(away),
                    home_field=live_states[away].home_field,
                    coaching=live_states[away].coaching,
                )
            else:
                universe.teams[home] = build_historical_proxy_state(
                    home,
                    _league_efficiency(home),
                    home_field_payload=_hfa(live_states[home]),
                )
                universe.teams[away] = build_historical_proxy_state(
                    away,
                    _league_efficiency(away),
                    home_field_payload=_hfa(live_states[away]),
                )

            proj = _project(
                universe, home, away, week, bool(raw.get("neutral_site"))
            )
            drivers = (proj.get("drivers") or {}).get("matchup") or {}
            model_total = float(proj["expected_total"])
            model_spread = float(proj["spread_home"])
            infl = None
            try:
                _, infl = matchup_inflation_on_sum(
                    model_total=model_total,
                    home_diag=drivers.get("home_points_diag") or {},
                    away_diag=drivers.get("away_points_diag") or {},
                    league_ppg=float(P.LEAGUE_TEAM_PPG),
                    points_clamp=P.EXPECTED_POINTS_CLAMP,
                    st_nudge=float(drivers.get("st_total_nudge") or 0.0),
                )
            except Exception:
                infl = None
            buckets[variant].append(
                {
                    "week": week,
                    "pair": pair,
                    "model_total": round(model_total, 4),
                    "model_spread_home": round(model_spread, 4),
                    "market_total": market_total,
                    "total_resid": round(model_total - market_total, 4),
                    "matchup_inflation": None if infl is None else round(infl, 4),
                    "home_off": universe.teams[home].offense_index,
                    "away_off": universe.teams[away].offense_index,
                    "home_def": universe.teams[home].defense_index,
                    "away_def": universe.teams[away].defense_index,
                }
            )

        # restore live
        universe.teams[home] = live_states[home]
        universe.teams[away] = live_states[away]

    summary = {}
    for variant, rows in buckets.items():
        resid = [r["total_resid"] for r in rows]
        infl = [
            r["matchup_inflation"]
            for r in rows
            if r.get("matchup_inflation") is not None
        ]
        spreads = [r["model_spread_home"] for r in rows]
        summary[variant] = {
            "n": len(rows),
            "mean_total_resid": _mean(resid),
            "median_total_resid": _median(resid),
            "total_mae": _mae(resid),
            "total_rmse": _rmse(resid),
            "mean_matchup_inflation": _mean(infl),
            "mean_model_total": _mean([r["model_total"] for r in rows]),
            "mean_abs_spread": _mean([abs(s) for s in spreads]),
            "mean_off_index": _mean(
                [0.5 * (r["home_off"] + r["away_off"]) for r in rows]
            ),
            "sd_off_index": _sd(
                [r["home_off"] for r in rows] + [r["away_off"] for r in rows]
            ),
        }

    # Restore nothing — process ends.
    payload = {
        "ok": True,
        "research_only": True,
        "production_model_changed": False,
        "kill_switch": "CFB_EDGE_BOARD_PUBLIC_ENABLED=false",
        "universe_mode": meta.get("mode"),
        "note": (
            "Confirmatory 2026 W1/W2 books only. Not a λ fit. "
            "2025 historical residuals were not opened."
        ),
        "summary": summary,
        "delta_vs_frozen": {
            k: {
                "mean_total_resid": _sub(
                    summary[k]["mean_total_resid"],
                    summary["frozen"]["mean_total_resid"],
                ),
                "mean_matchup_inflation": _sub(
                    summary[k]["mean_matchup_inflation"],
                    summary["frozen"]["mean_matchup_inflation"],
                ),
            }
            for k in variants
            if k != "frozen"
        },
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    print(f"wrote {OUT}")
    return 0


def _hfa(state) -> Optional[Dict[str, Any]]:
    if not state.home_field:
        return None
    return {
        "bucket": state.home_field.bucket,
        "hfa_points": state.home_field.hfa_points,
    }


def _sd(xs: List[float]) -> Optional[float]:
    if len(xs) < 2:
        return None
    mu = sum(xs) / len(xs)
    return round(math.sqrt(sum((x - mu) ** 2 for x in xs) / len(xs)), 4)


def _sub(a, b) -> Optional[float]:
    if a is None or b is None:
        return None
    return round(float(a) - float(b), 4)


if __name__ == "__main__":
    raise SystemExit(main())
