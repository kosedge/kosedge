"""Synthetic local-path fixtures only. No real seasons, no real game_ids."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.services.nfl_eval_prep.local_path import write_local_input_path


SYNTHETIC_SEASONS = (2016, 2017, 2018)


def _kickoff(season: int, week: int) -> str:
    # Deterministic fake kickoffs on a Thursday, far from any live slate.
    base = datetime(season, 9, 1, 17, 0, tzinfo=timezone.utc) + timedelta(days=7 * (week - 1))
    return base.isoformat()


def _as_of(season: int, week: int) -> str:
    kick = datetime.fromisoformat(_kickoff(season, week))
    return (kick - timedelta(hours=30)).isoformat()


def build_synthetic_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    features: list[dict[str, Any]] = []
    schedule: list[dict[str, Any]] = []
    for season in SYNTHETIC_SEASONS:
        for week in (1, 2, 3):
            gid = f"SYN-{season}-W{week:02d}-AAA-BBB"
            schedule.append(
                {
                    "game_id": gid,
                    "season": season,
                    "week": week,
                    "home": "AAA",
                    "away": "BBB",
                    "kickoff_utc": _kickoff(season, week),
                }
            )
            # Week-1 games have no prior week → omitted from features (excluded, not invented).
            if week == 1:
                continue
            features.append(
                {
                    "game_id": gid,
                    "season": season,
                    "week": week,
                    "feature_week": week - 1,
                    "as_of": _as_of(season, week),
                    "source": "synthetic",
                    "home_off_epa_5g": 0.02 * week,
                    "away_off_epa_5g": -0.01 * week,
                    "home_def_epa_allowed_5g": 0.01,
                    "away_def_epa_allowed_5g": 0.02,
                    "home_kav_net_5g": 0.05,
                    "away_kav_net_5g": -0.04,
                    "rest_days_home": 7.0,
                    "rest_days_away": 7.0,
                    "rest_observed": True,
                    "home_injury_impact": 0.0,
                    "away_injury_impact": 0.0,
                    "injury_observed": True,
                }
            )
    return features, schedule


def write_synthetic_bundle(root: Path | str) -> Path:
    features, schedule = build_synthetic_rows()
    write_local_input_path(
        root,
        manifest={
            "kind": "synthetic_nfl_eval_prep",
            "seasons": list(SYNTHETIC_SEASONS),
            "note": "Synthetic only. Not a historical evaluation.",
        },
        feature_rows=features,
        schedule_rows=schedule,
    )
    return Path(root)
