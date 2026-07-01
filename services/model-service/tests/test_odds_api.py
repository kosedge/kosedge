import importlib

import pytest


def test_get_odds_api_keys_prioritizes_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ODDS_API_KEY", "primary-key")
    monkeypatch.setenv("ODDS_API_KEY_BACKUP", "backup-key")
    module = importlib.import_module("src.services.odds_api")

    assert module.get_odds_api_keys()[:2] == ["primary-key", "backup-key"]


def test_assert_odds_key_present_uses_embedded_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    monkeypatch.delenv("ODDS_API_KEY_BACKUP", raising=False)
    module = importlib.import_module("src.services.odds_api")

    module.assert_odds_key_present()
    assert module.get_odds_api_key() is not None

