#!/usr/bin/env python3
"""NBA Chapter 4 — --kei-only emitter.

Reads Ch2 rebased + Ch3 schedule/situation. Does not rematerialize Ch1/Ch2/Ch5.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/model-service"))

from src.services.nba_season_engine.nba_kei import (  # noqa: E402
    KEI_PACK_PATH,
    emit_kei_for_schedule,
)


def main() -> None:
    pack = emit_kei_for_schedule()
    KEI_PACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    KEI_PACK_PATH.write_text(json.dumps(pack, indent=2) + "\n", encoding="utf-8")
    # Sample scorecard slice
    sample = pack["games"][:8]
    print(
        f"wrote {KEI_PACK_PATH.name} games={pack['game_count']} "
        f"sample_spread={sample[0]['kei_spread_home']} total={sample[0]['kei_total']}"
    )


if __name__ == "__main__":
    main()
