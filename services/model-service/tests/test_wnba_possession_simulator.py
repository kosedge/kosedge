from src.services.wnba_possession_simulator import (
    DEFAULT_WNBA_MODEL_VERSION,
    WNBA_WORKER_BUILD_ID,
    WnbaGameInputs,
    PossessionEventType,
    harmonic_mean_pace,
    resolve_possession,
    simulate_wnba_game,
)
import random


def _base_inputs(**overrides) -> WnbaGameInputs:
    base = dict(
        game_id="wnba-test-1",
        home_team="New York Liberty",
        away_team="Las Vegas Aces",
        pace_home=83.0,
        pace_away=79.0,
        ortg_home=108.0,
        ortg_away=100.0,
        drtg_home=99.0,
        drtg_away=105.0,
    )
    base.update(overrides)
    return WnbaGameInputs(**base)


def test_harmonic_mean_pace_below_arithmetic() -> None:
    # Wide pace spread: harmonic < arithmetic (WNBA volatility lesson).
    a, b = 70.0, 95.0
    hm = harmonic_mean_pace(a, b)
    am = 0.5 * (a + b)
    assert hm < am
    assert abs(hm - (2 * a * b / (a + b))) < 1e-9


def test_simulate_wnba_game_outputs_expected_shape() -> None:
    out = simulate_wnba_game(_base_inputs(), simulations=1500, seed=42)
    markets = out["markets"]
    assert out["game_id"] == "wnba-test-1"
    assert out["model_version"] == DEFAULT_WNBA_MODEL_VERSION
    assert out["worker_build_id"] == WNBA_WORKER_BUILD_ID
    assert 0.0 <= markets["home_win_prob"] <= 1.0
    # Pace≈81/team → regulation totals should land in a real WNBA band.
    assert 130.0 <= markets["total_mean"] <= 210.0
    assert isinstance(markets["fair_home_ml"], int)
    assert isinstance(markets["fair_away_ml"], int)
    assert markets["total_p10"] <= markets["total_p50"] <= markets["total_p90"]
    assert markets["fair_spread_home"] is not None
    assert abs(float(markets["fair_spread_home"])) >= 0.5
    assert 0.0 <= float(markets["home_cover_prob"]) <= 1.0
    assert out["diagnostics"]["simulator_type"] == "possession_monte_carlo"
    assert out["diagnostics"]["event_interface_version"] == "wnba-pbp-events-v1"
    assert out["rates"]["pace_method"] == "harmonic_mean"
    assert out["rates"]["game_minutes"] == 40.0


def test_simulate_wnba_game_is_deterministic_with_seed() -> None:
    params = _base_inputs(game_id="wnba-test-2")
    a = simulate_wnba_game(params, simulations=1200, seed=11)
    b = simulate_wnba_game(params, simulations=1200, seed=11)
    assert a["markets"] == b["markets"]


def test_stronger_home_offense_raises_home_win_prob() -> None:
    weak = _base_inputs(ortg_home=96.0, ortg_away=104.0, drtg_home=104.0, drtg_away=104.0)
    strong = _base_inputs(ortg_home=112.0, ortg_away=104.0, drtg_home=104.0, drtg_away=104.0)
    a = simulate_wnba_game(weak, simulations=2500, seed=7)
    b = simulate_wnba_game(strong, simulations=2500, seed=7)
    assert b["markets"]["home_win_prob"] > a["markets"]["home_win_prob"]
    assert b["markets"]["margin_mean"] > a["markets"]["margin_mean"]


def test_higher_pace_raises_total() -> None:
    slow = _base_inputs(pace_home=72.0, pace_away=72.0)
    fast = _base_inputs(pace_home=90.0, pace_away=90.0)
    a = simulate_wnba_game(slow, simulations=2000, seed=19)
    b = simulate_wnba_game(fast, simulations=2000, seed=19)
    assert b["markets"]["raw_total_mean"] > a["markets"]["raw_total_mean"]


def test_market_blend_pulls_toward_consensus() -> None:
    raw = _base_inputs(ortg_home=115.0, ortg_away=95.0, sample_games_home=5, sample_games_away=5)
    blended = _base_inputs(
        ortg_home=115.0,
        ortg_away=95.0,
        sample_games_home=5,
        sample_games_away=5,
        market_spread_home=-3.5,
        market_total=162.5,
    )
    a = simulate_wnba_game(raw, simulations=1800, seed=3)
    b = simulate_wnba_game(blended, simulations=1800, seed=3)
    assert abs(b["markets"]["fair_spread_home"] - (-3.5)) < abs(
        a["markets"]["fair_spread_home"] - (-3.5)
    )
    assert b["diagnostics"]["market_blend"]["applied_spread"] is True
    assert b["diagnostics"]["market_blend"]["applied_total"] is True
    assert b["diagnostics"]["market_blend"]["pace_method"] == "harmonic_mean"


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


def test_no_nba_defaults_in_wnba_inputs() -> None:
    """Guard: league priors must not silently use NBA pace/ORtg."""
    inp = _base_inputs()
    assert inp.pace_home < 95.0
    assert inp.ortg_home < 112.0
    assert abs(inp.home_court_advantage - 2.25) < 1e-6
