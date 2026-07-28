"""Preseason / offseason "roster continuity" nowcast.

Extends the in-season injury nowcast multiplier mechanism (see
`nfl_injury_nowcast.py`'s `_aggregate_team_nowcast`) to known offseason
roster moves -- key player departures via free agency/trade/retirement,
notable signings, and long-term injuries known before the season starts
-- that the preseason team-strength prior (season-average EPA blended
with market futures odds; see scripts/nfl/fix_2026_preseason_priors.py)
does not capture on its own.

Why this exists rather than a new adjustment system: the live simulator
already consumes an `offense_multiplier`/`defense_multiplier` pair per
team, sourced from `fetch_nfl_injury_nowcast`, and applies it inside
`NflGameInputs` (see `tasks.py::run_nfl_market_simulations` and
`routes/nfl.py`). Reusing that exact mechanism means:
  - one coherent pipeline (no second adjustment path to keep in sync),
  - roster-continuity effects compose naturally with real weekly injury
    data once the season starts (both are just multipliers that get
    multiplied together in `fetch_nfl_injury_nowcast`),
  - the same downstream consumers (win-probability sim, totals overlay,
    handicapping framework diagnostics) automatically pick this up with
    zero changes.

Entries live in `nfl_roster_continuity_adjustments`
(infra/db/028_nfl_roster_continuity_adjustments.sql) and are added via
`scripts/nfl/add_roster_adjustment.py`. Real automated transaction feeds
were investigated (nflverse rosters, ESPN's scoreboard API used in
`nfl_data.py`) and found insufficient for turnkey automation: nflverse's
`nfl_dp_rosters` table *does* eventually reflect a departure (e.g. a
player disappearing from a team's roster and appearing on another team's
roster the following season), but there's no "significance"/valuation
signal in our current sources to automatically tell a departed backup
from a departed star. So for now this is a small, explicit,
human-curated table rather than a fully automated feed -- see
`add_roster_adjustment.py` for the CLI to add entries.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


# Mirrors `_position_weights` in nfl_injury_nowcast.py so a position
# group carries the same offense/defense "share of team value" whether
# the signal comes from a live weekly injury report or a manually
# recorded offseason roster move.
_POSITION_GROUP_WEIGHTS: Dict[str, Dict[str, float]] = {
    "QB": {"offense": 1.0, "defense": 0.0},
    "WR": {"offense": 0.64, "defense": 0.0},
    "RB": {"offense": 0.64, "defense": 0.0},
    "TE": {"offense": 0.64, "defense": 0.0},
    "OL": {"offense": 0.54, "defense": 0.0},
    "DL": {"offense": 0.0, "defense": 0.62},
    "EDGE": {"offense": 0.0, "defense": 0.62},
    "DT": {"offense": 0.0, "defense": 0.62},
    "DE": {"offense": 0.0, "defense": 0.62},
    "LB": {"offense": 0.0, "defense": 0.52},
    "DB": {"offense": 0.0, "defense": 0.52},
    "CB": {"offense": 0.0, "defense": 0.52},
    "S": {"offense": 0.0, "defense": 0.52},
    "K": {"offense": 0.12, "defense": 0.0},
    "P": {"offense": 0.12, "defense": 0.0},
    "OFFENSE": {"offense": 0.5, "defense": 0.0},
    "DEFENSE": {"offense": 0.0, "defense": 0.5},
}
_DEFAULT_POSITION_GROUP_WEIGHTS = {"offense": 0.28, "defense": 0.24}

# Base confidence by source: a manual entry is a human judgment call
# (not verified against a second data source), so it starts below a
# fully-automated, cross-checked signal. Both sit below 1.0 because
# unlike a live injury report (which is itself uncertain but *current*),
# these are static assumptions that should visibly move the model
# without ever fully overriding the stats+market blend.
_SOURCE_BASE_CONFIDENCE = {
    "manual": 0.80,
    "nflverse": 0.90,
    "espn": 0.85,
}
_DEFAULT_SOURCE_CONFIDENCE = 0.70


def _position_group_weights(position_group: Optional[str]) -> Dict[str, float]:
    key = str(position_group or "").strip().upper()
    return _POSITION_GROUP_WEIGHTS.get(key, _DEFAULT_POSITION_GROUP_WEIGHTS)


def _source_confidence(source: Optional[str]) -> float:
    key = str(source or "").strip().lower()
    return _SOURCE_BASE_CONFIDENCE.get(key, _DEFAULT_SOURCE_CONFIDENCE)


def aggregate_roster_continuity_nowcast(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Turn a team's `nfl_roster_continuity_adjustments` rows into the same
    offense_multiplier/defense_multiplier/impact_score/confidence shape
    that `_aggregate_team_nowcast` produces for live injury data.

    Sign convention on `impact_score` (-1..1, per row): negative means the
    move made the team worse (departure/injury), positive means it made
    the team better (signing/return from injury). That sign flows through
    directly into the multiplier direction: a negative defensive-position
    impact score pushes defense_multiplier *above* 1.0 (weaker defense,
    matching the "higher defense_index = weaker defense" convention used
    throughout the simulator), and a negative offensive-position impact
    score pushes offense_multiplier *below* 1.0 (weaker offense).
    """
    if not rows:
        return {
            "adjustment_count": 0,
            "confidence": 0.0,
            "offense_multiplier": 1.0,
            "defense_multiplier": 1.0,
            "impact_score": 0.0,
            "top_drivers": [],
        }

    # A single fully-weighted position-group entry (e.g. one elite EDGE
    # departure, impact_score=-1.0, defense weight 0.62) should be able to
    # meaningfully move the multiplier on its own -- these are typically
    # a handful of curated entries per team, not a full weekly injury
    # report, so normalizing against "one maximal entry" (1.0) rather than
    # the in-season report's multi-player ceiling keeps a single
    # significant entry from being diluted away.
    max_raw_offense = max(0.01, _safe_float(os.getenv("NFL_ROSTER_CONTINUITY_MAX_RAW_OFFENSE"), 1.0))
    max_raw_defense = max(0.01, _safe_float(os.getenv("NFL_ROSTER_CONTINUITY_MAX_RAW_DEFENSE"), 1.0))
    # Reuses the in-season injury nowcast's own consumption-time clamp
    # bounds (see nfl_simulator.py) as this module's clamp bounds too, so
    # a roster-continuity-only nowcast can never produce a multiplier the
    # rest of the pipeline wouldn't already tolerate from real injury data.
    impact_scale = _clamp(_safe_float(os.getenv("NFL_ROSTER_CONTINUITY_IMPACT_SCALE"), 0.15), 0.01, 0.5)

    offense_raw = 0.0
    defense_raw = 0.0
    confidences: List[float] = []
    drivers: List[Dict[str, Any]] = []
    for row in rows:
        impact_score = _clamp(_safe_float(row.get("impact_score")), -1.0, 1.0)
        weights = _position_group_weights(row.get("position_group"))
        offense_raw += impact_score * weights["offense"]
        defense_raw += impact_score * weights["defense"]
        confidences.append(_source_confidence(row.get("source")))
        drivers.append(
            {
                "kind": "roster_continuity",
                "player_name": row.get("player_name"),
                "position_group": row.get("position_group"),
                "reason": row.get("reason"),
                "source": row.get("source"),
                "impact_score": round(impact_score, 4),
                "notes": row.get("notes"),
            }
        )

    confidence = _clamp(float(sum(confidences) / len(confidences)) if confidences else 0.0, 0.0, 1.0)
    offense_penalty = _clamp(offense_raw / max_raw_offense, -1.0, 1.0) * impact_scale
    defense_penalty = _clamp(defense_raw / max_raw_defense, -1.0, 1.0) * impact_scale

    offense_multiplier = _clamp(1.0 + (offense_penalty * confidence), 0.82, 1.08)
    # Positive defense_raw (net signings/returns on defense) should make
    # the defense *stronger* -> lower defense_multiplier, so this is a
    # subtraction, mirroring the sign flip documented above.
    defense_multiplier = _clamp(1.0 - (defense_penalty * confidence), 0.90, 1.18)
    impact_score_agg = _clamp((abs(offense_penalty) + abs(defense_penalty)) * 0.5, 0.0, 1.0)

    drivers = sorted(drivers, key=lambda item: abs(float(item["impact_score"])), reverse=True)[:5]
    return {
        "adjustment_count": len(rows),
        "confidence": round(confidence, 4),
        "offense_multiplier": round(offense_multiplier, 4),
        "defense_multiplier": round(defense_multiplier, 4),
        "impact_score": round(impact_score_agg, 4),
        "top_drivers": drivers,
    }


def fetch_roster_continuity_adjustments(
    session: Any,
    *,
    season_year: Optional[int],
    team: str,
) -> List[Dict[str, Any]]:
    if not team:
        return []
    season = int(season_year) if season_year is not None else datetime.now(timezone.utc).year
    rows = session.execute(
        text(
            """
            SELECT season, team, player_name, position_group, impact_score,
                   reason, source, notes, created_at
            FROM nfl_roster_continuity_adjustments
            -- Games in early January get their `season_year` naively derived
            -- from calendar year at ingestion time, so a game that's really
            -- part of the (e.g.) 2026 season but kicks off in January 2027
            -- gets labeled season_year=2027 (see the same accepted quirk in
            -- scripts/nfl/simulate_2026_season.py's own read query). Accept
            -- the prior calendar-year season too so a roster-continuity
            -- entry keyed by the "real" season still applies to that game.
            WHERE (season = :season OR season = :season - 1) AND team = :team AND active
            ORDER BY created_at
            """
        ),
        {"season": season, "team": team},
    ).fetchall()
    return [dict(row._mapping) for row in rows]


def fetch_roster_continuity_nowcast(
    session: Any,
    *,
    season_year: Optional[int],
    team: str,
) -> Dict[str, Any]:
    rows = fetch_roster_continuity_adjustments(session, season_year=season_year, team=team)
    return aggregate_roster_continuity_nowcast(rows)
