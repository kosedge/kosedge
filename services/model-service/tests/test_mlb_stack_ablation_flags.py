from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

import src.services.mlb_data as mlb_data
import src.services.mlb_simulator as mlb_sim
from src.services.mlb_simulator import MlbGameInputs, simulate_mlb_game


def test_matchup_flag_off_neutralizes_matchup_edge() -> None:
    prior = mlb_sim.get_stack_ablation_flags()
    try:
        soft = MlbGameInputs(
            game_id="flag-soft",
            home_team="Yankees",
            away_team="Red Sox",
            offense_split_home=1.10,
            recent_form_index_home=1.08,
            starter_k_factor_away=1.14,
            starter_bb_factor_away=0.90,
            starter_firmness_away=0.95,
        )
        walks = MlbGameInputs(
            game_id="flag-walks",
            home_team="Yankees",
            away_team="Red Sox",
            offense_split_home=1.10,
            recent_form_index_home=1.08,
            starter_k_factor_away=0.92,
            starter_bb_factor_away=1.14,
            starter_firmness_away=0.95,
        )
        mlb_sim.apply_stack_ablation_flags(matchup_mul_enabled=True)
        on_soft = simulate_mlb_game(soft, simulations=2200, seed=19)["markets"]["fg_home_win_prob"]
        on_walks = simulate_mlb_game(walks, simulations=2200, seed=19)["markets"]["fg_home_win_prob"]
        on_delta = on_walks - on_soft
        assert on_delta > 0

        mlb_sim.apply_stack_ablation_flags(matchup_mul_enabled=False)
        off_soft = simulate_mlb_game(soft, simulations=2200, seed=19)["markets"]["fg_home_win_prob"]
        off_walks = simulate_mlb_game(walks, simulations=2200, seed=19)["markets"]["fg_home_win_prob"]
        off_delta = off_walks - off_soft
        # K/BB still move starter_shape when matchup is off; matchup mul should add edge.
        assert on_delta > off_delta
    finally:
        mlb_sim.apply_stack_ablation_flags(
            matchup_mul_enabled=prior["matchup_mul_enabled"],
            weather_wind_dir_mul_enabled=prior["weather_wind_dir_mul_enabled"],
        )


def test_wind_dir_flag_changes_environment_mul() -> None:
    prior = mlb_sim.get_stack_ablation_flags()
    try:
        inputs = MlbGameInputs(
            game_id="wind",
            home_team="Cubs",
            away_team="Cards",
            weather_wind_dir_deg=180.0,
            weather_wind_mph=12.0,
            weather_temp_f=78.0,
            park_factor_runs=1.0,
        )
        mlb_sim.apply_stack_ablation_flags(weather_wind_dir_mul_enabled=True)
        on = mlb_sim._environment_run_multiplier(inputs)
        mlb_sim.apply_stack_ablation_flags(weather_wind_dir_mul_enabled=False)
        off = mlb_sim._environment_run_multiplier(inputs)
        assert on > off
    finally:
        mlb_sim.apply_stack_ablation_flags(
            matchup_mul_enabled=prior["matchup_mul_enabled"],
            weather_wind_dir_mul_enabled=prior["weather_wind_dir_mul_enabled"],
        )


def test_kbb_only_starter_quality_ignores_era_whip(monkeypatch) -> None:
    mlb_data._live_starter_features.cache_clear()
    prior = mlb_data.get_starter_quality_mode()

    class _Resp:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def fake_get(url, *args, **kwargs):
        if url.endswith("/people/search"):
            return _Resp(
                {
                    "people": [
                        {
                            "id": 700001,
                            "fullName": "Tarik Skubal",
                            "active": True,
                            "primaryPosition": {"code": "1"},
                            "pitchHand": {"code": "L"},
                        }
                    ]
                }
            )
        if url.endswith("/people/700001/stats"):
            return _Resp(
                {
                    "stats": [
                        {
                            "splits": [
                                {
                                    "stat": {
                                        # Terrible ERA/WHIP but elite K-BB shape
                                        "era": "6.50",
                                        "whip": "1.55",
                                        "strikeoutsPer9Inn": "12.0",
                                        "walksPer9Inn": "1.6",
                                        "groundOutsToAirouts": "1.30",
                                    }
                                }
                            ]
                        }
                    ]
                }
            )
        raise AssertionError(url)

    try:
        monkeypatch.setattr(mlb_data.requests, "get", fake_get)
        mlb_data.apply_starter_quality_mode("era_whip")
        era = mlb_data.starter_identity_features("Tarik Skubal", season=2026)
        mlb_data.apply_starter_quality_mode("kbb_only")
        kbb = mlb_data.starter_identity_features("Tarik Skubal", season=2026)
        assert era["starter_quality"] > 1.0
        assert kbb["starter_quality"] < 1.0
        assert kbb["quality_mode"] == "kbb_only"
    finally:
        mlb_data.apply_starter_quality_mode(prior)
