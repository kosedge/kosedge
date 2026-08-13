"""Daily intel overrides round-trip the one SoT pack into Week 1 KEI drivers."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nfl_daily_intel import (
    apply_intel_overrides,
    kei_smoke_for_teams,
)
from src.services.nfl_kei_week1_reprice import Week1Pack

PACK_PATH = (
    Path(__file__).resolve().parents[1]
    / "src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json"
)
FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "data/ops/nfl-daily-intel/sample-override.example.json"
)


def test_sample_override_changes_pack_and_kei_drivers() -> None:
    payload = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    ov_doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert ov_doc.get("fixture") is True

    before_pack = Week1Pack.from_payload(payload)
    wr1 = next(
        r
        for r in before_pack.skill("WAS")
        if r.get("player_name") == "Terry McLaurin"
    )
    assert wr1.get("injury_status") not in {"out", "ir"}

    before_smoke = kei_smoke_for_teams(payload, ["WAS"])
    result = apply_intel_overrides(payload, ov_doc["overrides"], as_of="2026-08-13")
    assert result.applied
    assert "WAS" in result.touched_teams
    assert result.republish_recommended is False

    after_pack = Week1Pack.from_payload(result.payload)
    wr1_after = next(
        r
        for r in after_pack.skill("WAS")
        if r.get("player_name") == "Terry McLaurin"
    )
    assert wr1_after.get("injury_status") == "out"

    after_smoke = kei_smoke_for_teams(result.payload, ["WAS"])
    after_game = next(r for r in after_smoke if r["game"] == "WAS @PHI")
    before_game = next(r for r in before_smoke if r["game"] == "WAS @PHI")
    factors = " ".join(after_game["factors"])
    assert "McLaurin" in factors
    assert after_game["spread_delta"] != before_game["spread_delta"] or "McLaurin" in factors

    # Original on-disk pack is untouched.
    disk = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    disk_wr = next(
        r
        for r in disk["rows"]
        if r.get("team") == "WAS" and r.get("player_name") == "Terry McLaurin"
    )
    assert disk_wr.get("injury_status") != "out"


def test_wait_republish_does_not_write() -> None:
    payload = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    result = apply_intel_overrides(
        payload,
        [
            {
                "team": "ATL",
                "player_name": "Tua Tagovailoa",
                "position": "QB",
                "field": "player_name",
                "before": "Tua Tagovailoa",
                "after": "Someone Else",
                "reason": "do not invent a starter",
                "as_of": "2026-08-13",
                "confidence": "low",
                "destination": "wait_republish",
            }
        ],
    )
    assert result.applied == []
    assert result.republish_recommended is True
    tua = next(
        r
        for r in result.payload["rows"]
        if r.get("team") == "ATL" and r.get("player_name") == "Tua Tagovailoa"
    )
    assert tua["player_name"] == "Tua Tagovailoa"


def test_qb_identity_sot_flags_republish() -> None:
    payload = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    result = apply_intel_overrides(
        payload,
        [
            {
                "team": "MIN",
                "player_name": "Kyler Murray",
                "position": "QB",
                "field": "competition_status",
                "before": "named_starter",
                "after": "open_competition",
                "reason": "desk would reopen the room",
                "as_of": "2026-08-13",
                "confidence": "medium",
                "destination": "sot",
            }
        ],
    )
    assert result.applied
    assert result.republish_recommended is True
