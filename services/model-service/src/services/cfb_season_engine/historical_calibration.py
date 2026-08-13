"""Historical closing-line calibration helpers for the CFB season engine.

Uses free SportsDataverse ESPN CFB betting + team box + linescores (no Odds API
credits) plus prior-year ``cfb_ratings`` adj EPA as an SP+-style efficiency
proxy. Reconstructs a fair hierarchy proxy: prior-year efficiency + league-
average roster/QB/units + curated HFA — historical roster snapshots are not
in-repo.

Honesty: this is graded backtest against real closes/results, but the
reconstruction is an approximation of what v0.8 would have projected (no
season-Y roster/QB). Documented limits ship with every artifact.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import math
import statistics
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.coaching_continuity import build_coaching_continuity
from src.services.cfb_season_engine.conferences import conference_for
from src.services.cfb_season_engine.efficiency import build_efficiency_profile
from src.services.cfb_season_engine.home_field import build_home_field_profile
from src.services.cfb_season_engine.position_groups import build_position_groups
from src.services.cfb_season_engine.qb_situation import build_qb_situation
from src.services.cfb_season_engine.roster_construction import build_roster_construction
from src.services.cfb_season_engine.team_projection import (
    compose_team_projection,
    project_game,
)
from src.services.cfb_season_engine.types import (
    EfficiencyProfile,
    EngineUniverse,
    TeamProjectionState,
)
from src.services.cfb_warehouse.identity import (
    ESPN_ABBR_TO_CODE,
    ESPN_NAME_TO_CODE,
    PACKAGED_CODE_ALIASES,
    resolve_team_code,
)

SDV_BASE = (
    "https://github.com/sportsdataverse/sportsdataverse-data/releases/download"
)
USER_AGENT = "kosedge-cfb-historical-calibration/0.8.1"

# Team identity maps live in cfb_warehouse.identity (single SoT).
# resolve_team_code / ESPN_* / PACKAGED_CODE_ALIASES imported above.


@dataclass(frozen=True)
class HistGame:
    game_id: str
    season: int
    week: int
    home_code: str
    away_code: str
    home_abbr: str
    away_abbr: str
    home_score: int
    away_score: int
    close_spread_home: float  # negative = home favored (Odds API convention)
    close_total: float
    home_conference: str
    away_conference: str


def _http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read()


def fetch_sdv_csv(
    tag: str,
    filename: str,
    *,
    cache_dir: Optional[Path] = None,
) -> List[Dict[str, str]]:
    """Fetch a SportsDataverse release CSV (plain or .gz), with optional cache."""
    cache_path: Optional[Path] = None
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / filename.replace(".gz", "")
        if cache_path.exists():
            with cache_path.open("r", encoding="utf-8") as fh:
                return list(csv.DictReader(fh))

    url = f"{SDV_BASE}/{tag}/{filename}"
    raw = _http_get(url)
    if filename.endswith(".gz"):
        text = gzip.decompress(raw).decode("utf-8", "replace")
    else:
        text = raw.decode("utf-8", "replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    if cache_path is not None:
        with cache_path.open("w", encoding="utf-8", newline="") as fh:
            if rows:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
    return rows


def _sum_linescores(rows: Sequence[Mapping[str, str]]) -> Dict[Tuple[str, str], int]:
    """(game_id, team_id) → total points."""
    out: Dict[Tuple[str, str], int] = defaultdict(int)
    for r in rows:
        try:
            out[(str(r["game_id"]), str(r["team_id"]))] += int(float(r["value"]))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def load_historical_games(
    seasons: Sequence[int],
    *,
    cache_dir: Optional[Path] = None,
    known_codes: Optional[Mapping[str, Any]] = None,
) -> Tuple[List[HistGame], Dict[str, Any]]:
    """Join betting + box + linescores into graded HistGame rows."""
    from src.services.cfb_season_engine.loaders import load_packaged_team_priors

    packaged = load_packaged_team_priors().get("teams") or {}
    if known_codes is None:
        # Accept any code we can name-map even if absent from 2026 priors —
        # proxy states are built on the fly for historical grading.
        known_codes = {
            **{c: True for c in packaged},
            **{c: True for c in ESPN_NAME_TO_CODE.values()},
            **{c: True for c in ESPN_ABBR_TO_CODE.values()},
            **{c: True for c in PACKAGED_CODE_ALIASES.values()},
        }

    games: List[HistGame] = []
    meta = {
        "seasons": list(seasons),
        "source": "sportsdataverse espn_cfb_betting + team_box + linescores",
        "skipped": {
            "missing_line": 0,
            "missing_score": 0,
            "unmapped_team": 0,
            "fcs_or_unknown": 0,
        },
        "mapped_games": 0,
    }

    for season in seasons:
        betting = fetch_sdv_csv(
            "espn_cfb_betting",
            f"betting_{season}.csv.gz",
            cache_dir=cache_dir,
        )
        box = fetch_sdv_csv(
            "espn_cfb_team_box",
            f"team_box_{season}.csv.gz",
            cache_dir=cache_dir,
        )
        lines = fetch_sdv_csv(
            "espn_cfb_linescores",
            f"linescores_{season}.csv.gz",
            cache_dir=cache_dir,
        )
        scores = _sum_linescores(lines)
        by_game: Dict[str, Dict[str, Dict[str, str]]] = defaultdict(dict)
        for row in box:
            by_game[str(row["game_id"])][str(row["home_away"])] = row

        for b in betting:
            gid = str(b["game_id"])
            spread_raw = b.get("home_team_spread") or b.get("game_spread")
            total_raw = b.get("over_under")
            if spread_raw in (None, "") or total_raw in (None, ""):
                meta["skipped"]["missing_line"] += 1
                continue
            try:
                spread = float(spread_raw)
                total = float(total_raw)
            except ValueError:
                meta["skipped"]["missing_line"] += 1
                continue

            sides = by_game.get(gid) or {}
            home = sides.get("home")
            away = sides.get("away")
            if not home or not away:
                meta["skipped"]["missing_score"] += 1
                continue
            hs = scores.get((gid, str(home["team_id"])))
            aws = scores.get((gid, str(away["team_id"])))
            if hs is None or aws is None:
                meta["skipped"]["missing_score"] += 1
                continue

            home_code = resolve_team_code(
                abbr=home.get("team_abbreviation", ""),
                name=home.get("team_name", ""),
                known_codes=known_codes,
            )
            away_code = resolve_team_code(
                abbr=away.get("team_abbreviation", ""),
                name=away.get("team_name", ""),
                known_codes=known_codes,
            )
            if home_code is None or away_code is None:
                meta["skipped"]["unmapped_team"] += 1
                continue
            if home_code == away_code:
                meta["skipped"]["fcs_or_unknown"] += 1
                continue

            week = int(float(b.get("week") or 0))
            games.append(
                HistGame(
                    game_id=gid,
                    season=int(season),
                    week=week,
                    home_code=home_code,
                    away_code=away_code,
                    home_abbr=str(home.get("team_abbreviation") or "").upper(),
                    away_abbr=str(away.get("team_abbreviation") or "").upper(),
                    home_score=int(hs),
                    away_score=int(aws),
                    close_spread_home=spread,
                    close_total=total,
                    home_conference=conference_for(home_code),
                    away_conference=conference_for(away_code),
                )
            )
            meta["mapped_games"] += 1

    return games, meta


def ratings_to_efficiency_map(
    season_prior: int,
    *,
    cache_dir: Optional[Path] = None,
    team_id_to_code: Optional[Mapping[str, str]] = None,
) -> Dict[str, EfficiencyProfile]:
    """Convert prior-year cfb_ratings adj EPA → EfficiencyProfile (0–100)."""
    rows = fetch_sdv_csv(
        "cfb_ratings",
        f"cfb_ratings_{season_prior}.csv",
        cache_dir=cache_dir,
    )
    # Need team_id → code: build from a box season when not provided.
    if team_id_to_code is None:
        box = fetch_sdv_csv(
            "espn_cfb_team_box",
            f"team_box_{season_prior}.csv.gz",
            cache_dir=cache_dir,
        )
        from src.services.cfb_season_engine.loaders import load_packaged_team_priors

        known = load_packaged_team_priors().get("teams") or {}
        tid_map: Dict[str, str] = {}
        for row in box:
            code = resolve_team_code(
                abbr=row.get("team_abbreviation", ""),
                name=row.get("team_name", ""),
                known_codes=known,
            )
            if code:
                tid_map[str(row["team_id"])] = code
        team_id_to_code = tid_map

    off_vals: List[float] = []
    def_vals: List[float] = []
    parsed: List[Tuple[str, float, float, float]] = []
    for r in rows:
        tid = str(r.get("team_id") or "")
        code = team_id_to_code.get(tid)
        if not code:
            continue
        try:
            adj_off = float(r["adj_off_epa"])
            # Lower (more negative) adj_def_epa is better defense in this feed.
            adj_def = float(r["adj_def_epa"])
            adj_net = float(r.get("adj_net") or (adj_off - adj_def))
        except (KeyError, TypeError, ValueError):
            continue
        off_vals.append(adj_off)
        def_vals.append(-adj_def)  # flip so higher = better
        parsed.append((code, adj_off, -adj_def, adj_net))

    def _to_100(val: float, series: Sequence[float]) -> float:
        if not series:
            return 50.0
        mu = statistics.fmean(series)
        sd = statistics.pstdev(series) or 1.0
        # ~N(50, 15) squash
        return max(5.0, min(95.0, 50.0 + 15.0 * (val - mu) / sd))

    out: Dict[str, EfficiencyProfile] = {}
    for code, off_raw, def_raw, net in parsed:
        off_eff = _to_100(off_raw, off_vals)
        def_eff = _to_100(def_raw, def_vals)
        explos = max(5.0, min(95.0, 50.0 + (off_eff - def_eff) * 0.15))
        out[code] = EfficiencyProfile(
            team=code,
            off_eff=off_eff,
            def_eff=def_eff,
            success_off=off_eff,
            success_def=def_eff,
            explosiveness=explos,
            sp_plus=net * 100.0,  # scaled label only
            sp_offense=off_raw,
            sp_defense=-def_raw,
            sp_rank=None,
            prior_year=season_prior,
            carry_to_season=season_prior + 1,
            source=f"cfb_ratings_adj_epa_{season_prior}",
            fidelity="approximate",
            notes=(
                "Prior-year cfb_ratings adj EPA normalized to 0–100 efficiency "
                "proxy for historical reconstruction (not live SP+)."
            ),
        )
    return out


def build_historical_proxy_state(
    code: str,
    efficiency: Optional[EfficiencyProfile],
    *,
    home_field_payload: Optional[Mapping[str, Any]] = None,
) -> TeamProjectionState:
    """League-avg roster/QB/units + prior-year efficiency + curated HFA."""
    roster = build_roster_construction(
        code,
        {
            "returning_production": 50.0,
            "portal_in_value": 50.0,
            "portal_out_value": 50.0,
            "recruiting_class_score": 50.0,
            "experience_index": 50.0,
            "fidelity": "placeholder",
            "source": "historical_reconstruction_league_avg",
            "notes": "Historical roster unavailable; league-average fill.",
        },
        default_source="historical_reconstruction_league_avg",
    )
    groups = build_position_groups(
        code,
        {
            "ol": 50.0,
            "skill": 50.0,
            "front_seven": 50.0,
            "secondary": 50.0,
            "special_teams": 50.0,
            "fidelity": "placeholder",
            "source": "historical_reconstruction_league_avg",
        },
        default_source="historical_reconstruction_league_avg",
    )
    qb = build_qb_situation(
        code,
        {
            "qb_class": "unknown",
            "qb_talent": 50.0,
            "ol_support": 50.0,
            "weapons_support": 50.0,
            "fidelity": "placeholder",
            "source": "historical_reconstruction_league_avg",
            "notes": "Historical QB situation unavailable; unknown @ 50 talent.",
        },
        default_source="historical_reconstruction_league_avg",
        ol_grade=groups.ol,
        skill_grade=groups.skill,
    )
    home_field = build_home_field_profile(code, home_field_payload)
    coaching = build_coaching_continuity(
        code,
        {
            "new_hc": False,
            "new_oc": False,
            "new_dc": False,
            "fidelity": "placeholder",
            "source": "historical_reconstruction_all_returning",
            "notes": "Historical coaching flags not wired; assume returning.",
        },
    )
    eff = efficiency or build_efficiency_profile(code, None)
    return compose_team_projection(
        code,
        roster,
        qb,
        groups,
        efficiency=eff,
        home_field=home_field,
        coaching=coaching,
    )


def build_historical_proxy_universe(
    season: int,
    efficiency_by_code: Mapping[str, EfficiencyProfile],
    *,
    codes: Optional[Iterable[str]] = None,
) -> EngineUniverse:
    """Universe for season Y using Y-1 efficiency + league-avg identity layers."""
    from src.services.cfb_season_engine.loaders import load_packaged_team_priors
    from src.services.cfb_season_engine.conferences import load_conference_map

    priors = load_packaged_team_priors()
    team_codes = list(codes or (priors.get("teams") or {}).keys())
    teams: Dict[str, TeamProjectionState] = {}
    for code in team_codes:
        payload = (priors.get("teams") or {}).get(code) or {}
        teams[code] = build_historical_proxy_state(
            code,
            efficiency_by_code.get(code),
            home_field_payload=payload.get("home_field"),
        )
    return EngineUniverse(
        season=season,
        teams=teams,
        schedule=[],
        conferences=load_conference_map(),
        player_hooks={},
        notes={
            "mode": "historical_proxy",
            "reconstruction": "prior_year_efficiency_league_avg_identity",
            "efficiency_prior_season": str(season - 1),
            "detail": (
                f"Historical proxy universe for {season}: prior-year efficiency "
                f"({season - 1} cfb_ratings) + league-avg roster/QB/units + "
                "curated HFA. Not a full live-hierarchy reconstruction."
            ),
        },
    )


def _safe_mean(xs: Sequence[float]) -> Optional[float]:
    return statistics.fmean(xs) if xs else None


def _rmse(xs: Sequence[float]) -> Optional[float]:
    if not xs:
        return None
    return math.sqrt(statistics.fmean(x * x for x in xs))


def _mae(xs: Sequence[float]) -> Optional[float]:
    return _safe_mean([abs(x) for x in xs])


def grade_projections(
    games: Sequence[HistGame],
    universes: Mapping[int, EngineUniverse],
) -> Dict[str, Any]:
    """Project each game and compute market / outcome metrics."""
    rows: List[Dict[str, Any]] = []
    for g in games:
        universe = universes.get(g.season)
        if universe is None:
            continue
        if g.home_code not in universe.teams or g.away_code not in universe.teams:
            continue
        proj = project_game(
            universe,
            home_team=g.home_code,
            away_team=g.away_code,
            week=g.week,
            season=g.season,
            neutral_site=False,
            engine_version=P.ENGINE_VERSION,
        )
        actual_margin = float(g.home_score - g.away_score)  # home − away
        actual_total = float(g.home_score + g.away_score)
        # Model spread_home: negative when home favored (same as close).
        model_spread = float(proj.spread_home)
        model_total = float(proj.expected_total)
        model_wp = float(proj.home_win_prob)
        close_spread = float(g.close_spread_home)
        close_total = float(g.close_total)

        # ATS vs close: home covers if actual_margin + close_spread > 0
        # (close_spread negative when home favored).
        cover_margin = actual_margin + close_spread
        home_covers = None
        if abs(cover_margin) < 1e-9:
            home_covers = None  # push
        else:
            home_covers = cover_margin > 0

        # Model side vs close: model likes home more if model_spread < close_spread
        # (more negative / smaller).
        model_home_edge = close_spread - model_spread
        model_ats_pick_home = model_home_edge > 0.5  # need ≥0.5 pt edge
        model_ats_pick_away = model_home_edge < -0.5
        ats_hit = None
        if home_covers is not None:
            if model_ats_pick_home:
                ats_hit = bool(home_covers)
            elif model_ats_pick_away:
                ats_hit = not bool(home_covers)

        ou_diff = actual_total - close_total
        over_hit = None if abs(ou_diff) < 1e-9 else ou_diff > 0
        model_over = model_total > close_total + 0.5
        model_under = model_total < close_total - 0.5
        ou_hit = None
        if over_hit is not None:
            if model_over:
                ou_hit = bool(over_hit)
            elif model_under:
                ou_hit = not bool(over_hit)

        home_won = g.home_score > g.away_score
        ml_hit = (model_wp >= 0.5) == home_won
        brier = (model_wp - (1.0 if home_won else 0.0)) ** 2

        fav_home = close_spread < 0
        slice_conf = (
            "P4"
            if g.home_conference in {"SEC", "Big Ten", "ACC", "Big 12"}
            and g.away_conference in {"SEC", "Big Ten", "ACC", "Big 12"}
            else "mixed_or_g5"
        )
        early = g.week <= 4

        rows.append(
            {
                "game_id": g.game_id,
                "season": g.season,
                "week": g.week,
                "home": g.home_code,
                "away": g.away_code,
                "home_score": g.home_score,
                "away_score": g.away_score,
                "actual_margin": actual_margin,
                "actual_total": actual_total,
                "close_spread_home": close_spread,
                "close_total": close_total,
                "model_spread_home": model_spread,
                "model_total": model_total,
                "model_home_wp": model_wp,
                "err_spread_vs_close": model_spread - close_spread,
                "err_spread_vs_actual": model_spread - (-actual_margin),
                # spread convention: model spread ≈ -expected_margin
                "err_margin_vs_actual": (-model_spread) - actual_margin,
                "err_total_vs_close": model_total - close_total,
                "err_total_vs_actual": model_total - actual_total,
                "ats_hit": ats_hit,
                "ou_hit": ou_hit,
                "ml_hit": ml_hit,
                "brier": brier,
                "favorite_home": fav_home,
                "slice_conf": slice_conf,
                "early_season": early,
                "home_conference": g.home_conference,
                "away_conference": g.away_conference,
            }
        )

    return summarize_rows(rows)


def summarize_rows(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    def _slice(pred) -> List[Mapping[str, Any]]:
        return [r for r in rows if pred(r)]

    def _block(subset: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
        if not subset:
            return {"n": 0}
        spread_close_err = [float(r["err_spread_vs_close"]) for r in subset]
        spread_act_err = [float(r["err_margin_vs_actual"]) for r in subset]
        total_close_err = [float(r["err_total_vs_close"]) for r in subset]
        total_act_err = [float(r["err_total_vs_actual"]) for r in subset]
        ats = [r["ats_hit"] for r in subset if r["ats_hit"] is not None]
        ou = [r["ou_hit"] for r in subset if r["ou_hit"] is not None]
        ml = [bool(r["ml_hit"]) for r in subset]
        brier = [float(r["brier"]) for r in subset]
        return {
            "n": len(subset),
            "spread_vs_close_bias": _safe_mean(spread_close_err),
            "spread_vs_close_mae": _mae(spread_close_err),
            "spread_vs_close_rmse": _rmse(spread_close_err),
            "margin_vs_actual_bias": _safe_mean(spread_act_err),
            "margin_vs_actual_mae": _mae(spread_act_err),
            "margin_vs_actual_rmse": _rmse(spread_act_err),
            "total_vs_close_bias": _safe_mean(total_close_err),
            "total_vs_close_mae": _mae(total_close_err),
            "total_vs_close_rmse": _rmse(total_close_err),
            "total_vs_actual_bias": _safe_mean(total_act_err),
            "total_vs_actual_mae": _mae(total_act_err),
            "ats_n": len(ats),
            "ats_hit_rate": (sum(1 for x in ats if x) / len(ats)) if ats else None,
            "ou_n": len(ou),
            "ou_hit_rate": (sum(1 for x in ou if x) / len(ou)) if ou else None,
            "ml_hit_rate": (sum(1 for x in ml if x) / len(ml)) if ml else None,
            "brier_home_wp": _safe_mean(brier),
        }

    overall = _block(rows)
    slices = {
        "early_season_w1_4": _block(_slice(lambda r: r["early_season"])),
        "late_season_w5_plus": _block(_slice(lambda r: not r["early_season"])),
        "home_favorite": _block(_slice(lambda r: r["favorite_home"])),
        "home_dog": _block(_slice(lambda r: not r["favorite_home"])),
        "p4_vs_p4": _block(_slice(lambda r: r["slice_conf"] == "P4")),
        "mixed_or_g5": _block(_slice(lambda r: r["slice_conf"] != "P4")),
    }
    by_season: Dict[str, Any] = {}
    seasons = sorted({int(r["season"]) for r in rows})
    for s in seasons:
        by_season[str(s)] = _block(_slice(lambda r, s=s: int(r["season"]) == s))

    return {
        "engine_version": P.ENGINE_VERSION,
        "calibration_tag": P.CALIBRATION_TAG,
        "n_games": len(rows),
        "overall": overall,
        "slices": slices,
        "by_season": by_season,
        "rows": list(rows),
        "reconstruction_limits": [
            "Prior-year cfb_ratings adj EPA stands in for SP+ efficiency.",
            "Roster / QB / position groups forced to league-average (no hist roster).",
            "Coaching flags assumed all-returning.",
            "HFA from curated 2026 venue proxies (not season-Y home splits).",
            "ESPN betting lines are resolved closing-ish (core_odds_api / pickcenter).",
            "Team-code mapping aliases some missing FBS codes onto peers — skip when both unmapped.",
        ],
    }


def run_historical_backtest(
    *,
    seasons: Sequence[int] = (2022, 2023, 2024, 2025),
    cache_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """End-to-end: load games, build proxy universes, grade."""
    games, load_meta = load_historical_games(seasons, cache_dir=cache_dir)
    codes_by_season: Dict[int, set] = defaultdict(set)
    for g in games:
        codes_by_season[g.season].add(g.home_code)
        codes_by_season[g.season].add(g.away_code)
    universes: Dict[int, EngineUniverse] = {}
    eff_meta: Dict[str, Any] = {}
    for season in seasons:
        prior = season - 1
        eff = ratings_to_efficiency_map(prior, cache_dir=cache_dir)
        codes = set(eff) | set(codes_by_season.get(season) or ())
        universes[season] = build_historical_proxy_universe(
            season, eff, codes=sorted(codes)
        )
        eff_meta[str(season)] = {
            "prior_ratings_year": prior,
            "teams_with_efficiency": len(eff),
            "universe_teams": len(codes),
        }
    graded = grade_projections(games, universes)
    # Drop bulky rows from top-level summary copy callers can keep.
    summary = {k: v for k, v in graded.items() if k != "rows"}
    return {
        "load": load_meta,
        "efficiency": eff_meta,
        "metrics": summary,
        "rows": graded.get("rows") or [],
        "priors_snapshot": {
            "ENGINE_VERSION": P.ENGINE_VERSION,
            "CALIBRATION_TAG": P.CALIBRATION_TAG,
            "HFA_BASELINE_POINTS": P.HFA_BASELINE_POINTS,
            "LEAGUE_TEAM_PPG": P.LEAGUE_TEAM_PPG,
            "MATCHUP_RESPONSE": P.MATCHUP_RESPONSE,
            "MATCHUP_RATIO_CLAMP": list(P.MATCHUP_RATIO_CLAMP),
            "WEIGHT_OFF_EFF": P.WEIGHT_OFF_EFF,
            "WEIGHT_DEF_EFF": P.WEIGHT_DEF_EFF,
            "EARLY_SEASON_SEPARATION_SOFTEN": dict(P.EARLY_SEASON_SEPARATION_SOFTEN),
            "EARLY_SEASON_MARGIN_SD_MULT": dict(P.EARLY_SEASON_MARGIN_SD_MULT),
            "WIN_PROB_MARGIN_SD": P.WIN_PROB_MARGIN_SD,
        },
    }


def documentation() -> Dict[str, Any]:
    return {
        "module": "historical_calibration",
        "data": "sportsdataverse espn_cfb_betting/team_box/linescores + cfb_ratings",
        "credits": "no_odds_api",
        "fidelity": "approximate_reconstruction",
    }
