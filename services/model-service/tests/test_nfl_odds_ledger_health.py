"""Unit tests for NFL odds ledger lag health (#5 R1 Slice B)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.services.nfl_odds_ledger_health import (
    build_odds_ledger_health_payload,
    derive_ledger_health,
    history_lag_seconds,
    probe_nfl_odds_ledger_health,
)


UTC = timezone.utc


def test_history_lag_seconds_null_when_either_missing() -> None:
    raw = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    assert history_lag_seconds(None, raw) is None
    assert history_lag_seconds(raw, None) is None
    assert history_lag_seconds(None, None) is None


def test_history_lag_seconds_positive_when_history_behind() -> None:
    raw = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    hist = raw - timedelta(seconds=90)
    assert history_lag_seconds(raw, hist) == 90


def test_history_lag_seconds_negative_when_history_ahead() -> None:
    raw = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    hist = raw + timedelta(seconds=15)
    assert history_lag_seconds(raw, hist) == -15


def test_derive_raw_dark_when_no_odds_snapshots() -> None:
    assert derive_ledger_health(raw_max=None, history_max=None) == "raw_dark"
    assert (
        derive_ledger_health(
            raw_max=None,
            history_max=datetime(2026, 9, 4, tzinfo=UTC),
        )
        == "raw_dark"
    )


def test_derive_history_lagging_when_history_missing_or_behind() -> None:
    raw = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    assert derive_ledger_health(raw_max=raw, history_max=None) == "history_lagging"
    assert (
        derive_ledger_health(raw_max=raw, history_max=raw - timedelta(seconds=1))
        == "history_lagging"
    )


def test_derive_ok_when_history_caught_up() -> None:
    raw = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    assert derive_ledger_health(raw_max=raw, history_max=raw) == "ok"
    assert (
        derive_ledger_health(raw_max=raw, history_max=raw + timedelta(seconds=5))
        == "ok"
    )


def test_derive_unknown_when_probe_failed() -> None:
    assert (
        derive_ledger_health(
            raw_max=datetime(2026, 9, 4, tzinfo=UTC),
            history_max=datetime(2026, 9, 4, tzinfo=UTC),
            probe_ok=False,
        )
        == "unknown"
    )


def test_payload_note_marks_persist_zeros_unmisreadable() -> None:
    payload = build_odds_ledger_health_payload(
        raw_max=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
        history_max=datetime(2026, 9, 4, 11, 59, tzinfo=UTC),
    )
    assert payload["ledger_health"] == "history_lagging"
    assert payload["history_lag_seconds"] == 60
    assert "persist=0" in payload["note"]
    assert "≠ dark" in payload["note"] or "!= dark" in payload["note"]
    assert "FRESH" in payload["note"]


class _LedgerRow:
    def __init__(self, mapping: dict) -> None:
        self._mapping = mapping


class _LedgerResult:
    def __init__(self, mapping: dict | None) -> None:
        self._mapping = mapping

    def fetchone(self):
        if self._mapping is None:
            return None
        return _LedgerRow(self._mapping)


class _LedgerSession:
    def __init__(self, mapping: dict | None) -> None:
        self._mapping = mapping

    def execute(self, *_args, **_kwargs):
        return _LedgerResult(self._mapping)


def test_probe_builds_ok_payload() -> None:
    raw = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    hist = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    payload = probe_nfl_odds_ledger_health(
        _LedgerSession(
            {
                "last_odds_snapshot_captured_at": raw,
                "last_market_history_captured_at": hist,
            }
        )
    )
    assert payload["ledger_health"] == "ok"
    assert payload["history_lag_seconds"] == 0
    assert payload["last_odds_snapshot_captured_at"] == raw.isoformat()


def test_probe_unknown_on_empty_row() -> None:
    payload = probe_nfl_odds_ledger_health(_LedgerSession(None))
    assert payload["ledger_health"] == "unknown"
    assert payload["last_odds_snapshot_captured_at"] is None
