"""Rebuild playoff / division-title probs via 7-seed conference selection.

Lowest broken Truth Layer layer for the locked 2026 board was *not* UI rescale:
publish wrote ``P(wins>=9)`` from win histograms (AFC≈7.89, NFC≈5.61). Hierarchical
season paths never applied 7 AFC + 7 NFC seeding.

This module samples regular-season records from ``team_week_win_rates.json`` +
wall-chart schedule structure, then applies the same ``seed_conference`` rule as
``simulate_2026_season.py`` so each path contributes exactly 7 playoff berths
per conference.
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]

# Import after path setup for publish / invariants callers
import sys

sys.path.insert(0, str(ROOT / "services" / "model-service" / "src"))
from services.nfl_canonical_teams import (  # noqa: E402
    CANONICAL_TEAMS,
    CONFERENCE_OF,
    DIVISION_OF,
    canonicalize_team,
)

OPP_RE = re.compile(r"^(?:@|vs)\s+([A-Z]{2,3})$")


def _load_wall_chart() -> Dict[str, Dict[str, str]]:
    path = ROOT / "apps" / "web" / "lib" / "nfl-wall-chart-2026.schedule.json"
    return json.loads(path.read_text(encoding="utf-8"))


def build_schedule_games(
    schedule: Optional[Dict[str, Dict[str, str]]] = None,
) -> List[Tuple[str, str, int]]:
    """Return unique (home, away, week) triples in canonical team codes."""
    chart = schedule or _load_wall_chart()
    games: List[Tuple[str, str, int]] = []
    seen = set()
    for team_raw, weeks in chart.items():
        team = canonicalize_team(team_raw)
        if not team:
            continue
        for week_s, label in weeks.items():
            m = OPP_RE.match(str(label).strip())
            if not m:
                continue
            opp = canonicalize_team(m.group(1))
            if not opp:
                continue
            week = int(week_s)
            if str(label).strip().startswith("@"):
                home, away = opp, team
            else:
                home, away = team, opp
            key = (home, away, week)
            if key in seen:
                continue
            seen.add(key)
            games.append(key)
    games.sort(key=lambda g: (g[2], g[0], g[1]))
    return games


def _normalize_week_rates(raw: Dict[str, Any]) -> Dict[str, Dict[int, float]]:
    out: Dict[str, Dict[int, float]] = {}
    for team_raw, weeks in raw.items():
        team = canonicalize_team(str(team_raw))
        if not team:
            continue
        bucket = out.setdefault(team, {})
        for wk, p in weeks.items():
            try:
                bucket[int(wk)] = float(p)
            except (TypeError, ValueError):
                continue
    return out


def home_win_prob(
    home: str,
    away: str,
    week: int,
    rates: Dict[str, Dict[int, float]],
) -> float:
    hp = rates.get(home, {}).get(week)
    ap = rates.get(away, {}).get(week)
    if hp is not None and ap is not None and hp + ap > 0:
        # Marginal week rates from the same sim should be near-complements;
        # renormalize for numerical drift / bye mismatches.
        return float(hp / (hp + ap))
    if hp is not None:
        return float(min(0.99, max(0.01, hp)))
    if ap is not None:
        return float(min(0.99, max(0.01, 1.0 - ap)))
    return 0.5


def seed_conference(
    rng: np.random.Generator,
    records: Dict[str, int],
    teams: Sequence[str],
) -> List[str]:
    division_winners: List[str] = []
    for div_key in sorted({DIVISION_OF[t] for t in teams}):
        div_teams = [t for t in teams if DIVISION_OF[t] == div_key]
        winner = max(div_teams, key=lambda t: (records[t], rng.random()))
        division_winners.append(winner)
    division_winners.sort(key=lambda t: (-records[t], rng.random()))
    remaining = [t for t in teams if t not in division_winners]
    remaining.sort(key=lambda t: (-records[t], rng.random()))
    wildcards = remaining[:3]
    return division_winners + wildcards


# Logistic slope for strength-based playoff matchups (wins units).
# ~3-win gap → ~P=0.79 favorite at neutral site when beta=0.45.
_STRENGTH_BETA = 0.45
_PLAYOFF_HFA = 0.55  # logit units for higher seed / home


def season_wins_from_rates(rates: Dict[str, Dict[int, float]]) -> Dict[str, float]:
    return {t: float(sum(weeks.values())) for t, weeks in rates.items()}


def rescale_week_rates_to_expected_wins(
    week_rates: Dict[str, Any],
    targets: Dict[str, float],
    *,
    clip: Tuple[float, float] = (0.02, 0.98),
) -> Dict[str, Dict[int, float]]:
    """Scale each team's week win rates so Σ_week p ≈ board expected wins.

    Soft-pile / defense finalize rewrites ``expected_wins`` from PF/PA budgets
    but historically left ``team_week_win_rates.json`` on the hierarchical MC
    path. Playoff Truth Layer then read the stale rates → wins vs playoff/SB
    split (LAR symptom). Align rates to the board wins that production uses.
    """
    rates = _normalize_week_rates(week_rates)
    lo, hi = clip
    out: Dict[str, Dict[int, float]] = {}
    for team in CANONICAL_TEAMS:
        target = float(targets.get(team) or 0.0)
        bucket = dict(rates.get(team) or {})
        if not bucket:
            # Fabricate a flat 17-week profile if rates are missing entirely.
            per = min(hi, max(lo, target / 17.0))
            out[team] = {w: per for w in range(1, 18)}
            continue
        current = sum(bucket.values())
        if current <= 1e-12:
            per = min(hi, max(lo, target / float(len(bucket))))
            scaled = {w: per for w in bucket}
        else:
            factor = target / current
            scaled = {w: float(p) * factor for w, p in bucket.items()}
        # Two-pass soft clip that preserves the target sum when possible.
        for _ in range(4):
            clipped = {w: min(hi, max(lo, p)) for w, p in scaled.items()}
            s = sum(clipped.values())
            if abs(s - target) <= 1e-6 or s <= 1e-12:
                scaled = clipped
                break
            # Nudge unclipped mass toward target.
            free = [w for w, p in clipped.items() if lo < p < hi]
            if not free:
                scaled = clipped
                break
            delta = (target - s) / float(len(free))
            for w in free:
                clipped[w] = min(hi, max(lo, clipped[w] + delta))
            scaled = clipped
        out[team] = {int(w): float(p) for w, p in scaled.items()}
    return out


def strength_win_prob(
    strength_home: float,
    strength_away: float,
    *,
    home_field: bool = True,
    beta: float = _STRENGTH_BETA,
    hfa: float = _PLAYOFF_HFA,
) -> float:
    edge = beta * (float(strength_home) - float(strength_away))
    if home_field:
        edge += hfa
    return float(1.0 / (1.0 + math.exp(-edge)))


def _run_conference_bracket(
    rng: np.random.Generator,
    seeds: Sequence[str],
    strength: Dict[str, float],
) -> str:
    """NFL re-seeding bracket; seeds[0] is #1. Returns conference champion."""
    s1, s2, s3, s4, s5, s6, s7 = seeds

    def play(home: str, away: str) -> str:
        p = strength_win_prob(strength[home], strength[away], home_field=True)
        return home if rng.random() < p else away

    wc1 = play(s2, s7)
    wc2 = play(s3, s6)
    wc3 = play(s4, s5)
    survivors = [(2, wc1), (3, wc2), (4, wc3)]
    survivors_by_seed = sorted(survivors, key=lambda x: x[0])
    lowest_remaining = survivors_by_seed[-1][1]
    others = [s for _seed, s in survivors_by_seed[:-1]]
    div1 = play(s1, lowest_remaining)
    div2 = play(others[0], others[1]) if len(others) == 2 else div1
    if div1 == div2:
        return div1
    # Championship: higher remaining seed hosts.
    seed_of = {s1: 1, s2: 2, s3: 3, s4: 4, s5: 5, s6: 6, s7: 7}
    home, away = (div1, div2) if seed_of.get(div1, 99) <= seed_of.get(div2, 99) else (div2, div1)
    return play(home, away)


def recompute_playoff_probs(
    week_rates: Dict[str, Any],
    *,
    n_replicates: int = 20_000,
    seed: int = 20260810,
    schedule: Optional[Dict[str, Dict[str, str]]] = None,
    run_super_bowl: bool = False,
) -> Dict[str, Any]:
    rates = _normalize_week_rates(week_rates)
    games = build_schedule_games(schedule)
    if len(games) < 250:
        raise RuntimeError(f"expected ~272 schedule games, got {len(games)}")

    rng = np.random.default_rng(seed)
    made = {t: 0 for t in CANONICAL_TEAMS}
    div_titles = {t: 0 for t in CANONICAL_TEAMS}
    wins_sum = {t: 0 for t in CANONICAL_TEAMS}
    sb_wins = {t: 0 for t in CANONICAL_TEAMS}

    home_list = [g[0] for g in games]
    away_list = [g[1] for g in games]
    weeks = [g[2] for g in games]
    probs = np.array(
        [
            home_win_prob(h, a, w, rates)
            for h, a, w in zip(home_list, away_list, weeks)
        ],
        dtype=np.float64,
    )
    # Path strength for playoff games: season win expectancy from aligned rates.
    strength = season_wins_from_rates(rates)
    for t in CANONICAL_TEAMS:
        strength.setdefault(t, 8.5)

    afc = [t for t in CANONICAL_TEAMS if CONFERENCE_OF[t] == "AFC"]
    nfc = [t for t in CANONICAL_TEAMS if CONFERENCE_OF[t] == "NFC"]

    for _ in range(n_replicates):
        draws = rng.random(len(games)) < probs
        records = {t: 0 for t in CANONICAL_TEAMS}
        for i, won_home in enumerate(draws):
            if won_home:
                records[home_list[i]] += 1
            else:
                records[away_list[i]] += 1
        for t in CANONICAL_TEAMS:
            wins_sum[t] += records[t]

        seeds = {
            "AFC": seed_conference(rng, records, afc),
            "NFC": seed_conference(rng, records, nfc),
        }
        for conf_seeds in seeds.values():
            for i, t in enumerate(conf_seeds):
                made[t] += 1
                if i < 4:
                    div_titles[t] += 1

        if run_super_bowl:
            # Path strength = this replicate's win total (not fixed E[wins]),
            # so a 9.7-E[win] team that runs 12-5 in-path can win the SB.
            path_strength = {t: float(records[t]) for t in CANONICAL_TEAMS}
            afc_champ = _run_conference_bracket(rng, seeds["AFC"], path_strength)
            nfc_champ = _run_conference_bracket(rng, seeds["NFC"], path_strength)
            p_afc = strength_win_prob(
                path_strength[afc_champ],
                path_strength[nfc_champ],
                home_field=False,
            )
            sb_winner = afc_champ if rng.random() < p_afc else nfc_champ
            sb_wins[sb_winner] += 1

    playoff = {t: made[t] / float(n_replicates) for t in CANONICAL_TEAMS}
    division = {t: div_titles[t] / float(n_replicates) for t in CANONICAL_TEAMS}
    expected_wins = {t: wins_sum[t] / float(n_replicates) for t in CANONICAL_TEAMS}
    sb_prob = (
        {t: sb_wins[t] / float(n_replicates) for t in CANONICAL_TEAMS}
        if run_super_bowl
        else None
    )

    sum_afc = sum(playoff[t] for t in afc)
    sum_nfc = sum(playoff[t] for t in nfc)
    method = "7seed_mc_from_week_win_rates_wall_chart"
    if run_super_bowl:
        method = "7seed_mc_plus_strength_bracket_sb"
    out: Dict[str, Any] = {
        "method": method,
        "n_replicates": n_replicates,
        "n_games": len(games),
        "playoff_prob": playoff,
        "division_title_prob": division,
        "expected_wins_check": expected_wins,
        "rate_strength": {t: round(strength[t], 4) for t in CANONICAL_TEAMS},
        "sanity": {
            "sum_playoff_afc": round(sum_afc, 6),
            "sum_playoff_nfc": round(sum_nfc, 6),
            "sum_playoff_league": round(sum_afc + sum_nfc, 6),
            "sum_expected_wins": round(sum(expected_wins.values()), 6),
            "sum_division_title": round(sum(division.values()), 6),
        },
    }
    if sb_prob is not None:
        out["super_bowl_win_prob"] = sb_prob
        out["sanity"]["sum_super_bowl"] = round(sum(sb_prob.values()), 6)
    return out


def apply_playoff_probs_to_team_rows(
    rows: Iterable[Dict[str, Any]],
    recomputed: Dict[str, Any],
    *,
    rewrite_expected_wins: bool = False,
    rewrite_super_bowl: bool = False,
) -> List[Dict[str, Any]]:
    playoff = recomputed["playoff_prob"]
    division = recomputed["division_title_prob"]
    ew = recomputed.get("expected_wins_check") or {}
    sb = recomputed.get("super_bowl_win_prob") or {}
    out: List[Dict[str, Any]] = []
    for row in rows:
        team = canonicalize_team(str(row.get("team") or "")) or str(row.get("team") or "")
        new_row = dict(row)
        new_row["team"] = team
        if team in CONFERENCE_OF:
            new_row["conference"] = CONFERENCE_OF[team]
            new_row["division"] = f"{CONFERENCE_OF[team]} {DIVISION_OF[team]}"
        if team in playoff:
            new_row["playoff_prob"] = round(float(playoff[team]), 6)
        if team in division:
            new_row["division_title_prob"] = round(float(division[team]), 6)
        if rewrite_expected_wins and team in ew:
            new_row["expected_wins"] = round(float(ew[team]), 4)
        if rewrite_super_bowl and team in sb:
            new_row["super_bowl_win_prob"] = round(float(sb[team]), 6)
        out.append(new_row)
    return out


def flag_wins_playoff_sb_contradictions(
    rows: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Report-only: wins vs playoff/SB stories that still disagree after align."""
    parsed: List[Dict[str, Any]] = []
    for row in rows:
        team = canonicalize_team(str(row.get("team") or "")) or str(row.get("team") or "")
        parsed.append(
            {
                "team": team,
                "expected_wins": float(row.get("expected_wins") or 0),
                "playoff_prob": float(row.get("playoff_prob") or 0),
                "super_bowl_win_prob": float(row.get("super_bowl_win_prob") or 0),
            }
        )
    flags: List[Dict[str, Any]] = []
    for r in parsed:
        reasons: List[str] = []
        ew, po, sb = r["expected_wins"], r["playoff_prob"], r["super_bowl_win_prob"]
        if ew >= 9.5 and po < 0.35:
            reasons.append("high_wins_low_playoff")
        if ew <= 7.5 and po >= 0.55:
            reasons.append("low_wins_high_playoff")
        if ew >= 9.5 and sb < 0.01:
            reasons.append("high_wins_thin_sb")
        if po >= 0.60 and sb < 0.005:
            reasons.append("high_playoff_thin_sb")
        if reasons:
            flags.append({**r, "reasons": reasons})
    flags.sort(key=lambda x: (-x["expected_wins"], x["team"]))
    return flags


def e_wins_histogram(rows: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    bands = {"<=5": 0, "5-7": 0, "7-10": 0, "10-12": 0, ">=12": 0}
    for row in rows:
        w = float(row.get("expected_wins") or 0)
        if w <= 5:
            bands["<=5"] += 1
        elif w < 7:
            bands["5-7"] += 1
        elif w <= 10:
            bands["7-10"] += 1
        elif w < 12:
            bands["10-12"] += 1
        else:
            bands[">=12"] += 1
    return bands


def load_week_rates_from_bundle(bundle_dir: Path) -> Dict[str, Any]:
    path = bundle_dir / "team_week_win_rates.json"
    return json.loads(path.read_text(encoding="utf-8"))
