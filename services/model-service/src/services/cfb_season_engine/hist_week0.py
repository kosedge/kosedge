"""Historical Week-0 reconstruction inventory (research only).

Documents what can be rebuilt for 2023–2025 without leaking 2026
information. Does not write KEI, change priors, or unseal 2025 residuals.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from src.services.cfb_season_engine.totals_guard_holdout import (
    FIT_SEASONS,
    UNUSED_EVAL_SEASONS,
)

DATA_DIR = Path(__file__).resolve().parent / "data"
RAW_DIR_DEFAULT = Path(__file__).resolve().parents[5] / "data" / "cfb" / "raw"

# Same-path live construction (2026).
LIVE_PATH_NAME = "live_style_espn_roster_qb_units_sp_plus"
# Honest reconstructable path in this environment (no CFBD, no insider SP+).
RECON_PATH_NAME = "year_locked_espn_core_roster_plus_sdv_adj_epa"
PROXY_PATH_NAME = "hist_cal_league_avg_roster_qb"

FIELD_AUDIT: Dict[str, Dict[str, Any]] = {
    "espn_core_athletes_year_locked": {
        "needed_for": "position / class / experience on Week-0 identity",
        "status": "reconstructable",
        "source": "sports.core.api.espn.com seasons/{Y}/teams/{id}/athletes",
        "notes": (
            "Year-specific counts (2024≠2026). Site roster ?season=Y ignores "
            "the year and returns the current 2026 club — must not be used."
        ),
    },
    "espn_site_roster_season_param": {
        "needed_for": "2026-style packaged roster",
        "status": "not_year_locked",
        "source": "site.web.api.espn.com .../roster?season=Y",
        "notes": "HTTP 200 with empty groups or current-season athletes. Forbidden.",
    },
    "connelly_sp_plus_prior_year": {
        "needed_for": "live 2026 efficiency carry (off_eff/def_eff from SP+)",
        "status": "missing_2022_2023_2024",
        "source": "CFBD /ratings/sp or ESPN insider final tables",
        "notes": (
            "2025 final SP+ is public and already packaged for 2026 carry. "
            "2022–2024 finals are ESPN Insider (no <tr> in HTML) and CFBD 401. "
            "Do not invent tables from search snippets. Do not reuse 2025 SP+ "
            "as a prior for 2023–25 (future leak)."
        ),
    },
    "sdv_cfb_ratings_adj_epa": {
        "needed_for": "opponent-adjusted efficiency proxy when SP+ is missing",
        "status": "available_not_sp_plus",
        "source": "sportsdataverse-data cfb_ratings_{Y}.csv",
        "notes": (
            "Already used by hist-cal. Not Connelly SP+. Label every row. "
            "Same-path lock: this is NOT the 2026 live efficiency feed."
        ),
    },
    "recruiting_capital": {
        "needed_for": "2026 unit talent (0.62 weight) and roster_strength",
        "status": "unminted",
        "source": "CFBD /recruiting/teams (keyed) or year-specific prior pack",
        "notes": (
            "2026 curated recruiting priors must not be applied to 2023–25. "
            "Without CFBD, recruiting stays 50 / unminted."
        ),
    },
    "portal_team_history": {
        "needed_for": "2026 portal-in heuristic (athlete bio teamHistory)",
        "status": "not_fetched",
        "source": "ESPN athlete bio (one extra GET per player)",
        "notes": (
            "2026 pack already documents portal-out as incomplete. Historical "
            "portal left unminted (is_portal=false) to avoid a second 70k fetch "
            "and to avoid pretending we have a departure feed."
        ),
    },
    "qb_prior_year_attempts": {
        "needed_for": "2026 QB talent from 2025 pass attempts",
        "status": "unminted",
        "source": "ESPN athlete overview career splits",
        "notes": "Not fetched. QB class from experience abbreviation only.",
    },
    "coaching_continuity": {
        "needed_for": "new HC/OC/DC week-decayed points",
        "status": "unminted_assume_returning",
        "source": "year-specific staff file (not in repo)",
        "notes": "Do not copy 2026 coaching flags onto 2023–25.",
    },
    "home_field_buckets": {
        "needed_for": "variable HFA",
        "status": "2026_venue_prior_documented",
        "source": "cfb_fbs_team_priors_2026 home_field",
        "notes": (
            "Venues persist more than rosters. Used as a contemporaneous venue "
            "prior and labeled. Not a 2026 efficiency leak."
        ),
    },
    "cfbd_api_key": {
        "needed_for": "SP+ + recruiting + returning production",
        "status": "absent",
        "source": "CFBD_API_KEY / CFBD_KEY",
        "notes": "Unauthorized without Bearer token.",
    },
}


def cfbd_key_present() -> bool:
    return bool(os.environ.get("CFBD_API_KEY") or os.environ.get("CFBD_KEY"))


def reconstruction_inventory() -> Dict[str, Any]:
    return {
        "live_path": LIVE_PATH_NAME,
        "reconstructable_path": RECON_PATH_NAME,
        "proxy_path": PROXY_PATH_NAME,
        "cfbd_api_key_present": cfbd_key_present(),
        "same_as_2026_live_path": False,
        "fields": FIELD_AUDIT,
        "fit_seasons": sorted(FIT_SEASONS),
        "sealed_eval_seasons": sorted(UNUSED_EVAL_SEASONS),
        "stop_same_path": True,
        "stop_reason": (
            "Connelly SP+ finals for 2022–2024 and year-specific recruiting "
            "are not reconstructable in this environment. A 2023–25 universe "
            "built here is ESPN class/position + SDV adj-EPA — not the 2026 "
            "live stack. Do not fit λ on this path and call it live-path OOS."
        ),
    }


def assert_2025_sealed(*, open_2025: bool, freeze_path: Path | None) -> None:
    """Refuse 2025 residual scoring until a 2023–24 freeze file exists."""
    if not open_2025:
        return
    if freeze_path is None or not Path(freeze_path).is_file():
        raise RuntimeError(
            "2025 is sealed. Will not score 2025 residuals until a 2023–24 "
            "freeze file exists (λ / offset / path name locked). "
            "Do not peek at 2025 to choose λ."
        )
