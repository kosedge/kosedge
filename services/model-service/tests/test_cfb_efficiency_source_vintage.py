"""Year-locked 2025 SP+ provenance — do not mix live 2026 into the carry."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine.fbs_universe import official_fbs_codes
from src.services.cfb_season_engine.name_to_code import (
    ESPN_FINAL_2025_STORY_NAME_TO_CODE,
    require_mapped_code,
)

ROOT = Path(__file__).resolve().parents[3]
DATA = Path(__file__).resolve().parents[1] / "src/services/cfb_season_engine/data"
CANARY = ROOT / "data/ops/cfb-w0-canary-20260831"
SOURCE = DATA / "cfb_sp_plus_final_2025_espn_story.json"
EFFICIENCY = DATA / "cfb_efficiency_snapshot_2025_carry_2026.json"
PACKAGER = ROOT / "scripts/cfb/package_efficiency_2025_carry.py"


def test_committed_espn_table_is_complete_official_136() -> None:
    blob = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = blob["teams"]
    official = official_fbs_codes()
    have = {r["team"] for r in rows}
    assert blob["source"]["id"] == "espn_story_46128861"
    assert blob["source"]["published"].startswith("2026-01-20")
    assert blob["source"]["legal_at_model_as_of"] == "2026-08-31"
    assert blob["coverage"]["rows"] == 136
    assert have == official
    assert "NDSU" not in have
    assert "SAC" not in have
    assert [r["rank"] for r in rows] == list(range(1, 137))
    assert next(r for r in rows if r["team"] == "IU")["sp_plus"] == 32.4
    assert next(r for r in rows if r["team"] == "OSU")["sp_plus"] == 30.1
    assert next(r for r in rows if r["team"] == "MIZZ")["sp_plus"] == 14.4
    assert next(r for r in rows if r["team"] == "M-OH")["name"] == "Miami-OH"


def test_espn_abbreviations_are_the_87_of_136_cause() -> None:
    blob = json.loads(SOURCE.read_text(encoding="utf-8"))
    via = [r["name_mapped_via"] for r in blob["teams"]]
    assert via.count("espn_story_abbreviation") == 49
    assert len(ESPN_FINAL_2025_STORY_NAME_TO_CODE) == 49
    for row in blob["teams"]:
        if row["name_mapped_via"] == "espn_story_abbreviation":
            assert require_mapped_code(row["name"]) == row["team"]


def test_packager_refuses_splice_and_live_public() -> None:
    text = PACKAGER.read_text(encoding="utf-8")
    assert "load_authoritative_sp_plus" in text
    assert "LivePublicIsNotFinal2025" in text
    assert "mixes ESPN rows onto a frozen cfbupdate" in text
    assert "final_2025_sp_plus_public_table" not in text.split("def main")[1]


def test_w0_canary_is_preserved() -> None:
    proj = json.loads(
        (CANARY / "cfb_season_projections_2026.json").read_text(encoding="utf-8")
    )
    by = {r["team"]: r for r in proj["teams"]}
    assert proj["artifact_id"] == (
        "cfb-season-projections-v0.15-n10000-week0-close-20260831"
    )
    assert proj["as_of"] == "2026-08-31"
    assert abs(float(by["USF"]["mean"]) - 8.382) <= 0.05
    assert abs(float(by["OSU"]["mean"]) - 9.537) <= 0.05
    assert abs(float(by["UTAH"]["mean"]) - 9.634) <= 0.05
    assert float(by["USF"]["std"]) < float(by["OSU"]["std"])
    manifest = json.loads((CANARY / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["role"] == "week0_close_canary"
    assert manifest["do_not_overwrite"] is True


def test_working_efficiency_is_single_espn_vintage() -> None:
    snap = json.loads(EFFICIENCY.read_text(encoding="utf-8"))
    assert snap["source"]["vintage"] == "espn_story_2025_final"
    assert snap["source"]["live_public"] == "rejected_2026_inseason_cfbupdate"
    assert "p0_splice" not in snap["source"]
    assert snap["provenance_complete"] == 136
    assert snap["team_count"] == 136
    # Live 2026 in-season TCU/UNC are 3.9 / +5.8. Year-lock is 8.3 / -6.6.
    assert snap["teams"]["TCU"]["sp_plus"] == 8.3
    assert snap["teams"]["UNC"]["sp_plus"] == -6.6
    assert snap["teams"]["UNT"]["sp_plus"] == 13.8
