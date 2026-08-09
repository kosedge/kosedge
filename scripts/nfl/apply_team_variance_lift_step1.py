#!/usr/bin/env python3
"""Step 1 — widen team offensive variance on the locked v1.20 defense board.

- Asymmetric rush stretch → ~64k league rush pool (pass + ARI/BAL/SEA frozen)
- Rebuild PF from offense; PF residual stretch + light PA re-stretch
- Pythagorean wins renormed to 272
- Publishes a new preseason bundle + ops note
- Does NOT lock the pre-season snapshot; Step 2/3 not started
"""

from __future__ import annotations

import csv
import json
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
import sys

sys.path.insert(0, str(ROOT / "services" / "data-platform-nfl" / "src"))

from data_platform_nfl.defensive_production_stack import (  # noqa: E402
    TARGET_LEAGUE_PF,
    apply_defensive_production_stack,
    budgets_to_rows,
    smoke_defensive_stack,
)
from data_platform_nfl.offensive_production_stack import (  # noqa: E402
    LOCKED_PASS_SCHEME_TEAMS,
    apply_offensive_variance_lift,
    locked_team_pass_yards,
    smoke_offensive_stack,
)

BASE_BUNDLE = ROOT / "data/ops/nfl-preseason-sim-2026-20260809T120227Z"
ENGINE = "nfl-season-engine-v1.21-team-variance-lift"


class _Game:
    def __init__(self, home: str, away: str):
        self.home_team = home
        self.away_team = away


def _circle_schedule(teams: List[str]) -> List[_Game]:
    """272-game round-robin proxy (17 games/team) when real schedule unavailable."""
    ts = list(teams)
    n = len(ts)
    schedule: List[_Game] = []
    for _ in range(n - 1):
        for i in range(n // 2):
            schedule.append(_Game(ts[i], ts[n - 1 - i]))
        ts = [ts[0]] + [ts[-1]] + ts[1:-1]
    return schedule[:272]


def _load_players(path: Path) -> List[Dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        return [dict(r) for r in csv.DictReader(f)]


def _write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_bundle = ROOT / f"data/ops/nfl-preseason-sim-2026-{stamp}"
    research = ROOT / (
        f"data/ops/nfl-season-engine-launch-{ENGINE}-Nteam50000-Nplayer1000-{stamp}"
    )
    ops_note = ROOT / f"data/ops/nfl-team-variance-lift-step1-{stamp[:8]}.md"

    before_players = _load_players(BASE_BUNDLE / "player_regular_season_totals.csv")
    before_defense = list(
        csv.DictReader((BASE_BUNDLE / "team_defense_season_totals.csv").open())
    )
    before_outcomes = list(
        csv.DictReader((BASE_BUNDLE / "team_regular_season_outcomes.csv").open())
    )

    before_pass = locked_team_pass_yards(before_players)
    before_rush: Dict[str, float] = defaultdict(float)
    before_rec: Dict[str, float] = defaultdict(float)
    for r in before_players:
        t = str(r.get("team") or "")
        before_rush[t] += float(r.get("rush_yards_total") or 0)
        before_rec[t] += float(r.get("receiving_yards_total") or 0)
    before_wins = [float(r["expected_wins"]) for r in before_outcomes]
    before_pf = [float(r["points_for"]) for r in before_outcomes]

    # --- Step 1 offense lift (pass locked) ---
    players, team_rush, off_audit = apply_offensive_variance_lift(before_players)
    after_pass = locked_team_pass_yards(players)
    for t in LOCKED_PASS_SCHEME_TEAMS:
        assert abs(after_pass[t] - before_pass[t]) < 0.05, (t, after_pass[t], before_pass[t])
    assert abs(sum(after_pass.values()) - sum(before_pass.values())) < 0.5

    off_smoke = smoke_offensive_stack(players)

    # --- Rebuild PF/PA/wins on lifted offense, keep prior PA baseline then light re-stretch ---
    teams = sorted(after_pass.keys())
    prior_pa = {r["team"]: float(r["points_against"]) for r in before_defense}
    prior_sacks = {r["team"]: float(r["sacks"]) for r in before_defense}
    prior_ints = {r["team"]: float(r["ints_forced"]) for r in before_defense}
    # Neutral strength ladders — prior PA already carries the v1.20 defense shape.
    defense_index = {t: 1.0 for t in teams}
    offense_index = {t: 1.0 for t in teams}
    schedule = _circle_schedule(teams)

    budgets, def_audit = apply_defensive_production_stack(
        players,
        schedule=schedule,
        defense_index=defense_index,
        offense_index=offense_index,
        variance_lift=False,
        offense_pf_variance_lift=True,
        prior_points_against=prior_pa,
        prior_sacks=prior_sacks,
        prior_ints_forced=prior_ints,
    )
    def_smoke = smoke_defensive_stack(budgets, players)
    outcome_rows = budgets_to_rows(budgets, prior_outcomes=before_outcomes)
    # Preserve sim_expected_wins from the pre-lift board for comparison.
    prior_by = {r["team"]: r for r in before_outcomes}
    for row in outcome_rows:
        prev = prior_by.get(row["team"]) or {}
        if prev.get("expected_wins") is not None:
            row["sim_expected_wins"] = round(float(prev["expected_wins"]), 4)

    defense_rows = [
        {
            "season": 2026,
            "team": b.team,
            "points_for": round(b.points_for, 2),
            "points_against": round(b.points_against, 2),
            "point_diff": round(b.point_diff, 2),
            "expected_wins": round(b.expected_wins, 4),
            "pass_yards_allowed": round(b.pass_yards_allowed, 1),
            "rush_yards_allowed": round(b.rush_yards_allowed, 1),
            "ints_forced": round(b.ints_forced, 2),
            "sacks": round(b.sacks, 2),
            "takeaways": round(b.takeaways, 2),
            "ppg": round(b.points_for / 17.0, 3),
            "pa_pg": round(b.points_against / 17.0, 3),
        }
        for b in sorted(budgets.values(), key=lambda x: -x.expected_wins)
    ]

    after_wins = [b.expected_wins for b in budgets.values()]
    after_pf = [b.points_for for b in budgets.values()]
    after_pa = [b.points_against for b in budgets.values()]
    after_rec = defaultdict(float)
    for r in players:
        after_rec[str(r.get("team") or "")] += float(r.get("receiving_yards_total") or 0)

    gates = {
        "league_pf_pa_11859": abs(sum(after_pf) - TARGET_LEAGUE_PF) < 1.0
        and abs(sum(after_pa) - TARGET_LEAGUE_PF) < 1.0
        and abs(sum(after_pf) - sum(after_pa)) <= 1.0,
        "wins_sum_272": abs(sum(after_wins) - 272.0) <= 0.05,
        "win_range_ge_7_5": (max(after_wins) - min(after_wins)) >= 7.5,
        "top_rush_supports_1450": max(team_rush.values()) * 0.60 >= 1450.0,
        "top_rec_supports_1500": max(after_pass.values()) * 0.38 >= 1500.0,
        "pass_pool_locked": abs(sum(after_pass.values()) - 126_000.0) < 50.0,
        "ari_bal_sea_pass_untouched": all(
            abs(after_pass[t] - before_pass[t]) < 0.05 for t in LOCKED_PASS_SCHEME_TEAMS
        ),
        "sacks_1150": abs(sum(b.sacks for b in budgets.values()) - 1150.0) < 1.0,
        "ints_350": abs(sum(b.ints_forced for b in budgets.values()) - 350.3) < 1.0,
        "offense_smoke": bool(off_smoke.get("all_pass")),
        "defense_smoke": bool(def_smoke.get("all_pass")),
    }

    # --- Write bundle ---
    out_bundle.mkdir(parents=True, exist_ok=True)
    research.mkdir(parents=True, exist_ok=True)

    player_fields = list(before_players[0].keys())
    for r in players:
        r.setdefault("season", 2026)
    _write_csv(out_bundle / "player_regular_season_totals.csv", players, player_fields)
    # Empty playoff stub (same as prior publish pattern).
    (out_bundle / "player_playoff_totals.csv").write_text(
        "season,player_key,player_name,team,position\n", encoding="utf-8"
    )
    _write_csv(
        out_bundle / "team_regular_season_outcomes.csv",
        outcome_rows,
        list(outcome_rows[0].keys()),
    )
    _write_csv(
        out_bundle / "team_defense_season_totals.csv",
        defense_rows,
        list(defense_rows[0].keys()),
    )

    # Carry forward sim artifacts that Step 1 does not regenerate.
    for name in (
        "team_week_win_rates.json",
        "team_win_distributions.json",
        "survivor_week1_evaluate.json",
    ):
        src = BASE_BUNDLE / name
        if src.exists():
            shutil.copy2(src, out_bundle / name)

    generated = datetime.now(timezone.utc).isoformat()
    run_summary = {
        "engine_version": ENGINE,
        "generated_at_utc": generated,
        "n_team_sims": 50000,
        "n_player_sims": 1000,
        "step": 1,
        "method": "offense_variance_lift_v1 + offense_pf_variance_lift_v1",
        "base_bundle": BASE_BUNDLE.name,
        "offense_audit": off_audit,
        "defense_audit": {
            "league_pf": def_audit.get("league_pf"),
            "league_pa": def_audit.get("league_pa"),
            "wins_sum": def_audit.get("wins_sum"),
            "offense_pf_variance_lift": def_audit.get("offense_pf_variance_lift"),
        },
        "gates": gates,
        "before": {
            "wins_min": round(min(before_wins), 4),
            "wins_max": round(max(before_wins), 4),
            "wins_range": round(max(before_wins) - min(before_wins), 4),
            "wins_sum": round(sum(before_wins), 4),
            "rush_pool": round(sum(before_rush.values()), 1),
            "pf_range": round(max(before_pf) - min(before_pf), 2),
        },
        "after": {
            "wins_min": round(min(after_wins), 4),
            "wins_max": round(max(after_wins), 4),
            "wins_range": round(max(after_wins) - min(after_wins), 4),
            "wins_sum": round(sum(after_wins), 4),
            "rush_pool": round(sum(team_rush.values()), 1),
            "pf_range": round(max(after_pf) - min(after_pf), 2),
            "pa_range": round(max(after_pa) - min(after_pa), 2),
        },
        "note": "Step 1 only — snapshot NOT locked; Step 2 (alpha usage) NOT started",
    }
    (out_bundle / "run_summary.json").write_text(
        json.dumps(run_summary, indent=2) + "\n", encoding="utf-8"
    )
    (out_bundle / "quality_checks.json").write_text(
        json.dumps(
            {
                "gates": gates,
                "offense_smoke": off_smoke,
                "defense_smoke": def_smoke,
                "all_step1_pass": all(gates.values()),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    shutil.copy2(out_bundle / "run_summary.json", research / "run_summary.json")

    # Pointers (do not lock snapshot).
    (ROOT / "data/ops/nfl-launch-research-sims-current.md").write_text(
        "\n".join(
            [
                "# NFL launch research sims — current pointer",
                "",
                f"- **Web bundle:** `{out_bundle.name}`",
                f"- **Source research:** `{research.relative_to(ROOT)}`",
                f"- **Engine:** `{ENGINE}`",
                "- **Team W/L N:** 50000",
                "- **Player full N:** 1000",
                f"- **Generated:** {generated}",
                f"- **Identity:** {ENGINE} · N_team=50000 · {stamp}",
                "- **Note:** Step 1 team offensive variance lift — snapshot NOT locked",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (ROOT / "data/ops/nfl-web-launch-bundle.json").write_text(
        json.dumps(
            {
                "bundle_id": out_bundle.name,
                "engine_version": ENGINE,
                "n_team_sims": 50000,
                "n_player_sims": 1000,
                "generated_at_utc": generated,
                "source_dir": str(research.relative_to(ROOT)),
                "preseason": True,
                "identity": f"{ENGINE} · N_team=50000 · {stamp}",
                "note": "Step 1 team offensive variance lift; pass pool locked; snapshot NOT locked",
                "locked_snapshot": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    top_rush_before = sorted(before_rush.items(), key=lambda kv: -kv[1])[:5]
    top_rush_after = sorted(team_rush.items(), key=lambda kv: -kv[1])[:5]
    top_rec_before = sorted(before_rec.items(), key=lambda kv: -kv[1])[:5]
    top_rec_after = sorted(after_rec.items(), key=lambda kv: -kv[1])[:5]
    top_wins = sorted(budgets.values(), key=lambda b: -b.expected_wins)[:5]
    bot_wins = sorted(budgets.values(), key=lambda b: b.expected_wins)[:5]

    gate_table = "\n".join(
        f"| {k} | {'**PASS**' if v else '**FAIL**'} |" for k, v in gates.items()
    )
    ops_note.write_text(
        f"""# NFL Team Variance Lift — Step 1 Smoke

Date: {stamp[:8]}  
Engine: `{ENGINE}`  
Base: v1.20 defense board (`{BASE_BUNDLE.name}`)  
Web pointer: `{out_bundle.name}`  
**Snapshot NOT locked. Step 2 NOT started.**

## Before → After

| Metric | Before | After |
|--------|-------:|------:|
| Wins min / max | {min(before_wins):.2f} / {max(before_wins):.2f} | {min(after_wins):.2f} / {max(after_wins):.2f} |
| Wins range | {max(before_wins)-min(before_wins):.2f} | {max(after_wins)-min(after_wins):.2f} |
| Wins Σ | {sum(before_wins):.2f} | {sum(after_wins):.2f} |
| League rush yards | {sum(before_rush.values()):.0f} | {sum(team_rush.values()):.0f} |
| PF range | {max(before_pf)-min(before_pf):.1f} | {max(after_pf)-min(after_pf):.1f} |
| League PF / PA | 11859.2 / 11859.2 | {sum(after_pf):.1f} / {sum(after_pa):.1f} |
| Pass pool | {sum(before_pass.values()):.1f} | {sum(after_pass.values()):.1f} |

### Top rush teams
- Before: {[(t, round(v)) for t, v in top_rush_before]}
- After: {[(t, round(v)) for t, v in top_rush_after]} (RB@60% ≈ {max(team_rush.values())*0.6:.0f})

### Top receiving teams (≈ locked pass)
- Before: {[(t, round(v)) for t, v in top_rec_before]}
- After: {[(t, round(v)) for t, v in top_rec_after]} (WR@38% ≈ {max(after_pass.values())*0.38:.0f})

### ARI / BAL / SEA pass (untouched)
{ {t: round(after_pass[t], 1) for t in LOCKED_PASS_SCHEME_TEAMS} }

### Wins leaders / trailers
- Top: {[(b.team, round(b.expected_wins, 2)) for b in top_wins]}
- Bot: {[(b.team, round(b.expected_wins, 2)) for b in bot_wins]}

## Smoke gates

| Check | Result |
|-------|--------|
{gate_table}
| **ALL Step 1** | {'**PASS**' if all(gates.values()) else '**FAIL**'} |

## Method
1. Asymmetric rush stretch (pos 1.40× / neg 0.55× about mean, soft 1280–2520) → 64k pool
2. Player rush yards/TDs scaled within team; pass/receiving frozen
3. PF rebuilt from offense → PF residual stretch (0.70) + light PA re-stretch (0.35)
4. Sacks 1150 / INTs ~350 lightly re-stretched with PA; Pythagorean wins → Σ 272

## Conservation
- Pass pool locked (~126k); ARI/BAL/SEA weights unchanged
- League PF = PA = {sum(after_pf):.1f}
- Sacks = {sum(b.sacks for b in budgets.values()):.1f}; INTs = {sum(b.ints_forced for b in budgets.values()):.2f}
""",
        encoding="utf-8",
    )

    print(json.dumps({"bundle": out_bundle.name, "ops_note": ops_note.name, "gates": gates}, indent=2))
    if not all(gates.values()):
        failed = [k for k, v in gates.items() if not v]
        print("FAILED GATES:", failed, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
