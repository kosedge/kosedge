#!/usr/bin/env python3
"""K-2 receipt: reproduce config_hash and bound hash from stated inputs.

IMV runs nothing. This script is the deposited receipt constructor.
Old inputs must reproduce:
  config  0d491abef53cb67e82106dda184fb40fbe21fc3883afd8313fd87108cf40d6cb
  bound   638198a551ad192180d635a8edd1406b5aa8f1f47fbb026a98332ffee09e7db5
New values use the same NFL_TOTALS_* (all unset) + protocol id + --code-sha.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
sys.path.insert(0, str(ROOT))

from src.services.nfl_injury_null_contract import (  # noqa: E402
    APPLICATION_SITE,
    ENGINEERING_CODE_SHA_D4_V1,
    FIT_PROTOCOL_ID,
    LEDGER_VERSION,
    NFL_TOTALS_ENV_KEYS,
    bound_hash,
    config_hash,
    resolve_nfl_totals_env,
)

OLD_CONFIG = "0d491abef53cb67e82106dda184fb40fbe21fc3883afd8313fd87108cf40d6cb"
OLD_BOUND = "638198a551ad192180d635a8edd1406b5aa8f1f47fbb026a98332ffee09e7db5"


def _empty_totals_env() -> dict[str, str]:
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--code-sha",
        default="",
        help="Full 40-hex git sha for the new bound hash (PR head).",
    )
    args = parser.parse_args()
    env = _empty_totals_env()
    resolved = resolve_nfl_totals_env(env)
    old_config = config_hash(env=env)
    old_bound = bound_hash(code_sha=ENGINEERING_CODE_SHA_D4_V1, env=env)
    new_config = config_hash(env=env)
    new_code = str(args.code_sha or "").strip()
    new_bound = bound_hash(code_sha=new_code, env=env) if new_code else None

    lines = [
        "NFL injury config/bound hash receipt (K-2)",
        f"protocol={FIT_PROTOCOL_ID}",
        f"ledger_version={LEDGER_VERSION}",
        f"application_site={APPLICATION_SITE}",
        f"nfl_totals_keys={len(NFL_TOTALS_ENV_KEYS)}",
        "nfl_totals_state=all unset (legal C-9)",
        f"resolved_nulls={sum(1 for v in resolved.values() if v is None)}/{len(resolved)}",
        "",
        "OLD INPUTS (D-4 v1)",
        f"  extra={{}}",
        f"  config_hash={old_config}",
        f"  expected_config={OLD_CONFIG}",
        f"  config_match={old_config == OLD_CONFIG}",
        f"  extra={{protocol={FIT_PROTOCOL_ID}, code_sha={ENGINEERING_CODE_SHA_D4_V1}}}",
        f"  bound_hash={old_bound}",
        f"  expected_bound={OLD_BOUND}",
        f"  bound_match={old_bound == OLD_BOUND}",
        "",
        "NEW INPUTS (this head)",
        f"  extra={{}}",
        f"  config_hash={new_config}",
        f"  extra={{protocol={FIT_PROTOCOL_ID}, code_sha={new_code or 'UNSET'}}}",
        f"  bound_hash={new_bound or 'UNSET'}",
    ]
    sys.stdout.write("\n".join(lines) + "\n")
    if old_config != OLD_CONFIG or old_bound != OLD_BOUND:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
