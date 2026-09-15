"""Point-in-time ADJUSTED opponent EPA (not a fitted model).

Week W consumes only team-games with week < W.
Same-game opponent observations are left out.
No λ, n0, prior blend, or HFA term.
No silent league fill when the opponent has no other book.

#560 joint-ridge remains MODELED research and is not used here.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.services.ke_football.aggregate import TeamGame
from src.services.ke_football.provenance import Layer, adjusted

# OT is excluded from the ADJUSTED target (spec: NFL OT out of modeled EPA;
# CFB adj already drops period >= 5). TeamGame rows may still include OT in
# DERIVED; callers should pass games built from non-OT plays for ADJUSTED.


def _pw(pairs: Sequence[Tuple[float, int]]) -> Optional[float]:
    den = sum(n for _v, n in pairs if n > 0)
    if den <= 0:
        return None
    return sum(v * n for v, n in pairs if n > 0) / den


def exclude_ot_games(games: Sequence[TeamGame]) -> List[TeamGame]:
    """Drop plays in OT from the ADJUSTED book by skipping zero-play leftovers.

    Callers who already filtered OT plays before ``build_team_games`` can
    pass the list through unchanged.
    """
    return [g for g in games if g.off_epa_n > 0 or g.def_epa_n > 0]


def derived_book(
    games: Sequence[TeamGame],
    *,
    as_of_week: int,
    exclude_game_id: Optional[str] = None,
    exclude_team: Optional[str] = None,
) -> Dict[str, Dict[str, Optional[float]]]:
    """Play-weighted DERIVED O/D EPA through week < as_of_week."""
    by_team: Dict[str, List[TeamGame]] = defaultdict(list)
    for g in games:
        if g.week >= as_of_week:
            continue
        if exclude_game_id and g.game_id == exclude_game_id:
            continue
        by_team[g.team].append(g)
    out: Dict[str, Dict[str, Optional[float]]] = {}
    for team, rows in by_team.items():
        if exclude_team and team == exclude_team:
            continue
        out[team] = {
            "off": _pw([(g.off_epa, g.off_epa_n) for g in rows if g.off_epa is not None]),
            "def": _pw([(g.def_epa, g.def_epa_n) for g in rows if g.def_epa is not None]),
            "n_off": float(sum(g.off_epa_n for g in rows)),
            "n_def": float(sum(g.def_epa_n for g in rows)),
            "n_games": float(len(rows)),
        }
    return out


def league_means(book: Dict[str, Dict[str, Optional[float]]]) -> Dict[str, Optional[float]]:
    offs = [(float(v["off"]), int(v["n_off"])) for v in book.values() if v.get("off") is not None]
    defs = [(float(v["def"]), int(v["n_def"])) for v in book.values() if v.get("def") is not None]
    return {"off": _pw(offs), "def": _pw(defs)}


def adjust_team_week(
    games: Sequence[TeamGame],
    *,
    team: str,
    as_of_week: int,
) -> Dict[str, Any]:
    """ADJUSTED off/def EPA for one team at week W.

    For each of the team's games g with week < W:
      opp_def = opponent DERIVED def EPA from *other* games with week < W
      off_adj_g = off_raw_g − (opp_def − league_def)
    Same on defense using opponents' offense.
    Games whose opponent has no other book are skipped (not filled).
    """
    mine = [g for g in games if g.team == team and g.week < as_of_week]
    off_terms: List[Tuple[float, int]] = []
    def_terms: List[Tuple[float, int]] = []
    skipped = 0
    used_games = 0
    details: List[Dict[str, Any]] = []

    for g in mine:
        book = derived_book(games, as_of_week=as_of_week, exclude_game_id=g.game_id)
        league = league_means(book)
        opp = book.get(g.opponent) or {}
        row: Dict[str, Any] = {
            "game_id": g.game_id,
            "week": g.week,
            "opponent": g.opponent,
            "off_raw": g.off_epa,
            "def_raw": g.def_epa,
        }
        if g.off_epa is not None and opp.get("def") is not None and league.get("def") is not None:
            off_adj_g = g.off_epa - (float(opp["def"]) - float(league["def"]))
            off_terms.append((off_adj_g, g.off_epa_n))
            row["off_adj"] = off_adj_g
            row["opp_def_loo"] = opp["def"]
        else:
            row["off_adj"] = None
            row["off_skip"] = "opponent_or_league_def_missing"
            skipped += 1
        if g.def_epa is not None and opp.get("off") is not None and league.get("off") is not None:
            def_adj_g = g.def_epa - (float(opp["off"]) - float(league["off"]))
            def_terms.append((def_adj_g, g.def_epa_n))
            row["def_adj"] = def_adj_g
            row["opp_off_loo"] = opp["off"]
        else:
            row["def_adj"] = None
            row["def_skip"] = "opponent_or_league_off_missing"
        if row.get("off_adj") is not None or row.get("def_adj") is not None:
            used_games += 1
        details.append(row)

    off_adj = _pw(off_terms)
    def_adj = _pw(def_terms)
    method = {
        "id": "ke.opp_adj_epa",
        "layer": Layer.ADJUSTED.value,
        "estimator": "pit_leave_one_game_out_sos",
        "formula": "raw - (opp_other_week_lt_W - league)",
        "not_used": [
            "fit_joint_v2_joint_mu_hfa_n0_ridge",
            "lambda",
            "n0",
            "prior_decay",
            "h_times_plays",
            "issue_562_coefficients",
        ],
        "cutoff": "week < as_of_week",
        "same_game_excluded": True,
    }
    return {
        "team": team,
        "as_of_week": as_of_week,
        "method": method,
        "components": {
            "ke.opp_adj_epa.off": adjusted(
                "ke.opp_adj_epa.off",
                off_adj,
                unit="epa_per_play",
                n=len(off_terms),
                notes=method,
            ).to_dict(),
            "ke.opp_adj_epa.def": adjusted(
                "ke.opp_adj_epa.def",
                def_adj,
                unit="epa_per_play_allowed",
                n=len(def_terms),
                notes=method,
            ).to_dict(),
        },
        "n_team_games": len(mine),
        "n_adjusted_games": used_games,
        "n_skipped_no_opp_book": skipped,
        "games": details,
        "production_promote": False,
        "modeled": False,
    }


def adjust_league(games: Sequence[TeamGame], *, as_of_week: int) -> List[Dict[str, Any]]:
    teams = sorted({g.team for g in games if g.week < as_of_week})
    return [adjust_team_week(games, team=team, as_of_week=as_of_week) for team in teams]


def assert_no_future_week(games: Sequence[TeamGame], *, as_of_week: int) -> None:
    leaked = [g for g in games if g.week >= as_of_week]
    if leaked:
        raise AssertionError(
            f"leakage: {len(leaked)} team-games with week >= {as_of_week}"
        )


def future_week_changes_snapshot(
    games: Sequence[TeamGame],
    *,
    team: str,
    as_of_week: int,
    future_game: TeamGame,
) -> bool:
    """Return True if inserting a week>=W game changes the ADJUSTED book (forbidden)."""
    before = adjust_team_week(games, team=team, as_of_week=as_of_week)
    after = adjust_team_week(list(games) + [future_game], team=team, as_of_week=as_of_week)
    return before["components"] != after["components"]
