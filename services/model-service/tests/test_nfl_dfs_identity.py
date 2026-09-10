"""Adversarial DFS identity fixtures — fail closed, never invent a row."""

from __future__ import annotations

from src.services.nfl_dfs_identity import (
    DfsProjectionTarget,
    DfsSalaryObservation,
    DfsSlateIdentity,
    certify_dfs_join,
    detect_duplicate_player_uids,
    present_salary_for_site,
)
from src.services.nfl_player_production import PRODUCTION_VERSION


def _slate(**overrides) -> DfsSlateIdentity:
    data = dict(season=2026, week=1, site="DK", slate_id="151307")
    data.update(overrides)
    return DfsSlateIdentity(**data)


def _salary(**overrides) -> DfsSalaryObservation:
    data = dict(
        site="DK",
        season=2026,
        week=1,
        slate_id="151307",
        source_player_id="868199",
        player_uid="uid-allen",
        player_name="Josh Allen",
        team="BUF",
        opponent="HOU",
        position="QB",
        salary=7000,
        game_id="buf-hou-2026w1",
        game_label="BUF @ HOU",
        game_time="2026-09-13T17:00:00Z",
        source="dk_csv",
        source_version="v1",
        captured_at="2026-09-10T12:00:00Z",
        is_current=True,
        identity_status="resolved",
    )
    data.update(overrides)
    return DfsSalaryObservation(**data)


def _proj(**overrides) -> DfsProjectionTarget:
    data = dict(
        season=2026,
        week=1,
        player_uid="uid-allen",
        player_name="Josh Allen",
        team="BUF",
        opponent="HOU",
        position="QB",
        game_id="buf-hou-2026w1",
        production_version=PRODUCTION_VERSION,
        scoring_system="dk_classic",
    )
    data.update(overrides)
    return DfsProjectionTarget(**data)


def test_certified_join_ok() -> None:
    verdict = certify_dfs_join(requested=_slate(), salary=_salary(), projection=_proj())
    assert verdict.ok is True
    assert verdict.allow_value is True
    assert verdict.reason == "ok"


def test_wrong_player_fail_closed() -> None:
    verdict = certify_dfs_join(
        requested=_slate(),
        salary=_salary(player_uid="uid-allen"),
        projection=_proj(player_uid="uid-mahomes"),
    )
    assert verdict.ok is False
    assert verdict.allow_value is False
    assert verdict.reason == "wrong_player"


def test_wrong_opponent_fail_closed() -> None:
    verdict = certify_dfs_join(
        requested=_slate(),
        salary=_salary(opponent="MIA"),
        projection=_proj(opponent="HOU"),
    )
    assert verdict.reason == "opponent_mismatch"
    assert verdict.allow_value is False


def test_wrong_week_fail_closed() -> None:
    verdict = certify_dfs_join(
        requested=_slate(week=2),
        salary=_salary(week=1),
        projection=_proj(week=2),
    )
    assert verdict.reason == "week_mismatch"
    assert verdict.allow_value is False


def test_wrong_slate_fail_closed() -> None:
    verdict = certify_dfs_join(
        requested=_slate(slate_id="showdown-153072"),
        salary=_salary(slate_id="151307"),
        projection=_proj(),
    )
    assert verdict.reason == "slate_mismatch"


def test_dk_salary_cannot_present_as_fd() -> None:
    assert present_salary_for_site(_salary(site="DK"), "FD").reason == "site_mismatch"
    verdict = certify_dfs_join(
        requested=_slate(site="FD"),
        salary=_salary(site="DK"),
        projection=_proj(scoring_system="fd_classic"),
    )
    assert verdict.reason == "site_mismatch"
    assert verdict.allow_value is False


def test_fd_salary_cannot_present_as_dk() -> None:
    assert present_salary_for_site(_salary(site="FD", salary=8800), "DK").reason == "site_mismatch"
    verdict = certify_dfs_join(
        requested=_slate(site="DK"),
        salary=_salary(site="FD", salary=8800),
        projection=_proj(),
    )
    assert verdict.reason == "site_mismatch"


def test_stale_salary_fail_closed() -> None:
    verdict = certify_dfs_join(
        requested=_slate(),
        salary=_salary(is_current=False),
        projection=_proj(),
    )
    assert verdict.reason == "stale_salary"
    assert verdict.allow_value is False


def test_missing_salary_fail_closed() -> None:
    verdict = certify_dfs_join(requested=_slate(), salary=None, projection=_proj())
    assert verdict.reason == "missing_salary"


def test_missing_projection_fail_closed() -> None:
    verdict = certify_dfs_join(requested=_slate(), salary=_salary(), projection=None)
    assert verdict.reason == "missing_projection"
    assert verdict.allow_value is False


def test_duplicate_player_identity_detected() -> None:
    rows = [
        _salary(source_player_id="1", player_uid="uid-allen"),
        _salary(source_player_id="2", player_uid="uid-allen"),
    ]
    assert "uid-allen" in detect_duplicate_player_uids(rows)


def test_traded_team_changed_fail_closed() -> None:
    verdict = certify_dfs_join(
        requested=_slate(),
        salary=_salary(team="BUF", opponent="HOU"),
        projection=_proj(team="LAR", opponent="SF"),
    )
    assert verdict.reason == "team_changed"
    assert verdict.allow_value is False


def test_missing_player_uid_fail_closed() -> None:
    verdict = certify_dfs_join(
        requested=_slate(),
        salary=_salary(player_uid=None, identity_status="unresolved"),
        projection=_proj(),
    )
    assert verdict.reason == "missing_player_identity"


def test_la_lar_team_alias_still_joins() -> None:
    verdict = certify_dfs_join(
        requested=_slate(),
        salary=_salary(team="LA", opponent="SF", player_uid="uid-puka"),
        projection=_proj(team="LAR", opponent="SF", player_uid="uid-puka"),
    )
    assert verdict.reason == "ok"
