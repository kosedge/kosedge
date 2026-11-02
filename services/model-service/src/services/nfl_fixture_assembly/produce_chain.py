"""Producer command for the opt-in offline A→B chain.

B consumes the written JSON. Refuse does not create or overwrite OUT.
Zero simulator / network / DB / jobs.

Usage (from services/model-service):
  PYTHONPATH=. python3 -m src.services.nfl_fixture_assembly.produce_chain \\
    --out /path/to/chain.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from src.services.nfl_fixture_assembly.assemble import (
    FORBIDDEN_CALL_ATTEMPTS,
    assemble_fixture_only,
)
from src.services.nfl_fixture_assembly.chain import chain_digest, serialize_fixture_chain
from src.services.nfl_fixture_assembly.contract import FixtureEnvelope, FixtureHardRefuse
from src.services.nfl_fixture_assembly.synth import synthetic_envelope


def produce_fixture_chain(
    *,
    dest: Optional[Path] = None,
    envelope: Optional[FixtureEnvelope] = None,
) -> dict:
    """Assemble then serialize. Raises FixtureHardRefuse before any dest write."""
    env = envelope if envelope is not None else synthetic_envelope()
    result = assemble_fixture_only(env)
    payload = serialize_fixture_chain(env, result)
    if dest is not None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return payload


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="t5194u fixture chain producer (CERT=0)")
    parser.add_argument("--out", required=True, help="destination JSON path")
    args = parser.parse_args(argv)
    dest = Path(args.out)
    prior = dest.read_bytes() if dest.exists() else None
    try:
        payload = produce_fixture_chain(dest=dest)
    except FixtureHardRefuse as exc:
        if prior is None:
            if dest.exists():
                dest.unlink()
        else:
            dest.write_bytes(prior)
        print(f"REFUSE {exc.result.value}: {exc.reason}", file=sys.stderr)
        return 2
    digest = chain_digest(payload)
    print(f"wrote {dest}")
    print(f"digest {digest}")
    print(f"forbidden_call_attempts {len(FORBIDDEN_CALL_ATTEMPTS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
