"""Football sanity tables for Phase 1B.

Top/bottom per measurement + representative team-week breakdowns.
Flags rankings that conflict materially with play-level EPA/success.
Not a ratings board. Not ATS.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence

from src.services.ke_football.aggregate import TeamGame
from src.services.ke_football.component_validate import team_game_metric
from src.services.ke_football.validation import ranking_sanity


SANITY_IDS = (
    "ke.off_eff",
    "ke.def_eff",
    "ke.success_native",
    "ke.success_standard",
    "ke.pace",
    "ke.expl",
    "ke.expl_pass",
    "ke.expl_rush",
    "ke.ppo",
    "ke.finish",
    "ke.opp_rate",
    "ke.st",
)


def _team_means(games: Sequence[TeamGame], cid: str, *, min_games: int) -> List[Dict[str, Any]]:
    acc: Dict[str, List[float]] = defaultdict(list)
    n_games: Dict[str, int] = defaultdict(int)
    for g in games:
        n_games[g.team] += 1
        val = team_game_metric(g, cid)
        if val is not None:
            acc[g.team].append(val)
    rows = []
    for team, vals in acc.items():
        if n_games[team] < min_games or not vals:
            continue
        rows.append(
            {
                "team": team,
                "value": sum(vals) / len(vals),
                "n_games": n_games[team],
                "n_obs": len(vals),
            }
        )
    return rows


def _rank_map(rows: Sequence[Dict[str, Any]], *, reverse: bool) -> Dict[str, int]:
    ordered = sorted(rows, key=lambda r: r["value"], reverse=reverse)
    return {r["team"]: i + 1 for i, r in enumerate(ordered)}


def top_bottom(rows: Sequence[Dict[str, Any]], *, k: int, reverse: bool) -> Dict[str, List[Dict[str, Any]]]:
    ordered = sorted(rows, key=lambda r: r["value"], reverse=reverse)
    worst_src = list(reversed(ordered[-k:])) if ordered else []
    return {"best": ordered[:k], "worst": worst_src}


def conflict_flags(
    games: Sequence[TeamGame],
    *,
    sport: str,
    min_games: int,
    k_delta: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Offense-like ranks that disagree with play-level off EPA by a wide margin."""
    delta = k_delta if k_delta is not None else (12 if sport == "nfl" else 40)
    off_rows = _team_means(games, "ke.off_eff", min_games=min_games)
    off_rank = _rank_map(off_rows, reverse=True)
    succ_rows = _team_means(games, "ke.success_native", min_games=min_games)
    succ_rank = _rank_map(succ_rows, reverse=True)
    flags: List[Dict[str, Any]] = []
    for cid, reverse in (
        ("ke.success_native", True),
        ("ke.success_standard", True),
        ("ke.expl", True),
        ("ke.ppo", True),
        ("ke.finish", True),
        ("ke.opp_rate", True),
    ):
        rows = _team_means(games, cid, min_games=min_games)
        ranks = _rank_map(rows, reverse=reverse)
        for team, rnk in ranks.items():
            o = off_rank.get(team)
            if o is None:
                continue
            if abs(rnk - o) >= delta:
                flags.append(
                    {
                        "team": team,
                        "component": cid,
                        "component_rank": rnk,
                        "off_epa_rank": o,
                        "success_rank": succ_rank.get(team),
                        "delta_vs_off_epa": rnk - o,
                        "note": "rank conflict vs play-level off EPA — inspect, do not auto-correct",
                    }
                )
    flags.sort(key=lambda r: -abs(int(r["delta_vs_off_epa"])))
    return flags[:40]


def representative_weeks(
    games: Sequence[TeamGame],
    *,
    teams: Sequence[str],
) -> List[Dict[str, Any]]:
    want = set(teams)
    by_team: Dict[str, List[TeamGame]] = defaultdict(list)
    for g in games:
        if g.team in want:
            by_team[g.team].append(g)
    out = []
    for team in teams:
        rows = sorted(by_team.get(team) or [], key=lambda g: (g.week, g.game_id))
        if not rows:
            continue
        picks = []
        if rows:
            picks.append(rows[0])
        mid = rows[len(rows) // 2]
        if mid not in picks:
            picks.append(mid)
        if rows[-1] not in picks:
            picks.append(rows[-1])
        out.append(
            {
                "team": team,
                "n_games": len(rows),
                "weeks": [
                    {
                        "week": g.week,
                        "game_id": g.game_id,
                        "opponent": g.opponent,
                        "off_epa": g.off_epa,
                        "def_epa": g.def_epa,
                        "success": team_game_metric(g, "ke.success_native"),
                        "expl": team_game_metric(g, "ke.expl"),
                        "pace": team_game_metric(g, "ke.pace"),
                        "ppo": team_game_metric(g, "ke.ppo"),
                        "finish": team_game_metric(g, "ke.finish"),
                        "opp_rate": team_game_metric(g, "ke.opp_rate"),
                        "n_drives": g.n_drives,
                        "n_opp": g.n_opp,
                        "points_source": g.points_source,
                    }
                    for g in picks
                ],
            }
        )
    return out


def build_sanity(
    games: Sequence[TeamGame],
    *,
    sport: str,
    example_teams: Sequence[str],
    min_games: int = 4,
    k: int = 8,
) -> Dict[str, Any]:
    tables: Dict[str, Any] = {}
    for cid in SANITY_IDS:
        if sport != "nfl" and cid == "ke.st":
            continue
        higher = cid != "ke.def_eff"
        rows = _team_means(games, cid, min_games=min_games)
        tables[cid] = {
            "higher_better": higher,
            "min_games": min_games,
            **top_bottom(rows, k=k, reverse=higher),
        }
    # EPA ranking reused from Phase 1 helper (n_games ≥ 4).
    from src.services.ke_football.aggregate import team_week_snapshot

    max_week = max((g.week for g in games), default=0)
    snaps = []
    teams = sorted({g.team for g in games})
    for team in teams:
        snaps.append(
            team_week_snapshot(
                games,
                sport=sport,
                season=games[0].season if games else 0,
                as_of_week=max_week + 1,
                team=team,
            )
        )
    return {
        "sport": sport,
        "min_games": min_games,
        "forbidden": ["ats", "close", "roi", "board_chrome"],
        "epa_ranking": ranking_sanity(snaps, k=k, min_games=min_games),
        "tables": tables,
        "conflicts_vs_off_epa": conflict_flags(games, sport=sport, min_games=min_games),
        "representative_team_weeks": representative_weeks(games, teams=example_teams),
        "production_promote": False,
        "note": "sanity only — not Team Strength, not a public board",
    }
