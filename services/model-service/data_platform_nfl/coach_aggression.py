"""Thin coach aggression rates from play-calling (nflverse PBP).

Simple state-dependent rates only: 4th-down go residual + tempo (no-huddle /
plays). Not a multi-factor latent overfit machine.

Leakage: weekly row for week W is as-of end of W. Pre-game joins use W-1.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import text

from .kav import assert_no_future_leakage

COACH_AGGRESSION_VERSION = "coach-agg-v1-thin"
MIN_PLAYS = 40
# League-ish baseline go-rate used as a simple residual anchor (not a fit model).
LEAGUE_FOURTH_GO_BASELINE = 0.28


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _rolling_mean(values: Sequence[float], window: int = 5) -> Optional[float]:
    if not values:
        return None
    slice_vals = list(values)[-window:]
    return sum(slice_vals) / len(slice_vals) if slice_vals else None


def expected_fourth_down_go_rate(
    *,
    ydstogo: float,
    yardline_100: float,
    score_differential: float,
    game_seconds_remaining: Optional[float],
) -> float:
    """Thin situational baseline go-rate. Higher when short + late + trailing."""
    dist_term = _clamp(1.0 - (ydstogo / 10.0), 0.05, 0.95)
    field_term = _clamp(1.0 - (yardline_100 / 100.0), 0.1, 0.9)
    trail = 1.0 if score_differential < 0 else (0.55 if score_differential == 0 else 0.35)
    late = 0.55
    if game_seconds_remaining is not None:
        late = _clamp(1.0 - (float(game_seconds_remaining) / 3600.0), 0.25, 0.95)
    return _clamp(0.35 * dist_term + 0.25 * field_term + 0.25 * trail + 0.15 * late, 0.05, 0.92)


def compute_aggression_latent(
    *,
    fourth_go_residual: float,
    early_down_proe: float = 0.0,
    no_huddle_rate: float,
    trailing_pass_rate: float = 0.0,
    leading_pass_rate: float = 0.0,
) -> float:
    """Bounded thin aggression from 4th-down residual + tempo only (~[-2, 2]).

    early_down_proe / pass-state args are accepted for API compatibility but
    intentionally unused (prevents overfit tilt into the live factor).
    """
    del early_down_proe, trailing_pass_rate, leading_pass_rate
    raw = 1.35 * fourth_go_residual + 0.75 * (no_huddle_rate - 0.08)
    return _clamp(raw, -2.0, 2.0)


def compute_pace_latent(*, no_huddle_rate: float, plays_per_game_proxy: float) -> float:
    """Mild tempo score from no-huddle + play volume proxy."""
    raw = 1.4 * (no_huddle_rate - 0.08) + 0.02 * (plays_per_game_proxy - 62.0)
    return _clamp(raw, -2.0, 2.0)


def materialize_coach_aggression(
    *,
    seasons: Sequence[int],
    replace_existing: bool = False,
) -> Dict[str, Any]:
    from .db import SessionLocal

    session = SessionLocal()
    started = _now()
    try:
        season_list = [int(s) for s in seasons]
        if replace_existing:
            session.execute(
                text("DELETE FROM nfl_coach_aggression_weekly WHERE season = ANY(:seasons)"),
                {"seasons": season_list},
            )
            session.commit()

        rows = session.execute(
            text(
                """
                SELECT
                  season, week, posteam AS team, game_id,
                  play_type, down, ydstogo, yardline_100,
                  score_differential, game_seconds_remaining,
                  no_huddle, xpass,
                  CASE WHEN play_type = 'pass' THEN 1.0 ELSE 0.0 END AS is_pass
                FROM nfl_dp_play_by_play
                WHERE season = ANY(:seasons)
                  AND play_type IN ('pass', 'run', 'punt', 'field_goal')
                  AND posteam IS NOT NULL
                  AND week IS NOT NULL
                  AND week BETWEEN 1 AND 22
                  AND down IS NOT NULL
                """
            ),
            {"seasons": season_list},
        ).fetchall()

        # Per game-team then roll to week cumulative
        game_stats: Dict[Tuple[int, int, str, str], Dict[str, float]] = defaultdict(
            lambda: {
                "plays": 0.0,
                "fourth_att": 0.0,
                "fourth_go": 0.0,
                "fourth_exp": 0.0,
                "early_n": 0.0,
                "early_pass": 0.0,
                "early_xpass": 0.0,
                "no_huddle": 0.0,
                "trail_n": 0.0,
                "trail_pass": 0.0,
                "lead_n": 0.0,
                "lead_pass": 0.0,
            }
        )

        for row in rows:
            m = dict(row._mapping)
            season = int(m["season"])
            week = int(m["week"])
            team = str(m["team"])
            game_id = str(m["game_id"])
            key = (season, week, team, game_id)
            g = game_stats[key]
            play_type = str(m.get("play_type") or "")
            down = int(m["down"])
            ydstogo = float(m["ydstogo"] or 10.0)
            yardline = float(m["yardline_100"] or 50.0)
            sd = float(m["score_differential"] or 0.0)
            gsr = m.get("game_seconds_remaining")
            gsr_f = float(gsr) if gsr is not None else None
            is_pass = float(m["is_pass"] or 0.0)
            is_scrimmage = play_type in {"pass", "run"}

            # Tendency / pace stats only on scrimmage plays.
            if is_scrimmage:
                g["plays"] += 1.0
                g["no_huddle"] += 1.0 if m.get("no_huddle") else 0.0
                if down in (1, 2):
                    g["early_n"] += 1.0
                    g["early_pass"] += is_pass
                    xpass = m.get("xpass")
                    g["early_xpass"] += float(xpass) if xpass is not None else 0.45
                if sd < 0:
                    g["trail_n"] += 1.0
                    g["trail_pass"] += is_pass
                elif sd > 0:
                    g["lead_n"] += 1.0
                    g["lead_pass"] += is_pass

            if down == 4:
                g["fourth_att"] += 1.0
                if is_scrimmage:
                    g["fourth_go"] += 1.0
                g["fourth_exp"] += expected_fourth_down_go_rate(
                    ydstogo=ydstogo,
                    yardline_100=yardline,
                    score_differential=sd,
                    game_seconds_remaining=gsr_f,
                )

        # Collapse to season/week/team game aggregates, then cumulative as-of
        week_games: Dict[Tuple[int, int, str], List[Dict[str, float]]] = defaultdict(list)
        for (season, week, team, _gid), g in game_stats.items():
            week_games[(season, week, team)].append(g)

        by_team: Dict[Tuple[int, str], List[int]] = defaultdict(list)
        for season, week, team in week_games:
            by_team[(season, team)].append(week)
        for k in by_team:
            by_team[k] = sorted(set(by_team[k]))

        written = 0
        for (season, team), weeks in by_team.items():
            cum = {
                "plays": 0.0,
                "fourth_att": 0.0,
                "fourth_go": 0.0,
                "fourth_exp": 0.0,
                "early_n": 0.0,
                "early_pass": 0.0,
                "early_xpass": 0.0,
                "no_huddle": 0.0,
                "trail_n": 0.0,
                "trail_pass": 0.0,
                "lead_n": 0.0,
                "lead_pass": 0.0,
                "games": 0.0,
            }
            agg_hist: List[float] = []
            pace_hist: List[float] = []
            for week in weeks:
                for g in week_games.get((season, week, team), []):
                    for key in (
                        "plays",
                        "fourth_att",
                        "fourth_go",
                        "fourth_exp",
                        "early_n",
                        "early_pass",
                        "early_xpass",
                        "no_huddle",
                        "trail_n",
                        "trail_pass",
                        "lead_n",
                        "lead_pass",
                    ):
                        cum[key] += g[key]
                    cum["games"] += 1.0

                if cum["plays"] < MIN_PLAYS:
                    continue

                fourth_go_rate = (
                    cum["fourth_go"] / cum["fourth_att"] if cum["fourth_att"] > 0 else None
                )
                fourth_exp_rate = (
                    cum["fourth_exp"] / cum["fourth_att"] if cum["fourth_att"] > 0 else 0.45
                )
                fourth_residual = (
                    (fourth_go_rate - fourth_exp_rate) if fourth_go_rate is not None else 0.0
                )
                early_pass_rate = cum["early_pass"] / cum["early_n"] if cum["early_n"] else 0.45
                early_xpass = cum["early_xpass"] / cum["early_n"] if cum["early_n"] else 0.45
                early_proe = early_pass_rate - early_xpass
                no_huddle_rate = cum["no_huddle"] / cum["plays"]
                trail_pass = cum["trail_pass"] / cum["trail_n"] if cum["trail_n"] else early_pass_rate
                lead_pass = cum["lead_pass"] / cum["lead_n"] if cum["lead_n"] else early_pass_rate
                plays_per_game = cum["plays"] / max(1.0, cum["games"])

                aggression = compute_aggression_latent(
                    fourth_go_residual=fourth_residual,
                    early_down_proe=early_proe,
                    no_huddle_rate=no_huddle_rate,
                    trailing_pass_rate=trail_pass,
                    leading_pass_rate=lead_pass,
                )
                pace = compute_pace_latent(
                    no_huddle_rate=no_huddle_rate,
                    plays_per_game_proxy=plays_per_game,
                )
                agg_hist.append(aggression)
                pace_hist.append(pace)

                session.execute(
                    text(
                        """
                        INSERT INTO nfl_coach_aggression_weekly (
                          season, week, team, plays,
                          fourth_down_attempts, fourth_down_go_rate, fourth_down_go_residual,
                          early_down_proe, no_huddle_rate, trailing_pass_rate, leading_pass_rate,
                          aggression_latent, aggression_latent_5g,
                          pace_latent, pace_latent_5g,
                          as_of_week, source, updated_at
                        ) VALUES (
                          :season, :week, :team, :plays,
                          :fourth_att, :fourth_go_rate, :fourth_res,
                          :early_proe, :no_huddle, :trail_pass, :lead_pass,
                          :agg, :agg_5g, :pace, :pace_5g,
                          :as_of_week, :source, :updated_at
                        )
                        ON CONFLICT (season, week, team) DO UPDATE SET
                          plays = EXCLUDED.plays,
                          fourth_down_attempts = EXCLUDED.fourth_down_attempts,
                          fourth_down_go_rate = EXCLUDED.fourth_down_go_rate,
                          fourth_down_go_residual = EXCLUDED.fourth_down_go_residual,
                          early_down_proe = EXCLUDED.early_down_proe,
                          no_huddle_rate = EXCLUDED.no_huddle_rate,
                          trailing_pass_rate = EXCLUDED.trailing_pass_rate,
                          leading_pass_rate = EXCLUDED.leading_pass_rate,
                          aggression_latent = EXCLUDED.aggression_latent,
                          aggression_latent_5g = EXCLUDED.aggression_latent_5g,
                          pace_latent = EXCLUDED.pace_latent,
                          pace_latent_5g = EXCLUDED.pace_latent_5g,
                          as_of_week = EXCLUDED.as_of_week,
                          source = EXCLUDED.source,
                          updated_at = EXCLUDED.updated_at
                        """
                    ),
                    {
                        "season": season,
                        "week": week,
                        "team": team,
                        "plays": int(cum["plays"]),
                        "fourth_att": int(cum["fourth_att"]),
                        "fourth_go_rate": round(fourth_go_rate, 6) if fourth_go_rate is not None else None,
                        "fourth_res": round(fourth_residual, 6),
                        "early_proe": round(early_proe, 6),
                        "no_huddle": round(no_huddle_rate, 6),
                        "trail_pass": round(trail_pass, 6),
                        "lead_pass": round(lead_pass, 6),
                        "agg": round(aggression, 6),
                        "agg_5g": round(_rolling_mean(agg_hist, 5) or aggression, 6),
                        "pace": round(pace, 6),
                        "pace_5g": round(_rolling_mean(pace_hist, 5) or pace, 6),
                        "as_of_week": week,
                        "source": "nflverse_pbp",
                        "updated_at": _now(),
                    },
                )
                written += 1
            session.commit()

        attach = attach_coach_to_matchup_features(session, seasons=season_list)
        return {
            "ok": True,
            "version": COACH_AGGRESSION_VERSION,
            "seasons": season_list,
            "rows": written,
            "matchup_attach": attach,
            "elapsed_sec": round((_now() - started).total_seconds(), 3),
            "notes": "Strict lag: join as_of_week = game.week - 1",
        }
    except Exception as exc:
        try:
            session.rollback()
        except Exception:
            pass
        return {"ok": False, "error": f"{type(exc).__name__}:{exc}"}
    finally:
        session.close()


def fetch_lagged_coach_for_matchup(
    session: Any,
    *,
    season: int,
    week: int,
    home_team: str,
    away_team: str,
) -> Dict[str, Any]:
    as_of = int(week) - 1
    assert_no_future_leakage(as_of if as_of >= 1 else None, int(week))
    if as_of < 1:
        return {"available": False, "as_of_week": None}

    def _one(team: str) -> Dict[str, Any]:
        row = session.execute(
            text(
                """
                SELECT aggression_latent_5g, pace_latent_5g, as_of_week
                FROM nfl_coach_aggression_weekly
                WHERE season = :season AND team = :team AND week = :week
                """
            ),
            {"season": season, "team": team, "week": as_of},
        ).fetchone()
        return dict(row._mapping) if row else {}

    home = _one(home_team)
    away = _one(away_team)
    h_agg = home.get("aggression_latent_5g")
    a_agg = away.get("aggression_latent_5g")
    return {
        "available": h_agg is not None and a_agg is not None,
        "as_of_week": as_of,
        "home_coach_aggression_5g": float(h_agg) if h_agg is not None else None,
        "away_coach_aggression_5g": float(a_agg) if a_agg is not None else None,
        "home_coach_pace_5g": float(home["pace_latent_5g"]) if home.get("pace_latent_5g") is not None else None,
        "away_coach_pace_5g": float(away["pace_latent_5g"]) if away.get("pace_latent_5g") is not None else None,
    }


def attach_coach_to_matchup_features(
    session: Any,
    *,
    seasons: Sequence[int],
) -> Dict[str, Any]:
    updated = 0
    packs = session.execute(
        text(
            """
            SELECT season, week, game_id, home_team, away_team
            FROM nfl_dp_matchup_features_weekly
            WHERE season = ANY(:seasons)
            """
        ),
        {"seasons": list(seasons)},
    ).fetchall()
    for row in packs:
        m = dict(row._mapping)
        season, week = int(m["season"]), int(m["week"])
        feat = fetch_lagged_coach_for_matchup(
            session,
            season=season,
            week=week,
            home_team=str(m["home_team"]),
            away_team=str(m["away_team"]),
        )
        h = feat.get("home_coach_aggression_5g")
        a = feat.get("away_coach_aggression_5g")
        diff = (h - a) if h is not None and a is not None else None
        session.execute(
            text(
                """
                UPDATE nfl_dp_matchup_features_weekly SET
                  home_coach_aggression_5g = :h,
                  away_coach_aggression_5g = :a,
                  diff_coach_aggression_5g = :diff,
                  home_coach_pace_5g = :hp,
                  away_coach_pace_5g = :ap,
                  second_order_as_of_week = COALESCE(:as_of, second_order_as_of_week),
                  updated_at = NOW()
                WHERE season = :season AND week = :week AND game_id = :game_id
                """
            ),
            {
                "h": h,
                "a": a,
                "diff": diff,
                "hp": feat.get("home_coach_pace_5g"),
                "ap": feat.get("away_coach_pace_5g"),
                "as_of": feat.get("as_of_week"),
                "season": season,
                "week": week,
                "game_id": m["game_id"],
            },
        )
        updated += 1
    session.commit()
    return {"ok": True, "updated": updated}
