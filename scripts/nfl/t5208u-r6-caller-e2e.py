#!/usr/bin/env python3
"""ONE t5213u R6 synthetic E2E (CERT=0). Live A invoke → B seal.

79264 authorizes synthetic IF invocation ≠ real science EXEC.

From repo root:
  PYTHONPATH=services/model-service python3 scripts/nfl/t5208u-r6-caller-e2e.py
Expected: EXIT 0 · spy-positive call_r6_point_margin · INTEGRATION OK
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

from src.services.nfl_r6_caller.caller import (  # noqa: E402
    A_DEMO_PACKET,
    A_EXPECTED_BINDS,
    SPY,
    prove_real_mode_refuse,
    prove_ryan_cases,
    prove_seal_refuses,
    refuse_real_mode,
    run_live_a_e2e,
)
from src.services.nfl_r6_caller.contract import (  # noqa: E402
    PACKAGE_ID,
    R6Refuse,
    R6RefuseCode,
    pin_block,
)


def main(argv: list[str] | None = None) -> int:
    del argv
    pins = pin_block()
    print(f"package {PACKAGE_ID}")
    print("owner_clear 8926fa72")
    print("preserve_package fb792390")
    print(f"algorithm_tip {pins['algorithm_tip']}")
    print(f"if_tip {pins['if_tip']}")
    print(f"c_formula {pins['c_formula']}")
    print(f"output_kind {pins['output_kind']}")
    print(f"real_mode_authorized {str(pins['real_mode_authorized']).lower()}")

    SPY.install()
    SPY.reset()
    real = prove_real_mode_refuse()
    print(f"REAL_MODE_REFUSED {real['code']}")
    try:
        refuse_real_mode("PRODUCTION")
        print("REAL_MODE_LEAKED", file=sys.stderr)
        return 3
    except R6Refuse as exc:
        if exc.code != R6RefuseCode.REFUSE_REAL_MODE:
            print(f"REAL_MODE_WRONG {exc.code}", file=sys.stderr)
            return 3

    proof_root = Path(tempfile.mkdtemp(prefix="t5213u-r6-refuse-"))
    proofs = prove_seal_refuses(proof_root)
    print(f"DUP_REFUSED {proofs['duplicate']}")
    print(f"RACE_REFUSED {proofs['race']}")
    print(f"PARTIAL_WRITE_REFUSED {proofs['partial_write']}")
    print(f"LEFTOVER_TMP_REFUSED {proofs['leftover_tmp']}")
    if any(
        v != expected
        for v, expected in (
            (proofs["duplicate"], R6RefuseCode.REFUSE_DUPLICATE),
            (proofs["race"], R6RefuseCode.REFUSE_RACE),
            (proofs["partial_write"], R6RefuseCode.REFUSE_PARTIAL),
            (proofs["leftover_tmp"], R6RefuseCode.REFUSE_PARTIAL),
        )
    ):
        print("REFUSE_PROOF_FAIL", file=sys.stderr)
        return 3

    ryan_root = Path(tempfile.mkdtemp(prefix="t5213u-r6-ryan-"))
    ryan = prove_ryan_cases(ryan_root)
    print(f"MISSING_PINS_REFUSED {ryan['missing_pins']}")
    print(f"PREFIX_IF_PIN_REFUSED {ryan['prefix_if_pin']}")
    print(f"SCHEMA_AS_HASH_REFUSED {ryan['schema_as_hash']}")
    print(f"EMPTY_STATE_HASH_REFUSED {ryan['empty_state_hash']}")
    print(f"BAD_KICKOFF_REFUSED {ryan['bad_kickoff']}")
    print(f"KICKOFF_AS_SEAL_REFUSED {ryan['kickoff_as_seal']}")
    print(f"TAMPER_READ_REFUSED {ryan['tamper_read']}")
    print(f"TAMPER_SEAL_REFUSED {ryan['tamper_seal']}")
    expected_ryan = {
        "missing_pins": R6RefuseCode.REFUSE_PIN,
        "prefix_if_pin": R6RefuseCode.REFUSE_PIN,
        "schema_as_hash": R6RefuseCode.REFUSE_HASH,
        "empty_state_hash": R6RefuseCode.REFUSE_HASH,
        "bad_kickoff": R6RefuseCode.REFUSE_CUTOFF,
        "kickoff_as_seal": R6RefuseCode.REFUSE_CUTOFF,
        "tamper_read": R6RefuseCode.REFUSE_TAMPER,
        "tamper_seal": R6RefuseCode.REFUSE_TAMPER,
    }
    if any(ryan[key] != code for key, code in expected_ryan.items()):
        print(f"RYAN_PROOF_FAIL {ryan}", file=sys.stderr)
        return 3
    if SPY.a_calls != 0 or SPY.model_calls != 0:
        print(
            f"MODEL_CALLED_ON_REFUSE a={SPY.a_calls} model={SPY.model_calls}",
            file=sys.stderr,
        )
        return 3
    print("ZERO_MODEL_CALLS_ON_REFUSE true")

    dest = Path(tempfile.mkdtemp(prefix="t5213u-r6-ledger-"))
    try:
        result = run_live_a_e2e(ledger_root=dest, handoff_path=A_DEMO_PACKET)
    except R6Refuse as exc:
        print(f"A_LIVE_REFUSE {exc.code}: {exc.reason}", file=sys.stderr)
        print("INTEGRATION PARTIAL")
        return 2
    except Exception as exc:
        print(f"A_LIVE_ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        print("INTEGRATION PARTIAL")
        return 2

    print(f"a_path {result['a_path']}")
    print(f"a_api {result.get('a_api')}")
    print(f"a_tip {result.get('a_tip')}")
    print(f"means_source {result.get('means_source')}")
    print(f"a_calls {result.get('a_calls')}")
    print(f"model_calls {result.get('model_calls')}")
    print(f"replay_ok {result.get('replay_ok')}")
    print(f"packet_hash {result.get('packet_hash')}")
    print(f"history_hash {result.get('history_hash')}")
    print(f"config_hash {result.get('config_hash')}")
    print(f"code_hash {result.get('code_hash')}")
    cutoff = result.get("cutoff") or {}
    print(f"cutoff_utc {cutoff.get('cutoff_utc')}")
    print(f"seal_utc {cutoff.get('seal_utc')}")
    print(f"sealed_n {len(result['sealed'])}")
    if int(result.get("a_calls") or 0) < 1 or int(result.get("model_calls") or 0) < 1:
        print("SPY_NEGATIVE live A call missing", file=sys.stderr)
        return 3
    for key in ("packet_hash", "history_hash", "config_hash", "code_hash"):
        if result.get(key) != A_EXPECTED_BINDS[key]:
            print(f"BIND_MISMATCH {key}", file=sys.stderr)
            return 3
    if cutoff.get("cutoff_utc") != A_EXPECTED_BINDS["cutoff_utc"]:
        print("BIND_MISMATCH cutoff_utc", file=sys.stderr)
        return 3
    if cutoff.get("seal_utc") != A_EXPECTED_BINDS["seal_utc"]:
        print("BIND_MISMATCH seal_utc", file=sys.stderr)
        return 3
    if cutoff.get("seal_utc") != cutoff.get("cutoff_utc"):
        print("SEAL_NE_CUTOFF", file=sys.stderr)
        return 3
    for proj, row in zip(result.get("projected") or [], result["sealed"]):
        if_mean = row["arms"]["IF"]["mean"]
        c_mean = row["arms"]["C"]["mean"]
        print(
            f"seal {row['game_id']} if={if_mean} q2={proj.get('q2_mean')} "
            f"c={c_mean} seed={proj.get('seed')} id={row['seal_id']}"
        )
    print(json.dumps({"manifest_id": result["sealed"][0]["manifest_id"]}, separators=(",", ":")))
    print("INTEGRATION OK")
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
