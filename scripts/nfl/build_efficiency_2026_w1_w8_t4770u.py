#!/usr/bin/env python3
"""Offline 2026 W1–W8 NFL efficiency recovery (t4770u / DECISION 751dd63c).

Approved source only:
  https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.parquet
  (same URL template CLEARed on t4696u S1 restage)

No DATABASE_URL. No production DB/service mutation. No 2025-prior fill.
Week 8 incomplete → fail closed (DATA_PARTIAL); do not declare through-W8.
Bound to Alex v2 b41f4b43 after IMV PASS_CONTRACT 1a53bbd3 (D1 CLOSED).
Ryan t4776u: IF consume proof must show the 20 required fields are used
by the Independent Fair path (call graph + input hash), not merely present.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
sys.path.insert(0, str(MS))

# Operative bind — IMV PASS_CONTRACT 1a53bbd3 on Alex v2 b41f4b43.
DECISION_SHA8 = "751dd63c"
ALEX_CONTRACT_V2_SHA8 = "b41f4b43"
ALEX_CONTRACT_V2_SHA256 = (
    "b41f4b43e1367bd5658c743475b9b84535c65395630a0b06c804f8b3552b81f4"
)
ALEX_CONTRACT_V1_SHA8 = "24600552"
IMV_PASS_CONTRACT_SHA8 = "1a53bbd3"
IMV_PASS_CONTRACT_SHA256 = (
    "1a53bbd33f32fec8d25a102f2abea7b975a92fbd55edbaaaafe020055c25b9f8"
)
IMV_RETURN_PARENT_SHA8 = "d2587de7"
CONTRACT_BIND = "BOUND_TO_V2_PASS_CONTRACT_1a53bbd3"
IF_CODE_COMMIT = "1b39f4e9f6b2e04c264a41831f3bb7273e475011"
ADDON_TICKETS = ("t4776u",)

# Existing approved transforms copied verbatim so this script needs no
# DATABASE_URL / requests / SQLAlchemy. Sources:
#   nfl_data.team_strength_from_record / rest_days_from_schedule
#   nfl_matchup_features.matchup_pack_to_sim_input_kwargs (T4)
#   data_platform_nfl/ingest.py (T3 diffs)
# NFL_TEAMS matches nfl_season_engine.loaders.NFL_TEAMS (LA = Rams).
NFL_TEAMS = [
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
    "LA", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG",
    "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
]


def _safe_float(value: Any, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def team_strength_from_record(record_summary: str | None) -> tuple[float, float]:
    """Exact nfl_data.team_strength_from_record (T5)."""
    if not record_summary or "-" not in record_summary:
        return 1.0, 1.0
    try:
        wins, losses = record_summary.split("-", 1)
        w = max(0.0, float(wins))
        l = max(0.0, float(losses))
        games = max(1.0, w + l)
        win_pct = w / games
    except Exception:
        return 1.0, 1.0
    offense = _safe_float(0.90 + (0.22 * win_pct), 1.0)
    defense = _safe_float(0.92 + (0.20 * win_pct), 1.0)
    return max(0.82, min(1.18, offense)), max(0.82, min(1.20, defense))


def rest_days_from_schedule(game_time_iso: str | None) -> float:
    """Exact nfl_data.rest_days_from_schedule."""
    if not game_time_iso:
        return 7.0
    try:
        game_dt = _parse_iso(game_time_iso)
    except Exception:
        return 7.0
    dow = game_dt.astimezone(timezone.utc).weekday()
    if dow == 3:
        return 4.0
    if dow == 0:
        return 6.0
    return 7.0


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def matchup_pack_to_sim_input_kwargs(matchup_pack: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Exact T4 + T3 field map from nfl_matchup_features.matchup_pack_to_sim_input_kwargs."""
    if not matchup_pack:
        return {}
    home_success_off = _to_float(matchup_pack.get("home_success_offense_5g"))
    away_success_off = _to_float(matchup_pack.get("away_success_offense_5g"))
    home_success_def = _to_float(matchup_pack.get("home_success_defense_allowed_5g"))
    away_success_def = _to_float(matchup_pack.get("away_success_defense_allowed_5g"))
    success_terms = []
    if home_success_off is not None and away_success_off is not None:
        success_terms.append(home_success_off - away_success_off)
    if away_success_def is not None and home_success_def is not None:
        success_terms.append(away_success_def - home_success_def)
    diff_success_rate = (sum(success_terms) / len(success_terms)) if success_terms else None
    return {
        "home_off_epa_5g": _to_float(matchup_pack.get("home_off_epa_5g")),
        "away_off_epa_5g": _to_float(matchup_pack.get("away_off_epa_5g")),
        "home_def_epa_allowed_5g": _to_float(matchup_pack.get("home_def_epa_allowed_5g")),
        "away_def_epa_allowed_5g": _to_float(matchup_pack.get("away_def_epa_allowed_5g")),
        "home_pass_rate_5g": _to_float(matchup_pack.get("home_pass_rate_5g")),
        "away_pass_rate_5g": _to_float(matchup_pack.get("away_pass_rate_5g")),
        "home_success_offense_5g": home_success_off,
        "away_success_offense_5g": away_success_off,
        "home_success_defense_allowed_5g": home_success_def,
        "away_success_defense_allowed_5g": away_success_def,
        "matchup_diff_off_epa_5g": _to_float(matchup_pack.get("diff_off_epa_5g")),
        "matchup_diff_def_epa_allowed_5g": _to_float(matchup_pack.get("diff_def_epa_allowed_5g")),
        "matchup_diff_pressure_generated_5g": _to_float(
            matchup_pack.get("diff_pressure_generated_5g")
        ),
        "matchup_diff_pressure_allowed_5g": _to_float(
            matchup_pack.get("diff_pressure_allowed_5g")
        ),
        "matchup_diff_red_zone_td_rate_5g": _to_float(
            matchup_pack.get("diff_red_zone_td_rate_5g")
        ),
        "matchup_diff_success_rate_5g": diff_success_rate,
    }

APPROVED_PBP_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/pbp/"
    "play_by_play_2026.parquet"
)
APPROVED_SOURCE_ID = "nflverse-data/releases/pbp/play_by_play_2026.parquet"
APPROVED_CLEAR_LINEAGE = [
    "t4696u S1 restage — same URL template seasons 2012–2022 (PR #654, do not merge)",
    "t4166u W4–W6 nflverse CLEAR (referenced by CoS; artifacts not on deploy-vercel)",
    "t4139u W7 nflverse CLEAR (referenced by CoS; artifacts not on deploy-vercel)",
    "DECISION 751dd63c t4770u — authorize 2026 W1–W8 recovery from approved no-cost sources",
]
LICENSE_NOTE = (
    "nflverse open data (nflverse-data GitHub releases). Public HTTPS. "
    "No credential. No paid vendor. Terms: github.com/nflverse/nflverse-data"
)

SEASON = 2026
TARGET_THROUGH_WEEK = 8
PARTIAL_PANEL_WEEK = 7
READY_PANEL_WEEK = 8
CONSISTENT_PANEL_WEEK = PARTIAL_PANEL_WEEK  # through-W7 PARTIAL; lift only when 14/14 W8


def panel_week_from_coverage(coverage: Dict[str, Any]) -> int:
    """READY panel is week 8 only after all 14 W8 games are final. Else 7."""
    if coverage.get("through_w8_complete"):
        return READY_PANEL_WEEK
    return PARTIAL_PANEL_WEEK
MIN_SCRIMMAGE_PLAYS = 80
ENGINE_TEAMS = list(NFL_TEAMS)
TEAM_TO_ENGINE = {"LAR": "LA", "WSH": "WAS"}
ENGINE_TO_SCHEDULE = {"LA": "LAR"}

SCHEDULE_PATH = (
    MS
    / "src"
    / "services"
    / "nfl_season_engine"
    / "data"
    / "nfl-canonical-schedule-2026.json"
)
OUT_DIR = ROOT / "data" / "ops" / "nfl-efficiency-2026-w1-w8-t4770u"
RAW_DIR = ROOT / "data" / "raw" / "nfl" / "pbp" / "t4770u"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _parse_iso(raw: str) -> datetime:
    text = str(raw or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text).astimezone(timezone.utc)


def engine_team(raw: Any) -> str:
    code = str(raw or "").strip().upper()
    return TEAM_TO_ENGINE.get(code, code)


def schedule_team(engine: str) -> str:
    return ENGINE_TO_SCHEDULE.get(engine, engine)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, obj: Any) -> str:
    text = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")
    return sha256_bytes(text.encode("utf-8"))


def load_schedule() -> Dict[str, Any]:
    payload = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))
    games = []
    for row in payload.get("games") or []:
        if int(row.get("season") or 0) != SEASON:
            continue
        if str(row.get("game_type") or "REG").upper() != "REG":
            continue
        week = int(row.get("week") or 0)
        if week < 1 or week > TARGET_THROUGH_WEEK:
            continue
        home = engine_team(row.get("home_team_id"))
        away = engine_team(row.get("away_team_id"))
        games.append(
            {
                "game_id": str(row.get("game_id")),
                "engine_game_id": str(row.get("engine_game_id") or row.get("game_id")),
                "season": SEASON,
                "week": week,
                "away_team": away,
                "home_team": home,
                "away_team_schedule": str(row.get("away_team_id")),
                "home_team_schedule": str(row.get("home_team_id")),
                "kickoff_utc": str(row.get("kickoff_utc") or ""),
                "venue": row.get("venue"),
                "network": row.get("network"),
            }
        )
    w9 = []
    for row in payload.get("games") or []:
        if int(row.get("season") or 0) != SEASON:
            continue
        if int(row.get("week") or 0) != 9:
            continue
        if str(row.get("game_type") or "REG").upper() != "REG":
            continue
        w9.append(
            {
                "game_id": str(row.get("game_id")),
                "engine_game_id": str(row.get("engine_game_id") or row.get("game_id")),
                "season": SEASON,
                "week": 9,
                "away_team": engine_team(row.get("away_team_id")),
                "home_team": engine_team(row.get("home_team_id")),
                "kickoff_utc": str(row.get("kickoff_utc") or ""),
            }
        )
    return {
        "meta": {
            "path": str(SCHEDULE_PATH.relative_to(ROOT)),
            "source": payload.get("source"),
            "as_of": payload.get("as_of"),
            "sha256": sha256_file(SCHEDULE_PATH),
        },
        "w1_w8": games,
        "w9": w9,
    }


def fetch_pbp(dest: Path) -> Dict[str, Any]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        APPROVED_PBP_URL,
        headers={"User-Agent": "kosedge-t4770u-efficiency-recovery"},
    )
    fetched_at = _now_utc()
    with urllib.request.urlopen(req, timeout=120) as resp:
        status = int(getattr(resp, "status", 200) or 200)
        raw = resp.read()
        headers = {k.lower(): v for k, v in resp.headers.items()}
    dest.write_bytes(raw)
    digest = sha256_bytes(raw)
    if sha256_file(dest) != digest:
        raise RuntimeError("persisted PBP sha256 mismatch vs in-memory bytes")
    return {
        "url": APPROVED_PBP_URL,
        "source_id": APPROVED_SOURCE_ID,
        "http_status": status,
        "fetched_at_utc": _iso(fetched_at),
        "bytes": len(raw),
        "sha256": digest,
        "path": str(dest.relative_to(ROOT)),
        "etag": headers.get("etag"),
        "last_modified": headers.get("last-modified"),
        "content_type": headers.get("content-type"),
        "license": LICENSE_NOTE,
        "access": "public HTTPS; no credential; no paid vendor",
        "hash_before_parse": True,
        "archived": False,
    }


def archive_pbp(raw_path: Path, source: Dict[str, Any]) -> Dict[str, Any]:
    """O-a: persist fetched bytes + fetched_at_utc. Public nflverse file mutates."""
    archive_dir = RAW_DIR / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    digest = str(source["sha256"])
    fetched = str(source.get("fetched_at_utc") or "unknown")
    stamp = fetched.replace(":", "").replace("-", "")
    dest = archive_dir / f"play_by_play_2026_{stamp}_{digest[:16]}.parquet"
    dest.write_bytes(raw_path.read_bytes())
    if sha256_file(dest) != digest:
        raise RuntimeError("archived PBP sha256 mismatch vs fetched bytes")
    sidecar = {
        "url": source.get("url"),
        "fetched_at_utc": source.get("fetched_at_utc"),
        "sha256": digest,
        "bytes": source.get("bytes"),
        "archive_path": str(dest.relative_to(ROOT)),
        "working_path": str(raw_path.relative_to(ROOT)),
    }
    write_json(archive_dir / f"{dest.stem}.json", sidecar)
    source = dict(source)
    source["archived"] = True
    source["archive_path"] = sidecar["archive_path"]
    source["archive_sidecar"] = str((archive_dir / f"{dest.stem}.json").relative_to(ROOT))
    return source


def rest_days_spotcheck(games: List[Dict[str, Any]]) -> Dict[str, Any]:
    """O-d: record DOW heuristic + short-week rows. Function is UTC weekday."""
    rows = []
    for game in games:
        kick = str(game.get("kickoff_utc") or "")
        days = rest_days_from_schedule(kick)
        dow_utc = None
        dow_et = None
        try:
            dt = _parse_iso(kick)
            dow_utc = dt.weekday()
            try:
                from zoneinfo import ZoneInfo

                dow_et = dt.astimezone(ZoneInfo("America/New_York")).weekday()
            except Exception:
                dow_et = None
        except Exception:
            dt = None
        expected = {3: 4.0, 0: 6.0}.get(dow_utc, 7.0) if dow_utc is not None else 7.0
        rows.append(
            {
                "game_id": game.get("game_id"),
                "kickoff_utc": kick,
                "dow_utc": dow_utc,
                "dow_et": dow_et,
                "utc_et_dow_mismatch": (
                    dow_utc is not None and dow_et is not None and dow_utc != dow_et
                ),
                "rest_days_home": game.get("rest_days_home", days),
                "rest_days_away": game.get("rest_days_away", days),
                "heuristic_days": days,
                "heuristic_matches_function": days == expected,
                "short_week": days < 7.0,
                "source": "nfl_data.rest_days_from_schedule",
            }
        )
    return {
        "function": "nfl_data.rest_days_from_schedule",
        "heuristic": "UTC weekday: Thu=4, Mon=6, else=7",
        "note": (
            "O-d: heuristic is UTC DOW. TNF/MNF kickoffs near midnight UTC can "
            "disagree with America/New_York DOW; record mismatch, do not invent rest."
        ),
        "n": len(rows),
        "n_short_week": sum(1 for r in rows if r.get("short_week")),
        "n_utc_et_dow_mismatch": sum(1 for r in rows if r.get("utc_et_dow_mismatch")),
        "rows": rows,
    }


def _truthy(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    try:
        return float(value) == 1.0
    except (TypeError, ValueError):
        return str(value).strip().lower() in {"true", "t", "yes", "y"}


def load_pbp_frame(path: Path):
    import pandas as pd

    wanted = [
        "season",
        "week",
        "game_id",
        "game_date",
        "home_team",
        "away_team",
        "posteam",
        "defteam",
        "play_type",
        "down",
        "epa",
        "success",
        "sack",
        "qb_hit",
        "yardline_100",
        "touchdown",
        "first_down",
        "passing_yards",
        "season_type",
        "qtr",
        "desc",
        "home_score",
        "away_score",
        "result",
    ]
    import pyarrow.parquet as pq

    schema_names = set(pq.ParquetFile(path).schema_arrow.names)
    cols = [c for c in wanted if c in schema_names]
    if "play_type" not in cols:
        raise RuntimeError(f"PBP missing play_type; have={sorted(schema_names)[:20]}")
    frame = pd.read_parquet(path, columns=cols)
    if "season" in frame.columns:
        frame = frame[frame["season"] == SEASON]
    if "season_type" in frame.columns:
        frame = frame[frame["season_type"].astype(str).str.upper().isin(["REG", "REGULAR"])]
    return frame


def nflverse_game_key(week: int, away: str, home: str) -> str:
    return f"{SEASON}_{int(week):02d}_{away}_{home}"


def complete_games_from_pbp(frame) -> Dict[str, Dict[str, Any]]:
    scrimmage = frame[frame["play_type"].isin(["pass", "run"])].copy()
    out: Dict[str, Dict[str, Any]] = {}
    if scrimmage.empty:
        return out
    grouped = scrimmage.groupby("game_id", dropna=False)
    for game_id, g in grouped:
        if not game_id:
            continue
        n_scrim = int(len(g))
        week = int(g["week"].dropna().iloc[0]) if g["week"].notna().any() else 0
        home = engine_team(g["home_team"].dropna().iloc[0]) if g["home_team"].notna().any() else ""
        away = engine_team(g["away_team"].dropna().iloc[0]) if g["away_team"].notna().any() else ""
        qtr_max = int(g["qtr"].max()) if g["qtr"].notna().any() else 0
        home_score = (
            int(g["home_score"].dropna().iloc[0]) if "home_score" in g and g["home_score"].notna().any() else None
        )
        away_score = (
            int(g["away_score"].dropna().iloc[0]) if "away_score" in g and g["away_score"].notna().any() else None
        )
        complete = (
            n_scrim >= MIN_SCRIMMAGE_PLAYS
            and qtr_max >= 4
            and home_score is not None
            and away_score is not None
        )
        out[str(game_id)] = {
            "nflverse_game_id": str(game_id),
            "week": week,
            "home_team": home,
            "away_team": away,
            "scrimmage_plays": n_scrim,
            "qtr_max": qtr_max,
            "home_score": home_score,
            "away_score": away_score,
            "complete": complete,
            "game_date": str(g["game_date"].dropna().iloc[0]) if g["game_date"].notna().any() else "",
        }
    return out


def classify_schedule_games(
    schedule_games: List[Dict[str, Any]],
    pbp_games: Dict[str, Dict[str, Any]],
    now: datetime,
) -> Dict[str, Any]:
    pbp_by_teams_week: Dict[Tuple[int, str, str], Dict[str, Any]] = {}
    for row in pbp_games.values():
        pbp_by_teams_week[(int(row["week"]), row["away_team"], row["home_team"])] = row

    classified = []
    missing_w8 = []
    incomplete_observed = []
    complete = []
    not_yet_kicked = []
    for game in schedule_games:
        key = (int(game["week"]), game["away_team"], game["home_team"])
        pbp = pbp_by_teams_week.get(key)
        kick = _parse_iso(game["kickoff_utc"]) if game.get("kickoff_utc") else None
        kicked = bool(kick and kick <= now)
        status = "MISSING"
        if pbp and pbp["complete"]:
            status = "COMPLETE"
            complete.append(game["game_id"])
        elif pbp and not pbp["complete"]:
            status = "INCOMPLETE_IN_PBP"
            incomplete_observed.append(game["game_id"])
        elif kick and kick > now:
            status = "NOT_YET_KICKED"
            not_yet_kicked.append(game["game_id"])
        else:
            status = "MISSING_FROM_PBP"
        rec = {
            **game,
            "status": status,
            "kicked_off": kicked,
            "pbp": (
                {
                    "nflverse_game_id": pbp["nflverse_game_id"],
                    "scrimmage_plays": pbp["scrimmage_plays"],
                    "qtr_max": pbp["qtr_max"],
                    "home_score": pbp.get("home_score"),
                    "away_score": pbp.get("away_score"),
                    "complete": pbp["complete"],
                }
                if pbp
                else None
            ),
        }
        classified.append(rec)
        if int(game["week"]) == TARGET_THROUGH_WEEK and status != "COMPLETE":
            missing_w8.append(
                {
                    "game_id": game["game_id"],
                    "week": game["week"],
                    "away_team": schedule_team(game["away_team"]),
                    "home_team": schedule_team(game["home_team"]),
                    "kickoff_utc": game["kickoff_utc"],
                    "status": status,
                }
            )
    by_week: Dict[str, Any] = {}
    for rec in classified:
        bucket = by_week.setdefault(
            str(rec["week"]),
            {"expected": 0, "complete": 0, "missing": []},
        )
        bucket["expected"] += 1
        if rec["status"] == "COMPLETE":
            bucket["complete"] += 1
        else:
            bucket["missing"].append(rec["game_id"])
    w8_complete = by_week.get(str(TARGET_THROUGH_WEEK), {}).get("complete", 0)
    w8_expected = by_week.get(str(TARGET_THROUGH_WEEK), {}).get("expected", 0)
    through_w7_complete = all(
        by_week.get(str(week), {}).get("complete") == by_week.get(str(week), {}).get("expected")
        and by_week.get(str(week), {}).get("expected", 0) > 0
        for week in range(1, CONSISTENT_PANEL_WEEK + 1)
    )
    return {
        "as_of_utc": _iso(now),
        "games": classified,
        "complete_game_ids": complete,
        "incomplete_in_pbp": incomplete_observed,
        "not_yet_kicked": not_yet_kicked,
        "by_week": by_week,
        "week8_missing": missing_w8,
        "week8_complete_count": w8_complete,
        "week8_expected_count": w8_expected,
        "through_w7_complete": through_w7_complete,
        "through_w8_complete": w8_complete == w8_expected and w8_expected > 0,
    }


def _safe_div(num: float, den: float) -> Optional[float]:
    if den is None or den == 0:
        return None
    return float(num) / float(den)


def build_situational(frame, max_week: int) -> List[Dict[str, Any]]:
    plays = frame[
        (frame["play_type"].isin(["pass", "run"]))
        & (frame["week"].notna())
        & (frame["posteam"].notna())
        & (frame["week"] <= max_week)
    ].copy()
    plays["posteam"] = plays["posteam"].map(engine_team)
    plays["defteam"] = plays["defteam"].map(engine_team)
    plays["is_pass"] = plays["play_type"].eq("pass")
    plays["is_run"] = plays["play_type"].eq("run")
    plays["early"] = plays["down"].isin([1, 2])
    plays["third"] = plays["down"].eq(3)
    plays["fourth"] = plays["down"].eq(4)
    plays["rz"] = plays["yardline_100"] <= 20
    plays["td"] = plays["touchdown"].map(_truthy)
    plays["fd"] = plays["first_down"].map(_truthy)
    plays["sack"] = plays["sack"].map(_truthy)
    plays["qb_hit"] = plays["qb_hit"].map(_truthy)
    plays["success_num"] = plays["success"].map(
        lambda v: None if v is None or (isinstance(v, float) and v != v) else (1.0 if _truthy(v) else 0.0)
    )
    plays["explosive"] = plays["is_pass"] & (plays["passing_yards"].fillna(0) >= 20)
    plays["pressure"] = plays["is_pass"] & (plays["sack"] | plays["qb_hit"])

    rows: List[Dict[str, Any]] = []
    offense = plays.groupby(["week", "posteam"], dropna=False)
    defense = plays.groupby(["week", "defteam"], dropna=False)
    def_map = {key: g for key, g in defense}

    for (week, team), g in offense:
        if team not in ENGINE_TEAMS:
            continue
        d = def_map.get((week, team))
        off_plays = int(len(g))
        pass_plays = int(g["is_pass"].sum())
        run_plays = int(g["is_run"].sum())
        early_plays = int(g["early"].sum())
        early_pass = int((g["early"] & g["is_pass"]).sum())
        third_att = int(g["third"].sum())
        third_conv = int((g["third"] & g["fd"]).sum())
        fourth_att = int(g["fourth"].sum())
        fourth_conv = int((g["fourth"] & g["fd"]).sum())
        rz_plays = int(g["rz"].sum())
        rz_td = int((g["rz"] & g["td"]).sum())
        sacks_allowed = int((g["is_pass"] & g["sack"]).sum())
        qb_hits_allowed = int((g["is_pass"] & g["qb_hit"]).sum())
        explosive_pass = int(g["explosive"].sum())
        dropbacks = pass_plays
        pressures_allowed = int(g["pressure"].sum())
        success_off = (
            float(g["success_num"].mean()) if g["success_num"].notna().any() else None
        )
        epa_off = float(g["epa"].mean()) if g["epa"].notna().any() else None
        pass_epa = (
            float(g.loc[g["is_pass"], "epa"].mean())
            if g.loc[g["is_pass"], "epa"].notna().any()
            else None
        )
        run_epa = (
            float(g.loc[g["is_run"], "epa"].mean())
            if g.loc[g["is_run"], "epa"].notna().any()
            else None
        )
        early_epa = (
            float(g.loc[g["early"], "epa"].mean())
            if g.loc[g["early"], "epa"].notna().any()
            else None
        )

        def_plays = int(len(d)) if d is not None else 0
        sacks_gen = int((d["is_pass"] & d["sack"]).sum()) if d is not None else 0
        qb_hits_gen = int((d["is_pass"] & d["qb_hit"]).sum()) if d is not None else 0
        explosive_allowed = int(d["explosive"].sum()) if d is not None else 0
        success_def = (
            float(d["success_num"].mean())
            if d is not None and d["success_num"].notna().any()
            else None
        )
        epa_def = (
            float(d["epa"].mean()) if d is not None and d["epa"].notna().any() else None
        )
        def_dropbacks = int(d["is_pass"].sum()) if d is not None else 0
        pressures_gen = int(d["pressure"].sum()) if d is not None else 0
        def_pass_plays = int(d["is_pass"].sum()) if d is not None else 0
        def_run_plays = int(d["is_run"].sum()) if d is not None else 0
        def_early_plays = int(d["early"].sum()) if d is not None else 0
        def_pass_epa = (
            float(d.loc[d["is_pass"], "epa"].mean())
            if d is not None and d.loc[d["is_pass"], "epa"].notna().any()
            else None
        )
        def_run_epa = (
            float(d.loc[d["is_run"], "epa"].mean())
            if d is not None and d.loc[d["is_run"], "epa"].notna().any()
            else None
        )
        def_early_epa = (
            float(d.loc[d["early"], "epa"].mean())
            if d is not None and d.loc[d["early"], "epa"].notna().any()
            else None
        )
        def_rz = int(d["rz"].sum()) if d is not None else 0
        def_rz_td = int((d["rz"] & d["td"]).sum()) if d is not None else 0
        def_explosive_rate = _safe_div(explosive_allowed, def_plays)

        rows.append(
            {
                "season": SEASON,
                "week": int(week),
                "team": team,
                "games_played": 1,
                "offensive_plays": off_plays,
                "defensive_plays": def_plays,
                "pass_plays": pass_plays,
                "run_plays": run_plays,
                "early_down_plays": early_plays,
                "early_down_pass_plays": early_pass,
                "third_down_attempts": third_att,
                "third_down_conversions": third_conv,
                "fourth_down_attempts": fourth_att,
                "fourth_down_conversions": fourth_conv,
                "red_zone_plays": rz_plays,
                "red_zone_touchdowns": rz_td,
                "sacks_allowed": sacks_allowed,
                "qb_hits_allowed": qb_hits_allowed,
                "sacks_generated": sacks_gen,
                "qb_hits_generated": qb_hits_gen,
                "explosive_pass_plays": explosive_pass,
                "explosive_pass_allowed": explosive_allowed,
                "pass_rate": _safe_div(pass_plays, off_plays),
                "early_down_pass_rate": _safe_div(early_pass, early_plays),
                "third_down_conversion_rate": _safe_div(third_conv, third_att),
                "fourth_down_conversion_rate": _safe_div(fourth_conv, fourth_att),
                "red_zone_td_rate": _safe_div(rz_td, rz_plays),
                "pressure_rate_allowed": _safe_div(pressures_allowed, dropbacks),
                "pressure_rate_generated": _safe_div(pressures_gen, def_dropbacks),
                "success_rate_offense": success_off,
                "success_rate_defense_allowed": success_def,
                "epa_per_play_offense": epa_off,
                "epa_per_play_defense_allowed": epa_def,
                "pass_epa": pass_epa,
                "run_epa": run_epa,
                "early_down_epa": early_epa,
                "def_pass_epa": def_pass_epa,
                "def_run_epa": def_run_epa,
                "def_early_down_epa": def_early_epa,
                "def_pass_plays": def_pass_plays,
                "def_run_plays": def_run_plays,
                "def_early_down_plays": def_early_plays,
                "def_red_zone_td_rate": _safe_div(def_rz_td, def_rz),
                "explosive_rate_offense": _safe_div(explosive_pass, off_plays),
                "explosive_rate_defense_allowed": def_explosive_rate,
                "source": "nflverse",
            }
        )
    rows.sort(key=lambda r: (r["team"], r["week"]))
    return rows


def _mean(values: Iterable[Optional[float]]) -> Optional[float]:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


def build_rolling(situational: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_team: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in situational:
        by_team[row["team"]].append(row)
    out = []
    for team, rows in by_team.items():
        rows = sorted(rows, key=lambda r: (r["season"], r["week"]))
        for idx, row in enumerate(rows):
            win3 = rows[max(0, idx - 2) : idx + 1]
            win5 = rows[max(0, idx - 4) : idx + 1]
            out.append(
                {
                    "season": SEASON,
                    "week": row["week"],
                    "team": team,
                    "games_in_window_3": len(win3),
                    "games_in_window_5": len(win5),
                    "off_epa_per_play_3g": _mean(r["epa_per_play_offense"] for r in win3),
                    "off_epa_per_play_5g": _mean(r["epa_per_play_offense"] for r in win5),
                    "def_epa_allowed_per_play_3g": _mean(
                        r["epa_per_play_defense_allowed"] for r in win3
                    ),
                    "def_epa_allowed_per_play_5g": _mean(
                        r["epa_per_play_defense_allowed"] for r in win5
                    ),
                    "pressure_rate_allowed_3g": _mean(r["pressure_rate_allowed"] for r in win3),
                    "pressure_rate_allowed_5g": _mean(r["pressure_rate_allowed"] for r in win5),
                    "pressure_rate_generated_3g": _mean(
                        r["pressure_rate_generated"] for r in win3
                    ),
                    "pressure_rate_generated_5g": _mean(
                        r["pressure_rate_generated"] for r in win5
                    ),
                    "pass_rate_3g": _mean(r["pass_rate"] for r in win3),
                    "pass_rate_5g": _mean(r["pass_rate"] for r in win5),
                    "early_down_pass_rate_3g": _mean(r["early_down_pass_rate"] for r in win3),
                    "early_down_pass_rate_5g": _mean(r["early_down_pass_rate"] for r in win5),
                    "red_zone_td_rate_3g": _mean(r["red_zone_td_rate"] for r in win3),
                    "red_zone_td_rate_5g": _mean(r["red_zone_td_rate"] for r in win5),
                    "success_rate_offense_3g": _mean(r["success_rate_offense"] for r in win3),
                    "success_rate_offense_5g": _mean(r["success_rate_offense"] for r in win5),
                    "success_rate_defense_allowed_3g": _mean(
                        r["success_rate_defense_allowed"] for r in win3
                    ),
                    "success_rate_defense_allowed_5g": _mean(
                        r["success_rate_defense_allowed"] for r in win5
                    ),
                    "source": "nflverse",
                    "window_semantics": "ingest.py ROWS BETWEEN 4 PRECEDING AND CURRENT ROW on team-weeks",
                }
            )
    out.sort(key=lambda r: (r["team"], r["week"]))
    return out


def _weighted_mean(pairs: List[Tuple[Optional[float], int]]) -> Optional[float]:
    num = 0.0
    den = 0
    for value, weight in pairs:
        if value is None or weight <= 0:
            continue
        num += float(value) * int(weight)
        den += int(weight)
    if den <= 0:
        return None
    return num / den


def records_from_completed(
    completed: List[Dict[str, Any]], as_of_week: int
) -> Dict[str, Dict[str, Any]]:
    book: Dict[str, Dict[str, int]] = {
        team: {"wins": 0, "losses": 0, "ties": 0} for team in ENGINE_TEAMS
    }
    used = []
    for game in completed:
        if int(game["week"]) > as_of_week:
            continue
        pbp = game.get("pbp") or {}
        hs, aws = pbp.get("home_score"), pbp.get("away_score")
        if hs is None or aws is None:
            continue
        home, away = game["home_team"], game["away_team"]
        if hs > aws:
            book[home]["wins"] += 1
            book[away]["losses"] += 1
        elif aws > hs:
            book[away]["wins"] += 1
            book[home]["losses"] += 1
        else:
            book[home]["ties"] += 1
            book[away]["ties"] += 1
        used.append(game["game_id"])
    out: Dict[str, Dict[str, Any]] = {}
    for team, rec in book.items():
        w, l, t = rec["wins"], rec["losses"], rec["ties"]
        summary = f"{w}-{l}"
        if w + l <= 0:
            out[team] = {
                "record": summary,
                "ties": t,
                "wins": w,
                "losses": l,
                "offense_index": None,
                "defense_index": None,
                "t5_ok": False,
                "t5_reason": "no W-L games; team_strength_from_record would silent-default 1.0",
            }
            continue
        off, deff = team_strength_from_record(summary)
        # Malformed path in team_strength_from_record returns (1.0, 1.0).
        # Valid W-L never needs that fallback; still record ties separately.
        out[team] = {
            "record": summary,
            "ties": t,
            "wins": w,
            "losses": l,
            "games_in_record": w + l,
            "offense_index": float(off),
            "defense_index": float(deff),
            "t5_ok": True,
            "t5_source": "team_strength_from_record",
            "t5_formula": "off=clamp(0.90+0.22*wp,0.82,1.18); def=clamp(0.92+0.20*wp,0.82,1.20); wp=W/(W+L); ties recorded, excluded from wp denom",
        }
    return out


def build_current_efficiency(
    situational: List[Dict[str, Any]],
    rolling: List[Dict[str, Any]],
    records: Dict[str, Dict[str, Any]],
    as_of_week: int,
    as_of_label: str,
) -> Dict[str, Dict[str, Any]]:
    sit = [r for r in situational if int(r["week"]) <= as_of_week]
    roll = [r for r in rolling if int(r["week"]) <= as_of_week]
    latest_roll = {}
    for row in roll:
        prev = latest_roll.get(row["team"])
        if prev is None or int(row["week"]) > int(prev["week"]):
            latest_roll[row["team"]] = row

    out: Dict[str, Dict[str, Any]] = {}
    by_team: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in sit:
        by_team[row["team"]].append(row)
    for team in ENGINE_TEAMS:
        rows = sorted(by_team.get(team, []), key=lambda r: r["week"])
        rec = records.get(team) or {}
        roll_row = latest_roll.get(team) or {}
        games = len(rows)
        out[team] = {
            "team": team,
            "schedule_team": schedule_team(team),
            "games_played": games,
            "as_of_week": as_of_week,
            "as_of": as_of_label,
            "source": "nflverse_2026_inseason_only",
            "2025_prior_used": False,
            "record": rec.get("record"),
            "ties": rec.get("ties"),
            "wins": rec.get("wins"),
            "losses": rec.get("losses"),
            "offense_index": rec.get("offense_index"),
            "defense_index": rec.get("defense_index"),
            "t5_ok": bool(rec.get("t5_ok")),
            "t5_source": rec.get("t5_source") or rec.get("t5_reason"),
            "off_epa_5g": roll_row.get("off_epa_per_play_5g"),
            "def_epa_allowed_5g": roll_row.get("def_epa_allowed_per_play_5g"),
            "success_5g": roll_row.get("success_rate_offense_5g"),
            "success_defense_allowed_5g": roll_row.get("success_rate_defense_allowed_5g"),
            "pass_rate_5g": roll_row.get("pass_rate_5g"),
            "pressure_rate_allowed_5g": roll_row.get("pressure_rate_allowed_5g"),
            "pressure_rate_generated_5g": roll_row.get("pressure_rate_generated_5g"),
            "red_zone_td_rate_5g": roll_row.get("red_zone_td_rate_5g"),
            "games_in_window_5": roll_row.get("games_in_window_5"),
            "rolling_as_of_week": roll_row.get("week"),
            "conversion": "T5 team_strength_from_record on 2026 W-L; T2 rolling 5g from 2026 situational",
        }
    return out


REQUIRED_20 = (
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
    "home_pass_rate_5g",
    "away_pass_rate_5g",
    "home_success_offense_5g",
    "away_success_offense_5g",
    "home_success_defense_allowed_5g",
    "away_success_defense_allowed_5g",
    "matchup_diff_off_epa_5g",
    "matchup_diff_def_epa_allowed_5g",
    "matchup_diff_success_rate_5g",
    "matchup_diff_pressure_generated_5g",
    "matchup_diff_pressure_allowed_5g",
    "matchup_diff_red_zone_td_rate_5g",
)

# NflGameInputs @1b39f4e9 — v2 §3 CATCH-ALL: any field not in REQUIRED_20
# and not in REQUIRED_CONTEXT must be None. Derived from the live dataclass
# so new OUTSIDE fields cannot silently drop out of the gate.
from src.services.nfl_simulator import NflGameInputs

REQUIRED_CONTEXT = (
    "game_id",
    "home_team",
    "away_team",
    "matchup_season",
    "matchup_week",
    "rest_days_home",
    "rest_days_away",
)
OUTSIDE_MUST_BE_NONE = tuple(
    name
    for name in NflGameInputs.__dataclass_fields__
    if name not in REQUIRED_20 and name not in REQUIRED_CONTEXT
)


def _finite(value: Any) -> bool:
    if value is None:
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return number == number and number not in (float("inf"), float("-inf"))


def gate_required_20(row: Dict[str, Any]) -> Dict[str, Any]:
    missing = [name for name in REQUIRED_20 if not _finite(row.get(name))]
    t5_reject = not row.get("t5_ok")
    window = row.get("games_in_window_5")
    window_reject = window is None or int(window) < 5
    leakage = int(row.get("rolling_as_of_week") or 0) >= 9
    prior = bool(row.get("2025_prior_used"))
    reject = bool(missing or t5_reject or window_reject or leakage or prior)
    reasons = []
    if missing:
        reasons.append(f"missing_or_nonfinite:{','.join(missing)}")
    if t5_reject:
        reasons.append("t5_record_default_or_missing")
    if window_reject:
        reasons.append(f"games_in_window_5={window}")
    if leakage:
        reasons.append("week9_rolling_consumed")
    if prior:
        reasons.append("2025_prior_used")
    return {
        "row_status": "REJECT" if reject else "ACCEPT",
        "reject_reasons": reasons,
    }


def build_w09_pack(
    current: Dict[str, Dict[str, Any]],
    w9_games: List[Dict[str, Any]],
    as_of_week: int,
    as_of_label: str,
) -> Dict[str, Any]:
    rows = []
    missing_teams = []
    for game in w9_games:
        home = game["home_team"]
        away = game["away_team"]
        h = current.get(home)
        a = current.get(away)
        if h is None or a is None:
            missing_teams.append({"game_id": game["game_id"], "home": home, "away": away})
            continue
        matchup_pack = {
            "season": SEASON,
            "week": 9,
            "game_id": game["game_id"],
            "home_team": home,
            "away_team": away,
            "home_off_epa_5g": h.get("off_epa_5g"),
            "away_off_epa_5g": a.get("off_epa_5g"),
            "home_def_epa_allowed_5g": h.get("def_epa_allowed_5g"),
            "away_def_epa_allowed_5g": a.get("def_epa_allowed_5g"),
            "home_pass_rate_5g": h.get("pass_rate_5g"),
            "away_pass_rate_5g": a.get("pass_rate_5g"),
            "home_success_offense_5g": h.get("success_5g"),
            "away_success_offense_5g": a.get("success_5g"),
            "home_success_defense_allowed_5g": h.get("success_defense_allowed_5g"),
            "away_success_defense_allowed_5g": a.get("success_defense_allowed_5g"),
            "diff_off_epa_5g": (
                None
                if h.get("off_epa_5g") is None or a.get("off_epa_5g") is None
                else float(h["off_epa_5g"]) - float(a["off_epa_5g"])
            ),
            "diff_def_epa_allowed_5g": (
                None
                if h.get("def_epa_allowed_5g") is None or a.get("def_epa_allowed_5g") is None
                else float(a["def_epa_allowed_5g"]) - float(h["def_epa_allowed_5g"])
            ),
            "diff_pressure_generated_5g": (
                None
                if h.get("pressure_rate_generated_5g") is None
                or a.get("pressure_rate_generated_5g") is None
                else float(h["pressure_rate_generated_5g"])
                - float(a["pressure_rate_generated_5g"])
            ),
            "diff_pressure_allowed_5g": (
                None
                if h.get("pressure_rate_allowed_5g") is None
                or a.get("pressure_rate_allowed_5g") is None
                else float(a["pressure_rate_allowed_5g"])
                - float(h["pressure_rate_allowed_5g"])
            ),
            "diff_red_zone_td_rate_5g": (
                None
                if h.get("red_zone_td_rate_5g") is None or a.get("red_zone_td_rate_5g") is None
                else float(h["red_zone_td_rate_5g"]) - float(a["red_zone_td_rate_5g"])
            ),
        }
        kwargs = matchup_pack_to_sim_input_kwargs(matchup_pack)
        both_success = (
            h.get("success_5g") is not None
            and a.get("success_5g") is not None
            and h.get("success_defense_allowed_5g") is not None
            and a.get("success_defense_allowed_5g") is not None
        )
        rest_home = rest_days_from_schedule(game.get("kickoff_utc"))
        rest_away = rest_days_from_schedule(game.get("kickoff_utc"))
        row = {
            "game_id": game["game_id"],
            "season": SEASON,
            "week": 9,
            "home_team": home,
            "away_team": away,
            "matchup_season": 2026,
            "matchup_week": 9,
            "kickoff_utc": game["kickoff_utc"],
            "offense_index_home": h.get("offense_index"),
            "offense_index_away": a.get("offense_index"),
            "defense_index_home": h.get("defense_index"),
            "defense_index_away": a.get("defense_index"),
            "home_off_epa_5g": kwargs.get("home_off_epa_5g"),
            "away_off_epa_5g": kwargs.get("away_off_epa_5g"),
            "home_def_epa_allowed_5g": kwargs.get("home_def_epa_allowed_5g"),
            "away_def_epa_allowed_5g": kwargs.get("away_def_epa_allowed_5g"),
            "home_pass_rate_5g": kwargs.get("home_pass_rate_5g"),
            "away_pass_rate_5g": kwargs.get("away_pass_rate_5g"),
            "home_success_offense_5g": kwargs.get("home_success_offense_5g"),
            "away_success_offense_5g": kwargs.get("away_success_offense_5g"),
            "home_success_defense_allowed_5g": kwargs.get(
                "home_success_defense_allowed_5g"
            ),
            "away_success_defense_allowed_5g": kwargs.get(
                "away_success_defense_allowed_5g"
            ),
            "matchup_diff_off_epa_5g": kwargs.get("matchup_diff_off_epa_5g"),
            "matchup_diff_def_epa_allowed_5g": kwargs.get(
                "matchup_diff_def_epa_allowed_5g"
            ),
            "matchup_diff_success_rate_5g": kwargs.get("matchup_diff_success_rate_5g"),
            "matchup_diff_pressure_generated_5g": kwargs.get(
                "matchup_diff_pressure_generated_5g"
            ),
            "matchup_diff_pressure_allowed_5g": kwargs.get(
                "matchup_diff_pressure_allowed_5g"
            ),
            "matchup_diff_red_zone_td_rate_5g": kwargs.get(
                "matchup_diff_red_zone_td_rate_5g"
            ),
            "t4_both_success_terms": both_success,
            "rest_days_home": rest_home,
            "rest_days_away": rest_away,
            "rest_days_source": "nfl_data.rest_days_from_schedule",
            "t5_ok": bool(h.get("t5_ok") and a.get("t5_ok")),
            "home_record": h.get("record"),
            "away_record": a.get("record"),
            "games_in_window_5": min(
                int(h.get("games_in_window_5") or 0),
                int(a.get("games_in_window_5") or 0),
            ),
            "rolling_as_of_week": max(
                int(h.get("rolling_as_of_week") or 0),
                int(a.get("rolling_as_of_week") or 0),
            ),
            "as_of_week": as_of_week,
            "as_of": as_of_label,
            "2025_prior_used": False,
            "overlays": "OFF",
            "market_inputs": "NONE",
        }
        for name in OUTSIDE_MUST_BE_NONE:
            row[name] = None
        if not both_success:
            row["matchup_diff_success_rate_5g"] = None
        gate = gate_required_20(row)
        row.update(gate)
        rows.append(row)
    accept = [r for r in rows if r["row_status"] == "ACCEPT"]
    return {
        "season": SEASON,
        "week": 9,
        "as_of_week": as_of_week,
        "as_of": as_of_label,
        "code_commit": IF_CODE_COMMIT,
        "alex_contract_sha8": ALEX_CONTRACT_V2_SHA8,
        "alex_contract_sha256": ALEX_CONTRACT_V2_SHA256,
        "alex_contract_version": "v2",
        "alex_contract_parent_v1_sha8": ALEX_CONTRACT_V1_SHA8,
        "contract_bind": CONTRACT_BIND,
        "imv_pass_contract": IMV_PASS_CONTRACT_SHA8,
        "imv_pass_contract_sha256": IMV_PASS_CONTRACT_SHA256,
        "imv_return_parent": IMV_RETURN_PARENT_SHA8,
        "imv_d1": "CLOSED — IMV PASS_CONTRACT 1a53bbd3 on v2 b41f4b43",
        "addon_tickets": list(ADDON_TICKETS),
        "market_blend": 0,
        "n_games": len(rows),
        "n_accept": len(accept),
        "n_reject": len(rows) - len(accept),
        "week_scoring_admissible": False,
        "missing_team_rows": missing_teams,
        "required_20": list(REQUIRED_20),
        "outside_fields_none": list(OUTSIDE_MUST_BE_NONE),
        "games": rows,
    }


def dq_checks(
    *,
    coverage: Dict[str, Any],
    current: Dict[str, Dict[str, Any]],
    situational: List[Dict[str, Any]],
    pack: Dict[str, Any],
    panel_week: int = CONSISTENT_PANEL_WEEK,
) -> Dict[str, Any]:
    checks = []

    def add(name: str, ok: bool, detail: Any) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    add("teams_32", set(current) == set(ENGINE_TEAMS), {"n": len(current)})
    add(
        "through_w7_complete",
        bool(coverage["through_w7_complete"]),
        coverage["by_week"],
    )
    add(
        "through_w8_not_declared",
        not coverage["through_w8_complete"],
        {
            "missing": coverage["week8_missing"],
            "complete": coverage["week8_complete_count"],
            "expected": coverage["week8_expected_count"],
        },
    )
    add(
        "no_2025_prior_flag",
        all(not row.get("2025_prior_used") for row in current.values()),
        "current-season 2026 only",
    )
    add(
        "situational_weeks_le_7_in_panel",
        all(int(r["week"]) <= panel_week for r in situational),
        {"max_week": max((int(r["week"]) for r in situational), default=None), "panel_week": panel_week},
    )
    add(
        "t5_ok_32",
        all(row.get("t5_ok") and row.get("offense_index") is not None for row in current.values()),
        "team_strength_from_record on 2026 W-L",
    )
    add(
        "five_g_present",
        all(
            row.get("off_epa_5g") is not None
            and row.get("pass_rate_5g") is not None
            and row.get("pressure_rate_generated_5g") is not None
            and row.get("red_zone_td_rate_5g") is not None
            for row in current.values()
        ),
        "5g features non-null including pressure/RZ",
    )
    add(
        "indices_in_t5_clamp",
        all(
            row.get("offense_index") is not None
            and row.get("defense_index") is not None
            and 0.82 <= float(row["offense_index"]) <= 1.18
            and 0.82 <= float(row["defense_index"]) <= 1.20
            for row in current.values()
        ),
        "team_strength_from_record clamps",
    )
    add(
        "contract_20_on_accept_or_labeled_reject",
        all(r.get("row_status") in {"ACCEPT", "REJECT"} for r in pack.get("games") or []),
        {"n_accept": pack.get("n_accept"), "n_reject": pack.get("n_reject")},
    )
    add("w09_games_15", int(pack.get("n_games") or 0) == 15, pack.get("n_games"))
    add(
        "w09_no_missing_teams",
        not pack.get("missing_team_rows"),
        pack.get("missing_team_rows"),
    )
    add(
        "no_future_week_in_current",
        all(int(row.get("as_of_week") or 0) <= panel_week for row in current.values()),
        f"as_of_week<={panel_week}",
    )
    add(
        "v2_catchall_nfl_game_inputs_none",
        all(
            all(g.get(name) is None for name in OUTSIDE_MUST_BE_NONE)
            for g in pack.get("games") or []
        ),
        {
            "n_catchall": len(OUTSIDE_MUST_BE_NONE),
            "note": "Alex v2 b41f4b43 catch-all live from NflGameInputs; D1 CLOSED via PASS_CONTRACT 1a53bbd3",
        },
    )
    failed = [c for c in checks if not c["ok"] and c["name"] != "through_w8_not_declared"]
    # through_w8_not_declared is informational expected-true for DATA_PARTIAL
    return {
        "checks": checks,
        "failed": [c["name"] for c in failed],
        "pass": not failed,
    }


def decide_status(coverage: Dict[str, Any], dq: Dict[str, Any], current: Dict[str, Any]) -> str:
    if not current or not coverage.get("through_w7_complete"):
        if not current:
            return "DATA_UNAVAILABLE"
        return "DATA_PARTIAL"
    if coverage.get("through_w8_complete") and dq.get("pass"):
        return "DATA_READY"
    return "DATA_PARTIAL"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-fetch", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = _now_utc()
    schedule = load_schedule()
    raw_path = RAW_DIR / "play_by_play_2026.parquet"
    if args.skip_fetch and raw_path.exists():
        source = {
            "url": APPROVED_PBP_URL,
            "source_id": APPROVED_SOURCE_ID,
            "fetched_at_utc": None,
            "bytes": raw_path.stat().st_size,
            "sha256": sha256_file(raw_path),
            "path": str(raw_path.relative_to(ROOT)),
            "skip_fetch": True,
            "license": LICENSE_NOTE,
            "access": "public HTTPS; no credential; no paid vendor",
            "hash_before_parse": True,
        }
    else:
        source = archive_pbp(raw_path, fetch_pbp(raw_path))

    frame = load_pbp_frame(raw_path)
    pbp_games = complete_games_from_pbp(frame)
    coverage = classify_schedule_games(schedule["w1_w8"], pbp_games, now)
    panel_week = panel_week_from_coverage(coverage)
    if coverage.get("through_w8_complete") and source.get("skip_fetch"):
        raise RuntimeError(
            "DATA_READY requires re-fetch + archive + fetched_at_utc (O-a); "
            "refuse --skip-fetch when W8 is 14/14"
        )

    # Through-W7 while W8 incomplete. Lift to W8 only after 14/14 including MNF.
    situational = build_situational(frame, panel_week)
    rolling = build_rolling(situational)
    if panel_week >= READY_PANEL_WEEK:
        as_of_label = f"2026 through W8 final as_of {coverage['as_of_utc']}"
    else:
        as_of_label = (
            f"2026 through W{panel_week} final; W8 incomplete as_of {coverage['as_of_utc']}"
        )
    completed_sched = [
        g
        for g in coverage["games"]
        if g["status"] == "COMPLETE" and int(g["week"]) <= panel_week
    ]
    records = records_from_completed(completed_sched, panel_week)
    current = build_current_efficiency(
        situational, rolling, records, panel_week, as_of_label
    )
    pack = build_w09_pack(
        current, schedule["w9"], panel_week, as_of_label
    )
    dq = dq_checks(
        coverage=coverage,
        current=current,
        situational=situational,
        pack=pack,
        panel_week=panel_week,
    )
    status = decide_status(coverage, dq, current)

    inventory = {
        "ticket": "t4770u",
        "addon_tickets": list(ADDON_TICKETS),
        "decision": DECISION_SHA8,
        "contract_bind": CONTRACT_BIND,
        "imv_pass_contract": IMV_PASS_CONTRACT_SHA8,
        "filed_utc": _iso(now),
        "preferred_sources": [
            {
                "id": "packaged_efficiency_backbone_2026",
                "path": "services/model-service/src/services/nfl_season_engine/data/nfl_team_efficiency_backbone_2026.json",
                "status": "EXISTING AND VERIFIED (packaged) — 2025 priors as_of 2026-08-08; NOT used as 2026 in-season substitute",
            },
            {
                "id": "packaged_epa_priors_2026",
                "path": "services/model-service/src/services/nfl_season_engine/data/nfl_team_epa_priors_2026.json",
                "status": "EXISTING AND VERIFIED (packaged) — 2025 priors; NOT used as 2026 in-season substitute",
            },
            {
                "id": "canonical_schedule_2026",
                "path": schedule["meta"]["path"],
                "status": "EXISTING AND VERIFIED (packaged)",
                "sha256": schedule["meta"]["sha256"],
                "as_of": schedule["meta"]["as_of"],
            },
            {
                "id": "t4696u_s1_pbp_restage",
                "status": "CLEARed URL template 2012–2022 only; 2026 not in that restage",
                "url_template": "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.parquet",
                "pr": "#654 DRAFT/OPEN — do not merge; binaries gitignored",
            },
            {
                "id": "t4139u_w7",
                "status": "referenced by CoS; no artifact on deploy-vercel / Slack / Notion / this VM",
            },
            {
                "id": "t4166u_w4_w6",
                "status": "referenced by CoS; no artifact on deploy-vercel / Slack / Notion / this VM",
            },
            {
                "id": "DATABASE_URL / Railway C10",
                "status": "HOLD — not used",
            },
        ],
        "used_source": source,
        "lineage": APPROVED_CLEAR_LINEAGE,
    }

    e1_retry = {
        "scoring_admissible_now": False,
        "reason": "through-W8 not complete; sealed panel is through W7 only",
        "do_not": [
            "retry E1 scoring-admissible emit on this DATA_PARTIAL set",
            "substitute 2025 packaged priors for missing W8 games",
            "restore C10 / Railway / DATABASE_URL",
            "open Odds / E2",
            "change CLEAR-P1 #662 merge status",
        ],
        "retry_when": [
            "W8 slate complete after 2026-W08-CHI@SEA kickoff 2026-11-03T01:15:00Z (MNF)",
            "re-fetch approved nflverse play_by_play_2026.parquet (same URL)",
            "builder reports through_w8_complete=true and 32/32 teams",
            "IMV PASS_CONTRACT 1a53bbd3 is on file for v2 b41f4b43 (D1 CLOSED) — not a DATA ACCEPT",
            "IMV ACCEPT of through-W8 inputs against the PASSed v2 contract (separate DATA grade)",
            "then E1 retry inside Tue 2026-11-03 00:00 – Wed 2026-11-04 23:59 America/New_York",
        ],
        "window_note": (
            "W9 O4 window starts Tue 00:00 ET, immediately after MNF. "
            "If nflverse PBP lands after Tue 00:00 ET, emit_ts may still sit inside the window "
            "provided as_of <= emit_ts and IMV ACCEPT is on file."
        ),
        "engineering_demo_only": (
            "W9 consume pack + IF consume proof (t4776u: 20-field call graph + "
            "input-hash perturbation) may be used as an offline demo that Independent "
            "Fair actually consumes staged 2026 inputs. That is not O4 scoring-admissible."
        ),
    }

    report = {
        "ticket": "t4770u",
        "addon_tickets": list(ADDON_TICKETS),
        "decision": DECISION_SHA8,
        "alex_contract_sha8": ALEX_CONTRACT_V2_SHA8,
        "alex_contract_sha256": ALEX_CONTRACT_V2_SHA256,
        "alex_contract_version": "v2",
        "alex_contract_parent_v1_sha8": ALEX_CONTRACT_V1_SHA8,
        "contract_bind": CONTRACT_BIND,
        "imv_pass_contract": IMV_PASS_CONTRACT_SHA8,
        "imv_pass_contract_sha256": IMV_PASS_CONTRACT_SHA256,
        "imv_return_parent": IMV_RETURN_PARENT_SHA8,
        "imv_d1": "CLOSED — IMV PASS_CONTRACT 1a53bbd3 on v2 b41f4b43. PASS_CONTRACT ≠ DATA ACCEPT.",
        "status": status,
        "season": SEASON,
        "consistent_panel_through_week": panel_week,
        "through_w8_declared_complete": bool(coverage["through_w8_complete"]),
        "week8_missing": coverage["week8_missing"],
        "week8_complete_count": coverage["week8_complete_count"],
        "week8_expected_count": coverage["week8_expected_count"],
        "through_w7_complete": coverage["through_w7_complete"],
        "teams": len(current),
        "dq_pass": dq["pass"],
        "dq_failed": dq["failed"],
        "e1_retry": e1_retry,
        "locks": [
            "NFL NO-GO",
            "CERT=0",
            "Coming Soon ON",
            "F2 frozen",
            "C10 HOLD",
            "Odds HOLD 70c56700",
            "overlays OFF",
        ],
    }

    hashes = {}
    artifacts = {
        "SOURCE_MANIFEST.json": {
            **inventory,
            "pbp": source,
            "schedule": schedule["meta"],
        },
        "INVENTORY.json": inventory,
        "COVERAGE.json": {
            "as_of_utc": coverage["as_of_utc"],
            "by_week": coverage["by_week"],
            "week8_missing": coverage["week8_missing"],
            "through_w7_complete": coverage["through_w7_complete"],
            "through_w8_complete": coverage["through_w8_complete"],
            "complete_game_ids": coverage["complete_game_ids"],
            "incomplete_in_pbp": coverage["incomplete_in_pbp"],
            "not_yet_kicked": coverage["not_yet_kicked"],
        },
        "DQ.json": dq,
        "STATUS.json": report,
        "team_situational_weekly.json": {
            "season": SEASON,
            "max_week": panel_week,
            "n": len(situational),
            "source": "nflverse",
            "rows": situational,
        },
        "team_rolling_features_weekly.json": {
            "season": SEASON,
            "max_week": panel_week,
            "n": len(rolling),
            "source": "nflverse",
            "window": "5g/3g matching ingest.py",
            "rows": rolling,
        },
        "w09_consume_pack.json": pack,
        "rest_days_spotcheck.json": rest_days_spotcheck(pack.get("games") or []),
    }
    current_name = (
        "team_efficiency_current_through_w8.json"
        if panel_week >= READY_PANEL_WEEK
        else "team_efficiency_current_through_w7.json"
    )
    artifacts[current_name] = {
        "season": SEASON,
        "as_of_week": panel_week,
        "as_of": as_of_label,
        "n": len(current),
        "2025_prior_used": False,
        "teams": current,
    }
    for name, obj in artifacts.items():
        hashes[name] = write_json(OUT_DIR / name, obj)
    # Reseal the whole packet so authority copies / STANDBY notes stay listed.
    for path in sorted(OUT_DIR.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            hashes[path.name] = sha256_file(path)
    sums = "".join(f"{digest}  {name}\n" for name, digest in sorted(hashes.items()))
    (OUT_DIR / "SHA256SUMS").write_text(sums, encoding="utf-8")
    print(json.dumps({"status": status, "out": str(OUT_DIR), "hashes": hashes}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
