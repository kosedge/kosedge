#!/usr/bin/env python3
"""Enterprise soft-flag fixes on the Step 1+2 / Step-3 review board (NOT locked).

Order:
1. High-volume pass → TD/PF scoring-efficiency floors (CIN + peers)
2. Soft differentiated RB alpha priors (no flat 1432 pile)
3. Tapered PF/PA stretch + renorm (replace hard clips)
4. QB depth-label hygiene from packaged depth SoT (Kyler MIN / Brissett ARI)
5. Rebuild Pythagorean wins; write bundle + ops note

Does NOT lock the snapshot.
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "data-platform-nfl" / "src"))

from data_platform_nfl.defensive_production_stack import (  # noqa: E402
    TARGET_LEAGUE_PF,
    apply_defensive_production_stack,
    budgets_to_rows,
    smoke_defensive_stack,
)
from data_platform_nfl.offensive_production_stack import (  # noqa: E402
    LOCKED_PASS_SCHEME_TEAMS,
    enforce_high_volume_pass_tds_on_rows,
    locked_team_pass_yards,
    repair_qb_team_labels,
    smoke_offensive_stack,
)
from data_platform_nfl.role_aware_production import (  # noqa: E402
    apply_role_aware_player_shape,
)

BASE_BUNDLE = ROOT / "data/ops/nfl-preseason-sim-2026-20260809T144255Z"
ENGINE = "nfl-season-engine-v1.23-soft-flags-enterprise"


class _Game:
    def __init__(self, home: str, away: str):
        self.home_team = home
        self.away_team = away


def _circle_schedule(teams: List[str]) -> List[_Game]:
    ts = list(teams)
    n = len(ts)
    schedule: List[_Game] = []
    for _ in range(n - 1):
        for i in range(n // 2):
            schedule.append(_Game(ts[i], ts[n - 1 - i]))
        ts = [ts[0]] + [ts[-1]] + ts[1:-1]
    return schedule[:272]


def _load_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        return [dict(r) for r in csv.DictReader(f)]


def _write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _f(row: Dict[str, Any], *keys: str) -> float:
    for k in keys:
        if k in row and row[k] not in (None, ""):
            try:
                return float(row[k])
            except (TypeError, ValueError):
                continue
    return 0.0


def main() -> int:
    if not BASE_BUNDLE.exists():
        print(f"Missing base bundle: {BASE_BUNDLE}", file=sys.stderr)
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    day = stamp[:8]
    out_bundle = ROOT / f"data/ops/nfl-preseason-sim-2026-{stamp}"
    research = ROOT / (
        f"data/ops/nfl-season-engine-launch-{ENGINE}-Nteam50000-Nplayer1000-{stamp}"
    )
    ops_note = ROOT / f"data/ops/nfl-soft-flags-enterprise-fix-{day}.md"

    before_players = _load_csv(BASE_BUNDLE / "player_regular_season_totals.csv")
    before_outcomes = _load_csv(BASE_BUNDLE / "team_regular_season_outcomes.csv")
    before_defense = _load_csv(BASE_BUNDLE / "team_defense_season_totals.csv")

    before_pass = locked_team_pass_yards(before_players)
    before_rush = defaultdict(float)
    for r in before_players:
        before_rush[str(r.get("team") or "")] += _f(r, "rush_yards_total")

    # --- 4 (early for hygiene): label repair (identity only; pools untouched) ---
    players, label_audit = repair_qb_team_labels(before_players)

    # --- 1: high-volume pass TD efficiency floors ---
    players, td_audit = enforce_high_volume_pass_tds_on_rows(players)

    # --- 2: role-aware RB/WR/QB shape (conserves team + league rush) ---
    players, rb_audit = apply_role_aware_player_shape(players)

    after_pass = locked_team_pass_yards(players)
    after_rush = defaultdict(float)
    for r in players:
        after_rush[str(r.get("team") or "")] += _f(r, "rush_yards_total")

    for t in LOCKED_PASS_SCHEME_TEAMS:
        assert abs(after_pass[t] - before_pass[t]) < 0.05, (t, after_pass[t], before_pass[t])
    assert abs(sum(after_pass.values()) - sum(before_pass.values())) < 0.5
    assert abs(sum(after_rush.values()) - 64_000.0) < 1.0

    off_smoke = smoke_offensive_stack(players)

    # --- 3: tapered PF/PA stretch + volume PF floors + Pythagorean ---
    teams = sorted(after_pass.keys())
    prior_pa = {r["team"]: float(r["points_against"]) for r in before_defense}
    prior_sacks = {r["team"]: float(r["sacks"]) for r in before_defense}
    prior_ints = {r["team"]: float(r["ints_forced"]) for r in before_defense}
    defense_index = {t: 1.0 for t in teams}
    offense_index = {t: 1.0 for t in teams}
    schedule = _circle_schedule(teams)

    # Schedule PA blended with prior PA inside the stack (defense memory without
    # inheriting hard-clipped PA piles). Keep sack/INT league shape.
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

    cin = budgets["CIN"]
    burrow = next(
        (r for r in players if "Burrow" in str(r.get("player_name") or "")),
        None,
    )
    rbs = sorted(
        [r for r in players if str(r.get("position") or "").upper() == "RB"],
        key=lambda r: -_f(r, "rush_yards_total"),
    )
    top_rb_yards = [_f(r, "rush_yards_total") for r in rbs[:15]]
    rb_unique = len({round(y, 0) for y in top_rb_yards[:12]})

    # Clustering diagnostics
    from collections import Counter

    win_round = Counter(round(w, 2) for w in after_wins)
    pf_round = Counter(round(p, 1) for p in after_pf)
    max_win_tie = max(win_round.values()) if win_round else 0
    max_pf_tie = max(pf_round.values()) if pf_round else 0
    # Cluster = values within 0.15 PF of each other (catches 289.8/289.9 piles).
    def _max_cluster(vals: List[float], width: float) -> int:
        xs = sorted(vals)
        best = 1
        j = 0
        for i in range(len(xs)):
            while xs[i] - xs[j] > width:
                j += 1
            best = max(best, i - j + 1)
        return best

    max_pf_cluster = _max_cluster(after_pf, 0.25)

    gates = {
        "league_pf_pa_11859": abs(sum(after_pf) - TARGET_LEAGUE_PF) < 1.0
        and abs(sum(after_pa) - TARGET_LEAGUE_PF) < 1.0
        and abs(sum(after_pf) - sum(after_pa)) <= 1.0,
        "wins_sum_272": abs(sum(after_wins) - 272.0) <= 0.05,
        "win_range_ge_7_5": (max(after_wins) - min(after_wins)) >= 7.5,
        "pass_pool_locked": abs(sum(after_pass.values()) - 126_000.0) < 50.0,
        "rush_pool_64000": abs(sum(after_rush.values()) - 64_000.0) < 1.0,
        "ari_bal_sea_pass_untouched": all(
            abs(after_pass[t] - before_pass[t]) < 0.05 for t in LOCKED_PASS_SCHEME_TEAMS
        ),
        "cin_not_bottom_tier": cin.expected_wins >= 8.0 and cin.points_for >= 340.0,
        "cin_wins_band_9_12": 9.0 <= cin.expected_wins <= 11.5,
        "rb_top12_differentiated": rb_unique >= 6,
        "top_rb_ge_1400": max(top_rb_yards) >= 1400.0,
        # Reject the old 11–18 team PF piles; allow modest renorm ties.
        "pf_cluster_lt_12": max_pf_cluster < 12,
        # Old board had 11 teams pinned at the same win total; allow small ties.
        "win_ties_improved": max_win_tie <= 6,
        "offense_smoke": bool(off_smoke.get("all_pass")),
        "defense_smoke": bool(def_smoke.get("all_pass")),
        "kyler_on_min": any(
            "Kyler" in str(r.get("player_name") or "") and r.get("team") == "MIN"
            for r in players
        ),
        "kyler_not_on_ari": not any(
            "Kyler" in str(r.get("player_name") or "") and r.get("team") == "ARI"
            for r in players
        ),
    }

    out_bundle.mkdir(parents=True, exist_ok=True)
    research.mkdir(parents=True, exist_ok=True)

    player_fields = list(before_players[0].keys())
    for extra in ("snap_share", "target_share", "carry_share", "is_rookie", "draft_round"):
        if extra not in player_fields:
            player_fields.append(extra)
    for r in players:
        r.setdefault("season", 2026)
    _write_csv(out_bundle / "player_regular_season_totals.csv", players, player_fields)
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
    for name in (
        "team_week_win_rates.json",
        "team_win_distributions.json",
        "survivor_week1_evaluate.json",
    ):
        src = BASE_BUNDLE / name
        if src.exists():
            shutil.copy2(src, out_bundle / name)

    generated = datetime.now(timezone.utc).isoformat()
    top_rbs_report = [
        {
            "rank": i,
            "player": r.get("player_name"),
            "team": r.get("team"),
            "rush_yards": round(_f(r, "rush_yards_total"), 1),
            "rush_tds": round(_f(r, "rush_tds_total"), 2),
        }
        for i, r in enumerate(rbs[:12], 1)
    ]

    run_summary = {
        "engine_version": ENGINE,
        "generated_at_utc": generated,
        "n_team_sims": 50000,
        "n_player_sims": 1000,
        "step": "soft_flags_enterprise_fix",
        "base_bundle": BASE_BUNDLE.name,
        "locked_snapshot": False,
        "audits": {
            "labels": label_audit,
            "pass_tds": {
                "teams_lifted": td_audit.get("teams_lifted"),
                "lift": td_audit.get("lift"),
            },
            "rb_priors": {
                "rush_pool": rb_audit.get("rush_pool"),
                "top_rb": rb_audit.get("top_rb"),
            },
            "defense": {
                "league_pf": def_audit.get("league_pf"),
                "league_pa": def_audit.get("league_pa"),
                "wins_sum": def_audit.get("wins_sum"),
                "offense_pf_variance_lift": def_audit.get("offense_pf_variance_lift"),
            },
        },
        "cin": {
            "pass_yards": round(after_pass["CIN"], 1),
            "points_for": round(cin.points_for, 2),
            "points_against": round(cin.points_against, 2),
            "expected_wins": round(cin.expected_wins, 4),
            "burrow_pass_yards": round(_f(burrow, "pass_yards_total"), 1) if burrow else None,
            "burrow_pass_tds": round(_f(burrow, "pass_tds_total"), 2) if burrow else None,
        },
        "top_rbs": top_rbs_report,
        "wins": {
            "min": round(min(after_wins), 4),
            "max": round(max(after_wins), 4),
            "range": round(max(after_wins) - min(after_wins), 4),
            "sum": round(sum(after_wins), 4),
            "max_tie_count": max_win_tie,
        },
        "pf": {
            "min": round(min(after_pf), 2),
            "max": round(max(after_pf), 2),
            "range": round(max(after_pf) - min(after_pf), 2),
            "max_tie_count": max_pf_tie,
            "max_cluster_0_25": max_pf_cluster,
            "league": round(sum(after_pf), 2),
        },
        "gates": gates,
        "note": "Enterprise soft-flag fix — snapshot NOT LOCKED",
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
                "all_pass": all(gates.values()),
                "locked_snapshot": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    shutil.copy2(out_bundle / "run_summary.json", research / "run_summary.json")

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
                "- **Note:** Enterprise soft-flag fix — snapshot NOT locked",
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
                "note": "Enterprise soft-flag fix; snapshot NOT locked",
                "locked_snapshot": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    rb_lines = "\n".join(
        f"| {x['rank']} | {x['player']} | {x['team']} | {x['rush_yards']:.0f} | {x['rush_tds']:.1f} |"
        for x in top_rbs_report
    )
    gate_table = "\n".join(
        f"| {k} | {'**PASS**' if v else '**FAIL**'} |" for k, v in gates.items()
    )
    label_lines = "\n".join(f"- {x}" for x in (label_audit.get("fixes") or [])[:20]) or "- (none)"

    ops_note.write_text(
        f"""# NFL Soft Flags — Enterprise Fix

Date: {day}  
Engine: `{ENGINE}`  
Base: Step-3 review board (`{BASE_BUNDLE.name}`)  
Web pointer: `{out_bundle.name}`  

## Status

**NOT LOCKED**

Do not treat this as a production lock. No final-lock tag.

## CIN (critical)

| | Value |
|--|------:|
| Pass yards (locked) | {after_pass['CIN']:.1f} |
| PF | {cin.points_for:.1f} |
| PA | {cin.points_against:.1f} |
| Wins | {cin.expected_wins:.2f} |
| Burrow pass yds | {_f(burrow, 'pass_yards_total') if burrow else 0:.1f} |
| Burrow pass TDs | {_f(burrow, 'pass_tds_total') if burrow else 0:.2f} |

## Top RBs (differentiated soft priors)

| Rank | Player | Team | Rush yds | Rush TDs |
|-----:|--------|------|---------:|---------:|
{rb_lines}

## Wins / PF

| Metric | Value |
|--------|------:|
| Wins min / max / range | {min(after_wins):.2f} / {max(after_wins):.2f} / {max(after_wins)-min(after_wins):.2f} |
| Wins Σ | {sum(after_wins):.2f} |
| Max win-value tie count | {max_win_tie} |
| PF min / max / range | {min(after_pf):.1f} / {max(after_pf):.1f} / {max(after_pf)-min(after_pf):.1f} |
| League PF / PA | {sum(after_pf):.1f} / {sum(after_pa):.1f} |
| Max PF-value tie count | {max_pf_tie} |

## Conservation

| Check | Value |
|-------|------:|
| Pass pool | {sum(after_pass.values()):.1f} |
| Rush pool | {sum(after_rush.values()):.1f} |
| ARI/BAL/SEA pass | { {t: round(after_pass[t], 1) for t in LOCKED_PASS_SCHEME_TEAMS} } |

## Labeling fixes

{label_lines}

## Gates

| Check | Result |
|-------|--------|
{gate_table}
| **ALL** | {'**PASS**' if all(gates.values()) else '**FAIL**'} |

## Method
1. High-volume (≥4600 pass yds) min ~5.1% pass-TD rate + PF points-per-attempt floor (~0.50)
2. RB hard floor → soft prior (~1380) + team-rush rank / prior residual / OL proxy; rush Σ=64k
3. PF/PA stretch: tapered band penalties (no hard clips), softer intensity, renorm PF=PA≈11859, wins Σ=272
4. QB label hygiene (identity swap; team pools untouched)
5. Smoke only — **NOT LOCKED**
""",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "bundle": out_bundle.name,
                "ops_note": ops_note.name,
                "engine": ENGINE,
                "locked_snapshot": False,
                "gates": gates,
                "cin": run_summary["cin"],
                "top_rb": top_rbs_report[:8],
                "wins": run_summary["wins"],
                "label_fixes": label_audit.get("fixes"),
            },
            indent=2,
        )
    )
    if not all(gates.values()):
        print("FAILED GATES:", [k for k, v in gates.items() if not v], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
