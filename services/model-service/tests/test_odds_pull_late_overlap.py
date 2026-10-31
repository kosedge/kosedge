"""Noon-dedupe: LATE odds pull must not share an hour with ACTIVE.

Live reduced cadence (ACTIVE 12–18 + LATE 12–12) would otherwise dispatch
TASK_PULL_ODDS_SNAPSHOT twice at 12:00 ET. Full-season defaults (LATE 03 vs
ACTIVE 07–23) have no overlap, so LATE stays.
"""

from __future__ import annotations

import importlib

import pytest

_ODDS_HOUR_ENV = (
    "ODDS_PULL_LATE_ENABLED",
    "ODDS_PULL_ACTIVE_START_HOUR",
    "ODDS_PULL_ACTIVE_END_HOUR",
    "ODDS_PULL_LATE_START_HOUR",
    "ODDS_PULL_LATE_END_HOUR",
)

# Receipt 4af4632e / beat d217d82d live reduced window. Do not restore 7–23.
_LIVE_REDUCED = {
    "ODDS_PULL_ACTIVE_START_HOUR": "12",
    "ODDS_PULL_ACTIVE_END_HOUR": "18",
    "ODDS_PULL_LATE_START_HOUR": "12",
    "ODDS_PULL_LATE_END_HOUR": "12",
}

_LATE_ENTRY = "pull-odds-3am-refresh"
_ACTIVE_ENTRY = "pull-odds-season-cadence"


@pytest.fixture
def reload_beat(monkeypatch: pytest.MonkeyPatch):
    def _load(**env: str):
        for name in _ODDS_HOUR_ENV:
            monkeypatch.delenv(name, raising=False)
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        module = importlib.import_module("src.celerybeat_schedule")
        return importlib.reload(module)

    yield _load
    for name in _ODDS_HOUR_ENV:
        monkeypatch.delenv(name, raising=False)
    importlib.reload(importlib.import_module("src.celerybeat_schedule"))


def _odds_pull_hours(module: object) -> set[int]:
    hours: set[int] = set()
    task = module.TASK_PULL_ODDS_SNAPSHOT
    for name, entry in module.beat_schedule.items():
        if entry["task"] != task or not name.startswith("pull-odds-"):
            continue
        hours.update(entry["schedule"].hour)
    return hours


def test_late_entry_absent_under_live_reduced_vars(reload_beat) -> None:
    module = reload_beat(**_LIVE_REDUCED)
    assert _LATE_ENTRY not in module.beat_schedule
    assert _ACTIVE_ENTRY in module.beat_schedule
    hours = _odds_pull_hours(module)
    assert hours == set(range(12, 19))
    assert len(hours) == 7


def test_late_entry_present_under_full_season_defaults(reload_beat) -> None:
    module = reload_beat()
    assert module.LATE_ENABLED is True
    assert module.LATE_START_HOUR == "3"
    assert module.LATE_END_HOUR == "3"
    assert module.ACTIVE_START_HOUR == "7"
    assert module.ACTIVE_END_HOUR == "23"
    assert not module._late_overlaps_active()
    assert _LATE_ENTRY in module.beat_schedule
    hours = _odds_pull_hours(module)
    assert 3 in hours
    assert hours == {3} | set(range(7, 24))


def test_late_disabled_drops_entry_even_without_overlap(reload_beat) -> None:
    module = reload_beat(ODDS_PULL_LATE_ENABLED="0")
    assert _LATE_ENTRY not in module.beat_schedule
    assert 3 not in _odds_pull_hours(module)
    assert _ACTIVE_ENTRY in module.beat_schedule
