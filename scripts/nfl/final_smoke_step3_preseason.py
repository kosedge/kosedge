#!/usr/bin/env python3
"""Step 3 — Final full-board smoke on Step 1+2 preseason board (NOT locked).

Loads the Step 2 board (team + player), runs comprehensive conservation /
distribution / alpha smokes, stamps a review bundle, writes the ops draft,
and optionally refreshes the web pointer — always with locked_snapshot=false.
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "data-platform-nfl" / "src"))

from data_platform_nfl.defensive_production_stack import (  # noqa: E402
    TeamDefenseBudget,
    smoke_defensive_stack,
)
from data_platform_nfl.offensive_production_stack import (  # noqa: E402
    LOCKED_PASS_SCHEME_TEAMS,
    locked_team_pass_yards,
    smoke_offensive_stack,
)

BASE_BUNDLE = ROOT / "data/ops/nfl-preseason-sim-2026-20260809T150233Z"
ENGINE = "nfl-season-engine-v1.23-soft-flags-enterprise"
TARGET_LEAGUE_PF = 11_859.2
LOCKED_PASS_POOL = 125_998.1
LOCKED_RUSH_POOL = 64_000.0
LOCKED_SCHEME_PASS = {"ARI": 4350.4, "BAL": 3578.6, "SEA": 4258.5}


def _f(row: Dict[str, Any], *keys: str) -> float:
    for k in keys:
        if k in row and row[k] not in (None, ""):
            try:
                return float(row[k])
            except (TypeError, ValueError):
                continue
    return 0.0


def _load_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        return [dict(r) for r in csv.DictReader(f)]


def _tb5(
    rows: Sequence[Dict[str, Any]], key: str, *, n: int = 5, label_keys: Sequence[str]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    ranked = sorted(rows, key=lambda r: -_f(r, key))
    def pack(r: Dict[str, Any], rank: int) -> Dict[str, Any]:
        out = {"rank": rank, key: round(_f(r, key), 2)}
        for lk in label_keys:
            out[lk] = r.get(lk)
        return out

    top = [pack(r, i) for i, r in enumerate(ranked[:n], 1)]
    bot = [pack(r, i) for i, r in enumerate(reversed(ranked[-n:]), 1)]
    # bottom ranked 1 = worst
    bot = [pack(r, i) for i, r in enumerate(ranked[-n:][::-1], 1)]
    return top, bot


def _fmt_tb(rows: Sequence[Dict[str, Any]], key: str, name_key: str, team_key: str = "team") -> str:
    lines = []
    for r in rows:
        name = r.get(name_key) or r.get("player") or r.get("team")
        team = r.get(team_key) or ""
        val = r.get(key)
        if team and name != team:
            lines.append(f"- {r['rank']}. {name} ({team}): {val}")
        else:
            lines.append(f"- {r['rank']}. {name}: {val}")
    return "\n".join(lines)


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
    ops_note = ROOT / f"data/ops/nfl-preseason-final-smoke-step3-{day}.md"

    players = _load_csv(BASE_BUNDLE / "player_regular_season_totals.csv")
    outcomes = _load_csv(BASE_BUNDLE / "team_regular_season_outcomes.csv")
    defense = _load_csv(BASE_BUNDLE / "team_defense_season_totals.csv")

    # ---- Player leaders (skill) ----
    qbs = [r for r in players if str(r.get("position") or "").upper() == "QB"]
    wrs = [r for r in players if str(r.get("position") or "").upper() == "WR"]
    rbs = [r for r in players if str(r.get("position") or "").upper() == "RB"]
    skill = [r for r in players if str(r.get("position") or "").upper() in {"WR", "TE", "RB"}]

    pass_yd_top, pass_yd_bot = _tb5(qbs, "pass_yards_total", label_keys=("player_name", "team"))
    rush_yd_top, rush_yd_bot = _tb5(rbs, "rush_yards_total", label_keys=("player_name", "team"))
    # Receiving: all skill (WR/TE/RB)
    rec_yd_top, rec_yd_bot = _tb5(skill, "receiving_yards_total", label_keys=("player_name", "team", "position"))
    pass_td_top, pass_td_bot = _tb5(qbs, "pass_tds_total", label_keys=("player_name", "team"))
    rush_td_top, rush_td_bot = _tb5(
        [r for r in players if _f(r, "rush_tds_total") > 0 or str(r.get("position") or "").upper() in {"RB", "QB"}],
        "rush_tds_total",
        label_keys=("player_name", "team", "position"),
    )
    rec_td_top, rec_td_bot = _tb5(skill, "rec_tds_total", label_keys=("player_name", "team", "position"))

    # ---- Team leaders ----
    pf_top, pf_bot = _tb5(outcomes, "points_for", label_keys=("team",))
    pa_top, pa_bot = _tb5(outcomes, "points_against", label_keys=("team",))
    wins_top, wins_bot = _tb5(outcomes, "expected_wins", label_keys=("team",))

    # ---- Alpha / JSN ----
    wr_ranked = sorted(wrs, key=lambda r: -_f(r, "receiving_yards_total"))
    jsn = next((r for r in wr_ranked if "Smith-Njigba" in str(r.get("player_name") or "")), None)
    jsn_rank = next(
        (i for i, r in enumerate(wr_ranked, 1) if "Smith-Njigba" in str(r.get("player_name") or "")),
        None,
    )
    top_wrs = [
        {
            "rank": i,
            "player": r.get("player_name"),
            "team": r.get("team"),
            "rec_yards": round(_f(r, "receiving_yards_total"), 1),
            "rec_tds": round(_f(r, "rec_tds_total"), 2),
            "target_share": round(_f(r, "target_share"), 3),
        }
        for i, r in enumerate(wr_ranked[:12], 1)
    ]
    rb_ranked = sorted(rbs, key=lambda r: -_f(r, "rush_yards_total"))
    top_rbs = [
        {
            "rank": i,
            "player": r.get("player_name"),
            "team": r.get("team"),
            "rush_yards": round(_f(r, "rush_yards_total"), 1),
            "rush_tds": round(_f(r, "rush_tds_total"), 2),
            "carry_share": round(_f(r, "carry_share"), 3),
        }
        for i, r in enumerate(rb_ranked[:12], 1)
    ]

    # ---- Conservation ----
    team_pass = locked_team_pass_yards(players)
    team_rec: Dict[str, float] = defaultdict(float)
    team_rush: Dict[str, float] = defaultdict(float)
    for r in players:
        t = str(r.get("team") or "")
        pos = str(r.get("position") or "").upper()
        team_rush[t] += _f(r, "rush_yards_total")
        if pos in {"WR", "TE", "RB"}:
            team_rec[t] += _f(r, "receiving_yards_total")
    pass_pool = sum(team_pass.values())
    rush_pool = sum(team_rush.values())
    rec_pool = sum(team_rec.values())
    max_gap = 0.0
    for t, py in team_pass.items():
        gap = abs(team_rec.get(t, 0.0) - py) / max(py, 1.0)
        max_gap = max(max_gap, gap)

    scheme_pass = {t: round(team_pass.get(t, 0.0), 1) for t in LOCKED_PASS_SCHEME_TEAMS}
    scheme_ok = all(
        abs(scheme_pass.get(t, 0.0) - LOCKED_SCHEME_PASS[t]) < 0.15 for t in LOCKED_SCHEME_PASS
    )

    wins = [_f(r, "expected_wins") for r in outcomes]
    pfs = [_f(r, "points_for") for r in outcomes]
    pas = [_f(r, "points_against") for r in outcomes]
    wins_sum = sum(wins)
    wins_min, wins_max = min(wins), max(wins)
    wins_range = wins_max - wins_min
    league_pf, league_pa = sum(pfs), sum(pas)

    off_smoke = smoke_offensive_stack(players)
    def_by_team = {str(r.get("team") or ""): r for r in defense}
    out_by_team = {str(r.get("team") or ""): r for r in outcomes}
    budgets: Dict[str, TeamDefenseBudget] = {}
    for team, o in out_by_team.items():
        d = def_by_team.get(team) or o
        budgets[team] = TeamDefenseBudget(
            team=team,
            points_for=_f(o, "points_for"),
            points_against=_f(o, "points_against"),
            expected_wins=_f(o, "expected_wins"),
            pass_yards_allowed=_f(d, "pass_yards_allowed"),
            rush_yards_allowed=_f(d, "rush_yards_allowed"),
            ints_forced=_f(d, "ints_forced"),
            sacks=_f(d, "sacks"),
            takeaways=_f(d, "takeaways", "ints_forced"),
            point_diff=_f(o, "point_diff") or (_f(o, "points_for") - _f(o, "points_against")),
        )
    def_smoke = smoke_defensive_stack(budgets, players)

    # Soft flags (non-blocking)
    soft_flags: List[str] = []
    rb_at_floor = sum(1 for r in rb_ranked if abs(_f(r, "rush_yards_total") - 1431.6) < 0.5)
    if rb_at_floor >= 8:
        soft_flags.append(
            f"RB yard floor clustering: {rb_at_floor} RBs pinned at ~1432 (bell-cow floor)."
        )
    else:
        top12_rb = [_f(r, "rush_yards_total") for r in rb_ranked[:12]]
        if top12_rb and (max(top12_rb) - min(top12_rb)) < 40:
            soft_flags.append(
                f"RB top-12 still compressed (span {max(top12_rb)-min(top12_rb):.0f} yds)."
            )
    win_ties_top = sum(1 for w in wins if abs(w - wins_max) < 1e-4)
    win_ties_bot = sum(1 for w in wins if abs(w - wins_min) < 1e-4)
    if win_ties_top >= 4:
        soft_flags.append(f"Win ceiling tie: {win_ties_top} teams at max expected_wins={wins_max:.2f}.")
    if win_ties_bot >= 4:
        soft_flags.append(f"Win floor tie: {win_ties_bot} teams at min expected_wins={wins_min:.2f}.")
    pf_ties = sum(1 for p in pfs if abs(p - max(pfs)) < 0.05)
    if pf_ties >= 4:
        soft_flags.append(f"PF ceiling clustering: {pf_ties} teams near max PF={max(pfs):.1f}.")
    # Unrealistic individual ceilings
    for r in wr_ranked[:5]:
        if _f(r, "receiving_yards_total") > 1900:
            soft_flags.append(f"Soft WR ceiling: {r.get('player_name')} {_f(r,'receiving_yards_total'):.0f} rec yds.")
    for r in rb_ranked[:5]:
        if _f(r, "rush_yards_total") > 1800:
            soft_flags.append(f"Soft RB ceiling: {r.get('player_name')} {_f(r,'rush_yards_total'):.0f} rush yds.")
    for r in qbs:
        if _f(r, "pass_yards_total") > 5200:
            soft_flags.append(f"Soft QB ceiling: {r.get('player_name')} {_f(r,'pass_yards_total'):.0f} pass yds.")
    # Scheme/roster sanity: SEA WR1 should be JSN-class; CIN WR1 Chase
    if jsn_rank is None or jsn_rank > 8:
        soft_flags.append(f"JSN not top-tier (rank={jsn_rank}).")
    chase = next((r for r in wr_ranked if "Chase" in str(r.get("player_name") or "")), None)
    if chase and wr_ranked.index(chase) + 1 > 5:
        soft_flags.append("Ja'Marr Chase outside top-5 WR — scheme flag.")
    # High-volume pass → PF/wins coherence (enterprise soft-flag).
    for team, py in team_pass.items():
        if py < 4600:
            continue
        row = out_by_team.get(team) or {}
        pf_t = _f(row, "points_for")
        w_t = _f(row, "expected_wins")
        if pf_t < 340 or w_t < 8.0:
            soft_flags.append(
                f"{team} volume-to-points soft flag: pass={py:.0f} PF={pf_t:.1f} wins={w_t:.2f}."
            )
    kyler = next((r for r in qbs if "Kyler" in str(r.get("player_name") or "")), None)
    if kyler and str(kyler.get("team") or "") != "MIN":
        soft_flags.append(f"Kyler Murray labeled {kyler.get('team')} (expected MIN).")

    gates = {
        "league_pf_pa_11859": abs(league_pf - TARGET_LEAGUE_PF) < 1.0
        and abs(league_pa - TARGET_LEAGUE_PF) < 1.0,
        "wins_sum_272": abs(wins_sum - 272.0) < 0.05,
        "win_range_ge_7_5": wins_range >= 7.5,
        "pass_pool_locked": abs(pass_pool - LOCKED_PASS_POOL) < 1.0,
        "rush_pool_64000": abs(rush_pool - LOCKED_RUSH_POOL) < 1.0,
        "rec_pass_within_1_5pct": max_gap <= 0.015 + 1e-9,
        "ari_bal_sea_pass_untouched": scheme_ok,
        "top_wr_multiple_1400": sum(1 for r in wr_ranked[:5] if _f(r, "receiving_yards_total") >= 1400) >= 3,
        "top_wr_end_1550": _f(wr_ranked[0], "receiving_yards_total") >= 1550,
        "top_rb_1400": _f(rb_ranked[0], "rush_yards_total") >= 1400,
        "jsn_top_tier": jsn_rank is not None and jsn_rank <= 5 and _f(jsn or {}, "receiving_yards_total") >= 1400,
        "offense_smoke": bool(off_smoke.get("all_pass")),
        "defense_smoke": bool(def_smoke.get("all_pass")),
        "step1_gates_held": True,  # filled below
        "step2_gates_held": True,
    }
    gates["step1_gates_held"] = all(
        [
            gates["league_pf_pa_11859"],
            gates["wins_sum_272"],
            gates["win_range_ge_7_5"],
            gates["pass_pool_locked"],
            gates["ari_bal_sea_pass_untouched"],
            gates["rush_pool_64000"],
        ]
    )
    gates["step2_gates_held"] = all(
        [
            gates["top_wr_multiple_1400"],
            gates["top_wr_end_1550"],
            gates["top_rb_1400"],
            gates["jsn_top_tier"],
            gates["rec_pass_within_1_5pct"],
        ]
    )
    all_pass = all(gates.values())

    # ---- Stamp review bundle (copy + enrich) ----
    out_bundle.mkdir(parents=True, exist_ok=True)
    research.mkdir(parents=True, exist_ok=True)
    for name in (
        "player_regular_season_totals.csv",
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
    leaders = {
        "pass_yards": {"top": pass_yd_top, "bottom": pass_yd_bot},
        "rush_yards": {"top": rush_yd_top, "bottom": rush_yd_bot},
        "receiving_yards": {"top": rec_yd_top, "bottom": rec_yd_bot},
        "pass_tds": {"top": pass_td_top, "bottom": pass_td_bot},
        "rush_tds": {"top": rush_td_top, "bottom": rush_td_bot},
        "rec_tds": {"top": rec_td_top, "bottom": rec_td_bot},
        "points_for": {"top": pf_top, "bottom": pf_bot},
        "points_against": {"top": pa_top, "bottom": pa_bot},
        "expected_wins": {"top": wins_top, "bottom": wins_bot},
    }
    run_summary = {
        "engine_version": ENGINE,
        "generated_at_utc": generated,
        "n_team_sims": 50000,
        "n_player_sims": 1000,
        "step": 3,
        "method": "final_full_board_smoke_v1",
        "base_bundle": BASE_BUNDLE.name,
        "locked_snapshot": False,
        "status": "NOT_LOCKED_AWAITING_REVIEW",
        "gates": gates,
        "all_step3_pass": all_pass,
        "jsn": {
            "rank": jsn_rank,
            "yards": round(_f(jsn or {}, "receiving_yards_total"), 1) if jsn else None,
            "rec_tds": round(_f(jsn or {}, "rec_tds_total"), 2) if jsn else None,
            "target_share": round(_f(jsn or {}, "target_share"), 3) if jsn else None,
            "team": "SEA",
        },
        "top_wrs": top_wrs,
        "top_rbs": top_rbs,
        "leaders": leaders,
        "conservation": {
            "pass_pool": round(pass_pool, 1),
            "rush_pool": round(rush_pool, 1),
            "rec_pool": round(rec_pool, 1),
            "max_rec_pass_gap_pct": round(max_gap * 100, 4),
            "scheme_pass": scheme_pass,
            "league_pf": round(league_pf, 2),
            "league_pa": round(league_pa, 2),
            "wins_sum": round(wins_sum, 4),
            "wins_min": round(wins_min, 4),
            "wins_max": round(wins_max, 4),
            "wins_range": round(wins_range, 4),
        },
        "soft_flags": soft_flags,
        "offense_smoke": off_smoke,
        "defense_smoke": def_smoke,
        "note": "Step 3 final smoke — snapshot NOT LOCKED — awaiting user review",
    }
    (out_bundle / "run_summary.json").write_text(
        json.dumps(run_summary, indent=2, default=str) + "\n", encoding="utf-8"
    )
    (out_bundle / "quality_checks.json").write_text(
        json.dumps(
            {
                "gates": gates,
                "all_step3_pass": all_pass,
                "soft_flags": soft_flags,
                "offense_smoke": off_smoke,
                "defense_smoke": def_smoke,
                "locked_snapshot": False,
            },
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_bundle / "leaders.json").write_text(
        json.dumps(leaders, indent=2) + "\n", encoding="utf-8"
    )
    shutil.copy2(out_bundle / "run_summary.json", research / "run_summary.json")
    shutil.copy2(out_bundle / "quality_checks.json", research / "quality_checks.json")
    shutil.copy2(out_bundle / "leaders.json", research / "leaders.json")

    # Web pointer — NOT locked
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
                "- **Note:** Step 3 final smoke — **NOT LOCKED — awaiting review**",
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
                "note": "Step 3 final smoke; NOT LOCKED — awaiting review",
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
    soft_block = (
        "\n".join(f"- {s}" for s in soft_flags)
        if soft_flags
        else "- None material beyond listed clustering notes."
    )
    wr_lines = "\n".join(
        f"| {x['rank']} | {x['player']} | {x['team']} | {x['rec_yards']:.0f} | {x['rec_tds']:.1f} |"
        for x in top_wrs
    )
    rb_lines = "\n".join(
        f"| {x['rank']} | {x['player']} | {x['team']} | {x['rush_yards']:.0f} | {x['rush_tds']:.1f} |"
        for x in top_rbs
    )

    jsn_yds = _f(jsn or {}, "receiving_yards_total")
    jsn_tgt = _f(jsn or {}, "target_share")
    md = f"""# NFL Preseason Final Smoke — Step 3

Date: {day}  
Engine: `{ENGINE}`  
Base: Step 2 board (`{BASE_BUNDLE.name}`)  
Review bundle: `{out_bundle.name}`  
Web pointer: `{out_bundle.name}`  

## Status

**NOT LOCKED — awaiting review**

Do not treat this as a production lock. No final-lock tag. No locked-baseline pointer update.

## Conservation

| Check | Value |
|-------|------:|
| Pass pool | {pass_pool:.1f} |
| Rec pool | {rec_pool:.1f} |
| max \\|rec−pass\\| / pass | {max_gap*100:.4f}% |
| Rush pool | {rush_pool:.1f} |
| League PF / PA | {league_pf:.1f} / {league_pa:.1f} |
| Wins Σ | {wins_sum:.2f} |
| Wins min / max / range | {wins_min:.2f} / {wins_max:.2f} / {wins_range:.2f} |
| ARI/BAL/SEA pass | {scheme_pass} |

## Key alpha check

| | Value |
|--|------:|
| JSN WR rank | {jsn_rank} |
| JSN rec yards | {jsn_yds:.0f} |
| JSN target share | {jsn_tgt:.3f} |

### Top WRs

| Rank | Player | Team | Rec yds | Rec TDs |
|-----:|--------|------|--------:|--------:|
{wr_lines}

### Top RBs

| Rank | Player | Team | Rush yds | Rush TDs |
|-----:|--------|------|---------:|---------:|
{rb_lines}

## Top / bottom 5 — Player

### Pass yards
**Top**
{_fmt_tb(pass_yd_top, 'pass_yards_total', 'player_name')}

**Bottom**
{_fmt_tb(pass_yd_bot, 'pass_yards_total', 'player_name')}

### Rush yards
**Top**
{_fmt_tb(rush_yd_top, 'rush_yards_total', 'player_name')}

**Bottom**
{_fmt_tb(rush_yd_bot, 'rush_yards_total', 'player_name')}

### Receiving yards
**Top**
{_fmt_tb(rec_yd_top, 'receiving_yards_total', 'player_name')}

**Bottom**
{_fmt_tb(rec_yd_bot, 'receiving_yards_total', 'player_name')}

### Passing TDs
**Top**
{_fmt_tb(pass_td_top, 'pass_tds_total', 'player_name')}

**Bottom**
{_fmt_tb(pass_td_bot, 'pass_tds_total', 'player_name')}

### Rushing TDs
**Top**
{_fmt_tb(rush_td_top, 'rush_tds_total', 'player_name')}

**Bottom**
{_fmt_tb(rush_td_bot, 'rush_tds_total', 'player_name')}

### Receiving TDs
**Top**
{_fmt_tb(rec_td_top, 'rec_tds_total', 'player_name')}

**Bottom**
{_fmt_tb(rec_td_bot, 'rec_tds_total', 'player_name')}

## Top / bottom 5 — Team

### PF
**Top**
{_fmt_tb(pf_top, 'points_for', 'team')}

**Bottom**
{_fmt_tb(pf_bot, 'points_for', 'team')}

### PA
**Top**
{_fmt_tb(pa_top, 'points_against', 'team')}

**Bottom**
{_fmt_tb(pa_bot, 'points_against', 'team')}

### Wins
**Top**
{_fmt_tb(wins_top, 'expected_wins', 'team')}

**Bottom**
{_fmt_tb(wins_bot, 'expected_wins', 'team')}

## Smoke gates

| Check | Result |
|-------|--------|
{gate_table}
| **ALL Step 3** | {'**PASS**' if all_pass else '**FAIL**'} |

Offense smoke all_pass: `{off_smoke.get('all_pass')}`  
Defense smoke all_pass: `{def_smoke.get('all_pass')}`

## Soft flags (non-blocking)

{soft_block}

## Method

1. Load Step 2 complete board (team outcomes + player totals; Step 1 variance + Step 2 alpha re-anchor)
2. Recompute conservation, Step 1/2 gates, offense + defense smoke
3. Emit top/bottom-5 leaderboards for yards/TDs/PF/PA/wins
4. Stamp review bundle + refresh web pointer with `locked_snapshot: false`
5. **Do not lock** — await user review

## Explicit

**NOT LOCKED**
"""
    ops_note.write_text(md, encoding="utf-8")
    (research / "LAUNCH_RESEARCH_NOTE.md").write_text(
        f"# Step 3 final smoke — {stamp}\n\n"
        f"- Engine: `{ENGINE}`\n"
        f"- Bundle: `{out_bundle.name}`\n"
        f"- Ops: `{ops_note.name}`\n"
        f"- **NOT LOCKED — awaiting review**\n",
        encoding="utf-8",
    )

    print(json.dumps(
        {
            "bundle": out_bundle.name,
            "ops_note": str(ops_note.relative_to(ROOT)),
            "all_step3_pass": all_pass,
            "gates": gates,
            "soft_flags": soft_flags,
            "jsn": run_summary["jsn"],
            "conservation": run_summary["conservation"],
            "locked_snapshot": False,
        },
        indent=2,
    ))
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
