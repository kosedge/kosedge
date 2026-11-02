from __future__ import annotations

# model-service/services/odds_api.py
import logging
import os

import requests

BASE_URL = "https://api.the-odds-api.com/v4"


class OddsAPIHTTPError(Exception):
    """HTTP failure from The Odds API with no request URL (and no apiKey)."""

    def __init__(self, status: int | None, endpoint: str, source: str) -> None:
        self.status = status
        self.endpoint = endpoint
        self.source = source
        super().__init__(
            f"Odds API HTTP {status} endpoint={endpoint} source={source}"
        )


def _detach_exception_chain(exc: BaseException) -> None:
    exc.__cause__ = None
    exc.__context__ = None
    exc.__suppress_context__ = True


def _raise_for_status_sanitized(
    resp: requests.Response, *, endpoint: str, source: str
) -> None:
    sanitized: OddsAPIHTTPError | None = None
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        status = None
        response = getattr(exc, "response", None)
        if response is not None:
            status = getattr(response, "status_code", None)
        if status is None:
            status = getattr(resp, "status_code", None)
        # Build the replacement inside the handler, raise it outside so
        # `from None` is not fighting an implicit HTTPError __context__.
        sanitized = OddsAPIHTTPError(status=status, endpoint=endpoint, source=source)
    if sanitized is not None:
        _detach_exception_chain(sanitized)
        raise sanitized from None


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return bool(default)
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


def _configured_key_pool() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for source, raw_key in (
        ("primary", os.getenv("ODDS_API_KEY")),
        ("backup", os.getenv("ODDS_API_KEY_BACKUP")),
    ):
        key = (raw_key or "").strip()
        if key and all(existing_key != key for _, existing_key in pairs):
            pairs.append((source, key))
    return pairs


def _select_odds_api_key_pairs() -> list[tuple[str, str]]:
    pool = _configured_key_pool()
    mode = str(os.getenv("ODDS_API_KEY_ACTIVE", "auto")).strip().lower()
    by_source = {source: key for source, key in pool}
    if mode == "auto":
        return pool
    if mode in {"primary", "backup"}:
        selected_key = by_source.get(mode)
        return [(mode, selected_key)] if selected_key else []
    if mode == "embedded":
        logging.warning(
            "ODDS_API_KEY_ACTIVE=embedded is retired; use ODDS_API_KEY / ODDS_API_KEY_BACKUP"
        )
        return []
    logging.warning("Unknown ODDS_API_KEY_ACTIVE value '%s'; defaulting to auto mode", mode)
    return pool


def get_odds_api_keys() -> list[str]:
    return [key for _, key in _select_odds_api_key_pairs()]


def get_odds_api_key() -> str | None:
    keys = get_odds_api_keys()
    return keys[0] if keys else None


def odds_key_diagnostics() -> dict[str, object]:
    selected = _select_odds_api_key_pairs()
    return {
        "active_mode": str(os.getenv("ODDS_API_KEY_ACTIVE", "auto")).strip().lower(),
        "selected_sources": [source for source, _ in selected],
        "selected_key_count": len(selected),
    }


def assert_odds_key_present() -> None:
    if not get_odds_api_key():
        raise RuntimeError(
            "Odds API key missing. Configure ODDS_API_KEY/ODDS_API_KEY_BACKUP. "
            f"diagnostics={odds_key_diagnostics()}"
        )


def request_path_paid_odds_allowed() -> bool:
    """C8: request-path paid Odds only when ODDS_API_REQUEST_PATH_ALLOW==\"1\".

    Unset / any other value denies. Beat/worker does not consult this flag.
    Setting the flag is an env CLEAR (A1 HOLD) — default deny is the ship state.
    """
    return os.getenv("ODDS_API_REQUEST_PATH_ALLOW", "").strip() == "1"


def fetch_odds(endpoint: str, params: dict):
    return fetch_odds_with_metadata(endpoint=endpoint, params=params)["payload"]


def fetch_odds_with_metadata(endpoint: str, params: dict) -> dict:
    assert_odds_key_present()
    last_error: OddsAPIHTTPError | None = None

    # Avoid inheriting host proxy auto-detection; local proxy settings can block
    # The Odds API while direct egress is available from this runtime.
    with requests.Session() as session:
        session.trust_env = False
        for source, api_key in _select_odds_api_key_pairs():
            resp = session.get(
                f"{BASE_URL}/{endpoint}",
                params={**params, "apiKey": api_key},
                timeout=15,
            )

            try:
                _raise_for_status_sanitized(resp, endpoint=endpoint, source=source)
            except OddsAPIHTTPError as exc:
                _detach_exception_chain(exc)
                last_error = exc
                continue

            remaining = resp.headers.get("x-requests-remaining")
            used = resp.headers.get("x-requests-used")
            last = resp.headers.get("x-requests-last")
            logging.info(
                "[ODDS_API] request succeeded source=%s remaining=%s used=%s last=%s",
                source,
                remaining,
                used,
                last,
            )
            return {
                "payload": resp.json(),
                "source": source,
                "x_requests_remaining": remaining,
                "x_requests_used": used,
                "x_requests_last": last,
            }

    if last_error is not None:
        _detach_exception_chain(last_error)
        raise last_error from None
    raise RuntimeError("Odds API key missing")
