import importlib

import pytest


def test_get_odds_api_keys_prioritizes_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ODDS_API_KEY", "primary-key")
    monkeypatch.setenv("ODDS_API_KEY_BACKUP", "backup-key")
    module = importlib.import_module("src.services.odds_api")

    assert module.get_odds_api_keys()[:2] == ["primary-key", "backup-key"]


def test_assert_odds_key_present_requires_configured_key_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    monkeypatch.delenv("ODDS_API_KEY_BACKUP", raising=False)
    monkeypatch.delenv("ODDS_API_ALLOW_EMBEDDED_FALLBACK", raising=False)
    module = importlib.import_module("src.services.odds_api")

    with pytest.raises(RuntimeError):
        module.assert_odds_key_present()


def test_embedded_fallback_requires_explicit_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    monkeypatch.delenv("ODDS_API_KEY_BACKUP", raising=False)
    monkeypatch.setenv("ODDS_API_ALLOW_EMBEDDED_FALLBACK", "true")
    module = importlib.import_module("src.services.odds_api")

    module.assert_odds_key_present()
    assert module.get_odds_api_key() == module.EMBEDDED_ODDS_API_BACKUP_KEY


def test_key_active_mode_picks_backup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ODDS_API_KEY", "primary-key")
    monkeypatch.setenv("ODDS_API_KEY_BACKUP", "backup-key")
    monkeypatch.setenv("ODDS_API_KEY_ACTIVE", "backup")
    module = importlib.import_module("src.services.odds_api")

    assert module.get_odds_api_keys() == ["backup-key"]

