# t4559u W8 current-input audit — deterministic repro

CERT_CANDIDATE=0. RESEARCH. No Odds. No seal dests.

```bash
cd services/model-service
PYTHONPATH=. python3 -m src.services.nfl_model_forecast_emit audit --season 2026 --week 8
# expect exit 2
# failing_components: depth_sot_week, injury_paths_current,
#   current_weekly_depth_db, inseason_efficiency_current
# passed: week_schedule_kickoffs (14 games)
# input_completeness_sha256: 21b96525d4b59eb810801495723ad5c4cc84b7a64e4fc422bbeab8e8a85ace71

PYTHONPATH=. python3 -m src.services.nfl_model_forecast_emit slate --season 2026 --week 8
# expect FAIL_CLOSED gap=G8 reason=slate_inputs_incomplete

PYTHONPATH=. python3 -m pytest -q tests/test_nfl_model_forecast_emit.py
# expect 15 passed
```

Do not run `project_game_player_boxes` against this pack and call it a current W8 forecast.
