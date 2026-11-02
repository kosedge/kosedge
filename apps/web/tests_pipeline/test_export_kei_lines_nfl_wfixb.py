"""t5178u W-FIX-B — export consumer uses the SAME fixture contract.

Synthetic only. No model/Odds HTTP. No DB. CERT=0.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

WEB_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = WEB_ROOT / "scripts" / "export_kei_lines_nfl.py"
CONTRACT = (
    WEB_ROOT.parent.parent
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "nfl_fixture_assembly"
    / "contract.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("export_kei_wfixb", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _allow() -> dict[str, Any]:
    return {
        "result": "ALLOW_FIXTURE",
        "reason": "fixture-channel transport admitted; not a production/betting allow",
        "fixture": True,
        "channel": "FIXTURE",
        "subscriber_consumable": False,
        "betting_consumable": False,
        "production_consumable": False,
        "env_bypass_honored": False,
        "cacheable": False,
        "contract_id": "t5178u-nfl-fixture-assembly-v0",
    }


def _assembly(eligibility: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "eligibility": eligibility or _allow(),
        "quote": {
            "book": "synth-book",
            "event_id": "2026_10_AAA_BBB",
            "side": "HOME",
            "period": "full_game",
            "line": -3.0,
            "price": -110,
            "time": "2026-11-08T16:00:00Z",
            "fixture": True,
            "transport_only": True,
            "injury_policy_approved": False,
        },
    }


def test_export_contract_id_matches_sot() -> None:
    mod = _load()
    src = CONTRACT.read_text(encoding="utf-8")
    assert f'CONTRACT_ID = "{mod.FIXTURE_CONTRACT_ID}"' in src


def test_fixture_export_spread_only_and_non_actionable_flags() -> None:
    mod = _load()
    doc = mod.project_fixture_assembly_to_export(
        _assembly(),
        consumer="fixture",
        home_team="Kansas City Chiefs",
        away_team="Buffalo Bills",
        home_abbr="KC",
        away_abbr="BUF",
    )
    assert doc["fixture"] is True
    assert doc["contract_id"] == "t5178u-nfl-fixture-assembly-v0"
    assert doc["eligibility"]["result"] == "ALLOW_FIXTURE"
    assert doc["eligibility"]["actionable"] is False
    assert doc["eligibility"]["subscriber_consumable"] is False
    assert doc["games"][0]["projSpreadHome"] == -3.0
    assert doc["games"][0]["projTotal"] is None
    assert doc["games"][0]["fixture"] is True


@pytest.mark.parametrize(
    "consumer",
    ["subscriber", "fair_lines_api", "betting", "production", "honesty_board"],
)
def test_customer_consumers_cannot_export_allow_fixture(consumer: str) -> None:
    mod = _load()
    with pytest.raises(mod.NflExportRefuse) as caught:
        mod.project_fixture_assembly_to_export(
            _assembly(),
            consumer=consumer,
            home_team="Kansas City Chiefs",
            away_team="Buffalo Bills",
        )
    assert caught.value.actionable is False
    assert caught.value.reason == "REFUSE_PRODUCTION_CHANNEL"


def test_customer_assemble_games_refuses_fixture_payload() -> None:
    mod = _load()
    with pytest.raises(mod.NflExportRefuse) as caught:
        mod.assemble_games(
            {
                "fixture": True,
                "eligibility": _allow(),
                "count": 1,
                "lines": [
                    {
                        "game_id": "2026_10_AAA_BBB",
                        "home_team": "Kansas City Chiefs",
                        "away_team": "Buffalo Bills",
                        "spread_home": -3.0,
                    }
                ],
            }
        )
    assert caught.value.reason == "REFUSE_PRODUCTION_CHANNEL"


@pytest.mark.parametrize(
    "requested,reason",
    [
        ("TOTAL", "REFUSE_TOTALS"),
        ("MONEYLINE", "REFUSE_MONEYLINE"),
        ("COVER_PROBABILITY", "REFUSE_COVER_PROBABILITY"),
    ],
)
def test_fixture_export_refuses_unsupported_channels(
    requested: str, reason: str
) -> None:
    mod = _load()
    with pytest.raises(mod.NflExportRefuse) as caught:
        mod.project_fixture_assembly_to_export(
            _assembly(),
            consumer="fixture",
            home_team="Kansas City Chiefs",
            away_team="Buffalo Bills",
            requested_output=requested,
        )
    assert caught.value.reason == reason


def test_fixture_export_blank_identity_and_period() -> None:
    mod = _load()
    with pytest.raises(mod.NflExportRefuse) as caught:
        mod.project_fixture_assembly_to_export(
            _assembly(),
            consumer="fixture",
            home_team="   ",
            away_team="Buffalo Bills",
        )
    assert caught.value.reason == "blank_required_identity"
    bad = _assembly()
    bad["quote"]["period"] = "h1"
    with pytest.raises(mod.NflExportRefuse) as caught:
        mod.project_fixture_assembly_to_export(
            bad,
            consumer="fixture",
            home_team="Kansas City Chiefs",
            away_team="Buffalo Bills",
        )
    assert caught.value.reason == "REFUSE_PERIOD"
