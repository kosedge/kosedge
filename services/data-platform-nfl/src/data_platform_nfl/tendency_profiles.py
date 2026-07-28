"""Real, honest situational/tendency analytics from normalized nflverse PBP.

This is the "nflsavant-style, better-than-Warren-Sharp" analytics layer for
this session's stated vision, built entirely from real, free nflverse/
nflreadpy play-by-play (`nfl_dp_play_by_play`) -- NOT from proprietary
coverage-scheme charting data, which we do not have and do not fabricate.

Explicitly NOT covered here (confirmed absent from free nflverse/nflreadpy
PBP by direct inspection of the raw ingested payloads before this module was
written): Cover 2/Cover 3/man/zone coverage labels, pass-rusher counts,
`defenders_in_box`, offense/defense personnel groupings. See
docs/NFL_TENDENCY_ANALYTICS.md for the full scope/provenance note.

What IS real and computed here:

- Team offense/defense situational tendencies (down & distance, score
  state/game script, field position) -- pass/rush mix, shotgun/no-huddle
  rate, real `xpass`-relative pass-rate-over-expected (PROE), EPA,
  success rate, explosive-play rate, sack rate.
- Team pass-direction (left/middle/right) and run-direction/gap tendency,
  per team and league-wide.
- QB situational efficiency splits, including a real sack/qb_hit-based
  pressure-vs-clean-pocket split (the honest proxy for "pressure" without a
  real blitz/pass-rusher-count column) and CPOE (completion% over
  nflfastR's own `cp` model).

Design note on aggregation strategy: unlike most of ingest.py (which
aggregates via large SQL GROUP BY/CASE blocks), the bucket-assignment logic
here is expressed as small, pure, directly-unit-testable Python functions
(`down_distance_bucket`, `score_state_bucket`, `field_position_bucket`,
`pressure_bucket`, `down_type_bucket`) and the aggregation itself is a pure
Python fold over a flat list of play dicts (`compute_*` functions below).
This keeps the bucket boundaries defined in exactly one place (no risk of a
Python helper and a parallel SQL CASE statement silently drifting apart) and
makes the core logic testable with plain dicts/lists, matching the existing
convention in team_intel.py's `build_standings_rows`/`infer_depth_chart_rows`.
Per-season play volume (tens of thousands of rows) is small enough that a
Python-side fold is not a performance concern.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import text

from .db import SessionLocal

LEAGUE_TEAM_LABEL = "LEAGUE"

# ---------------------------------------------------------------------------
# Pure bucket-assignment functions (single source of truth for bucket
# boundaries -- see module docstring).
# ---------------------------------------------------------------------------


def down_distance_bucket(down: Any, ydstogo: Any) -> Optional[str]:
    """Bucket a play by (down, distance-to-go). Early downs (1st/2nd) and
    money downs (3rd/4th) get independent short/medium/long thresholds since
    what counts as "short" is different in each context (e.g. 3rd-and-3 is a
    real, meaningfully different situation from 1st-and-3)."""
    if down is None or ydstogo is None:
        return None
    try:
        down_i = int(down)
        ytg = float(ydstogo)
    except (TypeError, ValueError):
        return None
    if down_i in (1, 2):
        if ytg <= 3:
            return "early_down_short"
        if ytg <= 7:
            return "early_down_medium"
        return "early_down_long"
    if down_i in (3, 4):
        if ytg <= 2:
            return "money_down_short"
        if ytg <= 6:
            return "money_down_medium"
        return "money_down_long"
    return None


def down_type_bucket(down: Any) -> Optional[str]:
    """Coarser early-down vs. money-down split (used for QB splits)."""
    if down is None:
        return None
    try:
        down_i = int(down)
    except (TypeError, ValueError):
        return None
    if down_i in (1, 2):
        return "early_down"
    if down_i in (3, 4):
        return "money_down"
    return None


def score_state_bucket(score_differential: Any) -> Optional[str]:
    """Bucket by game-script/score state. `score_differential` must already
    be signed from the perspective of the team being profiled (positive =
    that team is leading) -- see materialize_team_situational_tendencies for
    the sign flip applied to defense-perspective rows. Buckets mirror the
    standard "one-possession game" threshold (abs(diff) <= 8, since a
    touchdown + 2pt conversion is 8) used throughout real football
    analytics."""
    if score_differential is None:
        return None
    try:
        sd = float(score_differential)
    except (TypeError, ValueError):
        return None
    if sd <= -9:
        return "trailing_big"
    if sd <= -1:
        return "trailing_small"
    if sd == 0:
        return "tied"
    if sd <= 8:
        return "leading_small"
    return "leading_big"


def field_position_bucket(yardline_100: Any) -> Optional[str]:
    """Bucket by field position. `yardline_100` is nflverse's standard
    distance-to-opponent-goal-line measure (0 = opponent's goal line, 100 =
    own goal line), already symmetric for offense/defense perspectives (it
    describes where the ball is, not which team is favored)."""
    if yardline_100 is None:
        return None
    try:
        y = float(yardline_100)
    except (TypeError, ValueError):
        return None
    if y <= 5:
        return "goal_to_go"
    if y <= 20:
        return "red_zone"
    if y <= 50:
        return "midfield"
    return "own_territory"


def pressure_bucket(sack: Any, qb_hit: Any) -> str:
    """Real sack/qb_hit-based pressure proxy -- the honest analog to a real
    blitz/pass-rusher-count column, which does not exist in free nflverse
    PBP. Always returns a bucket (never None) since every pass play is
    either pressured or not by this definition."""
    return "pressure" if (bool(sack) or bool(qb_hit)) else "clean_pocket"


SITUATION_DIMENSIONS: Dict[str, Callable[[Dict[str, Any]], Optional[str]]] = {
    "down_distance": lambda p: down_distance_bucket(p.get("down"), p.get("ydstogo")),
    "score_state": lambda p: score_state_bucket(p.get("score_differential")),
    "field_position": lambda p: field_position_bucket(p.get("yardline_100")),
}

QB_SITUATION_DIMENSIONS: Dict[str, Callable[[Dict[str, Any]], Optional[str]]] = {
    "overall": lambda p: "overall",
    "down_type": lambda p: down_type_bucket(p.get("down")),
    "pressure": lambda p: pressure_bucket(p.get("sack"), p.get("qb_hit")),
    "score_state": lambda p: score_state_bucket(p.get("score_differential")),
    "field_position": lambda p: field_position_bucket(p.get("yardline_100")),
}

_EXPLOSIVE_PASS_YARDS = 20
_EXPLOSIVE_RUSH_YARDS = 10


# ---------------------------------------------------------------------------
# Team situational tendencies (down/distance, score state, field position)
# ---------------------------------------------------------------------------


def _new_situational_acc() -> Dict[str, Any]:
    return {
        "plays": 0,
        "pass_plays": 0,
        "rush_plays": 0,
        "dropback_plays": 0,
        "xpass_sum": 0.0,
        "xpass_n": 0,
        "shotgun_plays": 0,
        "no_huddle_plays": 0,
        "epa_sum": 0.0,
        "epa_n": 0,
        "success_sum": 0,
        "success_n": 0,
        "explosive_plays": 0,
        "sack_plays": 0,
    }


def _accumulate_situational_play(acc: Dict[str, Any], play: Dict[str, Any]) -> None:
    acc["plays"] += 1
    play_type = play.get("play_type")
    if play_type == "pass":
        acc["pass_plays"] += 1
    elif play_type == "run":
        acc["rush_plays"] += 1
    if play.get("qb_dropback"):
        acc["dropback_plays"] += 1
    xpass = play.get("xpass")
    if xpass is not None:
        acc["xpass_sum"] += float(xpass)
        acc["xpass_n"] += 1
    if play.get("shotgun"):
        acc["shotgun_plays"] += 1
    if play.get("no_huddle"):
        acc["no_huddle_plays"] += 1
    epa = play.get("epa")
    if epa is not None:
        acc["epa_sum"] += float(epa)
        acc["epa_n"] += 1
    success = play.get("success")
    if success is not None:
        acc["success_sum"] += 1 if success else 0
        acc["success_n"] += 1
    yards_gained = play.get("yards_gained")
    if yards_gained is not None:
        try:
            yg = float(yards_gained)
        except (TypeError, ValueError):
            yg = None
        if yg is not None:
            if (play_type == "pass" and yg >= _EXPLOSIVE_PASS_YARDS) or (
                play_type == "run" and yg >= _EXPLOSIVE_RUSH_YARDS
            ):
                acc["explosive_plays"] += 1
    if play.get("sack"):
        acc["sack_plays"] += 1


def _finalize_situational_acc(
    team: str, situation_type: str, bucket: str, acc: Dict[str, Any]
) -> Dict[str, Any]:
    plays = acc["plays"]
    dropback_rate = (acc["dropback_plays"] / plays) if plays else None
    avg_xpass = (acc["xpass_sum"] / acc["xpass_n"]) if acc["xpass_n"] else None
    return {
        "team": team,
        "situation_type": situation_type,
        "situation_bucket": bucket,
        "plays": plays,
        "pass_plays": acc["pass_plays"],
        "rush_plays": acc["rush_plays"],
        "pass_rate": (acc["pass_plays"] / plays) if plays else None,
        "dropback_plays": acc["dropback_plays"],
        "dropback_rate": dropback_rate,
        "avg_xpass": avg_xpass,
        "pass_rate_over_expected": (
            (dropback_rate - avg_xpass) if (dropback_rate is not None and avg_xpass is not None) else None
        ),
        "shotgun_plays": acc["shotgun_plays"],
        "shotgun_rate": (acc["shotgun_plays"] / plays) if plays else None,
        "no_huddle_plays": acc["no_huddle_plays"],
        "no_huddle_rate": (acc["no_huddle_plays"] / plays) if plays else None,
        "epa_per_play": (acc["epa_sum"] / acc["epa_n"]) if acc["epa_n"] else None,
        "success_rate": (acc["success_sum"] / acc["success_n"]) if acc["success_n"] else None,
        "explosive_play_rate": (acc["explosive_plays"] / plays) if plays else None,
        "sack_rate": (acc["sack_plays"] / acc["dropback_plays"]) if acc["dropback_plays"] else None,
    }


def compute_team_situational_tendencies(
    plays: List[Dict[str, Any]], *, team_key: str = "team"
) -> List[Dict[str, Any]]:
    """Aggregate a flat list of scrimmage plays (already filtered upstream
    to `play_type IN ('pass', 'run')`) into per-team, per-situation-bucket
    tendency rows across every dimension in SITUATION_DIMENSIONS
    independently -- a single play contributes to one bucket per dimension
    (its down/distance bucket AND its score-state bucket AND its field
    position bucket), not to one bucket overall.

    `score_differential` on each play must already be signed from the
    profiled team's own perspective (positive = that team leading).
    """
    buckets: Dict[tuple, Dict[str, Any]] = {}
    for play in plays:
        team = play.get(team_key)
        if not team:
            continue
        for situation_type, bucket_fn in SITUATION_DIMENSIONS.items():
            bucket = bucket_fn(play)
            if bucket is None:
                continue
            key = (team, situation_type, bucket)
            acc = buckets.setdefault(key, _new_situational_acc())
            _accumulate_situational_play(acc, play)
    return [
        _finalize_situational_acc(team, situation_type, bucket, acc)
        for (team, situation_type, bucket), acc in buckets.items()
    ]


# ---------------------------------------------------------------------------
# Team direction tendencies (pass left/middle/right, run location + gap)
# ---------------------------------------------------------------------------


def _new_direction_acc() -> Dict[str, Any]:
    return {
        "pass_left": 0,
        "pass_middle": 0,
        "pass_right": 0,
        "pass_total": 0,
        "run_left": 0,
        "run_middle": 0,
        "run_right": 0,
        "run_loc_total": 0,
        "run_end": 0,
        "run_guard": 0,
        "run_tackle": 0,
        "run_gap_total": 0,
    }


def _accumulate_direction_play(acc: Dict[str, Any], play: Dict[str, Any]) -> None:
    play_type = play.get("play_type")
    if play_type == "pass":
        loc = play.get("pass_location")
        if loc in ("left", "middle", "right"):
            acc["pass_total"] += 1
            acc[f"pass_{loc}"] += 1
    elif play_type == "run":
        loc = play.get("run_location")
        if loc in ("left", "middle", "right"):
            acc["run_loc_total"] += 1
            acc[f"run_{loc}"] += 1
        gap = play.get("run_gap")
        if gap in ("end", "guard", "tackle"):
            acc["run_gap_total"] += 1
            acc[f"run_{gap}"] += 1


def _finalize_direction_acc(team: str, acc: Dict[str, Any]) -> Dict[str, Any]:
    pass_total = acc["pass_total"]
    run_loc_total = acc["run_loc_total"]
    run_gap_total = acc["run_gap_total"]
    return {
        "team": team,
        "pass_plays_with_location": pass_total,
        "pass_left_rate": (acc["pass_left"] / pass_total) if pass_total else None,
        "pass_middle_rate": (acc["pass_middle"] / pass_total) if pass_total else None,
        "pass_right_rate": (acc["pass_right"] / pass_total) if pass_total else None,
        "run_plays_with_location": run_loc_total,
        "run_left_rate": (acc["run_left"] / run_loc_total) if run_loc_total else None,
        "run_middle_rate": (acc["run_middle"] / run_loc_total) if run_loc_total else None,
        "run_right_rate": (acc["run_right"] / run_loc_total) if run_loc_total else None,
        "run_plays_with_gap": run_gap_total,
        "run_end_rate": (acc["run_end"] / run_gap_total) if run_gap_total else None,
        "run_guard_rate": (acc["run_guard"] / run_gap_total) if run_gap_total else None,
        "run_tackle_rate": (acc["run_tackle"] / run_gap_total) if run_gap_total else None,
    }


def compute_team_direction_tendencies(
    plays: List[Dict[str, Any]], *, team_key: str = "team", include_league: bool = True
) -> List[Dict[str, Any]]:
    """Aggregate pass-direction and run-direction/gap tendency by team. When
    `include_league` is True (default), also emits a `LEAGUE_TEAM_LABEL` row
    aggregated across every play regardless of team, for context (per the
    task's "per team and league-wide for context" ask)."""
    buckets: Dict[str, Dict[str, Any]] = {}
    for play in plays:
        team = play.get(team_key)
        if not team:
            continue
        acc = buckets.setdefault(team, _new_direction_acc())
        _accumulate_direction_play(acc, play)
        if include_league:
            league_acc = buckets.setdefault(LEAGUE_TEAM_LABEL, _new_direction_acc())
            _accumulate_direction_play(league_acc, play)
    return [_finalize_direction_acc(team, acc) for team, acc in buckets.items()]


# ---------------------------------------------------------------------------
# QB situational splits
# ---------------------------------------------------------------------------


def _new_qb_acc() -> Dict[str, Any]:
    return {
        "dropbacks": 0,
        "pass_attempts": 0,
        "completions": 0,
        "pass_yards": 0.0,
        "epa_sum": 0.0,
        "epa_n": 0,
        "success_sum": 0,
        "success_n": 0,
        "cp_sum": 0.0,
        "cp_n": 0,
        "sacks": 0,
        "interceptions": 0,
        "passing_tds": 0,
    }


def _accumulate_qb_play(acc: Dict[str, Any], play: Dict[str, Any]) -> None:
    acc["dropbacks"] += 1
    sacked = bool(play.get("sack"))
    if sacked:
        acc["sacks"] += 1
    else:
        acc["pass_attempts"] += 1
        if play.get("complete_pass"):
            acc["completions"] += 1
        pass_yards = play.get("passing_yards")
        if pass_yards is not None:
            acc["pass_yards"] += float(pass_yards)
        if play.get("interception"):
            acc["interceptions"] += 1
        if play.get("touchdown"):
            acc["passing_tds"] += 1
        cp = play.get("cp")
        if cp is not None:
            acc["cp_sum"] += float(cp)
            acc["cp_n"] += 1
    epa = play.get("epa")
    if epa is not None:
        acc["epa_sum"] += float(epa)
        acc["epa_n"] += 1
    success = play.get("success")
    if success is not None:
        acc["success_sum"] += 1 if success else 0
        acc["success_n"] += 1


def _finalize_qb_acc(
    player_id: str, meta: Dict[str, Any], situation_type: str, bucket: str, acc: Dict[str, Any]
) -> Dict[str, Any]:
    dropbacks = acc["dropbacks"]
    pass_attempts = acc["pass_attempts"]
    completion_rate = (acc["completions"] / pass_attempts) if pass_attempts else None
    avg_cp = (acc["cp_sum"] / acc["cp_n"]) if acc["cp_n"] else None
    cpoe = ((completion_rate - avg_cp) * 100.0) if (completion_rate is not None and avg_cp is not None) else None
    return {
        "player_id": player_id,
        "player_name": meta.get("player_name"),
        "team": meta.get("team"),
        "situation_type": situation_type,
        "situation_bucket": bucket,
        "dropbacks": dropbacks,
        "pass_attempts": pass_attempts,
        "completions": acc["completions"],
        "completion_rate": completion_rate,
        "pass_yards": acc["pass_yards"],
        "yards_per_attempt": (acc["pass_yards"] / pass_attempts) if pass_attempts else None,
        "epa_per_play": (acc["epa_sum"] / acc["epa_n"]) if acc["epa_n"] else None,
        "success_rate": (acc["success_sum"] / acc["success_n"]) if acc["success_n"] else None,
        "avg_cp": avg_cp,
        "cpoe": cpoe,
        "sacks": acc["sacks"],
        "sack_rate": (acc["sacks"] / dropbacks) if dropbacks else None,
        "interceptions": acc["interceptions"],
        "interception_rate": (acc["interceptions"] / pass_attempts) if pass_attempts else None,
        "passing_tds": acc["passing_tds"],
        "td_rate": (acc["passing_tds"] / pass_attempts) if pass_attempts else None,
    }


def compute_qb_situational_splits(plays: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate a flat list of QB dropbacks (pass attempts + sacks, i.e.
    `play_type == 'pass'` rows with a real `passer_player_id`) into
    per-player, per-situation-bucket efficiency splits across every
    dimension in QB_SITUATION_DIMENSIONS independently (mirrors
    compute_team_situational_tendencies -- one play contributes to its
    'overall' bucket AND its down_type bucket AND its pressure bucket,
    etc.)."""
    buckets: Dict[tuple, Dict[str, Any]] = {}
    meta: Dict[str, Dict[str, Any]] = {}
    for play in plays:
        player_id = play.get("passer_player_id")
        if not player_id:
            continue
        player_meta = meta.setdefault(player_id, {})
        if play.get("posteam"):
            player_meta["team"] = play.get("posteam")
        if play.get("passer_player_name"):
            player_meta["player_name"] = play.get("passer_player_name")
        for situation_type, bucket_fn in QB_SITUATION_DIMENSIONS.items():
            bucket = bucket_fn(play)
            if bucket is None:
                continue
            key = (player_id, situation_type, bucket)
            acc = buckets.setdefault(key, _new_qb_acc())
            _accumulate_qb_play(acc, play)
    return [
        _finalize_qb_acc(player_id, meta.get(player_id, {}), situation_type, bucket, acc)
        for (player_id, situation_type, bucket), acc in buckets.items()
    ]


# ---------------------------------------------------------------------------
# Materialization (DB read -> pure aggregation -> DB write)
# ---------------------------------------------------------------------------

_SITUATIONAL_SELECT_COLUMNS = """
  down, ydstogo, yardline_100, play_type, qb_dropback, xpass,
  shotgun, no_huddle, epa, success, yards_gained, sack
"""


def materialize_team_situational_tendencies(
    *, seasons: List[int], min_sample_plays: int = 8
) -> Dict[str, Any]:
    """Recompute nfl_dp_team_situational_tendencies for the given seasons
    from real nfl_dp_play_by_play rows. Fully replaces each season's rows
    (small, fully derived table -- safe to re-run any time normalized PBP
    changes). Buckets with fewer than `min_sample_plays` real plays are
    dropped rather than persisted as noisy small-sample rates.
    """
    session = SessionLocal()
    rows_written = 0
    rows_skipped_low_sample = 0
    try:
        for season in seasons:
            offense_rows = session.execute(
                text(
                    f"""
                    SELECT posteam AS team, score_differential, {_SITUATIONAL_SELECT_COLUMNS}
                    FROM nfl_dp_play_by_play
                    WHERE season = :season AND play_type IN ('pass', 'run') AND posteam IS NOT NULL
                    """
                ),
                {"season": season},
            ).mappings().all()
            defense_rows = session.execute(
                text(
                    f"""
                    SELECT defteam AS team, (-score_differential) AS score_differential, {_SITUATIONAL_SELECT_COLUMNS}
                    FROM nfl_dp_play_by_play
                    WHERE season = :season AND play_type IN ('pass', 'run') AND defteam IS NOT NULL
                    """
                ),
                {"season": season},
            ).mappings().all()

            session.execute(
                text("DELETE FROM nfl_dp_team_situational_tendencies WHERE season = :season"),
                {"season": season},
            )

            for perspective, rows in (("offense", offense_rows), ("defense", defense_rows)):
                agg = compute_team_situational_tendencies([dict(r) for r in rows])
                for row in agg:
                    if row["plays"] < min_sample_plays:
                        rows_skipped_low_sample += 1
                        continue
                    session.execute(
                        text(
                            """
                            INSERT INTO nfl_dp_team_situational_tendencies (
                              season, team, perspective, situation_type, situation_bucket,
                              plays, pass_plays, rush_plays, pass_rate,
                              dropback_plays, dropback_rate, avg_xpass, pass_rate_over_expected,
                              shotgun_plays, shotgun_rate, no_huddle_plays, no_huddle_rate,
                              epa_per_play, success_rate, explosive_play_rate, sack_rate,
                              source, computed_at
                            ) VALUES (
                              :season, :team, :perspective, :situation_type, :situation_bucket,
                              :plays, :pass_plays, :rush_plays, :pass_rate,
                              :dropback_plays, :dropback_rate, :avg_xpass, :pass_rate_over_expected,
                              :shotgun_plays, :shotgun_rate, :no_huddle_plays, :no_huddle_rate,
                              :epa_per_play, :success_rate, :explosive_play_rate, :sack_rate,
                              'nflverse', NOW()
                            )
                            ON CONFLICT (season, team, perspective, situation_type, situation_bucket) DO UPDATE SET
                              plays = EXCLUDED.plays,
                              pass_plays = EXCLUDED.pass_plays,
                              rush_plays = EXCLUDED.rush_plays,
                              pass_rate = EXCLUDED.pass_rate,
                              dropback_plays = EXCLUDED.dropback_plays,
                              dropback_rate = EXCLUDED.dropback_rate,
                              avg_xpass = EXCLUDED.avg_xpass,
                              pass_rate_over_expected = EXCLUDED.pass_rate_over_expected,
                              shotgun_plays = EXCLUDED.shotgun_plays,
                              shotgun_rate = EXCLUDED.shotgun_rate,
                              no_huddle_plays = EXCLUDED.no_huddle_plays,
                              no_huddle_rate = EXCLUDED.no_huddle_rate,
                              epa_per_play = EXCLUDED.epa_per_play,
                              success_rate = EXCLUDED.success_rate,
                              explosive_play_rate = EXCLUDED.explosive_play_rate,
                              sack_rate = EXCLUDED.sack_rate,
                              computed_at = EXCLUDED.computed_at
                            """
                        ),
                        {
                            "season": season,
                            "team": row["team"],
                            "perspective": perspective,
                            "situation_type": row["situation_type"],
                            "situation_bucket": row["situation_bucket"],
                            "plays": row["plays"],
                            "pass_plays": row["pass_plays"],
                            "rush_plays": row["rush_plays"],
                            "pass_rate": row["pass_rate"],
                            "dropback_plays": row["dropback_plays"],
                            "dropback_rate": row["dropback_rate"],
                            "avg_xpass": row["avg_xpass"],
                            "pass_rate_over_expected": row["pass_rate_over_expected"],
                            "shotgun_plays": row["shotgun_plays"],
                            "shotgun_rate": row["shotgun_rate"],
                            "no_huddle_plays": row["no_huddle_plays"],
                            "no_huddle_rate": row["no_huddle_rate"],
                            "epa_per_play": row["epa_per_play"],
                            "success_rate": row["success_rate"],
                            "explosive_play_rate": row["explosive_play_rate"],
                            "sack_rate": row["sack_rate"],
                        },
                    )
                    rows_written += 1
            session.commit()
        return {
            "status": "ok",
            "seasons": seasons,
            "rows_written": rows_written,
            "rows_skipped_low_sample": rows_skipped_low_sample,
            "min_sample_plays": min_sample_plays,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def materialize_team_direction_tendencies(*, seasons: List[int], min_sample_plays: int = 8) -> Dict[str, Any]:
    """Recompute nfl_dp_team_direction_tendencies (pass left/middle/right,
    run location + gap) for the given seasons, including a LEAGUE_TEAM_LABEL
    league-average row per (season, perspective)."""
    session = SessionLocal()
    rows_written = 0
    rows_skipped_low_sample = 0
    try:
        for season in seasons:
            offense_rows = session.execute(
                text(
                    """
                    SELECT posteam AS team, play_type, pass_location, run_location, run_gap
                    FROM nfl_dp_play_by_play
                    WHERE season = :season AND play_type IN ('pass', 'run') AND posteam IS NOT NULL
                    """
                ),
                {"season": season},
            ).mappings().all()
            defense_rows = session.execute(
                text(
                    """
                    SELECT defteam AS team, play_type, pass_location, run_location, run_gap
                    FROM nfl_dp_play_by_play
                    WHERE season = :season AND play_type IN ('pass', 'run') AND defteam IS NOT NULL
                    """
                ),
                {"season": season},
            ).mappings().all()

            session.execute(
                text("DELETE FROM nfl_dp_team_direction_tendencies WHERE season = :season"),
                {"season": season},
            )

            for perspective, rows in (("offense", offense_rows), ("defense", defense_rows)):
                agg = compute_team_direction_tendencies([dict(r) for r in rows])
                for row in agg:
                    sample = row["pass_plays_with_location"] + row["run_plays_with_location"]
                    if row["team"] != LEAGUE_TEAM_LABEL and sample < min_sample_plays:
                        rows_skipped_low_sample += 1
                        continue
                    session.execute(
                        text(
                            """
                            INSERT INTO nfl_dp_team_direction_tendencies (
                              season, team, perspective,
                              pass_plays_with_location, pass_left_rate, pass_middle_rate, pass_right_rate,
                              run_plays_with_location, run_left_rate, run_middle_rate, run_right_rate,
                              run_plays_with_gap, run_end_rate, run_guard_rate, run_tackle_rate,
                              source, computed_at
                            ) VALUES (
                              :season, :team, :perspective,
                              :pass_plays_with_location, :pass_left_rate, :pass_middle_rate, :pass_right_rate,
                              :run_plays_with_location, :run_left_rate, :run_middle_rate, :run_right_rate,
                              :run_plays_with_gap, :run_end_rate, :run_guard_rate, :run_tackle_rate,
                              'nflverse', NOW()
                            )
                            ON CONFLICT (season, team, perspective) DO UPDATE SET
                              pass_plays_with_location = EXCLUDED.pass_plays_with_location,
                              pass_left_rate = EXCLUDED.pass_left_rate,
                              pass_middle_rate = EXCLUDED.pass_middle_rate,
                              pass_right_rate = EXCLUDED.pass_right_rate,
                              run_plays_with_location = EXCLUDED.run_plays_with_location,
                              run_left_rate = EXCLUDED.run_left_rate,
                              run_middle_rate = EXCLUDED.run_middle_rate,
                              run_right_rate = EXCLUDED.run_right_rate,
                              run_plays_with_gap = EXCLUDED.run_plays_with_gap,
                              run_end_rate = EXCLUDED.run_end_rate,
                              run_guard_rate = EXCLUDED.run_guard_rate,
                              run_tackle_rate = EXCLUDED.run_tackle_rate,
                              computed_at = EXCLUDED.computed_at
                            """
                        ),
                        {
                            "season": season,
                            "team": row["team"],
                            "perspective": perspective,
                            "pass_plays_with_location": row["pass_plays_with_location"],
                            "pass_left_rate": row["pass_left_rate"],
                            "pass_middle_rate": row["pass_middle_rate"],
                            "pass_right_rate": row["pass_right_rate"],
                            "run_plays_with_location": row["run_plays_with_location"],
                            "run_left_rate": row["run_left_rate"],
                            "run_middle_rate": row["run_middle_rate"],
                            "run_right_rate": row["run_right_rate"],
                            "run_plays_with_gap": row["run_plays_with_gap"],
                            "run_end_rate": row["run_end_rate"],
                            "run_guard_rate": row["run_guard_rate"],
                            "run_tackle_rate": row["run_tackle_rate"],
                        },
                    )
                    rows_written += 1
            session.commit()
        return {
            "status": "ok",
            "seasons": seasons,
            "rows_written": rows_written,
            "rows_skipped_low_sample": rows_skipped_low_sample,
            "min_sample_plays": min_sample_plays,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def materialize_qb_situational_splits(*, seasons: List[int], min_sample_dropbacks: int = 5) -> Dict[str, Any]:
    """Recompute nfl_dp_qb_situational_splits for the given seasons from
    real nfl_dp_play_by_play pass plays. Buckets with fewer than
    `min_sample_dropbacks` real dropbacks are dropped."""
    session = SessionLocal()
    rows_written = 0
    rows_skipped_low_sample = 0
    try:
        for season in seasons:
            pass_rows = session.execute(
                text(
                    """
                    SELECT
                      passer_player_id, passer_player_name, posteam,
                      down, score_differential, yardline_100, sack, qb_hit,
                      complete_pass, passing_yards, epa, success, cp, interception, touchdown
                    FROM nfl_dp_play_by_play
                    WHERE season = :season AND play_type = 'pass' AND passer_player_id IS NOT NULL
                    """
                ),
                {"season": season},
            ).mappings().all()

            session.execute(
                text("DELETE FROM nfl_dp_qb_situational_splits WHERE season = :season"),
                {"season": season},
            )

            agg = compute_qb_situational_splits([dict(r) for r in pass_rows])
            for row in agg:
                if row["dropbacks"] < min_sample_dropbacks:
                    rows_skipped_low_sample += 1
                    continue
                session.execute(
                    text(
                        """
                        INSERT INTO nfl_dp_qb_situational_splits (
                          season, player_id, player_name, team, situation_type, situation_bucket,
                          dropbacks, pass_attempts, completions, completion_rate, pass_yards,
                          yards_per_attempt, epa_per_play, success_rate, avg_cp, cpoe,
                          sacks, sack_rate, interceptions, interception_rate, passing_tds, td_rate,
                          source, computed_at
                        ) VALUES (
                          :season, :player_id, :player_name, :team, :situation_type, :situation_bucket,
                          :dropbacks, :pass_attempts, :completions, :completion_rate, :pass_yards,
                          :yards_per_attempt, :epa_per_play, :success_rate, :avg_cp, :cpoe,
                          :sacks, :sack_rate, :interceptions, :interception_rate, :passing_tds, :td_rate,
                          'nflverse', NOW()
                        )
                        ON CONFLICT (season, player_id, situation_type, situation_bucket) DO UPDATE SET
                          player_name = EXCLUDED.player_name,
                          team = EXCLUDED.team,
                          dropbacks = EXCLUDED.dropbacks,
                          pass_attempts = EXCLUDED.pass_attempts,
                          completions = EXCLUDED.completions,
                          completion_rate = EXCLUDED.completion_rate,
                          pass_yards = EXCLUDED.pass_yards,
                          yards_per_attempt = EXCLUDED.yards_per_attempt,
                          epa_per_play = EXCLUDED.epa_per_play,
                          success_rate = EXCLUDED.success_rate,
                          avg_cp = EXCLUDED.avg_cp,
                          cpoe = EXCLUDED.cpoe,
                          sacks = EXCLUDED.sacks,
                          sack_rate = EXCLUDED.sack_rate,
                          interceptions = EXCLUDED.interceptions,
                          interception_rate = EXCLUDED.interception_rate,
                          passing_tds = EXCLUDED.passing_tds,
                          td_rate = EXCLUDED.td_rate,
                          computed_at = EXCLUDED.computed_at
                        """
                    ),
                    {
                        "season": season,
                        "player_id": row["player_id"],
                        "player_name": row["player_name"],
                        "team": row["team"],
                        "situation_type": row["situation_type"],
                        "situation_bucket": row["situation_bucket"],
                        "dropbacks": row["dropbacks"],
                        "pass_attempts": row["pass_attempts"],
                        "completions": row["completions"],
                        "completion_rate": row["completion_rate"],
                        "pass_yards": row["pass_yards"],
                        "yards_per_attempt": row["yards_per_attempt"],
                        "epa_per_play": row["epa_per_play"],
                        "success_rate": row["success_rate"],
                        "avg_cp": row["avg_cp"],
                        "cpoe": row["cpoe"],
                        "sacks": row["sacks"],
                        "sack_rate": row["sack_rate"],
                        "interceptions": row["interceptions"],
                        "interception_rate": row["interception_rate"],
                        "passing_tds": row["passing_tds"],
                        "td_rate": row["td_rate"],
                    },
                )
                rows_written += 1
            session.commit()
        return {
            "status": "ok",
            "seasons": seasons,
            "rows_written": rows_written,
            "rows_skipped_low_sample": rows_skipped_low_sample,
            "min_sample_dropbacks": min_sample_dropbacks,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def materialize_all_tendency_profiles(*, seasons: List[int]) -> Dict[str, Any]:
    """Convenience wrapper to rebuild all three tendency tables for the
    given seasons in one call (used by the CLI's --materialize-tendency-profiles
    flag)."""
    return {
        "team_situational": materialize_team_situational_tendencies(seasons=seasons),
        "team_direction": materialize_team_direction_tendencies(seasons=seasons),
        "qb_situational": materialize_qb_situational_splits(seasons=seasons),
    }
