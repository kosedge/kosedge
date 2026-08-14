"""P1 warehouse spine — immutable fairs, leakage, coverage + dry-run (no KEI)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.leakage import (
    LEAKAGE_RULE,
    assert_available_before_kickoff,
    is_available_before_kickoff,
)
from src.services.cfb_warehouse.predictions import (
    ImmutablePredictionError,
    MissingPredictionIdentityError,
    snapshot_exists,
    write_prediction,
)

REPO = Path(__file__).resolve().parents[3]


def _load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _legal_row(**overrides):
    row = {
        "model_version": "cfb-season-engine-v0.9-inseason",
        "as_of": "2024-08-01T00:00:00+00:00",
        "game_id": "401628323",
        "season": 2024,
        "week": 1,
        "home_team_id": "UGA",
        "away_team_id": "CLEM",
        "fair_spread": -5.04,
        "fair_total": 48.5,
        "wp": 0.72,
        "uncertainty": 4.3,
        "available_at": "2024-08-01T00:00:00+00:00",
        "kickoff": "2024-08-31T16:00:00+00:00",
        "game_date": "2024-08-31",
    }
    row.update(overrides)
    return row


def test_write_requires_model_version_and_as_of(tmp_path: Path) -> None:
    with pytest.raises(MissingPredictionIdentityError):
        write_prediction(
            {"game_id": "x", "as_of": "2024-08-01T00:00:00Z"},
            root=tmp_path,
        )
    with pytest.raises(MissingPredictionIdentityError):
        write_prediction(
            {
                "model_version": "cfb-season-engine-v0.9-inseason",
                "game_id": "x",
            },
            root=tmp_path,
        )


def test_immutable_write_rejects_overwrite(tmp_path: Path) -> None:
    first = write_prediction(_legal_row(), root=tmp_path, formats=("json", "jsonl"))
    assert first["kei"] is False
    assert snapshot_exists(
        model_version=first["model_version"],
        as_of=first["as_of"],
        game_id=first["game_id"],
        root=tmp_path,
    )
    with pytest.raises(ImmutablePredictionError, match="refuse overwrite"):
        write_prediction(
            _legal_row(fair_spread=-13.5),
            root=tmp_path,
            formats=("json",),
        )
    # New as_of is a new row (injury / restatement), not a mutate.
    second = write_prediction(
        _legal_row(as_of="2024-08-15T00:00:00+00:00", fair_spread=-6.0),
        root=tmp_path,
    )
    assert second["fair_spread"] == -6.0
    assert second["as_of"] != first["as_of"]


def test_prediction_rejects_same_timestamp_and_future_info(tmp_path: Path) -> None:
    kick = datetime(2024, 8, 31, 16, 0, tzinfo=timezone.utc)
    assert not is_available_before_kickoff(available_at=kick, kickoff=kick)
    with pytest.raises(ValueError, match="leakage"):
        assert_available_before_kickoff(
            available_at="2024-08-31T16:00:00+00:00",
            kickoff="2024-08-31T16:00:00+00:00",
            feature_name="model_prediction",
        )
    with pytest.raises(ValueError, match="leakage"):
        write_prediction(
            _legal_row(available_at="2024-12-15T00:00:00+00:00"),
            root=tmp_path,
        )
    assert LEAKAGE_RULE == "strictly_before_kickoff"


def test_coverage_script_dry_run() -> None:
    mod = _load_script(
        "report_warehouse_coverage",
        REPO / "scripts" / "cfb" / "report_warehouse_coverage.py",
    )
    rc = mod.main(["--dry-run", "--no-hd"])
    assert rc == 0
    report = mod.build_report(overlay=False)
    assert report["source"] == "committed_inventory"
    assert report["totals"]["games_2020_2025"] == 5196
    assert report["by_season"]["2024"]["games"] == 965
    assert report["by_season"]["2014"]["pbp_plays"] == 155521
    assert report["leakage_rule"] == "strictly_before_kickoff"


def test_walkforward_dry_run_does_not_write_kei(tmp_path: Path) -> None:
    mod = _load_script(
        "run_walkforward_dry_run",
        REPO / "scripts" / "cfb" / "run_walkforward_dry_run.py",
    )
    summary = tmp_path / "walkforward_dry_run.json"
    rc = mod.main(
        [
            "--fixtures",
            "--limit",
            "2",
            "--write-research-summary",
            str(summary),
        ]
    )
    assert rc == 0
    payload = json.loads(summary.read_text())
    assert payload["kei_written"] is False
    assert payload["source"] == "fixtures"
    assert not (REPO / "apps" / "web" / "data" / "kei_lines_cfb.json").exists()
    assert not (REPO / "data" / "kei_lines_cfb.json").exists()
    # Refuse a KEI-shaped output path.
    rc_bad = mod.main(
        [
            "--fixtures",
            "--write-research-summary",
            str(tmp_path / "kei_lines_cfb.json"),
        ]
    )
    assert rc_bad == 2
    assert not (tmp_path / "kei_lines_cfb.json").exists()
