#!/usr/bin/env python3
"""Build frozen CFB KEI W0/W1 lines + path futures (natty / CFP / conf titles)."""

from __future__ import annotations

import json
import os
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
sys.path.insert(0, str(MS))

from src.services.cfb_season_engine import (  # noqa: E402
    DEFAULT_SEASON_ENGINE_VERSION,
    project_game_preview,
    project_game_to_dict,
    resolve_season_universe,
)
from src.services.cfb_season_engine.types import TeamProjectionState  # noqa: E402
from src.services.cfb_season_engine.cfb_futures import (  # noqa: E402
    FUTURES_VERSION,
    accumulate_path,
    finalize_futures,
)
from src.services.cfb_season_engine.cfb_kei import (  # noqa: E402
    KEI_VERSION,
    apply_cfb_kei,
    diagnostic_short_fav_sample,
)
from src.services.cfb_season_engine.conferences import conference_for  # noqa: E402
from src.services.cfb_season_engine.product_desk import official_week_board  # noqa: E402
from src.services.cfb_season_engine.team_projection import expected_team_points  # noqa: E402
from src.services.cfb_season_engine import priors as P  # noqa: E402

AS_OF = os.environ.get("CFB_CLOSE_AS_OF") or "2026-08-31"
N_FUTURES = 2500
SEED = int(os.environ.get("CFB_FUTURES_SEED") or 20260831)


def hydrate_missing_from_power_sot(universe) -> int:
    """Fill official FBS codes that the packaged roster universe omitted."""
    path = MS / "src/services/cfb_season_engine/data/cfb_power_sot_2026.json"
    pack = json.loads(path.read_text(encoding="utf-8"))
    added = 0
    for row in pack.get("teams") or []:
        code = str(row.get("team") or "").upper()
        if not code or code in universe.teams:
            continue
        universe.teams[code] = TeamProjectionState(
            team=code,
            offense_index=float(row.get("offense_index") or 1.0),
            defense_index=float(row.get("defense_index") or 1.0),
            early_season_uncertainty=float(row.get("early_season_uncertainty") or 0.35),
            source="power_sot_v0.15_fill",
            fidelity="approximate",
            notes={"fill": "power_sot_identity_gap"},
        )
        added += 1
    return added


def _load_official() -> Dict[str, Any]:
    path = MS / "src/services/cfb_season_engine/data/cfb_official_schedule_2026.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path} ({path.stat().st_size} bytes)")


def build_kei_board(universe, official: Dict[str, Any]) -> Dict[str, Any]:
    games_out: List[Dict[str, Any]] = []
    for raw in official.get("games") or []:
        try:
            week = int(raw.get("week"))
        except (TypeError, ValueError):
            continue
        if week not in (0, 1):
            continue
        home = str(raw.get("home") or "").upper()
        away = str(raw.get("away") or "").upper()
        fcs_home = bool(raw.get("fcs_home")) or home.startswith("FCS:")
        fcs_away = bool(raw.get("fcs_away")) or away.startswith("FCS:")
        fbs = (not fcs_home) and (not fcs_away)
        row: Dict[str, Any] = {
            "game_id": raw.get("game_id"),
            "week": week,
            "home": home,
            "away": away,
            "home_name": raw.get("home_name") or home,
            "away_name": raw.get("away_name") or away,
            "kickoff": raw.get("kickoff"),
            "neutral_site": bool(raw.get("neutral_site")),
            "fcs_home": fcs_home,
            "fcs_away": fcs_away,
            "fbs_vs_fbs": fbs,
        }
        if not fbs or home not in universe.teams or away not in universe.teams:
            row["kei"] = {
                "kei_version": KEI_VERSION,
                "used_in_spread": False,
                "fcs_opener": True,
                "tag": "PASS",
                "reason": "FCS or unknown code — no FBS-equivalent KEI precision",
            }
            games_out.append(row)
            continue
        proj = project_game_to_dict(
            project_game_preview(
                universe,
                home_team=home,
                away_team=away,
                week=week,
                season=2026,
                neutral_site=bool(raw.get("neutral_site")),
            )
        )
        kei = apply_cfb_kei(proj, fbs_vs_fbs=True)
        row["model_spread_home"] = kei["model_spread_home"]
        row["model_total"] = kei["model_total"]
        row["model_home_win_prob"] = kei["model_home_win_prob"]
        row["kei"] = kei
        games_out.append(row)

    fbs_rows = [g for g in games_out if g.get("fbs_vs_fbs") and g.get("kei", {}).get("kei_spread_home") is not None]
    return {
        "ok": True,
        "kei_version": KEI_VERSION,
        "engine_version": DEFAULT_SEASON_ENGINE_VERSION,
        "as_of": AS_OF,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "weeks": [0, 1],
        "n_games": len(games_out),
        "n_fbs_with_kei": len(fbs_rows),
        "n_w0_fbs_with_kei": sum(1 for g in fbs_rows if g["week"] == 0),
        "used_in_spread": True,
        "model_used_in_spread": False,
        "bias_guard": diagnostic_short_fav_sample(),
        "games": games_out,
    }


def kei_lines_file(board: Dict[str, Any]) -> Dict[str, Any]:
    games = []
    for row in board["games"]:
        kei = row.get("kei") or {}
        if kei.get("kei_spread_home") is None:
            continue
        games.append(
            {
                "id": row.get("game_id"),
                "homeTeam": row.get("home_name"),
                "awayTeam": row.get("away_name"),
                "homeAbbr": row.get("home"),
                "awayAbbr": row.get("away"),
                "commenceTime": row.get("kickoff"),
                "week": row.get("week"),
                "handicapSpreadHome": kei.get("kei_spread_home"),
                "handicapTotal": kei.get("kei_total"),
                "handicapHomeWinProb": kei.get("kei_home_win_prob"),
                "projSpreadHome": kei.get("kei_spread_home"),
                "projTotal": kei.get("kei_total"),
                "modelSpreadHome": kei.get("model_spread_home"),
                "modelTotal": kei.get("model_total"),
                "modelHomeWinProb": kei.get("model_home_win_prob"),
                "kei_version": KEI_VERSION,
            }
        )
    return {"sport": "cfb", "kei_version": KEI_VERSION, "as_of": AS_OF, "games": games}


def build_futures(universe, official: Dict[str, Any]) -> Dict[str, Any]:
    teams = list(universe.team_codes)
    conferences = universe.conferences
    power = {
        code: 0.5
        * (
            float(getattr(universe.teams[code], "offense_index", 1.0) or 1.0)
            + float(getattr(universe.teams[code], "defense_index", 1.0) or 1.0)
        )
        for code in teams
        if code in universe.teams
    }
    precomputed = []
    locked = []
    for raw in official.get("games") or []:
        if str(raw.get("season_type") or "regular") not in {"regular", ""}:
            continue
        home = str(raw.get("home") or "").upper()
        away = str(raw.get("away") or "").upper()
        if home.startswith("FCS:") or away.startswith("FCS:"):
            continue
        if home not in universe.teams or away not in universe.teams:
            continue
        try:
            week = int(raw.get("week"))
        except (TypeError, ValueError):
            week = 1
        conf_game = bool(raw.get("conference_game")) or (
            conference_for(home, conferences)
            == conference_for(away, conferences)
            != "Independent"
        )
        # Lock closed finals — no power refit from the margin.
        if raw.get("home_score") is not None and raw.get("away_score") is not None:
            try:
                hs = float(raw["home_score"])
                aws = float(raw["away_score"])
            except (TypeError, ValueError):
                hs = aws = None
            if hs is not None and aws is not None:
                locked.append(
                    {
                        "home": home,
                        "away": away,
                        "home_won": hs >= aws,
                        "conference_game": conf_game,
                    }
                )
                continue
        hs = universe.teams[home]
        aws = universe.teams[away]
        home_exp, _ = expected_team_points(
            hs,
            aws,
            home=True,
            neutral_site=bool(raw.get("neutral_site")),
            week=week,
            night_game=False,
            home_hfa_profile=hs.home_field,
        )
        away_exp, _ = expected_team_points(
            aws,
            hs,
            home=False,
            neutral_site=bool(raw.get("neutral_site")),
            week=week,
            night_game=False,
            home_hfa_profile=hs.home_field,
        )
        precomputed.append(
            {
                "home": home,
                "away": away,
                "home_exp": home_exp,
                "away_exp": away_exp,
                "sd": P.score_noise_sd_for_week(week),
                "conference_game": conf_game,
            }
        )

    rng = random.Random(SEED)
    counts = {"cfp": defaultdict(int), "natty": defaultdict(int), "conf": defaultdict(int)}
    for i in range(N_FUTURES):
        wins: Dict[str, float] = defaultdict(float)
        conf_wins: Dict[str, float] = defaultdict(float)
        for g in locked:
            if g["home_won"]:
                wins[g["home"]] += 1.0
                if g["conference_game"]:
                    conf_wins[g["home"]] += 1.0
            else:
                wins[g["away"]] += 1.0
                if g["conference_game"]:
                    conf_wins[g["away"]] += 1.0
        for g in precomputed:
            hs = max(0.0, rng.gauss(g["home_exp"], g["sd"]))
            aws = max(0.0, rng.gauss(g["away_exp"], g["sd"]))
            if hs >= aws:
                wins[g["home"]] += 1.0
                if g["conference_game"]:
                    conf_wins[g["home"]] += 1.0
            else:
                wins[g["away"]] += 1.0
                if g["conference_game"]:
                    conf_wins[g["away"]] += 1.0
        accumulate_path(
            counts=counts,
            teams=teams,
            wins=wins,
            conf_wins=conf_wins,
            conferences=conferences,
            power=power,
            rng=rng,
        )
        if (i + 1) % 500 == 0:
            print(f"  futures {i + 1}/{N_FUTURES}")

    payload = finalize_futures(
        n_sims=N_FUTURES,
        teams=teams,
        conferences=conferences,
        power=power,
        counts=counts,
        engine_version=DEFAULT_SEASON_ENGINE_VERSION,
        as_of=AS_OF,
    )
    payload["n_games_scored"] = len(precomputed) + len(locked)
    payload["n_games_locked"] = len(locked)
    payload["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload["futures_version"] = FUTURES_VERSION
    return payload


def main() -> None:
    kei_only = "--kei-only" in sys.argv
    universe, meta = resolve_season_universe(season=2026, as_of_week=1, demo=True, session=None)
    filled = hydrate_missing_from_power_sot(universe)
    print("universe", meta.get("mode"), "teams", len(universe.teams), "power_sot_fill", filled)
    official = _load_official()
    board = build_kei_board(universe, official)
    print("KEI W0 FBS", board["n_w0_fbs_with_kei"], "all FBS", board["n_fbs_with_kei"])

    _write(MS / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json", board)
    _write(ROOT / "apps/web/lib/data/cfb-kei-w0-w1-2026.json", board)
    _write(ROOT / "apps/web/data/processed/kei_lines_cfb.json", kei_lines_file(board))
    if kei_only:
        return
    futures = build_futures(universe, official)
    print("futures N", futures["n_sims"], "top natty", [t["team"] for t in futures["top_natty"][:5]])
    _write(MS / "src/services/cfb_season_engine/data/cfb_futures_2026.json", futures)
    _write(ROOT / "apps/web/lib/data/cfb-futures-2026.json", futures)


if __name__ == "__main__":
    main()
