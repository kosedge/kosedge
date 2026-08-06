"""Unified projection logging, CLV, and grading for NFL + CFB.

Durable proof lake via Postgres (production) or JSONL (local fallback).
Never blocks live projection paths on write failures.
"""

from __future__ import annotations

import logging
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.proof_layer.proof_lake import (
    ProofLakeError,
    get_lake,
    resolve_backend_name,
)

log = logging.getLogger("kosedge.proof_layer")

_SERVICE_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_LAKE = _SERVICE_ROOT / "data" / "ops" / "projection_logs"
JSONL_NAME = "projections.jsonl"

BACKEND = resolve_backend_name()
AUTO_LOG_ENV = "PROOF_AUTO_LOG_PROJECTIONS"

SUPPORTED_SPORTS = frozenset({"nfl", "cfb"})


def default_lake_dir() -> Path:
    return Path(
        os.getenv("PROJECTION_LOG_DIR")
        or os.getenv("PROOF_LAYER_LOG_DIR")
        or _DEFAULT_LAKE
    )


LAKE_DIR = default_lake_dir()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def game_key(*, season: int, week: int, home_team: str, away_team: str) -> str:
    home = str(home_team).strip().upper()
    away = str(away_team).strip().upper()
    return f"{int(season)}-W{int(week):02d}-{away}@{home}"


def compute_spread_clv(
    model_spread_home: Optional[float], close_spread_home: Optional[float]
) -> Optional[float]:
    if model_spread_home is None or close_spread_home is None:
        return None
    return round(float(model_spread_home) - float(close_spread_home), 4)


def compute_total_clv(
    model_total: Optional[float], close_total: Optional[float]
) -> Optional[float]:
    if model_total is None or close_total is None:
        return None
    return round(float(model_total) - float(close_total), 4)


def _grade_cover(actual_margin: float, line: float) -> str:
    cover_margin = float(actual_margin) + float(line)
    if abs(cover_margin) < 1e-9:
        return "push"
    return "win" if cover_margin > 0 else "loss"


def _grade_ou(actual_total: float, line: float) -> str:
    diff = float(actual_total) - float(line)
    if abs(diff) < 1e-9:
        return "push"
    return "over" if diff > 0 else "under"


def grade_projection(record: Mapping[str, Any]) -> Dict[str, Optional[str]]:
    home_score = record.get("home_score")
    away_score = record.get("away_score")
    if home_score is None or away_score is None:
        return {"grade_ats": None, "grade_ou": None, "grade_su": None, "ats_side": None}

    hs = int(home_score)
    aws = int(away_score)
    actual_margin = float(hs - aws)
    actual_total = float(hs + aws)

    close_spread = record.get("close_spread_home")
    model_spread = record.get("model_spread_home")
    ats_line = close_spread if close_spread is not None else model_spread
    ats_side = (
        "close"
        if close_spread is not None
        else ("model" if model_spread is not None else None)
    )
    grade_ats: Optional[str] = None
    if ats_line is not None:
        line_f = float(ats_line)
        model_s = float(model_spread) if model_spread is not None else line_f
        home_cover = _grade_cover(actual_margin, line_f)
        model_home_edge = line_f - model_s
        if abs(model_home_edge) < 0.5:
            grade_ats = "push" if home_cover == "push" else None
            if grade_ats is None:
                grade_ats = "home_" + home_cover
        elif model_home_edge > 0:
            if home_cover == "push":
                grade_ats = "push"
            else:
                grade_ats = "win" if home_cover == "win" else "loss"
        else:
            if home_cover == "push":
                grade_ats = "push"
            else:
                grade_ats = "win" if home_cover == "loss" else "loss"

    close_total = record.get("close_total")
    model_total = record.get("model_total")
    ou_line = close_total if close_total is not None else model_total
    grade_ou: Optional[str] = None
    if ou_line is not None:
        ou_result = _grade_ou(actual_total, float(ou_line))
        model_t = float(model_total) if model_total is not None else float(ou_line)
        line_t = float(ou_line)
        if abs(model_t - line_t) < 0.5:
            grade_ou = "push" if ou_result == "push" else ("neutral_" + ou_result)
        elif model_t > line_t:
            if ou_result == "push":
                grade_ou = "push"
            else:
                grade_ou = "win" if ou_result == "over" else "loss"
        else:
            if ou_result == "push":
                grade_ou = "push"
            else:
                grade_ou = "win" if ou_result == "under" else "loss"

    home_wp = record.get("home_win_prob")
    model_home = float(home_wp) >= 0.5 if home_wp is not None else None
    home_won = hs > aws
    if hs == aws:
        grade_su: Optional[str] = "push"
    elif model_home is None:
        grade_su = "home_win" if home_won else "away_win"
    else:
        grade_su = "win" if model_home == home_won else "loss"

    return {
        "grade_ats": grade_ats,
        "grade_ou": grade_ou,
        "grade_su": grade_su,
        "ats_side": ats_side,
    }


@dataclass
class ProjectionLog:
    id: str
    sport: str
    market_type: str
    game_key: str
    season: int
    week: int
    home_team: str
    away_team: str
    engine_version: str
    projected_at: str
    model_spread_home: Optional[float] = None
    model_total: Optional[float] = None
    home_win_prob: Optional[float] = None
    away_win_prob: Optional[float] = None
    expected_home_score: Optional[float] = None
    expected_away_score: Optional[float] = None
    drivers: Dict[str, Any] = field(default_factory=dict)
    projection: Dict[str, Any] = field(default_factory=dict)
    close_spread_home: Optional[float] = None
    close_total: Optional[float] = None
    close_captured_at: Optional[str] = None
    close_source: Optional[str] = None
    spread_clv: Optional[float] = None
    total_clv: Optional[float] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    result_captured_at: Optional[str] = None
    result_source: Optional[str] = None
    grade_ats: Optional[str] = None
    grade_ou: Optional[str] = None
    grade_su: Optional[str] = None
    storage: str = "jsonl"
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProjectionLog":
        sport = str(payload.get("sport") or "cfb").strip().lower()
        return cls(
            id=str(payload.get("id") or uuid.uuid4()),
            sport=sport,
            market_type=str(payload.get("market_type") or "game"),
            game_key=str(payload.get("game_key") or ""),
            season=int(payload.get("season") or 0),
            week=int(payload.get("week") or 0),
            home_team=str(payload.get("home_team") or "").upper(),
            away_team=str(payload.get("away_team") or "").upper(),
            engine_version=str(payload.get("engine_version") or "unknown"),
            projected_at=str(payload.get("projected_at") or _utc_now()),
            model_spread_home=_opt_float(payload.get("model_spread_home")),
            model_total=_opt_float(payload.get("model_total")),
            home_win_prob=_opt_float(payload.get("home_win_prob")),
            away_win_prob=_opt_float(payload.get("away_win_prob")),
            expected_home_score=_opt_float(payload.get("expected_home_score")),
            expected_away_score=_opt_float(payload.get("expected_away_score")),
            drivers=dict(payload.get("drivers") or {}),
            projection=dict(payload.get("projection") or {}),
            close_spread_home=_opt_float(payload.get("close_spread_home")),
            close_total=_opt_float(payload.get("close_total")),
            close_captured_at=_opt_str(payload.get("close_captured_at")),
            close_source=_opt_str(payload.get("close_source")),
            spread_clv=_opt_float(payload.get("spread_clv")),
            total_clv=_opt_float(payload.get("total_clv")),
            home_score=_opt_int(payload.get("home_score")),
            away_score=_opt_int(payload.get("away_score")),
            result_captured_at=_opt_str(payload.get("result_captured_at")),
            result_source=_opt_str(payload.get("result_source")),
            grade_ats=_opt_str(payload.get("grade_ats")),
            grade_ou=_opt_str(payload.get("grade_ou")),
            grade_su=_opt_str(payload.get("grade_su")),
            storage=str(payload.get("storage") or "jsonl"),
            updated_at=_opt_str(payload.get("updated_at")),
        )


def _opt_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _opt_int(v: Any) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _opt_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _default_engine_version(sport: str) -> str:
    if sport == "nfl":
        from src.services.nfl_season_engine import DEFAULT_SEASON_ENGINE_VERSION

        return DEFAULT_SEASON_ENGINE_VERSION
    from src.services.cfb_season_engine import priors as P

    return P.ENGINE_VERSION


def _resolve_lake_for_sport(sport: str, lake_dir: Optional[Path]) -> Optional[Path]:
    if lake_dir is not None:
        return lake_dir
    if sport == "cfb" and os.getenv("CFB_PROJECTION_LOG_DIR"):
        return Path(os.getenv("CFB_PROJECTION_LOG_DIR"))
    return None


def _lake_backend(lake_dir: Optional[Path] = None):
    return get_lake(lake_dir=lake_dir)


def _persist_record(record: ProjectionLog, *, lake_dir: Optional[Path] = None) -> ProjectionLog:
    """Write to configured lake; warn on failure (never block live paths)."""
    try:
        return _lake_backend(lake_dir).upsert(record)
    except ProofLakeError as exc:
        log.warning("proof lake write failed: %s", exc)
        record.storage = f"failed:{resolve_backend_name()}"
        return record


def log_projection(
    payload: Mapping[str, Any],
    *,
    sport: Optional[str] = None,
    lake_dir: Optional[Path] = None,
    projection_id: Optional[str] = None,
) -> ProjectionLog:
    resolved_sport = str(sport or payload.get("sport") or "cfb").strip().lower()
    if resolved_sport not in SUPPORTED_SPORTS:
        resolved_sport = "cfb"
    lake = _resolve_lake_for_sport(resolved_sport, lake_dir)

    home = str(payload.get("home_team") or "").strip().upper()
    away = str(payload.get("away_team") or "").strip().upper()
    season = int(payload.get("season") or 0)
    week = int(payload.get("week") or 0)
    gkey = str(payload.get("game_key") or "") or game_key(
        season=season, week=week, home_team=home, away_team=away
    )
    drivers = payload.get("drivers")
    if not isinstance(drivers, dict):
        drivers = {}
    drivers_compact = {
        k: drivers[k]
        for k in ("summary", "home", "away", "matchup", "efficiency")
        if k in drivers
    } or drivers

    projection_meta = dict(payload.get("projection") or {})
    if not isinstance(projection_meta, dict):
        projection_meta = {}

    record = ProjectionLog(
        id=str(projection_id or uuid.uuid4()),
        sport=resolved_sport,
        market_type=str(payload.get("market_type") or "game"),
        game_key=gkey,
        season=season,
        week=week,
        home_team=home,
        away_team=away,
        engine_version=str(
            payload.get("engine_version") or _default_engine_version(resolved_sport)
        ),
        projected_at=str(payload.get("projected_at") or _utc_now()),
        model_spread_home=_opt_float(
            payload.get("spread_home")
            if payload.get("spread_home") is not None
            else payload.get("model_spread_home")
        ),
        model_total=_opt_float(
            payload.get("expected_total")
            if payload.get("expected_total") is not None
            else payload.get("model_total")
        ),
        home_win_prob=_opt_float(payload.get("home_win_prob")),
        away_win_prob=_opt_float(payload.get("away_win_prob")),
        expected_home_score=_opt_float(payload.get("expected_home_score")),
        expected_away_score=_opt_float(payload.get("expected_away_score")),
        drivers=drivers_compact,
        projection={
            "game_id": payload.get("game_id") or projection_meta.get("game_id"),
            "margin_sd": payload.get("margin_sd") or projection_meta.get("margin_sd"),
            "fidelity": payload.get("fidelity") or projection_meta.get("fidelity"),
            "mode": payload.get("mode") or projection_meta.get("mode"),
            "notes": payload.get("notes") or projection_meta.get("notes"),
            "source": projection_meta.get("source"),
            **{
                k: v
                for k, v in projection_meta.items()
                if k not in {"game_id", "margin_sd", "fidelity", "mode", "notes", "source"}
            },
        },
        updated_at=_utc_now(),
    )
    return _persist_record(record, lake_dir=lake)


def record_close(
    proj_id: str,
    *,
    close_spread_home: Optional[float] = None,
    close_total: Optional[float] = None,
    source: str = "manual",
    lake_dir: Optional[Path] = None,
) -> Optional[ProjectionLog]:
    record = get_projection(proj_id, lake_dir=lake_dir)
    if record is None:
        return None
    if close_spread_home is not None:
        record.close_spread_home = float(close_spread_home)
    if close_total is not None:
        record.close_total = float(close_total)
    record.close_captured_at = _utc_now()
    record.close_source = source
    record.spread_clv = compute_spread_clv(
        record.model_spread_home, record.close_spread_home
    )
    record.total_clv = compute_total_clv(record.model_total, record.close_total)
    record.updated_at = _utc_now()
    if record.home_score is not None and record.away_score is not None:
        grades = grade_projection(record.to_dict())
        record.grade_ats = grades.get("grade_ats")
        record.grade_ou = grades.get("grade_ou")
        record.grade_su = grades.get("grade_su")
    return _persist_record(record, lake_dir=lake_dir)


def record_result(
    proj_id: str,
    *,
    home_score: int,
    away_score: int,
    source: str = "manual",
    lake_dir: Optional[Path] = None,
    apply_inseason: bool = False,
) -> Optional[ProjectionLog]:
    record = get_projection(proj_id, lake_dir=lake_dir)
    if record is None:
        return None
    record.home_score = int(home_score)
    record.away_score = int(away_score)
    record.result_captured_at = _utc_now()
    record.result_source = source
    grades = grade_projection(record.to_dict())
    record.grade_ats = grades.get("grade_ats")
    record.grade_ou = grades.get("grade_ou")
    record.grade_su = grades.get("grade_su")
    record.updated_at = _utc_now()
    record = _persist_record(record, lake_dir=lake_dir)
    if apply_inseason and record.sport == "cfb":
        try:
            from src.services.cfb_season_engine.in_season_update import ingest_result

            game_id = str((record.projection or {}).get("game_id") or "")
            ingest_result(
                home_team=record.home_team,
                away_team=record.away_team,
                home_score=int(home_score),
                away_score=int(away_score),
                week=int(record.week or 1),
                season=int(record.season or 2026),
                model_spread_home=record.model_spread_home,
                expected_home_score=record.expected_home_score,
                expected_away_score=record.expected_away_score,
                game_id=game_id,
                projection_id=str(record.id),
                source=f"tracking:{source}",
            )
        except Exception as exc:  # pragma: no cover
            log.warning("in-season update from result failed: %s", exc)
    return record


def get_projection(
    proj_id: str, *, lake_dir: Optional[Path] = None
) -> Optional[ProjectionLog]:
    return _lake_backend(lake_dir).get(proj_id)


def list_projections(
    *,
    sport: Optional[str] = None,
    limit: int = 50,
    engine_version: Optional[str] = None,
    lake_dir: Optional[Path] = None,
) -> List[ProjectionLog]:
    return _lake_backend(lake_dir).list_records(
        sport=sport,
        limit=limit,
        engine_version=engine_version,
    )


def _record_rate(grades: Sequence[Optional[str]]) -> Dict[str, Any]:
    wins = sum(1 for g in grades if g == "win")
    losses = sum(1 for g in grades if g == "loss")
    pushes = sum(1 for g in grades if g == "push")
    decided = wins + losses
    return {
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "n": decided,
        "win_pct": round(wins / decided, 4) if decided else None,
        "record": f"{wins}-{losses}" + (f"-{pushes}" if pushes else ""),
    }


def performance_summary(
    *,
    sport: Optional[str] = None,
    limit: int = 200,
    engine_version: Optional[str] = None,
    lake_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    backend = _lake_backend(lake_dir)
    rows = backend.list_records(
        sport=sport,
        limit=limit,
        engine_version=engine_version,
    )
    with_close = [
        r for r in rows if r.close_spread_home is not None or r.close_total is not None
    ]
    with_result = [r for r in rows if r.home_score is not None and r.away_score is not None]
    spread_clvs = [r.spread_clv for r in rows if r.spread_clv is not None]
    total_clvs = [r.total_clv for r in rows if r.total_clv is not None]

    spread_errors: List[float] = []
    total_errors: List[float] = []
    for r in with_result:
        if r.model_spread_home is not None:
            actual_margin = float(r.home_score) - float(r.away_score)  # type: ignore[arg-type]
            model_margin = -float(r.model_spread_home)
            spread_errors.append(abs(model_margin - actual_margin))
        if r.model_total is not None:
            actual_total = float(r.home_score) + float(r.away_score)  # type: ignore[arg-type]
            total_errors.append(abs(float(r.model_total) - actual_total))

    versions = sorted({r.engine_version for r in rows})
    sports = sorted({r.sport for r in rows})
    recent = [
        {
            "id": r.id,
            "sport": r.sport,
            "market_type": r.market_type,
            "game_key": r.game_key,
            "engine_version": r.engine_version,
            "projected_at": r.projected_at,
            "model_spread_home": r.model_spread_home,
            "model_total": r.model_total,
            "home_win_prob": r.home_win_prob,
            "close_spread_home": r.close_spread_home,
            "close_total": r.close_total,
            "spread_clv": r.spread_clv,
            "total_clv": r.total_clv,
            "home_score": r.home_score,
            "away_score": r.away_score,
            "grade_ats": r.grade_ats,
            "grade_ou": r.grade_ou,
            "grade_su": r.grade_su,
        }
        for r in rows[:25]
    ]

    current_engine = None
    if sport == "nfl":
        from src.services.nfl_season_engine import DEFAULT_SEASON_ENGINE_VERSION

        current_engine = DEFAULT_SEASON_ENGINE_VERSION
    elif sport == "cfb" or not sport:
        from src.services.cfb_season_engine import priors as P

        current_engine = P.ENGINE_VERSION

    lake_health = backend.health()

    return {
        "ok": True,
        "sport_filter": sport,
        "engine_version_filter": engine_version,
        "sports_seen": sports,
        "engine_versions_seen": versions,
        "current_engine_version": current_engine,
        "n_logged": len(rows),
        "n_with_close": len(with_close),
        "n_with_result": len(with_result),
        "ats": _record_rate([r.grade_ats for r in with_result]),
        "ou": _record_rate([r.grade_ou for r in with_result]),
        "su": _record_rate([r.grade_su for r in with_result]),
        "clv": {
            "n_spread": len(spread_clvs),
            "avg_spread_clv": round(sum(spread_clvs) / len(spread_clvs), 4)
            if spread_clvs
            else None,
            "spread_clv_positive_rate": round(
                sum(1 for c in spread_clvs if c > 0) / len(spread_clvs), 4
            )
            if spread_clvs
            else None,
            "n_total": len(total_clvs),
            "avg_total_clv": round(sum(total_clvs) / len(total_clvs), 4)
            if total_clvs
            else None,
            "definition": (
                "spread_clv = model_spread_home - close_spread_home; "
                "positive = beat close on home-side price; only when close exists"
            ),
        },
        "avg_error": {
            "avg_abs_margin_error": round(sum(spread_errors) / len(spread_errors), 3)
            if spread_errors
            else None,
            "avg_abs_total_error": round(sum(total_errors) / len(total_errors), 3)
            if total_errors
            else None,
            "n_margin": len(spread_errors),
            "n_total": len(total_errors),
        },
        "lake_dir": backend.location,
        "backend": backend.backend_name,
        "lake_health": lake_health,
        "recent": recent,
    }


def auto_log_enabled(*, sport: Optional[str] = None) -> bool:
    if sport == "cfb":
        if os.getenv("CFB_AUTO_LOG_PROJECTIONS", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            return True
    if sport == "nfl":
        if os.getenv("NFL_AUTO_LOG_PROJECTIONS", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            return True
    return os.getenv(AUTO_LOG_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def maybe_auto_log_projection(
    payload: Mapping[str, Any],
    *,
    sport: Optional[str] = None,
) -> None:
    resolved_sport = str(sport or payload.get("sport") or "cfb").strip().lower()
    if not auto_log_enabled(sport=resolved_sport):
        return
    if not payload.get("ok", True):
        return

    def _run() -> None:
        try:
            log_projection(payload, sport=resolved_sport)
        except Exception as exc:  # pragma: no cover
            log.warning("auto-log projection failed (%s): %s", resolved_sport, exc)

    try:
        threading.Thread(
            target=_run, name=f"proof-proj-log-{resolved_sport}", daemon=True
        ).start()
    except Exception as exc:  # pragma: no cover
        log.warning("auto-log spawn failed: %s", exc)


def documentation() -> Dict[str, Any]:
    backend = resolve_backend_name()
    try:
        lake = get_lake()
        location = lake.location
        health = lake.health()
    except Exception as exc:
        location = str(LAKE_DIR)
        health = {"ok": False, "error": str(exc)}

    return {
        "module": "proof_layer",
        "supported_sports": sorted(SUPPORTED_SPORTS),
        "lake_dir": location,
        "backend": backend,
        "lake_health": health,
        "table": "proof_projections" if backend == "postgres" else None,
        "env": {
            "PROOF_LAKE_BACKEND": "postgres|jsonl|auto (auto → postgres when DATABASE_URL set)",
            "PROJECTION_LOG_DIR": "JSONL lake directory (dev/fallback only)",
            "PROOF_LAYER_LOG_DIR": "Alias for PROJECTION_LOG_DIR",
            "CFB_PROJECTION_LOG_DIR": "Optional CFB-only JSONL override (legacy compat)",
            "PROJECTION_LOG_BACKEND": "Legacy alias for PROOF_LAKE_BACKEND",
            "PROOF_AUTO_LOG_PROJECTIONS": "Auto-log all supported sports",
            "CFB_AUTO_LOG_PROJECTIONS": "Auto-log CFB only",
            "NFL_AUTO_LOG_PROJECTIONS": "Auto-log NFL only",
        },
        "clv": {
            "spread": "model_spread_home - close_spread_home (positive = beat close)",
            "total": "model_total - close_total",
            "spread_sign": "home-relative; negative = home favored",
            "honesty": "CLV only computed when close exists",
        },
        "endpoints": {
            "log": "POST /proof/projections",
            "close": "POST /proof/projections/{id}/close",
            "result": "POST /proof/projections/{id}/result",
            "performance": "GET /proof/performance?sport=nfl|cfb",
            "calibration_report": "GET /proof/calibration-report?sport=nfl|cfb&engine_version=&from=&to=&season=",
            "calibration_report_generate": "POST /proof/calibration-report/generate",
            "docs": "GET /proof/docs — shows backend + lake location",
            "cfb_compat": {
                "log": "POST /cfb/season-engine/projections/log",
                "close": "POST /cfb/season-engine/projections/{id}/close",
                "result": "POST /cfb/season-engine/projections/{id}/result",
                "performance": "GET /cfb/season-engine/performance",
            },
        },
        "ops": "data/ops/persistent-proof-lake-20260806.md",
        "calibration_reports": "data/ops/historical-calibration-reports-20260806.md",
        "durability": (
            "Production uses Postgres table proof_projections (survives Railway redeploys). "
            "JSONL is dev/fallback only."
        ),
    }
