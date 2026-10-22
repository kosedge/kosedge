"""Fail-closed tests for IMV F-0..F-6 (W8 RA-1 / RA-6)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.services.nfl_handicapping_framework import (
    _env_float,
    get_nfl_handicapping_config,
)
from src.services.nfl_season_engine.continuity_score import (
    ContinuitySourceError,
    _load_packaged_qb1,
    build_continuity_book,
    fetch_current_qb1,
    fetch_prior_primary_qbs,
    fetch_roster_sets,
    fetch_skill_yards_by_player,
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
    collect_nfl_env_overrides,
    db_loader_import_hits,
    record_nfl_env_overrides,
    refuse_db_loaders,
    run_builder_guards,
    w8_build_context,
)
from src.services.nfl_w8_capture.seal import CaptureError, build_and_seal


def _now() -> datetime:
    return datetime(2026, 10, 29, 22, 0, tzinfo=timezone.utc)


def _empty_seal_kwargs(tmp_path: Path) -> dict:
    return {
        "root": str(tmp_path / "seal"),
        "games": [],
        "market_predictions": [],
        "independent_predictions": [],
        "market_inputs": [],
        "independent_inputs": [],
        "market_proofs": [],
        "independent_proofs": [],
        "odds_snapshots": [],
        "model_version": "x",
        "code_sha": "x",
        "now_utc": _now(),
        "dry_run": True,
    }


def test_f0_continuity_import_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "src.services.nfl_season_engine.continuity_score":
            raise ImportError("simulated missing continuity_score")
        return real_import(name, *args, **kwargs)

    prior = league_anchor_package()
    current = TeamEfficiencyPackage(
        **{**league_anchor_package().__dict__, "games_played": 2, "team": "SEA"}
    )
    monkeypatch.setattr(builtins, "__import__", blocked)
    with pytest.raises(RuntimeError, match="fail closed"):
        blend_packages(
            prior,
            current,
            current_games=2,
            prior_travel_weight=0.7,
            continuity_score=0.4,
        )


def test_f1_missing_sqlalchemy_does_not_drop_tendency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F-1: tendency_game_signals is pure math — missing SQLAlchemy must not zero it."""
    import builtins

    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "sqlalchemy" or name.startswith("sqlalchemy."):
            raise ImportError("No module named sqlalchemy")
        return real_import(name, *args, **kwargs)

    sys.modules.pop("src.services.nfl_tendency_pricing", None)
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
    result = _build_matchup_adjustments(inputs)
    points = result["components"]["tendency_proe_spread"]["points"]
    assert points != 0.0
    assert abs(points - 0.28) < 1e-9


def test_f1_tendency_module_import_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
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


@pytest.mark.parametrize(
    ("target", "match"),
    [
        ("fetch_prior_primary_qbs", "prior QB"),
        ("fetch_current_qb1", "current QB"),
        ("fetch_roster_sets_prior", "prior roster"),
        ("fetch_roster_sets_current", "current roster"),
        ("fetch_skill_yards_by_player", "skill-yards"),
        ("continuity_staff_from_packaged", "coaching"),
    ],
)
def test_f2_continuity_loaders_fail_closed(
    monkeypatch: pytest.MonkeyPatch, target: str, match: str
) -> None:
    import src.services.nfl_season_engine.continuity_score as cs

    def boom(*_a, **_k):
        raise RuntimeError("loader down")

    monkeypatch.setattr(cs, "fetch_prior_primary_qbs", lambda *a, **k: {})
    monkeypatch.setattr(cs, "fetch_current_qb1", lambda *a, **k: {})
    monkeypatch.setattr(cs, "fetch_roster_sets", lambda *a, **k: {})
    monkeypatch.setattr(cs, "fetch_skill_yards_by_player", lambda *a, **k: {})

    if target == "continuity_staff_from_packaged":
        import src.services.nfl_season_engine.coaching_staff as staff

        monkeypatch.setattr(staff, "continuity_staff_from_packaged", boom)
    elif target.startswith("fetch_roster_sets"):
        fail_on = 1 if target.endswith("prior") else 2
        calls = {"n": 0}

        def roster_once(*_a, **_k):
            calls["n"] += 1
            if calls["n"] == fail_on:
                raise RuntimeError("roster down")
            return {}

        monkeypatch.setattr(cs, "fetch_roster_sets", roster_once)
    else:
        monkeypatch.setattr(cs, target, boom)

    with pytest.raises(ContinuitySourceError, match="fail closed"):
        build_continuity_book(MagicMock(), season=2026, teams=["SEA"])
    assert match


def test_f3_json_decode_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import src.services.nfl_season_engine.continuity_score as cs

    bad = tmp_path / "nfl_depth_chart_2026_w1.json"
    bad.write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(cs, "_PACKAGE_DATA_DIR", tmp_path)
    with pytest.raises(ContinuitySourceError, match="fail closed"):
        _load_packaged_qb1(2026)


def test_f3_db_loader_fallback_fails_closed() -> None:
    session = MagicMock()
    session.execute.side_effect = RuntimeError("db down")
    with pytest.raises(ContinuitySourceError, match="fail closed"):
        fetch_current_qb1(session, season=1999, as_of_week=1)


def test_f3_coaching_json_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import src.services.nfl_season_engine.coaching_staff as staff

    bad = tmp_path / "nfl_coaching_staff_2026.json"
    bad.write_text("{not-json", encoding="utf-8")
    monkeypatch.setitem(staff._PACKAGED_COACHING_FILES, 2026, bad)
    with pytest.raises(RuntimeError, match="fail closed"):
        staff.load_packaged_coaching_staff(2026)


def test_f4_nfl_env_override_is_stop_and_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NFL_FRAMEWORK_HFA_POINTS", "9.99")
    names = collect_nfl_env_overrides()
    assert "NFL_FRAMEWORK_HFA_POINTS" in names
    with pytest.raises(FailClosedError, match="F-4 STOP") as exc:
        record_nfl_env_overrides()
    assert "NFL_FRAMEWORK_HFA_POINTS" in str(exc.value)
    with pytest.raises(CaptureError, match="F-4 STOP") as cap:
        build_and_seal(**_empty_seal_kwargs(tmp_path))
    assert "NFL_FRAMEWORK_HFA_POINTS" in str(cap.value)


def test_f4_bad_env_value_does_not_revert_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NFL_FRAMEWORK_HFA_POINTS", "not-a-float")
    with pytest.raises(RuntimeError, match="fail closed"):
        _env_float("NFL_FRAMEWORK_HFA_POINTS", 1.05)
    with pytest.raises(RuntimeError, match="fail closed"):
        get_nfl_handicapping_config()


def test_f4_successful_build_records_empty_overrides(tmp_path: Path) -> None:
    built = build_and_seal(**_empty_seal_kwargs(tmp_path))
    manifest = json.loads(
        (Path(built.root) / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["nfl_env_overrides"] == []


def test_f5_shadowed_src_is_stop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "src" / "services"
    fake.mkdir(parents=True)
    (fake / "__init__.py").write_text("# shadow\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(FailClosedError, match="F-5"):
        assert_src_not_shadowed()


def test_f5_regular_src_package_without_services_is_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = tmp_path / "src"
    fake.mkdir(parents=True)
    (fake / "__init__.py").write_text("# regular package shadow\n", encoding="utf-8")
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
    with pytest.raises(FailClosedError, match="F-6"):
        run_builder_guards(session=object())


def test_f6_reaching_db_loader_during_w8_build_is_stop() -> None:
    session = MagicMock()
    with w8_build_context():
        with pytest.raises(RuntimeError, match="F-6 STOP"):
            fetch_prior_primary_qbs(session, prior_season=2025)
        with pytest.raises(RuntimeError, match="F-6 STOP"):
            fetch_roster_sets(session, season=2026)
        with pytest.raises(RuntimeError, match="F-6 STOP"):
            fetch_skill_yards_by_player(session, prior_season=2025)
        with pytest.raises(RuntimeError, match="F-6 STOP"):
            fetch_current_qb1(session, season=2026)


def test_f6_w8_capture_source_does_not_import_db_loaders() -> None:
    assert db_loader_import_hits() == []
