"""CFB futures from OUR season paths — not an invented ESPN bracket.

Assumptions (explicit, 2026)
----------------------------
- Field: 12-team CFP.
- Auto bids: 5 highest-ranked conference champions (any conference with a
  champion = team with most conference wins on that path; Independents cannot
  be conference champions).
- At-large: next 7 teams by ranking not already in.
- Ranking on a path: regular-season wins, then power_index, then team code.
- Byes: seeds 1–4. First round 5v12, 6v11, 7v10, 8v9. Neutral-site playoff
  games use project_game WP (or power-index logistic if project_game missing).
- Conference title: most conference wins in that conference on the path
  (tiebreak: total wins, then power).
- G5: a G5 champion can take an auto bid if they are one of the top-5
  conference champions by rank. Otherwise they are at-large only.
- Preseason mass is wide — publish percents to 1 decimal for N≥1000, else
  integer percent / rank tiers.

This is sim-derived. Not book prices.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_season_engine.conferences import conference_for

FUTURES_VERSION = "cfb-futures-v1-cfp12-2026"
CFP_FIELD = 12
AUTO_BIDS = 5
AT_LARGE = 7
BYE_SEEDS = 4
POWER4 = frozenset({"SEC", "Big Ten", "ACC", "Big 12"})
G5 = frozenset(
    {"AAC", "Mountain West", "Sun Belt", "MAC", "CUSA", "Pac-12", "Conference USA"}
)

ROUND_PAIRINGS = ((5, 12), (6, 11), (7, 10), (8, 9))


def _power(team: str, power: Mapping[str, float]) -> float:
    return float(power.get(team, 0.0) or 0.0)


def _rank_key(
    team: str,
    wins: Mapping[str, float],
    power: Mapping[str, float],
) -> Tuple[float, float, str]:
    return (float(wins.get(team, 0.0)), _power(team, power), team)


def conference_champions(
    *,
    teams: Sequence[str],
    conf_wins: Mapping[str, float],
    wins: Mapping[str, float],
    conferences: Mapping[str, str],
    power: Mapping[str, float],
) -> Dict[str, str]:
    """Best team per conference (Independents excluded)."""
    by_conf: Dict[str, List[str]] = defaultdict(list)
    for team in teams:
        conf = conference_for(team, conferences)
        if not conf or conf == "Independent":
            continue
        by_conf[conf].append(team)
    champs: Dict[str, str] = {}
    for conf, members in by_conf.items():
        champs[conf] = max(
            members,
            key=lambda t: (
                float(conf_wins.get(t, 0.0)),
                float(wins.get(t, 0.0)),
                _power(t, power),
                t,
            ),
        )
    return champs


def select_cfp_field(
    *,
    teams: Sequence[str],
    wins: Mapping[str, float],
    conf_wins: Mapping[str, float],
    conferences: Mapping[str, str],
    power: Mapping[str, float],
) -> List[str]:
    ranked = sorted(teams, key=lambda t: _rank_key(t, wins, power), reverse=True)
    champs = conference_champions(
        teams=teams,
        conf_wins=conf_wins,
        wins=wins,
        conferences=conferences,
        power=power,
    )
    champ_rank = {team: i for i, team in enumerate(ranked)}
    auto = sorted(champs.values(), key=lambda t: champ_rank.get(t, 10_000))[:AUTO_BIDS]
    field: List[str] = []
    seen = set()
    for team in auto:
        if team not in seen:
            field.append(team)
            seen.add(team)
    for team in ranked:
        if team in seen:
            continue
        field.append(team)
        seen.add(team)
        if len(field) >= CFP_FIELD:
            break
    # Re-seed by ranking
    return sorted(field, key=lambda t: _rank_key(t, wins, power), reverse=True)


def _playoff_wp(home: str, away: str, power: Mapping[str, float]) -> float:
    """Neutral-site logistic from power_index gap. Not a book line."""
    gap = _power(home, power) - _power(away, power)
    # power_index is ~0.7–1.7; 0.25 gap ≈ a decent favorite.
    z = 2.1 * gap
    return max(0.08, min(0.92, 1.0 / (1.0 + math.exp(-z))))


def simulate_playoff(
    seeds: Sequence[str],
    *,
    rng: random.Random,
    power: Mapping[str, float],
) -> str:
    if not seeds:
        return ""
    if len(seeds) == 1:
        return seeds[0]
    by_seed = {i + 1: seeds[i] for i in range(min(len(seeds), CFP_FIELD))}
    winners: List[str] = [by_seed[i] for i in range(1, BYE_SEEDS + 1) if i in by_seed]
    for hi, lo in ROUND_PAIRINGS:
        a = by_seed.get(hi)
        b = by_seed.get(lo)
        if not a or not b:
            continue
        wp = _playoff_wp(a, b, power)
        winners.append(a if rng.random() < wp else b)
    # Quarters: 4 byes + 4 first-round winners, keep seed order among remaining
    remaining = winners
    while len(remaining) > 1:
        nxt: List[str] = []
        for i in range(0, len(remaining) - 1, 2):
            a, b = remaining[i], remaining[i + 1]
            wp = _playoff_wp(a, b, power)
            nxt.append(a if rng.random() < wp else b)
        if len(remaining) % 2 == 1:
            nxt.append(remaining[-1])
        remaining = nxt
    return remaining[0]


def accumulate_path(
    *,
    counts: Dict[str, Dict[str, int]],
    teams: Sequence[str],
    wins: Mapping[str, float],
    conf_wins: Mapping[str, float],
    conferences: Mapping[str, str],
    power: Mapping[str, float],
    rng: random.Random,
) -> None:
    field = select_cfp_field(
        teams=teams,
        wins=wins,
        conf_wins=conf_wins,
        conferences=conferences,
        power=power,
    )
    for team in field:
        counts["cfp"][team] += 1
    champ = simulate_playoff(field, rng=rng, power=power)
    if champ:
        counts["natty"][champ] += 1
    conf_champs = conference_champions(
        teams=teams,
        conf_wins=conf_wins,
        wins=wins,
        conferences=conferences,
        power=power,
    )
    for conf, team in conf_champs.items():
        counts["conf"][f"{conf}::{team}"] += 1


def finalize_futures(
    *,
    n_sims: int,
    teams: Sequence[str],
    conferences: Mapping[str, str],
    power: Mapping[str, float],
    counts: Mapping[str, Mapping[str, int]],
    engine_version: str,
    as_of: str,
) -> Dict[str, Any]:
    n = max(int(n_sims), 1)
    decimals = 1 if n >= 1000 else 0

    def pct(hits: int) -> float:
        raw = 100.0 * hits / n
        return round(raw, decimals)

    rows: List[Dict[str, Any]] = []
    for team in teams:
        conf = conference_for(team, conferences)
        cfp_hits = int(counts["cfp"].get(team, 0))
        natty_hits = int(counts["natty"].get(team, 0))
        conf_hits = int(counts["conf"].get(f"{conf}::{team}", 0)) if conf != "Independent" else 0
        rows.append(
            {
                "team": team,
                "conference": conf,
                "power_index": round(_power(team, power), 4),
                "cfp_make_pct": pct(cfp_hits),
                "natty_pct": pct(natty_hits),
                "conf_title_pct": pct(conf_hits) if conf != "Independent" else None,
                "cfp_hits": cfp_hits,
                "natty_hits": natty_hits,
                "conf_title_hits": conf_hits,
                "g5": conf in G5,
                "power4": conf in POWER4,
            }
        )
    rows.sort(key=lambda r: (r["natty_pct"], r["cfp_make_pct"], r["power_index"]), reverse=True)
    for i, row in enumerate(rows, start=1):
        row["rank"] = i

    conf_titles: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        conf = row["conference"]
        if not conf or conf == "Independent" or row["conf_title_pct"] is None:
            continue
        if row["conf_title_hits"] <= 0:
            continue
        conf_titles[conf].append(
            {
                "team": row["team"],
                "conf_title_pct": row["conf_title_pct"],
                "cfp_make_pct": row["cfp_make_pct"],
            }
        )
    for conf in conf_titles:
        conf_titles[conf].sort(key=lambda r: r["conf_title_pct"], reverse=True)

    return {
        "ok": True,
        "futures_version": FUTURES_VERSION,
        "engine_version": engine_version,
        "as_of": as_of,
        "n_sims": n,
        "cfp_field": CFP_FIELD,
        "auto_bids": AUTO_BIDS,
        "at_large": AT_LARGE,
        "bye_seeds": BYE_SEEDS,
        "method": (
            "Path-level ranking (wins, power_index) → 12-team CFP "
            "(5 conference champs + 7 at-large) → neutral-site playoff WP from power gap. "
            "Sim-derived. Not book prices. Not an ESPN bracket copy."
        ),
        "assumptions": {
            "cfp_field": CFP_FIELD,
            "auto_bids": AUTO_BIDS,
            "independents": "at-large only",
            "g5": "G5 champ can take an auto bid if among the top-5 conference champs by rank",
            "playoff_wp": "logistic of power_index gap, neutral",
            "precision": "1 decimal when N>=1000 else integer percent",
        },
        "used_in_spread": False,
        "kei": False,
        "research_only": True,
        "teams": rows,
        "conference_titles": dict(conf_titles),
        "top_natty": rows[:10],
        "top_cfp": sorted(rows, key=lambda r: r["cfp_make_pct"], reverse=True)[:10],
    }
