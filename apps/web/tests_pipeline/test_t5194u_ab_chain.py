"""t5194u A→B chain — consume A's pinned FixtureChainRecord via export.

Real functions. No invented allow tokens. CERT=0.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

WEB_ROOT = Path(__file__).resolve().parents[1]
REPO = WEB_ROOT.parent.parent
SCRIPT = WEB_ROOT / "scripts" / "export_kei_lines_nfl.py"
CHAIN_CMD = REPO / "scripts" / "nfl" / "t5194u-ab-chain.py"
PINNED = REPO / "data" / "ops" / "t5194u-wfix-a-chain" / "positive-output.json"
EXPECTED = "27f32649050578108720b2ff26eacebadb92c7324f1930661c88b8f1ce6e6124"


def _load():
    spec = importlib.util.spec_from_file_location("export_t5194u", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _payload() -> dict:
    return json.loads(PINNED.read_text(encoding="utf-8"))


def test_command_and_pinned_digest() -> None:
    proc = subprocess.run(
        [sys.executable, str(CHAIN_CMD)],
        cwd=str(REPO),
        env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(REPO / "services" / "model-service")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"digest {EXPECTED}" in proc.stdout
    assert "OK" in proc.stdout
    assert "forbidden_call_attempts 0" in proc.stdout


def test_export_consumes_a_artifact_not_invented_allow() -> None:
    mod = _load()
    payload = _payload()
    assert payload["chain_contract_id"] == "t5194u-nfl-fixture-chain-v1"
    decision = mod.consume_fixture_eligibility(payload["eligibility"], "fixture")
    assert decision["result"] == "ALLOW_FIXTURE"
    assert decision["schema_version"] == "nfl-fixture-assembly-v0"
    doc = mod.project_fixture_assembly_to_export(
        payload,
        consumer="fixture",
        home_team="Synthetic Home",
        away_team="Synthetic Away",
    )
    assert doc["games"][0]["projSpreadHome"] == -3.0
    assert doc["games"][0]["projTotal"] is None


def test_export_refuses_bare_allow() -> None:
    mod = _load()
    with pytest.raises(mod.NflExportRefuse) as caught:
        mod.consume_fixture_eligibility({"result": "ALLOW_FIXTURE"}, "fixture")
    assert caught.value.reason == "REFUSE_MISSING"


@pytest.mark.parametrize(
    "mutator,reason",
    [
        (lambda p: p.__setitem__("admitted_capture_id", "0" * 64), "REFUSE_IDENTITY"),
        (lambda p: p["forecast"].__setitem__("forecast_id", "not-a-sha256"), "REFUSE_HASH"),
        (lambda p: p["eligibility"].__setitem__("schema_version", "wrong"), "REFUSE_VERSION"),
        (lambda p: p.__setitem__("game_id", "2026_99_OTHER"), "REFUSE_GAME"),
        (lambda p: p["quote"].__setitem__("period", "h1"), "REFUSE_PERIOD"),
        (lambda p: p["quote"].__setitem__("line", 99.5), "REFUSE_LINE"),
        (lambda p: p["quote"].__setitem__("side", "AWAY"), "REFUSE_SIGN"),
        (lambda p: p["quote"].__setitem__("time", "2026-11-08T12:00:00Z"), "REFUSE_TIME"),
        (lambda p: p["cutoff"].__setitem__("decision_ts", "2026-11-08T10:00:00Z"), "REFUSE_CUTOFF"),
        (lambda p: p["capability"].__setitem__("bits", []), "REFUSE_CAPABILITY"),
        (lambda p: p["eligibility"].__setitem__("fixture", False), "REFUSE_QUALIFICATION"),
        (lambda p: p["cutoff"].__setitem__("as_of_ts", "2026-11-08T19:00:00Z"), "REFUSE_STALE"),
        (lambda p: p.pop("forecast", None), "REFUSE_PARTIAL"),
        (lambda p: p.__setitem__("cacheable", True), "REFUSE_CACHE"),
    ],
)
def test_export_refuses_mutated_chain(mutator, reason: str) -> None:
    mod = _load()
    payload = copy.deepcopy(_payload())
    mutator(payload)
    with pytest.raises(mod.NflExportRefuse) as caught:
        if "eligibility" in payload:
            try:
                mod.consume_fixture_eligibility(payload["eligibility"], "fixture")
            except mod.NflExportRefuse:
                raise
        mod.project_fixture_assembly_to_export(
            payload,
            consumer="fixture",
            home_team="Synthetic Home",
            away_team="Synthetic Away",
        )
    assert caught.value.reason == reason
    assert caught.value.actionable is False
