import os
from datetime import date

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.tasks import _payload_checksum, _upsert_mlb_raw_data_object


class _FakeSession:
    def __init__(self) -> None:
        self.calls = []

    def execute(self, statement, params):
        self.calls.append((str(statement), params))
        return None


def test_payload_checksum_is_stable_for_key_order() -> None:
    a = {"x": 1, "y": {"z": 2, "k": 3}}
    b = {"y": {"k": 3, "z": 2}, "x": 1}
    assert _payload_checksum(a) == _payload_checksum(b)


def test_upsert_raw_object_executes_with_expected_keys() -> None:
    session = _FakeSession()
    _upsert_mlb_raw_data_object(
        session,
        source="mlb-stats-api",
        object_type="schedule_game",
        object_key="12345",
        as_of_date=date(2026, 4, 12),
        payload={"hello": "world"},
    )
    assert len(session.calls) == 1
    _, params = session.calls[0]
    assert params["source"] == "mlb-stats-api"
    assert params["object_type"] == "schedule_game"
    assert params["object_key"] == "12345"
    assert params["as_of_date"].isoformat() == "2026-04-12"
    assert isinstance(params["checksum"], str) and len(params["checksum"]) == 64
