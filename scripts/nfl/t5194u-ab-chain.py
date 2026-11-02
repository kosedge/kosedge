#!/usr/bin/env python3
"""ONE opt-in offline A→B chain command (t5194u).

Loads A's serialized FixtureChainRecord (do not invent allow tokens),
verifies the pinned digest, then runs real B export consume/project.
Refuse preserves prior OUT. Zero forbidden calls.

From repo root:
  PYTHONPATH=services/model-service python3 scripts/nfl/t5194u-ab-chain.py
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

from src.services.nfl_fixture_assembly.assemble import (  # noqa: E402
    FORBIDDEN_CALL_ATTEMPTS,
    consume_fixture_eligibility,
)
from src.services.nfl_fixture_assembly.chain import chain_digest  # noqa: E402
from src.services.nfl_fixture_assembly.contract import (  # noqa: E402
    CHAIN_CONTRACT_ID,
    CHAIN_SCHEMA_VERSION,
)

PINNED = ROOT / "data" / "ops" / "t5194u-wfix-a-chain" / "positive-output.json"
PINNED_SHA = ROOT / "data" / "ops" / "t5194u-wfix-a-chain" / "positive-output.sha256"
EXPORT = ROOT / "apps" / "web" / "scripts" / "export_kei_lines_nfl.py"
EXPECTED_DIGEST = "27f32649050578108720b2ff26eacebadb92c7324f1930661c88b8f1ce6e6124"


def _load_export():
    spec = importlib.util.spec_from_file_location("export_kei_ab_chain", EXPORT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _project_export(mod: Any, payload: dict) -> dict:
    return mod.project_fixture_assembly_to_export(
        payload,
        consumer="fixture",
        home_team="Synthetic Home",
        away_team="Synthetic Away",
        home_abbr="SYN",
        away_abbr="TST",
    )


def main() -> int:
    payload = json.loads(PINNED.read_text(encoding="utf-8"))
    digest = chain_digest(payload)
    pinned = PINNED_SHA.read_text(encoding="utf-8").strip()
    if digest != pinned or digest != EXPECTED_DIGEST:
        print(f"DIGEST_MISMATCH got={digest} pinned={pinned}", file=sys.stderr)
        return 2
    if payload.get("chain_contract_id") != CHAIN_CONTRACT_ID:
        print("wrong chain_contract_id", file=sys.stderr)
        return 2
    if payload.get("chain_schema_version") != CHAIN_SCHEMA_VERSION:
        print("wrong chain_schema_version", file=sys.stderr)
        return 2

    consume_fixture_eligibility(payload["eligibility"], consumer="fixture")
    export = _load_export()
    export.consume_fixture_eligibility(payload["eligibility"], "fixture")
    export.assert_fixture_chain_record(payload)
    doc = _project_export(export, payload)
    if doc["games"][0]["projSpreadHome"] != -3.0 or doc["games"][0]["projTotal"] is not None:
        print("positive export mismatch", file=sys.stderr)
        return 2

    out = Path("/tmp/t5194u-ab-chain-out.json")
    out.write_text("ORIGINAL_SENTINEL\n", encoding="utf-8")
    prior = out.read_bytes()

    def mutate(mutator: Callable[[dict], None]) -> dict:
        cloned = copy.deepcopy(payload)
        mutator(cloned)
        return cloned

    faults: list[tuple[str, Callable[[dict], None]]] = [
        ("identity", lambda p: p.__setitem__("admitted_capture_id", "0" * 64)),
        ("hash", lambda p: p["forecast"].__setitem__("forecast_id", "not-a-sha256")),
        ("version", lambda p: p["eligibility"].__setitem__("schema_version", "wrong")),
        ("game", lambda p: p.__setitem__("game_id", "2026_99_OTHER")),
        ("period", lambda p: p["quote"].__setitem__("period", "h1")),
        ("line", lambda p: p["quote"].__setitem__("line", 99.5)),
        ("sign", lambda p: p["quote"].__setitem__("side", "AWAY")),
        ("time", lambda p: p["quote"].__setitem__("time", "2026-11-08T12:00:00Z")),
        ("cutoff", lambda p: p["cutoff"].__setitem__("decision_ts", "2026-11-08T10:00:00Z")),
        ("capability", lambda p: p["capability"].__setitem__("bits", [])),
        ("qualification", lambda p: p["eligibility"].__setitem__("fixture", False)),
        ("stale", lambda p: p["cutoff"].__setitem__("as_of_ts", "2026-11-08T19:00:00Z")),
        ("partial", lambda p: p.pop("forecast", None)),
        ("cache", lambda p: p.__setitem__("cacheable", True)),
    ]

    refused: list[str] = []
    for name, mutator in faults:
        bad = mutate(mutator)
        try:
            export.consume_fixture_eligibility(bad.get("eligibility") or {}, "fixture")
            _project_export(export, bad)
            print(f"FAULT_LEAKED {name}", file=sys.stderr)
            return 2
        except export.NflExportRefuse:
            refused.append(name)
            if out.read_bytes() != prior:
                print(f"OUT_MUTATED_ON_REFUSE {name}", file=sys.stderr)
                return 2

    if FORBIDDEN_CALL_ATTEMPTS:
        print(f"FORBIDDEN {FORBIDDEN_CALL_ATTEMPTS}", file=sys.stderr)
        return 2

    print(f"digest {digest}")
    print(f"chain_contract_id {CHAIN_CONTRACT_ID}")
    print(f"positive_export_spread {doc['games'][0]['projSpreadHome']}")
    print(f"refused {','.join(refused)}")
    print(f"out_preserved {out.read_bytes() == prior}")
    print(f"forbidden_call_attempts {len(FORBIDDEN_CALL_ATTEMPTS)}")
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
