"""Regression: nullable week_cap bind must be typed for psycopg.

Alex live after #567: POST /api/jobs/run-nfl-simulations?game_date=2026-09-17
failed with AmbiguousParameter on ``AND ($2 IS NULL OR week <= $2)``.
The remat prior-season path always binds week_cap=None.
"""

from __future__ import annotations

import inspect
import os
from typing import Any, List, Optional, Tuple

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

import pytest
from sqlalchemy import Integer, text
from sqlalchemy.sql.elements import BindParameter

from src.tasks import (
    FULL_ENGINE_INPUT_MISSING,
    _fetch_rolling_feature_latest_rows,
    _fetch_st_kav_by_team_season,
    _full_engine_input_status,
    _week_cap_bindparam,
    _week_cap_nullable_predicate,
    run_nfl_market_simulations,
)
from src.main import job_run_nfl_simulations


UNTYPED_WEEK_CAP = "(:week_cap IS NULL OR week <= :week_cap)"
TYPED_WEEK_CAP = "(CAST(:week_cap AS int) IS NULL OR week <= CAST(:week_cap AS int))"


class _Result:
    def fetchall(self) -> List[Any]:
        return []


class _CaptureSession:
    def __init__(self) -> None:
        self.calls: List[Tuple[Any, dict]] = []

    def execute(self, sql: Any, params: Optional[dict] = None) -> _Result:
        self.calls.append((sql, dict(params or {})))
        return _Result()


def test_week_cap_predicate_is_explicitly_cast() -> None:
    assert _week_cap_nullable_predicate() == TYPED_WEEK_CAP
    assert UNTYPED_WEEK_CAP not in _week_cap_nullable_predicate()
    bp = _week_cap_bindparam()
    assert isinstance(bp, BindParameter)
    assert isinstance(bp.type, Integer)


def test_prior_season_null_week_cap_sql_is_typed() -> None:
    """The live remat path calls these with week_cap=None before packaged EPA."""
    session = _CaptureSession()
    _fetch_rolling_feature_latest_rows(session, seasons=[2025], week_cap=None)
    _fetch_st_kav_by_team_season(session, seasons=[2025], week_cap=None)
    assert len(session.calls) == 2
    for stmt, params in session.calls:
        sql = str(stmt)
        assert "CAST(:week_cap AS int) IS NULL" in sql
        assert "week <= CAST(:week_cap AS int)" in sql
        assert UNTYPED_WEEK_CAP not in sql
        assert params["week_cap"] is None
        assert params["seasons"] == [2025]
        binds = {b.key: b for b in stmt._bindparams.values()}  # type: ignore[attr-defined]
        assert "week_cap" in binds
        assert isinstance(binds["week_cap"].type, Integer)


def test_fail_closed_overlay_defaults_unchanged() -> None:
    remat = inspect.signature(run_nfl_market_simulations).parameters
    assert remat["force_overlays_off"].default is True
    assert remat["prefer_packaged_epa"].default is True
    assert remat["unlock_overlays"].default is False
    job = inspect.signature(job_run_nfl_simulations).parameters
    assert job["force_overlays_off"].default.default is True
    assert job["prefer_packaged_epa"].default.default is True
    assert job["unlock_overlays"].default.default is False


def _local_postgres_url() -> Optional[str]:
    for key in ("MIG_TEST_DATABASE_URL", "KOSEDGE_MIG_TEST_DATABASE_URL", "DATABASE_URL"):
        raw = (os.environ.get(key) or "").strip()
        if raw and any(h in raw for h in ("localhost", "127.0.0.1", "@postgres:")):
            return raw
    return None


def _t08_blocker(*, url: Optional[str], error: Optional[BaseException]) -> str:
    err = (
        f"{type(error).__name__}: {error}"
        if error is not None
        else "no local DSN (MIG_TEST_DATABASE_URL / DATABASE_URL localhost)"
    )
    return (
        "T-08 BLOCKED_WITH_REPRO: Postgres proof did not run.\n"
        f"tried_url={url!r}\n"
        f"error={err}\n"
        "repro:\n"
        "  sudo pg_ctlcluster 16 main start   # or: docker run -d --name migtest "
        "-e POSTGRES_USER=migtest -e POSTGRES_PASSWORD=migtest "
        "-e POSTGRES_DB=migtest -p 5432:5432 postgres:16\n"
        "  sudo -u postgres psql -c \"CREATE ROLE migtest LOGIN PASSWORD 'migtest' SUPERUSER;\" || true\n"
        "  sudo -u postgres createdb -O migtest migtest || true\n"
        "  cd services/model-service && "
        "MIG_TEST_DATABASE_URL=postgresql://migtest:migtest@127.0.0.1:5432/migtest "
        "pytest -rs -v tests/test_nfl_week_cap_bind.py\n"
        "minimal_infra_ask: postgres:16 on 127.0.0.1:5432 user/db/password=migtest "
        "(same as .github/workflows/pr-check.yml services.postgres). "
        "Skip is not evidence. Set T08_ALLOW_SKIP=1 only for an explicit local opt-out."
    )


def _can_connect(url: str) -> Tuple[bool, Optional[BaseException]]:
    try:
        import psycopg

        with psycopg.connect(url, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, exc


def test_untyped_null_week_bind_raises_ambiguous_parameter() -> None:
    """Proof: the pre-fix predicate is what threw on Railway SHA 8614021."""
    try:
        import psycopg
    except ImportError as exc:
        if os.environ.get("T08_ALLOW_SKIP") == "1":
            pytest.skip(_t08_blocker(url=None, error=exc))
        pytest.fail(_t08_blocker(url=None, error=exc))
    url = _local_postgres_url()
    ok, connect_err = _can_connect(url) if url else (False, None)
    if not url or not ok:
        if os.environ.get("T08_ALLOW_SKIP") == "1":
            pytest.skip(_t08_blocker(url=url, error=connect_err))
        pytest.fail(_t08_blocker(url=url, error=connect_err))

    from sqlalchemy import create_engine
    from sqlalchemy.exc import ProgrammingError

    sa_url = url
    if sa_url.startswith("postgresql://") and "+psycopg" not in sa_url:
        sa_url = sa_url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(sa_url)

    # Same shape as remat fetchers: $1 = seasons (typed list), $2 = week_cap NULL.
    untyped = text(
        """
        SELECT 1
        WHERE :seasons IS NOT NULL
          AND (:week_cap IS NULL OR 1 <= :week_cap)
        """
    )
    with engine.connect() as sa_conn:
        with pytest.raises(ProgrammingError) as ei:
            sa_conn.execute(untyped, {"seasons": [2025], "week_cap": None})
        orig = getattr(ei.value, "orig", ei.value)
        assert isinstance(orig, psycopg.errors.AmbiguousParameter)
        assert "could not determine data type of parameter" in str(orig)
        sa_conn.rollback()

    typed = text(
        f"""
        SELECT 1 AS ok
        WHERE :seasons IS NOT NULL
          AND {TYPED_WEEK_CAP.replace("week <=", "1 <=")}
        """
    ).bindparams(_week_cap_bindparam())
    with engine.connect() as sa_conn:
        got = sa_conn.execute(typed, {"seasons": [2025], "week_cap": None}).fetchone()
        assert got is not None and int(got[0]) == 1
        typed_int = sa_conn.execute(
            typed, {"seasons": [2025], "week_cap": 2}
        ).fetchone()
        assert typed_int is not None and int(typed_int[0]) == 1


def test_full_engine_input_status_ok_when_both_sides_have_epa() -> None:
    status = _full_engine_input_status(
        home_prior={"offense_index": 1.08, "defense_index": 0.97},
        away_prior={"offense_index": 1.01, "defense_index": 1.04},
        prior_source="packaged_epa_prior",
    )
    assert status == "packaged_epa_prior"
    assert status != FULL_ENGINE_INPUT_MISSING


def test_full_engine_input_status_context_fallback_not_missing() -> None:
    """Record/context indices remain a valid cold start — not invented 1.0."""
    status = _full_engine_input_status(
        home_prior={},
        away_prior={},
        context_offense_home=1.132,
        context_offense_away=0.958,
        context_defense_home=1.062,
        context_defense_away=0.958,
        prior_source="true_pr_blend",
    )
    assert status == "true_pr_blend"


def test_full_engine_input_status_explicit_missing() -> None:
    status = _full_engine_input_status(
        home_prior={},
        away_prior=None,
        context_offense_home=None,
        context_offense_away=None,
        context_defense_home=None,
        context_defense_away=None,
        prior_source="true_pr_blend",
    )
    assert status == FULL_ENGINE_INPUT_MISSING
