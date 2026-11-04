"""CLI: produce isolated fixtures + hand-off JSON. CERT=0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.services.nfl_owned_market_v1.produce import produce_artifacts
from src.services.nfl_owned_market_v1.profiles import handoff_interface


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="nfl_owned_market_v1 produce (CERT=0)")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="repository root (writes data/ops/nfl_owned_market_v1)",
    )
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    artifacts = produce_artifacts(repo_root=root)
    interface = handoff_interface(artifacts)
    handoff_path = root / "data/ops/nfl_owned_market_v1/HANDOFF_INTERFACE.json"
    handoff_path.write_text(
        json.dumps(interface, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {handoff_path}")
    print(f"trace_fixture {artifacts['hashes_doc']['profiles']['OWNED_MARKET_TRACE_V1']['fixture_sha256']}")
    print(
        "events_fixture "
        f"{artifacts['hashes_doc']['profiles']['SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1']['fixture_sha256']}"
    )
    print(f"code_hash {interface['code_hash']}")
    print("CERT=0 SYNTHETIC ready_for_A=true (B does not register)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
