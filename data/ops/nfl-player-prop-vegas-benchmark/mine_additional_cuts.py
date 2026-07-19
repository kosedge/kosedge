"""Grown-sample follow-up analysis (2026-07-19, batch-2 growth task).

Answers two things `compute_benchmark.py`/`compute_roi_and_significance.py`
don't, using the SAME already-graded `raw_prop_records.json` (now the
COMBINED batch-1 + batch-2 sample, 156 real games / 2,850 real bets) --
no new API/DB writes, read-only.

1. **The pre-specified confirmatory test**: does the `new`-method
   receiving-yards high-conviction win rate found in batch 1 (53.6%,
   n=168) hold up on batch 2 -- 78 REAL games never used to generate that
   hypothesis, a genuine held-out replication, not just a bigger pooled
   sample.

2. **Exploratory mining for other promising cuts** (position, home/away,
   favorite/underdog, game-total context, alternate conviction
   thresholds) -- done ONLY on the batch-1 (`EXPLORATION`) games, exactly
   like the original discovery was. Any cut that looks promising in
   EXPLORATION is then checked ONCE against batch-2 (`HOLDOUT`) -- the
   same discipline as #1 -- rather than being reported as "found" purely
   from a pooled/combined number, which would silently launder a
   multiple-comparisons-inflated result into looking like real out-of-
   sample confirmation.

Batch membership for each (season, week, team, opponent) record is
recovered from the two pull run logs (`pull_run_log.json` = batch 1,
`pull_run_log_batch2.json` = batch 2) via `game_id`. Favorite/underdog and
total-line context come from `nfl_dp_schedules` (real spread_line/
total_line columns, joined by season/week/home/away).

Usage: /Users/ryankos/kosedge/.venv/bin/python3 mine_additional_cuts.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import psycopg

MODEL_SERVICE_SRC = "/Users/ryankos/kosedge/services/model-service"
sys.path.insert(0, MODEL_SERVICE_SRC)

from src.services.nfl_player_prop_backtest_scoring import grade_prop_bet, summarize_grades  # noqa: E402

DATABASE_URL = "postgresql://ryankos:postgres@127.0.0.1:5432/kosedge"
OUTPUT_DIR = Path(__file__).parent


def wilson_ci(wins: int, n: int, z: float = 1.96) -> Optional[Dict[str, Any]]:
    if n == 0:
        return None
    p = wins / n
    denom = 1.0 + (z * z) / n
    center = (p + (z * z) / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p) / n) + (z * z) / (4 * n * n))) / denom
    return {"n": n, "wins": wins, "point": round(p, 4), "low": round(max(0.0, center - half), 4), "high": round(min(1.0, center + half), 4)}


def win_rate_ci_for_grades(grades: Sequence) -> Optional[Dict[str, Any]]:
    decided = [g for g in grades if g.outcome in ("win", "loss")]
    if not decided:
        return None
    wins = sum(1 for g in decided if g.outcome == "win")
    return wilson_ci(wins, len(decided))


def load_batch_game_ids(run_log_path: Path) -> set:
    log = json.loads(run_log_path.read_text())
    return {g["game_id"] for g in log.get("games_pulled", [])}


def load_game_context(conn: psycopg.Connection) -> Dict[Tuple[int, int, str, str], Dict[str, Any]]:
    """(season, week, team_a, team_b) [both orders] -> {game_id, home_team,
    away_team, spread_line, total_line}. spread_line follows nflverse
    convention: home team's own spread (negative = home favored)."""
    rows = conn.execute(
        """
        SELECT season, week, game_id, home_team, away_team, spread_line, total_line
        FROM nfl_dp_schedules
        WHERE season = ANY(%(seasons)s) AND week BETWEEN 4 AND 17
        """,
        {"seasons": [2023, 2024, 2025]},
    ).fetchall()
    out: Dict[Tuple[int, int, str, str], Dict[str, Any]] = {}
    for season, week, game_id, home, away, spread, total in rows:
        rec = {
            "game_id": game_id,
            "home_team": home,
            "away_team": away,
            "spread_line": float(spread) if spread is not None else None,
            "total_line": float(total) if total is not None else None,
        }
        out[(int(season), int(week), home, away)] = rec
        out[(int(season), int(week), away, home)] = rec
    return out


def enrich_records(records: List[Dict[str, Any]], game_ctx, batch1_ids: set, batch2_ids: set) -> List[Dict[str, Any]]:
    out = []
    n_no_ctx = 0
    for r in records:
        key = (int(r["season"]), int(r["week"]), r["team"], r["opponent"])
        ctx = game_ctx.get(key)
        if ctx is None:
            n_no_ctx += 1
            batch = None
            is_home = None
            team_spread = None
            total_line = None
        else:
            gid = ctx["game_id"]
            batch = 1 if gid in batch1_ids else (2 if gid in batch2_ids else None)
            is_home = r["team"] == ctx["home_team"]
            total_line = ctx["total_line"]
            if ctx["spread_line"] is not None:
                team_spread = ctx["spread_line"] if is_home else -ctx["spread_line"]
            else:
                team_spread = None
        rr = dict(r)
        rr["batch"] = batch
        rr["is_home"] = is_home
        rr["team_spread"] = team_spread  # negative = this player's team favored
        rr["total_line"] = total_line
        out.append(rr)
    if n_no_ctx:
        print(f"[warn] {n_no_ctx} records had no matching schedule context (spread/total/batch unknown)")
    return out


def grade(records: List[Dict[str, Any]], method: str, high_conviction_z: float = 0.5):
    grades = []
    for r in records:
        mean, std = r.get(f"{method}_mean"), r.get(f"{method}_std")
        if mean is None or std is None:
            continue
        grades.append(
            grade_prop_bet(
                model_mean=float(mean), model_std=float(std), line=float(r["line"]), actual=float(r["actual"]),
                market_over_price=r["over_price"], market_under_price=r["under_price"], high_conviction_z=high_conviction_z,
            )
        )
    return grades


def high_conviction_win_rate(records: List[Dict[str, Any]], method: str, high_conviction_z: float = 0.5) -> Optional[Dict[str, Any]]:
    grades = grade(records, method, high_conviction_z)
    high = [g for g in grades if g.conviction == "high"]
    return win_rate_ci_for_grades(high)


def low_conviction_win_rate(records: List[Dict[str, Any]], method: str, high_conviction_z: float = 0.5) -> Optional[Dict[str, Any]]:
    grades = grade(records, method, high_conviction_z)
    low = [g for g in grades if g.conviction == "low"]
    return win_rate_ci_for_grades(low)


def cut_report(name: str, records: List[Dict[str, Any]], method: str = "new", high_conviction_z: float = 0.5) -> Dict[str, Any]:
    return {
        "cut": name,
        "n_records": len(records),
        "high_conviction": high_conviction_win_rate(records, method, high_conviction_z),
        "low_conviction": low_conviction_win_rate(records, method, high_conviction_z),
    }


def main() -> None:
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    records_all = json.loads((OUTPUT_DIR / "raw_prop_records.json").read_text())
    batch1_ids = load_batch_game_ids(OUTPUT_DIR / "pull_run_log.json")
    batch2_ids = load_batch_game_ids(OUTPUT_DIR / "pull_run_log_batch2.json")
    game_ctx = load_game_context(conn)
    records = enrich_records(records_all, game_ctx, batch1_ids, batch2_ids)

    batch1 = [r for r in records if r["batch"] == 1]
    batch2 = [r for r in records if r["batch"] == 2]
    print(f"Total records: {len(records)}  batch1: {len(batch1)}  batch2: {len(batch2)}  unmatched: {sum(1 for r in records if r['batch'] is None)}")

    rec_yds_all = [r for r in records if r["stat"] == "receiving_yards"]
    rec_yds_b1 = [r for r in batch1 if r["stat"] == "receiving_yards"]
    rec_yds_b2 = [r for r in batch2 if r["stat"] == "receiving_yards"]

    report: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # 1. PRIMARY CONFIRMATORY TEST: new/receiving_yards high-conviction,
    #    z=0.5 (the exact cut flagged in the 2026-07-19 addendum),
    #    reported separately for batch1 (original discovery sample),
    #    batch2 (fresh holdout), and combined.
    # ------------------------------------------------------------------
    report["primary_confirmatory_test"] = {
        "description": "new-method receiving_yards high-conviction (z=0.5) win rate: batch1 (original discovery sample, n=168 in prior report) vs batch2 (fresh 78-game holdout never used to generate this hypothesis) vs combined.",
        "batch1_only": cut_report("batch1_only", rec_yds_b1),
        "batch2_holdout": cut_report("batch2_holdout", rec_yds_b2),
        "combined": cut_report("combined", rec_yds_all),
    }

    # ------------------------------------------------------------------
    # 2. EXPLORATORY MINING -- done ONLY on batch1 (EXPLORATION set).
    #    Enumerate every cut tested (multiple-comparisons transparency).
    # ------------------------------------------------------------------
    exploration_cuts: Dict[str, Any] = {}

    # Position split (rec_yds: WR vs TE vs RB)
    for pos in ("WR", "TE", "RB"):
        subset = [r for r in rec_yds_b1 if r["position"] == pos]
        exploration_cuts[f"position_{pos}"] = cut_report(f"position_{pos}", subset)

    # Home vs away
    for label, flag in (("home", True), ("away", False)):
        subset = [r for r in rec_yds_b1 if r["is_home"] == flag]
        exploration_cuts[f"home_away_{label}"] = cut_report(f"home_away_{label}", subset)

    # Favorite vs underdog (team's own spread; negative = favored)
    fav = [r for r in rec_yds_b1 if r["team_spread"] is not None and r["team_spread"] < 0]
    dog = [r for r in rec_yds_b1 if r["team_spread"] is not None and r["team_spread"] > 0]
    exploration_cuts["favorite"] = cut_report("favorite", fav)
    exploration_cuts["underdog"] = cut_report("underdog", dog)

    # Game total median split
    totals = sorted(r["total_line"] for r in rec_yds_b1 if r["total_line"] is not None)
    median_total = totals[len(totals) // 2] if totals else None
    if median_total is not None:
        high_total = [r for r in rec_yds_b1 if r["total_line"] is not None and r["total_line"] >= median_total]
        low_total = [r for r in rec_yds_b1 if r["total_line"] is not None and r["total_line"] < median_total]
        exploration_cuts["high_total"] = cut_report("high_total", high_total)
        exploration_cuts["low_total"] = cut_report("low_total", low_total)
        exploration_cuts["_median_total_line"] = median_total

    # Alternate conviction thresholds on rec_yds (0.35, 0.75, 1.0 std, vs the baseline 0.5)
    for z in (0.35, 0.75, 1.0):
        exploration_cuts[f"alt_threshold_z{z}"] = cut_report(f"alt_threshold_z{z}", rec_yds_b1, high_conviction_z=z)

    report["exploration_batch1_cuts"] = exploration_cuts
    report["n_exploratory_cuts_tested"] = len([k for k in exploration_cuts if not k.startswith("_")])

    # ------------------------------------------------------------------
    # 3. HOLDOUT VALIDATION on batch2 for any exploration cut whose
    #    high-conviction point estimate beat both breakeven (52.4%) AND
    #    its own low-conviction win rate in EXPLORATION -- the same two-
    #    part bar the original discovery had to clear.
    # ------------------------------------------------------------------
    BREAKEVEN = 110.0 / 210.0
    promising_labels = []
    for label, res in exploration_cuts.items():
        if label.startswith("_"):
            continue
        hc = res.get("high_conviction")
        lc = res.get("low_conviction")
        if hc and hc["n"] >= 20 and hc["point"] > BREAKEVEN and (lc is None or hc["point"] > lc["point"]):
            promising_labels.append(label)

    holdout_validation: Dict[str, Any] = {}
    for label in promising_labels:
        if label.startswith("position_"):
            pos = label.split("_", 1)[1]
            subset = [r for r in rec_yds_b2 if r["position"] == pos]
            holdout_validation[label] = cut_report(label, subset)
        elif label == "home_away_home":
            subset = [r for r in rec_yds_b2 if r["is_home"] is True]
            holdout_validation[label] = cut_report(label, subset)
        elif label == "home_away_away":
            subset = [r for r in rec_yds_b2 if r["is_home"] is False]
            holdout_validation[label] = cut_report(label, subset)
        elif label == "favorite":
            subset = [r for r in rec_yds_b2 if r["team_spread"] is not None and r["team_spread"] < 0]
            holdout_validation[label] = cut_report(label, subset)
        elif label == "underdog":
            subset = [r for r in rec_yds_b2 if r["team_spread"] is not None and r["team_spread"] > 0]
            holdout_validation[label] = cut_report(label, subset)
        elif label == "high_total":
            subset = [r for r in rec_yds_b2 if r["total_line"] is not None and r["total_line"] >= median_total]
            holdout_validation[label] = cut_report(label, subset)
        elif label == "low_total":
            subset = [r for r in rec_yds_b2 if r["total_line"] is not None and r["total_line"] < median_total]
            holdout_validation[label] = cut_report(label, subset)
        elif label.startswith("alt_threshold_z"):
            z = float(label.replace("alt_threshold_z", ""))
            holdout_validation[label] = cut_report(label, rec_yds_b2, high_conviction_z=z)

    report["promising_exploration_labels"] = promising_labels
    report["holdout_validation_batch2"] = holdout_validation
    report["breakeven_win_rate"] = round(BREAKEVEN, 4)

    (OUTPUT_DIR / "mine_additional_cuts_report.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
