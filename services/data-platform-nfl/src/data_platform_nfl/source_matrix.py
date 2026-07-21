"""Executable source fallback matrix for subscription-grade NFL data ownership.

Primary = preferred production source.
Fallback = used when primary is unavailable or fails freshness.
Degraded = product behavior when neither source can refresh the field.
"""

from __future__ import annotations

from typing import Any, Dict, List

# max_age_hours: soft SLO for "fresh enough for paid boards" during the season.
SOURCE_FALLBACK_MATRIX: List[Dict[str, Any]] = [
    {
        "domain": "schedules_scores",
        "primary": "nflverse.load_schedules",
        "fallback": "espn_scoreboard",
        "owned_tables": ["nfl_dp_schedules"],
        "max_age_hours_in_season": 36,
        "degraded_mode": "freeze_last_known_schedule; mark boards historical_only",
    },
    {
        "domain": "play_by_play",
        "primary": "nflverse.load_pbp",
        "fallback": None,
        "owned_tables": ["nfl_dp_raw_objects", "nfl_dp_play_by_play"],
        "max_age_hours_in_season": 48,
        "degraded_mode": "reuse_owned_history; block new usage rematerialization; alert critical",
        "notes": "No free drop-in PBP replacement. Licensed feed required for true independence.",
    },
    {
        "domain": "player_game_stats",
        "primary": "nflverse.load_player_stats",
        "fallback": None,
        "owned_tables": ["nfl_dp_player_game_stats"],
        "max_age_hours_in_season": 48,
        "degraded_mode": "serve last owned week; suppress PLAY stake tags",
    },
    {
        "domain": "team_game_stats",
        "primary": "nflverse.load_team_stats",
        "fallback": "nfl_com.team_stats",
        "owned_tables": ["nfl_dp_team_game_stats", "nfl_dp_raw_objects"],
        "max_age_hours_in_season": 48,
        "degraded_mode": "serve last owned week",
    },
    {
        "domain": "injuries",
        "primary": "nflverse.load_injuries",
        "fallback": "nfl_com.rosters_status_signals",
        "owned_tables": ["nfl_dp_injuries"],
        "max_age_hours_in_season": 24,
        "degraded_mode": "show_stale_injury_banner; widen uncertainty; suppress thin-edge PLAY",
    },
    {
        "domain": "rosters",
        "primary": "nfl_com.rosters",
        "fallback": "nflverse.load_rosters",
        "owned_tables": ["nfl_dp_rosters"],
        "max_age_hours_in_season": 72,
        "degraded_mode": "freeze_last_roster_snapshot",
    },
    {
        "domain": "depth_charts",
        "primary": "nflverse.load_depth_charts",
        "fallback": "inferred_from_usage_injuries",
        "owned_tables": ["nfl_dp_official_depth_charts", "nfl_dp_depth_chart_weekly"],
        "max_age_hours_in_season": 72,
        "degraded_mode": "use_inferred_depth_only; flag role_confidence_down",
    },
    {
        "domain": "snap_counts",
        "primary": "nflverse.load_snap_counts",
        "fallback": "pbp_derived_team_snap_share",
        "owned_tables": ["nfl_dp_snap_counts_weekly", "nfl_player_projection_features_weekly"],
        "max_age_hours_in_season": 48,
        "degraded_mode": "fall_back_to_pbp_proxy_shares",
    },
    {
        "domain": "standings_team_intel",
        "primary": "nfl_com.standings",
        "fallback": "derived_from_schedules",
        "owned_tables": ["nfl_dp_standings_weekly"],
        "max_age_hours_in_season": 36,
        "degraded_mode": "derive_from_owned_schedules",
    },
    {
        "domain": "vegas_player_props",
        "primary": "the_odds_api",
        "fallback": "owned_odds_snapshots_only",
        "owned_tables": ["nfl_player_prop_market_snapshots", "odds_snapshots"],
        "max_age_hours_in_season": 6,
        "degraded_mode": "fair_lines_only; hide +EV PLAY until odds refresh",
        "notes": "Independent of nflverse. Credits and key rotation are first-class ops.",
    },
    {
        "domain": "closing_game_lines_historical",
        "primary": "nflverse.schedules.spread_line/total_line",
        "fallback": "owned_market_history",
        "owned_tables": ["nfl_dp_schedules", "nfl_market_projections"],
        "max_age_hours_in_season": None,
        "degraded_mode": "train_on_owned_history_only",
    },
]


LICENSED_FEED_EVALUATION: Dict[str, Any] = {
    "status": "planned_not_integrated",
    "recommended_order": [
        {
            "vendor": "SportsDataIO",
            "fit": "rosters, injuries, scores, depth, basic stats",
            "priority": 1,
        },
        {
            "vendor": "Sportradar",
            "fit": "enterprise scores/PBP-adjacent feeds; higher cost",
            "priority": 2,
        },
        {
            "vendor": "Opta / Stats Perform",
            "fit": "advanced team/player; evaluate only if product needs proprietary charting",
            "priority": 3,
        },
    ],
    "decision_gate": (
        "Buy a licensed feed when (a) nflverse becomes paid/unavailable, or "
        "(b) paid subscribers require <24h injury/PBP freshness SLOs that free sources cannot meet."
    ),
    "adapter_contract": "Write into nfl_dp_raw_objects with source=<vendor> then normalize into existing typed tables.",
}


def source_matrix_payload() -> Dict[str, Any]:
    return {
        "version": "nfl-source-matrix-v1",
        "domains": SOURCE_FALLBACK_MATRIX,
        "licensed_feed_evaluation": LICENSED_FEED_EVALUATION,
    }
