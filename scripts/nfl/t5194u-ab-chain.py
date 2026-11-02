#!/usr/bin/env python3
"""ONE opt-in offline A→B chain command (t5194u).

Loads A's serialized FixtureChainRecord (do not invent allow tokens),
verifies the pinned digest, then runs real B export consume/project.
Activates A's shared guard; last_guard_report()['guard_active'] must be
true before claiming 0 attempts. Refuse preserves prior OUT.

From repo root:
  PYTHONPATH=services/model-service python3 scripts/nfl/t5194u-ab-chain.py
  PYTHONPATH=services/model-service python3 scripts/nfl/t5194u-ab-chain.py --probe-forbidden
"""

from __future__ import annotations

import argparse
import copy
import importlib
import importlib.util
import json
import socket
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
    FixtureEligibilityResult,
    FixtureHardRefuse,
)
from src.services.nfl_fixture_assembly.guard import (  # noqa: E402
    chain_guard,
    guard_active,
    last_guard_report,
    run_under_chain_guard,
)

PINNED = ROOT / "data" / "ops" / "t5194u-wfix-a-chain" / "positive-output.json"
PINNED_SHA = ROOT / "data" / "ops" / "t5194u-wfix-a-chain" / "positive-output.sha256"
EXPORT = ROOT / "apps" / "web" / "scripts" / "export_kei_lines_nfl.py"
EXPECTED_DIGEST = "27f32649050578108720b2ff26eacebadb92c7324f1930661c88b8f1ce6e6124"
OUT = Path("/tmp/t5194u-ab-chain-out.json")


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


def _print_report(*, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    report = last_guard_report()
    print(f"guard_active {str(bool(report['guard_active'])).lower()}")
    print(f"forbidden_call_attempts {report['forbidden_call_attempts']}")
    if extra:
        for key, value in extra.items():
            print(f"{key} {value}")
    return report


def _probe_forbidden() -> None:
    sys.modules.pop("src.services.nfl_simulator", None)
    hits = 0
    try:
        importlib.import_module("src.services.nfl_simulator")
    except FixtureHardRefuse:
        hits += 1
    try:
        socket.socket().connect(("203.0.113.1", 9))
    except FixtureHardRefuse:
        hits += 1
    try:
        socket.getaddrinfo("example.test", 80)
    except FixtureHardRefuse:
        hits += 1
    if hits < 2:
        raise AssertionError(f"expected import+socket attempts, got {FORBIDDEN_CALL_ATTEMPTS}")
    raise FixtureHardRefuse(
        FixtureEligibilityResult.REFUSE_QUALIFICATION,
        "chain path observed forbidden import and socket",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="t5194u A→B chain (CERT=0)")
    parser.add_argument(
        "--probe-forbidden",
        action="store_true",
        help="negative: real forbidden import+connect; refuse usable output",
    )
    args = parser.parse_args(argv)

    payload = json.loads(PINNED.read_text(encoding="utf-8"))
    digest = chain_digest(payload)
    pinned = PINNED_SHA.read_text(encoding="utf-8").strip()
    if digest != pinned or digest != EXPECTED_DIGEST:
        print(f"DIGEST_MISMATCH got={digest} pinned={pinned}", file=sys.stderr)
        return 2

    OUT.write_text("ORIGINAL_SENTINEL\n", encoding="utf-8")
    prior = OUT.read_bytes()

    if args.probe_forbidden:
        FORBIDDEN_CALL_ATTEMPTS.clear()
        usable = None
        try:
            def _run() -> None:
                if not guard_active():
                    raise FixtureHardRefuse(
                        FixtureEligibilityResult.REFUSE_QUALIFICATION,
                        "produce_chain guard_active is not true",
                    )
                _probe_forbidden()
                export = _load_export()
                raise AssertionError(f"forbidden import should have refused: {_project_export(export, payload)}")

            run_under_chain_guard(_run)
        except FixtureHardRefuse:
            usable = None
        except Exception:
            usable = None
        report = last_guard_report()
        if not report["guard_active"]:
            print("guard_active false", file=sys.stderr)
            return 3
        if report["forbidden_call_attempts"] < 2:
            print(f"PROBE_DID_NOT_INCREMENT {report['attempts']}", file=sys.stderr)
            return 2
        if usable is not None:
            print("PROBE_LEAKED_USABLE_OUTPUT", file=sys.stderr)
            return 2
        if OUT.read_bytes() != prior:
            print("OUT_MUTATED_ON_REFUSE", file=sys.stderr)
            return 2
        _print_report()
        print("PROBE_REFUSED")
        return 2

    if payload.get("chain_contract_id") != CHAIN_CONTRACT_ID:
        print("wrong chain_contract_id", file=sys.stderr)
        return 2
    if payload.get("chain_schema_version") != CHAIN_SCHEMA_VERSION:
        print("wrong chain_schema_version", file=sys.stderr)
        return 2

    export = _load_export()

    def _consume_and_project() -> dict:
        if not guard_active():
            raise FixtureHardRefuse(
                FixtureEligibilityResult.REFUSE_QUALIFICATION,
                "ab-chain guard_active is not true",
            )
        consume_fixture_eligibility(payload["eligibility"], consumer="fixture")
        export.consume_fixture_eligibility(payload["eligibility"], "fixture")
        export.assert_fixture_chain_record(payload)
        doc = _project_export(export, payload)
        if doc["games"][0]["projSpreadHome"] != -3.0 or doc["games"][0]["projTotal"] is not None:
            raise FixtureHardRefuse(
                FixtureEligibilityResult.REFUSE_VALIDATION,
                "positive export mismatch",
            )

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
                raise FixtureHardRefuse(
                    FixtureEligibilityResult.REFUSE_VALIDATION,
                    f"FAULT_LEAKED {name}",
                )
            except export.NflExportRefuse:
                refused.append(name)
                if OUT.read_bytes() != prior:
                    raise FixtureHardRefuse(
                        FixtureEligibilityResult.REFUSE_VALIDATION,
                        f"OUT_MUTATED_ON_REFUSE {name}",
                    )
        doc["refused"] = refused
        return doc

    try:
        with chain_guard() as state:
            if not state.active or not guard_active():
                raise FixtureHardRefuse(
                    FixtureEligibilityResult.REFUSE_QUALIFICATION,
                    "ab-chain guard_active is not true",
                )
            doc = _consume_and_project()
    except FixtureHardRefuse as exc:
        report = last_guard_report()
        print(f"REFUSE {exc.result.value}: {exc.reason}", file=sys.stderr)
        print(f"guard_active {str(bool(report['guard_active'])).lower()}")
        print(f"forbidden_call_attempts {report['forbidden_call_attempts']}")
        return 2

    report = last_guard_report()
    if not report["guard_active"]:
        print("guard_active false", file=sys.stderr)
        return 3
    if report["forbidden_call_attempts"]:
        print(f"FORBIDDEN {report['attempts']}", file=sys.stderr)
        return 2

    print(f"digest {digest}")
    print(f"chain_contract_id {CHAIN_CONTRACT_ID}")
    print(f"positive_export_spread {doc['games'][0]['projSpreadHome']}")
    print(f"refused {','.join(doc['refused'])}")
    print(f"out_preserved {OUT.read_bytes() == prior}")
    print("guard_active true")
    print(f"forbidden_call_attempts {report['forbidden_call_attempts']}")
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
