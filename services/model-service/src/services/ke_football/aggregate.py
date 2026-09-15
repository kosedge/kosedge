"""Team-game and team-week snapshots (DERIVED components)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from src.services.ke_football.adapters import is_explosive, play_standard_success
from src.services.ke_football.disruption import (
    audit_disruption_columns,
    event_rate,
    havoc_component,
    nfl_proxy_rate,
)
from src.services.ke_football.plays import CanonicalPlay
from src.services.ke_football.provenance import (
    CLOCK_NULL_MAX,
    EPA_NULL_PARTIAL,
    SCORE_DIFF_NULL_MAX,
    THIN_DRIVES_GAME,
    THIN_GAMES_STD,
    THIN_OPPORTUNITIES_STD,
    THIN_PASS_SPLIT,
    THIN_PLAYS_STD,
    THIN_RUSH_SPLIT,
    THIN_ST_PLAYS,
    Component,
    Status,
    derived,
    omitted,
)

COMPETITIVE_MARGIN = 16
OPP_YTE = 40
RZ_YTE = 20


def filter_week_lt(plays: Iterable[CanonicalPlay], *, season: int, as_of_week: int) -> List[CanonicalPlay]:
    """Strict PIT: same season, week < as_of_week. Unprovable weeks dropped."""
    out: List[CanonicalPlay] = []
    for play in plays:
        if play.season != season:
            continue
        if play.week < 1:
            continue
        if play.week >= as_of_week:
            continue
        out.append(play)
    return out


def _mean(xs: Sequence[float]) -> Optional[float]:
    if not xs:
        return None
    return sum(xs) / len(xs)


def _rate(n: float, d: float) -> Optional[float]:
    if d <= 0:
        return None
    return n / d


@dataclass
class TeamGame:
    sport: str
    season: int
    week: int
    game_id: str
    team: str
    opponent: str
    home: bool
    n_off_plays: int = 0
    n_def_plays: int = 0
    off_epa_sum: float = 0.0
    def_epa_sum: float = 0.0
    off_epa_n: int = 0
    def_epa_n: int = 0
    off_epa_null: int = 0
    def_epa_null: int = 0
    success_n: int = 0
    success_d: int = 0
    success_allowed_n: int = 0
    success_allowed_d: int = 0
    std_n: int = 0
    std_d: int = 0
    expl_n: int = 0
    expl_d: int = 0
    expl_pass_n: int = 0
    expl_pass_d: int = 0
    expl_rush_n: int = 0
    expl_rush_d: int = 0
    expl_allowed_n: int = 0
    expl_allowed_d: int = 0
    pass_epa_sum: float = 0.0
    pass_epa_n: int = 0
    rush_epa_sum: float = 0.0
    rush_epa_n: int = 0
    early_epa_sum: float = 0.0
    early_epa_n: int = 0
    early_succ_n: int = 0
    early_succ_d: int = 0
    comp_plays: int = 0
    score_diff_known: int = 0
    clock_known: int = 0
    clock_deltas: List[float] = field(default_factory=list)
    st_epa_sum: float = 0.0
    st_n: int = 0
    n_drives: int = 0
    n_opp: int = 0
    n_rz: int = 0
    opp_points: int = 0
    finished_opp: int = 0
    rz_td: int = 0
    rz_plays: int = 0
    drive_ids_missing: int = 0
    off_plays: List[CanonicalPlay] = field(default_factory=list)
    def_plays: List[CanonicalPlay] = field(default_factory=list)

    @property
    def off_epa(self) -> Optional[float]:
        return _rate(self.off_epa_sum, self.off_epa_n)

    @property
    def def_epa(self) -> Optional[float]:
        return _rate(self.def_epa_sum, self.def_epa_n)


def _drive_key(play: CanonicalPlay) -> Optional[Tuple[str, str, str]]:
    if not play.drive_id:
        return None
    return (play.game_id, play.drive_id, play.offense)


def build_team_games(plays: Sequence[CanonicalPlay]) -> List[TeamGame]:
    games: Dict[Tuple[str, int, int, str, str, str], TeamGame] = {}

    def slot(play: CanonicalPlay, team: str, opp: str) -> TeamGame:
        key = (play.sport, play.season, play.week, play.game_id, team, opp)
        if key not in games:
            home = bool(play.home and team == play.home)
            games[key] = TeamGame(
                sport=play.sport,
                season=play.season,
                week=play.week,
                game_id=play.game_id,
                team=team,
                opponent=opp,
                home=home,
            )
        return games[key]

    for play in plays:
        if play.is_scrimmage:
            off = slot(play, play.offense, play.defense)
            deff = slot(play, play.defense, play.offense)
            off.n_off_plays += 1
            deff.n_def_plays += 1
            off.off_plays.append(play)
            deff.def_plays.append(play)
            if play.epa is None:
                off.off_epa_null += 1
                deff.def_epa_null += 1
            else:
                off.off_epa_sum += play.epa
                off.off_epa_n += 1
                deff.def_epa_sum += play.epa
                deff.def_epa_n += 1
            if play.success_native is not None:
                off.success_d += 1
                deff.success_allowed_d += 1
                if play.success_native:
                    off.success_n += 1
                    deff.success_allowed_n += 1
            std = play_standard_success(play)
            if std is not None:
                off.std_d += 1
                if std:
                    off.std_n += 1
            expl_ok = play.epa is not None or play.yards is not None
            if expl_ok:
                off.expl_d += 1
                deff.expl_allowed_d += 1
                if is_explosive(play):
                    off.expl_n += 1
                    deff.expl_allowed_n += 1
            if play.is_pass:
                off.expl_pass_d += 1
                if is_explosive(play):
                    off.expl_pass_n += 1
                if play.epa is not None:
                    off.pass_epa_sum += play.epa
                    off.pass_epa_n += 1
            if play.is_rush:
                off.expl_rush_d += 1
                if is_explosive(play):
                    off.expl_rush_n += 1
                if play.epa is not None:
                    off.rush_epa_sum += play.epa
                    off.rush_epa_n += 1
            if play.down is not None and int(play.down) in (1, 2):
                off.early_epa_n += 1
                if play.epa is not None:
                    off.early_epa_sum += play.epa
                if play.success_native is not None:
                    off.early_succ_d += 1
                    if play.success_native:
                        off.early_succ_n += 1
            if play.score_diff is not None:
                off.score_diff_known += 1
                if abs(play.score_diff) < COMPETITIVE_MARGIN:
                    off.comp_plays += 1
            if play.game_seconds_remaining is not None:
                off.clock_known += 1
            if play.yards_to_endzone is not None and play.yards_to_endzone <= RZ_YTE:
                off.rz_plays += 1
                if play.touchdown is True:
                    off.rz_td += 1
        if play.is_st and play.sport == "nfl" and play.epa is not None:
            st = slot(play, play.offense, play.defense)
            st.st_epa_sum += play.epa
            st.st_n += 1

    # Drive finishing (offense side).
    by_drive: Dict[Tuple[str, str, str], List[CanonicalPlay]] = defaultdict(list)
    missing_drive = defaultdict(int)
    for play in plays:
        key = _drive_key(play)
        if key is None:
            if play.is_scrimmage:
                missing_drive[(play.sport, play.season, play.week, play.game_id, play.offense)] += 1
            continue
        by_drive[key].append(play)

    for (gid, _did, off), group in by_drive.items():
        first = group[0]
        tg = None
        for play in group:
            tg = games.get((play.sport, play.season, play.week, gid, off, play.defense))
            if tg:
                break
        if tg is None:
            continue
        tg.n_drives += 1
        reached_40 = False
        reached_rz = False
        points = 0
        for play in group:
            if play.yards_to_endzone is not None and play.yards_to_endzone <= OPP_YTE:
                reached_40 = True
            if play.yards_to_endzone is not None and play.yards_to_endzone <= RZ_YTE:
                reached_rz = True
            if play.extra.get("rz_play") is True:
                reached_40 = True
                reached_rz = True
            points += int(play.points or 0)
        if reached_40:
            tg.n_opp += 1
            tg.opp_points += points
            if points > 0:
                tg.finished_opp += 1
        if reached_rz:
            tg.n_rz += 1

    for key, nmiss in missing_drive.items():
        # key without opponent — stamp any matching team-game
        sport, season, week, gid, team = key
        for tg in games.values():
            if (
                tg.sport == sport
                and tg.season == season
                and tg.week == week
                and tg.game_id == gid
                and tg.team == team
            ):
                tg.drive_ids_missing += nmiss

    # Clock deltas: consecutive scrimmage on same drive.
    for group in by_drive.values():
        ordered = sorted(
            [p for p in group if p.is_scrimmage],
            key=lambda p: (p.period or 0, -(p.game_seconds_remaining or 0), p.play_id),
        )
        prev = None
        for play in ordered:
            if (
                prev is not None
                and play.game_seconds_remaining is not None
                and prev.game_seconds_remaining is not None
            ):
                delta = prev.game_seconds_remaining - play.game_seconds_remaining
                if 0 < delta <= 80:
                    tg = games.get(
                        (play.sport, play.season, play.week, play.game_id, play.offense, play.defense)
                    )
                    if tg:
                        tg.clock_deltas.append(delta)
            prev = play

    return list(games.values())


def _epa_partial(nulls: int, n: int) -> bool:
    if n + nulls <= 0:
        return False
    return (nulls / (n + nulls)) > EPA_NULL_PARTIAL


def team_game_components(tg: TeamGame) -> Dict[str, Component]:
    off_partial = _epa_partial(tg.off_epa_null, tg.off_epa_n)
    def_partial = _epa_partial(tg.def_epa_null, tg.def_epa_n)
    comps: Dict[str, Component] = {
        "ke.off_eff": derived(
            "ke.off_eff",
            tg.off_epa,
            unit="epa_per_play",
            n=tg.off_epa_n,
            thin_n=1,
            partial=off_partial,
            notes={"higher_better": True},
        ),
        "ke.def_eff": derived(
            "ke.def_eff",
            tg.def_epa,
            unit="epa_per_play_allowed",
            n=tg.def_epa_n,
            thin_n=1,
            partial=def_partial,
            notes={"lower_better": True},
        ),
        "ke.success_native": derived(
            "ke.success_native",
            _rate(tg.success_n, tg.success_d),
            unit="rate",
            n=tg.success_d,
        ),
        "ke.success_standard": derived(
            "ke.success_standard",
            _rate(tg.std_n, tg.std_d),
            unit="rate",
            n=tg.std_d,
        ),
        "ke.success_allowed": derived(
            "ke.success_allowed",
            _rate(tg.success_allowed_n, tg.success_allowed_d),
            unit="rate",
            n=tg.success_allowed_d,
        ),
        "ke.pace": derived(
            "ke.pace",
            float(tg.n_off_plays) if tg.n_off_plays else None,
            unit="plays_per_offense_game",
            n=tg.n_off_plays,
        ),
        "ke.pace_competitive": derived(
            "ke.pace_competitive",
            float(tg.comp_plays) if tg.n_off_plays else None,
            unit="plays_per_offense_game",
            n=tg.comp_plays,
            notes={"margin": COMPETITIVE_MARGIN},
            required=tg.n_off_plays > 0
            and (tg.score_diff_known / tg.n_off_plays) >= (1 - SCORE_DIFF_NULL_MAX)
            if tg.n_off_plays
            else False,
        ),
    }

    clock_null = 1.0
    if tg.n_off_plays:
        clock_null = 1.0 - (tg.clock_known / tg.n_off_plays)
    if clock_null > CLOCK_NULL_MAX:
        comps["ke.pace_seconds"] = derived(
            "ke.pace_seconds",
            None,
            unit="seconds_per_play",
            n=0,
            missing_fields=["game_seconds_remaining"],
            notes={"clock_null_rate": clock_null, "threshold": CLOCK_NULL_MAX},
        )
    else:
        comps["ke.pace_seconds"] = derived(
            "ke.pace_seconds",
            _mean(tg.clock_deltas),
            unit="seconds_per_play",
            n=len(tg.clock_deltas),
        )

    rush_missing = tg.expl_rush_d == 0 and tg.expl_pass_d > 0
    comps["ke.expl_pass"] = derived(
        "ke.expl_pass",
        _rate(tg.expl_pass_n, tg.expl_pass_d),
        unit="rate",
        n=tg.expl_pass_d,
        thin_n=THIN_PASS_SPLIT,
        notes={"nfl_knob": "pass>=20", "cfb_knob": "EPA>=1 or yards>=15"},
    )
    comps["ke.expl_rush"] = derived(
        "ke.expl_rush",
        _rate(tg.expl_rush_n, tg.expl_rush_d),
        unit="rate",
        n=tg.expl_rush_d,
        thin_n=THIN_RUSH_SPLIT,
        notes={"nfl_knob": "rush>=10", "cfb_knob": "EPA>=1 or yards>=15"},
    )
    if rush_missing:
        expl = derived(
            "ke.expl",
            None,
            unit="rate",
            n=tg.expl_d,
            required=False,
            missing_fields=["ke.expl_rush"],
            notes={"rule": "do not publish combined expl as complete without rush split"},
        )
        expl.status = Status.PARTIAL
        comps["ke.expl"] = expl
    else:
        comps["ke.expl"] = derived(
            "ke.expl",
            _rate(tg.expl_n, tg.expl_d),
            unit="rate",
            n=tg.expl_d,
            thin_n=THIN_PLAYS_STD,
        )
    comps["ke.expl_allowed"] = derived(
        "ke.expl_allowed",
        _rate(tg.expl_allowed_n, tg.expl_allowed_d),
        unit="rate",
        n=tg.expl_allowed_d,
        thin_n=THIN_PLAYS_STD,
    )
    comps["ke.off_pass_epa"] = derived(
        "ke.off_pass_epa",
        _rate(tg.pass_epa_sum, tg.pass_epa_n),
        unit="epa_per_play",
        n=tg.pass_epa_n,
        thin_n=THIN_PASS_SPLIT,
        notes={"split": True, "not_a_second_rating": True},
    )
    comps["ke.off_rush_epa"] = derived(
        "ke.off_rush_epa",
        _rate(tg.rush_epa_sum, tg.rush_epa_n),
        unit="epa_per_play",
        n=tg.rush_epa_n,
        thin_n=THIN_RUSH_SPLIT,
        notes={"split": True},
    )
    comps["ke.off_early_epa"] = derived(
        "ke.off_early_epa",
        _rate(tg.early_epa_sum, tg.early_epa_n),
        unit="epa_per_play",
        n=tg.early_epa_n,
        notes={"split": True, "down": "1-2"},
    )

    if tg.sport != "nfl":
        comps["ke.st"] = omitted("ke.st", unit="st_epa_per_play", reason="CFB ST uncertified — omit")
    else:
        comps["ke.st"] = derived(
            "ke.st",
            _rate(tg.st_epa_sum, tg.st_n),
            unit="st_epa_per_play",
            n=tg.st_n,
            thin_n=THIN_ST_PLAYS,
            notes={"no_1_0_hook": True},
        )

    if tg.drive_ids_missing and tg.n_drives == 0:
        comps["ke.finish"] = derived(
            "ke.finish",
            None,
            unit="rate",
            n=0,
            missing_fields=["drive_id"],
        )
        comps["ke.ppo"] = derived("ke.ppo", None, unit="points_per_opportunity", n=0, missing_fields=["drive_id"])
        comps["ke.opp_rate"] = derived("ke.opp_rate", None, unit="rate", n=0, missing_fields=["drive_id"])
    else:
        finish_thin = tg.n_opp < THIN_OPPORTUNITIES_STD
        if tg.n_drives < THIN_DRIVES_GAME:
            comps["ke.opp_rate"] = derived("ke.opp_rate", None, unit="rate", n=tg.n_drives)
        else:
            comps["ke.opp_rate"] = derived(
                "ke.opp_rate",
                _rate(tg.n_opp, tg.n_drives),
                unit="rate",
                n=tg.n_drives,
            )
        comps["ke.ppo"] = derived(
            "ke.ppo",
            _rate(tg.opp_points, tg.n_opp),
            unit="points_per_opportunity",
            n=tg.n_opp,
            thin_n=THIN_OPPORTUNITIES_STD,
            notes={"points_source": "nflverse_scoring_flags" if tg.sport == "nfl" else "type_text_heuristic"},
        )
        comps["ke.finish"] = derived(
            "ke.finish",
            _rate(tg.finished_opp, tg.n_opp),
            unit="rate",
            n=tg.n_opp,
            thin_n=THIN_OPPORTUNITIES_STD,
        )
        if finish_thin:
            pass
    comps["ke.rz_td"] = derived(
        "ke.rz_td",
        _rate(tg.rz_td, tg.rz_plays),
        unit="rate",
        n=tg.rz_plays,
        notes={"must_not_be_named": "ke.finish", "partial_rz_only": True},
    )

    audit = audit_disruption_columns(tg.off_plays + tg.def_plays)
    comps["ke.havoc"] = havoc_component(audit)
    if tg.sport == "nfl":
        comps["ke.disruption_proxy_nfl"] = nfl_proxy_rate(tg.def_plays)
    else:
        comps["ke.disruption_flags_cfb"] = omitted(
            "ke.disruption_flags_cfb",
            unit="rate",
            reason="publish per-event rates only; flags uncertified as official havoc",
        )
    for attr in ("sack", "interception", "qb_hit", "fumble", "fumble_forced", "tfl", "pass_breakup"):
        comps[f"ke.disruption_{attr}"] = event_rate(tg.def_plays, attr)

    comps["ke.team_strength"] = omitted(
        "ke.team_strength",
        unit="net_epa_per_play",
        reason="Phase 1 hard stop — no Team Strength composite",
    )
    return comps


def _play_weighted(values: Sequence[Tuple[float, int]]) -> Optional[float]:
    den = sum(n for _v, n in values if n > 0)
    if den <= 0:
        return None
    return sum(v * n for v, n in values if n > 0) / den


def team_week_snapshot(
    games: Sequence[TeamGame],
    *,
    sport: str,
    season: int,
    as_of_week: int,
    team: str,
) -> Dict[str, Any]:
    mine = [g for g in games if g.team == team and g.week < as_of_week and g.season == season]
    n_games = len(mine)
    off = _play_weighted([(g.off_epa, g.off_epa_n) for g in mine if g.off_epa is not None])
    deff = _play_weighted([(g.def_epa, g.def_epa_n) for g in mine if g.def_epa is not None])
    n_off = sum(g.off_epa_n for g in mine)
    n_def = sum(g.def_epa_n for g in mine)

    # Merge components via play-weighted means of team-game native values.
    merged: Dict[str, Component] = {}
    if not mine:
        empty = team_game_components(
            TeamGame(sport=sport, season=season, week=0, game_id="", team=team, opponent="", home=False)
        )
        for cid, comp in empty.items():
            merged[cid] = derived(cid, None, unit=comp.unit, n=0)
        merged["ke.st"] = empty["ke.st"]
        merged["ke.havoc"] = empty["ke.havoc"]
        merged["ke.team_strength"] = empty["ke.team_strength"]
    else:
        # Use last game's component schema, recompute from summed counters.
        acc = TeamGame(sport=sport, season=season, week=as_of_week - 1, game_id="STD", team=team, opponent="", home=False)
        acc.off_plays = []
        acc.def_plays = []
        for g in mine:
            acc.n_off_plays += g.n_off_plays
            acc.n_def_plays += g.n_def_plays
            acc.off_epa_sum += g.off_epa_sum
            acc.off_epa_n += g.off_epa_n
            acc.def_epa_sum += g.def_epa_sum
            acc.def_epa_n += g.def_epa_n
            acc.off_epa_null += g.off_epa_null
            acc.def_epa_null += g.def_epa_null
            acc.success_n += g.success_n
            acc.success_d += g.success_d
            acc.success_allowed_n += g.success_allowed_n
            acc.success_allowed_d += g.success_allowed_d
            acc.std_n += g.std_n
            acc.std_d += g.std_d
            acc.expl_n += g.expl_n
            acc.expl_d += g.expl_d
            acc.expl_pass_n += g.expl_pass_n
            acc.expl_pass_d += g.expl_pass_d
            acc.expl_rush_n += g.expl_rush_n
            acc.expl_rush_d += g.expl_rush_d
            acc.expl_allowed_n += g.expl_allowed_n
            acc.expl_allowed_d += g.expl_allowed_d
            acc.pass_epa_sum += g.pass_epa_sum
            acc.pass_epa_n += g.pass_epa_n
            acc.rush_epa_sum += g.rush_epa_sum
            acc.rush_epa_n += g.rush_epa_n
            acc.early_epa_sum += g.early_epa_sum
            acc.early_epa_n += g.early_epa_n
            acc.early_succ_n += g.early_succ_n
            acc.early_succ_d += g.early_succ_d
            acc.comp_plays += g.comp_plays
            acc.score_diff_known += g.score_diff_known
            acc.clock_known += g.clock_known
            acc.clock_deltas.extend(g.clock_deltas)
            acc.st_epa_sum += g.st_epa_sum
            acc.st_n += g.st_n
            acc.n_drives += g.n_drives
            acc.n_opp += g.n_opp
            acc.n_rz += g.n_rz
            acc.opp_points += g.opp_points
            acc.finished_opp += g.finished_opp
            acc.rz_td += g.rz_td
            acc.rz_plays += g.rz_plays
            acc.drive_ids_missing += g.drive_ids_missing
            acc.off_plays.extend(g.off_plays)
            acc.def_plays.extend(g.def_plays)
        # Pace at week grain is mean of team-game play counts, not a sum.
        merged = team_game_components(acc)
        merged["ke.pace"] = derived(
            "ke.pace",
            _mean([float(g.n_off_plays) for g in mine if g.n_off_plays]),
            unit="plays_per_offense_game",
            n=n_games,
            thin_n=THIN_GAMES_STD,
        )
        merged["ke.pace_competitive"] = derived(
            "ke.pace_competitive",
            _mean([float(g.comp_plays) for g in mine if g.n_off_plays]),
            unit="plays_per_offense_game",
            n=n_games,
            thin_n=THIN_GAMES_STD,
            notes={"margin": COMPETITIVE_MARGIN},
        )
        if n_off < THIN_PLAYS_STD and merged["ke.off_eff"].value is not None:
            merged["ke.off_eff"].status = Status.THIN
            merged["ke.off_eff"].notes["thin_plays"] = n_off
        if n_def < THIN_PLAYS_STD and merged["ke.def_eff"].value is not None:
            merged["ke.def_eff"].status = Status.THIN
            merged["ke.def_eff"].notes["thin_plays"] = n_def

    return {
        "sport": sport,
        "season": season,
        "as_of_week": as_of_week,
        "feature_week_max": max((g.week for g in mine), default=0),
        "cutoff": "week < as_of_week",
        "team": team,
        "n_games": n_games,
        "n_off_plays": n_off,
        "n_def_plays": n_def,
        "components": {k: v.to_dict() for k, v in merged.items()},
        "off_epa_raw": off,
        "def_epa_raw": deff,
        "opponents": sorted({g.opponent for g in mine if g.opponent}),
        "game_ids": sorted({g.game_id for g in mine}),
        "production_promote": False,
        "layer_note": "component layers declared per cell; no Team Strength",
    }


def snapshots_for_week(
    plays: Sequence[CanonicalPlay],
    *,
    sport: str,
    season: int,
    as_of_week: int,
) -> List[Dict[str, Any]]:
    window = filter_week_lt(plays, season=season, as_of_week=as_of_week)
    games = build_team_games(window)
    teams = sorted({g.team for g in games})
    return [
        team_week_snapshot(games, sport=sport, season=season, as_of_week=as_of_week, team=team)
        for team in teams
    ]
