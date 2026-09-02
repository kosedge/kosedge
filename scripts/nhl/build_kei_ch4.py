#!/usr/bin/env python3
"""NHL Chapter 4 — --kei-only emitter.

Reads Ch1 prior + Ch3 schedule/situation. Does not rematerialize Ch1/Ch2/Ch5
or retune Ch3 coeffs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/model-service"))

from src.services.nhl_season_engine.nhl_kei import (  # noqa: E402
    KEI_PACK_PATH,
    emit_kei_for_schedule,
)


def main() -> None:
    pack = emit_kei_for_schedule()
    KEI_PACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    KEI_PACK_PATH.write_text(json.dumps(pack, indent=2) + "\n", encoding="utf-8")
    fla = next(
        (
            g
            for g in pack["games"]
            if g.get("away") == "FLA" and g.get("home") == "CAR"
        ),
        pack["games"][0],
    )
    print(
        f"wrote {KEI_PACK_PATH.name} games={pack['game_count']} "
        f"FLA@CAR puck={fla['kei_puck_home']} total={fla['kei_total']} "
        f"wp={fla['kei_home_win_prob']} date={fla.get('date')}"
    )


if __name__ == "__main__":
    main()
