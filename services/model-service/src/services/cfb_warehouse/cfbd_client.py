"""Server-side CollegeFootballData client.

Reads ``CFBD_API_KEY`` from the process environment or a gitignored
``.env.local``. Never logs, prints, or persists the secret. Never used by
the frontend. 2025+ seasons are refused.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple
from urllib.parse import parse_qsl, urlparse, urlunparse

from src.services.cfb_warehouse.frozen_140_scoring import FrozenScoringError
from src.services.cfb_warehouse.paths import REPO_ROOT

CFBD_BASE = "https://api.collegefootballdata.com"
SEALED_MIN_YEAR = 2025
ENV_NAMES = ("CFBD_API_KEY", "CFBD_KEY")
USER_AGENT = "kosedge-cfbd-research"


def _parse_env_file(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip("'").strip('"')
    return out


def _env_search_roots() -> Tuple[Path, ...]:
    roots = [Path.cwd(), REPO_ROOT, REPO_ROOT.parent, REPO_ROOT.parent.parent]
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "apps" / "web").is_dir() and (parent / "services" / "model-service").is_dir():
            roots.append(parent)
            break
    # unique, existing only
    out = []
    seen = set()
    for root in roots:
        try:
            resolved = root.resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.is_dir():
            continue
        seen.add(resolved)
        out.append(resolved)
    return tuple(out)


def load_cfbd_api_key() -> Optional[str]:
    for name in ENV_NAMES:
        val = (os.environ.get(name) or "").strip()
        if val:
            return val
    for root in _env_search_roots():
        for rel in (".env.local", ".env"):
            path = root / rel
            if not path.is_file():
                continue
            parsed = _parse_env_file(path.read_text(encoding="utf-8"))
            for name in ENV_NAMES:
                val = (parsed.get(name) or "").strip()
                if val:
                    os.environ["CFBD_API_KEY"] = val
                    return val
    return None


def key_present() -> bool:
    return bool(load_cfbd_api_key())


def redact(text: Any) -> str:
    raw = str(text or "")
    key = load_cfbd_api_key() or ""
    if key:
        raw = raw.replace(key, "[REDACTED]")
    raw = raw.replace("Bearer ", "Bearer [REDACTED]")
    return raw


def refuse_sealed_year(year: Optional[int]) -> None:
    if year is None:
        return
    if int(year) >= SEALED_MIN_YEAR:
        raise FrozenScoringError(
            f"refusing CFBD year {year}; 2025 sealed, 2026 not in the loss"
        )


def refuse_sealed_params(params: Optional[Mapping[str, Any]]) -> None:
    if not params:
        return
    for key in ("year", "season"):
        if params.get(key) not in (None, ""):
            refuse_sealed_year(int(params[key]))


def _sanitize_url(url: str) -> str:
    parsed = urlparse(url)
    query = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in {"api_key", "key", "authorization"}
    ]
    return urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))


class CfbdClient:
    """Thin authenticated GET client with a request budget counter."""

    def __init__(self, *, max_calls: int = 20) -> None:
        self.max_calls = int(max_calls)
        self.calls = 0
        self.key = load_cfbd_api_key()
        if not self.key:
            raise FrozenScoringError("CFBD_API_KEY is not set")

    def get(
        self,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
        *,
        timeout: int = 60,
    ) -> Tuple[Any, Dict[str, Any]]:
        refuse_sealed_params(params)
        if self.calls >= self.max_calls:
            raise FrozenScoringError(
                f"CFBD audit budget exhausted ({self.calls}/{self.max_calls})"
            )
        qs = urllib.parse.urlencode(
            {k: v for k, v in (params or {}).items() if v is not None}
        )
        url = f"{CFBD_BASE}{path}"
        if qs:
            url = f"{url}?{qs}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.key}",
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        self.calls += 1
        meta: Dict[str, Any] = {
            "path": path,
            "params": dict(params or {}),
            "url": _sanitize_url(url),
            "call_index": self.calls,
            "status": None,
            "n_rows": None,
            "bytes": None,
            "error": None,
        }
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                meta["status"] = int(resp.status)
                meta["bytes"] = len(body)
                payload = json.loads(body.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err_body = exc.read() if exc.fp else b""
            meta["status"] = int(exc.code)
            meta["bytes"] = len(err_body)
            meta["error"] = redact(f"HTTP {exc.code}")
            payload = None
            try:
                payload = json.loads(err_body.decode("utf-8"))
            except Exception:
                payload = None
            return payload, meta
        except Exception as exc:  # noqa: BLE001
            meta["error"] = redact(type(exc).__name__)
            return None, meta
        if isinstance(payload, list):
            meta["n_rows"] = len(payload)
        elif isinstance(payload, dict):
            meta["n_rows"] = 1
        else:
            meta["n_rows"] = 0
        return payload, meta
