"""JSON-file store for The Book (local + ops artifact).

Postgres schema lives in infra/db/053_book_ledger.sql; this module is the
runtime SoT for snapshot/CLI until PG is wired.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.book_ledger.clv import compute_clv
from src.services.book_ledger.ids import make_book_id, normalize_posted_at, units_for_type
from src.services.book_ledger.schema import BookRow, default_created_at

_SERVICE_ROOT = Path(__file__).resolve().parents[3]
# Railway uses `railway up --path-as-root` so service root is /app (no monorepo
# parent). Never index parents[1] of /app — that IndexError crashes uvicorn boot.
_DEFAULT_DIR = _SERVICE_ROOT / "data" / "ops" / "book"

_lock = threading.RLock()
_STORE: Optional["BookStore"] = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def default_book_dir() -> Path:
    return Path(os.getenv("BOOK_LEDGER_DIR") or _DEFAULT_DIR)


class BookStore:
    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root) if root else default_book_dir()
        # Defer create so import never blocks on I/O; mkdir when first used.
        self._index_path = self.root / "ledger.jsonl"

    def _ensure_root(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def _read_all(self) -> List[Dict[str, Any]]:
        if not self._index_path.exists():
            return []
        rows: List[Dict[str, Any]] = []
        for line in self._index_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
        return rows

    def _write_all(self, rows: Sequence[Mapping[str, Any]]) -> None:
        self._ensure_root()
        tmp = self._index_path.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        tmp.replace(self._index_path)

    def list_rows(
        self,
        *,
        sport: Optional[str] = None,
        week_or_slate: Optional[str] = None,
        result: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with _lock:
            rows = self._read_all()
        out = []
        for r in rows:
            if sport and str(r.get("sport")).lower() != sport.lower():
                continue
            if week_or_slate and str(r.get("week_or_slate")) != str(week_or_slate):
                continue
            if result and str(r.get("result")).lower() != result.lower():
                continue
            out.append(r)
        return out

    def get(self, book_id: str) -> Optional[Dict[str, Any]]:
        with _lock:
            for r in self._read_all():
                if r.get("book_id") == book_id:
                    return r
        return None

    def snapshot(self, row: BookRow) -> Dict[str, Any]:
        """Insert row if new; return existing on natural-key collision (idempotent)."""
        row.posted_at = normalize_posted_at(row.posted_at)
        row.units = units_for_type(row.type)
        row.book_id = make_book_id(
            sport=row.sport,
            game_id=row.game_id,
            market=row.market,
            side=row.side,
            posted_at=row.posted_at,
            type=row.type,
        )
        row.validate()
        now = _utc_now()
        if not row.created_at:
            row.created_at = default_created_at()
        row.updated_at = now
        payload = row.to_dict()

        with _lock:
            rows = self._read_all()
            for existing in rows:
                if existing.get("book_id") == payload["book_id"]:
                    return {"ok": True, "created": False, "row": existing}
                # Natural key defense even if book_id algorithm changes.
                if (
                    str(existing.get("sport")).lower() == payload["sport"]
                    and str(existing.get("game_id")) == payload["game_id"]
                    and str(existing.get("market")).lower() == payload["market"]
                    and str(existing.get("side")).lower() == payload["side"]
                    and normalize_posted_at(str(existing.get("posted_at")))
                    == payload["posted_at"]
                    and str(existing.get("type")).lower() == payload["type"]
                ):
                    return {"ok": True, "created": False, "row": existing}
            rows.append(payload)
            self._write_all(rows)
        return {"ok": True, "created": True, "row": payload}

    def record_close(
        self,
        book_id: str,
        *,
        close_line: Optional[float] = None,
        close_price: Optional[float] = None,
        close_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        with _lock:
            rows = self._read_all()
            for i, existing in enumerate(rows):
                if existing.get("book_id") != book_id:
                    continue
                if str(existing.get("result", "pending")).lower() != "pending":
                    raise ValueError("settled row is immutable")
                existing["close_line"] = close_line
                existing["close_price"] = close_price
                existing["close_at"] = close_at or _utc_now()
                post_line = existing.get("line")
                post_price = existing.get("price")
                existing["clv"] = compute_clv(
                    market=str(existing.get("market")),
                    side=str(existing.get("side")),
                    post_line=float(post_line) if post_line is not None else None,
                    post_price=float(post_price) if post_price is not None else None,
                    close_line=float(close_line) if close_line is not None else None,
                    close_price=float(close_price) if close_price is not None else None,
                )
                existing["updated_at"] = _utc_now()
                rows[i] = existing
                self._write_all(rows)
                return {"ok": True, "row": existing}
        raise KeyError(f"book_id not found: {book_id}")

    def settle(
        self,
        book_id: str,
        *,
        result: str,
        pnl_units: Optional[float] = None,
    ) -> Dict[str, Any]:
        result_tok = str(result).strip().lower()
        if result_tok not in {"win", "loss", "push", "void"}:
            raise ValueError(f"invalid settle result: {result!r}")
        with _lock:
            rows = self._read_all()
            for i, existing in enumerate(rows):
                if existing.get("book_id") != book_id:
                    continue
                if str(existing.get("result", "pending")).lower() != "pending":
                    raise ValueError("settled row is immutable")
                existing["result"] = result_tok
                if pnl_units is not None:
                    existing["pnl_units"] = float(pnl_units)
                elif result_tok == "win":
                    existing["pnl_units"] = float(existing.get("units") or 0.0)
                elif result_tok == "loss":
                    existing["pnl_units"] = -float(existing.get("units") or 0.0)
                else:
                    existing["pnl_units"] = 0.0
                existing["settled_at"] = _utc_now()
                existing["updated_at"] = existing["settled_at"]
                rows[i] = existing
                self._write_all(rows)
                return {"ok": True, "row": existing}
        raise KeyError(f"book_id not found: {book_id}")

    def write_slate_artifact(self, *, sport: str, slate: str, summary: Dict[str, Any]) -> Path:
        self._ensure_root()
        path = self.root / f"{sport}-{slate}.json"
        path.write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        return path


def get_store(root: Optional[Path] = None) -> BookStore:
    global _STORE
    if root is not None:
        return BookStore(root=root)
    with _lock:
        if _STORE is None:
            _STORE = BookStore()
        return _STORE
