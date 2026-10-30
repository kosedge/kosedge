#!/usr/bin/env python3
"""Non-test invocation path for the t4838u offline Independent Fair caller.

DRAFT / engineering-only. Fail-closed. Never an E1 emit.

    PYTHONPATH=services/model-service python3 scripts/nfl/run_offline_if_caller_t4838u.py --dry-run
    PYTHONPATH=services/model-service python3 scripts/nfl/run_offline_if_caller_t4838u.py --packet
    PYTHONPATH=services/model-service python3 scripts/nfl/run_offline_if_caller_t4838u.py --invoke request.json

Railway / C10 / production deploy is not required and is not invoked.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

from src.services.nfl_offline_if_caller import (  # noqa: E402
    CALLER_MODE_OPERATIONAL,
    OfflineIfCallerReject,
    evaluate_caller,
    invoke_independent_fair,
    request_from_mapping,
    wiring_probe,
)


def _print(obj: object) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True, default=str))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline DRAFT Independent Fair caller (t4838u). Not E1."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Deterministic synthetic wiring probe + BLOCKED/CALLER_READY packet",
    )
    parser.add_argument(
        "--packet",
        action="store_true",
        help="Evaluate fail-closed gates and write the sealed packet",
    )
    parser.add_argument(
        "--invoke",
        metavar="JSON",
        help="Operational invoke of a request file (fail-closed; no E1 label)",
    )
    parser.add_argument(
        "--write-evidence",
        action="store_true",
        help="Write EVIDENCE.json / CALLER_PACKET / DRY_RUN under data/ops",
    )
    args = parser.parse_args(argv)

    if not (args.dry_run or args.packet or args.invoke):
        parser.error("one of --dry-run, --packet, --invoke is required")

    write = bool(args.write_evidence or args.dry_run or args.packet)

    if args.invoke:
        raw = json.loads(Path(args.invoke).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise SystemExit("invoke JSON must be an object")
        raw.setdefault("mode", CALLER_MODE_OPERATIONAL)
        request = request_from_mapping(raw)
        try:
            payload = invoke_independent_fair(request)
        except OfflineIfCallerReject as exc:
            _print(
                {
                    "status": "BLOCKED",
                    "e1_admissible": False,
                    "code": exc.code,
                    "message": exc.message,
                    "independent_fair_invoked": False,
                }
            )
            evaluate_caller(write=write)
            return 2
        _print(
            {
                "status": "BLOCKED" if payload.get("e1_admissible") else "INVOKED_NOT_E1",
                "e1_admissible": False,
                "independent_fair_invoked": True,
                "market_blend": payload.get("market_blend"),
                "forecast_class": payload.get("forecast_class"),
                "note": "Operational invoke returned. Not labeled E1. Through-W8 ACCEPT still required for OWNER E1 CLEAR.",
            }
        )
        evaluate_caller(write=write)
        return 0

    result = evaluate_caller(write=write)
    out = {
        "status": result.status,
        "blocked": result.blocked,
        "e1_admissible": result.e1_admissible,
        "codes": result.codes,
        "messages": result.messages,
        "independent_fair_invoked_operational": result.independent_fair_invoked,
        "market_blend": result.market_blend,
        "forecast_class": result.forecast_class,
        "wiring_digest": None if result.wiring is None else result.wiring.get("digest"),
        "evidence_sha256": result.evidence.get("implementation_sha256"),
    }
    if args.dry_run:
        out["wiring"] = {
            "forecast_class": (result.wiring or {}).get("forecast_class"),
            "e1_admissible": False,
            "market_blend": (result.wiring or {}).get("market_blend"),
            "digest": (result.wiring or {}).get("digest"),
            "note": (result.wiring or {}).get("note"),
        }
        # Keep mus off the CLI summary to avoid looking like an E1 slate.
        _ = wiring_probe
    _print(out)
    return 0 if result.status in {"CALLER_READY", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
