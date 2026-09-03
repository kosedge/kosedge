"""Real-roster totals-guard path inventory + same-path locks (research only).

Purpose: refuse a fake / mixed unused-2025 real-roster holdout when
2023–24 live-style roster+SP+ packs are not reconstructable.

Does NOT write pack / KEI / enable kei_total divergence / unsat PLAY.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Set

from src.services.cfb_season_engine.totals_guard_holdout import (
    FIT_SEASONS,
    UNUSED_EVAL_SEASONS,
)

DATA_DIR = Path(__file__).resolve().parent / "data"

# Live-style packs present in-repo today (2026 season engine).
PACKAGED_REAL_ROSTER_2026 = DATA_DIR / "cfb_real_roster_snapshot_2026.json"
PACKAGED_EFFICIENCY_2025_CARRY_2026 = (
    DATA_DIR / "cfb_efficiency_snapshot_2025_carry_2026.json"
)

# Required for same-path fit (season Y uses prior-year SP+ + that year's roster).
REQUIRED_ROSTER_SEASONS = frozenset({2023, 2024, 2025})
REQUIRED_SP_PLUS_CARRIES = frozenset(
    {
        (2022, 2023),  # final-2022 SP+ carry into 2023
        (2023, 2024),
        (2024, 2025),
    }
)

PROXY_ROSTER_PATH = "hist_cal_league_avg_roster_qb"
REAL_ROSTER_PATH = "live_style_espn_roster_qb_units_sp_plus"

COS_SAME_PATH_LOCK = (
    "Fit and eval must share the SAME roster path. "
    "Do NOT mix proxy-fit λ onto a real-roster eval. "
    "If 2023–24 real roster/SP+ is not reconstructable: STOP."
)


def roster_snapshot_path(season: int) -> Path:
    return DATA_DIR / f"cfb_real_roster_snapshot_{int(season)}.json"


def efficiency_carry_path(prior_season: int, carry_to_season: int) -> Path:
    return (
        DATA_DIR
        / f"cfb_efficiency_snapshot_{int(prior_season)}_carry_{int(carry_to_season)}.json"
    )


def packaged_roster_seasons(*, data_dir: Optional[Path] = None) -> Set[int]:
    root = data_dir or DATA_DIR
    found: Set[int] = set()
    for path in root.glob("cfb_real_roster_snapshot_*.json"):
        stem = path.stem  # cfb_real_roster_snapshot_YYYY
        try:
            found.add(int(stem.rsplit("_", 1)[-1]))
        except ValueError:
            continue
    return found


def packaged_sp_plus_carries(
    *, data_dir: Optional[Path] = None
) -> Set[tuple[int, int]]:
    root = data_dir or DATA_DIR
    found: Set[tuple[int, int]] = set()
    for path in root.glob("cfb_efficiency_snapshot_*_carry_*.json"):
        # cfb_efficiency_snapshot_{prior}_carry_{carry}.json
        parts = path.stem.split("_")
        # ['cfb', 'efficiency', 'snapshot', prior, 'carry', carry]
        try:
            carry_idx = parts.index("carry")
            prior = int(parts[carry_idx - 1])
            carry = int(parts[carry_idx + 1])
        except (ValueError, IndexError):
            continue
        found.add((prior, carry))
    return found


def cfbd_key_present() -> bool:
    return bool(os.environ.get("CFBD_API_KEY") or os.environ.get("CFBD_KEY"))


def inventory(*, data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """What exists vs what a live-style 2023–25 holdout needs."""
    roster_years = packaged_roster_seasons(data_dir=data_dir)
    carries = packaged_sp_plus_carries(data_dir=data_dir)
    missing_rosters = sorted(REQUIRED_ROSTER_SEASONS - roster_years)
    missing_carries = sorted(REQUIRED_SP_PLUS_CARRIES - carries)
    return {
        "data_dir": str(data_dir or DATA_DIR),
        "packaged_roster_seasons": sorted(roster_years),
        "packaged_sp_plus_carries": [
            {"prior_season": a, "carry_to_season": b} for a, b in sorted(carries)
        ],
        "required_roster_seasons": sorted(REQUIRED_ROSTER_SEASONS),
        "required_sp_plus_carries": [
            {"prior_season": a, "carry_to_season": b}
            for a, b in sorted(REQUIRED_SP_PLUS_CARRIES)
        ],
        "missing_roster_seasons": missing_rosters,
        "missing_sp_plus_carries": [
            {"prior_season": a, "carry_to_season": b} for a, b in missing_carries
        ],
        "cfbd_api_key_present": cfbd_key_present(),
        "warehouse_historical_rosters_materialized": False,
        "notes": [
            "Live 2026 uses ESPN roster/QB/units + SP+ carry packs.",
            "Hist-cal 2022–2025 uses league-avg roster/QB + cfb_ratings (not SP+).",
            "Warehouse v1 did not materialize historical rosters.",
        ],
    }


def real_roster_path_reconstructable(
    *, data_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """True only when fit+eval years have packaged live-style roster and SP+."""
    inv = inventory(data_dir=data_dir)
    ok = (
        not inv["missing_roster_seasons"] and not inv["missing_sp_plus_carries"]
    )
    return {
        "reconstructable": ok,
        "fit_seasons": sorted(FIT_SEASONS),
        "eval_seasons": sorted(UNUSED_EVAL_SEASONS),
        "inventory": inv,
        "stop": not ok,
        "message": (
            "Real-roster path reconstructable — twin holdout may run."
            if ok
            else (
                "STOP — 2023–24/25 live-style roster/SP+ packs missing; "
                "do not invent a mix; do not retune from 2025; "
                "do not apply proxy-fit λ to a real-roster eval."
            )
        ),
    }


def assert_same_roster_path(
    fit_path: str,
    eval_path: str,
    *,
    proxy_lambda: Optional[float] = None,
) -> None:
    """Hard lock: fit and eval share one path; no proxy λ on real eval."""
    if fit_path != eval_path:
        raise AssertionError(
            f"same-path lock violated: fit={fit_path!r} eval={eval_path!r}. "
            f"{COS_SAME_PATH_LOCK}"
        )
    if eval_path == REAL_ROSTER_PATH and proxy_lambda is not None:
        raise AssertionError(
            "forbid mixing proxy-fit λ onto real-roster eval "
            f"(proxy_lambda={proxy_lambda}). {COS_SAME_PATH_LOCK}"
        )


def assert_no_eval_year_in_fit(seasons: Iterable[int]) -> None:
    bad = set(int(s) for s in seasons) & set(UNUSED_EVAL_SEASONS)
    if bad:
        raise AssertionError(
            f"unused eval year(s) leaked into fit set: {sorted(bad)}"
        )


def blocker_payload(*, data_dir: Optional[Path] = None) -> Dict[str, Any]:
    gate = real_roster_path_reconstructable(data_dir=data_dir)
    return {
        "verdict": "STOP" if gate["stop"] else "GO",
        "gate": gate,
        "product": {
            "apply_cfb_kei": False,
            "totals_guard_flag": "OFF",
            "kei_total": "identity",
            "play_flip": False,
        },
        "cos_lock": COS_SAME_PATH_LOCK,
        "proxy_path": PROXY_ROSTER_PATH,
        "real_path": REAL_ROSTER_PATH,
        "eval_table": None,
        "coefficients": None,
    }
