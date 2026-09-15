"""NFL #564 remediation — packaged EPA authority + W1 outcomes coverage.

Does not change the scoring equation. Does not flip Coming soon.
production_promote stays false.

Used by:
- readiness (sample_size from ingested outcomes when the quality snapshot is empty)
- board week (advance past completed W1)
- ad-hoc ``POST /nfl/simulations/{id}`` (EPA-or-refuse; never persist ESPN W-L)
- W2+ remat with personnel/injury overlays forced off
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_regression_diagnose import (
    LOCKED_SCORING,
    classify_strength_source,
    decompose_matchup,
    load_packaged_epa_priors,
    locked_scoring_snapshot,
    looks_like_week1_record_bucket,
    replay_focus_matchups,
)

NFL_564_REMEDIATION = "nfl-564-remediation-20260915"
PRODUCTION_PROMOTE = False
OVERLAYS_OFF_LABEL = "personnel_injury_overlays_off"

# ESPN scoreboard captured 2026-09-15 for REG 2026 Week 1 (all Final).
NFL_2026_W1_OUTCOMES: Tuple[Dict[str, Any], ...] = (
    {"key": "NE@SEA", "week": 1, "away": "NE", "home": "SEA", "away_score": 10, "home_score": 13, "game_date": "2026-09-09"},
    {"key": "SF@LAR", "week": 1, "away": "SF", "home": "LAR", "away_score": 27, "home_score": 7, "game_date": "2026-09-10"},
    {"key": "TB@CIN", "week": 1, "away": "TB", "home": "CIN", "away_score": 27, "home_score": 33, "game_date": "2026-09-13"},
    {"key": "NO@DET", "week": 1, "away": "NO", "home": "DET", "away_score": 30, "home_score": 31, "game_date": "2026-09-13"},
    {"key": "NYJ@TEN", "week": 1, "away": "NYJ", "home": "TEN", "away_score": 23, "home_score": 10, "game_date": "2026-09-13"},
    {"key": "BAL@IND", "week": 1, "away": "BAL", "home": "IND", "away_score": 41, "home_score": 23, "game_date": "2026-09-13"},
    {"key": "ATL@PIT", "week": 1, "away": "ATL", "home": "PIT", "away_score": 13, "home_score": 20, "game_date": "2026-09-13"},
    {"key": "CHI@CAR", "week": 1, "away": "CHI", "home": "CAR", "away_score": 59, "home_score": 37, "game_date": "2026-09-13"},
    {"key": "CLE@JAX", "week": 1, "away": "CLE", "home": "JAX", "away_score": 10, "home_score": 34, "game_date": "2026-09-13"},
    {"key": "BUF@HOU", "week": 1, "away": "BUF", "home": "HOU", "away_score": 36, "home_score": 31, "game_date": "2026-09-13"},
    {"key": "MIA@LV", "week": 1, "away": "MIA", "home": "LV", "away_score": 13, "home_score": 27, "game_date": "2026-09-13"},
    {"key": "GB@MIN", "week": 1, "away": "GB", "home": "MIN", "away_score": 22, "home_score": 39, "game_date": "2026-09-13"},
    {"key": "WSH@PHI", "week": 1, "away": "WSH", "home": "PHI", "away_score": 22, "home_score": 24, "game_date": "2026-09-13"},
    {"key": "ARI@LAC", "week": 1, "away": "ARI", "home": "LAC", "away_score": 26, "home_score": 14, "game_date": "2026-09-13"},
    {"key": "DAL@NYG", "week": 1, "away": "DAL", "home": "NYG", "away_score": 20, "home_score": 28, "game_date": "2026-09-13"},
    {"key": "DEN@KC", "week": 1, "away": "DEN", "home": "KC", "away_score": 10, "home_score": 31, "game_date": "2026-09-14"},
)

# ESPN scoreboard captured 2026-09-15 — Week 2 still scheduled.
NFL_2026_W2_SLATE: Tuple[Dict[str, Any], ...] = (
    {"key": "DET@BUF", "week": 2, "away": "DET", "home": "BUF", "game_date": "2026-09-17"},
    {"key": "CAR@ATL", "week": 2, "away": "CAR", "home": "ATL", "game_date": "2026-09-20"},
    {"key": "MIN@CHI", "week": 2, "away": "MIN", "home": "CHI", "game_date": "2026-09-20"},
    {"key": "PHI@TEN", "week": 2, "away": "PHI", "home": "TEN", "game_date": "2026-09-20"},
    {"key": "PIT@NE", "week": 2, "away": "PIT", "home": "NE", "game_date": "2026-09-20"},
    {"key": "GB@NYJ", "week": 2, "away": "GB", "home": "NYJ", "game_date": "2026-09-20"},
    {"key": "CLE@TB", "week": 2, "away": "CLE", "home": "TB", "game_date": "2026-09-20"},
    {"key": "NO@BAL", "week": 2, "away": "NO", "home": "BAL", "game_date": "2026-09-20"},
    {"key": "CIN@HOU", "week": 2, "away": "CIN", "home": "HOU", "game_date": "2026-09-20"},
    {"key": "JAX@DEN", "week": 2, "away": "JAX", "home": "DEN", "game_date": "2026-09-20"},
    {"key": "LV@LAC", "week": 2, "away": "LV", "home": "LAC", "game_date": "2026-09-20"},
    {"key": "WSH@DAL", "week": 2, "away": "WSH", "home": "DAL", "game_date": "2026-09-20"},
    {"key": "SEA@ARI", "week": 2, "away": "SEA", "home": "ARI", "game_date": "2026-09-20"},
    {"key": "MIA@SF", "week": 2, "away": "MIA", "home": "SF", "game_date": "2026-09-20"},
    {"key": "IND@KC", "week": 2, "away": "IND", "home": "KC", "game_date": "2026-09-20"},
    {"key": "NYG@LAR", "week": 2, "away": "NYG", "home": "LAR", "game_date": "2026-09-21"},
)

INTEGRITY_FOCUS_KEYS = ("DET@BUF", "CAR@ATL", "ATL@PIT", "CHI@CAR")


class NflWlPersistRefused(Exception):
    """Ad-hoc sim must not persist the ESPN W-L two-bucket book."""

    def __init__(self, reason: str, detail: Optional[Dict[str, Any]] = None) -> None:
        self.reason = str(reason)
        self.detail = dict(detail or {})
        super().__init__(self.reason)


@dataclass(frozen=True)
class ResolvedAdhocStrength:
    offense_index_home: float
    offense_index_away: float
    defense_index_home: float
    defense_index_away: float
    source: str
    overlays_off: bool
    refused_win_loss: bool


def normalize_nfl_abbr(raw: Any) -> str:
    team = str(raw or "").strip().upper()
    if team == "LA":
        return "LAR"
    if team == "WAS":
        return "WSH"
    return team


def packaged_epa_row(
    priors: Mapping[str, Mapping[str, float]],
    abbr: Any,
) -> Optional[Dict[str, float]]:
    team = normalize_nfl_abbr(abbr)
    row = priors.get(team)
    if row is None and team == "LAR":
        row = priors.get("LA")
    if row is None and team == "WSH":
        row = priors.get("WAS")
    if row is None and team == "WAS":
        row = priors.get("WSH")
    if not isinstance(row, Mapping):
        return None
    try:
        return {
            "offense_index": float(row["offense_index"]),
            "defense_index": float(row["defense_index"]),
        }
    except (KeyError, TypeError, ValueError):
        return None


def context_looks_like_win_loss(
    *,
    offense_index: Optional[float],
    defense_index: Optional[float],
    record_summary: Optional[str],
) -> bool:
    if offense_index is None or defense_index is None or not record_summary:
        return False
    return looks_like_week1_record_bucket(
        offense_index=float(offense_index),
        defense_index=float(defense_index),
        record_summary=str(record_summary),
    )


def overlays_must_stay_off(*, completed_reg_season: int, force_overlays_off: bool) -> bool:
    """Injury / personnel / tendency stay off when forced or season is too early."""
    return bool(force_overlays_off) or int(completed_reg_season or 0) < 3


def resolve_adhoc_simulation_strength(
    *,
    home_abbr: str,
    away_abbr: str,
    context_offense_home: Optional[float],
    context_offense_away: Optional[float],
    context_defense_home: Optional[float],
    context_defense_away: Optional[float],
    home_record_summary: Optional[str] = None,
    away_record_summary: Optional[str] = None,
    priors: Optional[Mapping[str, Mapping[str, float]]] = None,
    resolve_indices=None,
) -> ResolvedAdhocStrength:
    """Packaged EPA or refuse. Never return ESPN W-L indices for persist."""
    book = dict(priors or load_packaged_epa_priors())
    home_epa = packaged_epa_row(book, home_abbr)
    away_epa = packaged_epa_row(book, away_abbr)
    if home_epa is None or away_epa is None:
        raise NflWlPersistRefused(
            "packaged_epa_unavailable",
            {
                "home_abbr": normalize_nfl_abbr(home_abbr),
                "away_abbr": normalize_nfl_abbr(away_abbr),
                "home_epa": home_epa is not None,
                "away_epa": away_epa is not None,
            },
        )

    context_is_wl = context_looks_like_win_loss(
        offense_index=context_offense_home,
        defense_index=context_defense_home,
        record_summary=home_record_summary,
    ) or context_looks_like_win_loss(
        offense_index=context_offense_away,
        defense_index=context_defense_away,
        record_summary=away_record_summary,
    )

    if resolve_indices is None:
        from src.tasks import _resolve_team_strength_indices

        resolve_indices = _resolve_team_strength_indices

    offense_home, offense_away, defense_home, defense_away = resolve_indices(
        base_offense_home=float(context_offense_home if context_offense_home is not None else 1.0),
        base_offense_away=float(context_offense_away if context_offense_away is not None else 1.0),
        base_defense_home=float(context_defense_home if context_defense_home is not None else 1.0),
        base_defense_away=float(context_defense_away if context_defense_away is not None else 1.0),
        home_prior=home_epa,
        away_prior=away_epa,
    )

    resolved_is_wl = False
    if home_record_summary:
        resolved_is_wl = resolved_is_wl or looks_like_week1_record_bucket(
            offense_index=float(offense_home),
            defense_index=float(defense_home),
            record_summary=str(home_record_summary),
        )
    if away_record_summary:
        resolved_is_wl = resolved_is_wl or looks_like_week1_record_bucket(
            offense_index=float(offense_away),
            defense_index=float(defense_away),
            record_summary=str(away_record_summary),
        )
    if resolved_is_wl and context_is_wl:
        raise NflWlPersistRefused(
            "espn_win_loss_persist_refused",
            {
                "home_abbr": normalize_nfl_abbr(home_abbr),
                "away_abbr": normalize_nfl_abbr(away_abbr),
                "note": "resolved indices still match the ESPN W-L two-bucket; refuse persist",
            },
        )

    return ResolvedAdhocStrength(
        offense_index_home=float(offense_home),
        offense_index_away=float(offense_away),
        defense_index_home=float(defense_home),
        defense_index_away=float(defense_away),
        source="packaged_epa_prior",
        overlays_off=True,
        refused_win_loss=context_is_wl,
    )


def slate_row_is_completed(row: Mapping[str, Any]) -> bool:
    home = row.get("home_score")
    away = row.get("away_score")
    has_outcome = bool(row.get("has_outcome"))
    if has_outcome:
        return True
    if home is None or away is None or home == "" or away == "":
        return False
    try:
        int(home)
        int(away)
    except (TypeError, ValueError):
        return False
    return True


def resolve_current_nfl_board_week_from_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    today: Optional[date] = None,
) -> int:
    """Advance past weeks whose REG games are completed (scores or outcomes).

    Date-window lookback alone stuck ``current_week`` at 1 after W1 Monday.
    """
    del today  # reserved for callers that already filtered; unused on purpose
    unfinished: List[Tuple[date, int]] = []
    finished_weeks: List[int] = []
    for raw in rows:
        week_raw = raw.get("week")
        try:
            week = int(week_raw)
        except (TypeError, ValueError):
            continue
        if week < 1 or week > 18:
            continue
        game_date = _coerce_date(raw.get("game_date")) or date.min
        if slate_row_is_completed(raw):
            finished_weeks.append(week)
        else:
            unfinished.append((game_date, week))
    if unfinished:
        unfinished.sort(key=lambda item: (item[0], item[1]))
        return int(unfinished[0][1])
    if finished_weeks:
        return min(18, max(finished_weeks) + 1)
    return 1


def merge_readiness_with_outcomes_coverage(
    *,
    snapshot_sample_size: int,
    snapshot_last_game_date: Optional[date],
    snapshot_calendar_days: int,
    outcomes_sample_size: int,
    outcomes_last_game_date: Optional[date],
    outcomes_calendar_days: int,
) -> Dict[str, Any]:
    """Fold ingested outcomes into readiness when the quality snapshot is empty."""
    snap_n = int(snapshot_sample_size or 0)
    out_n = int(outcomes_sample_size or 0)
    if snap_n <= 0 and out_n > 0:
        return {
            "sample_size": out_n,
            "last_game_date": outcomes_last_game_date,
            "calendar_days_covered": max(int(snapshot_calendar_days or 0), int(outcomes_calendar_days or 0)),
            "snapshot_sample_size": snap_n,
            "outcomes_sample_size": out_n,
            "coverage_source": "nfl_market_outcomes",
        }
    return {
        "sample_size": snap_n,
        "last_game_date": snapshot_last_game_date,
        "calendar_days_covered": int(snapshot_calendar_days or 0),
        "snapshot_sample_size": snap_n,
        "outcomes_sample_size": out_n,
        "coverage_source": "quality_snapshot",
    }


def week1_outcomes_coverage_fixture() -> Dict[str, Any]:
    dates = sorted({str(row["game_date"]) for row in NFL_2026_W1_OUTCOMES})
    return {
        "season": 2026,
        "week": 1,
        "sample_size": len(NFL_2026_W1_OUTCOMES),
        "calendar_days_covered": len(dates),
        "last_game_date": dates[-1] if dates else None,
        "games": [dict(row) for row in NFL_2026_W1_OUTCOMES],
        "before_ingest_sample_size": 0,
        "after_ingest_sample_size": len(NFL_2026_W1_OUTCOMES),
    }


def rematerialize_week_epa_overlays_off(
    slate: Optional[Iterable[Mapping[str, Any]]] = None,
    *,
    priors: Optional[Mapping[str, Mapping[str, float]]] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Research remat: packaged EPA only, personnel/injury off. No production write."""
    book = dict(priors or load_packaged_epa_priors())
    games: List[Dict[str, Any]] = []
    for item in slate or NFL_2026_W2_SLATE:
        home = normalize_nfl_abbr(item["home"])
        away = normalize_nfl_abbr(item["away"])
        home_epa = packaged_epa_row(book, home)
        away_epa = packaged_epa_row(book, away)
        if home_epa is None or away_epa is None:
            raise KeyError(f"missing packaged EPA prior for {away}@{home}")
        row = decompose_matchup(
            home=home,
            away=away,
            offense_index_home=home_epa["offense_index"],
            offense_index_away=away_epa["offense_index"],
            defense_index_home=home_epa["defense_index"],
            defense_index_away=away_epa["defense_index"],
            strength_source="packaged_epa_prior",
        )
        comps = row.get("components") or {}
        games.append(
            {
                "key": item.get("key") or f"{away}@{home}",
                "week": item.get("week"),
                "game_date": item.get("game_date"),
                "spread_home": row.get("spread_home"),
                "predicted_total": row.get("predicted_total"),
                "expected_home_points": row.get("expected_home_points"),
                "expected_away_points": row.get("expected_away_points"),
                "offense_index_home": row.get("offense_index_home"),
                "offense_index_away": row.get("offense_index_away"),
                "defense_index_home": row.get("defense_index_home"),
                "defense_index_away": row.get("defense_index_away"),
                "strength_source": "packaged_epa_prior",
                "overlays": {
                    "personnel_efficiency": False,
                    "injuries_depth": False,
                    "personnel_margin_points": float((comps.get("personnel_efficiency") or {}).get("margin_points") or 0.0),
                    "injuries_margin_points": float((comps.get("injuries_depth") or {}).get("margin_points") or 0.0),
                },
            }
        )
    payload = {
        "run_id": run_id or NFL_564_REMEDIATION,
        "production_promote": PRODUCTION_PROMOTE,
        "strength_source": "packaged_epa_prior",
        "overlays_off": True,
        "personnel_overlay": False,
        "injury_overlay": False,
        "locked_scoring": LOCKED_SCORING,
        "live_scoring": locked_scoring_snapshot(),
        "game_count": len(games),
        "games": games,
    }
    payload["checksum_sha256"] = sha256_canonical(payload)
    return payload


def build_multi_matchup_integrity_report(
    *,
    remat: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Double-count / residual check across more than one matchup."""
    replay = {row["key"]: row for row in replay_focus_matchups()}
    remat_games = {
        str(g.get("key")): g
        for g in ((remat or {}).get("games") or [])
        if isinstance(g, dict)
    }
    rows: List[Dict[str, Any]] = []
    material_wl_vs_epa: List[str] = []
    overlay_leaks: List[str] = []
    for key in INTEGRITY_FOCUS_KEYS:
        replay_row = replay.get(key)
        remat_row = remat_games.get(key)
        if replay_row is None:
            continue
        epa = replay_row["epa"]
        rec = replay_row["record"]
        delta = replay_row["deltas"].get("record_spread_minus_epa_spread")
        if delta is not None and abs(float(delta)) >= 0.75:
            material_wl_vs_epa.append(key)
        for src_name, block in (("epa", epa), ("record", rec)):
            comps = block.get("components") or {}
            if float((comps.get("injuries_depth") or {}).get("margin_points") or 0.0) != 0.0:
                overlay_leaks.append(f"{key}:{src_name}:injuries_depth")
            if float((comps.get("personnel_efficiency") or {}).get("margin_points") or 0.0) != 0.0:
                overlay_leaks.append(f"{key}:{src_name}:personnel_efficiency")
        remat_overlay_ok = True
        if remat_row is not None:
            overlays = remat_row.get("overlays") or {}
            remat_overlay_ok = (
                abs(float(overlays.get("personnel_margin_points") or 0.0)) == 0.0
                and abs(float(overlays.get("injuries_margin_points") or 0.0)) == 0.0
            )
            if not remat_overlay_ok:
                overlay_leaks.append(f"{key}:remat_overlay")
        actual = replay_row.get("actual") or {}
        residual = None
        if actual.get("total") is not None and epa.get("predicted_total") is not None:
            residual = round(float(actual["total"]) - float(epa["predicted_total"]), 4)
        rows.append(
            {
                "key": key,
                "week": replay_row.get("week"),
                "epa_spread_home": epa.get("spread_home"),
                "epa_total": epa.get("predicted_total"),
                "record_spread_home": rec.get("spread_home"),
                "record_minus_epa_spread": delta,
                "actual_total": actual.get("total"),
                "epa_total_residual": residual,
                "remat_spread_home": (remat_row or {}).get("spread_home"),
                "classify_epa": classify_strength_source(
                    offense_index=float(epa["offense_index_home"]),
                    defense_index=float(epa["defense_index_home"]),
                    record_summary=None,
                    epa={"offense_index": epa["offense_index_home"], "defense_index": epa["defense_index_home"]},
                ),
                "overlay_zero": remat_overlay_ok,
            }
        )
    passed = (
        len(rows) >= 4
        and len(material_wl_vs_epa) >= 2
        and not overlay_leaks
        and "ATL@PIT" in material_wl_vs_epa
        and "CHI@CAR" in material_wl_vs_epa
    )
    report = {
        "run_id": NFL_564_REMEDIATION,
        "production_promote": PRODUCTION_PROMOTE,
        "focus_keys": list(INTEGRITY_FOCUS_KEYS),
        "matchups": rows,
        "material_wl_vs_epa_keys": material_wl_vs_epa,
        "overlay_leaks": overlay_leaks,
        "double_count_check": "pass" if not overlay_leaks else "fail",
        "multi_matchup_required": True,
        "passed": passed,
        "recommendation": "HOLD_PUBLIC",
        "note": (
            "Personnel/injury remain off. Do not turn overlays on until this "
            "check stays pass on ≥2 matchups. Ryan CLEAR still required before reopen."
        ),
    }
    report["checksum_sha256"] = sha256_canonical(report)
    return report


def sha256_canonical(payload: Mapping[str, Any]) -> str:
    copy = {k: v for k, v in payload.items() if k != "checksum_sha256"}
    blob = json.dumps(copy, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _coerce_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


__all__ = [
    "INTEGRITY_FOCUS_KEYS",
    "NFL_2026_W1_OUTCOMES",
    "NFL_2026_W2_SLATE",
    "NFL_564_REMEDIATION",
    "NflWlPersistRefused",
    "OVERLAYS_OFF_LABEL",
    "PRODUCTION_PROMOTE",
    "ResolvedAdhocStrength",
    "build_multi_matchup_integrity_report",
    "context_looks_like_win_loss",
    "merge_readiness_with_outcomes_coverage",
    "normalize_nfl_abbr",
    "overlays_must_stay_off",
    "packaged_epa_row",
    "rematerialize_week_epa_overlays_off",
    "resolve_adhoc_simulation_strength",
    "resolve_current_nfl_board_week_from_rows",
    "sha256_canonical",
    "slate_row_is_completed",
    "week1_outcomes_coverage_fixture",
]
