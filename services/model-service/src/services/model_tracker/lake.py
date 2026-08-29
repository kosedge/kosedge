"""Persistence for model_pick_ledger — Postgres preferred, JSONL fallback."""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.model_tracker.schema import ensure_model_pick_ledger_table

log = logging.getLogger("kosedge.model_tracker.lake")

_SERVICE_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_LAKE = _SERVICE_ROOT / "data" / "ops" / "model_pick_ledger"
JSONL_NAME = "picks.jsonl"
TABLE = "model_pick_ledger"

_lock = threading.Lock()


class TrackerLakeError(RuntimeError):
    pass


def resolve_backend_name() -> str:
    raw = (
        os.getenv("MODEL_TRACKER_BACKEND")
        or os.getenv("PROOF_LAKE_BACKEND")
        or "auto"
    ).strip().lower()
    if raw in {"jsonl", "db", "postgres", "auto"}:
        return "postgres" if raw in {"db", "postgres"} else raw
    return "auto"


def default_lake_dir() -> Path:
    return Path(os.getenv("MODEL_TRACKER_LOG_DIR") or _DEFAULT_LAKE)


def _jsonl_path(lake_dir: Optional[Path] = None) -> Path:
    root = Path(lake_dir) if lake_dir is not None else default_lake_dir()
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return root / JSONL_NAME
    except OSError:
        fallback = Path("/tmp/kosedge_model_pick_ledger")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback / JSONL_NAME


def _row_to_dict(row: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = dict(row)
    for key in ("result_detail", "payload"):
        val = out.get(key)
        if isinstance(val, str):
            try:
                out[key] = json.loads(val)
            except json.JSONDecodeError:
                out[key] = {}
    for key, val in list(out.items()):
        if hasattr(val, "isoformat"):
            out[key] = val.isoformat().replace("+00:00", "Z")
        elif hasattr(val, "__float__") and key not in {
            "season",
            "week",
            "home_score",
            "away_score",
            "odds_american",
        }:
            try:
                if val is not None and not isinstance(val, (int, float, str, bool)):
                    out[key] = float(val)
            except (TypeError, ValueError):
                pass
    return out


class JsonlLake:
    def __init__(self, lake_dir: Optional[Path] = None) -> None:
        self.path = _jsonl_path(lake_dir)

    def upsert(self, record: Mapping[str, Any]) -> Dict[str, Any]:
        rid = str(record["id"])
        with _lock:
            rows = self._read_all()
            replaced = False
            for i, row in enumerate(rows):
                if str(row.get("id")) == rid:
                    rows[i] = dict(record)
                    replaced = True
                    break
            if not replaced:
                rows.append(dict(record))
            self._write_all(rows)
        out = dict(record)
        out["storage"] = "jsonl"
        return out

    def get(self, pick_id: str) -> Optional[Dict[str, Any]]:
        with _lock:
            for row in self._read_all():
                if str(row.get("id")) == str(pick_id):
                    out = dict(row)
                    out["storage"] = "jsonl"
                    return out
        return None

    def list(
        self,
        *,
        sport: Optional[str] = None,
        season: Optional[int] = None,
        week: Optional[int] = None,
        tag: Optional[str] = None,
        grade: Optional[str] = None,
        engine_version: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        with _lock:
            rows = self._read_all()
        out: List[Dict[str, Any]] = []
        for row in reversed(rows):
            if sport and str(row.get("sport", "")).lower() != sport.lower():
                continue
            if season is not None and int(row.get("season") or -1) != int(season):
                continue
            if week is not None and int(row.get("week") or -1) != int(week):
                continue
            if tag and str(row.get("tag", "")).upper() != tag.upper():
                continue
            if grade and str(row.get("grade", "")).lower() != grade.lower():
                continue
            if engine_version and str(row.get("engine_version") or "") != engine_version:
                continue
            item = dict(row)
            item["storage"] = "jsonl"
            out.append(item)
            if len(out) >= limit:
                break
        return out

    def _read_all(self) -> List[Dict[str, Any]]:
        if not self.path.is_file():
            return []
        rows: List[Dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    def _write_all(self, rows: Sequence[Mapping[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, default=str, separators=(",", ":")))
                fh.write("\n")
        tmp.replace(self.path)


_UPSERT_SQL = f"""
INSERT INTO {TABLE} (
  id, sport, season, week, slate_id, game_id, game_key, home_team, away_team,
  market_type, side, line_at_publish, odds_american, tag, units,
  engine_version, artifact_as_of, deploy_git_sha, kei_version,
  fair_line, kei_line, edge_pts, confidence, variance, confirmation, info_overlap,
  line_at_close, close_captured_at, close_source, clv, open_to_close_move,
  home_score, away_score, result_detail, grade, graded_at,
  units_risked, units_won, units_lost, units_pnl,
  proof_projection_id, created_by, source, notes, payload,
  published_at, created_at, updated_at
) VALUES (
  CAST(:id AS uuid), :sport, :season, :week, :slate_id, :game_id, :game_key,
  :home_team, :away_team, :market_type, :side, :line_at_publish, :odds_american,
  :tag, :units, :engine_version, :artifact_as_of, :deploy_git_sha, :kei_version,
  :fair_line, :kei_line, :edge_pts, :confidence, :variance, :confirmation, :info_overlap,
  :line_at_close, CAST(:close_captured_at AS timestamptz), :close_source, :clv,
  :open_to_close_move, :home_score, :away_score, CAST(:result_detail AS jsonb),
  :grade, CAST(:graded_at AS timestamptz),
  :units_risked, :units_won, :units_lost, :units_pnl,
  CAST(:proof_projection_id AS uuid), :created_by, :source, :notes,
  CAST(:payload AS jsonb),
  CAST(:published_at AS timestamptz), CAST(:created_at AS timestamptz),
  CAST(:updated_at AS timestamptz)
)
ON CONFLICT (id) DO UPDATE SET
  line_at_close = EXCLUDED.line_at_close,
  close_captured_at = EXCLUDED.close_captured_at,
  close_source = EXCLUDED.close_source,
  clv = EXCLUDED.clv,
  open_to_close_move = EXCLUDED.open_to_close_move,
  home_score = EXCLUDED.home_score,
  away_score = EXCLUDED.away_score,
  result_detail = EXCLUDED.result_detail,
  grade = EXCLUDED.grade,
  graded_at = EXCLUDED.graded_at,
  units_risked = EXCLUDED.units_risked,
  units_won = EXCLUDED.units_won,
  units_lost = EXCLUDED.units_lost,
  units_pnl = EXCLUDED.units_pnl,
  notes = EXCLUDED.notes,
  payload = EXCLUDED.payload,
  updated_at = EXCLUDED.updated_at
"""


class PostgresLake:
    def __init__(self) -> None:
        from sqlalchemy import text  # noqa: F401 — ensure importable
        from src.db import SessionLocal

        self._SessionLocal = SessionLocal
        self._text = __import__("sqlalchemy", fromlist=["text"]).text

    def upsert(self, record: Mapping[str, Any]) -> Dict[str, Any]:
        params = self._params(record)
        with self._SessionLocal() as session:
            ensure_model_pick_ledger_table(session)
            session.execute(self._text(_UPSERT_SQL), params)
            session.commit()
        out = dict(record)
        out["storage"] = "postgres"
        return out

    def get(self, pick_id: str) -> Optional[Dict[str, Any]]:
        with self._SessionLocal() as session:
            ensure_model_pick_ledger_table(session)
            row = session.execute(
                self._text(f"SELECT * FROM {TABLE} WHERE id = CAST(:id AS uuid)"),
                {"id": pick_id},
            ).mappings().first()
            session.commit()
        if not row:
            return None
        out = _row_to_dict(row)
        out["storage"] = "postgres"
        return out

    def list(
        self,
        *,
        sport: Optional[str] = None,
        season: Optional[int] = None,
        week: Optional[int] = None,
        tag: Optional[str] = None,
        grade: Optional[str] = None,
        engine_version: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        clauses = ["TRUE"]
        params: Dict[str, Any] = {"limit": int(limit)}
        if sport:
            clauses.append("sport = :sport")
            params["sport"] = sport.lower()
        if season is not None:
            clauses.append("season = :season")
            params["season"] = int(season)
        if week is not None:
            clauses.append("week = :week")
            params["week"] = int(week)
        if tag:
            clauses.append("tag = :tag")
            params["tag"] = tag.upper()
        if grade:
            clauses.append("grade = :grade")
            params["grade"] = grade.lower()
        if engine_version:
            clauses.append("engine_version = :engine_version")
            params["engine_version"] = engine_version
        sql = (
            f"SELECT * FROM {TABLE} WHERE {' AND '.join(clauses)} "
            f"ORDER BY published_at DESC LIMIT :limit"
        )
        with self._SessionLocal() as session:
            ensure_model_pick_ledger_table(session)
            rows = session.execute(self._text(sql), params).mappings().all()
            session.commit()
        out = []
        for row in rows:
            item = _row_to_dict(row)
            item["storage"] = "postgres"
            out.append(item)
        return out

    def _params(self, record: Mapping[str, Any]) -> Dict[str, Any]:
        def j(v: Any) -> str:
            return json.dumps(v if v is not None else {}, default=str)

        return {
            "id": str(record["id"]),
            "sport": str(record.get("sport") or "").lower(),
            "season": int(record.get("season") or 0),
            "week": int(record.get("week") or 0),
            "slate_id": record.get("slate_id"),
            "game_id": record.get("game_id"),
            "game_key": str(record.get("game_key") or ""),
            "home_team": str(record.get("home_team") or "").upper(),
            "away_team": str(record.get("away_team") or "").upper(),
            "market_type": str(record.get("market_type") or "spread").lower(),
            "side": str(record.get("side") or "").lower(),
            "line_at_publish": record.get("line_at_publish"),
            "odds_american": int(record.get("odds_american") or -110),
            "tag": str(record.get("tag") or "").upper(),
            "units": float(record.get("units") or 0),
            "engine_version": record.get("engine_version"),
            "artifact_as_of": record.get("artifact_as_of"),
            "deploy_git_sha": record.get("deploy_git_sha"),
            "kei_version": record.get("kei_version"),
            "fair_line": record.get("fair_line"),
            "kei_line": record.get("kei_line"),
            "edge_pts": record.get("edge_pts"),
            "confidence": record.get("confidence"),
            "variance": record.get("variance"),
            "confirmation": record.get("confirmation"),
            "info_overlap": record.get("info_overlap"),
            "line_at_close": record.get("line_at_close"),
            "close_captured_at": record.get("close_captured_at"),
            "close_source": record.get("close_source"),
            "clv": record.get("clv"),
            "open_to_close_move": record.get("open_to_close_move"),
            "home_score": record.get("home_score"),
            "away_score": record.get("away_score"),
            "result_detail": j(record.get("result_detail") or {}),
            "grade": str(record.get("grade") or "pending").lower(),
            "graded_at": record.get("graded_at"),
            "units_risked": float(record.get("units_risked") or 0),
            "units_won": float(record.get("units_won") or 0),
            "units_lost": float(record.get("units_lost") or 0),
            "units_pnl": float(record.get("units_pnl") or 0),
            "proof_projection_id": record.get("proof_projection_id"),
            "created_by": str(record.get("created_by") or "desk"),
            "source": str(record.get("source") or "manual"),
            "notes": record.get("notes"),
            "payload": j(record.get("payload") or {}),
            "published_at": record.get("published_at"),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
        }


class AutoLake:
    """Try Postgres; always mirror JSONL; fall back to JSONL on DB errors."""

    def __init__(self, lake_dir: Optional[Path] = None) -> None:
        self.jsonl = JsonlLake(lake_dir)
        self._pg: Optional[PostgresLake] = None
        backend = resolve_backend_name()
        self.prefer_pg = backend in {"auto", "postgres"}
        if backend == "jsonl":
            self.prefer_pg = False

    def _pg_lake(self) -> PostgresLake:
        if self._pg is None:
            self._pg = PostgresLake()
        return self._pg

    def upsert(self, record: Mapping[str, Any]) -> Dict[str, Any]:
        mirrored = self.jsonl.upsert(record)
        if not self.prefer_pg:
            return mirrored
        try:
            return self._pg_lake().upsert(record)
        except Exception as exc:
            log.warning("model_tracker postgres upsert failed; using jsonl: %s", exc)
            return mirrored

    def get(self, pick_id: str) -> Optional[Dict[str, Any]]:
        if self.prefer_pg:
            try:
                hit = self._pg_lake().get(pick_id)
                if hit is not None:
                    return hit
            except Exception as exc:
                log.warning("model_tracker postgres get failed: %s", exc)
        return self.jsonl.get(pick_id)

    def list(self, **kwargs: Any) -> List[Dict[str, Any]]:
        if self.prefer_pg:
            try:
                return self._pg_lake().list(**kwargs)
            except Exception as exc:
                log.warning("model_tracker postgres list failed: %s", exc)
        return self.jsonl.list(**kwargs)


_lake_cache: Dict[str, AutoLake] = {}


def get_lake(lake_dir: Optional[Path] = None) -> AutoLake:
    key = str(lake_dir or default_lake_dir())
    if key not in _lake_cache:
        _lake_cache[key] = AutoLake(lake_dir)
    return _lake_cache[key]
