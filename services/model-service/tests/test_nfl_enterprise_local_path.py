"""t4141u — operate week, local inputs, trace, 2998 retraction."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
POINTER = ROOT / "data/ops/nfl-web-launch-bundle.json"
PRESEASON_LOCK = "nfl-season-engine-2026-preseason-lock"


def _load(name: str):
    path = ROOT / "scripts" / "nfl" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_operate_week_decoupled_from_research_pin() -> None:
    week = _load("nfl_operate_week")
    # After W6 MNF (WAS@SF 2026-10-20T00:15Z), before W7 TNF (NE@CHI 2026-10-23T00:15Z).
    as_of = datetime(2026, 10, 22, 15, 30, tzinfo=timezone.utc)
    meta = week.resolve_operate_week(as_of=as_of)
    assert meta["research_pin_decoupled"] is True
    assert meta["inferred_finished_week"] == 6
    assert meta["operate_week"] == 6
    assert meta["in_season"] is True
    assert meta["next_game_id"] == "2026-W07-NE@CHI"
    explicit = week.resolve_operate_week(as_of=as_of, explicit_week=0)
    assert explicit["operate_week"] == 0
    assert explicit["week_source"] == "cli_explicit"
    assert explicit["inferred_finished_week"] == 6


def test_operate_week_preseason_as_of() -> None:
    week = _load("nfl_operate_week")
    as_of = datetime(2026, 8, 1, tzinfo=timezone.utc)
    meta = week.resolve_operate_week(as_of=as_of)
    assert meta["inferred_finished_week"] == 0
    assert meta["in_season"] is False


def test_local_inputs_refuse_silent_default_and_placeholder(tmp_path: Path) -> None:
    local = _load("nfl_local_inputs")
    with pytest.raises(local.LocalInputError):
        local.refuse_silent_default("rest_days", 7.0)
    with pytest.raises(local.LocalInputError):
        local.refuse_silent_default("injury_impact", 0.0)
    local.refuse_silent_default("rest_days", 7.0, source="explicit_named_value")

    blob = b"nflverse-test\n"
    path = tmp_path / "games.csv"
    path.write_bytes(blob)
    digest = hashlib.sha256(blob).hexdigest()
    man = tmp_path / "imv-manifest.tsv"
    man.write_text(
        f"{digest}\t{path}\tschedule_games_csv\t2026-10-22T14:43:22Z\n",
        encoding="utf-8",
    )
    now = datetime(2026, 10, 22, 15, 0, tzinfo=timezone.utc)
    report = local.load_manifest(man, now=now)
    assert report["status"] == "READY"
    assert report["never_silent_default"] is True

    man_bad = tmp_path / "bad.tsv"
    man_bad.write_text(
        "PLACEHOLDER_SHA256_RYAN_AUTHORIZES_SEPARATELY\tmissing.csv\tschedule_games_csv\t2026-01-01T00:00:00Z\n",
        encoding="utf-8",
    )
    blocked = local.load_manifest(man_bad, now=now)
    assert blocked["status"] == "BLOCKED"
    assert "schedule_games_csv" in blocked["missing_roles"]


def test_computation_trace_labels_retrospective_and_blocks_missing() -> None:
    trace = _load("nfl_computation_trace")
    doc = trace.empty_in_season_trace(
        season=2026,
        week=6,
        record_class="RETROSPECTIVE",
        reason="test skeleton",
    )
    assert doc["record_class"] == "RETROSPECTIVE"
    assert doc["fabricated_pregame"] is False
    assert doc["status"] == "BLOCKED"
    assert [h["hop"] for h in doc["hops"]] == list(trace.HOPS)


def test_n2998_retracted_and_holdout_contaminated() -> None:
    ev = _load("nfl_historical_eval_contract")
    report = ev.contract_report(include_leakage_scan=True)
    assert report["retraction"]["status"] == "RETRACTED"
    assert report["retraction"]["claim"] == 2998
    assert report["retraction"]["do_not_invent_drop_list"] is True
    assert report["retraction"]["closest_train_n"] == 2992
    assert report["split"]["test_status"] == "CONTAMINATED_DO_NOT_USE_FOR_CERT"
    assert report["split"]["recompute_holdout"] == "FORBIDDEN"
    assert report["leakage"]["label"] == "LEAKAGE-EXPOSED"
    assert report["fabricated_pregame"] is False


def test_weekly_inseason_dry_run_does_not_skip_ingest_for_preseason_pin(
    tmp_path: Path,
) -> None:
    weekly = _load("run_weekly_operate")
    before = POINTER.read_text(encoding="utf-8")
    payload = weekly.run_weekly(
        week=6,
        dry_run=True,
        skip_kei=True,
        skip_audit=True,
        last_run_path=tmp_path / "last.json",
        pointer_path=POINTER,
        week_explicit=True,
    )
    after = POINTER.read_text(encoding="utf-8")
    assert after == before
    assert json.loads(before).get("lock_tag") == PRESEASON_LOCK
    assert payload["research_pin_preseason"] is True
    assert payload["research_pin_decoupled"] is True
    assert payload["record_class"] == "RETROSPECTIVE"
    ingest = next(s for s in payload["stages"] if s["id"] == "results_ingest")
    assert ingest["status"] == "pass"
    assert "not skipped" in ingest["detail"]
    b0 = next(s for s in payload["stages"] if s["id"] == "b0_snapshot")
    assert b0["status"] == "skip"
    assert b0["record_class"] == "RETROSPECTIVE"
    kei = next(s for s in payload["stages"] if s["id"] == "kei_board_rebuild")
    assert kei["status"] == "skip"
    assert payload["historical_eval"]["retraction"]["status"] == "RETRACTED"
    contract = _load("nfl_operate_contract")
    assert contract.validate_weekly_last_run(payload) == []
