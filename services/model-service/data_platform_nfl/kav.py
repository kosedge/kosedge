"""KAV — Kos Edge Adjusted Value (owned opponent-adjusted efficiency).

KAV is Kos Edge's DVOA-style team efficiency metric. It is NOT Football
Outsiders / FTN DVOA. Computation:

1. Aggregate EPA / success / explosive rates from owned nflverse PBP
   (`nfl_dp_play_by_play`) per team-game.
2. Iteratively opponent-adjust offense and defense within an as-of window
   (games with week <= W for season S).
3. Express as percentage vs league (scale = 0.15 EPA/play ≈ 100% KAV).
4. Persist game + weekly tables; weekly row for week W is as-of end of W.
5. Pre-game features for a game in week W join KAV from week W-1 (strict lag).

Defense KAV follows FO sign convention: negative is good (suppresses EPA).
Net KAV = offense KAV − defense KAV (higher = better team).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import text

KAV_VERSION = "kav-v1"
KAV_PCT_SCALE = 0.15  # EPA/play gap mapping to ~100% KAV
DEFAULT_ITERATIONS = 12
CONVERGENCE_EPS = 1e-6
EXPLOSIVE_YARDS = 12.0
MIN_PLAYS_GAME = 8


@dataclass(frozen=True)
class TeamGameRaw:
    season: int
    week: int
    game_id: str
    team: str
    opponent: str
    is_home: Optional[bool]
    off_plays: int
    def_plays: int
    raw_off_epa: float
    raw_def_epa_allowed: float
    raw_off_success: float
    raw_def_success_allowed: float
    raw_off_explosive: float
    raw_def_explosive_allowed: float


@dataclass
class TeamRating:
    off_epa: float
    def_epa: float  # EPA allowed; lower is better


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def epa_to_kav_pct(adj_epa: float, league_mean: float, *, scale: float = KAV_PCT_SCALE) -> float:
    """Convert opponent-adjusted EPA/play into KAV percentage points.

    +15% means ~0.0225 EPA/play above league mean at default scale.
    """
    denom = max(1e-6, float(scale))
    return (float(adj_epa) - float(league_mean)) / denom


def iterative_opponent_adjust(
    games: Sequence[TeamGameRaw],
    *,
    iterations: int = DEFAULT_ITERATIONS,
    dampen: float = 1.0,
) -> Tuple[Dict[str, TeamRating], Dict[Tuple[str, str, str], TeamRating], int]:
    """Iterative SOS adjustment over a closed set of team-games.

    Returns:
      team_ratings: final season-to-date ratings by team
      game_adjusted: (game_id, team) -> adjusted off/def EPA for that game
      iters_used: iterations actually performed
    """
    if not games:
        return {}, {}, 0

    teams = sorted({g.team for g in games})
    # Initialize with play-weighted team means
    off_sum: Dict[str, float] = {t: 0.0 for t in teams}
    off_n: Dict[str, float] = {t: 0.0 for t in teams}
    def_sum: Dict[str, float] = {t: 0.0 for t in teams}
    def_n: Dict[str, float] = {t: 0.0 for t in teams}
    for g in games:
        if g.off_plays > 0:
            off_sum[g.team] += g.raw_off_epa * g.off_plays
            off_n[g.team] += g.off_plays
        if g.def_plays > 0:
            def_sum[g.team] += g.raw_def_epa_allowed * g.def_plays
            def_n[g.team] += g.def_plays

    ratings: Dict[str, TeamRating] = {}
    for t in teams:
        ratings[t] = TeamRating(
            off_epa=(off_sum[t] / off_n[t]) if off_n[t] else 0.0,
            def_epa=(def_sum[t] / def_n[t]) if def_n[t] else 0.0,
        )

    games_by_team: Dict[str, List[TeamGameRaw]] = {t: [] for t in teams}
    for g in games:
        games_by_team[g.team].append(g)

    iters_used = 0
    for _ in range(max(1, int(iterations))):
        iters_used += 1
        league_off = sum(r.off_epa for r in ratings.values()) / len(ratings)
        league_def = sum(r.def_epa for r in ratings.values()) / len(ratings)
        new_ratings: Dict[str, TeamRating] = {}
        max_delta = 0.0
        for t in teams:
            tg = games_by_team[t]
            if not tg:
                new_ratings[t] = ratings[t]
                continue
            adj_off_num = 0.0
            adj_off_den = 0.0
            adj_def_num = 0.0
            adj_def_den = 0.0
            for g in tg:
                opp = ratings.get(g.opponent)
                if opp is None:
                    continue
                # Soft schedule (high opp.def_epa) inflates raw offense → subtract.
                # Tough schedule (low opp.def_epa) deflates raw offense → add back.
                off_adj = g.raw_off_epa + dampen * (league_def - opp.def_epa)
                def_adj = g.raw_def_epa_allowed + dampen * (league_off - opp.off_epa)
                if g.off_plays > 0:
                    adj_off_num += off_adj * g.off_plays
                    adj_off_den += g.off_plays
                if g.def_plays > 0:
                    adj_def_num += def_adj * g.def_plays
                    adj_def_den += g.def_plays
            new_off = (adj_off_num / adj_off_den) if adj_off_den else ratings[t].off_epa
            new_def = (adj_def_num / adj_def_den) if adj_def_den else ratings[t].def_epa
            max_delta = max(
                max_delta,
                abs(new_off - ratings[t].off_epa),
                abs(new_def - ratings[t].def_epa),
            )
            new_ratings[t] = TeamRating(off_epa=new_off, def_epa=new_def)
        ratings = new_ratings
        if max_delta < CONVERGENCE_EPS:
            break

    league_off = sum(r.off_epa for r in ratings.values()) / len(ratings)
    league_def = sum(r.def_epa for r in ratings.values()) / len(ratings)
    game_adjusted: Dict[Tuple[str, str, str], TeamRating] = {}
    for g in games:
        opp = ratings.get(g.opponent)
        if opp is None:
            continue
        off_adj = g.raw_off_epa + dampen * (league_def - opp.def_epa)
        def_adj = g.raw_def_epa_allowed + dampen * (league_off - opp.off_epa)
        game_adjusted[(g.game_id, g.team, g.opponent)] = TeamRating(off_epa=off_adj, def_epa=def_adj)

    return ratings, game_adjusted, iters_used


def build_weekly_lagged_features(
    weekly_as_of: Dict[Tuple[int, int, str], Dict[str, float]],
    *,
    season: int,
    week: int,
    team: str,
) -> Dict[str, Optional[float]]:
    """Strict-lag feature bundle for a game in `week`.

    Uses as-of ratings from week-1 only. Returns None fields when unavailable
    (week 1, missing history). Never reads same-week or future weeks.
    """
    as_of_week = int(week) - 1
    if as_of_week < 1:
        return {
            "kav_as_of_week": None,
            "kav_offense_ytd": None,
            "kav_defense_ytd": None,
            "kav_net_ytd": None,
            "kav_offense_5g": None,
            "kav_defense_5g": None,
            "kav_net_5g": None,
        }
    row = weekly_as_of.get((int(season), as_of_week, str(team)))
    if not row:
        return {
            "kav_as_of_week": as_of_week,
            "kav_offense_ytd": None,
            "kav_defense_ytd": None,
            "kav_net_ytd": None,
            "kav_offense_5g": None,
            "kav_defense_5g": None,
            "kav_net_5g": None,
        }
    return {
        "kav_as_of_week": as_of_week,
        "kav_offense_ytd": row.get("kav_offense_ytd"),
        "kav_defense_ytd": row.get("kav_defense_ytd"),
        "kav_net_ytd": row.get("kav_net_ytd"),
        "kav_offense_5g": row.get("kav_offense_5g"),
        "kav_defense_5g": row.get("kav_defense_5g"),
        "kav_net_5g": row.get("kav_net_5g"),
    }


def assert_no_future_leakage(
    feature_as_of_week: Optional[int],
    game_week: int,
) -> None:
    """Raise if a feature as-of week is not strictly before the game week."""
    if feature_as_of_week is None:
        return
    if int(feature_as_of_week) >= int(game_week):
        raise ValueError(
            f"KAV leakage: feature as_of_week={feature_as_of_week} >= game_week={game_week}"
        )


def _fetch_team_game_raw(session: Any, *, seasons: Sequence[int]) -> List[TeamGameRaw]:
    rows = session.execute(
        text(
            """
            WITH plays AS (
              SELECT
                season,
                week,
                game_id,
                posteam AS team,
                defteam AS opponent,
                CASE
                  WHEN posteam = home_team THEN TRUE
                  WHEN posteam = away_team THEN FALSE
                  ELSE NULL
                END AS is_home,
                epa,
                success,
                COALESCE(yards_gained, 0) AS yards_gained,
                'off' AS side
              FROM nfl_dp_play_by_play
              WHERE season = ANY(:seasons)
                AND play_type IN ('pass', 'run')
                AND posteam IS NOT NULL
                AND defteam IS NOT NULL
                AND epa IS NOT NULL
                AND week IS NOT NULL
                AND week BETWEEN 1 AND 22
              UNION ALL
              SELECT
                season,
                week,
                game_id,
                defteam AS team,
                posteam AS opponent,
                CASE
                  WHEN defteam = home_team THEN TRUE
                  WHEN defteam = away_team THEN FALSE
                  ELSE NULL
                END AS is_home,
                epa,
                success,
                COALESCE(yards_gained, 0) AS yards_gained,
                'def' AS side
              FROM nfl_dp_play_by_play
              WHERE season = ANY(:seasons)
                AND play_type IN ('pass', 'run')
                AND posteam IS NOT NULL
                AND defteam IS NOT NULL
                AND epa IS NOT NULL
                AND week IS NOT NULL
                AND week BETWEEN 1 AND 22
            ),
            agg AS (
              SELECT
                season, week, game_id, team, opponent,
                bool_or(is_home) FILTER (WHERE side = 'off') AS is_home,
                COUNT(*) FILTER (WHERE side = 'off') AS off_plays,
                COUNT(*) FILTER (WHERE side = 'def') AS def_plays,
                AVG(epa) FILTER (WHERE side = 'off') AS raw_off_epa,
                AVG(epa) FILTER (WHERE side = 'def') AS raw_def_epa,
                AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) FILTER (WHERE side = 'off') AS raw_off_success,
                AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) FILTER (WHERE side = 'def') AS raw_def_success,
                AVG(CASE WHEN yards_gained >= :explosive THEN 1.0 ELSE 0.0 END)
                  FILTER (WHERE side = 'off') AS raw_off_explosive,
                AVG(CASE WHEN yards_gained >= :explosive THEN 1.0 ELSE 0.0 END)
                  FILTER (WHERE side = 'def') AS raw_def_explosive
              FROM plays
              GROUP BY season, week, game_id, team, opponent
            )
            SELECT *
            FROM agg
            WHERE off_plays >= :min_plays OR def_plays >= :min_plays
            ORDER BY season, week, game_id, team
            """
        ),
        {
            "seasons": list(seasons),
            "explosive": EXPLOSIVE_YARDS,
            "min_plays": MIN_PLAYS_GAME,
        },
    ).fetchall()

    out: List[TeamGameRaw] = []
    for row in rows:
        m = dict(row._mapping)
        off_plays = int(m["off_plays"] or 0)
        def_plays = int(m["def_plays"] or 0)
        if off_plays < MIN_PLAYS_GAME and def_plays < MIN_PLAYS_GAME:
            continue
        out.append(
            TeamGameRaw(
                season=int(m["season"]),
                week=int(m["week"]),
                game_id=str(m["game_id"]),
                team=str(m["team"]),
                opponent=str(m["opponent"]),
                is_home=m.get("is_home"),
                off_plays=off_plays,
                def_plays=def_plays,
                raw_off_epa=float(m["raw_off_epa"] or 0.0),
                raw_def_epa_allowed=float(m["raw_def_epa"] or 0.0),
                raw_off_success=float(m["raw_off_success"] or 0.0),
                raw_def_success_allowed=float(m["raw_def_success"] or 0.0),
                raw_off_explosive=float(m["raw_off_explosive"] or 0.0),
                raw_def_explosive_allowed=float(m["raw_def_explosive"] or 0.0),
            )
        )
    return out


def _rolling_mean(values: Sequence[float], window: int = 5) -> Optional[float]:
    if not values:
        return None
    slice_vals = list(values)[-window:]
    if not slice_vals:
        return None
    return sum(slice_vals) / len(slice_vals)


def materialize_kav(
    *,
    seasons: Sequence[int],
    replace_existing: bool = False,
    iterations: int = DEFAULT_ITERATIONS,
) -> Dict[str, Any]:
    """Materialize game + weekly KAV tables for the given seasons."""
    from .db import SessionLocal

    session = SessionLocal()
    started = _now()
    try:
        season_list = [int(s) for s in seasons]
        if replace_existing:
            session.execute(
                text("DELETE FROM nfl_dp_team_kav_game WHERE season = ANY(:seasons)"),
                {"seasons": season_list},
            )
            session.execute(
                text("DELETE FROM nfl_dp_team_kav_weekly WHERE season = ANY(:seasons)"),
                {"seasons": season_list},
            )
            session.commit()

        raw_games = _fetch_team_game_raw(session, seasons=season_list)
        by_season: Dict[int, List[TeamGameRaw]] = {}
        for g in raw_games:
            by_season.setdefault(g.season, []).append(g)

        game_rows_written = 0
        weekly_rows_written = 0

        for season, season_games in sorted(by_season.items()):
            max_week = max(g.week for g in season_games)
            # Cache game-level kav pct chronologically for 5g rolling
            game_kav_series: Dict[str, List[Tuple[int, float, float, float]]] = {}

            for as_of_week in range(1, max_week + 1):
                window = [g for g in season_games if g.week <= as_of_week]
                if not window:
                    continue
                team_ratings, game_adj, iters_used = iterative_opponent_adjust(
                    window, iterations=iterations
                )
                if not team_ratings:
                    continue
                league_off = sum(r.off_epa for r in team_ratings.values()) / len(team_ratings)
                league_def = sum(r.def_epa for r in team_ratings.values()) / len(team_ratings)

                # Persist game rows only for games in this exact week (final season pass
                # would duplicate; write once when as_of_week == game.week using final
                # as-of that includes the game — still OK for descriptive game KAV).
                week_games = [g for g in window if g.week == as_of_week]
                for g in week_games:
                    key = (g.game_id, g.team, g.opponent)
                    adj = game_adj.get(key)
                    if adj is None:
                        continue
                    kav_off = epa_to_kav_pct(adj.off_epa, league_off)
                    kav_def = epa_to_kav_pct(adj.def_epa, league_def)
                    kav_net = kav_off - kav_def
                    session.execute(
                        text(
                            """
                            INSERT INTO nfl_dp_team_kav_game (
                              season, week, game_id, team, opponent, is_home,
                              off_plays, def_plays,
                              raw_off_epa_per_play, raw_def_epa_allowed_per_play,
                              raw_off_success_rate, raw_def_success_allowed_rate,
                              raw_off_explosive_rate, raw_def_explosive_allowed_rate,
                              kav_off_epa_per_play, kav_def_epa_allowed_per_play,
                              kav_offense, kav_defense, kav_net,
                              iterations, source, updated_at
                            ) VALUES (
                              :season, :week, :game_id, :team, :opponent, :is_home,
                              :off_plays, :def_plays,
                              :raw_off_epa, :raw_def_epa,
                              :raw_off_success, :raw_def_success,
                              :raw_off_explosive, :raw_def_explosive,
                              :kav_off_epa, :kav_def_epa,
                              :kav_offense, :kav_defense, :kav_net,
                              :iterations, :source, :updated_at
                            )
                            ON CONFLICT (season, week, game_id, team) DO UPDATE SET
                              opponent = EXCLUDED.opponent,
                              is_home = EXCLUDED.is_home,
                              off_plays = EXCLUDED.off_plays,
                              def_plays = EXCLUDED.def_plays,
                              raw_off_epa_per_play = EXCLUDED.raw_off_epa_per_play,
                              raw_def_epa_allowed_per_play = EXCLUDED.raw_def_epa_allowed_per_play,
                              raw_off_success_rate = EXCLUDED.raw_off_success_rate,
                              raw_def_success_allowed_rate = EXCLUDED.raw_def_success_allowed_rate,
                              raw_off_explosive_rate = EXCLUDED.raw_off_explosive_rate,
                              raw_def_explosive_allowed_rate = EXCLUDED.raw_def_explosive_allowed_rate,
                              kav_off_epa_per_play = EXCLUDED.kav_off_epa_per_play,
                              kav_def_epa_allowed_per_play = EXCLUDED.kav_def_epa_allowed_per_play,
                              kav_offense = EXCLUDED.kav_offense,
                              kav_defense = EXCLUDED.kav_defense,
                              kav_net = EXCLUDED.kav_net,
                              iterations = EXCLUDED.iterations,
                              source = EXCLUDED.source,
                              updated_at = EXCLUDED.updated_at
                            """
                        ),
                        {
                            "season": season,
                            "week": g.week,
                            "game_id": g.game_id,
                            "team": g.team,
                            "opponent": g.opponent,
                            "is_home": g.is_home,
                            "off_plays": g.off_plays,
                            "def_plays": g.def_plays,
                            "raw_off_epa": round(g.raw_off_epa, 6),
                            "raw_def_epa": round(g.raw_def_epa_allowed, 6),
                            "raw_off_success": round(g.raw_off_success, 6),
                            "raw_def_success": round(g.raw_def_success_allowed, 6),
                            "raw_off_explosive": round(g.raw_off_explosive, 6),
                            "raw_def_explosive": round(g.raw_def_explosive_allowed, 6),
                            "kav_off_epa": round(adj.off_epa, 6),
                            "kav_def_epa": round(adj.def_epa, 6),
                            "kav_offense": round(kav_off, 6),
                            "kav_defense": round(kav_def, 6),
                            "kav_net": round(kav_net, 6),
                            "iterations": iters_used,
                            "source": "nflverse_pbp",
                            "updated_at": _now(),
                        },
                    )
                    game_rows_written += 1
                    game_kav_series.setdefault(g.team, []).append(
                        (g.week, kav_off, kav_def, kav_net)
                    )

                for team, rating in team_ratings.items():
                    kav_off_ytd = epa_to_kav_pct(rating.off_epa, league_off)
                    kav_def_ytd = epa_to_kav_pct(rating.def_epa, league_def)
                    kav_net_ytd = kav_off_ytd - kav_def_ytd
                    series = game_kav_series.get(team, [])
                    # Only games through as_of_week
                    series_thru = [(w, o, d, n) for w, o, d, n in series if w <= as_of_week]
                    off_5g = _rolling_mean([o for _, o, _, _ in series_thru], 5)
                    def_5g = _rolling_mean([d for _, _, d, _ in series_thru], 5)
                    net_5g = _rolling_mean([n for _, _, _, n in series_thru], 5)
                    team_games = [g for g in window if g.team == team]
                    off_plays = sum(g.off_plays for g in team_games)
                    def_plays = sum(g.def_plays for g in team_games)
                    raw_off = (
                        sum(g.raw_off_epa * g.off_plays for g in team_games) / off_plays
                        if off_plays
                        else None
                    )
                    raw_def = (
                        sum(g.raw_def_epa_allowed * g.def_plays for g in team_games) / def_plays
                        if def_plays
                        else None
                    )
                    session.execute(
                        text(
                            """
                            INSERT INTO nfl_dp_team_kav_weekly (
                              season, week, team, games_played, off_plays, def_plays,
                              raw_off_epa_per_play, raw_def_epa_allowed_per_play,
                              kav_off_epa_per_play, kav_def_epa_allowed_per_play,
                              kav_offense, kav_defense, kav_net,
                              kav_offense_ytd, kav_defense_ytd, kav_net_ytd,
                              kav_offense_5g, kav_defense_5g, kav_net_5g,
                              iterations, as_of_week, source, updated_at
                            ) VALUES (
                              :season, :week, :team, :games_played, :off_plays, :def_plays,
                              :raw_off, :raw_def,
                              :kav_off_epa, :kav_def_epa,
                              :kav_offense, :kav_defense, :kav_net,
                              :kav_offense_ytd, :kav_defense_ytd, :kav_net_ytd,
                              :kav_offense_5g, :kav_defense_5g, :kav_net_5g,
                              :iterations, :as_of_week, :source, :updated_at
                            )
                            ON CONFLICT (season, week, team) DO UPDATE SET
                              games_played = EXCLUDED.games_played,
                              off_plays = EXCLUDED.off_plays,
                              def_plays = EXCLUDED.def_plays,
                              raw_off_epa_per_play = EXCLUDED.raw_off_epa_per_play,
                              raw_def_epa_allowed_per_play = EXCLUDED.raw_def_epa_allowed_per_play,
                              kav_off_epa_per_play = EXCLUDED.kav_off_epa_per_play,
                              kav_def_epa_allowed_per_play = EXCLUDED.kav_def_epa_allowed_per_play,
                              kav_offense = EXCLUDED.kav_offense,
                              kav_defense = EXCLUDED.kav_defense,
                              kav_net = EXCLUDED.kav_net,
                              kav_offense_ytd = EXCLUDED.kav_offense_ytd,
                              kav_defense_ytd = EXCLUDED.kav_defense_ytd,
                              kav_net_ytd = EXCLUDED.kav_net_ytd,
                              kav_offense_5g = EXCLUDED.kav_offense_5g,
                              kav_defense_5g = EXCLUDED.kav_defense_5g,
                              kav_net_5g = EXCLUDED.kav_net_5g,
                              iterations = EXCLUDED.iterations,
                              as_of_week = EXCLUDED.as_of_week,
                              source = EXCLUDED.source,
                              updated_at = EXCLUDED.updated_at
                            """
                        ),
                        {
                            "season": season,
                            "week": as_of_week,
                            "team": team,
                            "games_played": len(team_games),
                            "off_plays": off_plays,
                            "def_plays": def_plays,
                            "raw_off": round(raw_off, 6) if raw_off is not None else None,
                            "raw_def": round(raw_def, 6) if raw_def is not None else None,
                            "kav_off_epa": round(rating.off_epa, 6),
                            "kav_def_epa": round(rating.def_epa, 6),
                            "kav_offense": round(kav_off_ytd, 6),
                            "kav_defense": round(kav_def_ytd, 6),
                            "kav_net": round(kav_net_ytd, 6),
                            "kav_offense_ytd": round(kav_off_ytd, 6),
                            "kav_defense_ytd": round(kav_def_ytd, 6),
                            "kav_net_ytd": round(kav_net_ytd, 6),
                            "kav_offense_5g": round(off_5g, 6) if off_5g is not None else None,
                            "kav_defense_5g": round(def_5g, 6) if def_5g is not None else None,
                            "kav_net_5g": round(net_5g, 6) if net_5g is not None else None,
                            "iterations": iters_used,
                            "as_of_week": as_of_week,
                            "source": "nflverse_pbp",
                            "updated_at": _now(),
                        },
                    )
                    weekly_rows_written += 1
                session.commit()

        # Attach lagged KAV onto matchup feature packs when present.
        matchup_updated = _attach_kav_to_matchup_features(session, seasons=season_list)
        session.commit()
        return {
            "ok": True,
            "kav_version": KAV_VERSION,
            "seasons": season_list,
            "raw_team_games": len(raw_games),
            "game_rows_written": game_rows_written,
            "weekly_rows_written": weekly_rows_written,
            "matchup_rows_updated": matchup_updated,
            "iterations": int(iterations),
            "elapsed_seconds": round((_now() - started).total_seconds(), 2),
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _attach_kav_to_matchup_features(session: Any, *, seasons: Sequence[int]) -> int:
    """Fill KAV columns on matchup packs using week-1 lag (no leakage)."""
    cols = session.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'nfl_dp_matchup_features_weekly'
              AND column_name = 'home_kav_net_5g'
            """
        )
    ).fetchone()
    if cols is None:
        return 0
    result = session.execute(
        text(
            """
            UPDATE nfl_dp_matchup_features_weekly m
            SET
              home_kav_offense_5g = hk.kav_offense_5g,
              away_kav_offense_5g = ak.kav_offense_5g,
              home_kav_defense_5g = hk.kav_defense_5g,
              away_kav_defense_5g = ak.kav_defense_5g,
              home_kav_net_5g = hk.kav_net_5g,
              away_kav_net_5g = ak.kav_net_5g,
              home_kav_offense_ytd = hk.kav_offense_ytd,
              away_kav_offense_ytd = ak.kav_offense_ytd,
              home_kav_defense_ytd = hk.kav_defense_ytd,
              away_kav_defense_ytd = ak.kav_defense_ytd,
              home_kav_net_ytd = hk.kav_net_ytd,
              away_kav_net_ytd = ak.kav_net_ytd,
              diff_kav_offense_5g = CASE
                WHEN hk.kav_offense_5g IS NULL OR ak.kav_offense_5g IS NULL THEN NULL
                ELSE hk.kav_offense_5g - ak.kav_offense_5g
              END,
              diff_kav_defense_5g = CASE
                WHEN hk.kav_defense_5g IS NULL OR ak.kav_defense_5g IS NULL THEN NULL
                ELSE hk.kav_defense_5g - ak.kav_defense_5g
              END,
              diff_kav_net_5g = CASE
                WHEN hk.kav_net_5g IS NULL OR ak.kav_net_5g IS NULL THEN NULL
                ELSE hk.kav_net_5g - ak.kav_net_5g
              END,
              kav_as_of_week = (m.week - 1),
              updated_at = NOW()
            FROM nfl_dp_team_kav_weekly hk, nfl_dp_team_kav_weekly ak
            WHERE m.season = ANY(:seasons)
              AND hk.season = m.season
              AND ak.season = m.season
              AND hk.team = m.home_team
              AND ak.team = m.away_team
              AND hk.week = (m.week - 1)
              AND ak.week = (m.week - 1)
              AND m.week >= 2
            """
        ),
        {"seasons": list(seasons)},
    )
    return int(result.rowcount or 0)


def kav_signal_to_points(
    *,
    home_kav_net_5g: Optional[float],
    away_kav_net_5g: Optional[float],
    home_kav_offense_5g: Optional[float] = None,
    away_kav_offense_5g: Optional[float] = None,
    home_kav_defense_5g: Optional[float] = None,
    away_kav_defense_5g: Optional[float] = None,
    margin_weight: float = 3.2,
    total_weight: float = 2.4,
    max_margin: float = 3.5,
    max_total: float = 2.8,
) -> Dict[str, Any]:
    """Map lagged KAV differentials into bounded margin/total point contributions."""
    if home_kav_net_5g is None or away_kav_net_5g is None:
        return {
            "available": False,
            "margin_points": 0.0,
            "total_points": 0.0,
            "diff_net": None,
            "sum_offense": None,
        }
    diff_net = float(home_kav_net_5g) - float(away_kav_net_5g)
    # KAV is in fraction-of-scale units (~±1.0 typical). Convert to points.
    margin_points = _clamp(diff_net * margin_weight, -max_margin, max_margin)
    sum_offense = None
    if home_kav_offense_5g is not None and away_kav_offense_5g is not None:
        # High offense KAV + soft defense KAV (positive def KAV = leaky) → higher total
        home_def = float(home_kav_defense_5g or 0.0)
        away_def = float(away_kav_defense_5g or 0.0)
        sum_offense = (
            float(home_kav_offense_5g)
            + float(away_kav_offense_5g)
            + home_def
            + away_def
        )
        total_points = _clamp(sum_offense * total_weight * 0.5, -max_total, max_total)
    else:
        total_points = _clamp(abs(diff_net) * 0.15, -max_total, max_total)
    return {
        "available": True,
        "margin_points": round(margin_points, 4),
        "total_points": round(total_points, 4),
        "diff_net": round(diff_net, 6),
        "sum_offense": round(sum_offense, 6) if sum_offense is not None else None,
    }
