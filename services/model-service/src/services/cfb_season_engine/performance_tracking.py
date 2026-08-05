"""CFB season-engine performance tracking + CLV logging.

Logs project-game outputs against closing lines and final scores so the model
can be measured continuously. Designed to never block the happy path:

- Durable JSONL lake (always available; Railway Postgres has been flaky)
- Optional Postgres ``cfb_projection_logs`` best-effort upsert
- Auto-log from project-game when ``CFB_AUTO_LOG_PROJECTIONS=1``

CLV convention (home-relative spreads; negative = home favored)
--------------------------------------------------------------
``spread_clv = model_spread_home - close_spread_home``

Positive CLV means the model's home spread was a *better home-side price*
than the close (e.g. model −3, close −7 → CLV +4). Negative means the model
was more home-favoring than the market closed.

``total_clv = model_total - close_total`` (positive = model higher than close).

Grading
-------
- ATS: vs close when available, else vs model spread. Home covers if
  ``actual_margin + line > 0`` (push on ~0).
- O/U: vs close when available, else vs model total.
- SU: home win if ``home_score > away_score``; model pick is home when WP ≥ 0.5.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.cfb_season_engine import priors as P

log = logging.getLogger("kosedge.cfb.performance_tracking")

_REPO_ROOT = Path(__file__).resolve().parents[5]
_DEFAULT_LAKE = _REPO_ROOT / "data" / "ops" / "cfb_projection_logs"
LAKE_DIR = Path(os.getenv("CFB_PROJECTION_LOG_DIR") or _DEFAULT_LAKE)
JSONL_NAME = "projections.jsonl"

# jsonl | db | auto (try db, always mirror jsonl)
BACKEND = (os.getenv("CFB_PROJECTION_LOG_BACKEND") or "auto").strip().lower()
AUTO_LOG_ENV = "CFB_AUTO_LOG_PROJECTIONS"


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
    """model_spread − close_spread; positive = beat close on the home-side price."""
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
    """Home covers if actual_margin + line > 0 (standard ATS)."""
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
    """Grade ATS / O/U / SU for a logged projection with result (+ optional close)."""
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
    ats_side = "close" if close_spread is not None else (
        "model" if model_spread is not None else None
    )
    grade_ats: Optional[str] = None
    if ats_line is not None:
        # Grade the *model's preferred side* vs the line.
        # Model likes home when model_spread < line (more negative / smaller).
        line_f = float(ats_line)
        model_s = float(model_spread) if model_spread is not None else line_f
        home_cover = _grade_cover(actual_margin, line_f)
        model_home_edge = line_f - model_s
        if abs(model_home_edge) < 0.5:
            # No material lean — grade home side of the line as neutral push proxy.
            grade_ats = "push" if home_cover == "push" else None
            if grade_ats is None:
                # Still record whether home covered for bookkeeping.
                grade_ats = "home_" + home_cover
        elif model_home_edge > 0:
            # Model liked home
            if home_cover == "push":
                grade_ats = "push"
            else:
                grade_ats = "win" if home_cover == "win" else "loss"
        else:
            # Model liked away
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
            # Model over
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
        return cls(
            id=str(payload.get("id") or uuid.uuid4()),
            game_key=str(payload.get("game_key") or ""),
            season=int(payload.get("season") or 0),
            week=int(payload.get("week") or 0),
            home_team=str(payload.get("home_team") or "").upper(),
            away_team=str(payload.get("away_team") or "").upper(),
            engine_version=str(payload.get("engine_version") or P.ENGINE_VERSION),
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


def _jsonl_path(lake_dir: Optional[Path] = None) -> Path:
    d = Path(lake_dir) if lake_dir is not None else LAKE_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d / JSONL_NAME


def _read_jsonl(lake_dir: Optional[Path] = None) -> List[ProjectionLog]:
    path = _jsonl_path(lake_dir)
    if not path.exists():
        return []
    out: List[ProjectionLog] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(ProjectionLog.from_dict(json.loads(line)))
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                log.warning("skip bad projection log line: %s", exc)
    return out


def _rewrite_jsonl(records: Sequence[ProjectionLog], lake_dir: Optional[Path] = None) -> None:
    path = _jsonl_path(lake_dir)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec.to_dict(), separators=(",", ":"), default=str))
            fh.write("\n")
    tmp.replace(path)


def _append_jsonl(record: ProjectionLog, lake_dir: Optional[Path] = None) -> None:
    path = _jsonl_path(lake_dir)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record.to_dict(), separators=(",", ":"), default=str))
        fh.write("\n")


def _upsert_jsonl(record: ProjectionLog, lake_dir: Optional[Path] = None) -> ProjectionLog:
    rows = _read_jsonl(lake_dir)
    found = False
    for i, row in enumerate(rows):
        if row.id == record.id:
            rows[i] = record
            found = True
            break
    if found:
        _rewrite_jsonl(rows, lake_dir)
    else:
        _append_jsonl(record, lake_dir)
    record.storage = "jsonl"
    return record


def _get_jsonl(proj_id: str, lake_dir: Optional[Path] = None) -> Optional[ProjectionLog]:
    for row in _read_jsonl(lake_dir):
        if row.id == proj_id:
            return row
    return None


def _db_enabled() -> bool:
    backend = (os.getenv("CFB_PROJECTION_LOG_BACKEND") or BACKEND or "auto").strip().lower()
    if backend == "jsonl":
        return False
    if backend == "db":
        return True
    # auto — skip unless explicitly opted in (Railway Postgres has been flaky;
    # JSONL is the durable default). Set CFB_PROJECTION_LOG_DB=1 to enable.
    if os.getenv("CFB_PROJECTION_LOG_DB", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return False
    return bool(os.getenv("DATABASE_URL"))


def _try_db_insert(record: ProjectionLog) -> bool:
    if not _db_enabled():
        return False
    try:
        from sqlalchemy import text

        from src.db import SessionLocal
    except Exception as exc:  # pragma: no cover - import / env edge
        log.debug("cfb projection db unavailable: %s", exc)
        return False

    session = None
    try:
        session = SessionLocal()
        session.execute(
            text(
                """
                INSERT INTO cfb_projection_logs (
                  id, game_key, season, week, home_team, away_team, engine_version,
                  projected_at, model_spread_home, model_total, home_win_prob,
                  away_win_prob, expected_home_score, expected_away_score,
                  drivers, projection, close_spread_home, close_total,
                  close_captured_at, close_source, spread_clv, total_clv,
                  home_score, away_score, result_captured_at, result_source,
                  grade_ats, grade_ou, grade_su, updated_at
                ) VALUES (
                  CAST(:id AS uuid), :game_key, :season, :week, :home_team, :away_team,
                  :engine_version, CAST(:projected_at AS timestamptz),
                  :model_spread_home, :model_total, :home_win_prob, :away_win_prob,
                  :expected_home_score, :expected_away_score,
                  CAST(:drivers AS jsonb), CAST(:projection AS jsonb),
                  :close_spread_home, :close_total,
                  CAST(:close_captured_at AS timestamptz), :close_source,
                  :spread_clv, :total_clv, :home_score, :away_score,
                  CAST(:result_captured_at AS timestamptz), :result_source,
                  :grade_ats, :grade_ou, :grade_su,
                  CAST(:updated_at AS timestamptz)
                )
                ON CONFLICT (id) DO UPDATE SET
                  close_spread_home = EXCLUDED.close_spread_home,
                  close_total = EXCLUDED.close_total,
                  close_captured_at = EXCLUDED.close_captured_at,
                  close_source = EXCLUDED.close_source,
                  spread_clv = EXCLUDED.spread_clv,
                  total_clv = EXCLUDED.total_clv,
                  home_score = EXCLUDED.home_score,
                  away_score = EXCLUDED.away_score,
                  result_captured_at = EXCLUDED.result_captured_at,
                  result_source = EXCLUDED.result_source,
                  grade_ats = EXCLUDED.grade_ats,
                  grade_ou = EXCLUDED.grade_ou,
                  grade_su = EXCLUDED.grade_su,
                  updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "id": record.id,
                "game_key": record.game_key,
                "season": record.season,
                "week": record.week,
                "home_team": record.home_team,
                "away_team": record.away_team,
                "engine_version": record.engine_version,
                "projected_at": record.projected_at,
                "model_spread_home": record.model_spread_home,
                "model_total": record.model_total,
                "home_win_prob": record.home_win_prob,
                "away_win_prob": record.away_win_prob,
                "expected_home_score": record.expected_home_score,
                "expected_away_score": record.expected_away_score,
                "drivers": json.dumps(record.drivers),
                "projection": json.dumps(record.projection),
                "close_spread_home": record.close_spread_home,
                "close_total": record.close_total,
                "close_captured_at": record.close_captured_at,
                "close_source": record.close_source,
                "spread_clv": record.spread_clv,
                "total_clv": record.total_clv,
                "home_score": record.home_score,
                "away_score": record.away_score,
                "result_captured_at": record.result_captured_at,
                "result_source": record.result_source,
                "grade_ats": record.grade_ats,
                "grade_ou": record.grade_ou,
                "grade_su": record.grade_su,
                "updated_at": record.updated_at or _utc_now(),
            },
        )
        session.commit()
        record.storage = "db+jsonl"
        return True
    except Exception as exc:
        log.warning("cfb projection db write failed (jsonl retained): %s", exc)
        if session is not None:
            try:
                session.rollback()
            except Exception:  # pragma: no cover
                pass
        return False
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:  # pragma: no cover
                pass


def _try_db_get(proj_id: str) -> Optional[ProjectionLog]:
    if not _db_enabled():
        return None
    try:
        from sqlalchemy import text

        from src.db import SessionLocal
    except Exception:
        return None
    session = None
    try:
        session = SessionLocal()
        row = session.execute(
            text(
                """
                SELECT id::text, game_key, season, week, home_team, away_team,
                       engine_version, projected_at::text, model_spread_home,
                       model_total, home_win_prob, away_win_prob,
                       expected_home_score, expected_away_score, drivers, projection,
                       close_spread_home, close_total, close_captured_at::text,
                       close_source, spread_clv, total_clv, home_score, away_score,
                       result_captured_at::text, result_source,
                       grade_ats, grade_ou, grade_su, updated_at::text
                FROM cfb_projection_logs
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": proj_id},
        ).mappings().first()
        if not row:
            return None
        data = dict(row)
        if "drivers" in data and not isinstance(data["drivers"], dict):
            data["drivers"] = (
                json.loads(data["drivers"])
                if isinstance(data["drivers"], str)
                else dict(data["drivers"] or {})
            )
        if "projection" in data and not isinstance(data["projection"], dict):
            data["projection"] = (
                json.loads(data["projection"])
                if isinstance(data["projection"], str)
                else dict(data["projection"] or {})
            )
        data["storage"] = "db"
        return ProjectionLog.from_dict(data)
    except Exception as exc:
        log.debug("cfb projection db get failed: %s", exc)
        return None
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:  # pragma: no cover
                pass


def log_projection(
    payload: Mapping[str, Any],
    *,
    lake_dir: Optional[Path] = None,
    projection_id: Optional[str] = None,
) -> ProjectionLog:
    """Store a project-game style payload. Never raises to callers if lake writable."""
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
    # Keep a compact drivers snapshot (avoid huge nested blobs when present).
    drivers_compact = {
        k: drivers[k]
        for k in ("summary", "home", "away", "matchup", "efficiency")
        if k in drivers
    } or drivers

    record = ProjectionLog(
        id=str(projection_id or uuid.uuid4()),
        game_key=gkey,
        season=season,
        week=week,
        home_team=home,
        away_team=away,
        engine_version=str(
            payload.get("engine_version") or P.ENGINE_VERSION
        ),
        projected_at=str(payload.get("projected_at") or _utc_now()),
        model_spread_home=_opt_float(payload.get("spread_home")
                                     if payload.get("spread_home") is not None
                                     else payload.get("model_spread_home")),
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
            "game_id": payload.get("game_id"),
            "margin_sd": payload.get("margin_sd"),
            "fidelity": payload.get("fidelity"),
            "mode": payload.get("mode"),
            "notes": payload.get("notes"),
        },
        updated_at=_utc_now(),
    )
    _upsert_jsonl(record, lake_dir)
    if _try_db_insert(record):
        # Re-write jsonl with storage tag
        _upsert_jsonl(record, lake_dir)
    return record


def record_close(
    proj_id: str,
    *,
    close_spread_home: Optional[float] = None,
    close_total: Optional[float] = None,
    source: str = "manual",
    lake_dir: Optional[Path] = None,
) -> Optional[ProjectionLog]:
    record = _get_jsonl(proj_id, lake_dir) or _try_db_get(proj_id)
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
    # Re-grade if result already present
    if record.home_score is not None and record.away_score is not None:
        grades = grade_projection(record.to_dict())
        record.grade_ats = grades.get("grade_ats")
        record.grade_ou = grades.get("grade_ou")
        record.grade_su = grades.get("grade_su")
    _upsert_jsonl(record, lake_dir)
    _try_db_insert(record)
    return record


def record_result(
    proj_id: str,
    *,
    home_score: int,
    away_score: int,
    source: str = "manual",
    lake_dir: Optional[Path] = None,
) -> Optional[ProjectionLog]:
    record = _get_jsonl(proj_id, lake_dir) or _try_db_get(proj_id)
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
    _upsert_jsonl(record, lake_dir)
    _try_db_insert(record)
    return record


def get_projection(
    proj_id: str, *, lake_dir: Optional[Path] = None
) -> Optional[ProjectionLog]:
    return _get_jsonl(proj_id, lake_dir) or _try_db_get(proj_id)


def list_projections(
    *,
    limit: int = 50,
    engine_version: Optional[str] = None,
    lake_dir: Optional[Path] = None,
) -> List[ProjectionLog]:
    rows = _read_jsonl(lake_dir)
    if engine_version:
        rows = [r for r in rows if r.engine_version == engine_version]
    rows.sort(key=lambda r: r.projected_at or "", reverse=True)
    return rows[: max(1, min(int(limit), 500))]


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
    limit: int = 200,
    engine_version: Optional[str] = None,
    lake_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    rows = list_projections(
        limit=limit, engine_version=engine_version, lake_dir=lake_dir
    )
    with_close = [r for r in rows if r.close_spread_home is not None or r.close_total is not None]
    with_result = [r for r in rows if r.home_score is not None and r.away_score is not None]
    spread_clvs = [r.spread_clv for r in rows if r.spread_clv is not None]
    total_clvs = [r.total_clv for r in rows if r.total_clv is not None]

    # Avg absolute error vs result when we have scores
    spread_errors: List[float] = []
    total_errors: List[float] = []
    for r in with_result:
        if r.model_spread_home is not None:
            actual_margin = float(r.home_score) - float(r.away_score)  # type: ignore[arg-type]
            # Model spread_home is home line (neg when home favored); error vs −margin
            # Convention: model_spread ≈ −expected_margin → error = model_spread + margin
            # Simpler: compare model expected margin (−spread) to actual margin.
            model_margin = -float(r.model_spread_home)
            spread_errors.append(abs(model_margin - actual_margin))
        if r.model_total is not None:
            actual_total = float(r.home_score) + float(r.away_score)  # type: ignore[arg-type]
            total_errors.append(abs(float(r.model_total) - actual_total))

    versions = sorted({r.engine_version for r in rows})
    recent = [
        {
            "id": r.id,
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

    return {
        "ok": True,
        "engine_version_filter": engine_version,
        "engine_versions_seen": versions,
        "current_engine_version": P.ENGINE_VERSION,
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
                "positive = beat close on home-side price"
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
        "lake_dir": str(lake_dir or LAKE_DIR),
        "backend": BACKEND,
        "recent": recent,
    }


def auto_log_enabled() -> bool:
    return os.getenv(AUTO_LOG_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def maybe_auto_log_projection(payload: Mapping[str, Any]) -> None:
    """Best-effort background log; never raises / never blocks the request thread long."""
    if not auto_log_enabled():
        return
    if not payload.get("ok", True):
        return

    def _run() -> None:
        try:
            log_projection(payload)
        except Exception as exc:  # pragma: no cover
            log.warning("auto-log projection failed: %s", exc)

    try:
        threading.Thread(target=_run, name="cfb-proj-log", daemon=True).start()
    except Exception as exc:  # pragma: no cover
        log.warning("auto-log spawn failed: %s", exc)


def documentation() -> Dict[str, Any]:
    return {
        "module": "performance_tracking",
        "engine_version": P.ENGINE_VERSION,
        "lake_dir": str(LAKE_DIR),
        "backend": os.getenv("CFB_PROJECTION_LOG_BACKEND") or BACKEND,
        "db_opt_in_env": "CFB_PROJECTION_LOG_DB",
        "auto_log_env": AUTO_LOG_ENV,
        "clv": {
            "spread": "model_spread_home - close_spread_home (positive = beat close)",
            "total": "model_total - close_total",
            "spread_sign": "home-relative; negative = home favored",
        },
        "endpoints": {
            "log": "POST /cfb/season-engine/projections/log",
            "close": "POST /cfb/season-engine/projections/{id}/close",
            "result": "POST /cfb/season-engine/projections/{id}/result",
            "performance": "GET /cfb/season-engine/performance",
        },
        "ops": "data/ops/cfb-performance-tracking-20260805.md",
    }
