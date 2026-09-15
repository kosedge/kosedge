"""2026 CFB current-season PBP proof — SportsDataverse / ESPN only.

No CFBD API. No cfbd_* loaders. Does not write the 2014–2025 historical lake
(``/Volumes/KosEdgeData/raw/cfb/pbp/``). Current-season bytes land on a
versioned ``pbp_current/as_of_YYYYMMDD/`` path (HD target) or the gitignored
repo research mirror.

Research-only. No model fit, opponent-adjusted ratings, Edge Board, or KEI.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.services.cfb_warehouse.pbp import PBP_CORE_COLUMNS, PBP_TAG
from src.services.cfb_warehouse.paths import (
    HD_RAW_PBP,
    HD_RAW_PBP_CURRENT,
    REPO_RAW_PBP,
    REPO_RESEARCH_PBP_CURRENT,
    REPO_ROOT,
    hd_mounted,
    hd_pbp_current_target,
)
from src.services.cfb_warehouse.sdv import SDV_BASE, fetch_sdv_file

SEASON = 2026
PROOF_VERSION = "cfb-2026-current-season-sdv-proof-v1"
SCHEDULE_TAG = "espn_cfb_schedules"
PBP_FILENAME = "play_by_play_2026.parquet"
SCHEDULE_FILENAME = "cfb_schedule_2026.parquet"
SCHEDULE_CSV_FALLBACK = "cfb_schedule_2026.csv"

# ESPN public routes (no key). Site summary is often 403 from datacenter IPs;
# sports.core plays is the individual-game path used here.
ESPN_SUMMARY_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/football/"
    "college-football/summary?event={game_id}"
)
ESPN_CORE_PLAYS_URL = (
    "https://sports.core.api.espn.com/v2/sports/football/leagues/"
    "college-football/events/{game_id}/competitions/{game_id}/plays?limit=300"
)
ESPN_USER_AGENT = "kosedge-cfb-2026-current-proof/1.0"

FORBIDDEN_HOST_FRAGMENTS = ("collegefootballdata.com", "api.collegefootballdata")

COMPLETED_STATUSES = frozenset(
    {
        "STATUS_FINAL",
        "STATUS_COMPLETED",
        "FINAL",
        "COMPLETED",
        "STATUS_FULL_TIME",
        "STATUS_FINAL_OT",
        "STATUS_FINAL_AOT",
        "STATUS_FINAL_PEN",
    }
)
NOT_COMPLETED_STATUSES = frozenset(
    {
        "STATUS_SCHEDULED",
        "STATUS_IN_PROGRESS",
        "STATUS_HALFTIME",
        "STATUS_END_PERIOD",
        "STATUS_DELAYED",
        "STATUS_POSTPONED",
        "STATUS_CANCELED",
        "STATUS_CANCELLED",
        "SCHEDULED",
        "IN_PROGRESS",
        "PRE",
        "IN",
    }
)

# Fields that #555 owned raw metrics require (plus pace / explosiveness / opp).
METRIC_FIELD_REQUIREMENTS: Dict[str, Sequence[str]] = {
    "EPA": ("EPA",),
    "EPA_success": ("EPA_success",),
    "scrimmage_play": ("scrimmage_play",),
    "pass": ("pass",),
    "rush": ("rush",),
    "down": ("down",),
    "distance": ("distance",),
    "start.yardsToEndzone": ("start.yardsToEndzone",),
    "drive.id": ("drive.id",),
    "type.text": ("type.text",),
    "pace": ("scrimmage_play", "game_id", "pos_team"),
    "true_pace_competitive": ("scrimmage_play", "game_id", "pos_team", "pos_score_diff"),
    "explosiveness": ("EPA", "statYardage", "scrimmage_play", "pass", "rush"),
    "scoring_opportunity": (
        "drive.id",
        "start.yardsToEndzone",
        "type.text",
        "game_id",
    ),
}

NULL_RATE_WARN = 0.01


def today_as_of(*, now: Optional[datetime] = None) -> str:
    stamp = now or datetime.now(timezone.utc)
    return stamp.strftime("%Y%m%d")


def historical_forbidden_dirs() -> List[Path]:
    return [HD_RAW_PBP.resolve(), REPO_RAW_PBP.resolve()]


def assert_not_historical_write(dest: Path) -> None:
    """Refuse any write that would land in the 2014–2025 lake."""
    resolved = dest.resolve()
    for forbidden in historical_forbidden_dirs():
        try:
            resolved.relative_to(forbidden)
        except ValueError:
            continue
        raise RuntimeError(
            f"refusing write into historical PBP lake {forbidden} (got {resolved})"
        )
    dest_s = str(resolved)
    if "/raw/cfb/pbp/" in dest_s and "pbp_current" not in dest_s:
        raise RuntimeError(f"refusing historical-shaped path {resolved}")


def research_dest_dir(as_of: str) -> Path:
    """VM restore path: gitignored research tree. Never historical warehouse/raw/pbp."""
    dest = REPO_RESEARCH_PBP_CURRENT / f"as_of_{as_of}"
    assert_not_historical_write(dest)
    return dest


def path_convention(as_of: str) -> Dict[str, Any]:
    return {
        "as_of": as_of,
        "historical_canonical_hd": str(HD_RAW_PBP),
        "historical_note": (
            "2014–2025 Aug 13 lake is CANONICAL. Do not overwrite "
            "play_by_play_{2014-2025}.parquet."
        ),
        "current_season_hd_target": str(hd_pbp_current_target(as_of)),
        "current_season_hd_root": str(HD_RAW_PBP_CURRENT),
        "vm_research_path": str(research_dest_dir(as_of)),
        "vm_research_root": str(REPO_RESEARCH_PBP_CURRENT),
        "hd_mounted": hd_mounted(),
        "prefer_hd_current_when_mounted": True,
        "versioning": "raw/cfb/pbp_current/as_of_YYYYMMDD/",
    }


def _sha256(path: Path, *, chunk: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _forbid_cfbd_url(url: str) -> None:
    lower = url.lower()
    for frag in FORBIDDEN_HOST_FRAGMENTS:
        if frag in lower:
            raise RuntimeError(f"CFBD is soft-parked; refusing URL {url}")


def restore_sdv_file(
    tag: str,
    filename: str,
    *,
    dest_dir: Path,
    timeout: int = 300,
) -> Path:
    """Download-once SDV release into dest_dir. No CFBD."""
    url = f"{SDV_BASE}/{tag}/{filename}"
    _forbid_cfbd_url(url)
    dest_dir.mkdir(parents=True, exist_ok=True)
    assert_not_historical_write(dest_dir / filename)
    return fetch_sdv_file(tag, filename, cache_dir=dest_dir, timeout=timeout)


def restore_2026_pbp(*, dest_dir: Path, timeout: int = 300) -> Path:
    return restore_sdv_file(PBP_TAG, PBP_FILENAME, dest_dir=dest_dir, timeout=timeout)


def restore_2026_schedule(*, dest_dir: Path, timeout: int = 120) -> Path:
    try:
        return restore_sdv_file(
            SCHEDULE_TAG, SCHEDULE_FILENAME, dest_dir=dest_dir, timeout=timeout
        )
    except Exception:  # noqa: BLE001 — csv fallback is same SDV tag
        return restore_sdv_file(
            SCHEDULE_TAG, SCHEDULE_CSV_FALLBACK, dest_dir=dest_dir, timeout=timeout
        )


def _first_col(df, names: Sequence[str]) -> Optional[str]:
    cols = {str(c): c for c in df.columns}
    lower = {str(c).lower(): c for c in df.columns}
    for name in names:
        if name in cols:
            return str(cols[name])
        if name.lower() in lower:
            return str(lower[name.lower()])
    return None


def _as_str_id(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    try:
        if isinstance(raw, float) and raw != raw:
            return None
    except TypeError:
        pass
    text = str(raw).strip()
    if not text or text.lower() in {"none", "nan", "<na>"}:
        return None
    if text.endswith(".0") and text.replace(".", "", 1).replace("-", "", 1).isdigit():
        text = text[:-2]
    return text


def classify_status(
    status: Any,
    *,
    completed_flag: Any = None,
    home_score: Any = None,
    away_score: Any = None,
) -> str:
    token = str(status or "").strip().upper().replace(" ", "_")
    if token in COMPLETED_STATUSES:
        return "completed"
    if token in NOT_COMPLETED_STATUSES:
        return "not_completed"
    flag = completed_flag
    if isinstance(flag, str):
        flag = flag.strip().lower() in {"1", "true", "t", "yes"}
    if flag is True:
        return "completed"
    if flag is False and token:
        return "not_completed"
    try:
        hs = None if home_score in (None, "") else float(home_score)
        aws = None if away_score in (None, "") else float(away_score)
    except (TypeError, ValueError):
        hs = aws = None
    if hs is not None and aws is not None and token in {"", "STATUS_UNKNOWN"}:
        return "completed_inferred_from_scores"
    if token:
        return "unknown_status"
    return "unknown_status"


def load_schedule_frame(path: Path):
    import pandas as pd

    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_parquet(path)


def schedule_game_rows(df) -> List[Dict[str, Any]]:
    gid_col = _first_col(df, ("game_id", "id", "gameId", "game.id"))
    if not gid_col:
        raise ValueError(f"schedule missing game_id-like column; have {list(df.columns)}")
    status_col = _first_col(
        df, ("status", "status_type_name", "type", "status.type.name")
    )
    completed_col = _first_col(
        df, ("status_type_completed", "completed", "status.completed")
    )
    week_col = _first_col(df, ("week", "week_number", "game_week"))
    season_col = _first_col(df, ("season", "year"))
    home_col = _first_col(
        df, ("home_team_name", "homeTeamName", "home_team", "home_display_name")
    )
    away_col = _first_col(
        df, ("away_team_name", "awayTeamName", "away_team", "away_display_name")
    )
    hs_col = _first_col(df, ("home_score", "homeScore", "home_points"))
    as_col = _first_col(df, ("away_score", "awayScore", "away_points"))
    date_col = _first_col(df, ("game_date", "date", "start_date", "kickoff"))

    rows: List[Dict[str, Any]] = []
    for rec in df.to_dict(orient="records"):
        gid = _as_str_id(rec.get(gid_col))
        if not gid:
            continue
        status = rec.get(status_col) if status_col else None
        completed_flag = rec.get(completed_col) if completed_col else None
        home_score = rec.get(hs_col) if hs_col else None
        away_score = rec.get(as_col) if as_col else None
        klass = classify_status(
            status,
            completed_flag=completed_flag,
            home_score=home_score,
            away_score=away_score,
        )
        week_raw = rec.get(week_col) if week_col else None
        try:
            week = int(week_raw) if week_raw is not None and str(week_raw) != "nan" else None
        except (TypeError, ValueError):
            week = None
        rows.append(
            {
                "game_id": gid,
                "status_raw": None if status is None else str(status),
                "status_class": klass,
                "week": week,
                "season": rec.get(season_col) if season_col else SEASON,
                "home": None if home_col is None else rec.get(home_col),
                "away": None if away_col is None else rec.get(away_col),
                "home_score": home_score,
                "away_score": away_score,
                "date": None if date_col is None else rec.get(date_col),
            }
        )
    return rows


def pbp_game_ids(df) -> Set[str]:
    col = _first_col(df, ("game_id", "gameId", "id.game"))
    if not col:
        return set()
    out: Set[str] = set()
    for raw in df[col].tolist():
        gid = _as_str_id(raw)
        if gid:
            out.add(gid)
    return out


def reconcile_coverage(
    schedule_rows: Sequence[Mapping[str, Any]],
    pbp_ids: Iterable[str],
) -> Dict[str, Any]:
    pbp = {str(g) for g in pbp_ids}
    sched_ids = {r["game_id"] for r in schedule_rows}
    completed = [r for r in schedule_rows if r["status_class"].startswith("completed")]
    not_completed = [r for r in schedule_rows if r["status_class"] == "not_completed"]
    unknown = [r for r in schedule_rows if r["status_class"] == "unknown_status"]
    completed_ids = {r["game_id"] for r in completed}
    completed_in_pbp = sorted(completed_ids & pbp)
    completed_missing_pbp = sorted(completed_ids - pbp)
    pbp_not_on_schedule = sorted(pbp - sched_ids)
    pbp_not_completed_on_schedule = sorted(pbp & ({r["game_id"] for r in not_completed}))
    schedule_without_pbp = sorted(sched_ids - pbp)

    by_week: Dict[str, Dict[str, int]] = {}
    for row in schedule_rows:
        key = str(row.get("week") if row.get("week") is not None else "unknown")
        bucket = by_week.setdefault(
            key,
            {
                "scheduled": 0,
                "completed": 0,
                "completed_in_pbp": 0,
                "completed_missing_pbp": 0,
            },
        )
        bucket["scheduled"] += 1
        if row["status_class"].startswith("completed"):
            bucket["completed"] += 1
            if row["game_id"] in pbp:
                bucket["completed_in_pbp"] += 1
            else:
                bucket["completed_missing_pbp"] += 1

    return {
        "schedule_games": len(schedule_rows),
        "schedule_unique_ids": len(sched_ids),
        "pbp_games": len(pbp),
        "completed_on_schedule": len(completed),
        "not_completed_on_schedule": len(not_completed),
        "unknown_status_on_schedule": len(unknown),
        "completed_in_pbp": len(completed_in_pbp),
        "completed_missing_pbp": len(completed_missing_pbp),
        "pbp_not_on_schedule": len(pbp_not_on_schedule),
        "pbp_not_completed_on_schedule": len(pbp_not_completed_on_schedule),
        "schedule_without_pbp": len(schedule_without_pbp),
        "coverage_rate_completed": (
            round(len(completed_in_pbp) / len(completed), 6) if completed else None
        ),
        "completed_missing_pbp_ids": completed_missing_pbp[:40],
        "pbp_not_on_schedule_ids": pbp_not_on_schedule[:40],
        "schedule_without_pbp_ids": schedule_without_pbp[:40],
        "by_week": dict(sorted(by_week.items(), key=lambda kv: (kv[0] == "unknown", kv[0]))),
        "honest_gaps": _gap_notes(
            completed_missing=len(completed_missing_pbp),
            extra_pbp=len(pbp_not_on_schedule),
            unknown=len(unknown),
            pbp_not_final=len(pbp_not_completed_on_schedule),
            schedule_without_pbp=len(schedule_without_pbp),
        ),
    }


def _gap_notes(
    *,
    completed_missing: int,
    extra_pbp: int,
    unknown: int,
    pbp_not_final: int = 0,
    schedule_without_pbp: int = 0,
) -> List[str]:
    notes: List[str] = []
    if completed_missing:
        notes.append(
            f"{completed_missing} schedule-completed game(s) have no PBP rows "
            "(SDV in-season parquet lag or ESPN feed hole)."
        )
    else:
        notes.append("Every schedule-completed (STATUS_FINAL) game in this file is present in PBP.")
    if pbp_not_final:
        notes.append(
            f"{pbp_not_final} PBP game_id(s) are still STATUS_IN_PROGRESS / DELAYED / "
            "HALFTIME / END_PERIOD on the SDV schedule snapshot. Treat those as live or "
            "stale-status — not W−1 completed form unless independently finalized."
        )
    if schedule_without_pbp:
        notes.append(
            f"{schedule_without_pbp} schedule game(s) have zero PBP rows "
            "(mostly STATUS_DELAYED 0–0 in this snapshot)."
        )
    if extra_pbp:
        notes.append(
            f"{extra_pbp} PBP game_id(s) are absent from the 2026 schedule file."
        )
    if unknown:
        notes.append(f"{unknown} schedule row(s) have an unclassified status.")
    return notes


def _null_rate(series) -> Optional[float]:
    n = int(len(series))
    if n == 0:
        return None
    return round(float(series.isna().mean()), 6)


def field_support_matrix(df) -> Dict[str, Any]:
    cols = [str(c) for c in df.columns]
    colset = set(cols)
    n = int(len(df))
    core: Dict[str, Any] = {}
    for col in PBP_CORE_COLUMNS:
        present = col in colset
        rate = _null_rate(df[col]) if present else None
        core[col] = {
            "present": present,
            "null_rate": rate,
            "class": _field_class(present, rate),
        }

    extras = {}
    for col in (
        "half",
        "period",
        "scoring_opp",
        "sack",
        "TFL",
        "int",
        "havoc",
        "statYardage",
        "rz_play",
        "pos_score_diff",
        "PPA",
        "ppa",
    ):
        present = col in colset
        extras[col] = {
            "present": present,
            "null_rate": _null_rate(df[col]) if present else None,
        }

    metrics: Dict[str, Any] = {}
    for name, required in METRIC_FIELD_REQUIREMENTS.items():
        missing = [c for c in required if c not in colset]
        present_rates = {
            c: (_null_rate(df[c]) if c in colset else None) for c in required
        }
        if missing:
            klass = "UNSUPPORTED" if name in {"EPA", "EPA_success", "scrimmage_play"} else "PARTIAL"
        elif any((present_rates[c] or 0) > 0.25 for c in required):
            klass = "PARTIAL"
        else:
            klass = "SUPPORTED"
        metrics[name] = {
            "required": list(required),
            "missing": missing,
            "null_rates": present_rates,
            "class": klass,
        }

    return {
        "plays": n,
        "columns": len(cols),
        "core31_present": [c for c in PBP_CORE_COLUMNS if c in colset],
        "core31_absent": [c for c in PBP_CORE_COLUMNS if c not in colset],
        "core31": core,
        "extras": extras,
        "metrics": metrics,
        "ppa_present": bool(colset & {"PPA", "ppa"}),
        "havoc_flag_present": "havoc" in colset,
        "note": (
            "SUPPORTED means columns exist at usable null rates for #555 raw "
            "unadjusted metrics. Not a fitted rating. Havoc/ST still need field "
            "verification. PPA is optional and expected absent on SDV."
        ),
    }


def _field_class(present: bool, null_rate: Optional[float]) -> str:
    if not present:
        return "ABSENT"
    if null_rate is None:
        return "PRESENT_UNKNOWN_NULL"
    if null_rate > NULL_RATE_WARN:
        return "PRESENT_HIGH_NULL"
    return "PRESENT_LOW_NULL"


def espn_game_summary(game_id: str, *, timeout: int = 30) -> Dict[str, Any]:
    """Public ESPN individual-game path. No CFBD. Prefers core plays."""
    core = _espn_json(ESPN_CORE_PLAYS_URL.format(game_id=game_id), timeout=timeout)
    site = _espn_json(ESPN_SUMMARY_URL.format(game_id=game_id), timeout=timeout)
    out: Dict[str, Any] = {
        "game_id": game_id,
        "cfbd_used": False,
        "core_plays": core,
        "site_summary": site,
    }
    if core.get("ok"):
        payload = core.get("payload") or {}
        items = payload.get("items") if isinstance(payload, dict) else None
        count = payload.get("count") if isinstance(payload, dict) else None
        out.update(
            {
                "ok": True,
                "url": core.get("url"),
                "route": "espn_core_plays",
                "http_status": core.get("http_status"),
                "play_count": len(items) if isinstance(items, list) else None,
                "reported_count": count,
                "page_count": payload.get("pageCount") if isinstance(payload, dict) else None,
            }
        )
        core.pop("payload", None)
        return out
    if site.get("ok"):
        payload = site.get("payload") or {}
        drives = payload.get("drives") or {}
        drive_items: List[Any] = []
        if isinstance(drives, dict):
            previous = drives.get("previous") or []
            current = drives.get("current") or []
            if isinstance(previous, list):
                drive_items.extend(previous)
            if isinstance(current, list):
                drive_items.extend(current)
        play_n = 0
        for drive in drive_items:
            if isinstance(drive, dict):
                plays = drive.get("plays") or []
                if isinstance(plays, list):
                    play_n += len(plays)
        out.update(
            {
                "ok": True,
                "url": site.get("url"),
                "route": "espn_site_summary",
                "http_status": site.get("http_status"),
                "drive_count": len(drive_items),
                "play_count_from_drives": play_n,
            }
        )
        site.pop("payload", None)
        return out
    out.update(
        {
            "ok": False,
            "url": core.get("url") or site.get("url"),
            "error": core.get("error") or site.get("error"),
        }
    )
    return out


def _espn_json(url: str, *, timeout: int) -> Dict[str, Any]:
    _forbid_cfbd_url(url)
    req = Request(url, headers={"User-Agent": ESPN_USER_AGENT})
    try:
        with urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", "replace"))
            status = int(getattr(resp, "status", 200) or 200)
    except HTTPError as exc:
        return {"ok": False, "url": url, "error": f"HTTP {exc.code}"}
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "url": url, "error": str(exc)[:240]}
    return {"ok": True, "url": url, "http_status": status, "payload": payload}


def inspect_pbp(path: Path) -> Dict[str, Any]:
    import pandas as pd

    df = pd.read_parquet(path)
    seasons = []
    if "season" in df.columns:
        seasons = sorted({int(x) for x in df["season"].dropna().unique()})
    weeks = []
    if "week" in df.columns:
        weeks = sorted({int(x) for x in df["week"].dropna().unique()})
    games = pbp_game_ids(df)
    return {
        "path": str(path),
        "bytes": int(path.stat().st_size),
        "sha256": _sha256(path),
        "plays": int(len(df)),
        "games": len(games),
        "game_ids": sorted(games),
        "seasons_in_file": seasons,
        "weeks_in_file": weeks,
        "columns": int(len(df.columns)),
        "column_names_head": [str(c) for c in df.columns[:40]],
        "duplicate_id": (
            int(df.duplicated(subset=["id"]).sum()) if "id" in df.columns else None
        ),
        "field_support": field_support_matrix(df),
    }


def inspect_schedule(path: Path) -> Dict[str, Any]:
    df = load_schedule_frame(path)
    rows = schedule_game_rows(df)
    return {
        "path": str(path),
        "bytes": int(path.stat().st_size),
        "sha256": _sha256(path),
        "rows": int(len(df)),
        "columns": [str(c) for c in df.columns],
        "games": rows,
    }


def run_proof(
    *,
    as_of: Optional[str] = None,
    dest_dir: Optional[Path] = None,
    include_espn_sample: bool = True,
) -> Dict[str, Any]:
    stamp = as_of or today_as_of()
    dest = dest_dir or research_dest_dir(stamp)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    assert_not_historical_write(dest)

    pbp_path = restore_2026_pbp(dest_dir=dest)
    sched_path = restore_2026_schedule(dest_dir=dest)
    pbp = inspect_pbp(pbp_path)
    sched = inspect_schedule(sched_path)
    coverage = reconcile_coverage(sched["games"], pbp["game_ids"])

    espn_sample: Optional[Dict[str, Any]] = None
    if include_espn_sample:
        sample_id = None
        completed_in = [
            r["game_id"]
            for r in sched["games"]
            if r["status_class"].startswith("completed")
            and r["game_id"] in set(pbp["game_ids"])
        ]
        if completed_in:
            sample_id = completed_in[0]
        elif pbp["game_ids"]:
            sample_id = pbp["game_ids"][0]
        if sample_id:
            espn_sample = espn_game_summary(sample_id)

    # Drop bulky game lists from the committed summary; keep counts + samples.
    sched_summary = {
        k: v for k, v in sched.items() if k != "games"
    }
    sched_summary["status_counts"] = _count_by(sched["games"], "status_class")
    pbp_summary = {k: v for k, v in pbp.items() if k != "game_ids"}
    pbp_summary["game_ids_head"] = pbp["game_ids"][:20]

    return {
        "proof_version": PROOF_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "season": SEASON,
        "source": {
            "pbp": f"{SDV_BASE}/{PBP_TAG}/{PBP_FILENAME}",
            "schedule": f"{SDV_BASE}/{SCHEDULE_TAG}/{SCHEDULE_FILENAME}",
            "schedule_fallback": f"{SDV_BASE}/{SCHEDULE_TAG}/{SCHEDULE_CSV_FALLBACK}",
            "stack": "sportsdataverse espn_cfb_pbp + espn_cfb_schedules",
            "cfbd_used": False,
            "cfbd_parked": True,
        },
        "path_convention": path_convention(stamp),
        "vm_dest": str(dest),
        "pbp": pbp_summary,
        "schedule": sched_summary,
        "coverage": coverage,
        "espn_sample_game": espn_sample,
        "historical_inventory_rewritten": False,
        "research_only": True,
        "opponent_adjusted": False,
        "kei_or_edge_board": False,
    }


def _count_by(rows: Sequence[Mapping[str, Any]], key: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for row in rows:
        token = str(row.get(key) or "unknown")
        out[token] = out.get(token, 0) + 1
    return out


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def committed_ops_dir() -> Path:
    return REPO_ROOT / "data" / "ops" / "cfb-2026-current-season-proof-20260915"
