#!/usr/bin/env python3
"""Step 2 — re-anchor player usage (alpha sticky shares) on the Step 1 board.

- Sticky 85–90% retention of 2025 elite target/carry shares (cut volume regression)
- WR/RB yard floors; TE compression when WR1 alpha present
- Team pass + rush pools locked (ARI/BAL/SEA untouched); rec≈pass ±1.5%
- Team W/L / PF/PA carried forward from Step 1 (team totals unchanged)
- Does NOT lock the pre-season snapshot; Step 3 not started
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

from data_platform_nfl.offensive_production_stack import (  # noqa: E402
    LOCKED_PASS_SCHEME_TEAMS,
    apply_alpha_usage_reanchor,
    locked_team_pass_yards,
    smoke_offensive_stack,
)

BASE_BUNDLE = ROOT / "data/ops/nfl-preseason-sim-2026-20260809T133342Z"
ENGINE = "nfl-season-engine-v1.22-alpha-usage-reanchor"
TARGET_LEAGUE_PF = 11_859.2


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


def _f(row: Dict[str, Any], key: str) -> float:
    try:
        return float(row.get(key) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_bundle = ROOT / f"data/ops/nfl-preseason-sim-2026-{stamp}"
    research = ROOT / (
        f"data/ops/nfl-season-engine-launch-{ENGINE}-Nteam50000-Nplayer1000-{stamp}"
    )
    ops_note = ROOT / f"data/ops/nfl-alpha-usage-reanchor-step2-{stamp[:8]}.md"

    before_players = _load_players(BASE_BUNDLE / "player_regular_season_totals.csv")
    before_outcomes = list(
        csv.DictReader((BASE_BUNDLE / "team_regular_season_outcomes.csv").open())
    )
    before_defense = list(
        csv.DictReader((BASE_BUNDLE / "team_defense_season_totals.csv").open())
    )

    before_pass = locked_team_pass_yards(before_players)
    before_rush: Dict[str, float] = defaultdict(float)
    before_rec_by_player = {
        str(r.get("player_name") or ""): _f(r, "receiving_yards_total")
        for r in before_players
    }
    before_rush_by_player = {
        str(r.get("player_name") or ""): _f(r, "rush_yards_total")
        for r in before_players
    }
    for r in before_players:
        before_rush[str(r.get("team") or "")] += _f(r, "rush_yards_total")

    before_wins = [_f(r, "expected_wins") for r in before_outcomes]
    before_pf = [_f(r, "points_for") for r in before_outcomes]
    before_pa = [_f(r, "points_against") for r in before_outcomes]

    # WR rank before (JSN)
    wr_before = sorted(
        [r for r in before_players if str(r.get("position") or "").upper() == "WR"],
        key=lambda r: -_f(r, "receiving_yards_total"),
    )
    jsn_before_rank = next(
        (
            i
            for i, r in enumerate(wr_before, 1)
            if "Smith-Njigba" in str(r.get("player_name") or "")
        ),
        None,
    )

    players, audit = apply_alpha_usage_reanchor(before_players)
    after_pass = locked_team_pass_yards(players)
    after_rush: Dict[str, float] = defaultdict(float)
    for r in players:
        after_rush[str(r.get("team") or "")] += _f(r, "rush_yards_total")

    off_smoke = smoke_offensive_stack(players)

    # Conservation: max team |rec-pass|/pass
    max_gap = 0.0
    for team in after_pass:
        rec = sum(
            _f(r, "receiving_yards_total")
            for r in players
            if str(r.get("team") or "") == team
            and str(r.get("position") or "").upper() in {"WR", "TE", "RB"}
        )
        gap = abs(rec - after_pass[team]) / max(after_pass[team], 1.0)
        max_gap = max(max_gap, gap)

    rush_ok = all(
        abs(after_rush[t] - before_rush[t]) < 0.5 for t in before_rush if t
    )

    wr_after = sorted(
        [r for r in players if str(r.get("position") or "").upper() == "WR"],
        key=lambda r: -_f(r, "receiving_yards_total"),
    )
    rb_after = sorted(
        [r for r in players if str(r.get("position") or "").upper() == "RB"],
        key=lambda r: -_f(r, "rush_yards_total"),
    )
    jsn_after = next(
        (r for r in wr_after if "Smith-Njigba" in str(r.get("player_name") or "")),
        None,
    )
    jsn_rank = next(
        (
            i
            for i, r in enumerate(wr_after, 1)
            if "Smith-Njigba" in str(r.get("player_name") or "")
        ),
        None,
    )

    top_wr_yards = [_f(r, "receiving_yards_total") for r in wr_after[:15]]
    top_rb_yards = [_f(r, "rush_yards_total") for r in rb_after[:15]]

    # Team W/L / PF carried forward — Step 2 does not touch team totals.
    after_wins = list(before_wins)
    after_pf = list(before_pf)
    after_pa = list(before_pa)

    gates = {
        "top_wr_multiple_1400": sum(1 for y in top_wr_yards if y >= 1400.0) >= 3,
        "top_wr_end_1550": max(top_wr_yards) >= 1550.0,
        "top_rb_1400": max(top_rb_yards) >= 1400.0,
        "jsn_top_tier": (
            jsn_after is not None
            and jsn_rank is not None
            and jsn_rank <= 12
            and _f(jsn_after, "receiving_yards_total") >= 1400.0
        ),
        "rec_pass_within_1_5pct": max_gap <= 0.015 + 1e-9,
        "rush_sum_conserved": rush_ok,
        "pass_pool_locked": abs(sum(after_pass.values()) - 126_000.0) < 50.0,
        "ari_bal_sea_pass_untouched": all(
            abs(after_pass[t] - before_pass[t]) < 0.05 for t in LOCKED_PASS_SCHEME_TEAMS
        ),
        "league_pf_pa_11859": abs(sum(after_pf) - TARGET_LEAGUE_PF) < 1.0
        and abs(sum(after_pa) - TARGET_LEAGUE_PF) < 1.0,
        "wins_sum_272": abs(sum(after_wins) - 272.0) <= 0.05,
        "win_range_ge_7_5": (max(after_wins) - min(after_wins)) >= 7.5,
        "offense_smoke": bool(off_smoke.get("all_pass")),
        "step1_gates_held": True,  # team picture unchanged by construction
    }
    gates["step1_gates_held"] = all(
        [
            gates["pass_pool_locked"],
            gates["ari_bal_sea_pass_untouched"],
            gates["league_pf_pa_11859"],
            gates["wins_sum_272"],
            gates["win_range_ge_7_5"],
        ]
    )

    out_bundle.mkdir(parents=True, exist_ok=True)
    research.mkdir(parents=True, exist_ok=True)

    # Preserve original columns + any new usage fields.
    player_fields = list(before_players[0].keys())
    for extra in ("snap_share", "target_share", "carry_share", "is_rookie", "draft_round"):
        if extra not in player_fields:
            player_fields.append(extra)
    for r in players:
        r.setdefault("season", 2026)
    _write_csv(out_bundle / "player_regular_season_totals.csv", players, player_fields)

    # Carry team / sim artifacts unchanged from Step 1 board.
    for name in (
        "player_playoff_totals.csv",
        "team_regular_season_outcomes.csv",
        "team_defense_season_totals.csv",
        "team_week_win_rates.json",
        "team_win_distributions.json",
        "survivor_week1_evaluate.json",
    ):
        src = BASE_BUNDLE / name
        if src.exists():
            shutil.copy2(src, out_bundle / name)

    generated = datetime.now(timezone.utc).isoformat()
    top_wrs_report = [
        {
            "rank": i,
            "player": r.get("player_name"),
            "team": r.get("team"),
            "rec_yards": round(_f(r, "receiving_yards_total"), 1),
            "before": round(before_rec_by_player.get(str(r.get("player_name") or ""), 0.0), 1),
        }
        for i, r in enumerate(wr_after[:12], 1)
    ]
    top_rbs_report = [
        {
            "rank": i,
            "player": r.get("player_name"),
            "team": r.get("team"),
            "rush_yards": round(_f(r, "rush_yards_total"), 1),
            "before": round(before_rush_by_player.get(str(r.get("player_name") or ""), 0.0), 1),
        }
        for i, r in enumerate(rb_after[:12], 1)
    ]

    run_summary = {
        "engine_version": ENGINE,
        "generated_at_utc": generated,
        "n_team_sims": 50000,
        "n_player_sims": 1000,
        "step": 2,
        "method": "alpha_usage_reanchor_v1",
        "base_bundle": BASE_BUNDLE.name,
        "audit": {
            "pass_pool": audit.get("pass_pool"),
            "rush_pool": audit.get("rush_pool"),
            "locked_scheme_pass": audit.get("locked_scheme_pass"),
            "sticky": {
                "alpha_players": (audit.get("sticky") or {}).get("alpha_players"),
                "retention": (audit.get("sticky") or {}).get("retention"),
            },
        },
        "gates": gates,
        "jsn": {
            "rank_before": jsn_before_rank,
            "rank_after": jsn_rank,
            "yards_before": round(before_rec_by_player.get("Jaxon Smith-Njigba", 0.0), 1),
            "yards_after": round(_f(jsn_after, "receiving_yards_total"), 1) if jsn_after else None,
        },
        "top_wrs": top_wrs_report,
        "top_rbs": top_rbs_report,
        "conservation": {
            "max_rec_pass_gap_pct": round(max_gap, 6),
            "rush_sum_ok": rush_ok,
        },
        "team_picture": {
            "wins_min": round(min(after_wins), 4),
            "wins_max": round(max(after_wins), 4),
            "wins_range": round(max(after_wins) - min(after_wins), 4),
            "wins_sum": round(sum(after_wins), 4),
            "league_pf": round(sum(after_pf), 2),
            "league_pa": round(sum(after_pa), 2),
            "note": "unchanged from Step 1 (player reallocation only)",
        },
        "note": "Step 2 only — snapshot NOT locked; Step 3 NOT started",
    }
    (out_bundle / "run_summary.json").write_text(
        json.dumps(run_summary, indent=2) + "\n", encoding="utf-8"
    )
    (out_bundle / "quality_checks.json").write_text(
        json.dumps(
            {
                "gates": gates,
                "offense_smoke": off_smoke,
                "all_step2_pass": all(gates.values()),
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
                "- **Note:** Step 2 alpha usage re-anchor — snapshot NOT locked",
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
                "note": "Step 2 alpha usage re-anchor; pass/rush pools locked; snapshot NOT locked",
                "locked_snapshot": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    gate_table = "\n".join(
        f"| {k} | {'**PASS**' if v else '**FAIL**'} |" for k, v in gates.items()
    )
    wr_lines = "\n".join(
        f"| {x['rank']} | {x['player']} | {x['team']} | {x['rec_yards']:.0f} | {x['before']:.0f} |"
        for x in top_wrs_report
    )
    rb_lines = "\n".join(
        f"| {x['rank']} | {x['player']} | {x['team']} | {x['rush_yards']:.0f} | {x['before']:.0f} |"
        for x in top_rbs_report
    )

    ops_note.write_text(
        f"""# NFL Alpha Usage Re-anchor — Step 2 Smoke

Date: {stamp[:8]}  
Engine: `{ENGINE}`  
Base: Step 1 board (`{BASE_BUNDLE.name}`)  
Web pointer: `{out_bundle.name}`  
**Snapshot NOT locked. Step 3 NOT started. Awaiting user review.**

## JSN

| | Before | After |
|--|-------:|------:|
| WR rank | {jsn_before_rank} | {jsn_rank} |
| Rec yards | {before_rec_by_player.get('Jaxon Smith-Njigba', 0):.0f} | {_f(jsn_after, 'receiving_yards_total') if jsn_after else 0:.0f} |

## Top WRs

| Rank | Player | Team | Rec yds | Before |
|-----:|--------|------|--------:|-------:|
{wr_lines}

## Top RBs

| Rank | Player | Team | Rush yds | Before |
|-----:|--------|------|---------:|-------:|
{rb_lines}

## Conservation

| Check | Value |
|-------|------:|
| max \|rec−pass\| / pass | {max_gap:.4%} |
| rush team sums conserved | {rush_ok} |
| pass pool | {sum(after_pass.values()):.1f} |
| rush pool | {sum(after_rush.values()):.1f} |
| ARI/BAL/SEA pass | { {t: round(after_pass[t], 1) for t in LOCKED_PASS_SCHEME_TEAMS} } |

## Team win / PF picture (unchanged from Step 1)

| Metric | Value |
|--------|------:|
| Wins min / max | {min(after_wins):.2f} / {max(after_wins):.2f} |
| Wins range | {max(after_wins)-min(after_wins):.2f} |
| Wins Σ | {sum(after_wins):.2f} |
| League PF / PA | {sum(after_pf):.1f} / {sum(after_pa):.1f} |

## Smoke gates

| Check | Result |
|-------|--------|
{gate_table}
| **ALL Step 2** | {'**PASS**' if all(gates.values()) else '**FAIL**'} |

## Method
1. Hierarchical usage fallback (WR1 ≫ TE1) replaces WR=TE logjam
2. 2025 elite priors: sticky share = max(prior_tgt×{audit.get('retention')}, prior_yards×retention/team_pool)
3. Alpha volume regression cut to 8% (efficiency regression unchanged)
4. Yard floors: top-5 WR ≥1400; WR12–15 band ≥1150; bell-cow RB ≥1400 when team rush supports
5. TE compressed when sticky WR1 alpha present; rookies/depth not inflated
6. Team pass/rush locked; conservation renorm; team W/L+PF carried forward

## Status
**NOT locked** — awaiting user review before Step 3 final lock.
""",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "bundle": out_bundle.name,
                "ops_note": ops_note.name,
                "gates": gates,
                "jsn_rank": jsn_rank,
                "jsn_yards": round(_f(jsn_after, "receiving_yards_total"), 1) if jsn_after else None,
                "top_wr": top_wrs_report[:5],
                "top_rb": top_rbs_report[:5],
            },
            indent=2,
        )
    )
    if not all(gates.values()):
        failed = [k for k, v in gates.items() if not v]
        print("FAILED GATES:", failed, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
