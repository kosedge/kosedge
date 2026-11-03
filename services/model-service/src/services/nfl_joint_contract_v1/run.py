"""ONE command: freeze-intact → adapt → consume → handoff. CERT=0."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

from src.services.nfl_joint_contract_v1.adapter import adapt_literal_law
from src.services.nfl_joint_contract_v1.constants import KNOWN_SETTLEMENT_PROFILE, TASK_ID
from src.services.nfl_joint_contract_v1.consume import consume_literal_law
from src.services.nfl_joint_contract_v1.handoff import bind_handoff
from src.services.nfl_joint_contract_v1.hashes import sha256_text
from src.services.nfl_joint_contract_v1.refuse import JointContractRefuse
from src.services.nfl_joint_contract_v1.spy import (
    FORBIDDEN_CALL_ATTEMPTS,
    OutcomeReadSpy,
    run_spy_positive_control,
)


def _repo_root(root: Path | None) -> Path:
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[5]


def run_literal_law_command(
    *,
    dest_dir: Path,
    root: Path | None = None,
    write_receipt: bool = True,
) -> dict[str, Any]:
    repo = _repo_root(root)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    FORBIDDEN_CALL_ATTEMPTS.clear()
    spy = OutcomeReadSpy()
    spy_control = run_spy_positive_control()
    FORBIDDEN_CALL_ATTEMPTS.clear()

    adapted = adapt_literal_law(
        root=repo,
        settlement_profile=KNOWN_SETTLEMENT_PROFILE,
        outcome_spy=spy,
    )
    consumed = consume_literal_law(
        adapted,
        consumer="joint_literal",
        settlement_profile=KNOWN_SETTLEMENT_PROFILE,
        root=repo,
        outcome_spy=spy,
    )
    handoff = bind_handoff(consumed)
    body = dict(consumed)
    body["handoff"] = handoff
    body["spy_positive_control"] = spy_control
    body["status"] = "GATED_OK_AWAITING_CHIEF"
    body["ready_for_review"] = False
    body["self_accept"] = False
    body["accepted"] = False
    body["cert"] = 0
    body["task_id"] = TASK_ID
    body["not_integrated_through_evidence_gate"] = True

    if write_receipt:
        written = json.dumps(body, indent=2, sort_keys=True) + "\n"
        receipt = dest_dir / "CONSUME_RECEIPT.json"
        sample = dest_dir / "ADAPTER_SAMPLE.json"
        receipt.write_text(written, encoding="utf-8")
        sample.write_text(written, encoding="utf-8")
        body["receipt_sha256"] = sha256_text(written)
        body["_receipt_path"] = receipt.as_posix()
        body["_sample_path"] = sample.as_posix()
    if spy.reads != 0:
        raise JointContractRefuse(
            "outcome loader was read on the synthetic path",
            refuse_class="SPY",
        )
    return body


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    dest = Path(args[0]) if args else Path("/tmp/nfl-joint-contract-v1")
    try:
        result = run_literal_law_command(dest_dir=dest)
    except JointContractRefuse as exc:
        print(f"REFUSE [{exc.refuse_class}] {exc.reason}", file=sys.stderr)
        return 2
    print(f"status {result.get('status')}")
    print(f"freeze {result.get('freeze_receipt_hash')}")
    print(f"ready_for_review {str(result.get('ready_for_review')).lower()}")
    print("cert 0")
    print("not_integrated_through_evidence_gate true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
