"""CFB Data Layer v2 — point-in-time scoring-environment features.

Research only. Does not touch α, A1, E3, C2, MATCHUP_RESPONSE, or production.

Built from owned SportsDataverse PBP (2021–2024) plus Layer A QB and
prior-year / current-season schedule scores. 2025 is never opened.
Missing means missing: no 50-fills, no synthetic explosiveness, no
season aggregates that include the target game.

Every snapshot carries as_of_week / max_week_included / availability.
Week W current-season stats use only same-season plays with week < W.
Prior-year stats use the completed Y−1 season only.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.qb_feature_contract import (
    QB_FEATURE_CONTRACT_VERSION,
)
from src.services.cfb_season_engine.team_features import (
    CFB_EDGE_BOARD_PUBLIC_ENABLED,
)
from src.services.cfb_warehouse.efficiency_adj import iterative_adjust
from src.services.cfb_warehouse.frozen_140_scoring import (
    LEGAL_SEASONS,
    FrozenScoringError,
    _eligible,
    assert_frozen_priors,
    load_layer_a,
    load_legal_scoring_bundle,
    refuse_sealed_or_confirm,
)
from src.services.cfb_warehouse.garbage import weight_play
from src.services.cfb_warehouse.high_env_information import (
    HIGH_ENV_THRESHOLD,
    _mean,
    _oriented,
    _pct_ranks,
    average_precision,
    decile_card,
    load_current_env,
    load_prior_env,
    roc_auc,
)
from src.services.cfb_warehouse.identity import known_engine_codes, resolve_team_code
from src.services.cfb_warehouse.matchup_architecture_holdout import (
    FROZEN_BASELINE,
    PROTOCOL_SPLITS,
    _split_rows,
)
from src.services.cfb_warehouse.paths import clean_dir, hd_mounted, pbp_raw_dir

LEGAL_PBP_SEASONS = (2021, 2022, 2023, 2024)  # 2021 is prior-year only for Train-0
MIN_CURRENT_GAMES = 2
CHAIN_WEEKS = tuple(range(1, 15))

# Offensive scoring-drive decode. drive.pts is absent; this is the owned
# result field, not a stand-in for a missing explosiveness series.
OFFENSIVE_DRIVE_POINTS = {"TD": 6.0, "FG": 3.0}

PBP_COLS = (
    "season",
    "week",
    "game_id",
    "pos_team",
    "def_pos_team",
    "scrimmage_play",
    "pass",
    "rush",
    "EPA",
    "EPA_success",
    "EPA_explosive",
    "EPA_explosive_pass",
    "EPA_explosive_rush",
    "statYardage",
    "rz_play",
    "stuffed_run",
    "under_2",
    "start.TimeSecsRem",
    "end.TimeSecsRem",
    "pos_score_diff",
    "period",
    "half",
    "sack",
    "TFL",
    "havoc",
    "is_turnover",
    "drive.id",
    "drive.isScore",
    "drive.result",
)

LAYER_B_GAP = {
    "id": "layer_b_returning_units_coaching",
    "status": "SOURCE_GAP",
    "why": (
        "Historical returning production, unit grades, and coaching flags "
        "are not in-repo. The 2026 real-roster snapshot is the wrong year "
        "and must not be back-cast. Missing, not filled with 50."
    ),
}

SOURCE_GAPS: Tuple[Dict[str, str], ...] = (
    LAYER_B_GAP,
    {
        "id": "drive_pts",
        "status": "SOURCE_GAP",
        "why": (
            "drive.pts is not in the raw PBP. Finishing uses drive.result "
            "(TD=6, FG=3). PAT / two-point conversion points are not observed."
        ),
    },
    {
        "id": "injuries_weather",
        "status": "SOURCE_GAP",
        "why": "No point-in-time injury or weather series in the owned lake.",
    },
    {
        "id": "historical_roster_snapshots",
        "status": "SOURCE_GAP",
        "why": "No week-indexed returning-production files for 2021–2024.",
    },
)

# Stability is “better than chance, same direction, all three windows.”
# Not a capture target. Do not shop this after seeing scores.
STABLE_AUC = 0.55
PBP_FAMILIES = frozenset(
    {
        "curr_epa",
        "curr_interaction",
        "curr_explosive",
        "curr_success",
        "curr_havoc",
        "curr_pace",
        "curr_finish",
        "prior_epa",
        "prior_explosive",
        "prior_pace",
        "prior_finish",
    }
)


def refuse_sealed_pbp(seasons: Iterable[int]) -> None:
    bad = [int(s) for s in seasons if int(s) >= 2025]
    if bad:
        raise FrozenScoringError(
            f"refusing PBP seasons {bad}; 2025 sealed, 2026 not in the loss"
        )


def classify_drive(result: Any) -> Optional[Tuple[float, bool]]:
    """Return (offensive points, scored?) or None if the result is unusable."""
    if result is None or result == "":
        return None
    key = str(result).strip().upper()
    if key in {"NOT PROVIDED", "NAN", "NONE", "<NA>"}:
        return None
    if key in OFFENSIVE_DRIVE_POINTS:
        return OFFENSIVE_DRIVE_POINTS[key], True
    return 0.0, False


def _truthy(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if raw in (None, "", 0, "0"):
        return False
    return str(raw).lower() in {"1", "true", "t", "yes"}


def _f(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(val):
        return None
    return val


def _half(play: Mapping[str, Any]) -> int:
    if play.get("half") not in (None, ""):
        try:
            n = int(float(play.get("half")))
        except (TypeError, ValueError):
            return 2
        return 1 if n <= 1 else 2
    raw = play.get("period")
    try:
        n = int(float(raw))
    except (TypeError, ValueError):
        return 2
    return 1 if n <= 2 else 2


def _team(name: Any, known: Mapping[str, Any]) -> Tuple[str, bool]:
    label = str(name or "").strip()
    if not label or label.lower() in {"nan", "none", "nat", "<na>"}:
        return "", True
    code = resolve_team_code(name=label, abbr="", known_codes=known)
    if code:
        return code, False
    return f"fcs:{label}", True


def pbp_path(season: int, *, prefer_hd: bool = True) -> Path:
    refuse_sealed_pbp([season])
    raw = pbp_raw_dir(prefer_hd=prefer_hd) / f"play_by_play_{int(season)}.parquet"
    if "2025" in raw.name or "2026" in raw.name:
        raise FrozenScoringError(f"refusing sealed PBP path {raw}")
    if not raw.exists():
        raise FileNotFoundError(f"missing raw PBP for {season}: {raw}")
    return raw


def load_pbp_legal(season: int, *, prefer_hd: bool = True):
    import pyarrow.parquet as pq

    path = pbp_path(season, prefer_hd=prefer_hd)
    available = set(pq.ParquetFile(path).schema.names)
    cols = [c for c in PBP_COLS if c in available]
    missing = [c for c in PBP_COLS if c not in available]
    table = pq.read_table(path, columns=cols)
    return table.to_pylist(), {
        "path": str(path),
        "rows": table.num_rows,
        "cols_used": cols,
        "cols_requested_missing": missing,
        "has": {c: c in available for c in PBP_COLS},
    }


def _rate(present: bool, num: float, den: float) -> Optional[float]:
    if not present or den <= 0:
        return None
    return num / den


def aggregate_team_games(
    plays: Sequence[Mapping[str, Any]],
    *,
    known: Mapping[str, Any],
    available_cols: Optional[Sequence[str]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """One row per (game, offense team) plus matching defense rates."""
    cols = set(available_cols or [])
    if not cols and plays:
        cols = set(plays[0].keys())
    has = {c: c in cols for c in PBP_COLS}
    off: Dict[Tuple[Any, ...], Dict[str, float]] = {}
    meta: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    drives: Dict[Tuple[str, str], Dict[str, Any]] = {}
    col_hits = {c: 0 for c in ("havoc", "TFL", "sack", "EPA_explosive", "drive.result", "end.TimeSecsRem")}
    n_fcs = 0

    for play in plays:
        play = dict(play)
        play["half"] = _half(play)
        if play.get("scrimmage_play") is not None and not _truthy(play.get("scrimmage_play")):
            continue
        epa = _f(play.get("EPA"))
        if epa is None:
            continue
        off_id, fcs_off = _team(play.get("pos_team"), known)
        def_id, fcs_def = _team(play.get("def_pos_team"), known)
        if not off_id or not def_id:
            continue
        if fcs_off:
            n_fcs += 1
        w = weight_play(play)
        if w <= 0:
            continue
        gid = str(play.get("game_id") or "")
        season = int(_f(play.get("season")) or 0)
        week = int(_f(play.get("week")) or 0)
        if season >= 2025:
            raise FrozenScoringError("2025/2026 play leaked into data layer v2")
        key = (season, week, gid, off_id, def_id)
        acc = off.setdefault(
            key,
            {
                "w": 0.0,
                "n": 0.0,
                "epa": 0.0,
                "success": 0.0,
                "explosive": 0.0,
                "pass_w": 0.0,
                "pass_expl": 0.0,
                "rush_w": 0.0,
                "rush_expl": 0.0,
                "havoc_allowed": 0.0,
                "tfl_allowed": 0.0,
                "sack_allowed": 0.0,
                "to_allowed": 0.0,
                "rz_w": 0.0,
                "rz_epa": 0.0,
                "sec": 0.0,
                "sec_n": 0.0,
                "sit_w": 0.0,
            },
        )
        acc["w"] += w
        acc["n"] += 1.0
        acc["epa"] += w * epa
        if has["EPA_success"] and _truthy(play.get("EPA_success")):
            acc["success"] += w
        if has["EPA_explosive"]:
            if play.get("EPA_explosive") is not None:
                col_hits["EPA_explosive"] += 1
            if _truthy(play.get("EPA_explosive")):
                acc["explosive"] += w
        if has["EPA_explosive_pass"] and _truthy(play.get("EPA_explosive_pass")):
            acc["pass_expl"] += w
        elif has["EPA_explosive"] and _truthy(play.get("EPA_explosive")) and _truthy(play.get("pass")):
            acc["pass_expl"] += w
        if has["EPA_explosive_rush"] and _truthy(play.get("EPA_explosive_rush")):
            acc["rush_expl"] += w
        elif has["EPA_explosive"] and _truthy(play.get("EPA_explosive")) and _truthy(play.get("rush")):
            acc["rush_expl"] += w
        if _truthy(play.get("pass")):
            acc["pass_w"] += w
        if _truthy(play.get("rush")):
            acc["rush_w"] += w
        if has["havoc"]:
            if play.get("havoc") is not None:
                col_hits["havoc"] += 1
            if _truthy(play.get("havoc")):
                acc["havoc_allowed"] += w
        if has["TFL"]:
            if play.get("TFL") is not None:
                col_hits["TFL"] += 1
            if _truthy(play.get("TFL")):
                acc["tfl_allowed"] += w
        if has["sack"]:
            if play.get("sack") is not None:
                col_hits["sack"] += 1
            if _truthy(play.get("sack")):
                acc["sack_allowed"] += w
        if has["is_turnover"] and _truthy(play.get("is_turnover")):
            acc["to_allowed"] += w
        if _truthy(play.get("rz_play")):
            acc["rz_w"] += w
            acc["rz_epa"] += w * epa
        start_t = _f(play.get("start.TimeSecsRem"))
        end_t = _f(play.get("end.TimeSecsRem"))
        if has["end.TimeSecsRem"] and start_t is not None and end_t is not None:
            col_hits["end.TimeSecsRem"] += 1
            dt = start_t - end_t
            if 0.0 < dt <= 45.0:
                acc["sec"] += dt
                acc["sec_n"] += 1.0
        if has["under_2"] and not _truthy(play.get("under_2")):
            acc["sit_w"] += w
        did = str(play.get("drive.id") or "")
        if did and has["drive.result"]:
            dkey = (gid, did)
            if dkey not in drives:
                drives[dkey] = {
                    "team": off_id,
                    "season": season,
                    "week": week,
                    "pts": None,
                    "scored": None,
                }
            classified = classify_drive(play.get("drive.result"))
            if classified is not None:
                col_hits["drive.result"] += 1
                drives[dkey]["pts"] = classified[0]
                drives[dkey]["scored"] = classified[1]
        meta[key] = {
            "season": season,
            "week": week,
            "game_id": gid,
            "team_id": off_id,
            "opponent_id": def_id,
            "fcs_offense": fcs_off,
            "fcs_defense": fcs_def,
            "fcs_opponent": fcs_off or fcs_def,
        }

    finish: Dict[Tuple[int, int, str], List[float]] = defaultdict(list)
    ppp: Dict[Tuple[int, int, str], List[float]] = defaultdict(list)
    for _key, d in drives.items():
        if d.get("scored") is None or d.get("pts") is None:
            continue
        tk = (int(d["season"]), int(d["week"]), str(d["team"]))
        finish[tk].append(1.0 if d["scored"] else 0.0)
        ppp[tk].append(float(d["pts"]))

    rows: List[Dict[str, Any]] = []
    for key, acc in off.items():
        info = meta[key]
        w = acc["w"] or 1.0
        tk = (info["season"], info["week"], info["team_id"])
        rows.append(
            {
                **info,
                "n_plays": int(acc["n"]),
                "n_plays_weighted": round(w, 3),
                "off_epa_raw": acc["epa"] / w,
                "off_success_raw": _rate(has["EPA_success"], acc["success"], w),
                "off_explosive_rate": _rate(has["EPA_explosive"], acc["explosive"], w),
                "off_pass_explosive_rate": _rate(
                    has["EPA_explosive"] or has["EPA_explosive_pass"],
                    acc["pass_expl"],
                    acc["pass_w"],
                ),
                "off_rush_explosive_rate": _rate(
                    has["EPA_explosive"] or has["EPA_explosive_rush"],
                    acc["rush_expl"],
                    acc["rush_w"],
                ),
                "havoc_allowed": _rate(has["havoc"], acc["havoc_allowed"], w),
                "tfl_allowed": _rate(has["TFL"], acc["tfl_allowed"], w),
                "sack_allowed": _rate(has["sack"], acc["sack_allowed"], w),
                "turnover_allowed": _rate(has["is_turnover"], acc["to_allowed"], w),
                "rz_epa_raw": (acc["rz_epa"] / acc["rz_w"]) if acc["rz_w"] else None,
                "seconds_per_play": (acc["sec"] / acc["sec_n"]) if acc["sec_n"] else None,
                "sit_plays": acc["sit_w"] if has["under_2"] else None,
                "finish_rate": statistics.fmean(finish[tk]) if finish.get(tk) else None,
                "ppp": statistics.fmean(ppp[tk]) if ppp.get(tk) else None,
            }
        )
    return rows, {
        "col_hits": col_hits,
        "n_team_games": len(rows),
        "n_drives": len(drives),
        "n_fcs_offense_plays": n_fcs,
        "has_columns": has,
        "explosive_definition": (
            "EPA_explosive boolean from raw SDV PBP. No epa>=1.0 / yards>=15 fallback."
            if has["EPA_explosive"]
            else "MISSING: EPA_explosive column absent"
        ),
    }


def _mean_or_none(rows: Sequence[Mapping[str, Any]], key: str) -> Optional[float]:
    xs = [float(r[key]) for r in rows if r.get(key) is not None]
    return statistics.fmean(xs) if xs else None


def snapshot_team(
    games: Sequence[Mapping[str, Any]],
    *,
    season: int,
    week: int,
    team: str,
    adj: Mapping[str, Mapping[str, float]],
    source: str,
) -> Dict[str, Any]:
    prior = [
        r
        for r in games
        if int(r["season"]) == int(season)
        and int(r["week"]) < int(week)
        and str(r["team_id"]) == team
    ]
    faced = [
        r
        for r in games
        if int(r["season"]) == int(season)
        and int(r["week"]) < int(week)
        and str(r["opponent_id"]) == team
    ]
    max_included = max((int(r["week"]) for r in prior), default=0)
    n = len(prior)
    present = n >= MIN_CURRENT_GAMES if source == "current_season" else n >= 1
    availability = (
        "PRESENT"
        if present
        else (
            "MISSING_COLD_START"
            if source == "current_season" and n == 0
            else "MISSING_THIN_SAMPLE"
        )
    )
    stats = adj.get(team) or {}
    row = {
        "season": int(season),
        "as_of_week": int(week),
        "feature_week": int(max_included),
        "max_week_included": int(max_included),
        "team_id": team,
        "source": source,
        "n_games": n,
        "n_plays": sum(int(r.get("n_plays") or 0) for r in prior),
        "availability": availability,
        "available": present,
        "off_epa_adj": float(stats["off_epa_adj"]) if present and stats.get("off_epa_adj") is not None else None,
        "def_epa_adj": float(stats["def_epa_adj"]) if present and stats.get("def_epa_adj") is not None else None,
        "off_epa_raw": _mean_or_none(prior, "off_epa_raw") if present else None,
        "def_epa_raw": _mean_or_none(faced, "off_epa_raw") if present else None,
        "off_success": _mean_or_none(prior, "off_success_raw") if present else None,
        "def_success_allowed": _mean_or_none(faced, "off_success_raw") if present else None,
        "explosive_created": _mean_or_none(prior, "off_explosive_rate") if present else None,
        "explosive_allowed": _mean_or_none(faced, "off_explosive_rate") if present else None,
        "explosive_pass_created": _mean_or_none(prior, "off_pass_explosive_rate") if present else None,
        "explosive_rush_created": _mean_or_none(prior, "off_rush_explosive_rate") if present else None,
        "havoc_created": _mean_or_none(faced, "havoc_allowed") if present else None,
        "havoc_allowed": _mean_or_none(prior, "havoc_allowed") if present else None,
        "tfl_created": _mean_or_none(faced, "tfl_allowed") if present else None,
        "sack_created": _mean_or_none(faced, "sack_allowed") if present else None,
        "turnover_created": _mean_or_none(faced, "turnover_allowed") if present else None,
        "finish_rate": _mean_or_none(prior, "finish_rate") if present else None,
        "finish_allowed": _mean_or_none(faced, "finish_rate") if present else None,
        "ppp": _mean_or_none(prior, "ppp") if present else None,
        "ppp_allowed": _mean_or_none(faced, "ppp") if present else None,
        "rz_epa": _mean_or_none(prior, "rz_epa_raw") if present else None,
        "pace_plays": _mean_or_none(prior, "n_plays") if present else None,
        "sit_pace_plays": _mean_or_none(prior, "sit_plays") if present else None,
        "seconds_per_play": _mean_or_none(prior, "seconds_per_play") if present else None,
    }
    if row["max_week_included"] >= int(week) and source == "current_season":
        raise FrozenScoringError(
            f"PIT leak: season {season} week {week} included week {row['max_week_included']}"
        )
    if not present:
        for key in (
            "off_epa_adj",
            "def_epa_adj",
            "off_epa_raw",
            "def_epa_raw",
            "off_success",
            "def_success_allowed",
            "explosive_created",
            "explosive_allowed",
            "havoc_created",
            "finish_rate",
            "ppp",
            "pace_plays",
        ):
            if row[key] is not None:
                raise FrozenScoringError(f"missing snapshot leaked a value for {key}")
    return row


def build_season_snapshots(
    games: Sequence[Mapping[str, Any]],
    *,
    season: int,
) -> List[Dict[str, Any]]:
    refuse_sealed_pbp([season])
    teams = sorted(
        {
            str(r["team_id"])
            for r in games
            if int(r["season"]) == season and not str(r["team_id"]).startswith("fcs:")
        }
    )
    out: List[Dict[str, Any]] = []
    for week in CHAIN_WEEKS:
        prior = [r for r in games if int(r["season"]) == season and int(r["week"]) < week]
        adj = iterative_adjust(prior) if prior else {}
        for team in teams:
            out.append(
                snapshot_team(
                    games, season=season, week=week, team=team, adj=adj, source="current_season"
                )
            )
    return out


def season_final(games: Sequence[Mapping[str, Any]], *, season: int) -> Dict[str, Dict[str, Any]]:
    """Completed season Y snapshot, legal as a prior for season Y+1 week 1+."""
    refuse_sealed_pbp([season])
    teams = sorted(
        {
            str(r["team_id"])
            for r in games
            if int(r["season"]) == season and not str(r["team_id"]).startswith("fcs:")
        }
    )
    prior = [r for r in games if int(r["season"]) == season]
    adj = iterative_adjust(prior) if prior else {}
    out: Dict[str, Dict[str, Any]] = {}
    for team in teams:
        row = snapshot_team(
            games,
            season=season,
            week=99,
            team=team,
            adj=adj,
            source="prior_season_final",
        )
        row["as_of_week"] = None
        row["available_for_season"] = season + 1
        out[team] = row
    return out


def cache_dir(*, prefer_hd: bool = True) -> Path:
    root = clean_dir(prefer_hd=prefer_hd) / "data_layer_v2"
    root.mkdir(parents=True, exist_ok=True)
    return root


def build_data_layer_v2(*, prefer_hd: bool = True) -> Dict[str, Any]:
    assert_frozen_priors()
    refuse_sealed_or_confirm(LEGAL_SEASONS)
    refuse_sealed_pbp(LEGAL_PBP_SEASONS)
    if not hd_mounted() and prefer_hd:
        prefer_hd = False
    known = known_engine_codes()
    games: List[Dict[str, Any]] = []
    source_meta: Dict[str, Any] = {}
    for season in LEGAL_PBP_SEASONS:
        plays, meta = load_pbp_legal(season, prefer_hd=prefer_hd)
        if "2025" in str(meta.get("path") or "") or "2026" in str(meta.get("path") or ""):
            raise FrozenScoringError(f"sealed PBP path leaked: {meta.get('path')}")
        team_games, agg_meta = aggregate_team_games(
            plays, known=known, available_cols=meta.get("cols_used")
        )
        games.extend(team_games)
        source_meta[str(season)] = {**meta, **agg_meta}

    current: Dict[Tuple[int, int, str], Dict[str, Any]] = {}
    for season in LEGAL_SEASONS:
        for row in build_season_snapshots(games, season=season):
            current[(season, int(row["as_of_week"]), str(row["team_id"]))] = row

    prior_final: Dict[int, Dict[str, Dict[str, Any]]] = {}
    for season in LEGAL_PBP_SEASONS:
        prior_final[season] = season_final(games, season=season)

    dest = cache_dir(prefer_hd=prefer_hd)
    (dest / "inventory.json").write_text(
        json.dumps(
            {
                "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "legal_pbp_seasons": list(LEGAL_PBP_SEASONS),
                "opened_2025": False,
                "n_team_games": len(games),
                "n_current_snapshots": len(current),
                "source_meta": {
                    season: {
                        k: v
                        for k, v in meta.items()
                        if k != "has"
                    }
                    for season, meta in source_meta.items()
                },
                "layer_b": LAYER_B_GAP,
                "source_gaps": list(SOURCE_GAPS),
                "pit": "current as_of_week W uses only week < W; prior is Y-1 final",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "games": games,
        "current": current,
        "prior_final": prior_final,
        "source_meta": source_meta,
        "cache_dir": str(dest),
        "layer_b": LAYER_B_GAP,
        "source_gaps": list(SOURCE_GAPS),
    }


def _pair(a: Optional[float], b: Optional[float], fn) -> Optional[float]:
    if a is None or b is None:
        return None
    return fn(float(a), float(b))


def game_features(
    raw: Mapping[str, Any],
    *,
    layer: Mapping[str, Any],
    layer_a: Mapping[int, Mapping[str, Any]],
    universes: Mapping[int, Any],
    prior_env: Mapping[int, Mapping[str, Mapping[str, float]]],
    current_env: Optional[Mapping[int, Mapping[Tuple[str, int], Mapping[str, float]]]] = None,
) -> Optional[Dict[str, Any]]:
    season = int(raw["season"])
    week = int(raw["week"])
    home = str(raw["home_team_id"])
    away = str(raw["away_team_id"])
    hs = raw.get("home_score")
    aws = raw.get("away_score")
    if hs is None or aws is None:
        return None
    actual_total = float(int(hs) + int(aws))
    cur = layer["current"]
    prior = (layer["prior_final"].get(season - 1) or {})
    h = cur.get((season, week, home)) or {}
    a = cur.get((season, week, away)) or {}
    hp = prior.get(home) or {}
    ap = prior.get(away) or {}
    henv = (prior_env.get(season - 1) or {}).get(home) or {}
    aenv = (prior_env.get(season - 1) or {}).get(away) or {}
    hc = ((current_env or {}).get(season) or {}).get((home, week)) or {}
    ac = ((current_env or {}).get(season) or {}).get((away, week)) or {}
    hla = ((layer_a.get(season) or {}).get("teams") or {}).get(home) or {}
    ala = ((layer_a.get(season) or {}).get("teams") or {}).get(away) or {}
    hu = universes.get(season).teams.get(home) if universes.get(season) else None
    au = universes.get(season).teams.get(away) if universes.get(season) else None

    def g(row: Mapping[str, Any], key: str) -> Optional[float]:
        if not row.get("available"):
            return None
        return _f(row.get(key))

    feats: Dict[str, Optional[float]] = {
        "curr_sum_off_epa": _pair(g(h, "off_epa_adj"), g(a, "off_epa_adj"), lambda x, y: x + y),
        "curr_sum_def_epa": _pair(g(h, "def_epa_adj"), g(a, "def_epa_adj"), lambda x, y: x + y),
        "curr_max_off_minus_opp_def": _pair(
            _pair(g(h, "off_epa_adj"), g(a, "def_epa_adj"), lambda o, d: o - d),
            _pair(g(a, "off_epa_adj"), g(h, "def_epa_adj"), lambda o, d: o - d),
            max,
        ),
        "curr_product_mismatch": _pair(
            _pair(g(h, "off_epa_adj"), g(a, "def_epa_adj"), lambda o, d: o - d),
            _pair(g(a, "off_epa_adj"), g(h, "def_epa_adj"), lambda o, d: o - d),
            lambda x, y: x * y,
        ),
        "curr_sum_explosive_created": _pair(
            g(h, "explosive_created"), g(a, "explosive_created"), lambda x, y: x + y
        ),
        "curr_sum_explosive_allowed": _pair(
            g(h, "explosive_allowed"), g(a, "explosive_allowed"), lambda x, y: x + y
        ),
        "curr_sum_explosive_pass": _pair(
            g(h, "explosive_pass_created"), g(a, "explosive_pass_created"), lambda x, y: x + y
        ),
        "curr_sum_explosive_rush": _pair(
            g(h, "explosive_rush_created"), g(a, "explosive_rush_created"), lambda x, y: x + y
        ),
        "curr_sum_success_off": _pair(g(h, "off_success"), g(a, "off_success"), lambda x, y: x + y),
        "curr_sum_success_allowed": _pair(
            g(h, "def_success_allowed"), g(a, "def_success_allowed"), lambda x, y: x + y
        ),
        "curr_sum_havoc_created": _pair(
            g(h, "havoc_created"), g(a, "havoc_created"), lambda x, y: x + y
        ),
        "curr_sum_tfl_created": _pair(g(h, "tfl_created"), g(a, "tfl_created"), lambda x, y: x + y),
        "curr_sum_sack_created": _pair(
            g(h, "sack_created"), g(a, "sack_created"), lambda x, y: x + y
        ),
        "curr_sum_turnover_created": _pair(
            g(h, "turnover_created"), g(a, "turnover_created"), lambda x, y: x + y
        ),
        "curr_sum_pace_plays": _pair(g(h, "pace_plays"), g(a, "pace_plays"), lambda x, y: x + y),
        "curr_sum_sit_pace": _pair(
            g(h, "sit_pace_plays"), g(a, "sit_pace_plays"), lambda x, y: x + y
        ),
        "curr_mean_sec_per_play": _pair(
            g(h, "seconds_per_play"), g(a, "seconds_per_play"), lambda x, y: 0.5 * (x + y)
        ),
        "curr_sum_finish": _pair(g(h, "finish_rate"), g(a, "finish_rate"), lambda x, y: x + y),
        "curr_sum_finish_allowed": _pair(
            g(h, "finish_allowed"), g(a, "finish_allowed"), lambda x, y: x + y
        ),
        "curr_sum_ppp": _pair(g(h, "ppp"), g(a, "ppp"), lambda x, y: x + y),
        "curr_sum_ppp_allowed": _pair(g(h, "ppp_allowed"), g(a, "ppp_allowed"), lambda x, y: x + y),
        "curr_sum_rz_epa": _pair(g(h, "rz_epa"), g(a, "rz_epa"), lambda x, y: x + y),
        "curr_two_fast": _pair(g(h, "pace_plays"), g(a, "pace_plays"), min),
        "curr_two_explosive": _pair(
            g(h, "explosive_created"), g(a, "explosive_created"), min
        ),
        "curr_mean_game_total": _pair(
            hc.get("mean_total"), ac.get("mean_total"), lambda x, y: 0.5 * (x + y)
        ),
        "curr_high_env_rate": _pair(
            hc.get("high_env_rate"), ac.get("high_env_rate"), lambda x, y: 0.5 * (x + y)
        ),
        "prior_sum_off_epa": _pair(g(hp, "off_epa_adj"), g(ap, "off_epa_adj"), lambda x, y: x + y),
        "prior_sum_def_epa": _pair(g(hp, "def_epa_adj"), g(ap, "def_epa_adj"), lambda x, y: x + y),
        "prior_sum_explosive_created": _pair(
            g(hp, "explosive_created"), g(ap, "explosive_created"), lambda x, y: x + y
        ),
        "prior_sum_explosive_allowed": _pair(
            g(hp, "explosive_allowed"), g(ap, "explosive_allowed"), lambda x, y: x + y
        ),
        "prior_sum_pace": _pair(g(hp, "pace_plays"), g(ap, "pace_plays"), lambda x, y: x + y),
        "prior_sum_finish": _pair(g(hp, "finish_rate"), g(ap, "finish_rate"), lambda x, y: x + y),
        "prior_mean_game_total": _pair(
            henv.get("mean_total"), aenv.get("mean_total"), lambda x, y: 0.5 * (x + y)
        ),
        "prior_high_env_rate": _pair(
            henv.get("high_env_rate"), aenv.get("high_env_rate"), lambda x, y: 0.5 * (x + y)
        ),
        "sum_qb_talent": _pair(_f(hla.get("qb_talent")), _f(ala.get("qb_talent")), lambda x, y: x + y),
        "layer_b_returning": None,
        "close_total": _f(raw.get("close_total")),
        "v1_sum_off_eff": None,
        "v1_e3_proxy": None,
    }
    if hu and au and hu.efficiency and au.efficiency:
        ho, hd = float(hu.efficiency.off_eff), float(hu.efficiency.def_eff)
        ao, ad = float(au.efficiency.off_eff), float(au.efficiency.def_eff)
        feats["v1_sum_off_eff"] = ho + ao
        h_idx = 1.0 + (ho - 50.0) / P.SCORE_TO_INDEX_DIVISOR
        a_def = 1.0 + (ad - 50.0) / P.SCORE_TO_INDEX_DIVISOR
        a_idx = 1.0 + (ao - 50.0) / P.SCORE_TO_INDEX_DIVISOR
        h_def = 1.0 + (hd - 50.0) / P.SCORE_TO_INDEX_DIVISOR
        feats["v1_e3_proxy"] = P.LEAGUE_TEAM_PPG * (
            h_idx / max(0.50, a_def) + a_idx / max(0.50, h_def)
        )
    return {
        "season": season,
        "week": week,
        "home": home,
        "away": away,
        "actual_total": actual_total,
        "high_env": 1 if actual_total >= HIGH_ENV_THRESHOLD else 0,
        "curr_home_available": bool(h.get("available")),
        "curr_away_available": bool(a.get("available")),
        "curr_both_available": bool(h.get("available") and a.get("available")),
        "prior_both_available": bool(hp.get("available") and ap.get("available")),
        "features": feats,
    }


FEATURE_SPECS: Tuple[Dict[str, Any], ...] = (
    {"id": "curr_sum_off_epa", "family": "curr_epa", "dir": 1, "role": "v2"},
    {"id": "curr_sum_def_epa", "family": "curr_epa", "dir": 1, "role": "v2"},
    {"id": "curr_max_off_minus_opp_def", "family": "curr_interaction", "dir": 1, "role": "v2"},
    {"id": "curr_product_mismatch", "family": "curr_interaction", "dir": 1, "role": "v2"},
    {"id": "curr_sum_explosive_created", "family": "curr_explosive", "dir": 1, "role": "v2"},
    {"id": "curr_sum_explosive_allowed", "family": "curr_explosive", "dir": 1, "role": "v2"},
    {"id": "curr_sum_explosive_pass", "family": "curr_explosive", "dir": 1, "role": "v2"},
    {"id": "curr_sum_explosive_rush", "family": "curr_explosive", "dir": 1, "role": "v2"},
    {"id": "curr_sum_success_off", "family": "curr_success", "dir": 1, "role": "v2"},
    {"id": "curr_sum_success_allowed", "family": "curr_success", "dir": 1, "role": "v2"},
    {"id": "curr_sum_havoc_created", "family": "curr_havoc", "dir": -1, "role": "v2"},
    {"id": "curr_sum_tfl_created", "family": "curr_havoc", "dir": -1, "role": "v2"},
    {"id": "curr_sum_sack_created", "family": "curr_havoc", "dir": -1, "role": "v2"},
    {"id": "curr_sum_turnover_created", "family": "curr_havoc", "dir": -1, "role": "v2"},
    {"id": "curr_sum_pace_plays", "family": "curr_pace", "dir": 1, "role": "v2"},
    {"id": "curr_sum_sit_pace", "family": "curr_pace", "dir": 1, "role": "v2"},
    {"id": "curr_mean_sec_per_play", "family": "curr_pace", "dir": -1, "role": "v2"},
    {"id": "curr_sum_finish", "family": "curr_finish", "dir": 1, "role": "v2"},
    {"id": "curr_sum_finish_allowed", "family": "curr_finish", "dir": 1, "role": "v2"},
    {"id": "curr_sum_ppp", "family": "curr_finish", "dir": 1, "role": "v2"},
    {"id": "curr_sum_ppp_allowed", "family": "curr_finish", "dir": 1, "role": "v2"},
    {"id": "curr_sum_rz_epa", "family": "curr_finish", "dir": 1, "role": "v2"},
    {"id": "curr_two_fast", "family": "curr_interaction", "dir": 1, "role": "v2"},
    {"id": "curr_two_explosive", "family": "curr_interaction", "dir": 1, "role": "v2"},
    {"id": "curr_mean_game_total", "family": "curr_env", "dir": 1, "role": "v2"},
    {"id": "curr_high_env_rate", "family": "curr_env", "dir": 1, "role": "v2"},
    {"id": "prior_sum_off_epa", "family": "prior_epa", "dir": 1, "role": "v2"},
    {"id": "prior_sum_def_epa", "family": "prior_epa", "dir": 1, "role": "v2"},
    {"id": "prior_sum_explosive_created", "family": "prior_explosive", "dir": 1, "role": "v2"},
    {"id": "prior_sum_explosive_allowed", "family": "prior_explosive", "dir": 1, "role": "v2"},
    {"id": "prior_sum_pace", "family": "prior_pace", "dir": 1, "role": "v2"},
    {"id": "prior_sum_finish", "family": "prior_finish", "dir": 1, "role": "v2"},
    {"id": "prior_mean_game_total", "family": "prior_env", "dir": 1, "role": "v2"},
    {"id": "prior_high_env_rate", "family": "prior_env", "dir": 1, "role": "v2"},
    {"id": "sum_qb_talent", "family": "layer_a", "dir": 1, "role": "v2"},
    {"id": "layer_b_returning", "family": "layer_b", "dir": 1, "role": "source_gap"},
    {"id": "v1_sum_off_eff", "family": "v1_reference", "dir": 1, "role": "v1_reference"},
    {"id": "v1_e3_proxy", "family": "v1_reference", "dir": 1, "role": "v1_reference"},
    {"id": "close_total", "family": "market_diagnostic", "dir": 1, "role": "diagnostic"},
)

COMPOSITE_MEMBERS = (
    "curr_sum_off_epa",
    "curr_sum_def_epa",
    "curr_sum_explosive_allowed",
    "curr_sum_pace_plays",
    "curr_mean_game_total",
    "prior_mean_game_total",
)


def score_feature(rows: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]) -> Dict[str, Any]:
    raw = [((r.get("features") or {}).get(spec["id"])) for r in rows]
    labels = [int(r["high_env"]) for r in rows]
    oriented = _oriented(raw, int(spec.get("dir") or 1))
    n_present = sum(1 for v in oriented if v is not None)
    dec = decile_card(oriented, labels)
    xs = [float(v) for v in oriented if v is not None]
    return {
        "id": spec["id"],
        "family": spec["family"],
        "role": spec["role"],
        "direction": int(spec.get("dir") or 1),
        "n": len(rows),
        "n_present": n_present,
        "coverage": n_present / len(rows) if rows else 0.0,
        "mean": _mean(xs),
        "sd": statistics.pstdev(xs) if len(xs) > 1 else None,
        "auc": roc_auc(oriented, labels),
        "pr_auc": average_precision(oriented, labels),
        "prevalence": dec.get("prevalence"),
        "top_decile_rate": dec.get("top_decile_rate"),
        "top_decile_lift": dec.get("top_decile_lift"),
        "top_decile_capture": dec.get("top_decile_capture"),
        "deciles": dec,
    }


def score_composite(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    labels = [int(r["high_env"]) for r in rows]
    ranks: List[List[Optional[float]]] = []
    for fid in COMPOSITE_MEMBERS:
        spec = next(s for s in FEATURE_SPECS if s["id"] == fid)
        raw = [((r.get("features") or {}).get(fid)) for r in rows]
        ranks.append(_pct_ranks(_oriented(raw, int(spec["dir"]))))
    combo: List[Optional[float]] = []
    for i in range(len(rows)):
        vals = [col[i] for col in ranks if col[i] is not None]
        combo.append(statistics.fmean(vals) if len(vals) >= 2 else None)
    dec = decile_card(combo, labels)
    return {
        "id": "rank_avg_v2_env",
        "family": "predeclared_composite",
        "role": "v2",
        "members": list(COMPOSITE_MEMBERS),
        "n": len(rows),
        "n_present": sum(1 for v in combo if v is not None),
        "coverage": sum(1 for v in combo if v is not None) / len(rows) if rows else 0.0,
        "auc": roc_auc(combo, labels),
        "pr_auc": average_precision(combo, labels),
        "prevalence": dec.get("prevalence"),
        "top_decile_rate": dec.get("top_decile_rate"),
        "top_decile_lift": dec.get("top_decile_lift"),
        "top_decile_capture": dec.get("top_decile_capture"),
        "deciles": dec,
        "note": "Equal-weight rank average of present members. Not a fit. No capture target.",
    }


def _split_card(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    labels = [int(r["high_env"]) for r in rows]
    n_pos = sum(labels)
    highs = [float(r["actual_total"]) for r in rows if int(r["high_env"]) == 1]
    others = [float(r["actual_total"]) for r in rows if int(r["high_env"]) == 0]
    week_ge4 = [r for r in rows if int(r["week"]) >= 4]
    return {
        "n": len(rows),
        "high_env_n": n_pos,
        "prevalence": (n_pos / len(rows)) if rows else None,
        "mean_actual_total_high": _mean(highs),
        "mean_actual_total_other": _mean(others),
        "curr_both_available_n": sum(1 for r in rows if r.get("curr_both_available")),
        "curr_both_available_rate": (
            sum(1 for r in rows if r.get("curr_both_available")) / len(rows) if rows else None
        ),
        "prior_both_available_rate": (
            sum(1 for r in rows if r.get("prior_both_available")) / len(rows) if rows else None
        ),
        "features": [score_feature(rows, spec) for spec in FEATURE_SPECS],
        "composite": score_composite(rows),
        "week_ge4": {
            "n": len(week_ge4),
            "high_env_n": sum(int(r["high_env"]) for r in week_ge4),
            "features": [
                score_feature(week_ge4, spec)
                for spec in FEATURE_SPECS
                if spec["id"].startswith("curr_")
            ],
            "composite": score_composite(week_ge4) if week_ge4 else {},
        },
    }


def coverage_card(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    by: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        key = f"{r['season']}_w{int(r['week']):02d}"
        block = by.setdefault(
            key,
            {"n": 0, "high_env_n": 0, "curr_both": 0, "prior_both": 0},
        )
        block["n"] += 1
        block["high_env_n"] += int(r["high_env"])
        block["curr_both"] += 1 if r.get("curr_both_available") else 0
        block["prior_both"] += 1 if r.get("prior_both_available") else 0
    return by


def _gate_ok(feat: Mapping[str, Any]) -> bool:
    auc = feat.get("auc")
    rate = feat.get("top_decile_rate")
    prev = feat.get("prevalence")
    if auc is None or rate is None or prev is None:
        return False
    return float(auc) >= STABLE_AUC and float(rate) > float(prev)


def decide(cards: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    why = [
        "HIGH_ENV = actual total ≥ 68 locked. No capture target.",
        "Stability = AUC ≥ 0.55 and top-decile rate > prevalence on Train-0, Val-0, and Val-1.",
        "Close is diagnostic. Layer B is a source gap. Missing means missing.",
    ]
    by_split: Dict[str, Dict[str, Any]] = {}
    for name in PROTOCOL_SPLITS:
        feats = {f["id"]: f for f in ((cards.get(name) or {}).get("features") or [])}
        if (cards.get(name) or {}).get("composite"):
            feats["rank_avg_v2_env"] = cards[name]["composite"]
        by_split[name] = feats
    family_of = {s["id"]: s.get("family") for s in FEATURE_SPECS}
    family_of["rank_avg_v2_env"] = "predeclared_composite"
    stable: List[str] = []
    stability_table: Dict[str, Dict[str, Any]] = {}
    for spec in list(FEATURE_SPECS) + [{"id": "rank_avg_v2_env", "role": "v2"}]:
        if spec.get("role") not in {"v2"}:
            continue
        notes = []
        ok = True
        row: Dict[str, Any] = {"family": family_of.get(spec["id"])}
        for name in PROTOCOL_SPLITS:
            feat = (by_split.get(name) or {}).get(spec["id"]) or {}
            split_ok = _gate_ok(feat)
            row[name] = {
                "auc": feat.get("auc"),
                "top_decile_rate": feat.get("top_decile_rate"),
                "top_decile_lift": feat.get("top_decile_lift"),
                "top_decile_capture": feat.get("top_decile_capture"),
                "coverage": feat.get("coverage"),
                "ok": split_ok,
            }
            notes.append(f"{name} AUC={feat.get('auc')} rate={feat.get('top_decile_rate')}")
            if not split_ok:
                ok = False
        row["stable"] = ok
        stability_table[spec["id"]] = row
        if ok:
            stable.append(spec["id"])
    stable_families = sorted({family_of[i] for i in stable if family_of.get(i)})
    pbp_stable = [i for i in stable if family_of.get(i) in PBP_FAMILIES]
    if stable:
        decision = "STABLE_SIGNAL_CANDIDATE_FOR_ARCHITECTURE_V2"
        note = (
            "At least one v2 family ranks HIGH_ENV better than chance in the "
            "same direction on Train-0, Val-0, and Val-1. Still not a "
            "production model. Architecture v2 may be designed from these families."
        )
    else:
        decision = "DATA_LAYER_V2_BUILT_SIGNAL_NOT_STABLE"
        note = (
            "The data layer exists and is PIT-safe. No predeclared v2 family "
            "cleared the three-window stability gate. Do not design scoring "
            "architecture v2 yet. Do not torture thresholds."
        )
    return {
        "decision": decision,
        "ship": False,
        "winner": None,
        "play": False,
        "stable_features": stable,
        "stable_families": stable_families,
        "pbp_stable_features": pbp_stable,
        "note": note,
        "why": why,
        "stability_table": stability_table,
    }


def slim_split_card(card: Mapping[str, Any]) -> Dict[str, Any]:
    """Drop bulky decile bins except the composite."""
    out = dict(card)
    slim_feats = []
    for feat in card.get("features") or []:
        row = dict(feat)
        dec = dict(row.get("deciles") or {})
        dec.pop("bins", None)
        row["deciles"] = dec
        slim_feats.append(row)
    out["features"] = slim_feats
    week = dict(card.get("week_ge4") or {})
    if week.get("features"):
        week_feats = []
        for feat in week["features"]:
            row = dict(feat)
            dec = dict(row.get("deciles") or {})
            dec.pop("bins", None)
            row["deciles"] = dec
            week_feats.append(row)
        week["features"] = week_feats
    out["week_ge4"] = week
    return out


def run_data_layer_v2(*, cache_dir=None, lake_only: bool = True) -> Dict[str, Any]:
    assert_frozen_priors()
    refuse_sealed_or_confirm(LEGAL_SEASONS)
    if QB_FEATURE_CONTRACT_VERSION != "cfb-qb-feature-v1":
        raise FrozenScoringError("qb feature contract drifted")
    if CFB_EDGE_BOARD_PUBLIC_ENABLED:
        raise FrozenScoringError("public board kill switch must stay off")
    if abs(float(P.MATCHUP_RESPONSE) - FROZEN_BASELINE) > 1e-9:
        raise FrozenScoringError("production MATCHUP_RESPONSE drifted from 1.40")

    bundle = load_legal_scoring_bundle(cache_dir=cache_dir, lake_only=lake_only)
    lake_mounted = all(
        (bundle.get("lake_locate") or {}).get(str(season), {}).get("mounted")
        for season in LEGAL_SEASONS
    )
    layer = None
    rows: List[Dict[str, Any]] = []
    cards: Dict[str, Any] = {}
    cov: Dict[str, Any] = {}
    if lake_mounted:
        layer = build_data_layer_v2(prefer_hd=True)
        from src.services.cfb_warehouse.frozen_140_scoring import SDV_CACHE

        cache = Path(cache_dir or SDV_CACHE)
        prior_env: Dict[int, Any] = {}
        current_env: Dict[int, Any] = {}
        for season in LEGAL_SEASONS:
            try:
                prior_env[season - 1] = load_prior_env(season - 1, cache_dir=cache)
            except Exception:
                prior_env[season - 1] = {}
            try:
                current_env[season] = load_current_env(season, cache_dir=cache)
            except Exception:
                current_env[season] = {}
        layer_a = {season: load_layer_a(season) for season in LEGAL_SEASONS}
        for raw in bundle["joined"]:
            if not _eligible(raw, lake_only=lake_only):
                continue
            feat = game_features(
                raw,
                layer=layer,
                layer_a=layer_a,
                universes=bundle["universes"],
                prior_env=prior_env,
                current_env=current_env,
            )
            if feat is not None:
                rows.append(feat)
        for name in PROTOCOL_SPLITS:
            cards[name] = _split_card(_split_rows(rows, name))
        cov = coverage_card(rows)

    gate = (
        decide(cards)
        if lake_mounted
        else {
            "decision": "INSUFFICIENT_EVIDENCE_DO_NOT_SHIP",
            "ship": False,
            "winner": None,
            "play": False,
            "why": ["odds lake not mounted"],
        }
    )
    slim_cards = {name: slim_split_card(card) for name, card in cards.items()}
    return {
        "role": "cfb_data_layer_v2",
        "scoring_equation_frozen": True,
        "do_not_tune": True,
        "kill_switch": "OFF",
        "merge_532": False,
        "used_2026_for_fitting": False,
        "opened_2025": False,
        "wrote_production_coefficient": False,
        "play": False,
        "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
        "matchup_response_frozen": P.MATCHUP_RESPONSE,
        "target": {
            "name": "HIGH_ENV",
            "rule": "actual_total >= 68",
            "threshold": HIGH_ENV_THRESHOLD,
            "capture_target": None,
        },
        "pit_rules": [
            "current as_of_week W uses only same-season week < W",
            "prior-year uses completed Y-1 only",
            "no close in v2 features",
            "no target-game or future-game stats",
            "missing means missing",
            "2025 never opened",
        ],
        "layer_b": LAYER_B_GAP,
        "source_gaps": list(SOURCE_GAPS),
        "source_meta": None if layer is None else {
            season: {
                k: v
                for k, v in meta.items()
                if k not in {"has", "has_columns"}
            }
            for season, meta in (layer.get("source_meta") or {}).items()
        },
        "cache_dir": None if layer is None else layer.get("cache_dir"),
        "predeclared_features": [
            {"id": s["id"], "family": s["family"], "role": s["role"], "dir": s["dir"]}
            for s in FEATURE_SPECS
        ],
        "composite_members": list(COMPOSITE_MEMBERS),
        "stability_gate": {
            "auc_min_all_splits": STABLE_AUC,
            "top_decile_rate_gt_prevalence": True,
            "capture_target": None,
        },
        "leakage": {
            "opened_2025": False,
            "pbp_seasons": list(LEGAL_PBP_SEASONS),
            "current_uses_week_lt_W": True,
            "prior_season_always_ym1": True,
            "close_in_v2_features": False,
            "missing_means_missing": True,
        },
        "lake_mounted": lake_mounted,
        "n_eligible": len(rows),
        "coverage_by_season_week": cov,
        "splits": slim_cards,
        "decision": gate,
    }
