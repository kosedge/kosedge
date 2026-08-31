"""Single CFB Power source of truth (research only).

One composed strength table feeds Team DNA, project-game, and season
projections. used_in_spread stays false. No KEI. No CFP%.

Power indices are read from the v0.14+ universe compose (efficiency backbone
+ roster/QB prior). This module does not invent a parallel rating.
"""

from __future__ import annotations

import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_season_engine.conferences import conference_for
from src.services.cfb_season_engine.fbs_universe import official_fbs_codes
from src.services.cfb_season_engine.home_field import resolve_hfa_points
from src.services.cfb_season_engine.margin_calibration import (
    apply_calibrated_scores,
    fcs_matchup_from_states,
)
from src.services.cfb_season_engine.official_schedule import (
    games_from_blob,
    load_official_schedule_blob,
)
from src.services.cfb_season_engine.priors import ENGINE_VERSION, score_noise_sd_for_week
from src.services.cfb_season_engine.team_projection import expected_team_points
from src.services.cfb_season_engine.types import EngineUniverse, ScheduledGame

USED_IN_SPREAD = False
POWER_VERSION = "cfb-power-sot-v0.15-20260814"
POWER_AS_OF = "2026-08-14"
PROJECTION_ARTIFACT_ID = "cfb-season-projections-v0.15-n10000-20260814"
DEFAULT_N_SIMS = 10_000
BOWL_WIN_THRESHOLD = 6
# Post–Week-0 close stamp (research). Power indices stay on the pre-Week-0 SoT;
# only as_of / artifact ids advance when close_week0 packages.
CLOSE_AS_OF = "2026-08-31"
CLOSE_POWER_VERSION = "cfb-power-sot-v0.15-week0-close-20260831"
CLOSE_PROJECTION_ARTIFACT_ID = "cfb-season-projections-v0.15-n10000-week0-close-20260831"
DATA_DIR = Path(__file__).resolve().parent / "data"
POWER_PACK_PATH = DATA_DIR / "cfb_power_sot_2026.json"
PROJECTION_PACK_PATH = DATA_DIR / "cfb_season_projections_2026.json"
WEB_DATA = Path(__file__).resolve().parents[5] / "apps" / "web" / "lib" / "data"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _efficiency_fill(source: str) -> str:
    src = str(source or "")
    if "warehouse" in src:
        return "warehouse"
    if src == "thin_sample_labeled":
        return "thin"
    if src == "league_average_fill":
        return "league_avg"
    return "sp_plus_or_packaged"


def _week_board(weeks: Sequence[int] = (0, 1), *, season: int = 2026) -> Dict[str, Any]:
    blob = load_official_schedule_blob(season)
    wanted = {int(w) for w in weeks}
    games = [
        {
            "week": g.week,
            "home": g.home_team,
            "away": g.away_team,
            "neutral_site": bool(g.neutral_site),
        }
        for g in games_from_blob(blob, season=season)
        if int(g.week) in wanted
    ]
    return {
        "n_games": len(games),
        "weeks": sorted(wanted),
        "slate_complete": bool(blob.get("slate_complete")),
        "games": games,
    }


def _next_opponent(
    code: str,
    board: Mapping[str, Any],
) -> Optional[Dict[str, Any]]:
    for row in board.get("games") or []:
        if row.get("home") == code:
            return {
                "week": row.get("week"),
                "opponent": row.get("away"),
                "home": True,
                "neutral_site": row.get("neutral_site"),
            }
        if row.get("away") == code:
            return {
                "week": row.get("week"),
                "opponent": row.get("home"),
                "home": False,
                "neutral_site": row.get("neutral_site"),
            }
    return None


def power_row_from_universe(
    universe: EngineUniverse,
    code: str,
    *,
    board: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """One official-FBS row from the composed universe — the only strength SoT."""
    st = universe.teams.get(code)
    qb = st.qb if st else None
    eff = st.efficiency if st else None
    src = str(eff.source or "") if eff else ""
    return {
        "team": code,
        "conference": universe.conferences.get(code) or conference_for(code),
        "offense_index": round(st.offense_index, 4) if st else None,
        "defense_index": round(st.defense_index, 4) if st else None,
        "power_index": (
            round(0.5 * (st.offense_index + st.defense_index), 4) if st else None
        ),
        "early_season_uncertainty": (
            round(st.early_season_uncertainty, 4) if st else None
        ),
        "qb_class": qb.qb_class if qb else None,
        "qb_name": qb.starter_name if qb else None,
        "open_qb": bool(qb and qb.qb_class == "open_competition"),
        "efficiency_source": src or None,
        "efficiency_fill": _efficiency_fill(src),
        "off_eff": round(eff.off_eff, 2) if eff else None,
        "def_eff": round(eff.def_eff, 2) if eff else None,
        "next": _next_opponent(code, board or {}),
    }


def build_power_sot(
    universe: EngineUniverse,
    *,
    weeks: Sequence[int] = (0, 1),
    as_of: Optional[str] = None,
    power_version: Optional[str] = None,
) -> Dict[str, Any]:
    official = official_fbs_codes()
    board = _week_board(tuple(weeks), season=int(universe.season))
    rows = [power_row_from_universe(universe, code, board=board) for code in official]
    ranked = sorted(
        rows,
        key=lambda r: (-(r["power_index"] or -999.0), r["team"]),
    )
    for i, row in enumerate(ranked, start=1):
        row["rank"] = i
    by_code = {row["team"]: row for row in ranked}
    stamp_as_of = as_of or POWER_AS_OF
    stamp_version = power_version or POWER_VERSION
    return {
        "ok": True,
        "power_version": stamp_version,
        "power_as_of": stamp_as_of,
        "engine_version": ENGINE_VERSION,
        "n_teams": len(ranked),
        "official_fbs": len(official),
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
        "research_only": True,
        "method": (
            "0.5*(offense_index+defense_index) from the composed universe "
            "(v0.14 efficiency backbone + roster/QB prior). Not a second rating."
        ),
        "teams": ranked,
        "by_team": by_code,
        "week_board": {
            "n_games": board.get("n_games"),
            "weeks": board.get("weeks"),
            "slate_complete": board.get("slate_complete"),
        },
    }


def frozen_expected_scores(
    game: ScheduledGame,
    teams: Mapping[str, Any],
) -> Optional[Tuple[float, float, float]]:
    """Same expected-score path as realize_game_scores, without the RNG draw."""
    home = teams.get(game.home_team)
    away = teams.get(game.away_team)
    if home is None or away is None:
        return None
    night = bool(getattr(game, "night_game", False))
    home_exp, _ = expected_team_points(
        home,
        away,
        home=True,
        neutral_site=game.neutral_site,
        week=game.week,
        night_game=night,
        home_hfa_profile=home.home_field,
    )
    away_exp, _ = expected_team_points(
        away,
        home,
        home=False,
        neutral_site=game.neutral_site,
        week=game.week,
        night_game=False,
        home_hfa_profile=home.home_field,
    )
    hfa_pts = float(
        resolve_hfa_points(
            home.home_field,
            home=True,
            neutral_site=game.neutral_site,
            night_game=night,
        ).get("hfa_points")
        or 0.0
    )
    cal_scores = apply_calibrated_scores(
        home_exp - hfa_pts,
        away_exp,
        fcs_matchup=fcs_matchup_from_states(home, away)
        or bool(getattr(game, "fcs_home", False) or getattr(game, "fcs_away", False)),
    )
    home_exp = float(cal_scores["home_exp_cal"]) + hfa_pts
    away_exp = float(cal_scores["away_exp_cal"])
    sd = float(score_noise_sd_for_week(game.week))
    return home_exp, away_exp, sd


def frozen_home_wp(home_exp: float, away_exp: float, sd: float) -> float:
    """P(home_score > away_score) under the same independent-Gaussian model.

    Applies the same cupcake SD saturation as win_prob_from_expected_scores so
    published Bernoulli paths and project-game WP stay on one mapper family.
    """
    from src.services.cfb_season_engine import priors as P

    margin = float(home_exp) - float(away_exp)
    raw_sd = max(1e-6, float(sd) * math.sqrt(2.0))
    abs_m = abs(margin)
    if abs_m >= P.WP_CUPCAKE_Z * 8.0:
        sat_sd = abs_m / P.WP_CUPCAKE_Z
        eff_sd = min(raw_sd, sat_sd)
    else:
        eff_sd = raw_sd
    return float(NormalDist().cdf(margin / max(1e-6, eff_sd)))


def _game_is_final(game: ScheduledGame) -> bool:
    return (
        game.home_score is not None
        and game.away_score is not None
        and str(game.status or "").lower() in ("", "final", "closed", "complete", "completed")
    )


def build_season_projection_artifact(
    universe: EngineUniverse,
    *,
    n_sims: int = DEFAULT_N_SIMS,
    seed: int = 2026,
    power: Optional[Mapping[str, Any]] = None,
    as_of: Optional[str] = None,
    artifact_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Frozen-SoT Monte Carlo on the official slate.

    Each remaining game is an independent Bernoulli using project-game expected
    scores. Finals already on the schedule are locked (no power refit). In-path
    strength evolution is off so the published table stays on one power snapshot.
    """
    if n_sims < 1:
        raise ValueError("n_sims must be >= 1")
    official = official_fbs_codes()
    power = power if power is not None else build_power_sot(universe)
    stamp_as_of = as_of or str(power.get("power_as_of") or POWER_AS_OF)
    stamp_artifact = artifact_id or PROJECTION_ARTIFACT_ID
    open_games: List[Tuple[ScheduledGame, float]] = []
    locked: List[Tuple[ScheduledGame, bool]] = []
    skipped = 0
    for game in universe.schedule:
        if _game_is_final(game):
            locked.append((game, float(game.home_score) >= float(game.away_score)))
            continue
        pair = frozen_expected_scores(game, universe.teams)
        if pair is None:
            skipped += 1
            continue
        home_exp, away_exp, sd = pair
        open_games.append((game, frozen_home_wp(home_exp, away_exp, sd)))

    rng = random.Random(seed)
    win_paths: Dict[str, List[float]] = {t: [] for t in official}
    for _ in range(n_sims):
        tally = {t: 0.0 for t in official}
        for game, home_won in locked:
            winner = game.home_team if home_won else game.away_team
            if winner in tally:
                tally[winner] += 1.0
        for game, p_home in open_games:
            home_won = rng.random() < p_home
            winner = game.home_team if home_won else game.away_team
            if winner in tally:
                tally[winner] += 1.0
        for team in official:
            win_paths[team].append(tally[team])

    rows: List[Dict[str, Any]] = []
    for team in official:
        values = win_paths[team]
        ordered = sorted(values)
        n = len(ordered)
        mean = sum(values) / n
        var = sum((v - mean) ** 2 for v in values) / n
        std = math.sqrt(var)
        p10 = ordered[max(0, min(n - 1, int(round((n - 1) * 0.10))))]
        p50 = ordered[max(0, min(n - 1, int(round((n - 1) * 0.50))))]
        p90 = ordered[max(0, min(n - 1, int(round((n - 1) * 0.90))))]
        p_bowl = sum(1.0 for v in values if v >= BOWL_WIN_THRESHOLD) / n
        pwr = (power.get("by_team") or {}).get(team) or {}
        rows.append(
            {
                "team": team,
                "conference": pwr.get("conference") or conference_for(team),
                "mean": round(mean, 3),
                "std": round(std, 3),
                "p10": round(p10, 3),
                "p50": round(p50, 3),
                "p90": round(p90, 3),
                "p_bowl": round(p_bowl, 4),
                "power_index": pwr.get("power_index"),
                "power_rank": pwr.get("rank"),
                "offense_index": pwr.get("offense_index"),
                "defense_index": pwr.get("defense_index"),
            }
        )
    rows.sort(key=lambda r: (-r["mean"], -r["p50"], r["team"]))
    for i, row in enumerate(rows, start=1):
        row["rank"] = i

    sum_mean = sum(float(r["mean"]) for r in rows)
    n_scored = len(open_games) + len(locked)
    return {
        "ok": True,
        "artifact_id": stamp_artifact,
        "engine_version": ENGINE_VERSION,
        "power_version": power.get("power_version") or POWER_VERSION,
        "power_as_of": power.get("power_as_of") or POWER_AS_OF,
        "as_of": stamp_as_of,
        "generated_at": _utc_now(),
        "n_sims": n_sims,
        "sim_seed": seed,
        "n_teams": len(rows),
        "n_games_scored": n_scored,
        "n_games_locked": len(locked),
        "n_games_open": len(open_games),
        "n_games_skipped": skipped,
        "slate_games": len(universe.schedule),
        "sum_expected_wins": round(sum_mean, 3),
        "wins_conserved_note": (
            "Each scored game awards one win. Finals on the schedule are locked "
            "(no power refit). Sum of FBS E[wins] is below n_games_scored when "
            "FCS sides take wins. Not densified seed."
        ),
        "method": (
            "Frozen-SoT independent Bernoulli on official ESPN slate. "
            "P(home) from expected_team_points + margin calibration + HFA + "
            "cupcake WP saturation. In-path evolution off. Locked finals respected."
        ),
        "lineage": {
            "engine": "cfb",
            "as_of": stamp_as_of,
            "sim_seed": seed,
            "sim_n": n_sims,
            "wp_mapper": "power_sot.frozen_home_wp+team_projection.win_prob_from_expected_scores",
            "shock": "priors.SCORE_NOISE_SD+STRENGTH_NOISE",
            "kei_def": "cfb_kei.apply_cfb_kei",
        },
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
        "research_only": True,
        "win_tables_final": False,
        "cfp_make": None,
        "natty": None,
        "bowl_threshold": BOWL_WIN_THRESHOLD,
        "teams": rows,
    }


def write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return path


def load_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_packaged_power_sot() -> Dict[str, Any]:
    return load_json(POWER_PACK_PATH)


def load_packaged_season_projections() -> Dict[str, Any]:
    return load_json(PROJECTION_PACK_PATH)


def package_research_desk(
    universe: EngineUniverse,
    *,
    n_sims: int = DEFAULT_N_SIMS,
    seed: int = 2026,
    as_of: Optional[str] = None,
    power_version: Optional[str] = None,
    artifact_id: Optional[str] = None,
    write_web_mirrors: bool = True,
) -> Dict[str, Path]:
    stamp_as_of = as_of or POWER_AS_OF
    stamp_power = power_version or POWER_VERSION
    stamp_artifact = artifact_id or PROJECTION_ARTIFACT_ID
    power = build_power_sot(
        universe, as_of=stamp_as_of, power_version=stamp_power
    )
    # Drop by_team from the on-disk pack (teams[] is enough; keeps file lean).
    disk_power = {k: v for k, v in power.items() if k != "by_team"}
    proj = build_season_projection_artifact(
        universe,
        n_sims=n_sims,
        seed=seed,
        power=power,
        as_of=stamp_as_of,
        artifact_id=stamp_artifact,
    )
    paths = {
        "power": write_json(POWER_PACK_PATH, disk_power),
        "projections": write_json(PROJECTION_PACK_PATH, proj),
    }
    if write_web_mirrors and WEB_DATA.is_dir():
        paths["web_power"] = write_json(WEB_DATA / "cfb-power-sot-2026.json", disk_power)
        paths["web_projections"] = write_json(
            WEB_DATA / "cfb-season-projections-2026.json", proj
        )
    return paths


def documentation() -> Dict[str, Any]:
    return {
        "layer": "power_sot",
        "power_version": POWER_VERSION,
        "power_as_of": POWER_AS_OF,
        "projection_artifact_id": PROJECTION_ARTIFACT_ID,
        "n_sims_default": DEFAULT_N_SIMS,
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
        "cfp_make": None,
        "natty": None,
        "consumers": ["team_dna", "project_game_indices", "season_projections"],
        "ops": "data/ops/cfb-phase1-projections-power-20260814.md",
    }
