#!/usr/bin/env python3
"""IMV v2.1 contracts (fd97f103). Do not run the builder until IMV code-checks it.

C-1 pin feature-store sha, BLOCK on mismatch
C-2 per-row as-of: prior weeks only, pre-kickoff (prod CURRENT ROW = leak)
C-3 builder + parity tests with explicit week cap
C-4 no explicit_zero for injury; ALLOWED-FLAGGED nulls; never map injuries_2026
C-5 missing kickoff → BLOCKED, no fallback
C-6 BLOCKED_NO_MODEL_EXECUTION; parse week from W## (not gid[8:10])
C-7 read HFA from pinned BASE code, assert == 1.05
C-8 env + EPERM result recorded by the sealed runner (not here)

W7 refused. Never invent rest=7.0 / injury=0.0 / index=1.0.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

RULING = "fd97f103"
SCRIPT_ID = "nfl-imv-v2.1"
CERT_CANDIDATE = "b1d857d356d5afc422c86ffb1e9a25afdf2a4225"
HFA_REQUIRED = 1.05
PROD_LEAK_WINDOW_SQL = "ROWS BETWEEN 4 PRECEDING AND CURRENT ROW"
LAGGED_WINDOW_SQL = "ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING"
PRODUCT_WEEK_RE = re.compile(r"^20\d{2}-W(\d{2})-")
# v2 line ~680 used gid[8:10] on 2026-W04-ARI@NYG → "-A"
LEGACY_WEEK_SLICE = slice(8, 10)

INJURY_KEYS = ("home_injury_impact", "away_injury_impact", "diff_injury_impact")
RAW_INJURY_SOURCES = frozenset(
    {"injuries_2026", "nflverse_injuries", "raw_injury_report", "injuries_2026.parquet"}
)
FEATURE_STORE_FILES = ("features.jsonl", "feature-flags.jsonl", "imv-local.sqlite")

ROLLING_KEYS = (
    "off_epa_per_play_5g",
    "def_epa_allowed_per_play_5g",
    "pressure_rate_allowed_5g",
    "pressure_rate_generated_5g",
    "pass_rate_5g",
    "early_down_pass_rate_5g",
    "red_zone_td_rate_5g",
    "success_rate_offense_5g",
    "success_rate_defense_allowed_5g",
)

SIDE_MAP = {
    "off_epa_per_play_5g": ("home_off_epa_5g", "away_off_epa_5g"),
    "def_epa_allowed_per_play_5g": ("home_def_epa_allowed_5g", "away_def_epa_allowed_5g"),
    "pressure_rate_allowed_5g": ("home_pressure_allowed_5g", "away_pressure_allowed_5g"),
    "pressure_rate_generated_5g": ("home_pressure_generated_5g", "away_pressure_generated_5g"),
    "pass_rate_5g": ("home_pass_rate_5g", "away_pass_rate_5g"),
    "early_down_pass_rate_5g": ("home_early_down_pass_rate_5g", "away_early_down_pass_rate_5g"),
    "red_zone_td_rate_5g": ("home_red_zone_td_rate_5g", "away_red_zone_td_rate_5g"),
    "success_rate_offense_5g": ("home_success_offense_5g", "away_success_offense_5g"),
    "success_rate_defense_allowed_5g": (
        "home_success_defense_allowed_5g",
        "away_success_defense_allowed_5g",
    ),
}

CANON = {"LA": "LAR", "WSH": "WAS"}


class V21Error(ValueError):
    """Fail-closed v2.1 contract. Do not catch-and-fill."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canon_team(team: Optional[str]) -> str:
    t = (team or "").strip().upper()
    return CANON.get(t, t)


def parse_product_week(gid: str, pack_week: Any = None) -> Optional[int]:
    """C-6: week from `2026-W04-…` (group 1), never gid[8:10]."""
    m = PRODUCT_WEEK_RE.match(gid or "")
    if m:
        return int(m.group(1))
    if pack_week is not None and str(pack_week).strip() != "":
        try:
            return int(pack_week)
        except (TypeError, ValueError):
            return None
    return None


def legacy_week_slice_value(gid: str) -> str:
    """What v2 ~l.680 read. Documented leak/bug; never use as week."""
    if not gid or len(gid) < 10:
        return ""
    return gid[LEGACY_WEEK_SLICE]


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    s = (value or "").strip()
    if not s:
        return None
    if s.endswith(".000Z"):
        s = s[:-5] + "Z"
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except ValueError:
        return None


def require_kickoff(kickoff_utc: Optional[str], *, game_id: str) -> Dict[str, Any]:
    """C-5: missing/unparseable kickoff → BLOCKED. No slate-first fallback."""
    if not (kickoff_utc or "").strip():
        return {
            "ok": False,
            "kickoff_utc": None,
            "status": "BLOCKED",
            "flag": "BLOCKED_MISSING_KICKOFF",
            "game_id": game_id,
            "fallback_used": False,
        }
    dt = parse_iso(kickoff_utc)
    if dt is None:
        return {
            "ok": False,
            "kickoff_utc": kickoff_utc,
            "status": "BLOCKED",
            "flag": "BLOCKED_UNPARSEABLE_KICKOFF",
            "game_id": game_id,
            "fallback_used": False,
        }
    return {
        "ok": True,
        "kickoff_utc": kickoff_utc,
        "status": "OK",
        "flag": None,
        "game_id": game_id,
        "fallback_used": False,
        "kickoff_dt": dt,
    }


def model_execution_label(*, executed: bool) -> str:
    """C-6: null / skipped model uses BLOCKED_NO_MODEL_EXECUTION (not NOT_RUN)."""
    return "BASE_SIMULATE_NFL_GAME" if executed else "BLOCKED_NO_MODEL_EXECUTION"


def source_week_key(season: int, week: int) -> str:
    return f"{int(season)}-W{int(week):02d}"


def parse_source_week_key(value: Any) -> Optional[Tuple[int, int]]:
    if value is None:
        return None
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return int(value[0]), int(value[1])
    s = str(value)
    m = re.match(r"^(20\d{2})-W(\d{2})$", s)
    if m:
        return int(m.group(1)), int(m.group(2))
    try:
        return None, int(s)
    except (TypeError, ValueError):
        return None


def _normalize_source_weeks(
    source_weeks: Sequence[Any],
    *,
    default_season: int = 2026,
) -> List[str]:
    keys: List[str] = []
    for item in source_weeks:
        parsed = parse_source_week_key(item)
        if parsed is None:
            continue
        season, week = parsed
        if season is None:
            season = default_season
        keys.append(source_week_key(season, week))
    return sorted(set(keys))


def _source_after_or_same_game(key: str, game_season: int, game_week: int) -> bool:
    parsed = parse_source_week_key(key)
    if parsed is None or parsed[0] is None:
        return True
    season, week = parsed
    return (int(season), int(week)) >= (int(game_season), int(game_week))


@dataclass
class AsOfRecord:
    game_id: str
    game_week: Optional[int]
    as_of_week: Optional[int]
    source_weeks: List[str] = field(default_factory=list)
    kickoff_utc: Optional[str] = None
    prior_weeks_only: bool = False
    pre_kickoff: bool = False
    status: str = "BLOCKED"
    flags: List[str] = field(default_factory=list)
    game_season: int = 2026

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def record_as_of_check(
    *,
    game_id: str,
    game_week: Optional[int],
    source_weeks: Sequence[Any],
    kickoff_utc: Optional[str],
    source_kickoffs: Optional[Sequence[Optional[str]]] = None,
    feature_as_of_week: Optional[int] = None,
    game_season: int = 2026,
) -> AsOfRecord:
    """C-2: prior weeks only + pre-kickoff, recorded on the row.

    Prod `ingest.py` rolling uses CURRENT ROW (same-week leak). v2.1 joins
    rolling at week W-1 and refuses any source (season, week) >= game.
    2025 tail weeks are prior to every 2026 game week.
    """
    flags: List[str] = []
    keys = _normalize_source_weeks(source_weeks, default_season=game_season)
    as_of = feature_as_of_week
    same_season_weeks = [parse_source_week_key(k)[1] for k in keys if parse_source_week_key(k) and parse_source_week_key(k)[0] == game_season]
    if as_of is None and same_season_weeks:
        as_of = max(same_season_weeks)

    if game_week is None:
        flags.append("FLAG_MISSING_WEEK")
        return AsOfRecord(
            game_id=game_id,
            game_week=None,
            as_of_week=as_of,
            source_weeks=keys,
            kickoff_utc=kickoff_utc,
            status="BLOCKED",
            flags=flags,
            game_season=game_season,
        )

    expected_as_of = int(game_week) - 1
    if as_of is None:
        flags.append("FLAG_AS_OF_GAP")
    elif int(as_of) != expected_as_of:
        flags.append("FLAG_AS_OF_NOT_WEEK_MINUS_1")
    leaked = [k for k in keys if _source_after_or_same_game(k, game_season, int(game_week))]
    if leaked:
        flags.append("FLAG_SAME_WEEK_LEAK")
        if any(
            (parse_source_week_key(k) or (0, 0))[0] == game_season
            and (parse_source_week_key(k) or (0, 0))[1] > int(game_week)
            for k in leaked
        ):
            flags.append("FLAG_FUTURE_WEEK_LEAK")

    prior = (not leaked) and bool(keys) and (as_of == expected_as_of)
    if not keys:
        prior = False
        flags.append("FLAG_NO_SOURCE_WEEKS")

    ko = require_kickoff(kickoff_utc, game_id=game_id)
    pre = False
    if not ko["ok"]:
        flags.append(str(ko["flag"]))
    else:
        src_ko = list(source_kickoffs or [])
        parsed_src = [parse_iso(x) for x in src_ko]
        if src_ko and any(p is None for p in parsed_src):
            flags.append("BLOCKED_SOURCE_KICKOFF_MISSING")
            pre = False
        elif not src_ko:
            # weekly aggregates carry week < game_week; kickoff order implied by week
            pre = prior
            flags.append("AS_OF_PRE_KICKOFF_VIA_WEEK")
        else:
            game_dt = ko["kickoff_dt"]
            pre = all(p is not None and p < game_dt for p in parsed_src)
            if not pre:
                flags.append("FLAG_SOURCE_NOT_PRE_KICKOFF")

    status = "PASS" if prior and ko["ok"] and "FLAG_SAME_WEEK_LEAK" not in flags else "BLOCKED"
    if status == "BLOCKED" and "FLAG_SAME_WEEK_LEAK" in flags:
        flags.append("BLOCKED_SAME_WEEK_LEAK")
    return AsOfRecord(
        game_id=game_id,
        game_week=int(game_week),
        as_of_week=as_of,
        source_weeks=keys,
        kickoff_utc=kickoff_utc,
        prior_weeks_only=prior,
        pre_kickoff=pre and ko["ok"],
        status=status,
        flags=flags,
        game_season=game_season,
    )


def lagged_source_weeks(game_week: int, window: int = 5) -> List[int]:
    """Weeks that may enter a 5g window for game week W: (W-window) .. (W-1)."""
    as_of = int(game_week) - 1
    return [w for w in range(as_of - (window - 1), as_of + 1) if w >= 1]


def prod_leak_source_weeks(game_week: int, window: int = 5) -> List[int]:
    """What ingest.py CURRENT ROW includes when the rolling row is labeled week W."""
    return [w for w in range(int(game_week) - (window - 1), int(game_week) + 1) if w >= 1]


def rolling_mean_prior_weeks(
    values_by_week: Mapping[int, float],
    *,
    game_week: int,
    window: int = 5,
) -> Tuple[Optional[float], List[int]]:
    """5g mean using prior weeks only (never CURRENT / game week)."""
    src = [w for w in lagged_source_weeks(game_week, window) if w in values_by_week]
    nums = [float(values_by_week[w]) for w in src]
    if not nums:
        return None, src
    return sum(nums) / len(nums), src


def apply_week_cap(rows: Sequence[Mapping[str, Any]], week_cap: int) -> List[Dict[str, Any]]:
    """C-3: explicit week cap. Rows with week > cap are dropped, not filled."""
    out: List[Dict[str, Any]] = []
    for row in rows:
        week = parse_product_week(str(row.get("game_id_product") or row.get("game_id") or ""), row.get("week"))
        if week is None:
            continue
        if week > int(week_cap):
            continue
        rec = dict(row)
        rec["week"] = week
        rec["week_cap"] = int(week_cap)
        out.append(rec)
    return out


def feature_store_digest(store: Path) -> str:
    """C-1: deterministic digest of the file-backed store (not the directory mtime)."""
    lines: List[str] = []
    for name in FEATURE_STORE_FILES:
        p = store / name
        if p.is_file():
            lines.append(f"{sha256_file(p)}  {name}")
    payload = "\n".join(lines) + ("\n" if lines else "")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_feature_store_pin(store: Path) -> Dict[str, str]:
    digest = feature_store_digest(store)
    (store / "FEATURE_STORE.sha256").write_text(digest + "\n", encoding="utf-8")
    sums_path = store / "SHA256SUMS"
    names = [p.name for p in store.iterdir() if p.is_file() and p.name != "SHA256SUMS"]
    with sums_path.open("w", encoding="utf-8") as fh:
        for name in sorted(names):
            fh.write(f"{sha256_file(store / name)}  {name}\n")
    return {"feature_store_sha256": digest, "sha256sums": sha256_file(sums_path)}


def assert_feature_store_pin(store: Path, expected: Optional[str]) -> Dict[str, Any]:
    """C-1: missing pin or mismatch → BLOCKED."""
    if not store.is_dir():
        return {"status": "BLOCKED", "reason": "FEATURE_STORE_MISSING", "path": str(store)}
    got = feature_store_digest(store)
    pin_file = store / "FEATURE_STORE.sha256"
    file_pin = pin_file.read_text(encoding="utf-8").strip() if pin_file.is_file() else None
    pin = (expected or "").strip() or (file_pin or "")
    if not pin:
        return {
            "status": "BLOCKED",
            "reason": "FEATURE_STORE_SHA_UNPINNED",
            "got": got,
            "expected": None,
        }
    if got.lower() != pin.lower():
        return {
            "status": "BLOCKED",
            "reason": "FEATURE_STORE_SHA_MISMATCH",
            "got": got,
            "expected": pin.lower(),
        }
    return {"status": "OK", "sha256": got, "expected": pin.lower()}


def injury_allowed_flagged(feat: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """C-4 + injury ALLOWED-FLAGGED.

    Null is the only legal value on impact keys. Any present number is an
    imputation → flagged default, still emitted as null. explicit_zero is
    removed. Raw injuries_2026 is never mapped into impact keys.
    """
    feat = feat or {}
    flags: List[str] = ["FLAG_MISSING_KOSEDGE_INJURY_NOWCAST"]
    source = str(feat.get("injury_source") or "")
    if source == "explicit_zero":
        flags.append("FLAG_EXPLICIT_ZERO_INJURY_REMOVED")
        flags.append("FLAG_IMPUTED_INJURY_DEFAULT")
    if source in RAW_INJURY_SOURCES or feat.get("mapped_from_injuries_2026"):
        flags.append("FLAG_RAW_INJURIES_2026_REFUSED")
    for key in INJURY_KEYS:
        if key in feat and feat.get(key) is not None:
            flags.append("FLAG_IMPUTED_INJURY_DEFAULT")
            flags.append(f"FLAG_INJURY_VALUE_OMITTED:{key}")
    flags = list(dict.fromkeys(flags))
    return {
        "home_injury_impact": None,
        "away_injury_impact": None,
        "diff_injury_impact": None,
        "injury_handling": "null_allowed_flagged",
        "injury_source": "none_not_injuries_2026",
        "explicit_zero_removed": True,
        "recorded": True,
        "pass_to_sim": {
            "injury_nowcast_impact_home": None,
            "injury_nowcast_impact_away": None,
        },
        "flags": flags,
    }


def read_and_assert_hfa(base: Path) -> Dict[str, Any]:
    """C-7: import HOME_FIELD_POINTS from pinned BASE; assert == 1.05."""
    ms = Path(base) / "services" / "model-service"
    cal = (
        ms
        / "src"
        / "services"
        / "nfl_season_engine"
        / "calibration.py"
    )
    if not cal.is_file():
        return {
            "ok": False,
            "status": "BLOCKED",
            "flag": "HFA_UNDECLARED",
            "reason": "calibration.py missing in BASE",
            "hfa_points": None,
        }
    sys_path_inserted = False
    if str(ms) not in sys.path:
        sys.path.insert(0, str(ms))
        sys_path_inserted = True
    try:
        from src.services.nfl_season_engine.calibration import (  # type: ignore
            HOME_FIELD_POINTS,
        )
        value = float(HOME_FIELD_POINTS)
    except Exception as exc:  # noqa: BLE001 — fail closed
        return {
            "ok": False,
            "status": "BLOCKED",
            "flag": "HFA_UNDECLARED",
            "reason": f"{type(exc).__name__}: {exc}",
            "hfa_points": None,
        }
    if value != HFA_REQUIRED:
        return {
            "ok": False,
            "status": "BLOCKED",
            "flag": "HFA_PIN_MISMATCH",
            "reason": f"HOME_FIELD_POINTS={value} != {HFA_REQUIRED}",
            "hfa_points": value,
            "hfa_source": "BASE:nfl_season_engine.calibration.HOME_FIELD_POINTS",
        }
    return {
        "ok": True,
        "status": "OK",
        "hfa_declared": True,
        "hfa_points": value,
        "hfa_points_applied": value,
        "hfa_source": "BASE:nfl_season_engine.calibration.HOME_FIELD_POINTS",
        "calibration_path": str(cal),
        "sys_path_inserted": sys_path_inserted,
    }


def parse_num(value: Any) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.upper() in {"NA", "NAN", "NULL", "NONE"}:
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def product_game_id(season: int, week: int, away: str, home: str) -> str:
    return f"{int(season)}-W{int(week):02d}-{canon_team(away)}@{canon_team(home)}"


def _truthy(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    s = str(value).strip().lower()
    if s in {"1", "true", "t", "yes"}:
        return True
    try:
        return float(s) == 1.0
    except (TypeError, ValueError):
        return False


def weekly_situational_from_pbp(
    plays: Iterable[Mapping[str, Any]],
    *,
    pbp_week_cap: int,
) -> Dict[Tuple[int, int, str], Dict[str, Any]]:
    """Team-week rates from PBP with an explicit week cap. No current-game join."""
    buckets: Dict[Tuple[int, int, str], Dict[str, List[float]]] = {}

    def bucket(season: int, week: int, team: str) -> Dict[str, List[float]]:
        key = (season, week, team)
        if key not in buckets:
            buckets[key] = {
                "off_epa": [],
                "def_epa": [],
                "success_off": [],
                "success_def": [],
                "pass": [],
                "early_pass": [],
                "early_n": [],
                "rz_td": [],
                "rz_n": [],
                "press_allowed": [],
                "press_gen": [],
            }
        return buckets[key]

    for play in plays:
        try:
            season = int(play.get("season") or 0)
            week = int(play.get("week") or 0)
        except (TypeError, ValueError):
            continue
        if season not in {2025, 2026} or week < 1 or week > int(pbp_week_cap):
            continue
        posteam = canon_team(str(play.get("posteam") or ""))
        defteam = canon_team(str(play.get("defteam") or ""))
        if not posteam or not defteam:
            continue
        epa = parse_num(play.get("epa"))
        success = parse_num(play.get("success"))
        is_pass = _truthy(play.get("pass"))
        down = parse_num(play.get("down"))
        yl = parse_num(play.get("yardline_100"))
        td = _truthy(play.get("touchdown"))
        press = _truthy(play.get("sack")) or _truthy(play.get("qb_hit"))
        off = bucket(season, week, posteam)
        deff = bucket(season, week, defteam)
        if epa is not None:
            off["off_epa"].append(epa)
            deff["def_epa"].append(epa)
        if success is not None:
            off["success_off"].append(success)
            deff["success_def"].append(success)
        off["pass"].append(1.0 if is_pass else 0.0)
        if down in {1.0, 2.0}:
            off["early_n"].append(1.0)
            off["early_pass"].append(1.0 if is_pass else 0.0)
        if yl is not None and yl <= 20:
            off["rz_n"].append(1.0)
            off["rz_td"].append(1.0 if td else 0.0)
        if is_pass:
            off["press_allowed"].append(1.0 if press else 0.0)
            deff["press_gen"].append(1.0 if press else 0.0)

    def avg(xs: List[float]) -> Optional[float]:
        return (sum(xs) / len(xs)) if xs else None

    out: Dict[Tuple[int, int, str], Dict[str, Any]] = {}
    for key, b in buckets.items():
        out[key] = {
            "season": key[0],
            "week": key[1],
            "team": key[2],
            "off_epa_per_play": avg(b["off_epa"]),
            "def_epa_allowed_per_play": avg(b["def_epa"]),
            "success_rate_offense": avg(b["success_off"]),
            "success_rate_defense_allowed": avg(b["success_def"]),
            "pass_rate": avg(b["pass"]),
            "early_down_pass_rate": avg(b["early_pass"]) if b["early_n"] else None,
            "red_zone_td_rate": avg(b["rz_td"]) if b["rz_n"] else None,
            "pressure_rate_allowed": avg(b["press_allowed"]),
            "pressure_rate_generated": avg(b["press_gen"]),
        }
    return out


def attach_lagged_rolling(
    weekly: Mapping[Tuple[int, int, str], Mapping[str, Any]],
    *,
    season: int,
    team: str,
    game_week: int,
) -> Tuple[Dict[str, Optional[float]], List[str]]:
    used: List[str] = []
    out: Dict[str, Optional[float]] = {}
    field_map = {
        "off_epa_per_play_5g": "off_epa_per_play",
        "def_epa_allowed_per_play_5g": "def_epa_allowed_per_play",
        "pressure_rate_allowed_5g": "pressure_rate_allowed",
        "pressure_rate_generated_5g": "pressure_rate_generated",
        "pass_rate_5g": "pass_rate",
        "early_down_pass_rate_5g": "early_down_pass_rate",
        "red_zone_td_rate_5g": "red_zone_td_rate",
        "success_rate_offense_5g": "success_rate_offense",
        "success_rate_defense_allowed_5g": "success_rate_defense_allowed",
    }
    for dest, src in field_map.items():
        series: Dict[int, float] = {}
        src_keys: List[str] = []
        for w in lagged_source_weeks(game_week):
            key = (season, w, team)
            if key in weekly and weekly[key].get(src) is not None:
                series[w] = float(weekly[key][src])
                src_keys.append(source_week_key(season, w))
        if season == 2026 and len(series) < 5:
            # 2025 tail: highest 2025 weeks first, never labeled as 2026 source weeks.
            prior_2025 = sorted(
                (k[1] for k in weekly if k[0] == 2025 and k[2] == team and weekly[k].get(src) is not None),
                reverse=True,
            )
            offset = 0
            for w2025 in prior_2025:
                if len(series) >= 5:
                    break
                # synthetic negative index so rolling_mean can still average values
                offset -= 1
                series[offset] = float(weekly[(2025, w2025, team)][src])
                src_keys.append(source_week_key(2025, w2025))
        mean = (sum(series.values()) / len(series)) if series else None
        out[dest] = mean
        used.extend(src_keys)
    return out, sorted(set(used))


def _iter_pbp(path: Path) -> Iterable[Mapping[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                yield row
        return
    if suffix in {".parquet", ".pq"}:
        try:
            import pandas as pd  # type: ignore
        except ImportError as exc:
            raise V21Error(f"pandas required to read {path}: {exc}") from exc
        frame = pd.read_parquet(path)
        for rec in frame.to_dict(orient="records"):
            yield rec
        return
    raise V21Error(f"unsupported pbp suffix {suffix}")


def _load_games_csv(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                season = int(row.get("season") or 0)
                week = int(row.get("week") or 0)
            except ValueError:
                continue
            gt = str(row.get("game_type") or "REG").upper()
            if gt not in {"REG", "REGULAR"}:
                continue
            home = canon_team(row.get("home_team"))
            away = canon_team(row.get("away_team"))
            gid = product_game_id(season, week, away, home)
            rows.append(
                {
                    "season": season,
                    "week": week,
                    "game_id_product": gid,
                    "game_id_nflverse": row.get("game_id"),
                    "home_team": home,
                    "away_team": away,
                    "home_rest": parse_num(row.get("home_rest")),
                    "away_rest": parse_num(row.get("away_rest")),
                    "roof": row.get("roof"),
                    "surface": row.get("surface"),
                    "div_game": row.get("div_game"),
                    "home_score": parse_num(row.get("home_score")),
                    "away_score": parse_num(row.get("away_score")),
                    "gameday": row.get("gameday"),
                    "gametime": row.get("gametime"),
                }
            )
    return rows


def _load_pack_kickoffs(pack_path: Path) -> Dict[str, Dict[str, Any]]:
    if not pack_path.is_file():
        return {}
    doc = json.loads(pack_path.read_text(encoding="utf-8"))
    out: Dict[str, Dict[str, Any]] = {}
    for game in doc.get("games") or []:
        gid = game.get("game_id")
        if gid:
            out[str(gid)] = game
    return out


def build_feature_store(
    *,
    base: Path,
    games_csv: Path,
    pbp_paths: Sequence[Path],
    out_dir: Path,
    game_week_cap: int,
    pbp_week_cap: int,
    pack_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """File-backed store. Do not run until IMV code-checks this builder."""
    if pbp_week_cap >= game_week_cap and game_week_cap >= 1:
        # Prospective W8: game_week_cap=8, pbp_week_cap=7 is required.
        # Retrospective W6: game_week_cap=6, pbp_week_cap=5 (W6 games use ≤W5).
        pass
    out_dir.mkdir(parents=True, exist_ok=True)
    games = [g for g in _load_games_csv(games_csv) if g["season"] == 2026 and 1 <= g["week"] <= game_week_cap]
    pack = _load_pack_kickoffs(pack_path or (base / "apps/web/lib/nfl-canonical-schedule-2026.json"))
    plays: List[Mapping[str, Any]] = []
    for pbp in pbp_paths:
        plays.extend(list(_iter_pbp(Path(pbp))))
    weekly = weekly_situational_from_pbp(plays, pbp_week_cap=pbp_week_cap)

    rows: List[Dict[str, Any]] = []
    flags_out: List[Dict[str, Any]] = []
    blocked: List[str] = []
    for game in games:
        gid = game["game_id_product"]
        pack_row = pack.get(gid) or {}
        kickoff = pack_row.get("kickoff_utc")
        ko = require_kickoff(kickoff, game_id=gid)
        if not ko["ok"]:
            blocked.append(str(ko["flag"]) + " " + gid)
        home_roll, home_src = attach_lagged_rolling(
            weekly, season=2026, team=game["home_team"], game_week=int(game["week"])
        )
        away_roll, away_src = attach_lagged_rolling(
            weekly, season=2026, team=game["away_team"], game_week=int(game["week"])
        )
        src_weeks = sorted(set(home_src + away_src))
        as_of = record_as_of_check(
            game_id=gid,
            game_week=int(game["week"]),
            source_weeks=src_weeks,
            kickoff_utc=kickoff,
            feature_as_of_week=int(game["week"]) - 1,
        )
        inj = injury_allowed_flagged({})
        feat: Dict[str, Any] = {
            "game_id_product": gid,
            "season": 2026,
            "week": int(game["week"]),
            "home_team": game["home_team"],
            "away_team": game["away_team"],
            "kickoff_utc": kickoff,
            "as_of": as_of.to_dict(),
            "as_of_week": as_of.as_of_week,
            "source_weeks": src_weeks,
            "pbp_week_cap": int(pbp_week_cap),
            "game_week_cap": int(game_week_cap),
            "rolling_window_sql": LAGGED_WINDOW_SQL,
            "prod_leak_window_sql": PROD_LEAK_WINDOW_SQL,
            "home_rest_days": game.get("home_rest"),
            "away_rest_days": game.get("away_rest"),
            "diff_rest_days": (
                None
                if game.get("home_rest") is None or game.get("away_rest") is None
                else float(game["home_rest"]) - float(game["away_rest"])
            ),
            "roof_dome": (
                1
                if str(game.get("roof") or "").lower() in {"dome", "closed"}
                else (0 if game.get("roof") else None)
            ),
            "surface_turf": (
                1
                if "turf" in str(game.get("surface") or "").lower()
                else (0 if game.get("surface") else None)
            ),
            "is_divisional_game": parse_num(game.get("div_game")),
            "week_key": game["week"],
            "injury_handling": inj["injury_handling"],
            "injury_source": inj["injury_source"],
            "home_injury_impact": None,
            "away_injury_impact": None,
            "diff_injury_impact": None,
            "offense_index_home": None,
            "offense_index_away": None,
            "defense_index_home": None,
            "defense_index_away": None,
        }
        for roll_key, (hk, ak) in SIDE_MAP.items():
            feat[hk] = home_roll.get(roll_key)
            feat[ak] = away_roll.get(roll_key)
        for a, b, dest in (
            ("home_off_epa_5g", "away_off_epa_5g", "diff_off_epa_5g"),
            ("home_def_epa_allowed_5g", "away_def_epa_allowed_5g", "diff_def_epa_allowed_5g"),
            ("home_pressure_generated_5g", "away_pressure_generated_5g", "diff_pressure_generated_5g"),
            ("home_pressure_allowed_5g", "away_pressure_allowed_5g", "diff_pressure_allowed_5g"),
            ("home_red_zone_td_rate_5g", "away_red_zone_td_rate_5g", "diff_red_zone_td_rate_5g"),
            ("home_success_offense_5g", "away_success_offense_5g", "diff_success_rate_5g"),
            ("home_kav_net_5g", "away_kav_net_5g", "diff_kav_net_5g"),
        ):
            ha, aa = parse_num(feat.get(a)), parse_num(feat.get(b))
            feat[dest] = None if ha is None or aa is None else ha - aa
        for kav in (
            "home_kav_offense_5g",
            "away_kav_offense_5g",
            "home_kav_defense_5g",
            "away_kav_defense_5g",
            "home_kav_net_5g",
            "away_kav_net_5g",
        ):
            feat.setdefault(kav, None)
        if as_of.status != "PASS":
            blocked.append(f"as_of {gid} {as_of.flags}")
        row_flags = list(as_of.flags) + list(inj["flags"])
        if game.get("home_rest") is None or game.get("away_rest") is None:
            row_flags.append("FLAG_MISSING_REST")
        if feat.get("home_off_epa_5g") is None or feat.get("away_off_epa_5g") is None:
            row_flags.append("FLAG_MISSING_EPA")
        row_flags.append("FLAG_MISSING_TRUE_PR_PRIOR")
        row_flags.append("FLAG_KAV_LAGGED_NULL")
        rows.append(feat)
        for fl in row_flags:
            flags_out.append({"game_id_product": gid, "flag": fl, "as_of_week": as_of.as_of_week})

    feat_path = out_dir / "features.jsonl"
    flag_path = out_dir / "feature-flags.jsonl"
    with feat_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    with flag_path.open("w", encoding="utf-8") as fh:
        for row in flags_out:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    pin = write_feature_store_pin(out_dir)
    report = {
        "script_id": SCRIPT_ID,
        "ruling": RULING,
        "status": "BLOCKED" if blocked else "BUILT",
        "blocked": blocked,
        "n_rows": len(rows),
        "game_week_cap": int(game_week_cap),
        "pbp_week_cap": int(pbp_week_cap),
        "rolling_window_sql": LAGGED_WINDOW_SQL,
        "prod_leak_window_sql": PROD_LEAK_WINDOW_SQL,
        "feature_store_sha256": pin["feature_store_sha256"],
        "do_not_run_until_imv_code_check": True,
        "w7_refused": True,
    }
    (out_dir / "build-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_feature_store_pin(out_dir)
    return report


def parity_vs_prod(
    local_rows: Sequence[Mapping[str, Any]],
    prod_rows: Sequence[Mapping[str, Any]],
    *,
    week_cap: int,
    keys: Sequence[str] = ("home_off_epa_5g", "away_off_epa_5g"),
) -> Dict[str, Any]:
    """C-3: compare local lagged rows to prod features with an explicit week cap.

    Prod CURRENT-ROW windows that include the game week are flagged
    `PROD_SAME_WEEK_LEAK` — they are not the local truth.
    """
    local = {r.get("game_id_product") or r.get("game_id"): r for r in apply_week_cap(local_rows, week_cap)}
    prod = {r.get("game_id_product") or r.get("game_id"): r for r in apply_week_cap(prod_rows, week_cap)}
    diffs: List[Dict[str, Any]] = []
    prod_leaks: List[str] = []
    local_leaks: List[str] = []
    compared = 0
    for gid, lrow in sorted(local.items()):
        prow = prod.get(gid)
        if prow is None:
            diffs.append({"game_id": gid, "reason": "missing_in_prod"})
            continue
        compared += 1
        l_asof = lrow.get("as_of_week")
        p_asof = prow.get("as_of_week")
        week = int(lrow["week"])
        if l_asof is not None and int(l_asof) >= week:
            local_leaks.append(gid)
        if p_asof is None or int(p_asof) >= week:
            prod_leaks.append(gid)
        src = lrow.get("source_weeks") or []
        if any(_source_after_or_same_game(str(w), 2026, week) for w in src):
            local_leaks.append(gid)
        for key in keys:
            lv, pv = parse_num(lrow.get(key)), parse_num(prow.get(key))
            if lv is None and pv is None:
                continue
            if lv is None or pv is None or abs(lv - pv) > 1e-9:
                diffs.append({"game_id": gid, "key": key, "local": lv, "prod": pv})
    status = "PASS" if not local_leaks else "BLOCKED_LOCAL_LEAK"
    return {
        "status": status,
        "week_cap": int(week_cap),
        "compared": compared,
        "n_local": len(local),
        "n_prod": len(prod),
        "diffs": diffs,
        "prod_same_week_leak": sorted(set(prod_leaks)),
        "local_same_week_leak": sorted(set(local_leaks)),
        "note": "Prod CURRENT ROW is not the as-of truth. Local must stay lagged.",
    }


def _cmd_build(args: argparse.Namespace) -> int:
    report = build_feature_store(
        base=Path(args.base),
        games_csv=Path(args.games_csv),
        pbp_paths=[Path(p) for p in args.pbp],
        out_dir=Path(args.out),
        game_week_cap=int(args.game_week_cap),
        pbp_week_cap=int(args.pbp_week_cap),
        pack_path=Path(args.pack) if args.pack else None,
    )
    print(json.dumps(report, indent=2))
    return 6 if report["status"] == "BLOCKED" else 0


def _cmd_parity(args: argparse.Namespace) -> int:
    def load_jsonl(path: Path) -> List[Dict[str, Any]]:
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    doc = parity_vs_prod(
        load_jsonl(Path(args.local)),
        load_jsonl(Path(args.prod)),
        week_cap=int(args.week_cap),
    )
    print(json.dumps(doc, indent=2))
    return 0 if doc["status"] == "PASS" else 6


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="nfl_imv_v21")
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="Build file-backed store (do not run until IMV code-checks)")
    b.add_argument("--base", required=True)
    b.add_argument("--games-csv", required=True)
    b.add_argument("--pbp", action="append", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--game-week-cap", type=int, required=True)
    b.add_argument("--pbp-week-cap", type=int, required=True)
    b.add_argument("--pack", default="")
    b.set_defaults(func=_cmd_build)
    p = sub.add_parser("parity", help="Parity vs prod features with week cap")
    p.add_argument("--local", required=True)
    p.add_argument("--prod", required=True)
    p.add_argument("--week-cap", type=int, required=True)
    p.set_defaults(func=_cmd_parity)
    args = parser.parse_args(argv)
    if os.environ.get("IMV_REFUSE_W7") == "1":
        print("FAIL: W7 refused", file=sys.stderr)
        return 2
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
