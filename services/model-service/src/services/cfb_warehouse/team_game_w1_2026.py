"""CFB 2026 W−1 raw unadjusted team-game metrics (research-only).

First KE-path *build* — not KE Ratings. No opponent adjustment, no SP+
compose change, no KEI, no Edge Board, no CFBD, no NFL.

Eligibility = actually completed ∩ **complete** PBP ∩ ``week < as_of_week``.
Actually completed = STATUS_FINAL OR (has scores AND not live AND not parked).
Live / HALFTIME / END_PERIOD / DELAYED (even with a mid-game score) /
POSTPONED / unfinished are excluded unless independently verified FINAL.
Incomplete PBP for a completed game is fail-closed exclude (401868140 Q2 cut).
DELAYED + score is not a standing include.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

from src.services.cfb_warehouse.current_season_2026 import (
    LIVE_STATUSES,
    PBP_FILENAME,
    SCHEDULE_FILENAME,
    SEASON,
    assert_not_historical_write,
    classify_completion,
    field_support_matrix,
    load_schedule_frame,
    path_convention,
    pbp_game_ids,
    research_dest_dir,
    restore_2026_pbp,
    restore_2026_schedule,
    schedule_game_rows,
    today_as_of,
    write_json,
)
from src.services.cfb_warehouse.delayed_game_verify import (
    DELAYED_GAME_ID,
    audit_pbp_vs_official_final,
    should_exclude_snapshot_game,
)
from src.services.cfb_warehouse.leakage import assert_available_before_kickoff
from src.services.cfb_warehouse.owned_metrics import (
    DEFINITIONS,
    METRIC_VERSION,
    drive_metrics,
    filter_plays_w_minus_1,
    is_scrimmage,
    league_rollups,
    opportunity_summary,
    rolling_form,
    team_game_raw_metrics,
)
from src.services.cfb_warehouse.paths import REPO_ROOT
from src.services.cfb_warehouse.pbp import PBP_CORE_COLUMNS

PIPELINE_VERSION = "cfb-2026-w1-raw-team-game-v1"
PRODUCT_LABEL = "raw unadjusted team-game metrics"
SUCCESS_RATE_LABEL = "EPA_success = EPA>0"
RESEARCH_ONLY = True
OPPONENT_ADJUSTED = False

# Not KE Ratings. Do not rename this product.
FORBIDDEN_PRODUCT_NAMES = ("KE Ratings", "KEI", "Edge Board")

OPS_DIR_NAME = "cfb-2026-w1-raw-team-game-20260915"


def norm_game_id(raw: Any) -> Optional[str]:
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


def _week(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    try:
        if isinstance(raw, float) and raw != raw:
            return None
        value = int(float(raw))
    except (TypeError, ValueError):
        return None
    return value


def _sha256(path: Path, *, chunk: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def default_as_of_week(schedule_rows: Sequence[Mapping[str, Any]], pbp_ids: Set[str]) -> int:
    """Next predictive week after the latest completed∩PBP game."""
    weeks = []
    pbp = {str(g) for g in pbp_ids}
    for row in schedule_rows:
        if not row.get("actually_completed"):
            continue
        gid = norm_game_id(row.get("game_id"))
        if not gid or gid not in pbp:
            continue
        week = _week(row.get("week"))
        if week is not None:
            weeks.append(week)
    return (max(weeks) + 1) if weeks else 1


def exclude_reason(
    row: Mapping[str, Any],
    *,
    has_pbp: bool,
    as_of_week: int,
    unmatched: bool = False,
    pbp_complete: Optional[bool] = None,
) -> str:
    if unmatched:
        return "excluded_pbp_unmatched_schedule"
    gid = norm_game_id(row.get("game_id"))
    if should_exclude_snapshot_game(
        gid,
        status=row.get("status_raw") or row.get("status_token"),
        home_score=row.get("home_score"),
        away_score=row.get("away_score"),
        pbp_complete=pbp_complete,
    ):
        # Audited partial PBP beats parked/final status. DELAYED+score is not enough.
        if pbp_complete is False:
            return "excluded_incomplete_pbp"
        if row.get("actually_completed"):
            return (
                "excluded_incomplete_pbp"
                if has_pbp
                else "excluded_completed_missing_pbp"
            )
        # Snapshot still DELAYED/parked and completeness unknown → fall through.
    if not has_pbp:
        if row.get("actually_completed"):
            return "excluded_completed_missing_pbp"
        if row.get("live"):
            return "excluded_unfinished_live_no_pbp"
        if row.get("parked"):
            return "excluded_unfinished_parked_no_pbp"
        if row.get("scheduled"):
            return "excluded_scheduled_no_pbp"
        return "excluded_no_pbp"
    if row.get("live") or (not row.get("actually_completed") and _normalize_live(row)):
        return "excluded_unfinished_live"
    if not row.get("actually_completed"):
        if row.get("parked"):
            return "excluded_unfinished_parked"
        if row.get("scheduled"):
            return "excluded_scheduled"
        return "excluded_unfinished"
    week = _week(row.get("week"))
    if week is None:
        return "excluded_week_unknown"
    if week >= int(as_of_week):
        return "excluded_week_ge_as_of"
    return "included_eligible_completed_pbp_w_minus_1"


def _normalize_live(row: Mapping[str, Any]) -> bool:
    if row.get("live"):
        return True
    token = str(row.get("status_token") or row.get("status_raw") or "").strip().upper().replace(" ", "_")
    return token in LIVE_STATUSES


def build_eligibility_manifest(
    schedule_rows: Sequence[Mapping[str, Any]],
    pbp_ids: Iterable[str],
    *,
    as_of_week: int,
    as_of: str,
    pbp_sha256: Optional[str] = None,
    schedule_sha256: Optional[str] = None,
    pbp_path: Optional[str] = None,
    schedule_path: Optional[str] = None,
    plays: Optional[Sequence[Mapping[str, Any]]] = None,
    pbp_complete_by_id: Optional[Mapping[str, bool]] = None,
) -> Dict[str, Any]:
    pbp = {str(g) for g in pbp_ids if g}
    by_id = {str(r["game_id"]): r for r in schedule_rows if r.get("game_id")}
    games: List[Dict[str, Any]] = []
    complete_map: Dict[str, bool] = {
        str(k): bool(v) for k, v in (pbp_complete_by_id or {}).items()
    }
    pbp_audit: Optional[Dict[str, Any]] = None
    if plays is not None and DELAYED_GAME_ID not in complete_map:
        pbp_audit = audit_pbp_vs_official_final(plays)
        complete_map[DELAYED_GAME_ID] = bool(pbp_audit.get("complete_through_final"))

    for row in schedule_rows:
        gid = norm_game_id(row.get("game_id"))
        if not gid:
            continue
        has_pbp = gid in pbp
        reason = exclude_reason(
            row,
            has_pbp=has_pbp,
            as_of_week=as_of_week,
            pbp_complete=complete_map.get(gid),
        )
        included = reason.startswith("included_")
        games.append(
            {
                "game_id": gid,
                "week": _week(row.get("week")),
                "status": row.get("status_raw") or row.get("status_token"),
                "status_token": row.get("status_token"),
                "snapshot_bucket": row.get("snapshot_bucket"),
                "actually_completed": bool(row.get("actually_completed")),
                "status_final": bool(row.get("status_final")),
                "has_pbp": has_pbp,
                "included": included,
                "reason": reason,
                "home": row.get("home"),
                "away": row.get("away"),
                "home_score": row.get("home_score"),
                "away_score": row.get("away_score"),
            }
        )

    for gid in sorted(pbp - set(by_id)):
        games.append(
            {
                "game_id": gid,
                "week": None,
                "status": None,
                "status_token": None,
                "snapshot_bucket": "unmatched",
                "actually_completed": False,
                "status_final": False,
                "has_pbp": True,
                "included": False,
                "reason": "excluded_pbp_unmatched_schedule",
                "home": None,
                "away": None,
                "home_score": None,
                "away_score": None,
            }
        )

    eligible = [g for g in games if g["included"]]
    counts: Dict[str, int] = {}
    for game in games:
        key = str(game["reason"])
        counts[key] = counts.get(key, 0) + 1

    return {
        "pipeline_version": PIPELINE_VERSION,
        "product_label": PRODUCT_LABEL,
        "not_ke_ratings": True,
        "research_only": True,
        "opponent_adjusted": False,
        "season": SEASON,
        "as_of": as_of,
        "as_of_week": int(as_of_week),
        "eligibility_rule": (
            "actually_completed ∩ complete PBP ∩ week < as_of_week"
        ),
        "actually_completed_definition": (
            "STATUS_FINAL OR (has scores AND not live AND not parked). "
            "Exclude IN_PROGRESS / HALFTIME / END_PERIOD / DELAYED "
            "(score alone is insufficient) / POSTPONED / unfinished. "
            "Fail-closed: incomplete PBP for a completed game = exclude. "
            "DELAYED + score is not a standing include."
        ),
        "pbp_audit_401868140": pbp_audit,
        "success_rate_label": SUCCESS_RATE_LABEL,
        "pbp_sha256": pbp_sha256,
        "schedule_sha256": schedule_sha256,
        "pbp_path": pbp_path,
        "schedule_path": schedule_path,
        "path_convention": path_convention(as_of),
        "historical_lake_write": False,
        "games": games,
        "eligible_game_ids": [g["game_id"] for g in eligible],
        "eligible_count": len(eligible),
        "excluded_count": len(games) - len(eligible),
        "reason_counts": dict(sorted(counts.items())),
        "cfbd_used": False,
    }


def filter_eligible_plays(
    plays: Sequence[Mapping[str, Any]],
    eligible_ids: Set[str],
    *,
    as_of_week: int,
    season: int = SEASON,
) -> List[Dict[str, Any]]:
    """Keep only eligible completed games and week < W (leakage)."""
    out: List[Dict[str, Any]] = []
    for play in plays:
        if int(_safe_int(play.get("season"), 0)) != int(season):
            continue
        gid = norm_game_id(play.get("game_id"))
        if not gid or gid not in eligible_ids:
            continue
        week = _week(play.get("week"))
        if week is None or week >= int(as_of_week):
            continue
        rec = dict(play)
        rec["game_id"] = gid
        out.append(rec)
    return out


def _safe_int(raw: Any, default: int = 0) -> int:
    week = _week(raw)
    return default if week is None else week


def _opp_summary_for(drives: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return opportunity_summary(drives)


def compose_team_game_table(
    plays: Sequence[Mapping[str, Any]],
    *,
    schedule_by_id: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """One row per team-game: offense + defense allowed + drive/opportunity."""
    offense_rows = team_game_raw_metrics(plays)
    drives = drive_metrics(plays)
    drives_by_off: Dict[tuple, List[Mapping[str, Any]]] = {}
    for drive in drives:
        key = (str(drive.get("game_id")), str(drive.get("offense")))
        drives_by_off.setdefault(key, []).append(drive)

    by_game_team: Dict[tuple, Dict[str, Any]] = {}
    for row in offense_rows:
        gid = norm_game_id(row.get("game_id")) or str(row.get("game_id"))
        team = str(row.get("offense") or "")
        by_game_team[(gid, team)] = row

    table: List[Dict[str, Any]] = []
    for (gid, team), off in by_game_team.items():
        opp = str(off.get("defense") or "")
        allowed = by_game_team.get((gid, opp), {})
        opp_block = _opp_summary_for(drives_by_off.get((gid, team), []))
        sched = (schedule_by_id or {}).get(gid, {})
        table.append(
            {
                "season": off.get("season"),
                "week": off.get("week"),
                "game_id": gid,
                "team": team,
                "opponent": opp,
                "home": sched.get("home"),
                "away": sched.get("away"),
                "off_n_plays": off.get("n_plays"),
                "off_success_rate": off.get("success_rate"),
                "off_success_rate_label": SUCCESS_RATE_LABEL,
                "off_standard_success_rate": off.get("standard_success_rate"),
                "off_epa_per_play": off.get("epa_per_play"),
                "off_explosive_rate": off.get("explosive_rate"),
                "off_pass_explosive_rate": off.get("pass_explosive_rate"),
                "off_rush_explosive_rate": off.get("rush_explosive_rate"),
                "off_early_success_rate": off.get("early_success_rate"),
                "off_early_epa_per_play": off.get("early_epa_per_play"),
                "off_standard_down_success_rate": off.get("standard_down_success_rate"),
                "off_standard_down_epa_per_play": off.get("standard_down_epa_per_play"),
                "off_passing_down_success_rate": off.get("passing_down_success_rate"),
                "off_passing_down_epa_per_play": off.get("passing_down_epa_per_play"),
                "off_competitive_plays": off.get("competitive_plays"),
                "pace_plays": off.get("n_plays"),
                "competitive_pace_plays": off.get("competitive_plays"),
                "def_n_plays": allowed.get("n_plays"),
                "def_success_rate": allowed.get("success_rate"),
                "def_standard_success_rate": allowed.get("standard_success_rate"),
                "def_epa_per_play": allowed.get("epa_per_play"),
                "def_explosive_rate": allowed.get("explosive_rate"),
                "def_pass_explosive_rate": allowed.get("pass_explosive_rate"),
                "def_rush_explosive_rate": allowed.get("rush_explosive_rate"),
                "def_early_success_rate": allowed.get("early_success_rate"),
                "def_early_epa_per_play": allowed.get("early_epa_per_play"),
                "def_standard_down_success_rate": allowed.get("standard_down_success_rate"),
                "def_standard_down_epa_per_play": allowed.get("standard_down_epa_per_play"),
                "def_passing_down_success_rate": allowed.get("passing_down_success_rate"),
                "def_passing_down_epa_per_play": allowed.get("passing_down_epa_per_play"),
                "n_drives": opp_block.get("drives"),
                "scoring_opportunities": opp_block.get("scoring_opportunities"),
                "opportunity_rate": opp_block.get("opportunity_rate"),
                "points_per_opportunity": opp_block.get("points_per_opportunity"),
                "finish_rate": opp_block.get("finish_rate"),
                "mean_start_yards_to_endzone": opp_block.get("mean_start_yards_to_endzone"),
                "mean_drive_epa_sum": opp_block.get("mean_drive_epa_sum"),
                "opponent_adjusted": False,
                "research_only": True,
                "product_label": PRODUCT_LABEL,
                "metric_version": METRIC_VERSION,
                "pipeline_version": PIPELINE_VERSION,
            }
        )
    table.sort(key=lambda r: (int(r.get("week") or 0), str(r.get("game_id")), str(r.get("team"))))
    return table


def core31_and_epa_null_rates(plays: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    n = len(plays)
    present = [c for c in PBP_CORE_COLUMNS if any(c in p for p in plays[:1]) or any(c in p for p in plays)]
    # Presence: column appears as a key on at least one play.
    keys: Set[str] = set()
    for play in plays:
        keys.update(str(k) for k in play.keys())
    present = [c for c in PBP_CORE_COLUMNS if c in keys]
    absent = [c for c in PBP_CORE_COLUMNS if c not in keys]
    null_rates: Dict[str, Optional[float]] = {}
    if n == 0:
        for col in PBP_CORE_COLUMNS:
            null_rates[col] = None
    else:
        for col in PBP_CORE_COLUMNS:
            if col not in keys:
                null_rates[col] = None
                continue
            missing = 0
            for play in plays:
                val = play.get(col)
                if val is None or val == "":
                    missing += 1
                    continue
                if isinstance(val, float) and not math.isfinite(val):
                    missing += 1
            null_rates[col] = round(missing / n, 6)

    scrim = [p for p in plays if is_scrimmage(p)]
    epa_missing = 0
    for play in scrim:
        val = play.get("EPA")
        if val is None or val == "":
            epa_missing += 1
            continue
        try:
            if not math.isfinite(float(val)):
                epa_missing += 1
        except (TypeError, ValueError):
            epa_missing += 1
    return {
        "plays": n,
        "scrimmage_plays": len(scrim),
        "core31_present": present,
        "core31_absent": absent,
        "core31_present_count": len(present),
        "core31_null_rates": null_rates,
        "epa_null_rate_scrimmage": (
            round(epa_missing / len(scrim), 6) if scrim else None
        ),
        "epa_null_scrimmage_n": epa_missing,
    }


def validate_outputs(
    table: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    *,
    as_of_week: int,
    field_stats: Mapping[str, Any],
    pbp_sha256: Optional[str],
    schedule_sha256: Optional[str],
) -> Dict[str, Any]:
    eligible_ids = {str(g) for g in manifest.get("eligible_game_ids") or []}
    table_ids = {str(r.get("game_id")) for r in table}
    unfinished = [
        r
        for r in table
        if str(r.get("game_id")) not in eligible_ids
    ]
    weeks = [_week(r.get("week")) for r in table]
    weeks_ok = [w for w in weeks if w is not None]
    leakage_ok = all(w < int(as_of_week) for w in weeks_ok) and all(w is not None for w in weeks)
    if weeks_ok:
        try:
            assert_available_before_kickoff(
                available_at=None,
                feature_week=max(weeks_ok),
                game_week=int(as_of_week),
                feature_name="team_game_w1_2026",
            )
            kickoff_week_ok = True
            kickoff_week_error = None
        except ValueError as exc:
            kickoff_week_ok = False
            kickoff_week_error = str(exc)
    else:
        kickoff_week_ok = True
        kickoff_week_error = None

    adj_flags = [bool(r.get("opponent_adjusted")) for r in table]
    labels = {str(r.get("product_label")) for r in table}
    forbidden = [name for name in FORBIDDEN_PRODUCT_NAMES if any(name in (lab or "") for lab in labels)]

    included_count = int(manifest.get("eligible_count") or 0)
    unique_table_games = len(table_ids)
    included_matches = unique_table_games == included_count
    require_sha = bool(manifest.get("pbp_path") and manifest.get("schedule_path"))
    # Empty eligible is allowed (honest zero) — counts must still match.
    checks = {
        "zero_unfinished_rows": len(unfinished) == 0,
        "included_count_equals_manifest_eligible": included_matches,
        "leakage_week_lt_as_of": leakage_ok,
        "kickoff_week_contract": kickoff_week_ok,
        "opponent_adjusted_false_all_rows": (not any(adj_flags))
        or (not table and included_count == 0),
        "input_sha_recorded": (bool(pbp_sha256) and bool(schedule_sha256))
        if require_sha
        else True,
        "no_historical_lake_write": manifest.get("historical_lake_write") is False,
        "not_labeled_ke_ratings": len(forbidden) == 0,
        "cfbd_unused": manifest.get("cfbd_used") is False,
    }
    # If no rows (honest empty), opponent_adjusted check still passes.
    if not table and included_count == 0:
        checks["opponent_adjusted_false_all_rows"] = True

    passed = all(checks.values())
    return {
        "passed": passed,
        "checks": checks,
        "unfinished_row_count": len(unfinished),
        "unfinished_game_ids": sorted({str(r.get("game_id")) for r in unfinished})[:40],
        "table_rows": len(table),
        "table_games": unique_table_games,
        "manifest_eligible_count": included_count,
        "max_week": max(weeks_ok) if weeks_ok else None,
        "as_of_week": int(as_of_week),
        "kickoff_week_error": kickoff_week_error,
        "field_stats": field_stats,
        "pbp_sha256": pbp_sha256,
        "schedule_sha256": schedule_sha256,
        "opponent_adjusted": False,
        "product_label": PRODUCT_LABEL,
        "success_rate_label": SUCCESS_RATE_LABEL,
    }


def _stub_team_game(
    *,
    game_id: str,
    team: str,
    opponent: str,
    week: Optional[int],
    sched: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "season": SEASON,
        "week": week,
        "game_id": game_id,
        "team": team,
        "opponent": opponent,
        "home": sched.get("home"),
        "away": sched.get("away"),
        "off_n_plays": 0,
        "off_success_rate": None,
        "off_success_rate_label": SUCCESS_RATE_LABEL,
        "off_standard_success_rate": None,
        "off_epa_per_play": None,
        "off_explosive_rate": None,
        "off_pass_explosive_rate": None,
        "off_rush_explosive_rate": None,
        "off_early_success_rate": None,
        "off_early_epa_per_play": None,
        "off_standard_down_success_rate": None,
        "off_standard_down_epa_per_play": None,
        "off_passing_down_success_rate": None,
        "off_passing_down_epa_per_play": None,
        "off_competitive_plays": 0,
        "pace_plays": 0,
        "competitive_pace_plays": 0,
        "def_n_plays": None,
        "def_success_rate": None,
        "def_standard_success_rate": None,
        "def_epa_per_play": None,
        "def_explosive_rate": None,
        "def_pass_explosive_rate": None,
        "def_rush_explosive_rate": None,
        "def_early_success_rate": None,
        "def_early_epa_per_play": None,
        "def_standard_down_success_rate": None,
        "def_standard_down_epa_per_play": None,
        "def_passing_down_success_rate": None,
        "def_passing_down_epa_per_play": None,
        "n_drives": 0,
        "scoring_opportunities": 0,
        "opportunity_rate": None,
        "points_per_opportunity": None,
        "finish_rate": None,
        "mean_start_yards_to_endzone": None,
        "mean_drive_epa_sum": None,
        "opponent_adjusted": False,
        "research_only": True,
        "product_label": PRODUCT_LABEL,
        "metric_version": METRIC_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "stub_no_scrimmage": True,
    }


def _ensure_eligible_games_present(
    table: List[Dict[str, Any]],
    eligible_ids: Set[str],
    sched_by_id: Mapping[str, Mapping[str, Any]],
    _as_of_week: int,
) -> List[Dict[str, Any]]:
    present = {str(r.get("game_id")) for r in table}
    out = list(table)
    for gid in sorted(eligible_ids):
        if gid in present:
            continue
        sched = sched_by_id.get(gid, {})
        week = _week(sched.get("week"))
        home = str(sched.get("home") or "unknown_home")
        away = str(sched.get("away") or "unknown_away")
        out.append(_stub_team_game(game_id=gid, team=home, opponent=away, week=week, sched=sched))
        out.append(_stub_team_game(game_id=gid, team=away, opponent=home, week=week, sched=sched))
    out.sort(key=lambda r: (int(r.get("week") or 0), str(r.get("game_id")), str(r.get("team"))))
    return out


def load_pbp_records(path: Path) -> List[Dict[str, Any]]:
    import pandas as pd

    df = pd.read_parquet(path)
    records = df.to_dict(orient="records")
    for rec in records:
        gid = norm_game_id(rec.get("game_id"))
        if gid:
            rec["game_id"] = gid
    return records


def committed_ops_dir() -> Path:
    return REPO_ROOT / "data" / "ops" / OPS_DIR_NAME


def run_research_pipeline(
    *,
    as_of: Optional[str] = None,
    as_of_week: Optional[int] = None,
    dest_dir: Optional[Path] = None,
    allow_fetch: bool = True,
    plays: Optional[Sequence[Mapping[str, Any]]] = None,
    schedule_rows: Optional[Sequence[Mapping[str, Any]]] = None,
    pbp_path: Optional[Path] = None,
    schedule_path: Optional[Path] = None,
    write_artifacts: bool = True,
    commit_ops: bool = False,
) -> Dict[str, Any]:
    """Build eligibility + raw team-game metrics for completed 2026 games."""
    stamp = as_of or today_as_of()
    dest = Path(dest_dir) if dest_dir is not None else research_dest_dir(stamp)
    dest.mkdir(parents=True, exist_ok=True)
    assert_not_historical_write(dest)

    sha_pbp: Optional[str] = None
    sha_sched: Optional[str] = None
    used_pbp_path: Optional[Path] = Path(pbp_path) if pbp_path else None
    used_sched_path: Optional[Path] = Path(schedule_path) if schedule_path else None

    if plays is None or schedule_rows is None:
        if not allow_fetch and (used_pbp_path is None or used_sched_path is None):
            raise FileNotFoundError("2026 PBP/schedule missing and fetch disabled")
        if used_pbp_path is None:
            used_pbp_path = restore_2026_pbp(dest_dir=dest)
        if used_sched_path is None:
            used_sched_path = restore_2026_schedule(dest_dir=dest, force=True)
        assert_not_historical_write(used_pbp_path)
        assert_not_historical_write(used_sched_path)
        sha_pbp = _sha256(used_pbp_path)
        sha_sched = _sha256(used_sched_path)
        if plays is None:
            plays = load_pbp_records(used_pbp_path)
        if schedule_rows is None:
            schedule_rows = schedule_game_rows(load_schedule_frame(used_sched_path))
    else:
        if used_pbp_path and used_pbp_path.exists():
            sha_pbp = _sha256(used_pbp_path)
        if used_sched_path and used_sched_path.exists():
            sha_sched = _sha256(used_sched_path)

    pbp_ids = {norm_game_id(p.get("game_id")) for p in plays}
    pbp_ids.discard(None)
    pbp_ids_str = {str(g) for g in pbp_ids}

    # Prefer ids from the parquet frame when we loaded one (handles non-record path).
    if used_pbp_path and used_pbp_path.exists() and plays is not None:
        try:
            import pandas as pd

            pbp_ids_str = pbp_game_ids(pd.read_parquet(used_pbp_path))
        except Exception:  # noqa: BLE001 — records already have ids
            pass

    week_w = int(as_of_week) if as_of_week is not None else default_as_of_week(
        schedule_rows, pbp_ids_str
    )
    manifest = build_eligibility_manifest(
        schedule_rows,
        pbp_ids_str,
        as_of_week=week_w,
        as_of=stamp,
        pbp_sha256=sha_pbp,
        schedule_sha256=sha_sched,
        pbp_path=str(used_pbp_path) if used_pbp_path else None,
        schedule_path=str(used_sched_path) if used_sched_path else None,
        plays=plays,
    )
    eligible_ids = set(manifest["eligible_game_ids"])
    kept = filter_eligible_plays(plays, eligible_ids, as_of_week=week_w)
    # Extra leakage belt: same helper as #555 rolling form.
    kept = filter_plays_w_minus_1(kept, season=SEASON, as_of_week=week_w)
    for play in kept:
        gid = norm_game_id(play.get("game_id"))
        if gid:
            play["game_id"] = gid

    sched_by_id = {str(r["game_id"]): r for r in schedule_rows if r.get("game_id")}
    table = compose_team_game_table(kept, schedule_by_id=sched_by_id)
    table = _ensure_eligible_games_present(table, eligible_ids, sched_by_id, week_w)
    field_stats = core31_and_epa_null_rates(kept)
    try:
        import pandas as pd

        if kept:
            field_stats["field_support"] = field_support_matrix(pd.DataFrame(kept))
    except Exception:  # noqa: BLE001 — pandas optional
        pass

    form = rolling_form(kept, season=SEASON, as_of_week=week_w)
    for row in form:
        assert row.get("opponent_adjusted") is False
        if row.get("feature_week"):
            assert_available_before_kickoff(
                available_at=None,
                feature_week=int(row["feature_week"]),
                game_week=week_w,
                feature_name="w1_form_slice",
            )

    validation = validate_outputs(
        table,
        manifest,
        as_of_week=week_w,
        field_stats=field_stats,
        pbp_sha256=sha_pbp,
        schedule_sha256=sha_sched,
    )
    rollups = league_rollups(
        [
            {
                "success_rate": r.get("off_success_rate"),
                "standard_success_rate": r.get("off_standard_success_rate"),
                "epa_per_play": r.get("off_epa_per_play"),
                "explosive_rate": r.get("off_explosive_rate"),
                "pass_explosive_rate": r.get("off_pass_explosive_rate"),
                "rush_explosive_rate": r.get("off_rush_explosive_rate"),
                "early_success_rate": r.get("off_early_success_rate"),
                "standard_down_success_rate": r.get("off_standard_down_success_rate"),
                "passing_down_success_rate": r.get("off_passing_down_success_rate"),
            }
            for r in table
        ]
    )
    rollups["team_games"] = len(table)
    rollups["games"] = len({r["game_id"] for r in table})
    rollups["success_rate_label"] = SUCCESS_RATE_LABEL
    rollups["product_label"] = PRODUCT_LABEL

    summary = {
        "pipeline_version": PIPELINE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "product_label": PRODUCT_LABEL,
        "not_ke_ratings": True,
        "research_only": True,
        "opponent_adjusted": False,
        "season": SEASON,
        "as_of": stamp,
        "as_of_week": week_w,
        "definitions": {
            "success_rate": DEFINITIONS["success_rate"],
            "standard_success_rate": DEFINITIONS["standard_success_rate"],
            "epa_per_play": DEFINITIONS["epa_per_play"],
            "pace": DEFINITIONS["pace_plays_per_offense_game"],
            "true_pace_competitive": DEFINITIONS["true_pace_competitive"],
            "explosive_rate": DEFINITIONS["explosive_rate"],
            "scoring_opportunity": DEFINITIONS["scoring_opportunity"],
            "points_per_opportunity": DEFINITIONS["points_per_opportunity"],
            "field_position": DEFINITIONS["field_position"],
            "rolling_form": DEFINITIONS["rolling_form"],
        },
        "path_convention": path_convention(stamp),
        "vm_dest": str(dest),
        "hd_target": path_convention(stamp)["current_season_hd_target"],
        "eligible_count": manifest["eligible_count"],
        "table_rows": len(table),
        "table_games": len({r["game_id"] for r in table}),
        "form_teams": len(form),
        "league_rollups": rollups,
        "validation": validation,
        "reason_counts": manifest["reason_counts"],
        "cfbd_used": False,
        "historical_inventory_rewritten": False,
        "sp_plus_compose_changed": False,
        "kei_or_edge_board": False,
    }

    if write_artifacts:
        write_json(dest / "eligibility_manifest.json", manifest)
        write_json(dest / "team_game_raw_unadjusted.json", table)
        write_json(dest / "w1_form_slice.json", form)
        write_json(dest / "validation.json", validation)
        write_json(dest / "summary.json", summary)
        try:
            import pandas as pd

            pd.DataFrame(table).to_parquet(dest / "team_game_raw_unadjusted.parquet", index=False)
        except Exception:  # noqa: BLE001
            pass
        assert_not_historical_write(dest / "eligibility_manifest.json")

    if commit_ops:
        ops = committed_ops_dir()
        ops.mkdir(parents=True, exist_ok=True)
        write_json(
            ops / "validation.json",
            {
                **validation,
                "generated_at": summary["generated_at"],
                "as_of": stamp,
                "as_of_week": week_w,
                "path_convention": summary["path_convention"],
                "reason_counts": manifest["reason_counts"],
                "eligible_game_ids": manifest["eligible_game_ids"],
            },
        )
        write_json(ops / "eligibility_manifest.json", manifest)
        write_json(ops / "league_rollups.json", rollups)
        write_ops_readme(ops / "README.md", summary)

    return {
        "summary": summary,
        "manifest": manifest,
        "table": table,
        "form": form,
        "validation": validation,
        "dest": str(dest),
    }


def write_ops_readme(path: Path, summary: Mapping[str, Any]) -> None:
    val = summary.get("validation") or {}
    checks = val.get("checks") or {}
    lines = [
        "# CFB 2026 W−1 raw unadjusted team-game metrics",
        "",
        "Research-only. **Not KE Ratings.** `opponent_adjusted=false`.",
        "",
        f"- as_of: `{summary.get('as_of')}`",
        f"- as_of_week: `{summary.get('as_of_week')}`",
        f"- eligible games: `{summary.get('eligible_count')}`",
        f"- table rows: `{summary.get('table_rows')}`",
        f"- validation passed: `{val.get('passed')}`",
        "",
        "Checks:",
    ]
    for key, ok in checks.items():
        lines.append(f"- `{key}`: {'PASS' if ok else 'FAIL'}")
    lines.extend(
        [
            "",
            "Bulk parquet lives in the gitignored as_of folder.",
            "HD target: `/Volumes/KosEdgeData/raw/cfb/pbp_current/as_of_YYYYMMDD/`.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
