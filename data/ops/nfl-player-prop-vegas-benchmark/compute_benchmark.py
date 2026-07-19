"""Compute the player-prop-vs-real-market benchmark: for the real historical
closing lines pulled by `pull_historical_player_props.py`, walk-forward
project each player/game with this session's CURRENT model (and, for
comparison, the pre-session OLD flat formula and the NEW box-score Monte
Carlo engine), then grade "would betting the model-favored side at the real
closing price have paid off against the real outcome" -- NOT the
MAE-vs-truth question already answered by
`data/ops/nfl-matchup-engine-backtest/backtest_matchup_engine.py`.

Reuses REAL production code, not a reimplementation:
  - `baseline_projection_from_features` / `PlayerFeatureInputs` (the flat
    OLD/CURRENT projection formula) and `evaluate_prop_edge` (via
    `nfl_player_prop_backtest_scoring.grade_prop_bet`) --
    services/model-service/src/services/nfl_player_projection_engine.py
  - `simulate_team_player_box_scores` / `compute_team_volume_context` /
    `PlayerBoxScoreRole` (the NEW box-score engine) --
    services/model-service/src/services/nfl_player_box_score_simulator.py
  - The exact walk-forward trailing-feature-construction functions
    (`build_player_trailing_features`, `build_team_trailing_features`,
    `build_opponent_factors`, `build_role_confidence`,
    `old_and_current_predictions`, `load_real_usage`,
    `load_team_situational`, `load_schedules`, `build_indices`,
    `trailing_weeks`, `trailing_team_situational`,
    `trailing_league_avg_epa_allowed`) are imported directly from
    `backtest_matchup_engine.py` -- that script already re-derives these
    the same no-lookahead way this task requires, so reimplementing them a
    second time here would risk a subtle walk-forward/leakage divergence
    between the two backtests for no benefit.
  - `grade_prop_bet` / `summarize_grades` --
    services/model-service/src/services/nfl_player_prop_backtest_scoring.py
    (new pure module written for this task, unit-tested separately).

Read-only analysis script. Does not write to any production table.

Usage: /Users/ryankos/kosedge/.venv/bin/python3 compute_benchmark.py
"""

from __future__ import annotations

import importlib.util
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psycopg

MODEL_SERVICE_SRC = "/Users/ryankos/kosedge/services/model-service"
sys.path.insert(0, MODEL_SERVICE_SRC)

from src.services.nfl_player_box_score_simulator import (  # noqa: E402
    PlayerBoxScoreRole,
    compute_team_volume_context,
    simulate_team_player_box_scores,
)
from src.services.nfl_player_prop_backtest_scoring import (  # noqa: E402
    grade_prop_bet,
    summarize_grades,
)

BACKTEST_DIR = "/Users/ryankos/kosedge/data/ops/nfl-matchup-engine-backtest"
_spec = importlib.util.spec_from_file_location("backtest_matchup_engine", str(Path(BACKTEST_DIR) / "backtest_matchup_engine.py"))
bme = importlib.util.module_from_spec(_spec)
sys.modules["backtest_matchup_engine"] = bme
_spec.loader.exec_module(bme)  # type: ignore[union-attr]

DATABASE_URL = "postgresql://ryankos:postgres@127.0.0.1:5432/kosedge"
SEASONS = [2023, 2024, 2025]
SKILL_POSITIONS = ("QB", "RB", "WR", "TE")
MARKET_TO_STAT = {"pass_yds": "pass_yards", "rush_yds": "rush_yards", "rec_yds": "receiving_yards"}
BOOK_PREFERENCE = ["draftkings", "fanduel"]
BOX_SCORE_REPLICATES = 2000

OUTPUT_DIR = Path(__file__).parent
SUFFIX_RE = re.compile(r"\b(jr|sr|ii|iii|iv)\.?\b", re.IGNORECASE)


def normalize_player_name(raw: str) -> str:
    """Real nflverse usage rows and the real Odds API disagree on player
    name FORMAT for the same real player -- nflverse mostly uses
    "F.Lastname" (e.g. "J.Love", "A.St. Brown", "M.Pittman" -- suffix
    already dropped at the source), the Odds API always uses a full
    "First Last[ Suffix]" (e.g. "Jordan Love", "Amon-Ra St. Brown",
    "Michael Pittman Jr."), and a real minority of nflverse rows use full
    names too (observed for at least one real 2023 rookie, "Jay Higgins").
    A plain string-normalize (lowercase/strip punctuation) therefore does
    NOT make these two real formats agree ("jlove" vs "jordan love").

    This instead reduces EITHER format to a `{first_initial}|{lastname_no_spaces}`
    key: only the first character of whatever the first token is gets used
    (works whether that token is already just an initial like "A" or a
    full first name like "Amon-Ra" or "AJ"), and every remaining token is
    the last name with suffixes (Jr/Sr/II/III/IV) and separators dropped.
    Matching is additionally scoped to one real team's roster for one real
    game elsewhere in this script, so the small remaining collision risk
    (two skill players on the same team sharing a first initial AND last
    name) is negligible in practice."""
    s = SUFFIX_RE.sub("", str(raw or ""))
    s = s.replace(".", " ").replace("'", "")
    tokens = [t for t in re.split(r"[\s]+", s.strip()) if t]
    if not tokens:
        return ""
    initial = tokens[0][0].lower()
    lastname = "".join(t.lower() for t in tokens[1:])
    return f"{initial}|{lastname}"


def load_market_snapshot_rows(conn: psycopg.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT season, week, sportsbook, player_name, market_key, line,
          over_price, under_price, metadata
        FROM nfl_player_prop_market_snapshots
        WHERE source = 'odds_api_historical'
        """
    ).fetchall()
    cols = ["season", "week", "sportsbook", "player_name", "market_key", "line", "over_price", "under_price", "metadata"]
    return [dict(zip(cols, r)) for r in rows]


def pick_preferred_snapshot(rows_for_key: List[Dict[str, Any]]) -> Dict[str, Any]:
    for book in BOOK_PREFERENCE:
        for r in rows_for_key:
            if r["sportsbook"] == book:
                return r
    return rows_for_key[0]


def build_market_index(snapshot_rows: List[Dict[str, Any]]) -> Dict[Tuple[int, int, str, str, str], Dict[str, Any]]:
    """(season, week, home_team, away_team, market_key) -> {normalized_name: preferred_row}."""
    grouped: Dict[Tuple[int, int, str, str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for r in snapshot_rows:
        meta = r["metadata"] or {}
        home = meta.get("queried_home_team")
        away = meta.get("queried_away_team")
        if not home or not away:
            continue
        norm_name = normalize_player_name(r["player_name"])
        key = (int(r["season"]), int(r["week"]), home, away, r["market_key"], norm_name)
        grouped[key].append(r)

    out: Dict[Tuple[int, int, str, str, str], Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for (season, week, home, away, market_key, norm_name), candidates in grouped.items():
        out[(season, week, home, away, market_key)][norm_name] = pick_preferred_snapshot(candidates)
    return out


def load_sample_games_from_snapshots(snapshot_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[Tuple[int, int, str, str], Dict[str, Any]] = {}
    for r in snapshot_rows:
        meta = r["metadata"] or {}
        home = meta.get("queried_home_team")
        away = meta.get("queried_away_team")
        if not home or not away:
            continue
        key = (int(r["season"]), int(r["week"]), home, away)
        seen.setdefault(key, {"season": int(r["season"]), "week": int(r["week"]), "home_team": home, "away_team": away})
    return sorted(seen.values(), key=lambda g: (g["season"], g["week"], g["home_team"], g["away_team"]))


def build_team_roles_and_predictions(
    *,
    season: int,
    week: int,
    team: str,
    opponent: Optional[str],
    usage_by_team_week,
    situational_by_team_week,
    league_avg_epa_allowed: float,
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, float]]:
    """Returns (truth_rows, old_pred_by_player_id, current_pred_by_player_id)
    for every real skill-position player with real involvement in this
    team's game -- exact same eligibility/feature-construction as
    backtest_matchup_engine.main()'s per-team loop."""
    truth_rows_all = usage_by_team_week.get((season, week, team), [])
    team_features = bme.build_team_trailing_features(situational_by_team_week, season, team, week)
    opponent_features = (
        bme.build_opponent_factors(situational_by_team_week, season, week, opponent, league_avg_epa_allowed)
        if opponent
        else {"opponent_pass_defense_factor": 1.0, "opponent_rush_defense_factor": 1.0}
    )

    eligible_truth_rows = []
    old_by_id: Dict[str, Dict[str, Any]] = {}
    current_by_id: Dict[str, Dict[str, Any]] = {}
    role_confidence_by_id: Dict[str, float] = {}

    for truth_row in truth_rows_all:
        position = (truth_row["position"] or "").upper()
        if position not in SKILL_POSITIONS:
            continue
        if float(truth_row["involvement_plays"] or 0) <= 0:
            continue
        player_features = bme.build_player_trailing_features(usage_by_team_week, situational_by_team_week, season, team, week, truth_row["player_id"])
        if player_features is None or player_features["trailing_games"] < 1:
            continue
        role_confidence = bme.build_role_confidence(player_features)
        old_pred, current_pred = bme.old_and_current_predictions(position, player_features, team_features, opponent_features, role_confidence)

        pid = truth_row["player_id"]
        eligible_truth_rows.append(truth_row)
        old_by_id[pid] = old_pred
        current_by_id[pid] = current_pred
        role_confidence_by_id[pid] = role_confidence

    return eligible_truth_rows, old_by_id, current_by_id, role_confidence_by_id  # type: ignore[return-value]


def simulate_new_for_team(
    *,
    season: int,
    week: int,
    team: str,
    situational_by_team_week,
    truth_rows: List[Dict[str, Any]],
    current_by_id: Dict[str, Dict[str, Any]],
    role_confidence_by_id: Dict[str, float],
) -> Dict[str, Dict[str, Any]]:
    trailing_rows = bme.trailing_team_situational(situational_by_team_week, season, team, week)
    team_context = compute_team_volume_context([{"offensive_plays": r["offensive_plays"], "pass_rate": r["pass_rate"]} for r in trailing_rows])
    roles = [
        PlayerBoxScoreRole(
            player_key=tr["player_id"],
            player_name=str(tr["player_name"] or ""),
            position=(tr["position"] or "").upper(),
            baseline=current_by_id[tr["player_id"]],
            role_confidence=role_confidence_by_id[tr["player_id"]],
            experience_confidence=1.0,
        )
        for tr in truth_rows
    ]
    if not roles:
        return {}
    return simulate_team_player_box_scores(team_context, roles, replicates=BOX_SCORE_REPLICATES, seed=hash((season, week, team, "prop_benchmark")) % (2**31))


STAT_TO_DIST_KEY = {"pass_yards": "pass_yards_dist", "rush_yards": "rush_yards_dist", "receiving_yards": "receiving_yards_dist"}
STAT_TO_MEAN_KEY = {"pass_yards": "pass_yards_mean", "rush_yards": "rush_yards_mean", "receiving_yards": "receiving_yards_mean"}
STAT_TO_STD_KEY = {"pass_yards": "pass_yards_std", "rush_yards": "rush_yards_std", "receiving_yards": "receiving_yards_std"}


def main() -> None:
    conn = psycopg.connect(DATABASE_URL, autocommit=True)

    print("Loading real market snapshot rows...")
    snapshot_rows = load_market_snapshot_rows(conn)
    print(f"  {len(snapshot_rows)} raw snapshot rows")
    market_index = build_market_index(snapshot_rows)
    sample_games = load_sample_games_from_snapshots(snapshot_rows)
    print(f"  {len(sample_games)} distinct real games in the pulled sample")

    print("Loading real usage/situational/schedule data (2023-2025, for walk-forward trailing features)...")
    usage_rows = bme.load_real_usage(conn, SEASONS)
    situational_rows = bme.load_team_situational(conn, SEASONS)
    schedule_rows = bme.load_schedules(conn, SEASONS)
    usage_by_team_week, situational_by_team_week, opponent_by_team_week = bme.build_indices(usage_rows, situational_rows, schedule_rows)

    teams_by_season: Dict[int, set] = defaultdict(set)
    for r in situational_rows:
        teams_by_season[r["season"]].add(r["team"])

    records: List[Dict[str, Any]] = []
    games_processed = 0
    games_skipped_no_usage = 0

    for game in sample_games:
        season, week, home, away = game["season"], game["week"], game["home_team"], game["away_team"]
        league_avg_epa_allowed = bme.trailing_league_avg_epa_allowed(situational_by_team_week, season, week, teams_by_season[season])

        game_had_any_match = False
        for team, opponent in ((home, away), (away, home)):
            truth_rows, old_by_id, current_by_id, role_conf_by_id = build_team_roles_and_predictions(
                season=season, week=week, team=team, opponent=opponent,
                usage_by_team_week=usage_by_team_week, situational_by_team_week=situational_by_team_week,
                league_avg_epa_allowed=league_avg_epa_allowed,
            )
            if not truth_rows:
                continue

            new_dist_by_id = simulate_new_for_team(
                season=season, week=week, team=team, situational_by_team_week=situational_by_team_week,
                truth_rows=truth_rows, current_by_id=current_by_id, role_confidence_by_id=role_conf_by_id,
            )

            name_to_pid: Dict[str, str] = {}
            for tr in truth_rows:
                norm = normalize_player_name(tr["player_name"])
                if norm and norm not in name_to_pid:
                    name_to_pid[norm] = tr["player_id"]
            truth_by_pid = {tr["player_id"]: tr for tr in truth_rows}

            for market_key, stat in MARKET_TO_STAT.items():
                snapshots_for_market = market_index.get((season, week, home, away, market_key), {})
                for norm_name, snap in snapshots_for_market.items():
                    pid = name_to_pid.get(norm_name)
                    if pid is None:
                        continue
                    if pid not in old_by_id:
                        continue
                    truth_row = truth_by_pid[pid]
                    actual = float(truth_row.get(stat) or 0.0)
                    line = float(snap["line"]) if snap["line"] is not None else None
                    if line is None:
                        continue
                    over_price = snap["over_price"]
                    under_price = snap["under_price"]
                    if over_price is None and under_price is None:
                        continue

                    old_pred = old_by_id[pid]
                    current_pred = current_by_id[pid]
                    new_dist = (new_dist_by_id or {}).get(pid, {}).get(STAT_TO_DIST_KEY[stat])

                    game_had_any_match = True
                    record = {
                        "season": season, "week": week, "team": team, "opponent": opponent,
                        "player_id": pid, "player_name": truth_row["player_name"], "position": truth_row["position"],
                        "market_key": market_key, "stat": stat, "line": line,
                        "over_price": over_price, "under_price": under_price, "sportsbook": snap["sportsbook"],
                        "actual": actual,
                        "old_mean": old_pred[STAT_TO_MEAN_KEY[stat]], "old_std": old_pred[STAT_TO_STD_KEY[stat]],
                        "current_mean": current_pred[STAT_TO_MEAN_KEY[stat]], "current_std": current_pred[STAT_TO_STD_KEY[stat]],
                        "new_mean": (new_dist or {}).get("mean"), "new_std": (new_dist or {}).get("std"),
                    }
                    records.append(record)
            if truth_rows:
                games_processed += 1
        if not game_had_any_match:
            games_skipped_no_usage += 1

    print(f"\nGame-sides processed: {games_processed}  games with zero matched props: {games_skipped_no_usage}")
    print(f"Total (player, market, game) graded records: {len(records)}")

    with open(OUTPUT_DIR / "raw_prop_records.json", "w") as f:
        json.dump(records, f, default=str, indent=2)

    methodologies = ["old", "current", "new"]
    grades_by_method: Dict[str, list] = {m: [] for m in methodologies}
    grades_by_method_market: Dict[Tuple[str, str], list] = defaultdict(list)

    skipped_new_no_sim = 0
    for r in records:
        for method in methodologies:
            mean = r[f"{method}_mean"]
            std = r[f"{method}_std"]
            if mean is None or std is None:
                if method == "new":
                    skipped_new_no_sim += 1
                continue
            grade = grade_prop_bet(
                model_mean=float(mean), model_std=float(std), line=float(r["line"]), actual=float(r["actual"]),
                market_over_price=r["over_price"], market_under_price=r["under_price"],
            )
            grades_by_method[method].append(grade)
            grades_by_method_market[(method, r["market_key"])].append(grade)

    summary = {
        "n_games": len(sample_games),
        "n_records": len(records),
        "n_new_skipped_no_sim": skipped_new_no_sim,
        "by_method": {m: summarize_grades(grades_by_method[m]) for m in methodologies},
        "by_method_market": {f"{m}__{mk}": summarize_grades(g) for (m, mk), g in grades_by_method_market.items()},
    }

    with open(OUTPUT_DIR / "benchmark_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
