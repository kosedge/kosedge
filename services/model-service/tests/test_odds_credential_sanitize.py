from __future__ import annotations

import importlib
import logging
import re
import traceback
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

import pytest
import requests

# Obviously fake fixtures — never a live Odds API key.
FIXTURE_PRIMARY = "fixture-odds-primary-key-aaa"
FIXTURE_BACKUP = "fixture-odds-backup-key-bbb"
FIXTURE_LOG_KEY = "fixture-odds-log-key-ccc"
SRC_ROOT = Path(__file__).resolve().parents[1] / "src"


class _FakeResponse:
    def __init__(
        self,
        status_code: int,
        url: str,
        payload: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.url = url
        self.headers = headers or {}
        self._payload = payload if payload is not None else []
        self.reason = {401: "Unauthorized", 429: "Too Many Requests", 502: "Bad Gateway"}.get(
            status_code, "Error"
        )

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"{self.status_code} Client Error: {self.reason} for url: {self.url}",
                response=self,
            )

    def json(self) -> Any:
        return self._payload


class _FakeSession:
    def __init__(self, responder: Callable[[str, dict[str, Any] | None], _FakeResponse]) -> None:
        self._responder = responder
        self.trust_env = True
        self.calls: list[dict[str, Any]] = []

    def __enter__(self) -> _FakeSession:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def get(self, url: str, params: dict[str, Any] | None = None, timeout: object = None) -> _FakeResponse:
        self.calls.append({"url": url, "params": dict(params or {}), "timeout": timeout})
        full = f"{url}?{urlencode(params or {})}"
        return self._responder(full, params)


def _reload_odds(monkeypatch: pytest.MonkeyPatch, **env: str | None) -> Any:
    for name in ("ODDS_API_KEY", "ODDS_API_KEY_BACKUP", "ODDS_API_KEY_ACTIVE"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    module = importlib.import_module("src.services.odds_api")
    return importlib.reload(module)


def _assert_no_secret(blob: str, *keys: str, allow_redacted_api_key: bool = False) -> None:
    for key in keys:
        assert key not in blob
    if allow_redacted_api_key:
        leftover = re.sub(
            r"""([?&](apiKey|api_key)=)\*\*\*""",
            r"\1",
            blob,
            flags=re.IGNORECASE,
        )
        assert not re.search(
            r"""([?&](apiKey|api_key)=)(?!\*\*\*)[^&\s"']+""",
            leftover,
            flags=re.IGNORECASE,
        )
        return
    assert "apiKey=" not in blob


def test_sanitize_url_masks_sensitive_query_params() -> None:
    from src.logging_sanitize import sanitize_url

    raw = (
        "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
        f"?regions=us&apiKey={FIXTURE_PRIMARY}&token={FIXTURE_LOG_KEY}"
        f"&key={FIXTURE_BACKUP}&api_key={FIXTURE_PRIMARY}"
    )
    out = sanitize_url(raw)
    _assert_no_secret(
        out,
        FIXTURE_PRIMARY,
        FIXTURE_BACKUP,
        FIXTURE_LOG_KEY,
        allow_redacted_api_key=True,
    )
    assert "apiKey=***" in out
    assert "api_key=***" in out
    assert "key=***" in out
    assert "token=***" in out
    assert "regions=us" in out


@pytest.mark.parametrize("status", [502, 401, 429])
def test_http_error_has_no_url_or_key_in_str_repr_traceback(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    module = _reload_odds(monkeypatch, ODDS_API_KEY=FIXTURE_PRIMARY)

    def _respond(full_url: str, _params: dict[str, Any] | None) -> _FakeResponse:
        assert FIXTURE_PRIMARY in full_url
        return _FakeResponse(status, full_url)

    session = _FakeSession(_respond)
    monkeypatch.setattr(module.requests, "Session", lambda: session)

    with pytest.raises(module.OddsAPIHTTPError) as caught:
        module.fetch_odds_with_metadata(
            endpoint="sports/americanfootball_nfl/odds",
            params={"regions": "us"},
        )

    exc = caught.value
    formatted = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    for blob in (str(exc), repr(exc), formatted):
        _assert_no_secret(blob, FIXTURE_PRIMARY)
        assert "the-odds-api.com" not in blob
    assert exc.status == status
    assert exc.endpoint == "sports/americanfootball_nfl/odds"
    assert exc.source == "primary"
    assert exc.__cause__ is None
    assert exc.__context__ is None


def test_success_path_metadata_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _reload_odds(monkeypatch, ODDS_API_KEY=FIXTURE_PRIMARY)
    payload = [{"id": "evt-1", "sport_key": "americanfootball_nfl"}]
    headers = {
        "x-requests-remaining": "98",
        "x-requests-used": "2",
        "x-requests-last": "1",
    }

    def _respond(full_url: str, params: dict[str, Any] | None) -> _FakeResponse:
        assert (params or {}).get("apiKey") == FIXTURE_PRIMARY
        return _FakeResponse(200, full_url, payload=payload, headers=headers)

    monkeypatch.setattr(module.requests, "Session", lambda: _FakeSession(_respond))
    result = module.fetch_odds_with_metadata(
        endpoint="sports/americanfootball_nfl/odds",
        params={"regions": "us", "markets": "h2h"},
    )
    assert result["payload"] == payload
    assert result["source"] == "primary"
    assert result["x_requests_remaining"] == "98"
    assert result["x_requests_used"] == "2"
    assert result["x_requests_last"] == "1"
    assert module.fetch_odds("sports/americanfootball_nfl/odds", {"regions": "us"}) == payload


def test_backup_key_fallback_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _reload_odds(
        monkeypatch,
        ODDS_API_KEY=FIXTURE_PRIMARY,
        ODDS_API_KEY_BACKUP=FIXTURE_BACKUP,
    )
    payload = [{"id": "evt-backup"}]
    calls: list[str] = []

    def _respond(full_url: str, params: dict[str, Any] | None) -> _FakeResponse:
        key = (params or {}).get("apiKey")
        calls.append(str(key))
        if key == FIXTURE_PRIMARY:
            return _FakeResponse(502, full_url)
        return _FakeResponse(
            200,
            full_url,
            payload=payload,
            headers={"x-requests-remaining": "10", "x-requests-used": "1", "x-requests-last": "1"},
        )

    monkeypatch.setattr(module.requests, "Session", lambda: _FakeSession(_respond))
    result = module.fetch_odds_with_metadata(
        endpoint="sports/americanfootball_nfl/odds",
        params={"regions": "us"},
    )
    assert calls == [FIXTURE_PRIMARY, FIXTURE_BACKUP]
    assert result["source"] == "backup"
    assert result["payload"] == payload
    assert result["x_requests_remaining"] == "10"


def test_logging_filter_masks_msg_args_and_exc_info(caplog: pytest.LogCaptureFixture) -> None:
    from src.logging_sanitize import OddsCredentialLogFilter, install_odds_credential_log_filter

    install_odds_credential_log_filter()
    logger = logging.getLogger("src.tasks.odds_sanitize_test")
    logger.addFilter(OddsCredentialLogFilter())
    leak_url = (
        "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
        f"?bookmakers=draftkings&apiKey={FIXTURE_LOG_KEY}"
    )

    with caplog.at_level(logging.ERROR, logger=logger.name):
        logger.error("failed url=%s", leak_url)
        logger.error(f"inline {leak_url}")
        try:
            raise requests.HTTPError(f"401 Client Error: Unauthorized for url: {leak_url}")
        except requests.HTTPError:
            logger.exception("pull failed")

        text = caplog.text
    _assert_no_secret(text, FIXTURE_LOG_KEY, allow_redacted_api_key=True)

    for record in caplog.records:
        rendered = record.getMessage()
        _assert_no_secret(rendered, FIXTURE_LOG_KEY, allow_redacted_api_key=True)
        if record.exc_text:
            _assert_no_secret(record.exc_text, FIXTURE_LOG_KEY, allow_redacted_api_key=True)
        if record.args:
            args_blob = " ".join(str(item) for item in record.args)
            _assert_no_secret(args_blob, FIXTURE_LOG_KEY, allow_redacted_api_key=True)


def test_celery_and_main_install_the_filter() -> None:
    from src.logging_sanitize import OddsCredentialLogFilter

    celery_app_mod = importlib.import_module("src.celery_app")
    main_mod = importlib.import_module("src.main")
    root_filters = logging.getLogger().filters
    assert any(isinstance(item, OddsCredentialLogFilter) for item in root_filters)
    assert any(isinstance(item, OddsCredentialLogFilter) for item in logging.getLogger("celery").filters)
    assert hasattr(celery_app_mod, "_install_odds_credential_log_filter")
    assert hasattr(main_mod, "install_odds_credential_log_filter")


def test_model_service_src_does_not_log_response_urls() -> None:
    pattern = re.compile(
        r"""(?:log|logger|logging)\.\w+\([^)]*\b(?:resp|request|response)\.url\b"""
    )
    offenders: list[str] = []
    for path in SRC_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for index, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                offenders.append(f"{path.relative_to(SRC_ROOT)}:{index}:{line.strip()}")
    assert offenders == []
