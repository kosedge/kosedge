from datetime import date

from src.services import mlb_data, mlb_statcast_stuff as stuff


def test_aggregate_and_quality_from_pitch_rows() -> None:
    rows = []
    # Elite whiff pitcher: many swinging strikes, low EV
    for i in range(250):
        rows.append(
            {
                "pitcher": "123",
                "description": "swinging_strike" if i % 3 == 0 else "ball",
                "zone": "11" if i % 2 else "5",
                "launch_speed": "",
                "launch_angle": "",
                "game_date": "2026-05-01",
            }
        )
    for i in range(40):
        rows.append(
            {
                "pitcher": "123",
                "description": "hit_into_play",
                "zone": "5",
                "launch_speed": "85.0",
                "launch_angle": "12.0",
                "game_date": "2026-05-01",
            }
        )
    agg = stuff.aggregate_pitch_rows(rows)
    assert 123 in agg
    assert agg[123]["pitches"] >= 200
    assert agg[123]["whiff_pct"] > 0.20
    q = stuff.quality_from_stuff_metrics(agg[123])
    assert 0.82 <= q <= 1.18
    assert q < 1.0  # high whiff ⇒ better pitcher ⇒ lower run-allowed factor


def test_as_of_cutoff_rejects_same_day_pitches(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(stuff, "CACHE_DIR", tmp_path)
    stuff.clear_statcast_stuff_caches()
    # Inject cumulative index with day-before and same-day points.
    season_map = {
        99: [
            (
                "2026-05-19",
                {
                    "pitches": 250.0,
                    "whiff_pct": 0.15,
                    "chase_pct": 0.30,
                    "zone_pct": 0.48,
                    "avg_ev": 87.0,
                    "barrel_pct": 0.05,
                },
            ),
            (
                "2026-05-20",
                {
                    "pitches": 300.0,
                    "whiff_pct": 0.25,
                    "chase_pct": 0.35,
                    "zone_pct": 0.50,
                    "avg_ev": 85.0,
                    "barrel_pct": 0.04,
                },
            ),
        ]
    }
    stuff._PITCHER_CUMULATIVE[2026] = season_map
    metrics = stuff.get_pitcher_stuff_as_of(
        99, as_of=date(2026, 5, 20), season=2026, fetch_if_missing=False
    )
    assert metrics is not None
    # Must use through 2026-05-19 only (game day − 1), not same-day 0.25 whiff.
    assert abs(metrics["whiff_pct"] - 0.15) < 1e-9
    assert metrics["as_of_pitches_through"] == "2026-05-19"


def test_stuff_proxy_mode_uses_override_metrics(monkeypatch) -> None:
    prior = mlb_data.get_starter_quality_mode()
    stuff.clear_statcast_stuff_caches()
    try:
        mlb_data.apply_starter_quality_mode("stuff_proxy")
        stuff.set_stuff_metrics_override(
            season=2026,
            pitcher_id=555,
            as_of=date(2026, 6, 1),
            metrics={
                "pitches": 400.0,
                "whiff_pct": 0.18,
                "chase_pct": 0.33,
                "zone_pct": 0.50,
                "avg_ev": 86.0,
                "barrel_pct": 0.045,
                "as_of_pitches_through": "2026-05-31",
            },
        )
        # Bypass network: stub live features builder inputs via _starter_features_from_stat
        feat = mlb_data._starter_features_from_stat(
            starter_name="Test Arm",
            player_id=555,
            season=2026,
            handedness="R",
            stat={
                "era": 5.50,
                "whip": 1.45,
                "strikeoutsPer9Inn": 7.0,
                "walksPer9Inn": 3.5,
                "groundOutsToAirouts": 1.0,
                "inningsPitched": "40.0",
                "homeRuns": 8,
                "baseOnBalls": 20,
                "hitByPitch": 2,
                "strikeOuts": 35,
                "groundOuts": 40,
                "airOuts": 40,
            },
            as_of=date(2026, 6, 1),
        )
        assert feat is not None
        assert feat["quality_mode"] == "stuff_proxy"
        assert feat["source"] == "statcast-stuff"
        assert feat["starter_quality"] < 1.0
        assert "stuff" in feat
    finally:
        mlb_data.apply_starter_quality_mode(prior)
        stuff.clear_statcast_stuff_caches()
