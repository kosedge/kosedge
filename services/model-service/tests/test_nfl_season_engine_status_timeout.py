"""Season-engine status/universe resolve must not hang on a dead DB."""

from __future__ import annotations

import os
import time
from concurrent.futures import TimeoutError as FuturesTimeoutError

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.routes import nfl as nfl_routes
from src.services.nfl_season_engine.calibration import ENGINE_VERSION
from src.services.nfl_season_engine.loaders import SCHEDULE_SOURCE_PACKAGED


def test_engine_version_includes_projected_sos() -> None:
    assert ENGINE_VERSION.startswith("nfl-season-engine-v1.")
    assert any(
        v in ENGINE_VERSION
        for v in ("v1.14", "v1.15", "v1.16", "v1.17", "v1.18", "v1.19", "v1.20", "v1.21")
    )
    assert any(
        t in ENGINE_VERSION
        for t in (
            "projected-sos",
            "true-pr-harden",
            "season-coherence",
            "defense-variance",
            "team-variance",
        )
    )


def test_resolve_falls_back_to_packaged_when_db_times_out(monkeypatch) -> None:
    class _TimedOutFuture:
        def result(self, timeout=None):  # noqa: ANN001
            raise FuturesTimeoutError()

    class _FakePool:
        def submit(self, fn, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
            return _TimedOutFuture()

        def shutdown(self, wait=False, cancel_futures=True):  # noqa: ANN001
            return None

    monkeypatch.setattr(
        nfl_routes, "ThreadPoolExecutor", lambda max_workers=1: _FakePool()
    )

    started = time.monotonic()
    universe, meta = nfl_routes._resolve_season_engine_universe(
        season=2026,
        as_of_week=1,
        demo=False,
        db_timeout_s=0.8,
    )
    elapsed = time.monotonic() - started

    assert elapsed < 3.0
    assert meta["schedule_source"] == SCHEDULE_SOURCE_PACKAGED
    assert meta.get("mode") == "real"
    assert len(universe.schedule) == 272


def test_resolve_demo_skips_db(monkeypatch) -> None:
    def _boom() -> None:
        raise AssertionError("SessionLocal should not be called for demo")

    monkeypatch.setattr(nfl_routes, "SessionLocal", _boom)
    universe, meta = nfl_routes._resolve_season_engine_universe(
        season=2026, as_of_week=1, demo=True
    )
    assert meta["mode"] == "demo"
    assert len(universe.schedule) == 272
