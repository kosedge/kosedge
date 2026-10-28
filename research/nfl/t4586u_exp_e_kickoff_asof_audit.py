#!/usr/bin/env python3
"""t4586u Experiment E ONLY — kickoff-honest as-of audit (CERT=0).

Authority
  DECISION_RYAN_t4598u CLEAR Exp E ONLY     sha8 5bb608d0
  COS_ORDER_CURSOR_t4598u_EXP_E_EXECUTE     sha8 701ac13c
  IMV PASS_PROTOCOL v2                      sha8 60c18a4c §H
  Cursor FEASIBILITY v1.1                   sha8 15ee3a1b
  games.csv pin                             sha8 4fe1cdd7
  #646 rolling CSV                          sha8 1b07654e

H1: download PBP 2012–2023 and write SHA256SUMS (plus weather-via-parent-PBP
and a content-addressed 2012 schedule snapshot) BEFORE any parquet/CSV read
of those inputs. Missing hash or vintage drift vs #646 emit → BLOCKED.

Does NOT: run Exp A, fit β, import simulate_nfl_game, touch LOCKED_SCORING /
config_overrides, call Odds, require DATABASE_URL, merge #646/#647/#648,
touch 2024+, touch F2 PHI@WSH, or claim CERT.

NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · sealed=1.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
MS_SRC = ROOT / "services" / "model-service"
if str(MS_SRC) not in sys.path:
    sys.path.insert(0, str(MS_SRC))
_USER_SITE = Path.home() / ".local/lib/python3.12/site-packages"
if _USER_SITE.is_dir() and str(_USER_SITE) not in sys.path:
    sys.path.insert(0, str(_USER_SITE))

from src.services.nfl_canonical_teams import TEAM_ALIASES, canonicalize_team  # noqa: E402

# Forbidden production / Exp A surfaces — never imported.
_FORBIDDEN_IMPORTS = (
    "simulate_nfl_game",
    "LOCKED_SCORING",
    "config_overrides",
    "NflGameInputs",
)

TICKET = "t4586u"
LABEL = "RESEARCH_DIAGNOSTIC_EXP_E"
CERT_CANDIDATE = 0
WINDOW = 5
FILE_MODE = 0o444

DECISION_SHA8 = "5bb608d0"
COS_ORDER_SHA8 = "701ac13c"
IMV_SHA8 = "60c18a4c"
FEASIBILITY_SHA8 = "15ee3a1b"
ADDENDUM_SHA8 = "84a28a05"
ACK_SHA8 = "6fcc0af6"
ALEX_SPEC_SHA8 = "ddffb72e"

WF_TIP_FULL = "82ffb211d389b20e4d6ec305e4a0466532a48a6d"
GAMES_CSV_SHA256 = "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8"
ROLLING_CSV_SHA256 = "1b07654ea500535ff445e0f3c20acc26a6c3006857951562755e406adff52479"
OOS_SHA256 = "1ee90facf7d44dfd19758cbf89d5518417cbc1fba6faec4e76fb33d8532adaed"
N_GAMES_EXPECT = 2992
PBP_SEASONS = list(range(2012, 2024))  # 2012–2023 inclusive; 2024+ forbidden

PBP_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "pbp/play_by_play_{season}.parquet"
)
GAMES_URL = (
    "https://raw.githubusercontent.com/kosedge/kosedge/"
    f"{WF_TIP_FULL}/data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv"
)
ROLLING_GIT_REF = (
    "origin/cursor/epa-wf-feature-emit-5bcd:"
    "data/ops/nfl-t4564u-epa-wf-feature-emit/"
    "nfl-epa-wf-pbp-2013-2023-t4564u-20261027T213659Z/"
    "rolling_features_weekly_pbp_strict_asof_2013_2023.csv"
)
OOS_REL = Path(
    "data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv"
)

GAMES_COLUMNS = [
    "season",
    "week",
    "game_id",
    "home",
    "away",
    "kickoff_utc",
    "nflverse_gameday",
    "nflverse_gametime",
    "nflverse_location",
    "nflverse_join",
    "record_entering_home",
    "record_entering_away",
    "record_offense_index_home",
    "record_offense_index_away",
    "record_defense_index_home",
    "record_defense_index_away",
    "record_pred_margin_home",
    "record_spread_home",
    "record_total",
    "record_decomp_pred_margin_home",
    "record_decomp_spread_home",
    "record_decomp_total",
    "home_win_prob",
    "away_win_prob",
    "cover_prob",
    "cover_prob_home",
    "over_prob",
    "market_spread_home",
    "market_total",
    "market_line_source",
    "apply_market_blend",
    "research_label",
    "cert_candidate",
    "epa_trailing_spread_home",
    "epa_trailing_total",
    "epa_home_win_prob",
    "epa_away_win_prob",
    "epa_status",
    "epa_blocker",
    "market_blend_applied",
    "injury_overlay",
    "ifb_overlay",
    "personnel_overlay",
    "rest_days_home",
    "rest_days_away",
    "simulations",
    "seed",
    "model_version",
    "framework_version",
    "pit_schedule_path",
    "pit_schedule_sha256",
    "pit_record_rule",
]

RELOCATION_PAIRS = (("STL", "LAR"), ("SD", "LAC"), ("OAK", "LV"))
ET = ZoneInfo("America/New_York")

CACHE_DIR = Path(os.environ.get("T4586U_EXP_E_CACHE", "/tmp/nflverse-pbp-exp-e"))
OUT_DIR = ROOT / "research" / "nfl" / "t4586u_exp_e_kickoff_asof"
INPUTS_DIR = ROOT / "research" / "nfl" / "t4586u_exp_e_inputs"

# H1 gate: label → sha256. Reads of hashed inputs are forbidden until these exist.
_H1_HASHES: Dict[str, str] = {}
_H1_CLOSED = False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _fmt_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha8(digest: str) -> str:
    return str(digest)[:8]


def _write_readonly(path: Path, blob: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.chmod(0o644)
    path.write_bytes(blob)
    path.chmod(FILE_MODE)


def _write_json(path: Path, payload: Mapping[str, Any]) -> str:
    blob = (json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n").encode()
    _write_readonly(path, blob)
    return _sha256_bytes(blob)


def _write_text(path: Path, text: str) -> str:
    blob = text.encode("utf-8") if not text.endswith("\n") else text.encode("utf-8")
    if not text.endswith("\n"):
        blob = (text + "\n").encode("utf-8")
    _write_readonly(path, blob)
    return _sha256_bytes(blob)


def _franchise(team: str) -> str:
    raw = str(team or "").strip().upper()
    return str(canonicalize_team(raw) or raw)


def _register_hash(label: str, path: Path) -> str:
    if not path.is_file() or path.stat().st_size <= 0:
        raise RuntimeError(f"H1 hash target missing or empty: {label} ({path})")
    digest = _sha256_file(path)
    _H1_HASHES[label] = digest
    print(f"[h1] sha256 {label} {_sha8(digest)} bytes={path.stat().st_size}", flush=True)
    return digest


def _assert_h1_closed() -> None:
    if not _H1_CLOSED:
        raise RuntimeError("refusing parquet/CSV read of E inputs before H1 SHA256SUMS")


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    if tmp.exists():
        tmp.unlink()
    curl = [
        "curl",
        "-L",
        "--fail",
        "--retry",
        "5",
        "--retry-delay",
        "4",
        "--retry-all-errors",
        "-A",
        "kosedge-research/t4586u-exp-e",
        "--connect-timeout",
        "30",
        "--max-time",
        "300",
        "-o",
        str(tmp),
        url,
    ]
    try:
        subprocess.check_call(curl)
        tmp.replace(dest)
        return
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(f"[h1] curl failed ({exc}); urllib fallback {url}", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "kosedge-research/t4586u-exp-e"})
    with urllib.request.urlopen(req, timeout=300) as res:
        tmp.write_bytes(res.read())
    tmp.replace(dest)


def _ensure_downloaded(url: str, dest: Path, *, min_bytes: int) -> None:
    if dest.is_file() and dest.stat().st_size >= min_bytes:
        print(f"[h1] cache hit {dest.name} bytes={dest.stat().st_size}", flush=True)
        return
    print(f"[h1] download {url}", flush=True)
    _download(url, dest)
    if not dest.is_file() or dest.stat().st_size < min_bytes:
        raise RuntimeError(f"download too small: {dest} bytes={dest.stat().st_size if dest.is_file() else 0}")


def _extract_rolling_csv(dest: Path) -> None:
    """Cite-only extract of #646 rolling CSV. Not a merge."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    blob = subprocess.check_output(["git", "show", ROLLING_GIT_REF], cwd=str(ROOT))
    dest.write_bytes(blob)


def _write_sha256sums(path: Path, items: Mapping[str, str]) -> str:
    lines = [f"{sha}  {name}" for name, sha in sorted(items.items())]
    return _write_text(path, "\n".join(lines) + "\n")


def _as_bool_series(s: Any) -> int:
    if s is None:
        return 0
    if isinstance(s, bool):
        return int(s)
    text = str(s).strip().lower()
    if text in {"1", "true", "t", "yes"}:
        return 1
    try:
        return int(float(s) != 0.0)
    except (TypeError, ValueError):
        return 0


def _mean(vals: Sequence[Optional[float]]) -> Optional[float]:
    clean = [float(v) for v in vals if v is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def _rolling_before(
    history: Mapping[str, List[Mapping[str, Any]]],
    *,
    franchise: str,
    season: int,
    week: int,
) -> Optional[Dict[str, Any]]:
    """Bit-identical window predicate to #646 emit (no strength-index / sim)."""
    recs = [
        r
        for r in history.get(franchise, [])
        if (int(r["season"]), int(r["week"])) < (season, week)
        and r.get("off_epa") is not None
        and r.get("def_epa_allowed") is not None
    ]
    recs = recs[-WINDOW:]
    if not recs:
        return None
    off = _mean([r["off_epa"] for r in recs])
    deff = _mean([r["def_epa_allowed"] for r in recs])
    if off is None or deff is None:
        return None
    p_all = _mean([r.get("pressure_rate_allowed") for r in recs]) or 0.0
    p_gen = _mean([r.get("pressure_rate_generated") for r in recs]) or 0.0
    return {
        "games": len(recs),
        "off_epa_per_play_5g": round(off, 6),
        "def_epa_allowed_per_play_5g": round(deff, 6),
        "pressure_rate_allowed_5g": round(p_all, 6),
        "pressure_rate_generated_5g": round(p_gen, 6),
        "first": f"{recs[0]['season']}W{int(recs[0]['week']):02d}",
        "last": f"{recs[-1]['season']}W{int(recs[-1]['week']):02d}",
        "team_weeks": [(int(r["season"]), int(r["week"]), str(r["franchise"])) for r in recs],
        "recs": recs,
    }


def _to_utc(dt: datetime, *, naive_as_et: bool) -> Optional[datetime]:
    if dt.tzinfo is None:
        if not naive_as_et:
            return None
        dt = dt.replace(tzinfo=ET)
    return dt.astimezone(timezone.utc)


def _parse_utc(text: Any, *, naive_as_et: bool = False) -> Optional[datetime]:
    if text is None:
        return None
    if isinstance(text, datetime):
        return _to_utc(text, naive_as_et=naive_as_et)
    if hasattr(text, "to_pydatetime"):
        try:
            return _parse_utc(text.to_pydatetime(), naive_as_et=naive_as_et)
        except Exception:
            return None
    s = str(text).strip()
    if not s or s.lower() in {"nan", "none", "nat", "<na>"}:
        return None
    s = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return _to_utc(dt, naive_as_et=naive_as_et)


def _parse_clock(text: str) -> Optional[Tuple[int, int, int]]:
    s = str(text).strip()
    if not s:
        return None
    m = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AaPp][Mm])?", s)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2))
    ss = int(m.group(3) or 0)
    ampm = (m.group(4) or "").upper()
    if ampm:
        if hh == 12:
            hh = 0 if ampm == "AM" else 12
        elif ampm == "PM":
            hh += 12
    if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59):
        return None
    return hh, mm, ss


def _et_date_time_to_utc(date_s: Any, time_s: Any) -> Optional[datetime]:
    """gameday + gametime America/New_York → UTC. No invented noon."""
    if date_s is None or time_s is None:
        return None
    ds = str(date_s).strip()[:10]
    ts = str(time_s).strip()
    if not ds or not ts or ts.lower() in {"nan", "none", ""}:
        return None
    clock = _parse_clock(ts)
    if clock is None:
        aware = _parse_utc(ts)
        if aware is not None:
            return aware
        return None
    try:
        y, m, d = int(ds[0:4]), int(ds[5:7]), int(ds[8:10])
    except (TypeError, ValueError):
        return None
    hh, mm, ss = clock
    try:
        local = datetime(y, m, d, hh, mm, ss, tzinfo=ET)
    except ValueError:
        return None
    return local.astimezone(timezone.utc)


def _is_nan(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return True
    s = str(val).strip().lower()
    return s in {"", "nan", "none", "nat", "<na>"}


def _first_str(rec: Mapping[str, Any], keys: Sequence[str]) -> Optional[str]:
    for k in keys:
        if k in rec and not _is_nan(rec.get(k)):
            return str(rec.get(k)).strip()
    return None


def _kickoff_from_pbp_row(rec: Mapping[str, Any]) -> Tuple[Optional[datetime], str, str]:
    """Return (utc, source, raw). Never invents noon."""
    for key in ("start_time", "time_of_day"):
        if key in rec and not _is_nan(rec.get(key)):
            parsed = _parse_utc(rec.get(key), naive_as_et=True)
            if parsed is not None:
                src = f"pbp_{key}_aware" if _parse_utc(rec.get(key)) is not None else f"pbp_{key}_naive_et"
                return parsed, src, str(rec.get(key))
    date_s = _first_str(rec, ("game_date", "gameday"))
    time_s = _first_str(rec, ("start_time", "gametime", "start_time_eastern"))
    parsed = _et_date_time_to_utc(date_s, time_s)
    if parsed is not None:
        return parsed, "pbp_gameday_gametime_et", f"{date_s} {time_s}"
    return None, "unknown", f"date={date_s!r} time={time_s!r}"


def close_h1(cache: Path) -> Dict[str, Any]:
    """Download + hash every E input. MUST run before any parquet/CSV parse."""
    global _H1_CLOSED
    _H1_CLOSED = False
    _H1_HASHES.clear()
    cache.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)

    games_path = cache / "walkforward_games_82ffb211.csv"
    _ensure_downloaded(GAMES_URL, games_path, min_bytes=1000)
    games_sha = _register_hash("games.csv", games_path)

    oos_path = ROOT / OOS_REL
    oos_sha = _register_hash("historical_oos_games.csv", oos_path)

    rolling_path = cache / "rolling_features_weekly_pbp_strict_asof_2013_2023.csv"
    print("[h1] git-show #646 rolling CSV (cite; not a merge)", flush=True)
    _extract_rolling_csv(rolling_path)
    rolling_sha = _register_hash("rolling_features_weekly_pbp_strict_asof_2013_2023.csv", rolling_path)

    pbp_map: Dict[str, str] = {}
    for season in PBP_SEASONS:
        dest = cache / f"play_by_play_{season}.parquet"
        _ensure_downloaded(PBP_URL.format(season=season), dest, min_bytes=10_000)
        digest = _register_hash(f"play_by_play_{season}.parquet", dest)
        pbp_map[str(season)] = digest

    missing = []
    if games_sha != GAMES_CSV_SHA256:
        missing.append(
            f"games.csv sha mismatch got={games_sha} want={GAMES_CSV_SHA256}"
        )
    if rolling_sha != ROLLING_CSV_SHA256:
        missing.append(
            f"rolling csv sha mismatch got={rolling_sha} want={ROLLING_CSV_SHA256}"
        )
    if oos_sha != OOS_SHA256:
        missing.append(f"oos sha mismatch got={oos_sha} want={OOS_SHA256}")
    for season in PBP_SEASONS:
        label = f"play_by_play_{season}.parquet"
        if label not in _H1_HASHES:
            missing.append(f"missing hash {label}")

    input_sums = dict(_H1_HASHES)
    _write_sha256sums(OUT_DIR / "SHA256SUMS", input_sums)
    _write_sha256sums(INPUTS_DIR / "SHA256SUMS.inputs", input_sums)
    print(f"[h1] wrote {OUT_DIR / 'SHA256SUMS'} n={len(input_sums)} (before any input parse)", flush=True)

    if missing:
        _H1_CLOSED = False
        return {
            "ok": False,
            "blocked_reasons": missing,
            "pbp_sha256": pbp_map,
            "games_csv_sha256": games_sha,
            "rolling_csv_sha256": rolling_sha,
            "oos_sha256": oos_sha,
            "games_path": str(games_path),
            "rolling_path": str(rolling_path),
            "cache": str(cache),
        }

    _H1_CLOSED = True
    return {
        "ok": True,
        "blocked_reasons": [],
        "pbp_sha256": pbp_map,
        "games_csv_sha256": games_sha,
        "rolling_csv_sha256": rolling_sha,
        "oos_sha256": oos_sha,
        "games_path": str(games_path),
        "rolling_path": str(rolling_path),
        "cache": str(cache),
    }


def _load_games(path: Path) -> List[Dict[str, str]]:
    _assert_h1_closed()
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        cols = list(reader.fieldnames or [])
        rows = list(reader)
    if cols != GAMES_COLUMNS:
        raise RuntimeError(f"games.csv column order drift: {cols[:8]}...")
    return rows


def _load_rolling(path: Path) -> List[Dict[str, str]]:
    _assert_h1_closed()
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _load_pbp_week_rows(
    cache: Path, seasons: Sequence[int]
) -> Tuple[List[Dict[str, Any]], Dict[Tuple[int, int, str], Set[str]], List[Dict[str, Any]], List[Dict[str, Any]], int]:
    """Emit-identical weekly H plus game_id / kickoff / weather extracts.

    Hash-before-read already closed. Weather hashed via parent PBP bytes.
    """
    _assert_h1_closed()
    import pandas as pd
    import pyarrow.parquet as pq

    weekly: List[Dict[str, Any]] = []
    tw_games: Dict[Tuple[int, int, str], Set[str]] = defaultdict(set)
    game_meta: Dict[str, Dict[str, Any]] = {}
    weather_rows: Dict[str, Dict[str, Any]] = {}
    keep = [
        "season",
        "week",
        "game_id",
        "posteam",
        "defteam",
        "play_type",
        "epa",
        "sack",
        "qb_hit",
        "season_type",
    ]
    extra = [
        "home_team",
        "away_team",
        "game_date",
        "gameday",
        "start_time",
        "gametime",
        "start_time_eastern",
        "time_of_day",
        "temp",
        "wind",
        "roof",
        "surface",
    ]
    n_ge_2024 = 0
    for season in seasons:
        dest = cache / f"play_by_play_{season}.parquet"
        print(f"[pbp] load {season} bytes={dest.stat().st_size}", flush=True)
        schema_names = list(pq.ParquetFile(str(dest)).schema.names)
        present = [c for c in keep + extra if c in schema_names]
        df = pd.read_parquet(dest, columns=present)
        if "season" not in df.columns:
            df["season"] = season
        # Holdout fence (Alex invariant 7): count, then drop, never use.
        season_num = pd.to_numeric(df["season"], errors="coerce")
        n_ge_2024 += int((season_num >= 2024).sum())
        df = df[season_num < 2024]
        if "season_type" in df.columns:
            st = df["season_type"].astype(str).str.upper()
            df = df[st.isin(("REG", "POST", "REGULAR", "POSTSEASON"))]
        df = df[df["play_type"].astype(str).isin(("pass", "run"))]
        df = df[df["posteam"].notna() & df["defteam"].notna() & df["week"].notna()]
        df["epa"] = pd.to_numeric(df["epa"], errors="coerce")
        df = df[df["epa"].notna()]
        df["is_pass"] = df["play_type"].astype(str).eq("pass")
        sack = df["sack"].map(_as_bool_series) if "sack" in df.columns else 0
        hit = df["qb_hit"].map(_as_bool_series) if "qb_hit" in df.columns else 0
        df["pressure"] = ((sack + hit) > 0).astype(int)

        gid_cols = [c for c in ("season", "week", "game_id", "posteam", "defteam") if c in df.columns]
        for rec in df[gid_cols].drop_duplicates().to_dict("records"):
            s = int(rec["season"])
            w = int(rec["week"])
            gid = str(rec["game_id"]).strip()
            for raw in (rec.get("posteam"), rec.get("defteam")):
                if _is_nan(raw):
                    continue
                tw_games[(s, w, _franchise(str(raw)))].add(gid)

        meta_cols = [
            c
            for c in (
                "season",
                "week",
                "game_id",
                "home_team",
                "away_team",
                "game_date",
                "gameday",
                "start_time",
                "gametime",
                "start_time_eastern",
                "time_of_day",
                "temp",
                "wind",
                "roof",
                "surface",
            )
            if c in df.columns
        ]
        if "game_id" in df.columns:
            for rec in df[meta_cols].drop_duplicates(subset=["game_id"]).to_dict("records"):
                gid = str(rec["game_id"]).strip()
                if gid in game_meta:
                    continue
                ko, src, raw = _kickoff_from_pbp_row(rec)
                game_meta[gid] = {
                    "game_id": gid,
                    "season": int(rec["season"]) if not _is_nan(rec.get("season")) else season,
                    "week": int(rec["week"]) if not _is_nan(rec.get("week")) else None,
                    "home": _first_str(rec, ("home_team",)),
                    "away": _first_str(rec, ("away_team",)),
                    "game_date": _first_str(rec, ("game_date", "gameday")),
                    "start_time_raw": _first_str(
                        rec, ("start_time", "gametime", "start_time_eastern", "time_of_day")
                    ),
                    "kickoff_utc": _fmt_utc(ko) if ko is not None else "",
                    "kickoff_source": src,
                    "parse_status": "ok" if ko is not None else "unknown",
                }
                weather_rows[gid] = {
                    "game_id": gid,
                    "season": game_meta[gid]["season"],
                    "week": game_meta[gid]["week"],
                    "temp": _first_str(rec, ("temp",)) or "",
                    "wind": _first_str(rec, ("wind",)) or "",
                    "roof": _first_str(rec, ("roof",)) or "",
                    "surface": _first_str(rec, ("surface",)) or "",
                    "parent_pbp": f"play_by_play_{season}.parquet",
                    "parent_pbp_sha256": _H1_HASHES.get(f"play_by_play_{season}.parquet", ""),
                }

        off = (
            df.groupby(["season", "week", "posteam"], observed=True)
            .agg(
                off_plays=("epa", "count"),
                off_epa=("epa", "mean"),
                dropbacks=("is_pass", "sum"),
                pressures_allowed=("pressure", "sum"),
            )
            .reset_index()
        )
        deff = (
            df.groupby(["season", "week", "defteam"], observed=True)
            .agg(
                def_plays=("epa", "count"),
                def_epa_allowed=("epa", "mean"),
                dropbacks_faced=("is_pass", "sum"),
                pressures_generated=("pressure", "sum"),
            )
            .reset_index()
        )
        merged = off.merge(
            deff,
            left_on=["season", "week", "posteam"],
            right_on=["season", "week", "defteam"],
            how="outer",
        )
        for rec in merged.to_dict("records"):
            team = str(rec.get("posteam") or rec.get("defteam") or "").strip().upper()
            if not team:
                continue
            dropbacks = float(rec.get("dropbacks") or 0)
            faced = float(rec.get("dropbacks_faced") or 0)
            weekly.append(
                {
                    "season": int(rec["season"]),
                    "week": int(rec["week"]),
                    "team": team,
                    "franchise": _franchise(team),
                    "off_plays": float(rec.get("off_plays") or 0),
                    "off_epa": float(rec["off_epa"]) if rec.get("off_epa") == rec.get("off_epa") else None,
                    "def_plays": float(rec.get("def_plays") or 0),
                    "def_epa_allowed": (
                        float(rec["def_epa_allowed"])
                        if rec.get("def_epa_allowed") == rec.get("def_epa_allowed")
                        else None
                    ),
                    "pressure_rate_allowed": (
                        float(rec.get("pressures_allowed") or 0) / dropbacks
                        if dropbacks > 0
                        else None
                    ),
                    "pressure_rate_generated": (
                        float(rec.get("pressures_generated") or 0) / faced
                        if faced > 0
                        else None
                    ),
                }
            )
        del df, off, deff, merged
    weekly.sort(key=lambda r: (r["franchise"], r["season"], r["week"], r["team"]))
    print(
        f"[pbp] weekly_rows={len(weekly)} tw_keys={len(tw_games)} "
        f"game_meta={len(game_meta)} n_plays_season_ge_2024={n_ge_2024}",
        flush=True,
    )
    return weekly, tw_games, list(game_meta.values()), list(weather_rows.values()), n_ge_2024


def _num6(val: Any) -> str:
    if val is None or val == "":
        return ""
    try:
        return f"{round(float(val), 6):.6f}"
    except (TypeError, ValueError):
        return ""


def _reconstruct_rolling(
    weekly: Sequence[Mapping[str, Any]],
    history: Mapping[str, List[Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    rolling_rows: List[Dict[str, Any]] = []
    seen = set()
    for rec in weekly:
        key = (int(rec["season"]), int(rec["week"]), rec["franchise"])
        if key in seen or int(rec["season"]) < 2013:
            continue
        seen.add(key)
        rolled = _rolling_before(
            history,
            franchise=str(rec["franchise"]),
            season=int(rec["season"]),
            week=int(rec["week"]),
        )
        rolling_rows.append(
            {
                "season": int(rec["season"]),
                "week": int(rec["week"]),
                "team": rec["franchise"],
                "pbp_team": rec["team"],
                "games_in_window_5": 0 if rolled is None else rolled["games"],
                "off_epa_per_play_5g": "" if rolled is None else rolled["off_epa_per_play_5g"],
                "def_epa_allowed_per_play_5g": (
                    "" if rolled is None else rolled["def_epa_allowed_per_play_5g"]
                ),
                "pressure_rate_allowed_5g": (
                    "" if rolled is None else rolled["pressure_rate_allowed_5g"]
                ),
                "pressure_rate_generated_5g": (
                    "" if rolled is None else rolled["pressure_rate_generated_5g"]
                ),
            }
        )
    return rolling_rows


def _compare_vintage(
    reconstructed: Sequence[Mapping[str, Any]], pinned: Sequence[Mapping[str, str]]
) -> Tuple[int, List[str]]:
    """Return (n_mismatch, reasons). Any mismatch is vintage drift → BLOCKED."""
    reasons: List[str] = []
    recon_map = {
        (int(r["season"]), int(r["week"]), str(r["team"])): r for r in reconstructed
    }
    pin_map = {
        (int(r["season"]), int(r["week"]), str(r["team"])): r for r in pinned
    }
    extra = sorted(set(recon_map) - set(pin_map))
    missing = sorted(set(pin_map) - set(recon_map))
    if extra:
        reasons.append(f"reconstructed rolling keys not in #646: n={len(extra)} e.g. {extra[:3]}")
    if missing:
        reasons.append(f"#646 rolling keys missing from reconstruct: n={len(missing)} e.g. {missing[:3]}")
    n_val = 0
    for key, rec in recon_map.items():
        pin = pin_map.get(key)
        if pin is None:
            n_val += 1
            continue
        if int(rec["games_in_window_5"]) != int(float(pin["games_in_window_5"] or 0)):
            n_val += 1
            if len(reasons) < 8:
                reasons.append(
                    f"games_in_window_5 drift {key}: recon={rec['games_in_window_5']} pin={pin['games_in_window_5']}"
                )
            continue
        for col in ("off_epa_per_play_5g", "def_epa_allowed_per_play_5g"):
            if _num6(rec.get(col)) != _num6(pin.get(col)):
                n_val += 1
                if len(reasons) < 8:
                    reasons.append(
                        f"{col} drift {key}: recon={_num6(rec.get(col))} pin={_num6(pin.get(col))}"
                    )
                break
    return n_val + len(extra) + len(missing), reasons


def _aliases_for(franchise: str) -> Set[str]:
    out = {franchise}
    for raw, canon in TEAM_ALIASES.items():
        if canon == franchise:
            out.add(raw)
    return out


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> str:
    from io import StringIO

    sio = StringIO()
    w = csv.DictWriter(sio, fieldnames=list(fieldnames), extrasaction="ignore")
    w.writeheader()
    for row in rows:
        w.writerow({k: row.get(k, "") for k in fieldnames})
    blob = sio.getvalue().encode("utf-8")
    _write_readonly(path, blob)
    return _sha256_bytes(blob)


def main() -> int:
    for name in _FORBIDDEN_IMPORTS:
        if name in sys.modules:
            raise SystemExit(f"forbidden module already imported: {name}")

    forecast_ts = _utc_now()
    cache = CACHE_DIR
    blocked_reasons: List[str] = []
    fail_reasons: List[str] = []

    print("[e] H1 close-on-run FIRST (hash before any input parse)", flush=True)
    try:
        h1 = close_h1(cache)
    except Exception as exc:
        blocked_reasons.append(f"H1 download/hash failure: {type(exc).__name__}: {exc}")
        h1 = {
            "ok": False,
            "pbp_sha256": {},
            "games_csv_sha256": "",
            "rolling_csv_sha256": "",
            "oos_sha256": "",
            "games_path": "",
            "rolling_path": "",
        }

    if not h1.get("ok"):
        blocked_reasons.extend(h1.get("blocked_reasons") or ["H1 not closed"])

    counts: Dict[str, Any] = {
        "n_games": 0,
        "n_windows": 0,
        "n_windows_empty": 0,
        "n_windows_empty_exception_list": [],
        "n_rows_season_ge_2024": 0,
        "n_invariant6_game_id_diff": 0,
        "n_franchise_alias_drop": 0,
        "n_contributors": 0,
        "n_kickoff_ok": 0,
        "n_kickoff_fail": 0,
        "n_kickoff_unknown": 0,
        "n_self_game_leak": 0,
        "n_week1": 0,
        "n_covid_flex_flags": 0,
        "n_intraweek_conservative": 0,
        "n_franchise_cross": 0,
        "n_rest_placeholder": 0,
        "n_neutral": 0,
        "pbp_sha256": h1.get("pbp_sha256") or {},
        "games_csv_sha256": h1.get("games_csv_sha256") or "",
        "verdict": "BLOCKED",
    }

    artifact_sha: Dict[str, str] = {
        "SHA256SUMS.inputs": _H1_HASHES.get("games.csv", ""),
    }
    if blocked_reasons:
        return _seal_and_exit(
            counts,
            blocked_reasons,
            fail_reasons,
            artifact_sha,
            forecast_ts,
            inversions=[],
            week1=[],
            covid=[],
            intra=[],
            rest_rows=[],
            neutral_rows=[],
            extra_notes=["H1 blocked before audit body"],
        )

    games = _load_games(Path(h1["games_path"]))
    pinned_rolling = _load_rolling(Path(h1["rolling_path"]))
    n_games_ge_2024 = sum(1 for g in games if int(g["season"]) >= 2024)
    if n_games_ge_2024:
        fail_reasons.append(f"n_rows_season_ge_2024 games.csv={n_games_ge_2024}")

    weekly, tw_games, pbp_game_meta, weather_rows, n_pbp_ge_2024 = _load_pbp_week_rows(
        cache, PBP_SEASONS
    )
    counts["n_rows_season_ge_2024"] = int(n_games_ge_2024 + n_pbp_ge_2024)
    if counts["n_rows_season_ge_2024"] > 0:
        fail_reasons.append(f"n_rows_season_ge_2024={counts['n_rows_season_ge_2024']}")

    # Content-addressed 2012 / off-panel schedule snapshot (derived AFTER PBP hash).
    panel_ids = {str(g["game_id"]).strip() for g in games}
    offpanel = [r for r in pbp_game_meta if int(r["season"]) == 2012 or r["game_id"] not in panel_ids]
    offpanel.sort(key=lambda r: (int(r["season"]), int(r.get("week") or 0), r["game_id"]))
    snap_fields = [
        "game_id",
        "season",
        "week",
        "home",
        "away",
        "game_date",
        "start_time_raw",
        "kickoff_utc",
        "kickoff_source",
        "parse_status",
    ]
    snap_sha = _write_csv(INPUTS_DIR / "schedule_2012_offpanel_kickoffs.csv", snap_fields, offpanel)
    _H1_HASHES["schedule_2012_offpanel_kickoffs.csv"] = snap_sha
    if not snap_sha:
        blocked_reasons.append("2012 schedule snapshot hash missing")
    y2012 = [r for r in offpanel if int(r["season"]) == 2012]
    if not y2012:
        blocked_reasons.append("2012 schedule snapshot empty")

    weather_fields = [
        "game_id",
        "season",
        "week",
        "temp",
        "wind",
        "roof",
        "surface",
        "parent_pbp",
        "parent_pbp_sha256",
    ]
    weather_rows_sorted = sorted(
        weather_rows, key=lambda r: (int(r["season"]), int(r.get("week") or 0), r["game_id"])
    )
    weather_sha = _write_csv(
        INPUTS_DIR / "pbp_weather_game_2012_2023.csv", weather_fields, weather_rows_sorted
    )
    _H1_HASHES["pbp_weather_game_2012_2023.csv"] = weather_sha

    history: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    tw_raw: Dict[Tuple[int, int, str], Set[str]] = defaultdict(set)
    for rec in weekly:
        history[str(rec["franchise"])].append(rec)
        tw_raw[(int(rec["season"]), int(rec["week"]), str(rec["franchise"]))].add(str(rec["team"]))
    pin_map = {
        (int(r["season"]), int(r["week"]), str(r["team"])): r for r in pinned_rolling
    }

    reconstructed = _reconstruct_rolling(weekly, history)
    n_vintage, vintage_reasons = _compare_vintage(reconstructed, pinned_rolling)
    if n_vintage:
        blocked_reasons.append(f"vintage drift vs #646 rolling 1b07654e n={n_vintage}")
        blocked_reasons.extend(vintage_reasons[:8])

    # Kickoff lookup: panel first, then 2012/off-panel snapshot. No live schedule.
    kickoff_by_gid: Dict[str, Optional[datetime]] = {}
    kickoff_src: Dict[str, str] = {}
    for g in games:
        gid = str(g["game_id"]).strip()
        ko = _parse_utc(g.get("kickoff_utc"))
        kickoff_by_gid[gid] = ko
        kickoff_src[gid] = "games.csv.kickoff_utc"
    for rec in pbp_game_meta:
        gid = rec["game_id"]
        if gid in kickoff_by_gid and kickoff_by_gid[gid] is not None:
            continue
        ko = _parse_utc(rec.get("kickoff_utc")) if rec.get("kickoff_utc") else None
        kickoff_by_gid[gid] = ko
        kickoff_src[gid] = rec.get("kickoff_source") or "pbp_snapshot"

    def _tw_kickoff(s: int, w: int, franchise: str) -> Tuple[Optional[datetime], List[str], bool]:
        gids = sorted(tw_games.get((s, w, franchise), set()))
        unknown = False
        times: List[datetime] = []
        for gid in gids:
            ko = kickoff_by_gid.get(gid)
            if ko is None:
                unknown = True
            else:
                times.append(ko)
        if not times:
            return None, gids, True if gids else True
        return max(times), gids, unknown or (not gids)

    # First-pass windows
    inversions: List[Dict[str, Any]] = []
    week1_rows: List[Dict[str, Any]] = []
    intra_rows: List[Dict[str, Any]] = []
    pass1: Dict[Tuple[str, str], Set[str]] = {}
    pass1_keys: Dict[Tuple[str, str], List[Tuple[int, int, str]]] = {}

    n_windows = 0
    n_empty = 0
    n_ok = 0
    n_fail = 0
    n_unknown = 0
    n_self = 0
    n_contrib = 0
    n_cross = 0
    n_alias_drop = 0
    n_rest_ph = 0
    n_neutral = 0
    n_week1 = 0

    games_by_sw: Dict[Tuple[int, int], List[Dict[str, str]]] = defaultdict(list)
    for g in games:
        games_by_sw[(int(g["season"]), int(g["week"]))].append(g)

    for g in games:
        season = int(g["season"])
        week = int(g["week"])
        gid = str(g["game_id"]).strip()
        ko_g = kickoff_by_gid.get(gid)
        if float(g.get("rest_days_home") or 0) == 7.0 and float(g.get("rest_days_away") or 0) == 7.0:
            n_rest_ph += 1
        if str(g.get("nflverse_location") or "").strip() == "Neutral":
            n_neutral += 1
        if week == 1:
            n_week1 += 1
        same_week = games_by_sw[(season, week)]
        if ko_g is not None:
            for other in same_week:
                oid = str(other["game_id"]).strip()
                if oid == gid:
                    continue
                oko = kickoff_by_gid.get(oid)
                if oko is not None and oko < ko_g:
                    intra_rows.append(
                        {
                            "game_id": gid,
                            "season": season,
                            "week": week,
                            "excluded_game_id": oid,
                            "kickoff_G": _fmt_utc(ko_g),
                            "kickoff_excluded": _fmt_utc(oko),
                            "note": "same (season,week) earlier kickoff excluded by week <",
                        }
                    )

        for side, raw in (("home", g["home"]), ("away", g["away"])):
            franchise = _franchise(raw)
            rolled = _rolling_before(history, franchise=franchise, season=season, week=week)
            if rolled is None:
                n_empty += 1
                pass1[(gid, side)] = set()
                pass1_keys[(gid, side)] = []
                continue
            n_windows += 1
            n_contrib += int(rolled["games"])
            tws: List[Tuple[int, int, str]] = list(rolled["team_weeks"])
            pass1_keys[(gid, side)] = tws
            contrib_gids: Set[str] = set()
            raw_codes: Set[str] = set()
            max_ko: Optional[datetime] = None
            max_gid = ""
            unknown = False
            for ts, tw, tf in tws:
                kmax, gids, unk = _tw_kickoff(ts, tw, tf)
                contrib_gids.update(gids)
                unknown = unknown or unk
                raw_codes |= tw_raw.get((ts, tw, tf), set())
                expected = set(gids)
                for alias in _aliases_for(tf):
                    expected |= tw_games.get((ts, tw, _franchise(alias)), set())
                missing_alias = expected - set(gids)
                if missing_alias:
                    n_alias_drop += len(missing_alias)
                if kmax is not None and (max_ko is None or kmax > max_ko):
                    max_ko = kmax
                    for cg in gids:
                        if kickoff_by_gid.get(cg) == kmax:
                            max_gid = cg
                            break
            pass1[(gid, side)] = set(contrib_gids)
            if gid in contrib_gids:
                n_self += 1
            crossed = False
            for a, b in RELOCATION_PAIRS:
                if a in raw_codes and b in raw_codes:
                    crossed = True
            if crossed:
                n_cross += 1
            if week == 1:
                week1_rows.append(
                    {
                        "game_id": gid,
                        "season": season,
                        "week": week,
                        "side": side,
                        "franchise": franchise,
                        "n_in_window": rolled["games"],
                        "first": rolled["first"],
                        "last": rolled["last"],
                    }
                )
            if unknown:
                n_unknown += 1
                continue
            if ko_g is None:
                n_unknown += 1
                continue
            if max_ko is None:
                n_unknown += 1
                continue
            if max_ko >= ko_g:
                n_fail += 1
                inversions.append(
                    {
                        "game_id": gid,
                        "season": season,
                        "week": week,
                        "side": side,
                        "franchise": franchise,
                        "kickoff_G": _fmt_utc(ko_g),
                        "max_kickoff_TW": _fmt_utc(max_ko),
                        "contrib_game_id": max_gid,
                        "kickoff_contrib": _fmt_utc(max_ko),
                        "n_contributors": rolled["games"],
                        "first": rolled["first"],
                        "last": rolled["last"],
                    }
                )
            else:
                n_ok += 1

    # Re-emit (invariant 6): rebuild contributor game_id sets from the same weekly H.
    n_inv6 = 0
    for g in games:
        gid = str(g["game_id"]).strip()
        season = int(g["season"])
        week = int(g["week"])
        for side, raw in (("home", g["home"]), ("away", g["away"])):
            franchise = _franchise(raw)
            rolled = _rolling_before(history, franchise=franchise, season=season, week=week)
            if rolled is None:
                recon_ids: Set[str] = set()
            else:
                recon_ids = set()
                for ts, tw, tf in rolled["team_weeks"]:
                    recon_ids |= set(tw_games.get((ts, tw, tf), set()))
            if recon_ids != pass1.get((gid, side), set()):
                n_inv6 += 1
            pin = pin_map.get((season, week, franchise))
            recon_n = 0 if rolled is None else int(rolled["games"])
            if pin is not None and int(float(pin["games_in_window_5"] or 0)) != recon_n:
                n_inv6 += 1

    # COVID / flex: week-label order ≠ calendar kickoff order across different week labels.
    # One flag row per (season, week_lo, week_hi) where max(kickoff(lo)) > min(kickoff(hi)).
    covid_rows: List[Dict[str, Any]] = []
    by_season: Dict[int, List[Dict[str, str]]] = defaultdict(list)
    for g in games:
        by_season[int(g["season"])].append(g)
    for season, rows in by_season.items():
        week_minmax: Dict[int, Tuple[datetime, datetime, str, str]] = {}
        for g in rows:
            ko = kickoff_by_gid.get(str(g["game_id"]).strip())
            if ko is None:
                continue
            w = int(g["week"])
            gid = str(g["game_id"]).strip()
            if w not in week_minmax:
                week_minmax[w] = (ko, ko, gid, gid)
            else:
                mn, mx, gid_mn, gid_mx = week_minmax[w]
                if ko < mn:
                    mn, gid_mn = ko, gid
                if ko > mx:
                    mx, gid_mx = ko, gid
                week_minmax[w] = (mn, mx, gid_mn, gid_mx)
        weeks = sorted(week_minmax)
        for i, w_lo in enumerate(weeks):
            for w_hi in weeks[i + 1 :]:
                max_lo = week_minmax[w_lo][1]
                min_hi = week_minmax[w_hi][0]
                if max_lo > min_hi:
                    covid_rows.append(
                        {
                            "season": season,
                            "earlier_week": w_lo,
                            "later_week": w_hi,
                            "earlier_week_max_game_id": week_minmax[w_lo][3],
                            "later_week_min_game_id": week_minmax[w_hi][2],
                            "earlier_week_max_kickoff": _fmt_utc(max_lo),
                            "later_week_min_kickoff": _fmt_utc(min_hi),
                            "note": "week ordinal order != calendar kickoff order",
                        }
                    )

    # Rest catalog (sidecar only; no re-sim).
    team_games: Dict[str, List[Tuple[datetime, str, int, int]]] = defaultdict(list)
    for rec in pbp_game_meta:
        ko = _parse_utc(rec.get("kickoff_utc")) if rec.get("kickoff_utc") else None
        if ko is None:
            continue
        for side in ("home", "away"):
            raw = rec.get(side)
            if not raw:
                continue
            team_games[_franchise(str(raw))].append(
                (ko, rec["game_id"], int(rec["season"]), int(rec.get("week") or 0))
            )
    for g in games:
        ko = kickoff_by_gid.get(str(g["game_id"]).strip())
        if ko is None:
            continue
        for raw in (g["home"], g["away"]):
            team_games[_franchise(raw)].append(
                (ko, str(g["game_id"]).strip(), int(g["season"]), int(g["week"]))
            )
    prev_lookup: Dict[Tuple[str, str], Tuple[str, float]] = {}
    for franchise, items in team_games.items():
        uniq: Dict[str, Tuple[datetime, str, int, int]] = {}
        for ko, gid, s, w in items:
            uniq[gid] = (ko, gid, s, w)
        ordered = sorted(uniq.values(), key=lambda t: t[0])
        prev: Optional[Tuple[datetime, str, int, int]] = None
        for ko, gid, s, w in ordered:
            if prev is not None:
                days = (ko - prev[0]).total_seconds() / 86400.0
                prev_lookup[(franchise, gid)] = (prev[1], days)
            prev = (ko, gid, s, w)

    rest_rows: List[Dict[str, Any]] = []
    n_true_rest_ne_7 = 0
    n_short_rest_lt_6 = 0
    for g in games:
        gid = str(g["game_id"]).strip()
        fh = _franchise(g["home"])
        fa = _franchise(g["away"])
        prev_h = prev_lookup.get((fh, gid))
        prev_a = prev_lookup.get((fa, gid))
        true_h = "" if prev_h is None else round(prev_h[1], 3)
        true_a = "" if prev_a is None else round(prev_a[1], 3)
        rest_rows.append(
            {
                "game_id": gid,
                "season": g["season"],
                "week": g["week"],
                "home": g["home"],
                "away": g["away"],
                "rest_emit_home": g.get("rest_days_home"),
                "rest_emit_away": g.get("rest_days_away"),
                "rest_true_home": true_h,
                "rest_true_away": true_a,
                "prev_game_home": "" if prev_h is None else prev_h[0],
                "prev_game_away": "" if prev_a is None else prev_a[0],
            }
        )
        vals = [v for v in (true_h, true_a) if v != ""]
        if any(abs(float(v) - 7.0) > 0.05 for v in vals):
            n_true_rest_ne_7 += 1
        if any(float(v) < 6.0 for v in vals):
            n_short_rest_lt_6 += 1

    neutral_rows = [
        {
            "game_id": g["game_id"],
            "season": g["season"],
            "week": g["week"],
            "home": g["home"],
            "away": g["away"],
            "kickoff_utc": g.get("kickoff_utc"),
            "nflverse_location": g.get("nflverse_location"),
            "super_bowl": int(g["week"]) == 22,
        }
        for g in games
        if str(g.get("nflverse_location") or "").strip() == "Neutral"
    ]

    counts.update(
        {
            "n_games": len(games),
            "n_windows": n_windows,
            "n_windows_empty": n_empty,
            "n_windows_empty_exception_list": [],
            "n_invariant6_game_id_diff": n_inv6,
            "n_franchise_alias_drop": n_alias_drop,
            "n_contributors": n_contrib,
            "n_kickoff_ok": n_ok,
            "n_kickoff_fail": n_fail,
            "n_kickoff_unknown": n_unknown,
            "n_self_game_leak": n_self,
            "n_week1": n_week1,
            "n_covid_flex_flags": len(covid_rows),
            "n_intraweek_conservative": len(intra_rows),
            "n_franchise_cross": n_cross,
            "n_rest_placeholder": n_rest_ph,
            "n_neutral": n_neutral,
            "n_true_rest_ne_7": n_true_rest_ne_7,
            "n_short_rest_lt_6": n_short_rest_lt_6,
            "n_vintage_mismatch": n_vintage,
            "schedule_2012_sha256": snap_sha,
            "weather_extract_sha256": weather_sha,
            "rolling_csv_sha256": h1.get("rolling_csv_sha256") or "",
            "oos_sha256": h1.get("oos_sha256") or "",
        }
    )

    if counts["n_games"] != N_GAMES_EXPECT:
        fail_reasons.append(f"n_games={counts['n_games']} want={N_GAMES_EXPECT}")
    if counts["n_windows_empty"] > 0:
        fail_reasons.append(f"n_windows_empty={counts['n_windows_empty']}")
    if counts["n_windows_empty_exception_list"] != []:
        fail_reasons.append("n_windows_empty_exception_list not empty")
    if counts["n_rows_season_ge_2024"] > 0:
        fail_reasons.append(f"n_rows_season_ge_2024={counts['n_rows_season_ge_2024']}")
    if counts["n_invariant6_game_id_diff"] != 0:
        fail_reasons.append(f"n_invariant6_game_id_diff={counts['n_invariant6_game_id_diff']}")
    if counts["n_franchise_alias_drop"] > 0:
        fail_reasons.append(f"n_franchise_alias_drop={counts['n_franchise_alias_drop']}")
    if counts["n_kickoff_fail"] > 0:
        fail_reasons.append(f"n_kickoff_fail={counts['n_kickoff_fail']}")
    if counts["n_kickoff_unknown"] > 0:
        fail_reasons.append(f"n_kickoff_unknown={counts['n_kickoff_unknown']}")
    if counts["n_self_game_leak"] > 0:
        fail_reasons.append(f"n_self_game_leak={counts['n_self_game_leak']}")
    if not str(counts["games_csv_sha256"]).startswith("4fe1cdd7"):
        fail_reasons.append(
            f"games_csv_sha256={counts['games_csv_sha256']} want prefix 4fe1cdd7"
        )
    if counts["games_csv_sha256"] != GAMES_CSV_SHA256:
        fail_reasons.append("games_csv_sha256 full mismatch vs 4fe1cdd7… pin")
    if not snap_sha:
        blocked_reasons.append("2012 schedule snapshot hash missing")

    extra = [
        f"vintage_mismatch={n_vintage}",
        f"2012_snapshot_rows={len(y2012)}",
        f"offpanel_rows={len(offpanel)}",
        f"weather_rows={len(weather_rows_sorted)}",
    ]
    return _seal_and_exit(
        counts,
        blocked_reasons,
        fail_reasons,
        {
            "schedule_2012_offpanel_kickoffs.csv": snap_sha,
            "pbp_weather_game_2012_2023.csv": weather_sha,
        },
        forecast_ts,
        inversions=inversions,
        week1=week1_rows,
        covid=covid_rows,
        intra=intra_rows,
        rest_rows=rest_rows,
        neutral_rows=neutral_rows,
        extra_notes=extra,
    )


def _seal_and_exit(
    counts: Dict[str, Any],
    blocked_reasons: Sequence[str],
    fail_reasons: Sequence[str],
    extra_sha: Mapping[str, str],
    forecast_ts: datetime,
    *,
    inversions: Sequence[Mapping[str, Any]],
    week1: Sequence[Mapping[str, Any]],
    covid: Sequence[Mapping[str, Any]],
    intra: Sequence[Mapping[str, Any]],
    rest_rows: Sequence[Mapping[str, Any]],
    neutral_rows: Sequence[Mapping[str, Any]],
    extra_notes: Sequence[str],
) -> int:
    if blocked_reasons:
        verdict = "BLOCKED"
    elif fail_reasons:
        verdict = "FAIL"
    else:
        verdict = "PASS"
    counts["verdict"] = verdict
    counts["blocked_reasons"] = list(blocked_reasons)
    counts["fail_reasons"] = list(fail_reasons)
    counts["ticket"] = TICKET
    counts["label"] = LABEL
    counts["cert_candidate"] = CERT_CANDIDATE
    counts["authority"] = {
        "decision_sha8": DECISION_SHA8,
        "cos_order_sha8": COS_ORDER_SHA8,
        "imv_sha8": IMV_SHA8,
        "feasibility_sha8": FEASIBILITY_SHA8,
        "addendum_sha8": ADDENDUM_SHA8,
        "ack_sha8": ACK_SHA8,
        "alex_spec_sha8": ALEX_SPEC_SHA8,
    }
    counts["nfl_nogo"] = True
    counts["coming_soon"] = True
    counts["f2_frozen"] = True
    counts["exp_a_run"] = False
    counts["simulate_nfl_game_called"] = False

    artifact_sha: Dict[str, str] = dict(_H1_HASHES)
    artifact_sha.update(extra_sha)

    artifact_sha["inversions.csv"] = _write_csv(
        OUT_DIR / "inversions.csv",
        [
            "game_id",
            "season",
            "week",
            "side",
            "franchise",
            "kickoff_G",
            "max_kickoff_TW",
            "contrib_game_id",
            "kickoff_contrib",
            "n_contributors",
            "first",
            "last",
        ],
        inversions,
    )
    artifact_sha["week1_windows.csv"] = _write_csv(
        OUT_DIR / "week1_windows.csv",
        [
            "game_id",
            "season",
            "week",
            "side",
            "franchise",
            "n_in_window",
            "first",
            "last",
        ],
        week1,
    )
    artifact_sha["covid_flex_flags.csv"] = _write_csv(
        OUT_DIR / "covid_flex_flags.csv",
        [
            "season",
            "earlier_week",
            "later_week",
            "earlier_week_max_game_id",
            "later_week_min_game_id",
            "earlier_week_max_kickoff",
            "later_week_min_kickoff",
            "note",
        ],
        covid,
    )
    artifact_sha["intraweek_conservative.csv"] = _write_csv(
        OUT_DIR / "intraweek_conservative.csv",
        [
            "game_id",
            "season",
            "week",
            "excluded_game_id",
            "kickoff_G",
            "kickoff_excluded",
            "note",
        ],
        intra,
    )
    artifact_sha["rest_catalog.csv"] = _write_csv(
        OUT_DIR / "rest_catalog.csv",
        [
            "game_id",
            "season",
            "week",
            "home",
            "away",
            "rest_emit_home",
            "rest_emit_away",
            "rest_true_home",
            "rest_true_away",
            "prev_game_home",
            "prev_game_away",
        ],
        rest_rows,
    )
    artifact_sha["neutral_catalog.csv"] = _write_csv(
        OUT_DIR / "neutral_catalog.csv",
        [
            "game_id",
            "season",
            "week",
            "home",
            "away",
            "kickoff_utc",
            "nflverse_location",
            "super_bowl",
        ],
        neutral_rows,
    )

    artifact_sha["counts.json"] = _write_json(OUT_DIR / "counts.json", counts)

    sha8_table = {name: _sha8(sha) for name, sha in sorted(artifact_sha.items()) if sha}
    manifest = {
        "run_id": f"nfl-exp-e-kickoff-asof-{TICKET}-{forecast_ts.strftime('%Y%m%dT%H%M%SZ')}",
        "ticket": TICKET,
        "forecast_ts_utc": _fmt_utc(forecast_ts),
        "verdict": verdict,
        "n_kickoff_fail": counts.get("n_kickoff_fail"),
        "n_games": counts.get("n_games"),
        "authority": counts.get("authority"),
        "h1_hashes": {k: v for k, v in _H1_HASHES.items()},
        "artifact_sha256": artifact_sha,
        "artifact_sha8": sha8_table,
        "blocked_reasons": list(blocked_reasons),
        "fail_reasons": list(fail_reasons),
        "notes": list(extra_notes),
        "forbidden": {
            "exp_a": False,
            "simulate_nfl_game": False,
            "odds_api": False,
            "database_url_required": False,
            "merge": False,
            "deploy": False,
            "cert_claim": False,
        },
        "nfl_nogo": True,
        "cert_candidate": 0,
        "f2_frozen": True,
        "sealed": 1,
    }
    artifact_sha["manifest.json"] = _write_json(OUT_DIR / "manifest.json", manifest)
    sha8_table["manifest.json"] = _sha8(artifact_sha["manifest.json"])

    report = _render_report(counts, verdict, artifact_sha, sha8_table, extra_notes)
    artifact_sha["REPORT.md"] = _write_text(OUT_DIR / "REPORT.md", report)
    sha8_table["REPORT.md"] = _sha8(artifact_sha["REPORT.md"])

    # Final SHA256SUMS = inputs + outputs (inputs were written first, before parse).
    _write_sha256sums(OUT_DIR / "SHA256SUMS", artifact_sha)
    _write_json(OUT_DIR / "artifact_sha8.json", sha8_table)

    print(json.dumps({"verdict": verdict, "n_kickoff_fail": counts.get("n_kickoff_fail"), "sha8": sha8_table}, indent=2), flush=True)
    if verdict == "PASS":
        return 0
    if verdict == "BLOCKED":
        return 2
    return 3


def _render_report(
    counts: Mapping[str, Any],
    verdict: str,
    artifact_sha: Mapping[str, str],
    sha8_table: Mapping[str, str],
    extra_notes: Sequence[str],
) -> str:
    lines = [
        "# Experiment E — kickoff-honest as-of audit (t4586u / t4598u)",
        "",
        "**EXP E ONLY · CERT=0 · NFL NO-GO · F2 FROZEN · sealed=1 · #648 DRAFT · do not merge**",
        "",
        f"**VERDICT: `{verdict}`** · `n_kickoff_fail={counts.get('n_kickoff_fail')}`",
        "",
        "## Authority",
        "",
        "| item | sha8 |",
        "|---|---|",
        f"| Ryan CLEAR t4598u | {DECISION_SHA8} |",
        f"| CoS execute order | {COS_ORDER_SHA8} |",
        f"| IMV PASS_PROTOCOL v2 | {IMV_SHA8} |",
        f"| Cursor FEASIBILITY v1.1 | {FEASIBILITY_SHA8} |",
        f"| Alex SPEC | {ALEX_SPEC_SHA8} |",
        f"| ESTIMATOR addendum | {ADDENDUM_SHA8} |",
        f"| Cursor ACK | {ACK_SHA8} |",
        f"| games.csv pin | {_sha8(GAMES_CSV_SHA256)} |",
        f"| #646 rolling CSV | {_sha8(ROLLING_CSV_SHA256)} |",
        "",
        "## counts.json (v1.1 §1.7)",
        "",
        "| key | value |",
        "|---|---:|",
    ]
    for key in (
        "n_games",
        "n_windows",
        "n_windows_empty",
        "n_rows_season_ge_2024",
        "n_invariant6_game_id_diff",
        "n_franchise_alias_drop",
        "n_contributors",
        "n_kickoff_ok",
        "n_kickoff_fail",
        "n_kickoff_unknown",
        "n_self_game_leak",
        "n_week1",
        "n_covid_flex_flags",
        "n_intraweek_conservative",
        "n_franchise_cross",
        "n_rest_placeholder",
        "n_neutral",
    ):
        lines.append(f"| `{key}` | {counts.get(key)} |")
    lines.extend(
        [
            "",
            f"`n_windows_empty_exception_list` = `{counts.get('n_windows_empty_exception_list')}`",
            "",
            f"`games_csv_sha256` = `{counts.get('games_csv_sha256')}`",
            "",
            "## Artifact sha8",
            "",
            "| artifact | sha8 |",
            "|---|---|",
        ]
    )
    for name, sha8 in sorted(sha8_table.items()):
        lines.append(f"| `{name}` | `{sha8}` |")
    lines.extend(
        [
            "",
            "## Blocked / fail reasons",
            "",
            f"- blocked: {list(counts.get('blocked_reasons') or []) or 'none'}",
            f"- fail: {list(counts.get('fail_reasons') or []) or 'none'}",
            "",
            "## Notes",
            "",
        ]
    )
    for n in extra_notes:
        lines.append(f"- {n}")
    lines.extend(
        [
            "",
            "## Explicit non-runs",
            "",
            "- Exp A not run. β not fit. `simulate_nfl_game` not imported.",
            "- LOCKED_SCORING / config_overrides untouched.",
            "- Odds API not called. DATABASE_URL not required.",
            "- #646/#647/#648 not merged. 2024+ not used. F2 PHI@WSH not touched.",
            "- CERT=0. No fireable claim.",
            "",
            "NFL NO-GO · Coming Soon ON · F2 frozen · sealed=1",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
