"""Production Odds HTTP transport. Key from env/headers only; never logged.

fetch_odds_with_provenance still requires an injected transport (library
default does not open a socket). The one-shot CLI injects this class.
Celery tick must not import this as its primary path.

The Odds API requires ``apiKey`` as a query param. The key is taken from
the ``x-api-key`` header that fetch.py already built from ODDS_API_KEY
(env only). Exceptions are rewritten so URLs/params never leak the key.

Tests inject a fake session_factory. This module does not call The Odds
API at import time.
"""

from __future__ import annotations

from datetime import timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Mapping, Optional

from src.services.nfl_w8_capture.fetch import OddsTransportResult

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
DEFAULT_TIMEOUT_SEC = 15.0


class OddsHttpTransportError(RuntimeError):
    """HTTP transport failed. Message must never contain the key or URL."""


SessionFactory = Callable[[], Any]


def _default_session() -> Any:
    import requests

    session = requests.Session()
    session.trust_env = False
    return session


def provider_server_ts_from_headers(headers: Mapping[str, Any]) -> Optional[str]:
    """RFC 2822 Date header → UTC ISO. Missing Date is not invented."""
    raw = ""
    for key, value in headers.items():
        if str(key).strip().lower() == "date":
            raw = str(value or "").strip()
            break
    if not raw:
        return None
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _header_key(headers: Mapping[str, str]) -> str:
    for key, value in headers.items():
        if str(key).strip().lower() == "x-api-key":
            token = str(value or "").strip()
            if token:
                return token
    raise OddsHttpTransportError("x-api-key missing; ODDS_API_KEY is env-only and never hardcoded")


def _query_params(params: Mapping[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in params.items():
        name = str(key)
        if name == "sport_key":
            continue
        if name.lower() in {"apikey", "api_key", "api-key"}:
            continue
        out[name] = str(value)
    return out


class OddsHttpTransport:
    """Production GET to The Odds API. No secrets in logs or exception text."""

    def __init__(
        self,
        *,
        session_factory: Optional[SessionFactory] = None,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
        base_url: str = ODDS_API_BASE,
    ) -> None:
        self._session_factory = session_factory or _default_session
        self.timeout_sec = float(timeout_sec)
        self.base_url = str(base_url).rstrip("/")

    def __call__(
        self,
        *,
        endpoint: str,
        params: Mapping[str, str],
        headers: Mapping[str, str],
    ) -> OddsTransportResult:
        key = _header_key(headers)
        query = _query_params(params)
        url = f"{self.base_url}/{str(endpoint).lstrip('/')}"
        session = self._session_factory()
        closer = getattr(session, "close", None)
        try:
            try:
                response = session.get(
                    url,
                    params={**query, "apiKey": key},
                    timeout=self.timeout_sec,
                )
            except Exception as exc:  # noqa: BLE001 — rewrite; never leak URL/key
                raise OddsHttpTransportError(
                    f"http get failed: {type(exc).__name__}"
                ) from None
            raw_headers = {
                str(name): str(value) for name, value in dict(response.headers).items()
            }
            body = getattr(response, "content", None)
            if body is None:
                body = str(getattr(response, "text", "") or "").encode("utf-8")
            return OddsTransportResult(
                status_code=int(getattr(response, "status_code", 0) or 0),
                headers=raw_headers,
                body=bytes(body),
                provider_server_ts=provider_server_ts_from_headers(raw_headers),
            )
        finally:
            if closer is not None:
                try:
                    closer()
                except Exception:  # noqa: BLE001 — close is best-effort
                    pass
