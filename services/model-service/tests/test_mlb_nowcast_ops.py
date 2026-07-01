import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.routes.mlb import _aggregate_nowcast_snapshot_payloads


def test_aggregate_nowcast_snapshot_payloads_returns_expected_averages() -> None:
    out = _aggregate_nowcast_snapshot_payloads(
        [
            {
                "context_rows_updated": 4,
                "avg_nowcast_confidence": 0.82,
                "avg_prev_confidence": 0.76,
                "avg_confidence_delta": 0.06,
                "avg_freshness_score": 0.89,
                "lineup_confirmed_share": 0.50,
            },
            {
                "context_rows_updated": 6,
                "avg_nowcast_confidence": 0.86,
                "avg_prev_confidence": 0.81,
                "avg_confidence_delta": 0.05,
                "avg_freshness_score": 0.91,
                "lineup_confirmed_share": 0.67,
            },
        ]
    )
    assert out["runs_analyzed"] == 2
    assert out["games_repriced"] == 10
    assert out["avg_nowcast_confidence"] == 0.84
    assert out["avg_prev_confidence"] == 0.785
    assert out["avg_confidence_delta"] == 0.055
    assert out["avg_freshness_score"] == 0.9
    assert out["lineup_confirmed_share"] == 0.585


def test_aggregate_nowcast_snapshot_payloads_handles_empty() -> None:
    out = _aggregate_nowcast_snapshot_payloads([])
    assert out["runs_analyzed"] == 0
    assert out["games_repriced"] == 0
    assert out["avg_nowcast_confidence"] == 0.0
    assert out["avg_prev_confidence"] is None
    assert out["avg_confidence_delta"] is None
