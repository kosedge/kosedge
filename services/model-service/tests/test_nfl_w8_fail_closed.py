"""Fail-closed tests for IMV F-0..F-6 (W8 RA-1 / RA-6)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.services.nfl_season_engine.continuity_score import (
    ContinuitySourceError,
    build_continuity_book,
)
from src.services.nfl_season_engine.efficiency_backbone import (
    TeamEfficiencyPackage,
    blend_packages,
    league_anchor_package,
)
from src.services.nfl_simulator import NflGameInputs, _build_matchup_adjustments
from src.services.nfl_w8_capture.fail_closed import (
    FailClosedError,
    assert_src_not_shadowed,
    record_nfl_env_overrides,
    refuse_db_loaders,
    run_builder_guards,
)
from src.services.nfl_w8_capture.seal import CaptureError, build_and_seal


def test_f0_continuity_import_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "src.services.nfl_season_engine.continuity_score":
            raise ImportError("simulated missing continuity_score")
        return real_import(name, *args, **kwargs)

    prior = league_anchor_package()
    current = TeamEfficiencyPackage(**{**league_anchor_package().__dict__, "games_played": 2, "team": "SEA"})
    monkeypatch.setattr(builtins, "__import__", blocked)
    with pytest.raises(RuntimeError, match="fail closed"):
        blend_packages(prior, current, current_games=2, prior_travel_weight=0.7, continuity_score=0.4)


def test_f1_missing_sqlalchemy_does_not_drop_tendency(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "src.services.nfl_tendency_pricing":
            raise ImportError("No module named sqlalchemy")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    inputs = NflGameInputs(
        game_id="SYN-F1",
        home_team="AAA",
        away_team="BBB",
        home_off_epa_5g=0.05,
        away_off_epa_5g=-0.02,
        tendency_proe_home=0.04,
        tendency_proe_away=-0.03,
    )
    with pytest.raises(RuntimeError, match="fail closed"):
        _build_matchup_adjustments(inputs)


def test_f2_f3_continuity_loaders_fail_closed() -> None:
    session = MagicMock()
    session.execute.side_effect = RuntimeError("db down")
    with pytest.raises(ContinuitySourceError, match="fail closed"):
        build_continuity_book(session, season=2026, teams=["SEA"])


def test_f4_nfl_env_override_is_stop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NFL_FRAMEWORK_HFA_POINTS", "9.99")
    with pytest.raises(FailClosedError, match="F-4 STOP"):
        record_nfl_env_overrides()
    with pytest.raises(CaptureError, match="F-4 STOP"):
        build_and_seal(
            str(tmp_path / "seal"),
            games=[],
            market_predictions=[],
            independent_predictions=[],
            market_inputs=[],
            independent_inputs=[],
            market_proofs=[],
            independent_proofs=[],
            odds_snapshots=[],
            model_version="x",
            code_sha="x",
            now_utc=__import__("datetime").datetime(2026, 10, 29, 22, 0, tzinfo=__import__("datetime").timezone.utc),
            dry_run=True,
        )


def test_f5_shadowed_src_is_stop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "src" / "services"
    fake.mkdir(parents=True)
    (fake / "__init__.py").write_text("# shadow\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(FailClosedError, match="F-5"):
        assert_src_not_shadowed()


def test_f6_db_loaders_are_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://example.invalid/none")
    with pytest.raises(FailClosedError, match="F-6"):
        refuse_db_loaders()
    with pytest.raises(FailClosedError, match="F-6"):
        refuse_db_loaders(session=object())
    monkeypatch.delenv("DATABASE_URL", raising=False)
    refuse_db_loaders()
    # session alone is enough
    with pytest.raises(FailClosedError, match="F-6"):
        run_builder_guards(session=object())
