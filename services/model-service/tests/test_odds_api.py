import importlib

import pytest


def test_assert_odds_key_present_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    module = importlib.import_module("src.services.odds_api")
    module.ODDS_API_KEY = None

    with pytest.raises(RuntimeError, match="Odds API key missing"):
        module.assert_odds_key_present()

