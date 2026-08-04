"""Schedule helpers — densify packaged sample toward usable season paths.

There is no official full 2026 FBS schedule feed in-repo. We keep the curated
sample slate as seed matchups, then add synthetic games so packaged FBS teams
get ~target_games across weeks 1–14. Fidelity is always labeled approximate /
densified — never presented as official.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from src.services.cfb_season_engine.conferences import conference_for, load_conference_map
from src.services.cfb_season_engine.types import ScheduledGame

DEFAULT_TARGET_GAMES = 12
DEFAULT_MAX_WEEK = 14


def _game_key(g: ScheduledGame) -> Tuple[str, str, int]:
    a, b = sorted((g.home_team, g.away_team))
    return a, b, int(g.week)


def densify_schedule(
    seed_games: Sequence[ScheduledGame],
    team_codes: Sequence[str],
    *,
    season: int = 2026,
    target_games_per_team: int = DEFAULT_TARGET_GAMES,
    max_week: int = DEFAULT_MAX_WEEK,
    conference_by_team: Optional[Mapping[str, str]] = None,
    strength_by_team: Optional[Mapping[str, float]] = None,
) -> Tuple[List[ScheduledGame], Dict[str, Any]]:
    """Return densified schedule + honesty metadata.

    Algorithm (deterministic):
    1. Keep seed games (deduped).
    2. For weeks 1..max_week, pair idle teams that still need games —
       mix intra-conference with strength-matched cross games so soft
       G5 pods do not dominate season-win leaderboards alone.
    3. Stop when every team hits target or no pairs remain.
    """
    conf = dict(conference_by_team or load_conference_map())
    strength = {str(k).upper(): float(v) for k, v in (strength_by_team or {}).items()}
    teams = sorted({str(t).upper() for t in team_codes})
    if not teams:
        return [], {
            "schedule_source": "empty",
            "fidelity": "placeholder",
            "seed_games": 0,
            "densified_games": 0,
        }

    seen: Set[Tuple[str, str, int]] = set()
    pair_seen: Set[Tuple[str, str]] = set()
    games: List[ScheduledGame] = []
    counts: Dict[str, int] = defaultdict(int)
    busy_week: Dict[int, Set[str]] = defaultdict(set)
    # Soft cap on intra-conference densify games so SOS stays mixed.
    conf_counts: Dict[str, int] = defaultdict(int)
    max_conf_games = max(6, target_games_per_team - 4)

    def _add(game: ScheduledGame) -> bool:
        if game.home_team not in teams or game.away_team not in teams:
            return False
        key = _game_key(game)
        if key in seen:
            return False
        if game.home_team in busy_week[game.week] or game.away_team in busy_week[game.week]:
            return False
        seen.add(key)
        a, b = sorted((game.home_team, game.away_team))
        pair_seen.add((a, b))
        games.append(game)
        counts[game.home_team] += 1
        counts[game.away_team] += 1
        busy_week[game.week].add(game.home_team)
        busy_week[game.week].add(game.away_team)
        return True

    seed_kept = 0
    for g in seed_games:
        if _add(g):
            seed_kept += 1
            hc = conference_for(g.home_team, conf)
            ac = conference_for(g.away_team, conf)
            if hc == ac and hc != "Independent":
                conf_counts[g.home_team] += 1
                conf_counts[g.away_team] += 1

    def _strength(team: str) -> float:
        return strength.get(team, 50.0)

    def _pick_away(home: str, candidates: List[str], *, week: int) -> Optional[str]:
        if not candidates:
            return None
        home_conf = conference_for(home, conf)
        same = [
            a
            for a in candidates
            if conference_for(a, conf) == home_conf
            and tuple(sorted((home, a))) not in pair_seen
            and conf_counts[home] < max_conf_games
            and conf_counts[a] < max_conf_games
        ]
        cross = [
            a
            for a in candidates
            if conference_for(a, conf) != home_conf
            and tuple(sorted((home, a))) not in pair_seen
        ]
        rematch = [a for a in candidates if tuple(sorted((home, a))) in pair_seen]
        # Odd weeks lean conference; even weeks lean strength-matched cross.
        if week % 2 == 1 and same:
            pool = same
            return min(pool, key=lambda t: (counts[t], abs(_strength(t) - _strength(home)), t))
        if cross:
            return min(
                cross,
                key=lambda t: (abs(_strength(t) - _strength(home)), counts[t], t),
            )
        if same:
            return min(same, key=lambda t: (counts[t], t))
        if rematch:
            return min(rematch, key=lambda t: (counts[t], t))
        return None

    synthetic = 0
    cursor = 0
    for week in range(1, max_week + 1):
        needy = [
            t
            for t in teams
            if counts[t] < target_games_per_team and t not in busy_week[week]
        ]
        if len(needy) < 2:
            continue
        start = (cursor + week * 7) % len(needy)
        ordered = needy[start:] + needy[:start]
        used: Set[str] = set()
        for i, home in enumerate(ordered):
            if home in used or counts[home] >= target_games_per_team:
                continue
            candidates = [
                a
                for a in ordered[i + 1 :]
                if a not in used
                and counts[a] < target_games_per_team
                and a not in busy_week[week]
            ]
            away = _pick_away(home, candidates, week=week)
            if away is None:
                continue
            game = ScheduledGame(
                season=season,
                week=week,
                game_id=f"{season}_w{week}_{away}@{home}",
                home_team=home,
                away_team=away,
                neutral_site=False,
            )
            if _add(game):
                synthetic += 1
                used.add(home)
                used.add(away)
                hc = conference_for(home, conf)
                ac = conference_for(away, conf)
                if hc == ac and hc != "Independent":
                    conf_counts[home] += 1
                    conf_counts[away] += 1
        cursor = (cursor + 3) % max(1, len(teams))

    games_sorted = sorted(games, key=lambda g: (g.week, g.game_id))
    played = [counts[t] for t in teams]
    meta = {
        "schedule_source": "packaged_sample_densified",
        "fidelity": "approximate",
        "official_schedule": False,
        "seed_games_kept": seed_kept,
        "densified_added": synthetic,
        "total_games": len(games_sorted),
        "team_count": len(teams),
        "target_games_per_team": target_games_per_team,
        "games_per_team_min": min(played) if played else 0,
        "games_per_team_max": max(played) if played else 0,
        "games_per_team_mean": round(sum(played) / len(played), 3) if played else 0.0,
        "note": (
            "Densified synthetic slate from packaged sample seed — NOT the "
            "official 2026 FBS schedule. Usable for path-coherent season sims."
        ),
    }
    return games_sorted, meta


def documentation() -> Dict[str, Any]:
    return {
        "module": "src.services.cfb_season_engine.schedule",
        "role": "densify packaged sample toward usable season paths",
        "fidelity": "approximate / densified (not official)",
        "defaults": {
            "target_games_per_team": DEFAULT_TARGET_GAMES,
            "max_week": DEFAULT_MAX_WEEK,
        },
    }
