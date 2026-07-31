from src.services.nba_possession_simulator import (
    DEFAULT_NBA_MODEL_VERSION,
    NBA_WORKER_BUILD_ID,
    NbaGameInputs,
    PossessionEventType,
    resolve_possession,
    simulate_nba_game,
)
import random


def _base_inputs(**overrides) -> NbaGameInputs:
    base = dict(
        game_id="nba-test-1",
        home_team="Boston Celtics",
        away_team="New York Knicks",
        pace_home=102.0,
        pace_away=98.0,
        ortg_home=118.0,
        ortg_away=112.0,
        drtg_home=110.0,
        drtg_away=116.0,
    )
    base.update(overrides)
    return NbaGameInputs(**base)


def test_simulate_nba_game_outputs_expected_shape() -> None:
    out = simulate_nba_game(_base_inputs(), simulations=1500, seed=42)
    markets = out["markets"]
    assert out["game_id"] == "nba-test-1"
    assert out["model_version"] == DEFAULT_NBA_MODEL_VERSION
    assert out["worker_build_id"] == NBA_WORKER_BUILD_ID
    assert 0.0 <= markets["home_win_prob"] <= 1.0
    # Pace≈100/team → regulation totals should land in a real NBA band.
    assert 190.0 <= markets["total_mean"] <= 260.0
    assert isinstance(markets["fair_home_ml"], int)
    assert isinstance(markets["fair_away_ml"], int)
    assert markets["total_p10"] <= markets["total_p50"] <= markets["total_p90"]
    assert markets["fair_spread_home"] is not None
    assert abs(float(markets["fair_spread_home"])) >= 0.5
    assert 0.0 <= float(markets["home_cover_prob"]) <= 1.0
    assert out["diagnostics"]["simulator_type"] == "possession_monte_carlo"
    assert out["diagnostics"]["event_interface_version"] == "nba-pbp-events-v1"


def test_simulate_nba_game_is_deterministic_with_seed() -> None:
    params = _base_inputs(game_id="nba-test-2")
    a = simulate_nba_game(params, simulations=1200, seed=11)
    b = simulate_nba_game(params, simulations=1200, seed=11)
    assert a["markets"] == b["markets"]


def test_stronger_home_offense_raises_home_win_prob() -> None:
    weak = _base_inputs(ortg_home=108.0, ortg_away=114.0, drtg_home=114.0, drtg_away=114.0)
    strong = _base_inputs(ortg_home=124.0, ortg_away=114.0, drtg_home=114.0, drtg_away=114.0)
    a = simulate_nba_game(weak, simulations=2500, seed=7)
    b = simulate_nba_game(strong, simulations=2500, seed=7)
    assert b["markets"]["home_win_prob"] > a["markets"]["home_win_prob"]
    assert b["markets"]["margin_mean"] > a["markets"]["margin_mean"]


def test_higher_pace_raises_total() -> None:
    slow = _base_inputs(pace_home=92.0, pace_away=92.0)
    fast = _base_inputs(pace_home=108.0, pace_away=108.0)
    a = simulate_nba_game(slow, simulations=2000, seed=19)
    b = simulate_nba_game(fast, simulations=2000, seed=19)
    assert b["markets"]["raw_total_mean"] > a["markets"]["raw_total_mean"]


def test_market_blend_pulls_toward_consensus() -> None:
    raw = _base_inputs(ortg_home=125.0, ortg_away=105.0, sample_games_home=5, sample_games_away=5)
    blended = _base_inputs(
        ortg_home=125.0,
        ortg_away=105.0,
        sample_games_home=5,
        sample_games_away=5,
        market_spread_home=-3.5,
        market_total=224.5,
    )
    a = simulate_nba_game(raw, simulations=1800, seed=3)
    b = simulate_nba_game(blended, simulations=1800, seed=3)
    # Blended fair spread should be closer to -3.5 than raw.
    assert abs(b["markets"]["fair_spread_home"] - (-3.5)) < abs(
        a["markets"]["fair_spread_home"] - (-3.5)
    )
    assert b["diagnostics"]["market_blend"]["applied_spread"] is True
    assert b["diagnostics"]["market_blend"]["applied_total"] is True


def test_possession_emits_typed_events() -> None:
    rng = random.Random(99)
    outcome = resolve_possession(
        rng,
        offense="home",
        inputs=_base_inputs(),
        collect_events=True,
    )
    assert "points" in outcome
    assert outcome["events"]
    types = {e["event_type"] for e in outcome["events"]}
    assert PossessionEventType.POSSESSION_END.value in types


def test_event_sample_on_full_sim() -> None:
    out = simulate_nba_game(
        _base_inputs(),
        simulations=400,
        seed=5,
        collect_event_sample=True,
    )
    assert isinstance(out["event_sample"], list)
    assert len(out["event_sample"]) > 0
