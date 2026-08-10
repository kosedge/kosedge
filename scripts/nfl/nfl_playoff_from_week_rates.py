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


def recompute_playoff_probs(
    week_rates: Dict[str, Any],
    *,
    n_replicates: int = 20_000,
    seed: int = 20260810,
    schedule: Optional[Dict[str, Dict[str, str]]] = None,
) -> Dict[str, Any]:
    rates = _normalize_week_rates(week_rates)
    games = build_schedule_games(schedule)
    if len(games) < 250:
        raise RuntimeError(f"expected ~272 schedule games, got {len(games)}")

    rng = np.random.default_rng(seed)
    made = {t: 0 for t in CANONICAL_TEAMS}
    div_titles = {t: 0 for t in CANONICAL_TEAMS}
    wins_sum = {t: 0 for t in CANONICAL_TEAMS}

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

    playoff = {t: made[t] / float(n_replicates) for t in CANONICAL_TEAMS}
    division = {t: div_titles[t] / float(n_replicates) for t in CANONICAL_TEAMS}
    expected_wins = {t: wins_sum[t] / float(n_replicates) for t in CANONICAL_TEAMS}

    sum_afc = sum(playoff[t] for t in afc)
    sum_nfc = sum(playoff[t] for t in nfc)
    return {
        "method": "7seed_mc_from_week_win_rates_wall_chart",
        "n_replicates": n_replicates,
        "n_games": len(games),
        "playoff_prob": playoff,
        "division_title_prob": division,
        "expected_wins_check": expected_wins,
        "sanity": {
            "sum_playoff_afc": round(sum_afc, 6),
            "sum_playoff_nfc": round(sum_nfc, 6),
            "sum_playoff_league": round(sum_afc + sum_nfc, 6),
            "sum_expected_wins": round(sum(expected_wins.values()), 6),
            "sum_division_title": round(sum(division.values()), 6),
        },
    }


def apply_playoff_probs_to_team_rows(
    rows: Iterable[Dict[str, Any]],
    recomputed: Dict[str, Any],
    *,
    rewrite_expected_wins: bool = False,
) -> List[Dict[str, Any]]:
    playoff = recomputed["playoff_prob"]
    division = recomputed["division_title_prob"]
    ew = recomputed.get("expected_wins_check") or {}
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
        out.append(new_row)
    return out


def load_week_rates_from_bundle(bundle_dir: Path) -> Dict[str, Any]:
    path = bundle_dir / "team_week_win_rates.json"
    return json.loads(path.read_text(encoding="utf-8"))
