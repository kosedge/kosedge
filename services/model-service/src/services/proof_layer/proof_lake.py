"""Proof lake storage backends — JSONL (dev/fallback) and Postgres (production)."""

from __future__ import annotations

import json
import logging
import os
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.proof_layer.proof_schema import ensure_proof_projections_table

log = logging.getLogger("kosedge.proof_lake")

JSONL_NAME = "projections.jsonl"
TABLE_NAME = "proof_projections"
LEGACY_CFB_TABLE = "cfb_projection_logs"

_import_lock = threading.Lock()
_import_done = False


class ProofLakeError(RuntimeError):
    """Raised when durable storage is configured but unavailable."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def resolve_backend_name() -> str:
    """Resolve PROOF_LAKE_BACKEND with legacy env fallbacks."""
    raw = (
        os.getenv("PROOF_LAKE_BACKEND")
        or os.getenv("PROJECTION_LOG_BACKEND")
        or os.getenv("CFB_PROJECTION_LOG_BACKEND")
        or "auto"
    ).strip().lower()
    if raw in {"db", "postgres"}:
        return "postgres"
    if raw == "jsonl":
        return "jsonl"
    if raw == "auto":
        if os.getenv("DATABASE_URL"):
            return "postgres"
        return "jsonl"
    log.warning("unknown PROOF_LAKE_BACKEND=%s; defaulting to jsonl", raw)
    return "jsonl"


def _database_url_present() -> bool:
    return bool(os.getenv("DATABASE_URL"))


class ProofLakeBackend(ABC):
    @property
    @abstractmethod
    def backend_name(self) -> str: ...

    @property
    @abstractmethod
    def location(self) -> str: ...

    @abstractmethod
    def upsert(self, record: "ProjectionLog") -> "ProjectionLog": ...

    @abstractmethod
    def get(self, proj_id: str) -> Optional["ProjectionLog"]: ...

    @abstractmethod
    def list_records(
        self,
        *,
        sport: Optional[str] = None,
        limit: Optional[int] = None,
        engine_version: Optional[str] = None,
        season: Optional[int] = None,
        from_ts: Optional[str] = None,
        to_ts: Optional[str] = None,
    ) -> List["ProjectionLog"]: ...

    @abstractmethod
    def count(self) -> int: ...

    def health(self) -> Dict[str, Any]:
        try:
            n = self.count()
            return {"ok": True, "backend": self.backend_name, "location": self.location, "count": n}
        except ProofLakeError as exc:
            return {
                "ok": False,
                "backend": self.backend_name,
                "location": self.location,
                "error": str(exc),
            }


class JsonlLakeBackend(ProofLakeBackend):
    def __init__(self, lake_dir: Path) -> None:
        self._lake_dir = self._resolve_lake(lake_dir)

    @property
    def backend_name(self) -> str:
        return "jsonl"

    @property
    def location(self) -> str:
        return str(self._jsonl_path())

    def _jsonl_path(self) -> Path:
        return self._lake_dir / JSONL_NAME

    @staticmethod
    def _resolve_lake(lake_dir: Path) -> Path:
        candidates = [lake_dir, Path("/tmp/kosedge_projection_logs")]
        for d in candidates:
            try:
                d.mkdir(parents=True, exist_ok=True)
                probe = d / ".write_probe"
                probe.write_text("ok", encoding="utf-8")
                try:
                    probe.unlink()
                except OSError:
                    pass
                return d
            except OSError as exc:
                log.warning("jsonl lake not writable (%s): %s", d, exc)
        return Path("/tmp/kosedge_projection_logs")

    def _read_all(self) -> List["ProjectionLog"]:
        from src.services.proof_layer.core import ProjectionLog

        path = self._jsonl_path()
        if not path.exists():
            return []
        out: List[ProjectionLog] = []
        try:
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        out.append(ProjectionLog.from_dict(json.loads(line)))
                    except (json.JSONDecodeError, TypeError, ValueError) as exc:
                        log.warning("skip bad projection log line: %s", exc)
        except OSError as exc:
            raise ProofLakeError(f"jsonl read failed: {exc}") from exc
        return out

    def _rewrite(self, records: Sequence["ProjectionLog"]) -> None:
        path = self._jsonl_path()
        tmp = path.with_suffix(".tmp")
        try:
            with tmp.open("w", encoding="utf-8") as fh:
                for rec in records:
                    fh.write(json.dumps(rec.to_dict(), separators=(",", ":"), default=str))
                    fh.write("\n")
            tmp.replace(path)
        except OSError as exc:
            raise ProofLakeError(f"jsonl write failed: {exc}") from exc

    def upsert(self, record: "ProjectionLog") -> "ProjectionLog":
        rows = self._read_all()
        found = False
        for i, row in enumerate(rows):
            if row.id == record.id:
                rows[i] = record
                found = True
                break
        if found:
            self._rewrite(rows)
        else:
            try:
                with self._jsonl_path().open("a", encoding="utf-8") as fh:
                    fh.write(
                        json.dumps(record.to_dict(), separators=(",", ":"), default=str)
                    )
                    fh.write("\n")
            except OSError as exc:
                raise ProofLakeError(f"jsonl append failed: {exc}") from exc
        record.storage = "jsonl"
        return record

    def get(self, proj_id: str) -> Optional["ProjectionLog"]:
        for row in self._read_all():
            if row.id == proj_id:
                return row
        return None

    @staticmethod
    def _in_date_range(
        projected_at: Optional[str],
        *,
        from_ts: Optional[str] = None,
        to_ts: Optional[str] = None,
    ) -> bool:
        if not from_ts and not to_ts:
            return True
        if not projected_at:
            return False
        raw = str(projected_at).strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            ts = datetime.fromisoformat(raw)
        except ValueError:
            return False
        if from_ts:
            start_raw = from_ts.strip()
            if start_raw.endswith("Z"):
                start_raw = start_raw[:-1] + "+00:00"
            try:
                if ts < datetime.fromisoformat(start_raw):
                    return False
            except ValueError:
                pass
        if to_ts:
            end_raw = to_ts.strip()
            if end_raw.endswith("Z"):
                end_raw = end_raw[:-1] + "+00:00"
            try:
                if ts > datetime.fromisoformat(end_raw):
                    return False
            except ValueError:
                pass
        return True

    def list_records(
        self,
        *,
        sport: Optional[str] = None,
        limit: Optional[int] = None,
        engine_version: Optional[str] = None,
        season: Optional[int] = None,
        from_ts: Optional[str] = None,
        to_ts: Optional[str] = None,
    ) -> List["ProjectionLog"]:
        rows = self._read_all()
        if sport:
            sport_l = sport.strip().lower()
            rows = [r for r in rows if r.sport == sport_l]
        if engine_version:
            rows = [r for r in rows if r.engine_version == engine_version]
        if season is not None:
            rows = [r for r in rows if int(r.season) == int(season)]
        if from_ts or to_ts:
            rows = [
                r
                for r in rows
                if self._in_date_range(r.projected_at, from_ts=from_ts, to_ts=to_ts)
            ]
        rows.sort(key=lambda r: r.projected_at or "", reverse=True)
        if limit is not None:
            cap = max(1, min(int(limit), 5000))
            rows = rows[:cap]
        return rows

    def count(self) -> int:
        return len(self._read_all())


class PostgresLakeBackend(ProofLakeBackend):
    def __init__(self) -> None:
        self._schema_ready = False
        self._maybe_bootstrap()

    @property
    def backend_name(self) -> str:
        return "postgres"

    @property
    def location(self) -> str:
        return f"postgres://{TABLE_NAME}"

    def _session(self):
        if not _database_url_present():
            raise ProofLakeError("DATABASE_URL not configured")
        from src.db import SessionLocal

        return SessionLocal()

    def _ensure_schema(self, session) -> None:
        if self._schema_ready:
            return
        ensure_proof_projections_table(session)
        session.commit()
        self._schema_ready = True

    def _maybe_bootstrap(self) -> None:
        global _import_done
        with _import_lock:
            if _import_done:
                return
            try:
                self._ensure_schema_and_import_once()
            except Exception as exc:
                log.warning("proof lake bootstrap skipped: %s", exc)
            finally:
                _import_done = True

    def _ensure_schema_and_import_once(self) -> None:
        session = self._session()
        try:
            self._ensure_schema(session)
            count = session.execute(
                __import__("sqlalchemy").text(f"SELECT COUNT(*) FROM {TABLE_NAME}")
            ).scalar()
            if int(count or 0) > 0:
                return
            imported = self._import_jsonl_sources(session)
            legacy = self._import_legacy_cfb_table(session)
            if imported or legacy:
                session.commit()
                log.info(
                    "proof lake bootstrap imported jsonl=%s legacy_cfb=%s rows",
                    imported,
                    legacy,
                )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _import_jsonl_sources(self, session) -> int:
        from src.services.proof_layer.core import ProjectionLog, default_lake_dir

        paths: List[Path] = []
        default = default_lake_dir() / JSONL_NAME
        if default.exists():
            paths.append(default)
        cfb_dir = os.getenv("CFB_PROJECTION_LOG_DIR")
        if cfb_dir:
            cfb_path = Path(cfb_dir) / JSONL_NAME
            if cfb_path.exists() and cfb_path not in paths:
                paths.append(cfb_path)

        imported = 0
        for path in paths:
            try:
                with path.open("r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = ProjectionLog.from_dict(json.loads(line))
                            self._upsert_session(session, rec, commit=False)
                            imported += 1
                        except (json.JSONDecodeError, TypeError, ValueError) as exc:
                            log.warning("skip bad jsonl import line from %s: %s", path, exc)
            except OSError as exc:
                log.warning("jsonl import read failed (%s): %s", path, exc)
        return imported

    def _import_legacy_cfb_table(self, session) -> int:
        from sqlalchemy import text

        from src.services.proof_layer.core import ProjectionLog

        try:
            rows = session.execute(
                text(
                    f"""
                    SELECT id::text, game_key, season, week, home_team, away_team,
                           engine_version, projected_at::text, model_spread_home,
                           model_total, home_win_prob, away_win_prob,
                           expected_home_score, expected_away_score, drivers, projection,
                           close_spread_home, close_total, close_captured_at::text,
                           close_source, spread_clv, total_clv, home_score, away_score,
                           result_captured_at::text, result_source,
                           grade_ats, grade_ou, grade_su, updated_at::text
                    FROM {LEGACY_CFB_TABLE}
                    """
                )
            ).mappings().all()
        except Exception as exc:
            log.debug("legacy cfb_projection_logs import skipped: %s", exc)
            return 0

        imported = 0
        for row in rows:
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
            data["sport"] = str(
                (data.get("projection") or {}).get("sport")
                or (data.get("drivers") or {}).get("sport")
                or "cfb"
            )
            data["market_type"] = (data.get("projection") or {}).get("market_type") or "game"
            data["storage"] = "postgres"
            rec = ProjectionLog.from_dict(data)
            self._upsert_session(session, rec, commit=False)
            imported += 1
        return imported

    @staticmethod
    def _record_params(record: "ProjectionLog") -> Dict[str, Any]:
        return {
            "id": record.id,
            "sport": record.sport,
            "market_type": record.market_type,
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
            "drivers": json.dumps(record.drivers or {}),
            "projection": json.dumps(record.projection or {}),
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
            "payload": json.dumps(record.to_dict()),
            "updated_at": record.updated_at or _utc_now(),
        }

    def _upsert_session(
        self, session, record: "ProjectionLog", *, commit: bool = True
    ) -> None:
        from sqlalchemy import text

        session.execute(
            text(
                f"""
                INSERT INTO {TABLE_NAME} (
                  id, sport, market_type, game_key, season, week, home_team, away_team,
                  engine_version, projected_at, model_spread_home, model_total,
                  home_win_prob, away_win_prob, expected_home_score, expected_away_score,
                  drivers, projection, close_spread_home, close_total,
                  close_captured_at, close_source, spread_clv, total_clv,
                  home_score, away_score, result_captured_at, result_source,
                  grade_ats, grade_ou, grade_su, payload, updated_at
                ) VALUES (
                  CAST(:id AS uuid), :sport, :market_type, :game_key, :season, :week,
                  :home_team, :away_team, :engine_version,
                  CAST(:projected_at AS timestamptz),
                  :model_spread_home, :model_total, :home_win_prob, :away_win_prob,
                  :expected_home_score, :expected_away_score,
                  CAST(:drivers AS jsonb), CAST(:projection AS jsonb),
                  :close_spread_home, :close_total,
                  CAST(:close_captured_at AS timestamptz), :close_source,
                  :spread_clv, :total_clv, :home_score, :away_score,
                  CAST(:result_captured_at AS timestamptz), :result_source,
                  :grade_ats, :grade_ou, :grade_su,
                  CAST(:payload AS jsonb), CAST(:updated_at AS timestamptz)
                )
                ON CONFLICT (id) DO UPDATE SET
                  sport = EXCLUDED.sport,
                  market_type = EXCLUDED.market_type,
                  game_key = EXCLUDED.game_key,
                  season = EXCLUDED.season,
                  week = EXCLUDED.week,
                  home_team = EXCLUDED.home_team,
                  away_team = EXCLUDED.away_team,
                  engine_version = EXCLUDED.engine_version,
                  projected_at = EXCLUDED.projected_at,
                  model_spread_home = EXCLUDED.model_spread_home,
                  model_total = EXCLUDED.model_total,
                  home_win_prob = EXCLUDED.home_win_prob,
                  away_win_prob = EXCLUDED.away_win_prob,
                  expected_home_score = EXCLUDED.expected_home_score,
                  expected_away_score = EXCLUDED.expected_away_score,
                  drivers = EXCLUDED.drivers,
                  projection = EXCLUDED.projection,
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
                  payload = EXCLUDED.payload,
                  updated_at = EXCLUDED.updated_at
                """
            ),
            self._record_params(record),
        )
        if commit:
            session.commit()

    def upsert(self, record: "ProjectionLog") -> "ProjectionLog":
        session = self._session()
        try:
            self._ensure_schema(session)
            self._upsert_session(session, record)
            record.storage = "postgres"
            return record
        except ProofLakeError:
            session.rollback()
            raise
        except Exception as exc:
            session.rollback()
            raise ProofLakeError(f"postgres upsert failed: {exc}") from exc
        finally:
            session.close()

    def _row_to_record(self, row: Mapping[str, Any]) -> "ProjectionLog":
        from src.services.proof_layer.core import ProjectionLog

        data = dict(row)
        for key in ("drivers", "projection", "payload"):
            val = data.get(key)
            if val is not None and not isinstance(val, dict):
                data[key] = (
                    json.loads(val) if isinstance(val, str) else dict(val or {})
                )
        payload = data.get("payload") or {}
        if isinstance(payload, dict) and payload.get("id"):
            payload["storage"] = "postgres"
            return ProjectionLog.from_dict(payload)
        data["storage"] = "postgres"
        return ProjectionLog.from_dict(data)

    def get(self, proj_id: str) -> Optional["ProjectionLog"]:
        from sqlalchemy import text

        session = self._session()
        try:
            self._ensure_schema(session)
            row = session.execute(
                text(
                    f"""
                    SELECT id::text, sport, market_type, game_key, season, week,
                           home_team, away_team, engine_version, projected_at::text,
                           model_spread_home, model_total, home_win_prob, away_win_prob,
                           expected_home_score, expected_away_score, drivers, projection,
                           close_spread_home, close_total, close_captured_at::text,
                           close_source, spread_clv, total_clv, home_score, away_score,
                           result_captured_at::text, result_source,
                           grade_ats, grade_ou, grade_su, payload, updated_at::text
                    FROM {TABLE_NAME}
                    WHERE id = CAST(:id AS uuid)
                    """
                ),
                {"id": proj_id},
            ).mappings().first()
            if not row:
                return None
            return self._row_to_record(row)
        except ProofLakeError:
            raise
        except Exception as exc:
            raise ProofLakeError(f"postgres get failed: {exc}") from exc
        finally:
            session.close()

    def list_records(
        self,
        *,
        sport: Optional[str] = None,
        limit: Optional[int] = None,
        engine_version: Optional[str] = None,
        season: Optional[int] = None,
        from_ts: Optional[str] = None,
        to_ts: Optional[str] = None,
    ) -> List["ProjectionLog"]:
        from sqlalchemy import text

        clauses = ["1=1"]
        params: Dict[str, Any] = {}
        if sport:
            clauses.append("sport = :sport")
            params["sport"] = sport.strip().lower()
        if engine_version:
            clauses.append("engine_version = :engine_version")
            params["engine_version"] = engine_version
        if season is not None:
            clauses.append("season = :season")
            params["season"] = int(season)
        if from_ts:
            clauses.append("projected_at >= CAST(:from_ts AS timestamptz)")
            params["from_ts"] = from_ts
        if to_ts:
            clauses.append("projected_at <= CAST(:to_ts AS timestamptz)")
            params["to_ts"] = to_ts

        cap = max(1, min(int(limit or 500), 5000))
        params["limit"] = cap
        where = " AND ".join(clauses)

        session = self._session()
        try:
            self._ensure_schema(session)
            rows = session.execute(
                text(
                    f"""
                    SELECT id::text, sport, market_type, game_key, season, week,
                           home_team, away_team, engine_version, projected_at::text,
                           model_spread_home, model_total, home_win_prob, away_win_prob,
                           expected_home_score, expected_away_score, drivers, projection,
                           close_spread_home, close_total, close_captured_at::text,
                           close_source, spread_clv, total_clv, home_score, away_score,
                           result_captured_at::text, result_source,
                           grade_ats, grade_ou, grade_su, payload, updated_at::text
                    FROM {TABLE_NAME}
                    WHERE {where}
                    ORDER BY projected_at DESC
                    LIMIT :limit
                    """
                ),
                params,
            ).mappings().all()
            return [self._row_to_record(r) for r in rows]
        except ProofLakeError:
            raise
        except Exception as exc:
            raise ProofLakeError(f"postgres list failed: {exc}") from exc
        finally:
            session.close()

    def count(self) -> int:
        from sqlalchemy import text

        session = self._session()
        try:
            self._ensure_schema(session)
            n = session.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}")).scalar()
            return int(n or 0)
        except ProofLakeError:
            raise
        except Exception as exc:
            raise ProofLakeError(f"postgres count failed: {exc}") from exc
        finally:
            session.close()


_lake_cache: Dict[str, ProofLakeBackend] = {}


def get_lake(*, lake_dir: Optional[Path] = None) -> ProofLakeBackend:
    """Return the configured proof lake backend (cached per resolved path/backend)."""
    backend_name = resolve_backend_name()
    cache_key = f"{backend_name}:{lake_dir or 'default'}"
    if cache_key in _lake_cache:
        return _lake_cache[cache_key]

    if backend_name == "postgres":
        lake: ProofLakeBackend = PostgresLakeBackend()
    else:
        from src.services.proof_layer.core import default_lake_dir

        resolved = lake_dir or default_lake_dir()
        lake = JsonlLakeBackend(Path(resolved))

    _lake_cache[cache_key] = lake
    return lake


def reset_lake_cache() -> None:
    """Clear cached backends (tests)."""
    global _import_done
    _lake_cache.clear()
    _import_done = False
