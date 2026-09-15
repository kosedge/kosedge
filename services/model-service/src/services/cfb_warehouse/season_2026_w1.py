"""2026 completed-game ingest scaffold — research only, W−1 cutoffs.

Does not mint KEI, fairs, or Edge Board tags. Does not opponent-adjust.
Does not download 2026 PBP unless the caller explicitly restores a file.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from src.services.cfb_warehouse.owned_metrics import (
    DEFINITIONS,
    METRIC_VERSION,
    drive_metrics,
    filter_plays_w_minus_1,
    opportunity_summary,
    rolling_form,
    team_game_raw_metrics,
)
from src.services.cfb_warehouse.owned_pbp import locate_season
from src.services.cfb_warehouse.paths import hd_mounted

SEASON = 2026
INGEST_PLAN = {
    "season": SEASON,
    "purpose": "research-only current-season raw metrics through W−1",
    "sources_in_priority": [
        "Owned SDV espn_cfb_pbp play_by_play_2026.parquet when published (same ingest path as 2021–2025)",
        "CFBD API /plays and /drives for completed 2026 games if SDV file is not yet on disk (auth required)",
    ],
    "not_sources": [
        "CFBD Starter Pack",
        "new vendor",
        "Mac SMB mount from Railway",
    ],
    "cutoff": "Predicting week W uses only plays with season=2026 and week < W (and available_at strictly before kickoff when a kickoff is known).",
    "outputs": "research JSON / parquet under data/cfb/research (gitignored bulk). Not season-engine request path.",
    "opponent_adjustment": "out of scope — separate KE ratings / adj-EPA work",
}


def w1_status(*, as_of_week: int) -> Dict[str, Any]:
    files = locate_season(SEASON, prefer_hd=True)
    return {
        "season": SEASON,
        "as_of_week": int(as_of_week),
        "hd_mounted": hd_mounted(),
        "pbp_source": files.source,
        "raw_path": files.raw_path,
        "core_path": files.core_path,
        "ready": files.source != "missing",
        "plan": INGEST_PLAN,
        "cutoff": DEFINITIONS["rolling_form"],
        "metric_version": METRIC_VERSION,
        "research_only": True,
        "opponent_adjusted": False,
    }


def features_for_week(
    plays: Sequence[Mapping[str, Any]],
    *,
    as_of_week: int,
) -> Dict[str, Any]:
    """Build raw W−1 features. Empty-safe if 2026 plays are absent."""
    prior = filter_plays_w_minus_1(plays, season=SEASON, as_of_week=as_of_week)
    games = team_game_raw_metrics(prior)
    form = rolling_form(prior, season=SEASON, as_of_week=as_of_week)
    drives = drive_metrics(prior)
    return {
        "season": SEASON,
        "as_of_week": int(as_of_week),
        "plays_used": len(prior),
        "max_week_included": max((int(p.get("week") or 0) for p in prior), default=0),
        "leakage_ok": all(int(p.get("week") or 99) < int(as_of_week) for p in prior),
        "team_games": len(games),
        "rolling_form_teams": len(form),
        "opportunity": opportunity_summary(drives),
        "rolling_form": form,
        "research_only": True,
        "opponent_adjusted": False,
        "status": "ok" if prior else "no_2026_plays_before_cutoff",
    }
