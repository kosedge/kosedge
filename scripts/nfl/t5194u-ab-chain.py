#!/usr/bin/env python3
"""ONE opt-in offline A→B chain command (t5194u / t5201u).

1. Invoke the real A producer to a TEMP destination.
2. Bind its actual common digest.
3. Run Python export + TS API / view-model / cache consumers + faults.

Pinned originals/OUT are never rewritten. Guard must be active before
claiming 0 forbidden-call attempts.

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
import os
import socket
import subprocess
import sys
import tempfile
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
from src.services.nfl_fixture_assembly.consume_chain import (  # noqa: E402
    consume_fixture_chain,
)
from src.services.nfl_fixture_assembly.contract import (  # noqa: E402
    CHAIN_CONTRACT_ID,
    CHAIN_SCHEMA_VERSION,
    FixtureEligibilityResult,
    FixtureHardRefuse,
)
from src.services.nfl_fixture_assembly.produce_chain import (  # noqa: E402
    produce_fixture_chain,
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
WEB = ROOT / "apps" / "web"
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


def _run_ts_consumers(chain_json: Path) -> None:
    env = {
        **os.environ,
        "T5201U_CHAIN_JSON": str(chain_json),
        "PYTHONPATH": str(MS),
    }
    cmd = [
        "pnpm",
        "exec",
        "vitest",
        "run",
        "__tests__/lib/nfl-fair-lines-ab-chain.test.ts",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(WEB),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise FixtureHardRefuse(
            FixtureEligibilityResult.REFUSE_VALIDATION,
            f"TS consumers failed rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}",
        )


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

    pinned_bytes = PINNED.read_bytes()
    pinned_sha_bytes = PINNED_SHA.read_bytes()
    pinned = PINNED_SHA.read_text(encoding="utf-8").strip()
    if pinned != EXPECTED_DIGEST:
        print(f"PINNED_DIGEST_MISMATCH pinned={pinned}", file=sys.stderr)
        return 2

    tmpdir = Path(tempfile.mkdtemp(prefix="t5201u-chain-"))
    dest = tmpdir / "produced-chain.json"
    produced = produce_fixture_chain(dest=dest)
    payload = produced
    digest = chain_digest(payload)
    if dest.read_text(encoding="utf-8") == "":
        print("PRODUCE_EMPTY", file=sys.stderr)
        return 2
    if PINNED.read_bytes() != pinned_bytes or PINNED_SHA.read_bytes() != pinned_sha_bytes:
        print("PINNED_MUTATED", file=sys.stderr)
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
        consume_fixture_chain(payload, consumer="fixture")
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
            ("hash_valid_format", lambda p: p["forecast"].__setitem__("forecast_id", "0" * 64)),
            (
                "joint_not_a_time",
                lambda p: (
                    p["cutoff"].__setitem__("decision_ts", "not-a-time"),
                    p["provenance"].__setitem__("decision_ts", "not-a-time"),
                ),
            ),
            (
                "missing_decision",
                lambda p: (
                    p["cutoff"].pop("decision_ts", None),
                    p["provenance"].pop("decision_ts", None),
                ),
            ),
            ("price_zero", lambda p: p["quote"].__setitem__("price", 0)),
            (
                "invalid_side",
                lambda p: (
                    p["quote"].__setitem__("side", "PUSH"),
                    p["forecast"].__setitem__("side", "PUSH"),
                ),
            ),
            ("price_fraction", lambda p: p["quote"].__setitem__("price", -110.5)),
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
        _run_ts_consumers(dest)
        if PINNED.read_bytes() != pinned_bytes or PINNED_SHA.read_bytes() != pinned_sha_bytes:
            raise FixtureHardRefuse(
                FixtureEligibilityResult.REFUSE_VALIDATION,
                "PINNED_MUTATED_AFTER_TS",
            )
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

    print(f"produced {dest}")
    print(f"digest {digest}")
    print(f"pinned_digest {pinned}")
    print(f"pinned_preserved {PINNED.read_bytes() == pinned_bytes}")
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
