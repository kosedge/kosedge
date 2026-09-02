import os
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src import tasks
from src.services import nfl_player_identity as identity


def test_resolver_rule_order_prefers_external_id(monkeypatch) -> None:
    monkeypatch.setattr(identity, "_select_external_id_match", lambda *_args, **_kwargs: {"player_uid": "uid-ext", "confidence": 1.0, "trusted_link": True})
    monkeypatch.setattr(identity, "_select_exact_alias_candidates", lambda *_args, **_kwargs: [{"player_uid": "uid-alias"}])
    monkeypatch.setattr(identity, "_select_fuzzy_candidates", lambda *_args, **_kwargs: [{"player_uid": "uid-fuzzy", "normalized_alias": "josh allen"}])

    result = identity.resolve_player_identity(
        session=object(),
        payload=identity.IdentityInput(
            source_system="nfl_dp",
            external_id="123",
            player_name="Josh Allen",
            team="BUF",
            position="QB",
            season=2026,
            week=1,
        ),
    )

    assert result.status == "mapped"
    assert result.rule_used == "exact_external_id"
    assert result.player_uid == "uid-ext"


def test_resolver_threshold_behavior_unresolved_when_fuzzy_below_threshold(monkeypatch) -> None:
    monkeypatch.setattr(identity, "_select_external_id_match", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(identity, "_select_exact_alias_candidates", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        identity,
        "_select_fuzzy_candidates",
        lambda *_args, **_kwargs: [
            {"player_uid": "uid-1", "normalized_alias": "sam howel"},
            {"player_uid": "uid-2", "normalized_alias": "sam howard"},
        ],
    )
    monkeypatch.setattr(identity, "FUZZY_MIN_SCORE", 0.95)

    result = identity.resolve_player_identity(
        session=object(),
        payload=identity.IdentityInput(
            source_system="odds_api_nfl_props",
            external_id=None,
            player_name="Sam Howell",
            team="SEA",
            position="QB",
            season=2026,
            week=1,
        ),
    )

    assert result.status in {"unresolved", "conflict"}
    assert result.rule_used in {"fuzzy_name_below_threshold", "fuzzy_name_ambiguous"}


def test_resolver_conflict_detection_from_exact_candidates(monkeypatch) -> None:
    monkeypatch.setattr(identity, "_select_external_id_match", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        identity,
        "_select_exact_alias_candidates",
        lambda *_args, **_kwargs: [{"player_uid": "uid-1"}, {"player_uid": "uid-2"}],
    )
    monkeypatch.setattr(identity, "_select_fuzzy_candidates", lambda *_args, **_kwargs: [])

    result = identity.resolve_player_identity(
        session=object(),
        payload=identity.IdentityInput(
            source_system="odds_api_nfl_props",
            external_id=None,
            player_name="Michael Carter",
            team="NYJ",
            position="RB",
            season=2026,
            week=1,
        ),
    )

    assert result.status == "conflict"
    assert result.queue_reason == "conflict"
    assert len(result.candidate_player_uids) == 2


def test_no_silent_remap_guardrail_queues_conflict(monkeypatch) -> None:
    monkeypatch.setattr(
        identity,
        "resolve_player_identity",
        lambda *_args, **_kwargs: identity.IdentityResolution(
            status="mapped",
            player_uid="uid-new",
            confidence=0.9,
            rule_used="fuzzy_name_bounded_context",
            resolver_version=identity.DEFAULT_RESOLVER_VERSION,
            normalized_name="patrick mahomes",
            candidate_player_uids=["uid-new"],
            explanation={},
        ),
    )
    monkeypatch.setattr(
        identity,
        "_select_external_id_match",
        lambda *_args, **_kwargs: {"player_uid": "uid-trusted", "confidence": 0.99, "trusted_link": True},
    )
    monkeypatch.setattr(identity, "persist_mapping_event", lambda *_args, **_kwargs: "event-1")
    queued = []
    monkeypatch.setattr(identity, "queue_mapping_review", lambda *_args, **_kwargs: queued.append(True))

    result = identity.resolve_and_persist_player_identity(
        session=object(),
        payload=identity.IdentityInput(
            source_system="nfl_dp",
            external_id="pm-15",
            player_name="Patrick Mahomes",
            team="KC",
            position="QB",
            season=2026,
            week=1,
        ),
    )

    assert result.status == "conflict"
    assert result.rule_used == "guardrail_trusted_link_no_silent_remap"
    assert len(queued) == 1


class _PropsSession:
    def __init__(self):
        self.inserts = []
        self.deletes = []
        self.committed = False

    def execute(self, sql, params=None):
        query = str(sql)
        if "SELECT COALESCE(MAX(week), 1)::int AS week" in query:
            return _Result(row=(1,))
        if "FROM nfl_player_projection_features_weekly" in query and "role_confidence" in query:
            return _Result(rows=[])
        if "FROM nfl_dp_depth_chart_weekly" in query:
            return _Result(rows=[])
        if "FROM nfl_player_game_box_score_sims" in query:
            return _Result(rows=[])
        if "FROM nfl_player_projection_baselines" in query and "model_version" in query:
            row = SimpleNamespace(
                season=2026,
                week=1,
                team="BUF",
                player_id="p-1",
                player_uid=None,
                player_name="Player A",
                position="WR",
                game_id=None,
                pass_yards_mean=0.0,
                pass_yards_std=3.0,
                rush_yards_mean=15.0,
                rush_yards_std=7.0,
                receiving_yards_mean=82.0,
                receiving_yards_std=18.0,
                receptions_mean=6.0,
                receptions_std=2.0,
                anytime_td_prob=0.41,
            )
            return _Result(rows=[row])
        if "FROM nfl_player_prop_market_snapshots" in query and "SELECT DISTINCT ON" in query:
            row = SimpleNamespace(
                id="snap-1",
                season=2026,
                week=1,
                game_id=None,
                player_id="p-1",
                player_uid="uid-player-a",
                player_name="Player A",
                team="BUF",
                sportsbook="draftkings",
                market_key="rec_yds",
                line=71.5,
                over_price=-110,
                under_price=-110,
                captured_at=None,
            )
            return _Result(rows=[row])
        if "UPDATE nfl_player_projection_baselines" in query:
            return _Result()
        if "DELETE FROM nfl_player_prop_model_edges" in query:
            self.deletes.append(dict(params or {}))
            return _Result(rowcount=0)
        if "INSERT INTO nfl_player_prop_model_edges" in query:
            self.inserts.append(dict(params or {}))
            return _Result()
        if "INSERT INTO nfl_projection_audit_runs" in query:
            return _Result()
        raise AssertionError(f"Unexpected SQL in props integration test: {query}")

    def commit(self):
        self.committed = True

    def rollback(self):
        return None

    def close(self):
        return None


class _Result:
    def __init__(self, rows=None, row=None, rowcount=0):
        self._rows = rows or []
        self._row = row
        self.rowcount = rowcount

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._row


def test_prop_player_match_keys_bridge_abbrev_and_full_names() -> None:
    abbrev_keys = identity.prop_player_match_keys(player_uid="uid-1", player_name="D.Maye")
    full_keys = identity.prop_player_match_keys(player_uid=None, player_name="Drake Maye")
    assert "uid:uid-1" in abbrev_keys
    assert "il:d maye" in abbrev_keys
    assert "il:d maye" in full_keys
    assert "name:drake maye" in full_keys
    assert set(abbrev_keys) & set(full_keys) == {"il:d maye"}


def test_select_prop_market_blocks_ambiguous_il_cross_team() -> None:
    """Javonte Williams rush must not attach to Jameson Williams (DET WR)."""
    javonte = SimpleNamespace(
        player_name="Javonte Williams",
        team=None,
        sportsbook="draftkings",
        market_key="rush_yds",
        line=73.5,
        over_price=-110,
        under_price=-110,
        captured_at=None,
    )
    lookup = {
        ("il:j williams", "rush_yds"): javonte,
        ("il:j williams|DAL", "rush_yds"): javonte,
        ("name:javonte williams", "rush_yds"): javonte,
    }
    ambiguous = {"il:j williams"}
    det_wr = identity.select_prop_market_for_player(
        lookup,
        player_match_keys=identity.prop_player_match_keys(player_uid=None, player_name="J.Williams"),
        market_key="rush_yds",
        team="DET",
        position="WR",
        ambiguous_il_keys=ambiguous,
    )
    assert det_wr is None
    dal_rb = identity.select_prop_market_for_player(
        lookup,
        player_match_keys=identity.prop_player_match_keys(player_uid=None, player_name="J.Williams"),
        market_key="rush_yds",
        team="DAL",
        position="RB",
        ambiguous_il_keys=ambiguous,
    )
    assert dal_rb is javonte


def test_props_materialization_integration_uses_resolved_uid(monkeypatch) -> None:
    session = _PropsSession()
    monkeypatch.setattr(tasks, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        tasks,
        "resolve_and_persist_player_identity",
        lambda *_args, **_kwargs: SimpleNamespace(player_uid="uid-player-a"),
    )

    payload = tasks.materialize_nfl_player_props_edges(season=2026, week=1, model_version="nfl-player-v1")

    assert payload["prop_edges_upserted"] >= 1
    assert session.committed is True
    assert any(row.get("player_uid") == "uid-player-a" for row in session.inserts)


def test_props_materialization_joins_full_name_snapshot_to_abbrev_baseline(monkeypatch) -> None:
    """Odds-API full names + null uid must still attach market prices to D.Last baselines."""

    class _JoinSession(_PropsSession):
        def execute(self, sql, params=None):
            query = str(sql)
            if "FROM nfl_player_projection_features_weekly" in query and "role_confidence" in query:
                return _Result(
                    rows=[
                        SimpleNamespace(
                            player_id="p-maye",
                            team="NE",
                            position="QB",
                            role_confidence=0.85,
                            availability_confidence=0.9,
                            target_proxy=0.0,
                            rush_share=0.08,
                        )
                    ]
                )
            if "FROM nfl_dp_depth_chart_weekly" in query:
                return _Result(rows=[])
            if "FROM nfl_player_game_box_score_sims" in query:
                return _Result(rows=[])
            if "FROM nfl_player_projection_baselines" in query and "model_version" in query:
                row = SimpleNamespace(
                    season=2025,
                    week=17,
                    team="NE",
                    player_id="p-maye",
                    player_uid="uid-maye",
                    player_name="D.Maye",
                    position="QB",
                    game_id=None,
                    pass_yards_mean=240.0,
                    pass_yards_std=35.0,
                    rush_yards_mean=20.0,
                    rush_yards_std=10.0,
                    receiving_yards_mean=0.0,
                    receiving_yards_std=1.0,
                    receptions_mean=0.0,
                    receptions_std=0.5,
                    anytime_td_prob=0.22,
                )
                return _Result(rows=[row])
            if "FROM nfl_player_prop_market_snapshots" in query and "SELECT DISTINCT ON" in query:
                row = SimpleNamespace(
                    id="snap-maye",
                    season=2025,
                    week=17,
                    game_id=None,
                    player_id=None,
                    player_uid=None,
                    player_name="Drake Maye",
                    team=None,
                    sportsbook="draftkings",
                    market_key="pass_yds",
                    line=249.5,
                    over_price=-115,
                    under_price=-105,
                    captured_at=None,
                )
                return _Result(rows=[row])
            return super().execute(sql, params)

    session = _JoinSession()
    monkeypatch.setattr(tasks, "SessionLocal", lambda: session)

    payload = tasks.materialize_nfl_player_props_edges(season=2025, week=17, model_version="nfl-player-v1")

    assert payload["prop_edges_upserted"] >= 1
    pass_yds = [row for row in session.inserts if row.get("market_key") == "pass_yds"]
    assert pass_yds
    assert pass_yds[0]["market_over_price"] == -115
    assert pass_yds[0]["market_under_price"] == -105
    assert pass_yds[0]["edge_over"] is not None
    assert pass_yds[0]["line"] == 249.5


class _QualitySession:
    def __init__(self):
        self.calls = 0

    def execute(self, _sql, _params=None):
        self.calls += 1
        if self.calls == 1:
            return _Result(
                row=SimpleNamespace(
                    total_events=100,
                    mapped_events=92,
                    high_conf_mapped=76,
                    unresolved_events=6,
                    conflict_events=2,
                )
            )
        if self.calls == 2:
            return _Result(row=SimpleNamespace(remap_count=3, reversal_count=1))
        if self.calls == 3:
            return _Result(row=SimpleNamespace(source_freshness_hours=5.5))
        raise AssertionError("Unexpected quality snapshot call count")


def test_quality_snapshot_metric_calculation() -> None:
    payload = identity.compute_identity_quality_snapshot(
        _QualitySession(),
        season=2026,
        week=1,
        source_system="odds_api_nfl_props",
    )
    assert payload["coverage_rate"] == 0.92
    assert payload["high_confidence_auto_map_rate"] == 0.76
    assert payload["unresolved_rate"] == 0.06
    assert payload["conflict_rate"] == 0.02
    assert payload["remap_count"] == 3
