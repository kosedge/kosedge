#!/usr/bin/env python3
"""Finalize 100k expert-sim candidate board (NOT LOCKED).

Pipeline after ``run_launch_research_sims.py`` completes:
1. Publish research → web CSV bundle
2. Seed defense priors from latest enterprise board
3. Offense variance lift (rush → 64k; pass + ARI/BAL/SEA locked)
4. Alpha usage reanchor
5. Soft-flag enterprise (HV pass-TD floors, soft RB priors, tapered PF/PA)
6. Write expert ops report + pointer with locked_snapshot=false

Does NOT tag official baseline. Does NOT set locked_snapshot true.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "data-platform-nfl" / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "nfl"))

from data_platform_nfl.defensive_production_stack import (  # noqa: E402
    apply_defensive_production_stack,
    budgets_to_rows,
    smoke_defensive_stack,
)
from data_platform_nfl.offensive_production_stack import (  # noqa: E402
    LOCKED_PASS_SCHEME_TEAMS,
    apply_alpha_usage_reanchor,
    apply_offensive_variance_lift,
    apply_soft_rb_priors_on_board,
    build_team_rush_tds,
    enforce_high_volume_pass_tds_on_rows,
    locked_team_pass_yards,
    repair_qb_team_labels,
    repair_skill_team_labels,
    smoke_offensive_stack,
)

from publish_launch_research_to_web import publish  # noqa: E402

ENGINE = "nfl-season-engine-v1.24-soft-piles-cleanup"
SEED_DEFENSE_BUNDLE = ROOT / "data/ops/nfl-preseason-sim-2026-20260809T150309Z"
CANON_QB1 = {
    "ARI": "Kyler Murray",
    "MIN": "J.J. McCarthy",
    "ATL": "Michael Penix Jr.",
    "MIA": "Tua Tagovailoa",
}


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


def _tb(
    rows: Sequence[Dict[str, Any]], key: str, n: int = 10, bottom: int = 5
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    ranked = sorted(rows, key=lambda r: -_f(r, key))
    top = [
        {
            "rank": i,
            "label": r.get("player_name") or r.get("team"),
            "team": r.get("team"),
            "position": r.get("position"),
            "value": round(_f(r, key), 2),
        }
        for i, r in enumerate(ranked[:n], 1)
    ]
    bot = [
        {
            "rank": len(ranked) - len(ranked[-bottom:]) + i,
            "label": r.get("player_name") or r.get("team"),
            "team": r.get("team"),
            "position": r.get("position"),
            "value": round(_f(r, key), 2),
        }
        for i, r in enumerate(ranked[-bottom:], 1)
    ]
    return top, bot


def _fmt_tb(rows: List[Dict[str, Any]], *, with_team: bool = True) -> str:
    lines = []
    for r in rows:
        label = r["label"]
        team = r.get("team")
        if with_team and team and label != team:
            lines.append(f"| {r['rank']} | {label} | {team} | {r['value']} |")
        else:
            lines.append(f"| {r['rank']} | {label} | {r['value']} |")
    return "\n".join(lines)


def _seed_defense_into_bundle(bundle: Path, seed: Path) -> None:
    defense_dst = bundle / "team_defense_season_totals.csv"
    if defense_dst.exists():
        return
    src = seed / "team_defense_season_totals.csv"
    if not src.exists():
        raise FileNotFoundError(f"Missing seed defense: {src}")
    shutil.copy2(src, defense_dst)
    # Enrich thin outcomes with PF/PA columns from seed when missing.
    outcomes_path = bundle / "team_regular_season_outcomes.csv"
    outcomes = _load_csv(outcomes_path)
    if outcomes and "points_for" in outcomes[0]:
        return
    seed_out = {r["team"]: r for r in _load_csv(seed / "team_regular_season_outcomes.csv")}
    for r in outcomes:
        prev = seed_out.get(r["team"]) or {}
        for k in (
            "points_for",
            "points_against",
            "point_diff",
            "pass_yards_allowed",
            "rush_yards_allowed",
            "ints_forced",
            "sacks",
            "takeaways",
            "ppg",
            "pa_pg",
            "sim_expected_wins",
        ):
            if k not in r or r[k] in (None, ""):
                if k == "sim_expected_wins":
                    r[k] = r.get("expected_wins")
                elif k in prev:
                    r[k] = prev[k]
    fields = list(outcomes[0].keys())
    # Prefer a stable wide schema.
    for k in (
        "season",
        "team",
        "conference",
        "division",
        "expected_wins",
        "sim_expected_wins",
        "wins_p10",
        "wins_p90",
        "playoff_prob",
        "division_title_prob",
        "super_bowl_win_prob",
        "points_for",
        "points_against",
        "point_diff",
        "pass_yards_allowed",
        "rush_yards_allowed",
        "ints_forced",
        "sacks",
        "takeaways",
        "ppg",
        "pa_pg",
    ):
        if k not in fields:
            fields.append(k)
    _write_csv(outcomes_path, outcomes, fields)


def _enrich_players_from_json(bundle: Path, source: Path) -> None:
    """Ensure player CSV has share/int columns when available from research JSON."""
    json_path = source / "player_season_totals.json"
    csv_path = bundle / "player_regular_season_totals.csv"
    if not json_path.exists() or not csv_path.exists():
        return
    players = json.loads(json_path.read_text(encoding="utf-8"))
    by_key = {str(p.get("player_key") or ""): p for p in players}
    rows = _load_csv(csv_path)
    for r in rows:
        src = by_key.get(str(r.get("player_key") or "")) or {}
        if "ints_total" not in r or r.get("ints_total") in (None, ""):
            r["ints_total"] = round(float(src.get("ints_mean") or 0), 3)
        for src_k, dst_k in (
            ("snap_share", "snap_share"),
            ("target_share", "target_share"),
            ("rush_share", "carry_share"),
            ("is_rookie", "is_rookie"),
            ("draft_round", "draft_round"),
        ):
            if dst_k not in r or r.get(dst_k) in (None, ""):
                if src_k in src:
                    r[dst_k] = src[src_k]
    fields = list(rows[0].keys())
    for k in (
        "ints_total",
        "snap_share",
        "target_share",
        "carry_share",
        "is_rookie",
        "draft_round",
    ):
        if k not in fields:
            fields.append(k)
    _write_csv(csv_path, rows, fields)


def finalize(source: Path, *, seed_defense: Path, stamp: Optional[str] = None) -> Dict[str, Any]:
    source = source.resolve()
    if not (source / "run_summary.json").exists():
        raise FileNotFoundError(f"Missing research run_summary: {source}")

    summary = json.loads((source / "run_summary.json").read_text(encoding="utf-8"))
    n_team = int(summary.get("n_team_sims") or 100000)
    n_player = int(summary.get("n_player_sims") or 1000)
    # Post-board engine version (pile cleanup) — research may still say v1.23.
    engine = ENGINE
    timing = summary.get("timing_seconds") or {}

    published = publish(source, stamp)
    _seed_defense_into_bundle(published, seed_defense)
    _enrich_players_from_json(published, source)

    stamp = published.name.replace("nfl-preseason-sim-2026-", "")
    day = stamp[:8]
    out_bundle = ROOT / f"data/ops/nfl-preseason-sim-2026-{stamp}"
    if out_bundle.resolve() != published.resolve():
        # publish already created this path; keep working in published
        out_bundle = published

    players = _load_csv(out_bundle / "player_regular_season_totals.csv")
    before_outcomes = _load_csv(out_bundle / "team_regular_season_outcomes.csv")
    before_defense = _load_csv(out_bundle / "team_defense_season_totals.csv")

    before_pass = locked_team_pass_yards(players)
    scheme_before = {t: before_pass[t] for t in LOCKED_PASS_SCHEME_TEAMS}

    # 1) rush variance lift → 64k (v1.24 tapered — no hard rush rails)
    players, _team_rush, off_lift_audit = apply_offensive_variance_lift(players)
    # 2) alpha usage
    players, alpha_audit = apply_alpha_usage_reanchor(players)
    # 3) label hygiene (QB + skill; identity-only)
    players, label_audit = repair_qb_team_labels(players)
    players, skill_label_audit = repair_skill_team_labels(players)
    label_audit = {
        "applied": True,
        "fixes": list(label_audit.get("fixes") or [])
        + list(skill_label_audit.get("fixes") or []),
        "qb": label_audit,
        "skill": skill_label_audit,
    }
    # 4) high-volume pass TD floors
    players, td_audit = enforce_high_volume_pass_tds_on_rows(players)
    # 5) soft RB priors
    players, rb_audit = apply_soft_rb_priors_on_board(players)

    # 5b) rebuild rush-TD curve on lifted 64k pool (engine paths under-count TDs)
    team_rush_map: Dict[str, float] = defaultdict(float)
    for r in players:
        team_rush_map[str(r.get("team") or "")] += _f(r, "rush_yards_total")
    team_rush_tds = build_team_rush_tds(dict(team_rush_map))
    for team, target_td in team_rush_tds.items():
        team_rows = [r for r in players if str(r.get("team") or "") == team]
        cur_td = sum(_f(r, "rush_tds_total") for r in team_rows) or 1.0
        scale_td = float(target_td) / cur_td
        for r in team_rows:
            r["rush_tds_total"] = round(_f(r, "rush_tds_total") * scale_td, 4)
            # refresh anytime TD proxy when present
            if "anytime_td_prob" in r:
                rush_td = _f(r, "rush_tds_total")
                rec_td = _f(r, "rec_tds_total")
                r["anytime_td_prob"] = round(
                    min(0.9999, max(0.0, 1.0 - math.exp(-(rush_td + rec_td)))), 4
                )

    after_pass = locked_team_pass_yards(players)
    after_rush: Dict[str, float] = defaultdict(float)
    after_rec: Dict[str, float] = defaultdict(float)
    for r in players:
        t = str(r.get("team") or "")
        after_rush[t] += _f(r, "rush_yards_total")
        if str(r.get("position") or "").upper() in {"WR", "TE", "RB"}:
            after_rec[t] += _f(r, "receiving_yards_total")

    for t in LOCKED_PASS_SCHEME_TEAMS:
        assert abs(after_pass[t] - scheme_before[t]) < 0.05, (t, after_pass[t], scheme_before[t])
    assert abs(sum(after_pass.values()) - sum(before_pass.values())) < 1.0
    assert abs(sum(after_rush.values()) - 64_000.0) < 1.0, sum(after_rush.values())

    max_rec_gap = 0.0
    for t, py in after_pass.items():
        gap = abs(after_rec[t] - py) / max(py, 1.0)
        max_rec_gap = max(max_rec_gap, gap)
    assert max_rec_gap <= 0.015 + 1e-6, max_rec_gap

    off_smoke = smoke_offensive_stack(players)

    teams = sorted(after_pass.keys())
    prior_pa = {r["team"]: float(r["points_against"]) for r in before_defense}
    prior_sacks = {r["team"]: float(r["sacks"]) for r in before_defense}
    prior_ints = {r["team"]: float(r["ints_forced"]) for r in before_defense}
    budgets, def_audit = apply_defensive_production_stack(
        players,
        schedule=_circle_schedule(teams),
        defense_index={t: 1.0 for t in teams},
        offense_index={t: 1.0 for t in teams},
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
        for k in ("wins_p10", "wins_p90", "playoff_prob", "division_title_prob", "super_bowl_win_prob"):
            if k in prev and (k not in row or row[k] in (None, "")):
                row[k] = prev[k]

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

    # Write finalized CSVs into out_bundle (overwrite publish)
    player_fields = list(players[0].keys())
    for r in players:
        r.setdefault("season", 2026)
    _write_csv(out_bundle / "player_regular_season_totals.csv", players, player_fields)
    (out_bundle / "player_playoff_totals.csv").write_text(
        "season,player_key,player_name,team,position\n", encoding="utf-8"
    )
    _write_csv(out_bundle / "team_regular_season_outcomes.csv", outcome_rows, list(outcome_rows[0].keys()))
    _write_csv(out_bundle / "team_defense_season_totals.csv", defense_rows, list(defense_rows[0].keys()))

    # Leaders / coherence
    qbs = [r for r in players if str(r.get("position") or "").upper() == "QB"]
    wrs = [r for r in players if str(r.get("position") or "").upper() == "WR"]
    rbs = [r for r in players if str(r.get("position") or "").upper() == "RB"]
    skill = [r for r in players if str(r.get("position") or "").upper() in {"WR", "TE", "RB"}]

    team_pass_rows = [{"team": t, "pass_yards_total": v} for t, v in after_pass.items()]
    team_rush_rows = [{"team": t, "rush_yards_total": v} for t, v in after_rush.items()]

    pass_t_top, pass_t_bot = _tb(team_pass_rows, "pass_yards_total")
    rush_t_top, rush_t_bot = _tb(team_rush_rows, "rush_yards_total")
    pf_top, pf_bot = _tb(outcome_rows, "points_for")
    pa_top, pa_bot = _tb(outcome_rows, "points_against")
    wins_top, wins_bot = _tb(outcome_rows, "expected_wins")

    rec_yd_top, rec_yd_bot = _tb(skill, "receiving_yards_total")
    rush_yd_top, rush_yd_bot = _tb(rbs, "rush_yards_total")
    rec_td_top, _ = _tb(skill, "rec_tds_total")
    rush_td_top, _ = _tb(rbs, "rush_tds_total")
    pass_yd_top, pass_yd_bot = _tb(qbs, "pass_yards_total")
    pass_td_top, _ = _tb(qbs, "pass_tds_total")

    wr_ranked = sorted(wrs, key=lambda r: -_f(r, "receiving_yards_total"))
    jsn = next((r for r in wr_ranked if "Smith-Njigba" in str(r.get("player_name") or "")), None)
    jsn_rank = next(
        (i for i, r in enumerate(wr_ranked, 1) if "Smith-Njigba" in str(r.get("player_name") or "")),
        None,
    )
    chase = next((r for r in wr_ranked if "Chase" in str(r.get("player_name") or "")), None)
    chase_rank = next(
        (i for i, r in enumerate(wr_ranked, 1) if "Chase" in str(r.get("player_name") or "")),
        None,
    )
    nacua = next((r for r in wr_ranked if "Nacua" in str(r.get("player_name") or "")), None)
    nacua_rank = next(
        (i for i, r in enumerate(wr_ranked, 1) if "Nacua" in str(r.get("player_name") or "")),
        None,
    )
    top5_rbs = [
        {
            "rank": i,
            "player": r.get("player_name"),
            "team": r.get("team"),
            "rush_yards": round(_f(r, "rush_yards_total"), 1),
            "rush_tds": round(_f(r, "rush_tds_total"), 2),
        }
        for i, r in enumerate(sorted(rbs, key=lambda x: -_f(x, "rush_yards_total"))[:5], 1)
    ]

    wins = [b.expected_wins for b in budgets.values()]
    pfs = [b.points_for for b in budgets.values()]
    pas = [b.points_against for b in budgets.values()]
    wins_min, wins_max = min(wins), max(wins)
    win_range = wins_max - wins_min
    wins_sum = sum(wins)
    league_pf, league_pa = sum(pfs), sum(pas)

    def _max_cluster(vals: List[float], width: float) -> Tuple[int, float]:
        xs = sorted(vals)
        best = 1
        best_at = xs[0] if xs else 0.0
        j = 0
        for i in range(len(xs)):
            while xs[i] - xs[j] > width:
                j += 1
            if i - j + 1 > best:
                best = i - j + 1
                best_at = xs[j]
        return best, best_at

    # Soft flags
    soft_flags: List[str] = []
    if win_range < 7.5:
        soft_flags.append(f"Win range soft: {win_range:.2f} (<7.5).")
    win_ties_top = Counter(round(w, 2) for w in wins).most_common(1)[0][1]
    win_ceil_cluster, win_ceil_at = _max_cluster([w for w in wins if w >= wins_max - 0.05], 0.02)
    if win_ties_top >= 4 or win_ceil_cluster >= 4:
        soft_flags.append(
            f"Win ceiling clustering: {max(win_ties_top, win_ceil_cluster)} teams near max "
            f"(~{win_ceil_at:.2f})."
        )
    pf_ties = Counter(round(p, 1) for p in pfs).most_common(1)[0][1]
    pf_floor_cluster, pf_floor_at = _max_cluster(
        [p for p in pfs if p <= min(pfs) + 1.0], 0.25
    )
    pf_ceil_cluster, pf_ceil_at = _max_cluster(
        [p for p in pfs if p >= max(pfs) - 2.0], 0.25
    )
    if pf_ties >= 6:
        soft_flags.append(f"PF clustering: {pf_ties} teams near same PF.")
    if pf_floor_cluster >= 6:
        soft_flags.append(
            f"PF soft-floor pile: {pf_floor_cluster} teams at PF≈{pf_floor_at:.1f}."
        )
    if pf_ceil_cluster >= 6:
        soft_flags.append(
            f"PF soft-ceiling pile: {pf_ceil_cluster} teams at PF≈{pf_ceil_at:.1f}."
        )

    rush_vals = list(after_rush.values())
    rush_ceil_cluster, rush_ceil_at = _max_cluster(
        [v for v in rush_vals if v >= max(rush_vals) - 5.0], 1.0
    )
    rush_floor_cluster, rush_floor_at = _max_cluster(
        [v for v in rush_vals if v <= min(rush_vals) + 5.0], 1.0
    )
    if rush_ceil_cluster >= 6 or rush_floor_cluster >= 6:
        soft_flags.append(
            f"Rush soft-ceiling pile: {rush_ceil_cluster} teams at ~{rush_ceil_at:.0f} rush yds; "
            f"{rush_floor_cluster} at soft floor ~{rush_floor_at:.0f}."
        )

    for r in wr_ranked[:3]:
        if _f(r, "receiving_yards_total") >= 1600 and after_pass[str(r.get("team"))] < 3400:
            soft_flags.append(
                f"Orphan WR volume: {r.get('player_name')} on {r.get('team')} "
                f"pass={after_pass[str(r.get('team'))]:.0f}."
            )
    if jsn_rank is None or jsn_rank > 8:
        soft_flags.append(f"JSN not top-tier (rank={jsn_rank}).")
    if chase_rank is None or chase_rank > 5:
        soft_flags.append(f"Chase outside top-5 WR (rank={chase_rank}).")

    # High-volume pass → PF/wins
    for t, py in after_pass.items():
        if py < 4600:
            continue
        b = budgets[t]
        if b.points_for < 360 or b.expected_wins < 7.5:
            soft_flags.append(
                f"{t} volume-to-points soft flag: pass={py:.0f} PF={b.points_for:.1f} wins={b.expected_wins:.2f}."
            )

    # Depth labels
    label_issues = []
    for team, want in CANON_QB1.items():
        qb1 = max(
            (r for r in qbs if r.get("team") == team),
            key=lambda r: _f(r, "pass_yards_total"),
            default=None,
        )
        if qb1 is None or str(qb1.get("player_name")) != want:
            label_issues.append(f"{team}: got {None if qb1 is None else qb1.get('player_name')} want {want}")
    evans = next(
        (r for r in skill if "Mike Evans" in str(r.get("player_name") or "")),
        None,
    )
    if evans is not None and str(evans.get("team") or "") != "TB":
        soft_flags.append(
            f"Depth soft: Mike Evans labeled {evans.get('team')} (expected TB)."
        )

    cin = budgets["CIN"]
    burrow = next((r for r in qbs if "Burrow" in str(r.get("player_name") or "")), None)

    # Pythagorean / PF-wins coherence soft check
    by_pf = sorted(budgets.values(), key=lambda b: -b.points_for)
    top_half_pf = {b.team for b in by_pf[:16]}
    by_wins = sorted(budgets.values(), key=lambda b: -b.expected_wins)
    top_half_wins = {b.team for b in by_wins[:16]}
    pf_win_overlap = len(top_half_pf & top_half_wins)
    if pf_win_overlap < 10:
        soft_flags.append(f"PF/wins half overlap soft: {pf_win_overlap}/16.")

    gates = {
        "pass_pool_locked": abs(sum(after_pass.values()) - 126_000.0) < 5.0
        or abs(sum(after_pass.values()) - sum(before_pass.values())) < 1.0,
        "rush_pool_64000": abs(sum(after_rush.values()) - 64_000.0) < 1.0,
        "ari_bal_sea_pass_untouched": all(
            abs(after_pass[t] - scheme_before[t]) < 0.05 for t in LOCKED_PASS_SCHEME_TEAMS
        ),
        "rec_pass_within_1_5pct": max_rec_gap <= 0.015 + 1e-6,
        "league_pf_pa_11859": abs(league_pf - 11859) < 5 and abs(league_pa - 11859) < 5,
        "wins_sum_272": abs(wins_sum - 272.0) < 0.05,
        "win_range_ge_7_5": win_range >= 7.5,
        "cin_not_bottom_tier": cin.expected_wins >= 8.0 and cin.points_for >= 340.0,
        "offense_smoke": bool(off_smoke.get("all_pass", False)),
        "defense_smoke": bool(def_smoke.get("all_pass", False)),
        "qb_labels_clean": not label_issues,
        "jsn_top_tier": jsn_rank is not None and jsn_rank <= 8,
    }

    generated = datetime.now(timezone.utc).isoformat()
    runtime_s = float(timing.get("team_wl") or 0) + float(timing.get("player_full") or 0) + float(
        timing.get("survivor") or 0
    )

    leaders = {
        "team_pass": {"top10": pass_t_top, "bottom5": pass_t_bot},
        "team_rush": {"top10": rush_t_top, "bottom5": rush_t_bot},
        "points_for": {"top10": pf_top, "bottom5": pf_bot},
        "points_against": {"top10": pa_top, "bottom5": pa_bot},
        "expected_wins": {"top10": wins_top, "bottom5": wins_bot},
        "receiving_yards": {"top10": rec_yd_top, "bottom5": rec_yd_bot},
        "rush_yards": {"top10": rush_yd_top, "bottom5": rush_yd_bot},
        "rec_tds": {"top10": rec_td_top},
        "rush_tds": {"top10": rush_td_top},
        "pass_yards": {"top10": pass_yd_top, "bottom5": pass_yd_bot},
        "pass_tds": {"top10": pass_td_top},
    }
    (out_bundle / "leaders.json").write_text(json.dumps(leaders, indent=2) + "\n", encoding="utf-8")

    run_summary = {
        "engine_version": engine,
        "generated_at_utc": generated,
        "n_team_sims": n_team,
        "n_player_sims": n_player,
        "step": "100k_expert_sim_candidate",
        "source_research": str(source.relative_to(ROOT)),
        "locked_snapshot": False,
        "status": "NOT_LOCKED_AWAITING_CLEARANCE",
        "note": "100k expert-sim candidate — NOT LOCKED — awaiting explicit clearance",
        "timing_seconds": timing,
        "runtime_seconds_total": round(runtime_s, 1),
        "conservation": {
            "pass_pool": round(sum(after_pass.values()), 1),
            "rush_pool": round(sum(after_rush.values()), 1),
            "rec_pool": round(sum(after_rec.values()), 1),
            "max_rec_pass_gap_pct": round(max_rec_gap * 100, 3),
            "scheme_pass": {t: round(after_pass[t], 1) for t in LOCKED_PASS_SCHEME_TEAMS},
            "league_pf": round(league_pf, 2),
            "league_pa": round(league_pa, 2),
            "wins_sum": round(wins_sum, 4),
            "wins_min": round(wins_min, 4),
            "wins_max": round(wins_max, 4),
            "wins_range": round(win_range, 4),
        },
        "cin": {
            "pass_yards": round(after_pass["CIN"], 1),
            "points_for": round(cin.points_for, 2),
            "points_against": round(cin.points_against, 2),
            "expected_wins": round(cin.expected_wins, 4),
            "burrow_pass_yards": round(_f(burrow, "pass_yards_total"), 1) if burrow else None,
            "burrow_pass_tds": round(_f(burrow, "pass_tds_total"), 2) if burrow else None,
        },
        "jsn": {
            "rank": jsn_rank,
            "yards": round(_f(jsn, "receiving_yards_total"), 1) if jsn else None,
            "rec_tds": round(_f(jsn, "rec_tds_total"), 2) if jsn else None,
            "team": jsn.get("team") if jsn else None,
        },
        "chase": {
            "rank": chase_rank,
            "yards": round(_f(chase, "receiving_yards_total"), 1) if chase else None,
            "rec_tds": round(_f(chase, "rec_tds_total"), 2) if chase else None,
            "team": chase.get("team") if chase else None,
        },
        "nacua": {
            "rank": nacua_rank,
            "yards": round(_f(nacua, "receiving_yards_total"), 1) if nacua else None,
            "rec_tds": round(_f(nacua, "rec_tds_total"), 2) if nacua else None,
            "team": nacua.get("team") if nacua else None,
        },
        "top_rbs": top5_rbs,
        "soft_flags": soft_flags,
        "label_issues": label_issues,
        "label_fixes": label_audit.get("fixes"),
        "gates": gates,
        "audits": {
            "offense_lift": {
                "rush_pool_after": off_lift_audit.get("rush_pool_after"),
                "method": off_lift_audit.get("method"),
            },
            "alpha": {
                "alpha_players": (alpha_audit.get("sticky") or alpha_audit).get("alpha_players")
                if isinstance(alpha_audit, dict)
                else None
            },
            "pass_tds": {"teams_lifted": td_audit.get("teams_lifted")},
            "rb_priors": {"rush_pool": rb_audit.get("rush_pool"), "top_rb": rb_audit.get("top_rb")},
            "defense": {
                "league_pf": def_audit.get("league_pf"),
                "league_pa": def_audit.get("league_pa"),
                "wins_sum": def_audit.get("wins_sum"),
                "offense_pf_variance_lift": def_audit.get("offense_pf_variance_lift"),
            },
        },
        "pf_win_half_overlap": pf_win_overlap,
        "all_gates_pass": all(gates.values()),
    }
    (out_bundle / "run_summary.json").write_text(json.dumps(run_summary, indent=2) + "\n", encoding="utf-8")
    (out_bundle / "quality_checks.json").write_text(
        json.dumps(
            {
                "gates": gates,
                "soft_flags": soft_flags,
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

    ops_note = ROOT / f"data/ops/nfl-100k-expert-sim-candidate-{day}.md"
    soft_block = "\n".join(f"- {s}" for s in soft_flags) if soft_flags else "- (none material)"
    label_block = (
        "\n".join(f"- {x}" for x in (label_audit.get("fixes") or [])[:20]) or "- (none; depth chart clean)"
    )
    if label_issues:
        label_block += "\n" + "\n".join(f"- ISSUE: {x}" for x in label_issues)

    def _alpha_line(name: str, payload: Dict[str, Any]) -> str:
        return (
            f"- **{name}**: rank={payload.get('rank')}, "
            f"yds={payload.get('yards')}, TDs={payload.get('rec_tds')}, "
            f"team={payload.get('team')}"
        )

    rb_lines = "\n".join(
        f"| {x['rank']} | {x['player']} | {x['team']} | {x['rush_yards']:.0f} | {x['rush_tds']:.1f} |"
        for x in top5_rbs
    )
    gate_lines = "\n".join(
        f"| {k} | {'**PASS**' if v else '**FAIL**'} |" for k, v in gates.items()
    )

    ops_note.write_text(
        f"""# NFL 100k Expert-Sim Candidate — {day}

Engine: `{engine}`  
Source research: `{source.relative_to(ROOT)}`  
Web bundle: `{out_bundle.name}`  
N team / player: **{n_team:,}** / **{n_player:,}**  
Runtime (sim): team {float(timing.get('team_wl') or 0)/60:.1f}m · player {float(timing.get('player_full') or 0)/60:.1f}m · total ~{runtime_s/60:.1f}m

## Status

**NOT LOCKED — awaiting clearance**

Do not tag official baseline. `locked_snapshot: false`. No merge to deploy-vercel as official until explicit lock.

## Conservation

| Check | Value |
|-------|------:|
| Pass pool | {sum(after_pass.values()):.1f} |
| Rush pool | {sum(after_rush.values()):.1f} |
| Rec≈pass max gap | {max_rec_gap*100:.3f}% |
| ARI/BAL/SEA pass | { {t: round(after_pass[t], 1) for t in LOCKED_PASS_SCHEME_TEAMS} } |
| League PF / PA | {league_pf:.1f} / {league_pa:.1f} |
| Wins Σ / min / max / range | {wins_sum:.2f} / {wins_min:.2f} / {wins_max:.2f} / {win_range:.2f} |

## Team leaders (top 10 / bottom 5)

### Pass yards
| Rank | Team | Yards |
|-----:|------|------:|
{_fmt_tb(pass_t_top, with_team=False)}

Bottom 5:
| Rank | Team | Yards |
|-----:|------|------:|
{_fmt_tb(pass_t_bot, with_team=False)}

### Rush yards
| Rank | Team | Yards |
|-----:|------|------:|
{_fmt_tb(rush_t_top, with_team=False)}

Bottom 5:
| Rank | Team | Yards |
|-----:|------|------:|
{_fmt_tb(rush_t_bot, with_team=False)}

### Points for
| Rank | Team | PF |
|-----:|------|---:|
{_fmt_tb(pf_top, with_team=False)}

Bottom 5:
| Rank | Team | PF |
|-----:|------|---:|
{_fmt_tb(pf_bot, with_team=False)}

### Points against
| Rank | Team | PA |
|-----:|------|---:|
{_fmt_tb(pa_top, with_team=False)}

Bottom 5:
| Rank | Team | PA |
|-----:|------|---:|
{_fmt_tb(pa_bot, with_team=False)}

### Expected wins
| Rank | Team | Wins |
|-----:|------|-----:|
{_fmt_tb(wins_top, with_team=False)}

Bottom 5:
| Rank | Team | Wins |
|-----:|------|-----:|
{_fmt_tb(wins_bot, with_team=False)}

## Individual leaders

### Receiving yards (top 10 / bottom 5)
| Rank | Player | Team | Yards |
|-----:|--------|------|------:|
{_fmt_tb(rec_yd_top)}

Bottom 5:
| Rank | Player | Team | Yards |
|-----:|--------|------|------:|
{_fmt_tb(rec_yd_bot)}

### Rush yards
| Rank | Player | Team | Yards |
|-----:|--------|------|------:|
{_fmt_tb(rush_yd_top)}

Bottom 5:
| Rank | Player | Team | Yards |
|-----:|--------|------|------:|
{_fmt_tb(rush_yd_bot)}

### Rec TDs (top 10)
| Rank | Player | Team | TDs |
|-----:|--------|------|----:|
{_fmt_tb(rec_td_top)}

### Rush TDs (top 10)
| Rank | Player | Team | TDs |
|-----:|--------|------|----:|
{_fmt_tb(rush_td_top)}

### Pass yards
| Rank | Player | Team | Yards |
|-----:|--------|------|------:|
{_fmt_tb(pass_yd_top)}

### Pass TDs
| Rank | Player | Team | TDs |
|-----:|--------|------|----:|
{_fmt_tb(pass_td_top)}

## Alpha call-outs

{_alpha_line('JSN', run_summary['jsn'])}
{_alpha_line("Ja'Marr Chase", run_summary['chase'])}
{_alpha_line('Puka Nacua', run_summary['nacua'])}

### Top 5 RBs
| Rank | Player | Team | Rush yds | Rush TDs |
|-----:|--------|------|---------:|---------:|
{rb_lines}

## CIN check

| | Value |
|--|------:|
| Pass yards | {after_pass['CIN']:.1f} |
| PF / PA | {cin.points_for:.1f} / {cin.points_against:.1f} |
| Wins | {cin.expected_wins:.2f} |
| Burrow pass yds / TDs | {_f(burrow,'pass_yards_total') if burrow else 0:.1f} / {_f(burrow,'pass_tds_total') if burrow else 0:.2f} |

## Depth chart labels

{label_block}

## Soft flags (remaining)

{soft_block}

## Gates

| Check | Result |
|-------|--------|
{gate_lines}
| **ALL** | {'**PASS**' if all(gates.values()) else '**FAIL**'} |

## Method
1. Packaged universe `--force-packaged` with cleaned QB depth (Kyler ARI / McCarthy MIN / Penix ATL / Tua MIA)
2. Launch research: {n_team:,} team W/L + {n_player:,} full player paths (engine `{engine}`)
3. Post: offense variance lift → alpha usage → HV pass-TD floors → soft RB priors → tapered PF/PA + Pythagorean wins Σ=272
4. Constraints held: ~126k pass, ARI/BAL/SEA weights, 64k rush, PF=PA≈11859
5. **NOT LOCKED — awaiting clearance**
""",
        encoding="utf-8",
    )

    # Pointers — locked_snapshot false
    (ROOT / "data/ops/nfl-launch-research-sims-current.md").write_text(
        "\n".join(
            [
                "# NFL launch research sims — current pointer",
                "",
                f"- **Web bundle:** `{out_bundle.name}`",
                f"- **Source research:** `{source.relative_to(ROOT)}`",
                f"- **Engine:** `{engine}`",
                f"- **Team W/L N:** {n_team}",
                f"- **Player full N:** {n_player}",
                f"- **Generated:** {generated}",
                f"- **Identity:** {engine} · N_team={n_team} · {stamp}",
                "- **Note:** 100k expert-sim candidate — **NOT LOCKED — awaiting clearance**",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (ROOT / "data/ops/nfl-web-launch-bundle.json").write_text(
        json.dumps(
            {
                "bundle_id": out_bundle.name,
                "engine_version": engine,
                "n_team_sims": n_team,
                "n_player_sims": n_player,
                "generated_at_utc": generated,
                "source_dir": str(source.relative_to(ROOT)),
                "preseason": True,
                "identity": f"{engine} · N_team={n_team} · {stamp}",
                "note": "100k expert-sim candidate; NOT LOCKED — awaiting clearance",
                "locked_snapshot": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # HD mirror of finalized web bundle if available
    hd = Path("/Volumes/KosEdgeData/clean/nfl/research")
    if hd.is_dir():
        try:
            hd_out = hd / out_bundle.name
            if hd_out.exists():
                shutil.rmtree(hd_out)
            shutil.copytree(out_bundle, hd_out)
            (hd / "CURRENT.md").write_text(
                (ROOT / "data/ops/nfl-launch-research-sims-current.md").read_text(encoding="utf-8")
                + f"\n- **HD mirror:** `{hd_out}`\n",
                encoding="utf-8",
            )
        except OSError as exc:
            print(f"HD mirror skipped ({exc})", flush=True)

    result = {
        "bundle": out_bundle.name,
        "ops_note": ops_note.name,
        "engine": engine,
        "n_team_sims": n_team,
        "n_player_sims": n_player,
        "locked_snapshot": False,
        "gates": gates,
        "soft_flags": soft_flags,
        "conservation": run_summary["conservation"],
        "jsn": run_summary["jsn"],
        "top_rbs": top5_rbs,
        "all_gates_pass": all(gates.values()),
    }
    print(json.dumps(result, indent=2))
    if not all(gates.values()):
        print("FAILED GATES:", [k for k, v in gates.items() if not v], file=sys.stderr)
        return result
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True, help="Launch research out_dir")
    ap.add_argument(
        "--seed-defense",
        type=Path,
        default=SEED_DEFENSE_BUNDLE,
        help="Prior enterprise board for PA/sacks/INT memory",
    )
    ap.add_argument("--stamp", default=None)
    args = ap.parse_args()
    result = finalize(args.source, seed_defense=args.seed_defense.resolve(), stamp=args.stamp)
    return 0 if result.get("all_gates_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
