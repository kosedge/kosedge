"""Walk-forward backtest: matchup-aware box-score engine vs. the pre-session
flat/non-opponent-adjusted baseline vs. the already-shipped (this session)
opponent-adjusted flat baseline.

Read-only analysis script. Does NOT write to any production table. Imports
the REAL production functions from services/model-service/src (not a
re-implementation) so the backtest exercises the actual shipped code:
  - PlayerFeatureInputs / baseline_projection_from_features (flat point
    projection, with and without this session's team_snap_share/opponent
    fixes -- see the OLD vs CURRENT methodologies below)
  - TeamVolumeContext / PlayerBoxScoreRole / simulate_team_player_box_scores /
    compute_team_volume_context (the new box-score Monte Carlo engine)

Three methodologies compared against real actual box scores:
  OLD      -- baseline_projection_from_features called with
              team_snap_share=0.0 (falls back to the old touch-share
              `snap_proxy` signal) and opponent_pass_defense_factor /
              opponent_rush_defense_factor forced to 1.0 (neutral). This is
              exactly the pre-this-session production behavior (both fixes
              are backward-compatible fallbacks by design -- see
              test_qb_volume_falls_back_to_snap_proxy_when_team_snap_share_missing
              in services/model-service/tests/test_nfl_player_projection_engine.py).
  CURRENT  -- the same function with this session's real team_snap_share
              and real opponent-adjusted factors wired through (already
              shipped earlier this session, still a flat single-mean
              projection -- no per-game Monte Carlo).
  NEW      -- this session's box-score engine: CURRENT's baseline feeds
              simulate_team_player_box_scores(), which re-derives each
              player's mean via the team-volume-anchored Dirichlet
              allocation (see nfl_player_box_score_simulator.py's
              docstring for why this can shift the mean, not just add
              variance).

ALL THREE are computed walk-forward: every input for target week W is
built from TRAILING real weeks (< W) only, this season -- exactly replicating
the walk-forward discipline of the existing preseason methodology backtests
in ../nfl-preseason-methodology-backtest/, extended to this new engine.

Usage: python3 backtest_matchup_engine.py
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict

import psycopg

MODEL_SERVICE_SRC = "/Users/ryankos/kosedge/services/model-service"
sys.path.insert(0, MODEL_SERVICE_SRC)

from src.services.nfl_player_projection_engine import (  # noqa: E402
    PlayerFeatureInputs,
    baseline_projection_from_features,
)
from src.services.nfl_player_box_score_simulator import (  # noqa: E402
    PlayerBoxScoreRole,
    compute_team_volume_context,
    simulate_team_player_box_scores,
)

DATABASE_URL = "postgresql://ryankos:postgres@127.0.0.1:5432/kosedge"
FULL_SAMPLE_SEASONS = [2023, 2024, 2025]
FULL_SAMPLE_WEEKS = list(range(4, 18))  # 4..17 inclusive: needs >=3 trailing real weeks
BOX_SCORE_SUBSET_WEEKS = [6, 10, 14]  # expensive Monte Carlo comparison, smaller slate
BOX_SCORE_REPLICATES = 2000
SKILL_POSITIONS = ("QB", "RB", "WR", "TE")


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def load_real_usage(conn, seasons):
    rows = conn.execute(
        """
        SELECT season, week, team, player_id, player_name, position,
          involvement_plays, targets, receptions, rush_attempts,
          pass_attempts, pass_yards, rush_yards, receiving_yards,
          red_zone_targets, red_zone_carries, qb_dropbacks, qb_pressures_taken,
          success_rate
        FROM nfl_dp_player_usage_weekly
        WHERE season = ANY(%(seasons)s) AND source = 'pbp_aggregation'
        """,
        {"seasons": seasons},
    ).fetchall()
    cols = [
        "season", "week", "team", "player_id", "player_name", "position",
        "involvement_plays", "targets", "receptions", "rush_attempts",
        "pass_attempts", "pass_yards", "rush_yards", "receiving_yards",
        "red_zone_targets", "red_zone_carries", "qb_dropbacks", "qb_pressures_taken",
        "success_rate",
    ]
    return [dict(zip(cols, r)) for r in rows]


def load_team_situational(conn, seasons):
    rows = conn.execute(
        """
        SELECT season, week, team, offensive_plays, pass_rate,
          epa_per_play_defense_allowed, pressure_rate_generated, games_played
        FROM nfl_dp_team_situational_weekly
        WHERE season = ANY(%(seasons)s) AND source = 'nflverse'
        """,
        {"seasons": seasons},
    ).fetchall()
    cols = ["season", "week", "team", "offensive_plays", "pass_rate", "epa_per_play_defense_allowed", "pressure_rate_generated", "games_played"]
    return [dict(zip(cols, r)) for r in rows]


def load_schedules(conn, seasons):
    rows = conn.execute(
        """
        SELECT season, week, game_id, home_team, away_team
        FROM nfl_dp_schedules
        WHERE season = ANY(%(seasons)s) AND home_score IS NOT NULL
        """,
        {"seasons": seasons},
    ).fetchall()
    cols = ["season", "week", "game_id", "home_team", "away_team"]
    return [dict(zip(cols, r)) for r in rows]


def build_indices(usage_rows, situational_rows, schedule_rows):
    usage_by_team_week = defaultdict(list)
    for r in usage_rows:
        usage_by_team_week[(r["season"], r["week"], r["team"])].append(r)

    situational_by_team_week = {}
    for r in situational_rows:
        situational_by_team_week[(r["season"], r["week"], r["team"])] = r

    opponent_by_team_week = {}
    for r in schedule_rows:
        opponent_by_team_week[(r["season"], r["week"], r["home_team"])] = r["away_team"]
        opponent_by_team_week[(r["season"], r["week"], r["away_team"])] = r["home_team"]

    return usage_by_team_week, situational_by_team_week, opponent_by_team_week


def trailing_weeks(season, week, lookback_cap=8):
    lo = max(1, week - lookback_cap)
    return list(range(lo, week))


def trailing_team_situational(situational_by_team_week, season, team, week):
    rows = []
    for w in trailing_weeks(season, week):
        r = situational_by_team_week.get((season, w, team))
        if r is not None and (r["games_played"] or 0) > 0:
            rows.append(r)
    return rows


def trailing_league_avg_epa_allowed(situational_by_team_week, season, week, teams):
    vals = []
    for team in teams:
        rows = trailing_team_situational(situational_by_team_week, season, team, week)
        for r in rows:
            if r["epa_per_play_defense_allowed"] is not None:
                vals.append(float(r["epa_per_play_defense_allowed"]))
    return statistics.fmean(vals) if vals else 0.0


def build_player_trailing_features(usage_by_team_week, situational_by_team_week, season, team, week, player_id):
    weeks = trailing_weeks(season, week)
    player_rows = []
    team_involvement_total = 0.0
    team_targets_total = 0.0
    team_rush_total = 0.0
    team_rz_total = 0.0
    my_involvement = 0.0
    my_targets = 0.0
    my_receptions = 0.0
    my_rush = 0.0
    my_rz = 0.0
    my_dropbacks = 0.0
    my_pressures = 0.0
    my_success_vals = []

    for w in weeks:
        team_rows = usage_by_team_week.get((season, w, team), [])
        if not team_rows:
            continue
        team_involvement_total += sum(float(r["involvement_plays"] or 0) for r in team_rows)
        team_targets_total += sum(float(r["targets"] or 0) for r in team_rows)
        team_rush_total += sum(float(r["rush_attempts"] or 0) for r in team_rows)
        team_rz_total += sum(float((r["red_zone_targets"] or 0) + (r["red_zone_carries"] or 0)) for r in team_rows)
        for r in team_rows:
            if r["player_id"] == player_id:
                player_rows.append(r)
                my_involvement += float(r["involvement_plays"] or 0)
                my_targets += float(r["targets"] or 0)
                my_receptions += float(r["receptions"] or 0)
                my_rush += float(r["rush_attempts"] or 0)
                my_rz += float((r["red_zone_targets"] or 0) + (r["red_zone_carries"] or 0))
                my_dropbacks += float(r["qb_dropbacks"] or 0)
                my_pressures += float(r["qb_pressures_taken"] or 0)
                if r["success_rate"] is not None:
                    my_success_vals.append(float(r["success_rate"]))

    if not player_rows:
        return None

    situational_rows = trailing_team_situational(situational_by_team_week, season, team, week)
    team_offensive_plays_total = sum(float(r["offensive_plays"] or 0) for r in situational_rows)

    return {
        "trailing_games": len(player_rows),
        "snap_proxy": _clamp(my_involvement / (team_involvement_total + 1.0), 0.0, 1.0),
        # Correctly-denominated team snap share (involvement / team's real
        # offensive plays, NOT teammates' pooled touches -- see
        # infra/db/031_nfl_player_team_snap_share.sql) computed the same
        # walk-forward way as every other feature here.
        "team_snap_share": _clamp(my_involvement / (team_offensive_plays_total + 1.0), 0.0, 1.0),
        "target_proxy": _clamp(my_targets / (team_targets_total + 1.0), 0.0, 1.0),
        "route_proxy": _clamp((my_targets + my_receptions) / (team_targets_total + 1.0), 0.0, 1.0),
        "rush_share": _clamp(my_rush / (team_rush_total + 1.0), 0.0, 1.0),
        "red_zone_share": _clamp(my_rz / (team_rz_total + 1.0), 0.0, 1.0),
        "qb_dropback_factor": _clamp(my_dropbacks / (my_involvement + 1.0), 0.5, 1.5),
        "qb_pressure_factor": _clamp((my_pressures / (my_dropbacks + 1.0)) * 3.0, 0.5, 1.5),
        "success_rate": statistics.fmean(my_success_vals) if my_success_vals else 0.5,
    }


def build_team_trailing_features(situational_by_team_week, season, team, week):
    rows = trailing_team_situational(situational_by_team_week, season, team, week)
    if not rows:
        return {"team_pace_factor": 1.0, "team_pass_rate_factor": 1.0}
    plays = [float(r["offensive_plays"] or 0) for r in rows]
    rates = [float(r["pass_rate"]) for r in rows if r["pass_rate"] is not None]
    mean_plays = statistics.fmean(plays) if plays else 64.0
    mean_rate = statistics.fmean(rates) if rates else 0.55
    return {
        "team_pace_factor": _clamp(mean_plays / 64.0, 0.75, 1.25),
        "team_pass_rate_factor": _clamp(mean_rate / 0.55, 0.75, 1.25),
    }


def build_opponent_factors(situational_by_team_week, season, week, opponent, league_avg_epa_allowed):
    rows = trailing_team_situational(situational_by_team_week, season, opponent, week)
    if not rows:
        return {"opponent_pass_defense_factor": 1.0, "opponent_rush_defense_factor": 1.0}
    epa_vals = [float(r["epa_per_play_defense_allowed"]) for r in rows if r["epa_per_play_defense_allowed"] is not None]
    pressure_vals = [float(r["pressure_rate_generated"]) for r in rows if r["pressure_rate_generated"] is not None]
    opp_epa = statistics.fmean(epa_vals) if epa_vals else 0.0
    opp_pressure = statistics.fmean(pressure_vals) if pressure_vals else 0.22
    pass_factor = _clamp(1.0 + (1.15 * (opp_epa - league_avg_epa_allowed)) - (0.35 * (opp_pressure - 0.22)), 0.75, 1.30)
    rush_factor = _clamp(1.0 + (1.15 * (opp_epa - league_avg_epa_allowed)), 0.75, 1.30)
    return {"opponent_pass_defense_factor": pass_factor, "opponent_rush_defense_factor": rush_factor}


def build_role_confidence(player_features):
    return _clamp(
        (0.40 * player_features["snap_proxy"]) + (0.35 * player_features["target_proxy"]) + (0.25 * player_features["success_rate"]),
        0.15,
        0.99,
    )


def old_and_current_predictions(position, player_features, team_features, opponent_features, role_confidence):
    common = dict(
        position=position,
        snap_proxy=player_features["snap_proxy"],
        route_proxy=player_features["route_proxy"],
        target_proxy=player_features["target_proxy"],
        rush_share=player_features["rush_share"],
        red_zone_share=player_features["red_zone_share"],
        qb_dropback_factor=player_features["qb_dropback_factor"],
        qb_pressure_factor=player_features["qb_pressure_factor"],
        team_pace_factor=team_features["team_pace_factor"],
        team_pass_rate_factor=team_features["team_pass_rate_factor"],
        availability_confidence=0.90,
        role_confidence=role_confidence,
    )
    old = baseline_projection_from_features(
        PlayerFeatureInputs(**common, team_snap_share=0.0, opponent_pass_defense_factor=1.0, opponent_rush_defense_factor=1.0)
    )
    current = baseline_projection_from_features(
        PlayerFeatureInputs(
            **common,
            team_snap_share=player_features["team_snap_share"],
            opponent_pass_defense_factor=opponent_features["opponent_pass_defense_factor"],
            opponent_rush_defense_factor=opponent_features["opponent_rush_defense_factor"],
        )
    )
    return old, current


def mae(errors):
    return statistics.fmean(abs(e) for e in errors) if errors else float("nan")


def bias(errors):
    return statistics.fmean(errors) if errors else float("nan")


def main():
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    print("Loading real usage/situational/schedule data...")
    usage_rows = load_real_usage(conn, FULL_SAMPLE_SEASONS)
    situational_rows = load_team_situational(conn, FULL_SAMPLE_SEASONS)
    schedule_rows = load_schedules(conn, FULL_SAMPLE_SEASONS)
    usage_by_team_week, situational_by_team_week, opponent_by_team_week = build_indices(usage_rows, situational_rows, schedule_rows)

    teams_by_season = defaultdict(set)
    for r in situational_rows:
        teams_by_season[r["season"]].add(r["team"])

    full_records = []
    box_score_records = []

    for season in FULL_SAMPLE_SEASONS:
        for week in FULL_SAMPLE_WEEKS:
            league_avg_epa_allowed = trailing_league_avg_epa_allowed(situational_by_team_week, season, week, teams_by_season[season])
            teams_this_week = {team for (s, w, team) in usage_by_team_week if s == season and w == week}
            run_box_score = week in BOX_SCORE_SUBSET_WEEKS

            for team in teams_this_week:
                opponent = opponent_by_team_week.get((season, week, team))
                truth_rows = usage_by_team_week.get((season, week, team), [])
                team_features = build_team_trailing_features(situational_by_team_week, season, team, week)
                opponent_features = (
                    build_opponent_factors(situational_by_team_week, season, week, opponent, league_avg_epa_allowed)
                    if opponent
                    else {"opponent_pass_defense_factor": 1.0, "opponent_rush_defense_factor": 1.0}
                )

                team_context = None
                if run_box_score:
                    trailing_rows = trailing_team_situational(situational_by_team_week, season, team, week)
                    team_context = compute_team_volume_context(
                        [{"offensive_plays": r["offensive_plays"], "pass_rate": r["pass_rate"]} for r in trailing_rows]
                    )

                roles = []
                truth_by_key = {}
                pred_meta_by_key = {}

                for truth_row in truth_rows:
                    position = (truth_row["position"] or "").upper()
                    if position not in SKILL_POSITIONS:
                        continue
                    if float(truth_row["involvement_plays"] or 0) <= 0:
                        continue
                    player_features = build_player_trailing_features(usage_by_team_week, situational_by_team_week, season, team, week, truth_row["player_id"])
                    if player_features is None or player_features["trailing_games"] < 1:
                        continue
                    role_confidence = build_role_confidence(player_features)
                    old_pred, current_pred = old_and_current_predictions(position, player_features, team_features, opponent_features, role_confidence)

                    key = truth_row["player_id"]
                    truth_by_key[key] = truth_row
                    pred_meta_by_key[key] = {"old": old_pred, "current": current_pred, "position": position, "player_name": truth_row["player_name"]}

                    rec = {
                        "season": season, "week": week, "team": team, "position": position, "player_name": truth_row["player_name"],
                        "trailing_games": player_features["trailing_games"],
                        "truth_pass_yards": float(truth_row["pass_yards"] or 0), "truth_rush_yards": float(truth_row["rush_yards"] or 0),
                        "truth_receiving_yards": float(truth_row["receiving_yards"] or 0), "truth_targets": float(truth_row["targets"] or 0),
                        "truth_receptions": float(truth_row["receptions"] or 0),
                        "old_pass_yards": old_pred["pass_yards_mean"], "old_rush_yards": old_pred["rush_yards_mean"],
                        "old_receiving_yards": old_pred["receiving_yards_mean"], "old_targets": old_pred["targets_mean"],
                        "old_receptions": old_pred["receptions_mean"],
                        "current_pass_yards": current_pred["pass_yards_mean"], "current_rush_yards": current_pred["rush_yards_mean"],
                        "current_receiving_yards": current_pred["receiving_yards_mean"], "current_targets": current_pred["targets_mean"],
                        "current_receptions": current_pred["receptions_mean"],
                    }
                    full_records.append(rec)

                    if run_box_score:
                        roles.append(
                            PlayerBoxScoreRole(
                                player_key=key,
                                player_name=str(truth_row["player_name"] or ""),
                                position=position,
                                baseline=current_pred,
                                role_confidence=role_confidence,
                                experience_confidence=1.0,
                            )
                        )

                if run_box_score and roles and team_context is not None:
                    sim_result = simulate_team_player_box_scores(team_context, roles, replicates=BOX_SCORE_REPLICATES, seed=hash((season, week, team)) % (2**31))
                    for key, dist in sim_result.items():
                        truth_row = truth_by_key[key]
                        meta = pred_meta_by_key[key]
                        box_score_records.append(
                            {
                                "season": season, "week": week, "team": team, "position": meta["position"], "player_name": meta["player_name"],
                                "truth_pass_yards": float(truth_row["pass_yards"] or 0), "truth_rush_yards": float(truth_row["rush_yards"] or 0),
                                "truth_receiving_yards": float(truth_row["receiving_yards"] or 0), "truth_targets": float(truth_row["targets"] or 0),
                                "truth_receptions": float(truth_row["receptions"] or 0),
                                "old_pass_yards": meta["old"]["pass_yards_mean"], "old_rush_yards": meta["old"]["rush_yards_mean"],
                                "old_receiving_yards": meta["old"]["receiving_yards_mean"], "old_targets": meta["old"]["targets_mean"],
                                "old_receptions": meta["old"]["receptions_mean"],
                                "current_pass_yards": meta["current"]["pass_yards_mean"], "current_rush_yards": meta["current"]["rush_yards_mean"],
                                "current_receiving_yards": meta["current"]["receiving_yards_mean"], "current_targets": meta["current"]["targets_mean"],
                                "current_receptions": meta["current"]["receptions_mean"],
                                "new_pass_yards": dist["pass_yards_dist"]["mean"], "new_rush_yards": dist["rush_yards_dist"]["mean"],
                                "new_receiving_yards": dist["receiving_yards_dist"]["mean"], "new_targets": dist["targets_dist"]["mean"],
                                "new_receptions": dist["receptions_dist"]["mean"],
                            }
                        )

        print(f"season {season} done: full_records={len(full_records)} box_score_records={len(box_score_records)}")

    with open("/Users/ryankos/kosedge/data/ops/nfl-matchup-engine-backtest/full_sample_records.json", "w") as f:
        json.dump(full_records, f, default=str)
    with open("/Users/ryankos/kosedge/data/ops/nfl-matchup-engine-backtest/box_score_records.json", "w") as f:
        json.dump(box_score_records, f, default=str)

    print(f"\nTOTAL full_records={len(full_records)}  box_score_records={len(box_score_records)}")

    def report(records, methods, stats):
        print(f"\n=== Pooled (n={len(records)}) ===")
        for stat in stats:
            print(f"-- {stat} --")
            for m in methods:
                errors = [r[f"{m}_{stat}"] - r[f"truth_{stat}"] for r in records]
                print(f"   {m:10s} MAE={mae(errors):7.3f}  bias={bias(errors):7.3f}")
        print("\n=== By position ===")
        by_pos = defaultdict(list)
        for r in records:
            by_pos[r["position"]].append(r)
        for pos in sorted(by_pos):
            rows = by_pos[pos]
            print(f"-- {pos} (n={len(rows)}) --")
            for stat in stats:
                line = f"   {stat:16s}"
                for m in methods:
                    errors = [r[f"{m}_{stat}"] - r[f"truth_{stat}"] for r in rows]
                    line += f"  {m}_MAE={mae(errors):7.3f}"
                print(line)

    print("\n\n########## FULL SAMPLE: OLD vs CURRENT (weeks 4-17, 2023-2025) ##########")
    report(full_records, ["old", "current"], ["pass_yards", "rush_yards", "receiving_yards", "targets", "receptions"])

    print("\n\n########## BOX-SCORE SUBSET: OLD vs CURRENT vs NEW (weeks 6/10/14, 2023-2025) ##########")
    report(box_score_records, ["old", "current", "new"], ["pass_yards", "rush_yards", "receiving_yards", "targets", "receptions"])


if __name__ == "__main__":
    main()
