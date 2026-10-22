"""L-1 same-week join and L-2 uncapped-week contracts (78f5ee7e).

These fragments document the production leak and the rebuild fix. Production
``ingest.py`` / ``tasks.py`` are not rewritten by this module. The rebuild
path must use the FIXED contracts only.

L-1 (TEMPORAL): ``nfl_dp_team_rolling_features_weekly`` is built with
``ROWS BETWEEN … AND CURRENT ROW`` then joined at ``h.week = s.week``. The
week-W row therefore includes game W.

L-2 (TEMPORAL): ``_fetch_rolling_feature_latest_rows`` allows
``week_cap IS NULL``, which takes the latest week of the season (future
weeks relative to the game).

L-3: rest defaults to 7.0 and injury impact defaults to 0.0. Flag, do not
silently treat as observed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Optional, Sequence


# Exact leaky fragments copied from the production files they live in.
# Do not "fix" these strings; they are the audit baseline.

L1_LEAKY_JOIN = """
LEFT JOIN nfl_dp_team_rolling_features_weekly h
  ON h.season = s.season AND h.week = s.week AND h.team = s.home_team
LEFT JOIN nfl_dp_team_rolling_features_weekly a
  ON a.season = s.season AND a.week = s.week AND a.team = s.away_team
""".strip()

L1_FIXED_JOIN = """
LEFT JOIN LATERAL (
  SELECT * FROM nfl_dp_team_rolling_features_weekly h
  WHERE h.season = s.season AND h.team = s.home_team AND h.week < s.week
  ORDER BY h.week DESC
  LIMIT 1
) h ON TRUE
LEFT JOIN LATERAL (
  SELECT * FROM nfl_dp_team_rolling_features_weekly a
  WHERE a.season = s.season AND a.team = s.away_team AND a.week < s.week
  ORDER BY a.week DESC
  LIMIT 1
) a ON TRUE
""".strip()

L1_LEAKY_WINDOW = "ROWS BETWEEN 4 PRECEDING AND CURRENT ROW"
L1_FIXED_WINDOW = "ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING"

L1_SITES = (
    "services/model-service/data_platform_nfl/ingest.py:materialize_matchup_features_from_usage",
    "scripts/nfl/historical_market_backtest.py:main (hf.week = sch.week)",
    "services/model-service/src/tasks.py:_load_team_strength_priors as_of_week=game week",
)

L2_LEAKY_WEEK_CAP = "(CAST(:week_cap AS int) IS NULL OR week <= CAST(:week_cap AS int))"
L2_FIXED_WEEK_CAP = "week <= CAST(:week_cap AS int)"

L2_SITES = (
    "services/model-service/src/tasks.py:_week_cap_nullable_predicate",
    "services/model-service/src/tasks.py:_fetch_rolling_feature_latest_rows",
)


@dataclass(frozen=True)
class LeakFlag:
    code: str
    game_id: str
    field: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def leak_fix_diff() -> dict[str, Any]:
    """Machine-readable L-1 / L-2 current-vs-fixed contract."""
    return {
        "L-1": {
            "name": "same_week_join",
            "class": "TEMPORAL_LEAKAGE",
            "leaky_join": L1_LEAKY_JOIN,
            "fixed_join": L1_FIXED_JOIN,
            "leaky_window": L1_LEAKY_WINDOW,
            "fixed_window": L1_FIXED_WINDOW,
            "sites": list(L1_SITES),
            "rule": "feature_week < game_week; rolling window must not include the predicted game",
        },
        "L-2": {
            "name": "uncapped_week",
            "class": "TEMPORAL_LEAKAGE",
            "leaky_predicate": L2_LEAKY_WEEK_CAP,
            "fixed_predicate": L2_FIXED_WEEK_CAP,
            "sites": list(L2_SITES),
            "rule": "week_cap is required and must be < game_week",
        },
        "L-3": {
            "name": "defaulted_rest_or_injury",
            "class": "MISSINGNESS_FLAG",
            "rule": "None/missing rest or injury is flagged; never silently 7.0 / 0.0 as observed",
        },
        "production_rewritten": False,
    }


def require_week_cap(week_cap: Optional[int], *, game_week: int) -> int:
    """L-2 fix: refuse uncapped lookups. Cap must be an int strictly before game week."""
    if week_cap is None:
        raise ValueError("L-2: week_cap is required (uncapped week is forbidden)")
    cap = int(week_cap)
    gw = int(game_week)
    if cap >= gw:
        raise ValueError(f"L-2: week_cap={cap} must be < game_week={gw}")
    if cap < 1:
        raise ValueError(f"L-2: week_cap={cap} is not a usable prior week")
    return cap


def apply_strict_week_join(
    *,
    game_week: int,
    feature_week: Optional[int],
) -> bool:
    """Return True iff a rolling/matchup feature week is legal for the game."""
    if feature_week is None:
        return False
    return int(feature_week) < int(game_week)


def flag_l3_defaults(
    row: Mapping[str, Any],
    *,
    game_id: str,
    rest_keys: Sequence[str] = ("rest_days_home", "rest_days_away"),
    injury_keys: Sequence[str] = ("home_injury_impact", "away_injury_impact"),
    rest_observed_key: str = "rest_observed",
    injury_observed_key: str = "injury_observed",
) -> list[LeakFlag]:
    """Flag defaulted rest (7.0) / injury (0.0) when not marked observed."""
    flags: list[LeakFlag] = []
    rest_observed = row.get(rest_observed_key)
    injury_observed = row.get(injury_observed_key)
    for key in rest_keys:
        if key not in row:
            flags.append(LeakFlag("L-3", game_id, key, "rest_missing"))
            continue
        if row[key] is None:
            flags.append(LeakFlag("L-3", game_id, key, "rest_null"))
            continue
        if rest_observed is False or (
            rest_observed is None and float(row[key]) == 7.0
        ):
            flags.append(LeakFlag("L-3", game_id, key, "rest_defaulted_or_unmarked_7"))
    for key in injury_keys:
        if key not in row:
            flags.append(LeakFlag("L-3", game_id, key, "injury_missing"))
            continue
        if row[key] is None:
            flags.append(LeakFlag("L-3", game_id, key, "injury_null"))
            continue
        if injury_observed is False or (
            injury_observed is None and float(row[key]) == 0.0
        ):
            flags.append(
                LeakFlag("L-3", game_id, key, "injury_defaulted_or_unmarked_0")
            )
    return flags
