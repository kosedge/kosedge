"""Permanent, repeatable preseason hydration for a future NFL season.

Replaces the one-off ad-hoc SQL (`carryforward_2025`) that was previously
used to seed nfl_dp_team_situational_weekly / nfl_dp_player_usage_weekly for
a season with no real games played yet. That approach copied a *single*
snapshot (team: last week played; player: last week played) across all 18
weeks -- the noisiest, most recency-biased number available, and for
players it only covered the ~20% of the roster who happened to record
usage in the final week of the prior season, leaving rookies and bench
players completely absent from every downstream projection.

This module is idempotent and safe to call every offseason for any future
season:
  - Team priors = full prior-season average per team (every situational
    column), optionally blended with an external market signal.
  - Player priors, per rostered player on the target season:
      - Returning player with prior-season usage -> full prior-season
        per-game average, remapped to their CURRENT roster team (handles
        free agency/trades correctly).
      - Rookie or any rostered player with no prior-season usage -> the
        real historical draft-tier baseline from
        nfl_dp_rookie_usage_baselines (see rookie_baselines.py).

Both writers are guarded so they only ever touch rows tagged with one of
this module's own synthetic source values -- never real
'pbp_aggregation'/'nflverse'/'nfl_com' rows. Once real games are played for
a week, the normal materialize_usage_features_from_pbp() pipeline
overwrites that week with real data automatically (see the `source <>`
guards in ingest.py), so this hydration only ever matters for the
cold-start window before/just after kickoff.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import text

from .db import SessionLocal
from .rookie_baselines import compute_rookie_usage_baselines, get_rookie_baseline

TEAM_HYDRATE_SOURCE = "preseason_hydrate_v1"
PLAYER_HYDRATE_SOURCE = "preseason_hydrate_v1"
ROOKIE_BASELINE_SOURCE = "rookie_baseline_v1"
SYNTHETIC_TEAM_SOURCES = ("carryforward_2025", TEAM_HYDRATE_SOURCE)
SYNTHETIC_PLAYER_SOURCES = ("carryforward_2025", "preseason_hydrate_v1", "rookie_baseline_v1")
WEEKS = list(range(1, 19))

_TEAM_NUMERIC_COLUMNS = [
    "games_played", "offensive_plays", "defensive_plays", "pass_plays", "run_plays",
    "early_down_plays", "early_down_pass_plays", "third_down_attempts", "third_down_conversions",
    "fourth_down_attempts", "fourth_down_conversions", "red_zone_plays", "red_zone_touchdowns",
    "sacks_allowed", "qb_hits_allowed", "sacks_generated", "qb_hits_generated",
    "explosive_pass_plays", "explosive_pass_allowed", "pass_rate", "early_down_pass_rate",
    "third_down_conversion_rate", "fourth_down_conversion_rate", "red_zone_td_rate",
    "pressure_rate_allowed", "pressure_rate_generated", "success_rate_offense",
    "success_rate_defense_allowed", "epa_per_play_offense", "epa_per_play_defense_allowed",
]


def hydrate_preseason_team_situational(
    *,
    season: int,
    prior_season: Optional[int] = None,
    market_percentile_by_team: Optional[Dict[str, float]] = None,
    market_blend_weight: float = 0.5,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Seed/replace future-season team situational rows with full prior-season averages.

    market_percentile_by_team, if given, is {team_abbr: 0..1 rank by an
    external signal such as Super Bowl futures} -- 1.0 = market's best team.
    Applied only to the two EPA columns (the ones that most directly drive
    simulate_nfl_game), the same treatment validated in the original
    fix_2026_preseason_priors.py.
    """
    session = SessionLocal()
    try:
        prior = prior_season if prior_season is not None else season - 1
        avg_cols = ", ".join(f"AVG({c})::numeric AS {c}" for c in _TEAM_NUMERIC_COLUMNS)
        rows = session.execute(
            text(f"SELECT team, {avg_cols} FROM nfl_dp_team_situational_weekly WHERE season = :prior GROUP BY team"),
            {"prior": prior},
        ).mappings().all()
        season_avg = {r["team"]: dict(r) for r in rows}
        if not season_avg:
            return {"status": "skipped", "reason": f"no situational data for prior_season={prior}"}

        off_vals = [float(v["epa_per_play_offense"]) for v in season_avg.values() if v["epa_per_play_offense"] is not None]
        def_vals = [float(v["epa_per_play_defense_allowed"]) for v in season_avg.values() if v["epa_per_play_defense_allowed"] is not None]
        off_lo, off_hi = (min(off_vals), max(off_vals)) if off_vals else (0.0, 0.0)
        def_lo, def_hi = (min(def_vals), max(def_vals)) if def_vals else (0.0, 0.0)

        # Real bug found via a live production spot-check: a backup-caliber
        # QB (Jacoby Brissett, ARI) was projected to lead the entire league
        # in passing yards. Root cause traced to `pass_rate`/`offensive_plays`
        # (pace) being carried forward at FULL single-season strength with
        # no regression to the mean -- unlike EPA just above, which already
        # gets shrunk toward a market signal. ARI genuinely had the
        # league's single highest 2025 pass rate (65.9%, vs. a ~55% league
        # average), which is real, but extrapolating a single season's most
        # extreme rate stat at full strength into a new season overstates
        # how much of that was a stable team characteristic vs. one year's
        # game-script/personnel circumstances that won't necessarily repeat.
        # Shrinking rate stats toward the league mean for a small (n=1
        # season) sample is standard, well-established practice (this is
        # literally what "regression to the mean" means) -- 35% shrinkage
        # is a deliberately moderate choice: enough to pull true outliers
        # back toward plausible, without erasing real, persistent
        # team/scheme identity for teams with more moderate deviations.
        RATE_SHRINKAGE_WEIGHT = 0.35
        pass_rate_vals = [float(v["pass_rate"]) for v in season_avg.values() if v.get("pass_rate") is not None]
        plays_vals = [float(v["offensive_plays"]) for v in season_avg.values() if v.get("offensive_plays") is not None]
        league_avg_pass_rate = sum(pass_rate_vals) / len(pass_rate_vals) if pass_rate_vals else None
        league_avg_plays = sum(plays_vals) / len(plays_vals) if plays_vals else None

        teams_updated = []
        for team, stats in season_avg.items():
            values = dict(stats)
            pct = (market_percentile_by_team or {}).get(team)
            if pct is not None and stats["epa_per_play_offense"] is not None and stats["epa_per_play_defense_allowed"] is not None:
                market_off_equiv = off_lo + pct * (off_hi - off_lo)
                market_def_equiv = def_hi - pct * (def_hi - def_lo)
                values["epa_per_play_offense"] = (1 - market_blend_weight) * float(stats["epa_per_play_offense"]) + market_blend_weight * market_off_equiv
                values["epa_per_play_defense_allowed"] = (1 - market_blend_weight) * float(stats["epa_per_play_defense_allowed"]) + market_blend_weight * market_def_equiv

            if league_avg_pass_rate is not None and stats.get("pass_rate") is not None:
                values["pass_rate"] = (1 - RATE_SHRINKAGE_WEIGHT) * float(stats["pass_rate"]) + RATE_SHRINKAGE_WEIGHT * league_avg_pass_rate
            if league_avg_plays is not None and stats.get("offensive_plays") is not None:
                values["offensive_plays"] = (1 - RATE_SHRINKAGE_WEIGHT) * float(stats["offensive_plays"]) + RATE_SHRINKAGE_WEIGHT * league_avg_plays

            if dry_run:
                teams_updated.append(team)
                continue

            set_clause = ", ".join(f"{c} = :{c}" for c in _TEAM_NUMERIC_COLUMNS)
            params = {c: values.get(c) for c in _TEAM_NUMERIC_COLUMNS}
            params.update({"season": season, "team": team, "source": TEAM_HYDRATE_SOURCE, "weeks": WEEKS})
            session.execute(
                text(
                    f"""
                    UPDATE nfl_dp_team_situational_weekly
                    SET {set_clause}, source = :source, updated_at = NOW()
                    WHERE season = :season AND team = :team AND week = ANY(:weeks)
                      AND source = ANY(:guard_sources)
                    """
                ),
                {**params, "guard_sources": list(SYNTHETIC_TEAM_SOURCES)},
            )
            # Any week not yet present (schedule extended, new week added) gets inserted fresh.
            for week in WEEKS:
                session.execute(
                    text(
                        f"""
                        INSERT INTO nfl_dp_team_situational_weekly (season, week, team, {', '.join(_TEAM_NUMERIC_COLUMNS)}, source, updated_at)
                        SELECT :season, :week, :team, {', '.join(':' + c for c in _TEAM_NUMERIC_COLUMNS)}, :source, NOW()
                        WHERE NOT EXISTS (
                          SELECT 1 FROM nfl_dp_team_situational_weekly WHERE season = :season AND week = :week AND team = :team
                        )
                        """
                    ),
                    {**params, "week": week},
                )
            teams_updated.append(team)

        if not dry_run:
            session.commit()
        return {
            "status": "ok" if not dry_run else "dry_run",
            "season": season,
            "prior_season": prior,
            "teams_updated": len(teams_updated),
            "market_applied": bool(market_percentile_by_team),
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


_PLAYER_COUNT_COLUMNS = [
    "involvement_plays", "targets", "receptions", "receiving_yards", "air_yards",
    "yards_after_catch", "rush_attempts", "rush_yards", "pass_attempts", "pass_yards",
    "pass_touchdowns", "red_zone_targets", "red_zone_carries", "goal_to_go_carries",
    "qb_dropbacks", "qb_pressures_taken", "touchdowns_scored", "first_downs_generated",
    "explosive_plays",
]


def hydrate_preseason_player_usage(
    *, season: int, prior_season: Optional[int] = None, dry_run: bool = False
) -> Dict[str, Any]:
    """Seed future-season player usage rows for every rostered player.

    Returning players get their real full-prior-season per-game average.
    Rookies and anyone else with no prior-season usage get the historical
    draft-tier baseline. Nobody on the roster is left silently absent.
    """
    session = SessionLocal()
    try:
        prior = prior_season if prior_season is not None else season - 1

        roster_rows = session.execute(
            text(
                """
                SELECT player_id, team, position, draft_number, rookie_year, player_name
                FROM nfl_dp_rosters WHERE season = :season
                """
            ),
            {"season": season},
        ).mappings().all()
        if not roster_rows:
            return {"status": "skipped", "reason": f"no roster rows for season={season}"}

        # Clean up stale synthetic rows before re-seeding: a player who
        # changed teams (free agency/trade) leaves behind a placeholder row
        # keyed to their OLD team -- since (season, week, team, player_id) is
        # the primary key, inserting under their new team does not overwrite
        # it. A player no longer on ANY roster (retired/unsigned) should not
        # keep a dangling placeholder at all. Both cases are the same fix:
        # delete any synthetic row whose (player_id, team) pair isn't a
        # roster pair for this season. Real 'pbp_aggregation' rows are never
        # touched.
        if not dry_run:
            roster_pairs = {(r["player_id"], r["team"]) for r in roster_rows}
            stale = session.execute(
                text(
                    """
                    SELECT DISTINCT player_id, team FROM nfl_dp_player_usage_weekly
                    WHERE season = :season AND source = ANY(:guard_sources)
                    """
                ),
                {"season": season, "guard_sources": list(SYNTHETIC_PLAYER_SOURCES)},
            ).all()
            stale_pairs = [(r.player_id, r.team) for r in stale if (r.player_id, r.team) not in roster_pairs]
            for stale_player_id, stale_team in stale_pairs:
                session.execute(
                    text(
                        """
                        DELETE FROM nfl_dp_player_usage_weekly
                        WHERE season = :season AND source = ANY(:guard_sources)
                          AND player_id = :player_id AND team = :team
                        """
                    ),
                    {
                        "season": season,
                        "guard_sources": list(SYNTHETIC_PLAYER_SOURCES),
                        "player_id": stale_player_id,
                        "team": stale_team,
                    },
                )

        sum_cols = ", ".join(f"SUM({c})::numeric AS {c}" for c in _PLAYER_COUNT_COLUMNS)
        prior_usage_rows = session.execute(
            text(
                f"""
                SELECT player_id, MAX(player_name) AS player_name, COUNT(DISTINCT week) AS games,
                  {sum_cols}, AVG(success_rate) AS success_rate
                FROM nfl_dp_player_usage_weekly
                WHERE season = :prior AND games_played > 0
                GROUP BY player_id
                """
            ),
            {"prior": prior},
        ).mappings().all()
        prior_by_player = {r["player_id"]: dict(r) for r in prior_usage_rows}

        veterans_updated = 0
        rookies_inserted = 0
        no_baseline_available = 0

        for roster in roster_rows:
            player_id = roster["player_id"]
            team = roster["team"]
            position = (roster["position"] or "UNK").upper()
            prior_row = prior_by_player.get(player_id)

            if prior_row is not None:
                games = float(prior_row["games"] or 1)
                per_game = {c: float(prior_row[c] or 0) / games for c in _PLAYER_COUNT_COLUMNS}
                success_rate = prior_row["success_rate"]
                player_name = prior_row["player_name"]
                source = PLAYER_HYDRATE_SOURCE
            else:
                baseline = get_rookie_baseline(session, position=position, draft_number=roster["draft_number"])
                if baseline is None:
                    no_baseline_available += 1
                    continue
                per_game = {
                    "involvement_plays": float(baseline["avg_involvement_plays_per_game"] or 0),
                    "targets": float(baseline["avg_targets_per_game"] or 0),
                    "receptions": float(baseline["avg_receptions_per_game"] or 0),
                    "receiving_yards": float(baseline["avg_receiving_yards_per_game"] or 0),
                    "air_yards": 0.0,
                    "yards_after_catch": 0.0,
                    "rush_attempts": float(baseline["avg_rush_attempts_per_game"] or 0),
                    "rush_yards": float(baseline["avg_rush_yards_per_game"] or 0),
                    "pass_attempts": 0.0,
                    "pass_yards": 0.0,
                    "pass_touchdowns": 0.0,
                    "red_zone_targets": float(baseline["avg_red_zone_targets_per_game"] or 0),
                    "red_zone_carries": float(baseline["avg_red_zone_carries_per_game"] or 0),
                    "goal_to_go_carries": 0.0,
                    "qb_dropbacks": float(baseline["avg_qb_dropbacks_per_game"] or 0),
                    "qb_pressures_taken": 0.0,
                    "touchdowns_scored": 0.0,
                    "first_downs_generated": 0.0,
                    "explosive_plays": 0.0,
                }
                success_rate = baseline["avg_success_rate"]
                player_name = roster["player_name"]
                source = ROOKIE_BASELINE_SOURCE

            if dry_run:
                if prior_row is not None:
                    veterans_updated += 1
                else:
                    rookies_inserted += 1
                continue

            cols = ", ".join(_PLAYER_COUNT_COLUMNS)
            placeholders = ", ".join(f":{c}" for c in _PLAYER_COUNT_COLUMNS)
            params = dict(per_game)
            params.update(
                {
                    "season": season,
                    "team": team,
                    "player_id": player_id,
                    "player_name": player_name,
                    "position": position,
                    "success_rate": float(success_rate) if success_rate is not None else None,
                    "source": source,
                    "guard_sources": list(SYNTHETIC_PLAYER_SOURCES),
                }
            )
            for week in WEEKS:
                session.execute(
                    text(
                        f"""
                        INSERT INTO nfl_dp_player_usage_weekly (
                          season, week, team, player_id, player_name, position, games_played,
                          {cols}, success_rate, source, updated_at
                        ) VALUES (
                          :season, :week, :team, :player_id, :player_name, :position, 1,
                          {placeholders}, :success_rate, :source, NOW()
                        )
                        ON CONFLICT (season, week, team, player_id) DO UPDATE SET
                          team = EXCLUDED.team,
                          player_name = COALESCE(EXCLUDED.player_name, nfl_dp_player_usage_weekly.player_name),
                          position = EXCLUDED.position,
                          games_played = EXCLUDED.games_played,
                          {', '.join(f'{c} = EXCLUDED.{c}' for c in _PLAYER_COUNT_COLUMNS)},
                          success_rate = EXCLUDED.success_rate,
                          source = EXCLUDED.source,
                          updated_at = EXCLUDED.updated_at
                        WHERE nfl_dp_player_usage_weekly.source = ANY(:guard_sources)
                        """
                    ),
                    {**params, "week": week},
                )
            if prior_row is not None:
                veterans_updated += 1
            else:
                rookies_inserted += 1

        if not dry_run:
            session.commit()
        return {
            "status": "ok" if not dry_run else "dry_run",
            "season": season,
            "prior_season": prior,
            "roster_size": len(roster_rows),
            "veterans_hydrated": veterans_updated,
            "rookies_or_unproven_hydrated": rookies_inserted,
            "no_baseline_available": no_baseline_available,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


ROLLING_HYDRATE_SOURCE = "rolling_hydrate_v1"
# Every synthetic source this function is allowed to overwrite for FUTURE
# weeks -- deliberately includes its own tag (so re-running mid-season keeps
# refreshing forward) but never 'pbp_aggregation' (real played weeks).
_ROLLING_REFRESH_GUARD_SOURCES = ("carryforward_2025", PLAYER_HYDRATE_SOURCE, ROOKIE_BASELINE_SOURCE, ROLLING_HYDRATE_SOURCE)
# Shrinkage toward the real in-season trailing average as more real games
# accumulate: weight_real = min(1.0, real_games_so_far / SHRINKAGE_FULL_WEIGHT_GAMES).
# 4 games is a deliberate, documented choice (not fit to data): early in a
# season a player's role can still be genuinely unsettled (e.g. a rookie who
# barely played Week 1 but is now the clear starter by Week 3), so a small
# sample shouldn't fully override the preseason prior; by Week 5 (4 real
# games in hand) the in-season signal should dominate.
ROLLING_SHRINKAGE_FULL_WEIGHT_GAMES = 4.0


def compute_rolling_blend_weight(real_games: float, *, full_weight_games: float = ROLLING_SHRINKAGE_FULL_WEIGHT_GAMES) -> float:
    """Pure: how much weight the real in-season average gets vs. the
    existing (preseason/rookie) synthetic prior, as a function of how many
    real games are in hand so far. Linear ramp to 1.0 at `full_weight_games`."""
    if full_weight_games <= 0:
        return 1.0
    return max(0.0, min(1.0, float(real_games) / float(full_weight_games)))


def blend_usage_rates(
    real_per_game: Dict[str, float], existing_per_game: Dict[str, float], *, weight_real: float
) -> Dict[str, float]:
    """Pure: per-column weighted blend of a player's real in-season
    per-game usage rate and their existing synthetic per-game rate, for
    every key present in `real_per_game`. `weight_real` should come from
    `compute_rolling_blend_weight()`."""
    w = max(0.0, min(1.0, float(weight_real)))
    return {
        key: round((w * float(real_per_game.get(key) or 0.0)) + ((1.0 - w) * float(existing_per_game.get(key) or 0.0)), 6)
        for key in real_per_game
    }


def refresh_future_player_usage_from_rolling_real_weeks(
    *, season: int, through_week: int, dry_run: bool = False
) -> Dict[str, Any]:
    """Closes the "frozen preseason prior forever" gap: once real weeks
    have been played this season (`nfl_dp_player_usage_weekly.source =
    'pbp_aggregation'` for week <= `through_week`), blend each player's real
    in-season per-game average into every remaining FUTURE week (still
    tagged with a synthetic source -- see `_ROLLING_REFRESH_GUARD_SOURCES`)
    so a player's projected role keeps tracking their actual usage instead
    of staying pinned at the preseason/rookie-baseline snapshot for the rest
    of the year.

    This never touches a week that already has real `pbp_aggregation` data
    for that player (that data IS the ground truth for that week, nothing
    to refresh) -- it only rewrites still-synthetic FUTURE weeks with an
    updated blend. Idempotent and safe to call every week after that week's
    real usage has been ingested (see docs/NFL_PROPS_FANTASY_FOUNDATION.md's
    weekly cadence section for where this fits in the pipeline order).
    """
    session = SessionLocal()
    try:
        real_rows = session.execute(
            text(
                f"""
                SELECT player_id, team, MAX(player_name) AS player_name, COUNT(DISTINCT week) AS games,
                  {', '.join(f'SUM({c})::numeric AS {c}' for c in _PLAYER_COUNT_COLUMNS)},
                  AVG(success_rate) AS success_rate
                FROM nfl_dp_player_usage_weekly
                WHERE season = :season AND week <= :through_week AND source = 'pbp_aggregation'
                GROUP BY player_id, team
                """
            ),
            {"season": int(season), "through_week": int(through_week)},
        ).mappings().all()
        if not real_rows:
            return {"status": "skipped", "reason": f"no real pbp_aggregation weeks yet for season={season} through week={through_week}"}

        future_weeks = [w for w in WEEKS if w > int(through_week)]
        if not future_weeks:
            return {"status": "skipped", "reason": "no remaining future weeks this season"}

        players_refreshed = 0
        for row in real_rows:
            games = float(row["games"] or 0)
            if games <= 0:
                continue
            real_per_game = {c: float(row[c] or 0) / games for c in _PLAYER_COUNT_COLUMNS}

            existing = session.execute(
                text(
                    """
                    SELECT {cols}, success_rate
                    FROM nfl_dp_player_usage_weekly
                    WHERE season = :season AND team = :team AND player_id = :player_id
                      AND source = ANY(:guard_sources)
                    ORDER BY week DESC
                    LIMIT 1
                    """.format(cols=", ".join(_PLAYER_COUNT_COLUMNS))
                ),
                {
                    "season": int(season),
                    "team": row["team"],
                    "player_id": row["player_id"],
                    "guard_sources": list(_ROLLING_REFRESH_GUARD_SOURCES),
                },
            ).mappings().first()
            if existing is None:
                # No synthetic future-week baseline for this player (e.g. an
                # undrafted/UDFA pickup with no preseason row at all) --
                # nothing to blend toward without inventing a prior out of
                # nothing; skip rather than guess.
                continue

            weight_real = compute_rolling_blend_weight(games)
            existing_per_game = {c: float(existing[c] or 0.0) for c in _PLAYER_COUNT_COLUMNS}
            blended = blend_usage_rates(real_per_game, existing_per_game, weight_real=weight_real)
            blended_success_rate = (
                blend_usage_rates(
                    {"success_rate": float(row["success_rate"] or 0.0)},
                    {"success_rate": float(existing["success_rate"] or 0.0)},
                    weight_real=weight_real,
                )["success_rate"]
                if row["success_rate"] is not None or existing["success_rate"] is not None
                else None
            )

            if dry_run:
                players_refreshed += 1
                continue

            cols_set = ", ".join(f"{c} = :{c}" for c in _PLAYER_COUNT_COLUMNS)
            params = dict(blended)
            params.update(
                {
                    "season": int(season),
                    "team": row["team"],
                    "player_id": row["player_id"],
                    "player_name": row["player_name"],
                    "success_rate": blended_success_rate,
                    "source": ROLLING_HYDRATE_SOURCE,
                    "guard_sources": list(_ROLLING_REFRESH_GUARD_SOURCES),
                    "weeks": future_weeks,
                }
            )
            session.execute(
                text(
                    f"""
                    UPDATE nfl_dp_player_usage_weekly
                    SET {cols_set}, player_name = COALESCE(:player_name, player_name),
                        success_rate = :success_rate, source = :source, updated_at = NOW()
                    WHERE season = :season AND team = :team AND player_id = :player_id
                      AND week = ANY(:weeks) AND source = ANY(:guard_sources)
                    """
                ),
                params,
            )
            players_refreshed += 1

        if not dry_run:
            session.commit()
        return {
            "status": "ok" if not dry_run else "dry_run",
            "season": season,
            "through_week": through_week,
            "future_weeks_updated": future_weeks,
            "players_with_real_data": len(real_rows),
            "players_refreshed": players_refreshed,
            "shrinkage_full_weight_games": ROLLING_SHRINKAGE_FULL_WEIGHT_GAMES,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def run_preseason_bootstrap(
    *,
    season: int,
    prior_season: Optional[int] = None,
    use_market_signal: bool = True,
    market_blend_weight: float = 0.5,
    odds_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """The single entry point to run every offseason before Week 1.

    Order matters: rookie baselines must be refreshed first (in case a new
    completed rookie class from `prior_season` should join the historical
    sample), then team priors, then player priors (which depend on the
    freshly refreshed rookie baselines). Safe to re-run any time -- every
    step is idempotent and guarded against touching real in-season data.
    """
    result: Dict[str, Any] = {"season": season, "prior_season": prior_season or season - 1}

    result["rookie_baselines"] = compute_rookie_usage_baselines(through_season=prior_season or season - 1)

    market_percentile_by_team = None
    if use_market_signal:
        try:
            from .market_signals import fetch_market_sb_probabilities, market_probabilities_to_percentile_ranks

            probs = fetch_market_sb_probabilities(api_key=odds_api_key)
            market_percentile_by_team = market_probabilities_to_percentile_ranks(probs)
            result["market_signal"] = {"status": "ok", "teams": len(market_percentile_by_team)}
        except Exception as exc:
            result["market_signal"] = {"status": "failed", "error": str(exc)}

    result["team_situational"] = hydrate_preseason_team_situational(
        season=season,
        prior_season=prior_season,
        market_percentile_by_team=market_percentile_by_team,
        market_blend_weight=market_blend_weight,
    )
    result["player_usage"] = hydrate_preseason_player_usage(season=season, prior_season=prior_season)
    return result
