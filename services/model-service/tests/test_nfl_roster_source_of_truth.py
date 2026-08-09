"""Enterprise roster SoT: engine reads packaged depth exclusively."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_season_engine.coaching_staff import packaged_depth_intel_rows
from src.services.nfl_season_engine.loaders import (
    NFL_TEAMS,
    ROSTER_SOURCE_PACKAGED,
    build_packaged_real_universe,
    load_packaged_depth_chart,
    load_universe_from_db,
    resolve_season_universe,
)


def _qb_depth(rows, team: str):
    return sorted(
        [r for r in rows if r["team"] == team and r["position"] == "QB"],
        key=lambda r: int(r["depth_order"]),
    )


def test_packaged_depth_sot_kyler_on_min_not_ari() -> None:
    rows, meta = load_packaged_depth_chart(2026)
    assert meta["roster_source"] == ROSTER_SOURCE_PACKAGED

    kyler = [r for r in rows if "Kyler Murray" in str(r.get("player_name") or "")]
    assert len(kyler) == 1
    assert kyler[0]["team"] == "MIN"
    assert int(kyler[0]["depth_order"]) == 1

    ari_qbs = _qb_depth(rows, "ARI")
    assert ari_qbs
    assert ari_qbs[0]["player_name"] == "Jacoby Brissett"
    assert all("Kyler" not in r["player_name"] for r in ari_qbs)

    min_qbs = _qb_depth(rows, "MIN")
    assert min_qbs[0]["player_name"] == "Kyler Murray"
    assert min_qbs[1]["player_name"] == "J.J. McCarthy"


def test_engine_universe_reads_sot_qb_assignments() -> None:
    universe = build_packaged_real_universe(2026)
    assert universe.notes.get("roster_source") == ROSTER_SOURCE_PACKAGED
    assert "packaged" in str(universe.notes.get("rosters") or "").lower()

    min_qb1 = next(
        r for r in universe.rosters["MIN"] if r.position == "QB" and r.depth_order == 1
    )
    ari_qb1 = next(
        r for r in universe.rosters["ARI"] if r.position == "QB" and r.depth_order == 1
    )
    assert min_qb1.player_name == "Kyler Murray"
    assert min_qb1.team == "MIN"
    assert ari_qb1.player_name == "Jacoby Brissett"
    assert ari_qb1.team == "ARI"
    assert not any(
        "Kyler" in r.player_name for r in universe.rosters["ARI"] if r.position == "QB"
    )


def test_resolve_season_universe_offline_uses_packaged_sot() -> None:
    universe, meta = resolve_season_universe(season=2026, demo=False, session=None)
    assert meta["roster_source"] == ROSTER_SOURCE_PACKAGED
    min_qb1 = next(
        r for r in universe.rosters["MIN"] if r.position == "QB" and r.depth_order == 1
    )
    assert min_qb1.player_name == "Kyler Murray"


def test_db_loader_prefers_packaged_sot_over_stale_weekly(monkeypatch) -> None:
    """Stale DB weekly Kyler→ARI must not win when packaged SoT exists."""

    class _Row:
        def __init__(self, mapping):
            self._mapping = mapping

        def __getattr__(self, key):
            return self._mapping[key]

    class _Result:
        def __init__(self, rows):
            self._rows = rows

        def fetchall(self):
            return self._rows

        def fetchone(self):
            return self._rows[0] if self._rows else None

        def scalar(self):
            return None

    class _Session:
        def execute(self, statement, params=None):
            sql = str(statement)
            if "nfl_dp_depth_chart_weekly" in sql and "DISTINCT ON" in sql:
                # Deliberately wrong: Kyler on ARI (pre-SoT hygiene regression).
                return _Result(
                    [
                        _Row(
                            {
                                "team": "ARI",
                                "player_name": "Kyler Murray",
                                "position": "QB",
                                "depth_order": 1,
                                "role_confidence": 0.9,
                                "player_id": "00-0035228",
                            }
                        ),
                        _Row(
                            {
                                "team": "MIN",
                                "player_name": "J.J. McCarthy",
                                "position": "QB",
                                "depth_order": 1,
                                "role_confidence": 0.9,
                                "player_id": "00-0039923",
                            }
                        ),
                    ]
                )
            return _Result([])

    import src.tasks as tasks

    def _fake_strength(_session, *, season_year, as_of_week):  # noqa: ARG001
        return {
            t: {
                "offense_index": 1.0,
                "defense_index": 1.0,
                "pace_factor": 1.0,
                "games": 0,
            }
            for t in NFL_TEAMS
        }

    monkeypatch.setattr(tasks, "_load_team_strength_priors", _fake_strength)

    universe = load_universe_from_db(_Session(), season=2026, as_of_week=1)
    assert universe.notes["roster_source"] == ROSTER_SOURCE_PACKAGED
    assert "ignored stale DB depth" in str(universe.notes.get("rosters") or "")
    min_qb1 = next(
        r for r in universe.rosters["MIN"] if r.position == "QB" and r.depth_order == 1
    )
    ari_qb1 = next(
        r for r in universe.rosters["ARI"] if r.position == "QB" and r.depth_order == 1
    )
    assert min_qb1.player_name == "Kyler Murray"
    assert ari_qb1.player_name == "Jacoby Brissett"


def test_intel_depth_matches_engine_sot() -> None:
    depth_rows, meta = packaged_depth_intel_rows(season=2026, week=1, team="MIN")
    assert meta["roster_source"] == ROSTER_SOURCE_PACKAGED
    qb1 = next(
        r for r in depth_rows if r["position"] == "QB" and int(r["depth_order"]) == 1
    )
    assert qb1["player_name"] == "Kyler Murray"

    ari_rows, _ = packaged_depth_intel_rows(season=2026, week=1, team="ARI")
    ari_qb1 = next(
        r for r in ari_rows if r["position"] == "QB" and int(r["depth_order"]) == 1
    )
    assert ari_qb1["player_name"] == "Jacoby Brissett"


def test_was_daily_intel_20260809_depth_sot() -> None:
    """WAS camp flashpoint: Diggs WR2, Bates OUT/TE3, Sinnott TE2, OL roles."""
    rows, meta = load_packaged_depth_chart(2026)
    assert meta.get("daily_intel_as_of") == "2026-08-09"
    was = [r for r in rows if r["team"] == "WAS"]
    wr = sorted(
        [r for r in was if r["position"] == "WR"], key=lambda r: int(r["depth_order"])
    )
    te = sorted(
        [r for r in was if r["position"] == "TE"], key=lambda r: int(r["depth_order"])
    )
    assert [r["player_name"] for r in wr] == [
        "Terry McLaurin",
        "Stefon Diggs",
        "Antonio Williams",
    ]
    assert [r["player_name"] for r in te] == [
        "Chig Okonkwo",
        "Ben Sinnott",
        "John Bates",
    ]
    assert te[2].get("injury_status") == "out"

    ol = meta.get("ol_roles") or []
    was_ol = [r for r in ol if r.get("team") == "WAS"]
    assert was_ol
    tunsil = next(r for r in was_ol if r.get("player_name") == "Laremy Tunsil")
    coleman = next(r for r in was_ol if r.get("player_name") == "Brandon Coleman")
    allegretti = next(r for r in was_ol if r.get("player_name") == "Nick Allegretti")
    assert tunsil.get("injury_status") == "out"
    assert coleman.get("position") == "LT" and int(coleman.get("depth_order") or 0) == 1
    assert allegretti.get("injury_status") == "out"

    universe = build_packaged_real_universe(2026)
    assert universe.notes.get("roster_source") == ROSTER_SOURCE_PACKAGED
    was_wr2 = next(
        r
        for r in universe.rosters["WAS"]
        if r.position == "WR" and r.depth_order == 2
    )
    assert was_wr2.player_name == "Stefon Diggs"
    assert was_wr2.team == "WAS"
    # Engine must not invent OL→EPA magnitudes; hook is documented only.
    hooks = universe.notes.get("ol_efficiency_hooks") or {}
    assert hooks.get("status") == "documented_not_magical"
