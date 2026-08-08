import os
from collections import namedtuple
from datetime import date, datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src import tasks
from src.tasks import _box_score_replicate_seed


class _Result:
    def __init__(self, rows=None, row=None):
        self._rows = rows or []
        self._row = row

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._row


class _Session:
    def __init__(self, rows):
        self.rows = rows
        self.inserts = []
        self.committed = False
        self.closed = False

    def execute(self, sql, params=None):
        query = str(sql)
        if "SELECT" in query and "FROM games g" in query and "nfl_dp_schedules" in query:
            return _Result(rows=self.rows)
        if "INSERT INTO nfl_market_outcomes" in query:
            self.inserts.append(dict(params or {}))
            return _Result()
        raise AssertionError(f"Unexpected SQL in test: {query}")

    def commit(self):
        self.committed = True

    def rollback(self):
        return None

    def close(self):
        self.closed = True


def test_pull_nfl_outcomes_upserts_and_is_repeatable(monkeypatch) -> None:
    row = namedtuple(
        "Row",
        [
            "game_id",
            "external_id",
            "game_status",
            "game_date",
            "start_time",
            "home_score",
            "away_score",
            "schedule_updated_at",
        ],
    )(
        game_id="game-1",
        external_id="401547001",
        game_status="final",
        game_date="2026-09-11",
        start_time=None,
        home_score=27,
        away_score=21,
        schedule_updated_at=datetime(2026, 9, 11, 4, 0, tzinfo=timezone.utc),
    )

    session_1 = _Session(rows=[row])
    session_2 = _Session(rows=[row])
    sessions = [session_1, session_2]
    monkeypatch.setattr(tasks, "SessionLocal", lambda: sessions.pop(0))
    monkeypatch.setattr(tasks, "fetch_nfl_schedule", lambda *_args, **_kwargs: [])

    first = tasks.pull_nfl_outcomes(days_back=14)
    second = tasks.pull_nfl_outcomes(days_back=14)

    assert first["outcomes_upserted"] == 1
    assert second["outcomes_upserted"] == 1
    assert session_1.inserts[0]["final_total_points"] == 48
    assert session_1.inserts[0]["home_team_won"] is True
    assert session_1.inserts[0]["source"] == "nfl-dp-schedules"
    assert session_1.committed is True
    assert session_2.committed is True


def test_compute_nfl_quality_payload_metrics() -> None:
    payload = tasks._compute_nfl_quality_payload(
        point_rows=[
            {
                "home_win_prob": 0.7,
                "home_team_won": True,
                "total_mean": 46.0,
                "final_total_points": 49,
                "game_date": "2026-10-10",
            },
            {
                "home_win_prob": 0.4,
                "home_team_won": False,
                "total_mean": 43.0,
                "final_total_points": 41,
                "game_date": "2026-10-11",
            },
        ],
        clv_rollup={"sample_size": 4, "avg_clv": 0.025, "positive_count": 3},
        clv_rows=[
            {"market_code": "moneyline", "recommended_side": "home", "clv_value": 0.03, "home_team_won": True},
            {"market_code": "moneyline", "recommended_side": "away", "clv_value": -0.01, "home_team_won": True},
            {
                "market_code": "total",
                "recommended_side": "over",
                "clv_value": 0.04,
                "final_total_points": 52,
                "close_line": 49.5,
                "open_line": 48.5,
            },
        ],
        model_version="nfl-v1.5-matchup-sim",
        lookback_days=60,
        totals_calibration={"slope": 1.1, "intercept": -2.0, "sample_size": 200},
    )

    assert payload["sample_size"] == 2
    assert payload["moneyline_brier"] == 0.125
    assert payload["total_mae_base"] == 2.5
    assert payload["total_mae"] == 2.35
    assert payload["clv_avg"] == 0.025
    assert payload["clv_positive_rate"] == 0.75
    assert payload["moneyline_hit_rate"] == 0.5
    assert payload["moneyline_positive_edge_hit_rate"] == 1.0
    assert payload["total_hit_rate"] == 1.0
    assert payload["total_positive_edge_hit_rate"] == 1.0
    assert payload["totals_calibration"]["sample_size"] == 200


class _BacktestSession:
    def __init__(self) -> None:
        self.inserts = []
        self.committed = False

    def execute(self, sql, params=None):
        query = str(sql)
        if "INSERT INTO nfl_model_backtest_runs" in query:
            self.inserts.append(dict(params or {}))
            return _Result()
        raise AssertionError(f"Unexpected SQL in backtest test: {query}")

    def commit(self):
        self.committed = True

    def rollback(self):
        return None

    def close(self):
        return None


def test_run_nfl_walkforward_backtest_persists_metrics(monkeypatch) -> None:
    session = _BacktestSession()
    monkeypatch.setattr(tasks, "SessionLocal", lambda: session)

    start = date(2026, 9, 1)
    points = []
    for i in range(42):
        game_date = start + timedelta(days=i)
        home_win_prob = 0.66 if i % 2 == 0 else 0.34
        home_team_won = i % 2 == 0
        total_mean = 44.0 + float(i % 6)
        final_total = total_mean + (1.5 if i % 3 == 0 else -1.0)
        points.append(
            {
                "game_id": f"g-{i}",
                "game_date": game_date.isoformat(),
                "home_win_prob": home_win_prob,
                "total_mean": total_mean,
                "home_team_won": home_team_won,
                "final_total_points": final_total,
                "projection_created_at": datetime(2026, 9, 1, tzinfo=timezone.utc),
                "outcome_completed_at": datetime(2026, 9, 2, tzinfo=timezone.utc),
            }
        )

    monkeypatch.setattr(tasks, "_fetch_nfl_backtest_points", lambda *_args, **_kwargs: points)

    payload = tasks.run_nfl_walkforward_backtest(
        model_version="nfl-v1.5-matchup-sim",
        lookback_days=180,
        training_days=21,
        step_days=7,
        apply_calibration=True,
    )

    assert payload["fold_count"] >= 1
    assert payload["sample_size"] > 0
    assert payload["base_brier_ml"] is not None
    assert payload["calibrated_brier_ml"] is not None
    assert payload["calibrated_mae_total_runs"] is not None
    assert payload["mae_improvement"] is not None
    assert payload["leakage_violations"] == 0
    assert session.committed is True
    assert len(session.inserts) == 1
    assert session.inserts[0]["model_version"] == "nfl-v1.5-matchup-sim"


def test_decide_nfl_challenger_promotion_blocks_insufficient_data() -> None:
    decision = tasks._decide_nfl_challenger_promotion(
        champion_quality={"sample_size": 60, "moneyline_brier": 0.24, "total_mae": 5.8},
        challenger_quality={"sample_size": 55, "moneyline_brier": 0.22, "total_mae": 5.5},
        champion_backtest={"sample_size": 50, "calibrated_brier_ml": 0.245, "calibrated_mae_total_runs": 5.9},
        challenger_backtest={
            "sample_size": 48,
            "brier_improvement": 0.004,
            "calibrated_brier_ml": 0.223,
            "calibrated_mae_total_runs": 5.6,
        },
        champion_clv={"avg_clv": 0.001},
        challenger_clv={"avg_clv": 0.008},
    )
    assert decision["promote"] is False
    assert decision["checks"]["sample_size_ok"] is False


def test_count_leakage_violations_requires_strict_projection_order() -> None:
    violations = tasks._count_leakage_violations(
        [
            {
                "projection_created_at": datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc),
                "outcome_completed_at": datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc),
            },
            {
                "projection_created_at": datetime(2026, 9, 10, 11, 0, tzinfo=timezone.utc),
                "outcome_completed_at": datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc),
            },
        ]
    )
    assert violations == 1


def test_run_nfl_walkforward_backtest_excludes_ineligible_points(monkeypatch) -> None:
    session = _BacktestSession()
    monkeypatch.setattr(tasks, "SessionLocal", lambda: session)

    start = date(2026, 9, 1)
    points = []
    for i in range(49):
        game_date = start + timedelta(days=i)
        outcome_at = datetime.combine(game_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=20)
        if i < 35:
            projection_at = outcome_at - timedelta(hours=2)
        else:
            projection_at = outcome_at + timedelta(hours=1)

        points.append(
            {
                "game_id": f"mixed-{i}",
                "game_date": game_date.isoformat(),
                "home_win_prob": 0.61 if i % 2 == 0 else 0.39,
                "total_mean": 44.0 + float(i % 5),
                "home_team_won": i % 2 == 0,
                "final_total_points": 45.5 + float((i + 1) % 5),
                "projection_created_at": projection_at,
                "outcome_completed_at": outcome_at,
            }
        )

    monkeypatch.setattr(tasks, "_fetch_nfl_backtest_points", lambda *_args, **_kwargs: points)

    payload = tasks.run_nfl_walkforward_backtest(
        model_version="nfl-v1.5-matchup-sim",
        lookback_days=240,
        training_days=21,
        step_days=7,
        apply_calibration=True,
    )

    assert payload["fold_count"] >= 1
    assert payload["sample_size"] > 0
    assert payload["sample_size"] < len(points)
    assert payload["leakage_violations"] == 0


def test_box_score_replicate_seed_is_stable_across_calls() -> None:
    # Real bug found via the 2026-07-19 player-prop benchmark sample-growth
    # task: the old implementation used Python's built-in `hash()` on a
    # tuple containing a string, which is intentionally randomized
    # per-process (PYTHONHASHSEED) -- so re-materializing the same
    # season/week/team on unchanged data silently produced a DIFFERENT
    # seed (and therefore different Monte Carlo box-score distributions)
    # every run, discovered only because a backtest re-run on identical
    # input games produced different win rates. The fix must be provably
    # stable, not just "probably fine now."
    first = _box_score_replicate_seed(2026, 1, "KC")
    second = _box_score_replicate_seed(2026, 1, "KC")
    assert first == second
    assert isinstance(first, int)
    assert 0 <= first < 2**31


def test_box_score_replicate_seed_varies_by_inputs() -> None:
    seeds = {
        _box_score_replicate_seed(2026, 1, "KC"),
        _box_score_replicate_seed(2026, 2, "KC"),
        _box_score_replicate_seed(2026, 1, "BUF"),
        _box_score_replicate_seed(2025, 1, "KC"),
    }
    assert len(seeds) == 4


def test_resolve_nfl_projection_created_at_kickoff_minus_buffer() -> None:
    kickoff = datetime(2026, 9, 10, 20, 20, tzinfo=timezone.utc)
    created_at = tasks._resolve_nfl_projection_created_at(
        game_date=date(2026, 9, 10),
        start_time=kickoff,
        mode="kickoff_minus_buffer",
        kickoff_buffer_minutes=30,
    )
    assert created_at == datetime(2026, 9, 10, 19, 50, tzinfo=timezone.utc)


def test_backfill_nfl_historical_projections_uses_kickoff_timestamp_mode(monkeypatch) -> None:
    calls = []

    def _fake_run_nfl_market_simulations(**kwargs):
        calls.append(kwargs)
        return {"games_processed": 2, "projections_inserted": 2}

    monkeypatch.setattr(tasks, "run_nfl_market_simulations", _fake_run_nfl_market_simulations)

    payload = tasks.backfill_nfl_historical_projections(
        start_date="2026-09-10",
        end_date="2026-09-12",
        simulations=3000,
        model_version="nfl-v1.5-matchup-sim",
        kickoff_buffer_minutes=45,
    )

    assert payload["days_processed"] == 3
    assert payload["games_processed"] == 6
    assert payload["projections_inserted"] == 6
    assert payload["projection_created_at_mode"] == "kickoff_minus_buffer"
    assert payload["include_completed_games"] is True
    assert len(calls) == 3
    assert all(call.get("include_completed_games") is True for call in calls)
    assert all(call.get("projection_created_at_mode") == "kickoff_minus_buffer" for call in calls)
    assert all(call.get("kickoff_buffer_minutes") == 45 for call in calls)


def test_resolve_team_strength_indices_prefers_real_epa_prior_over_record() -> None:
    """Real bug found via the team-simulator calibration audit (see
    data/ops/nfl-team-simulator-calibration-audit-report.md): this used to
    prefer the cruder win/loss-record-derived index over the real,
    backtest-validated EPA-based rolling-feature prior whenever the record
    was non-degenerate (i.e. for the entire season past week 1). A real
    mid-season team with a real winning record but real rolling EPA data
    available must resolve to the EPA prior, not the record-based value."""
    offense_home, offense_away, defense_home, defense_away = tasks._resolve_team_strength_indices(
        base_offense_home=1.132,  # team_strength_from_record("11-6") -> real, non-degenerate
        base_offense_away=0.958,  # team_strength_from_record("3-14") -> real, non-degenerate
        base_defense_home=1.062,
        base_defense_away=0.958,
        home_prior={"offense_index": 1.081, "defense_index": 1.045, "_season": 2025.0},
        away_prior={"offense_index": 0.912, "defense_index": 0.936, "_season": 2025.0},
    )
    assert offense_home == 1.081
    assert offense_away == 0.912
    assert defense_home == 1.045
    assert defense_away == 0.936


def test_resolve_team_strength_indices_falls_back_to_record_on_genuine_cold_start() -> None:
    """When there is truly no EPA rolling-feature prior for a team/season
    (e.g. a brand-new franchise relocation with no prior-season row either),
    the record-based estimate remains a valid fallback -- this is the one
    real case the original fallback design was meant to cover."""
    offense_home, offense_away, defense_home, defense_away = tasks._resolve_team_strength_indices(
        base_offense_home=1.132,
        base_offense_away=1.0,
        base_defense_home=1.062,
        base_defense_away=1.0,
        home_prior={},
        away_prior={},
    )
    assert offense_home == 1.132
    assert offense_away == 1.0
    assert defense_home == 1.062
    assert defense_away == 1.0


def test_priors_from_matchup_pack_aligns_base_strength_to_week_epa() -> None:
    """Residual DAL@NYG failure mode after supervised skip: season-max-week
    hydrated priors fought the Week-1 matchup pack. Pack-derived indices must
    prefer the away club when pack EPA clearly favors them."""
    pack = {
        "season": 2026,
        "week": 1,
        "home_off_epa_5g": -0.05165,
        "away_off_epa_5g": 0.03415,
        "home_def_epa_allowed_5g": 0.07218,
        "away_def_epa_allowed_5g": 0.07718,
        "home_pressure_generated_5g": 0.1694,
        "away_pressure_generated_5g": 0.1775,
        "home_pressure_allowed_5g": 0.2068,
        "away_pressure_allowed_5g": 0.1393,
    }
    priors = tasks._priors_from_matchup_pack(pack)
    assert priors is not None
    home_prior, away_prior = priors
    # Away offense stronger; home allows much more pressure → away should be
    # the stronger club on offense index.
    assert away_prior["offense_index"] > home_prior["offense_index"]
    assert home_prior["_week"] == 1.0


def test_load_team_strength_priors_uses_prior_season_when_unplayed(monkeypatch) -> None:
    """On a not-yet-played season, week DESC against the hydrated grid would
    pick week-18 carry-forward. Force prior-season latest week instead."""
    Row = namedtuple(
        "Row",
        "season week team off_epa_per_play_5g def_epa_allowed_per_play_5g "
        "pressure_rate_generated_5g pressure_rate_allowed_5g "
        "pass_rate_5g success_rate_offense_5g success_rate_defense_allowed_5g "
        "red_zone_td_rate_5g games_in_window_5",
    )

    class _ScalarResult(_Result):
        def scalar(self):
            if self._row is not None and hasattr(self._row, "n"):
                return self._row.n
            return 0

    class _FakeSession:
        def __init__(self):
            self.queries = []

        def execute(self, sql, params=None):
            query = str(sql)
            params = dict(params or {})
            self.queries.append((query, params))
            if "COUNT(*)" in query and "nfl_dp_schedules" in query and "UNION ALL" not in query:
                return _ScalarResult(row=namedtuple("C", "n")(n=0))
            if "UNION ALL" in query and "nfl_dp_schedules" in query:
                # Per-team completed games — empty preseason.
                return _Result(rows=[])
            if "nfl_dp_team_st_kav_weekly" in query:
                return _Result(rows=[])
            if "nfl_dp_team_rolling_features_weekly" in query:
                # Only prior season should be requested when unplayed.
                assert params["seasons"] == [2025]
                return _Result(
                    rows=[
                        Row(
                            2025, 18, "NYG", -0.05, 0.07, 0.17, 0.20,
                            0.58, 0.42, 0.46, 0.50, 5,
                        ),
                        Row(
                            2025, 18, "DAL", 0.03, 0.08, 0.18, 0.14,
                            0.58, 0.46, 0.44, 0.55, 5,
                        ),
                    ]
                )
            raise AssertionError(f"Unexpected SQL: {query}")

    session = _FakeSession()
    # Avoid packaged fill expanding to 32 teams in this unit test.
    monkeypatch.setattr(
        "src.services.nfl_season_engine.loaders.load_packaged_epa_priors",
        lambda season: ({}, {}),
    )
    out = tasks._load_team_strength_priors(session, season_year=2026, as_of_week=1)
    assert "NYG" in out and "DAL" in out
    assert out["DAL"]["offense_index"] > out["NYG"]["offense_index"]
    assert out["NYG"]["_season"] == 2025.0
    assert out["NYG"]["blend_current_weight"] == 0.0
    assert out["NYG"]["blend_prior_weight"] == 1.0
    assert out["NYG"]["variance"] >= 1.2  # wide early — not tightened by completed_reg


def test_fetch_nfl_market_consensus_lines_passes_team_date_fallback_params() -> None:
    """Odds may live on a parallel games UUID; fetch must pass team/date fallback."""

    class _FakeSession:
        def __init__(self):
            self.params = None

        def execute(self, sql, params=None):
            self.params = dict(params or {})
            query = str(sql)
            assert "candidate_games" in query
            assert "game_date" in query
            Row = namedtuple("Row", "market_spread_home market_total")
            return _Result(row=Row(market_spread_home=2.5, market_total=48.0))

    session = _FakeSession()
    out = tasks._fetch_nfl_market_consensus_lines(
        session,
        game_id="c1df8ae6-458e-4b33-9805-94c5fd3436c7",
        home_abbr="NYG",
        away_abbr="DAL",
        home_team="New York Giants",
        away_team="Dallas Cowboys",
        game_date=date(2026, 9, 13),
    )
    assert out["market_spread_home"] == 2.5
    assert out["market_total"] == 48.0
    assert session.params["home_abbr"] == "NYG"
    assert session.params["away_abbr"] == "DAL"
    assert session.params["game_date"] == date(2026, 9, 13)
