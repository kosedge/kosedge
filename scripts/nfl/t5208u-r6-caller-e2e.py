#!/usr/bin/env python3
"""ONE t5208u R6 synthetic E2E command (CERT=0).

Refuse proofs always run. Positive IF/C consume uses Worker A's actual
synthetic file only — no fabricated IF mean.

From repo root:
  PYTHONPATH=services/model-service python3 scripts/nfl/t5208u-r6-caller-e2e.py
Expected when A is absent: EXIT 2 · INTEGRATION PARTIAL · A_OUTPUT_ABSENT
Expected when T5208U_A_SYNTHETIC_JSON points at A's file: EXIT 0 · INTEGRATION OK
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
    locate_a_output,
    prove_real_mode_refuse,
    prove_seal_refuses,
    refuse_real_mode,
    run_synthetic_e2e,
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
    print(f"algorithm_tip {pins['algorithm_tip']}")
    print(f"if_tip {pins['if_tip']}")
    print(f"c_formula {pins['c_formula']}")
    print(f"output_kind {pins['output_kind']}")
    print(f"real_mode_authorized {str(pins['real_mode_authorized']).lower()}")

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

    proof_root = Path(tempfile.mkdtemp(prefix="t5208u-r6-refuse-"))
    proofs = prove_seal_refuses(proof_root)
    print(f"DUP_REFUSED {proofs['duplicate']}")
    print(f"RACE_REFUSED {proofs['race']}")
    print(f"PARTIAL_WRITE_REFUSED {proofs['partial_write']}")
    print(f"LEFTOVER_TMP_REFUSED {proofs['leftover_tmp']}")
    if any(v != expected for v, expected in (
        (proofs["duplicate"], R6RefuseCode.REFUSE_DUPLICATE),
        (proofs["race"], R6RefuseCode.REFUSE_RACE),
        (proofs["partial_write"], R6RefuseCode.REFUSE_PARTIAL),
        (proofs["leftover_tmp"], R6RefuseCode.REFUSE_PARTIAL),
    )):
        print("REFUSE_PROOF_FAIL", file=sys.stderr)
        return 3

    found = locate_a_output()
    if found is None:
        print("A_OUTPUT_ABSENT")
        print("INTEGRATION PARTIAL")
        print("BLOCKER Worker A t5208u synthetic tip/output not landed")
        print("no fabricated IF mean")
        return 2

    dest = Path(tempfile.mkdtemp(prefix="t5208u-r6-ledger-"))
    try:
        result = run_synthetic_e2e(ledger_root=dest, a_path=found)
    except R6Refuse as exc:
        print(f"A_CONSUME_REFUSE {exc.code}: {exc.reason}", file=sys.stderr)
        print("INTEGRATION PARTIAL")
        return 2
    print(f"a_path {result['a_path']}")
    print(f"sealed_n {len(result['sealed'])}")
    for row in result["sealed"]:
        if_mean = row["arms"]["IF"]["mean"]
        c_mean = row["arms"]["C"]["mean"]
        print(f"seal {row['game_id']} if={if_mean} c={c_mean} id={row['seal_id'][:12]}")
    print(json.dumps({"manifest_id": result["sealed"][0]["manifest_id"]}, separators=(",", ":")))
    print("INTEGRATION OK")
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
