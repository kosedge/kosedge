from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def _load_parse_report_time():
    path = Path(__file__).resolve().parents[1] / "data_platform_nfl" / "ingest.py"
    source = path.read_text()
    start = source.index("def _parse_report_time")
    end = source.index("\ndef _to_int", start)
    ns: dict = {"datetime": datetime, "timezone": timezone, "Any": object, "Dict": dict}
    exec(source[start:end], ns)
    return ns["_parse_report_time"]


def test_parse_report_time_uses_source_not_now() -> None:
    parse = _load_parse_report_time()
    parsed = parse({"date_modified": "2023-10-01T16:00:00Z", "report_status": "Out"})
    assert parsed == datetime(2023, 10, 1, 16, 0, tzinfo=timezone.utc)


def test_parse_report_time_missing_is_none() -> None:
    parse = _load_parse_report_time()
    assert parse({"report_status": "Out"}) is None
    assert parse({}) is None
