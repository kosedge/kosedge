"""Stale QB ATD rows must clear when rush-only remat fails investable floor.

PR 401 mapped Anytime TD → rush TDs only for QBs. Remat that skips upsert on
``is_investable_prop`` must DELETE the prior pass-TD-inflated edge so Edges no
longer serves 0.8–0.9 Overs. Do not lower floors.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src import tasks
from src.services.nfl_prop_edge_policy import anytime_td_prob_from_td_mean
from src.services.nfl_props_eligibility import filter_investable_rows, is_investable_prop


class _Result:
    def __init__(self, rows=None, row=None, rowcount=0):
        self._rows = rows or []
        self._row = row
        self.rowcount = rowcount

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._row


def _qb_baseline(
    *,
    player_id: str,
    player_name: str,
    team: str,
    rush_tds_mean: float,
    pass_yards_mean: float = 250.0,
    rush_yards_mean: float = 12.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        season=2026,
        week=1,
        team=team,
        player_id=player_id,
        player_uid=f"uid-{player_id}",
        player_name=player_name,
        position="QB",
        game_id=None,
        pass_yards_mean=pass_yards_mean,
        pass_yards_std=35.0,
        rush_yards_mean=rush_yards_mean,
        rush_yards_std=8.0,
        receiving_yards_mean=0.0,
        receiving_yards_std=1.0,
        receptions_mean=0.0,
        receptions_std=0.5,
        pass_tds_mean=1.8,
        rush_tds_mean=rush_tds_mean,
        rec_tds_mean=0.0,
        total_tds_mean=1.8 + rush_tds_mean,
        anytime_td_prob=anytime_td_prob_from_td_mean(rush_tds_mean),
    )


def _feature(player_id: str, team: str, role_confidence: float = 0.85) -> SimpleNamespace:
    return SimpleNamespace(
        player_id=player_id,
        team=team,
        position="QB",
        role_confidence=role_confidence,
        availability_confidence=0.9,
        target_proxy=0.0,
        rush_share=0.05,
    )


class _ClearSession:
    """Tracks edge upserts/deletes; seeds pretend prior ATD rows via rowcount."""

    def __init__(self, baselines, features, *, prior_atd_players: set[str]):
        self.baselines = baselines
        self.features = features
        self.prior_atd_players = prior_atd_players
        self.inserts: list[dict] = []
        self.deletes: list[dict] = []
        self.committed = False
        # Simulate DB state for investable Over checks after remat.
        self.edge_rows: dict[tuple[str, str], dict] = {}
        for name in prior_atd_players:
            # Stale pass-TD-in-ATD row (pre-PR-401 / pre-rush-only).
            self.edge_rows[(name, "anytime_td")] = {
                "market_key": "anytime_td",
                "player_name": name,
                "model_mean": 0.9,
                "line": 0.5,
                "confidence": 0.7,
                "market_over_price": -110,
                "diagnostics": {"position": "QB", "role_confidence": 0.85},
            }

    def execute(self, sql, params=None):
        query = str(sql)
        params = dict(params or {})
        if "SELECT COALESCE(MAX(week), 1)::int AS week" in query:
            return _Result(row=(1,))
        if "FROM nfl_player_projection_features_weekly" in query and "role_confidence" in query:
            return _Result(rows=self.features)
        if "FROM nfl_dp_depth_chart_weekly" in query:
            return _Result(rows=[])
        if "FROM nfl_player_game_box_score_sims" in query:
            return _Result(rows=[])
        if "FROM nfl_player_projection_baselines" in query and "model_version" in query:
            return _Result(rows=self.baselines)
        if "FROM nfl_player_prop_market_snapshots" in query and "SELECT DISTINCT ON" in query:
            return _Result(rows=[])
        if "DELETE FROM nfl_player_prop_model_edges" in query:
            self.deletes.append(params)
            key = (str(params.get("player_name")), str(params.get("market_key")))
            existed = 1 if key in self.edge_rows else 0
            self.edge_rows.pop(key, None)
            return _Result(rowcount=existed)
        if "INSERT INTO nfl_player_prop_model_edges" in query:
            self.inserts.append(params)
            key = (str(params.get("player_name")), str(params.get("market_key")))
            self.edge_rows[key] = {
                "market_key": params.get("market_key"),
                "player_name": params.get("player_name"),
                "model_mean": params.get("model_mean"),
                "line": params.get("line"),
                "confidence": params.get("confidence"),
                "market_over_price": params.get("market_over_price"),
                "diagnostics": {
                    "position": "QB",
                    "role_confidence": 0.85,
                },
            }
            return _Result()
        if "INSERT INTO nfl_projection_audit_runs" in query:
            return _Result()
        raise AssertionError(f"Unexpected SQL in stale ATD clear test: {query}")

    def commit(self):
        self.committed = True

    def rollback(self):
        return None

    def close(self):
        return None


def test_subfloor_rush_only_atd_deletes_stale_inflated_row(monkeypatch) -> None:
    """Stafford-class: new rush-only ATD under floor → prior 0.9 gone; pass_yds upserts."""
    stafford = _qb_baseline(
        player_id="p-stafford",
        player_name="M.Stafford",
        team="LA",
        rush_tds_mean=0.05,  # ~0.049 ATD prob — under starter floor 0.06
        pass_yards_mean=262.5,
        rush_yards_mean=8.0,
    )
    new_atd = anytime_td_prob_from_td_mean(0.05)
    assert new_atd < 0.06
    assert not is_investable_prop(
        market_key="anytime_td",
        position="QB",
        model_mean=new_atd,
        role_confidence=0.85,
    )

    session = _ClearSession(
        baselines=[stafford],
        features=[_feature("p-stafford", "LA")],
        prior_atd_players={"M.Stafford"},
    )
    monkeypatch.setattr(tasks, "SessionLocal", lambda: session)

    payload = tasks.materialize_nfl_player_props_edges(
        season=2026, week=1, model_version="nfl-player-v1"
    )

    assert session.committed is True
    atd_deletes = [d for d in session.deletes if d.get("market_key") == "anytime_td"]
    assert len(atd_deletes) == 1
    assert atd_deletes[0]["player_name"] == "M.Stafford"
    assert ("M.Stafford", "anytime_td") not in session.edge_rows

    atd_inserts = [r for r in session.inserts if r.get("market_key") == "anytime_td"]
    assert atd_inserts == []

    pass_yds = [r for r in session.inserts if r.get("market_key") == "pass_yds"]
    assert len(pass_yds) == 1
    assert abs(float(pass_yds[0]["model_mean"]) - 262.5) < 1e-6
    assert ("M.Stafford", "pass_yds") in session.edge_rows

    # Live Edges/board would not return the stale Over after clear.
    kept, _ = filter_investable_rows(list(session.edge_rows.values()))
    assert not any(r.get("market_key") == "anytime_td" for r in kept)
    assert payload["prop_edges_cleared_non_investable"] >= 1


def test_abovefloor_rush_atd_still_upserts(monkeypatch) -> None:
    """Maye/Nix-class: rush-only ATD clears floor → upsert, no delete of ATD."""
    maye = _qb_baseline(
        player_id="p-maye",
        player_name="D.Maye",
        team="NE",
        rush_tds_mean=0.35,  # ~0.295 — above floor
        pass_yards_mean=230.0,
        rush_yards_mean=28.0,
    )
    new_atd = anytime_td_prob_from_td_mean(0.35)
    assert is_investable_prop(
        market_key="anytime_td",
        position="QB",
        model_mean=new_atd,
        role_confidence=0.85,
    )

    session = _ClearSession(
        baselines=[maye],
        features=[_feature("p-maye", "NE")],
        prior_atd_players={"D.Maye"},
    )
    monkeypatch.setattr(tasks, "SessionLocal", lambda: session)

    payload = tasks.materialize_nfl_player_props_edges(
        season=2026, week=1, model_version="nfl-player-v1"
    )

    atd_deletes = [d for d in session.deletes if d.get("market_key") == "anytime_td"]
    assert atd_deletes == []

    atd_inserts = [r for r in session.inserts if r.get("market_key") == "anytime_td"]
    assert len(atd_inserts) == 1
    assert abs(float(atd_inserts[0]["model_mean"]) - new_atd) < 1e-6
    assert float(atd_inserts[0]["model_mean"]) < 0.5  # not the stale 0.9 path
    assert payload["prop_edges_upserted"] >= 1


def test_mixed_slate_clears_pocket_keeps_scrambler_and_pass_yds(monkeypatch) -> None:
    """Pocket QB clears stale ATD; scrambler upserts; both keep pass_yds."""
    stafford = _qb_baseline(
        player_id="p-stafford",
        player_name="M.Stafford",
        team="LA",
        rush_tds_mean=0.05,
        pass_yards_mean=262.5,
    )
    maye = _qb_baseline(
        player_id="p-maye",
        player_name="D.Maye",
        team="NE",
        rush_tds_mean=0.35,
        pass_yards_mean=231.0,
        rush_yards_mean=28.0,
    )
    session = _ClearSession(
        baselines=[stafford, maye],
        features=[_feature("p-stafford", "LA"), _feature("p-maye", "NE")],
        prior_atd_players={"M.Stafford", "D.Maye"},
    )
    monkeypatch.setattr(tasks, "SessionLocal", lambda: session)

    tasks.materialize_nfl_player_props_edges(season=2026, week=1, model_version="nfl-player-v1")

    assert ("M.Stafford", "anytime_td") not in session.edge_rows
    assert ("D.Maye", "anytime_td") in session.edge_rows
    assert abs(float(session.edge_rows[("D.Maye", "anytime_td")]["model_mean"]) - anytime_td_prob_from_td_mean(0.35)) < 1e-6

    for name, expected_yds in (("M.Stafford", 262.5), ("D.Maye", 231.0)):
        row = session.edge_rows[(name, "pass_yds")]
        assert abs(float(row["model_mean"]) - expected_yds) < 1e-6

    kept, _ = filter_investable_rows(list(session.edge_rows.values()))
    atd_kept = [r for r in kept if r.get("market_key") == "anytime_td"]
    assert len(atd_kept) == 1
    assert atd_kept[0]["player_name"] == "D.Maye"
