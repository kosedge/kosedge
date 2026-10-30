"""Research-only snap-share `_5g` player exposure ledger (t4833u).

MATERIALIZE ≠ admit ≠ merge ≠ live ingest ≠ scoring ≠ injury weights.

Reads SHA-pinned staged nflverse parquets and writes one research ledger.
Unresolved / conflict / unknown / missing / verified_zero stay distinct.
Target-game snaps cannot enter their own pregame window (#666 / cf514078).

This module sits *outside* ``nfl_snap_share_exposure_ledger`` so the
isolated production builder remains fail-closed. It reuses
``resolve_if_5g_window`` for the IF `_5g` as-of contract and flags
states the production builder would reject.
"""

from __future__ import annotations

import argparse
import hashlib
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_pregame_asof import IF_MATCHUP_ASOF_CONTRACT
from src.services.nfl_snap_share_exposure_ledger.identity import fingerprint_payload
from src.services.nfl_snap_share_exposure_ledger.schema import (
    DEFENSE_POSITIONS,
    IF_5G_WINDOW_CONTRACT,
    OFFENSE_POSITIONS,
    SOURCE_NFLVERSE_SNAP_COUNTS,
    STARTER_LABEL_THRESHOLD,
    WINDOW_LABEL_5G,
    ExposureLedgerReject,
    ScheduleGameRow,
    SituationalWeekRow,
    normalize_position,
    normalize_team,
    side_for_position,
)
from src.services.nfl_snap_share_exposure_ledger.window import resolve_if_5g_window


RESEARCH_LEDGER_SCHEMA_VERSION = "research-snap-share-5g-exposure-ledger-v0-t4833u"
RESEARCH_TICKET = "t4833u"
SOURCE_NFLVERSE_PLAYERS = "nflverse_players"
SOURCE_NFLVERSE_ROSTER_WEEKLY = "nflverse_weekly_rosters"

# Exact staged files (DECISION 09f8a926). No additional acquisition.
EXPECTED_INPUT_SHA256 = {
    "snap_counts_2026.parquet": (
        "81a1e6f5838be0bc5fa11155ed95e39cd535dcb61745aec0ca2bba9287421241"
    ),
    "players.parquet": (
        "b6dd0c868c68b4854d212fbb71ea8f7b562beae6daf5d5dc83c3d88c7c40a647"
    ),
    "roster_weekly_2026.parquet": (
        "7ba8d815277b2ea49a82282d9e22b0ce11d38508a11781ddf8b155f9111a76f2"
    ),
}

STATE_MEASURED = "measured"
STATE_VERIFIED_ZERO = "verified_zero"
STATE_MISSING = "missing"
STATE_UNKNOWN = "unknown"
STATE_UNRESOLVED = "unresolved_identity"
STATE_CONFLICT = "conflict"

# Row roll-up: keep damaging states above usable ones. measured beats
# verified_zero so a player with some recorded snaps is not labeled zero.
STATE_PRIORITY = {
    STATE_CONFLICT: 50,
    STATE_UNRESOLVED: 40,
    STATE_UNKNOWN: 30,
    STATE_MISSING: 20,
    STATE_MEASURED: 10,
    STATE_VERIFIED_ZERO: 0,
}

GRAIN_WINDOW = "window_exposure"
GRAIN_RESIDUAL = "source_residual"

NON_ACT_ROSTER_STATUSES = frozenset(
    {"INA", "RES", "DEV", "CUT", "RET", "EXE", "TRD", "TRT", "PUP", "SUS", "IR"}
)


class ResearchExposureReject(Exception):
    """Fail closed on input / hash / date problems. Never invent a value."""

    def __init__(self, code: str, message: str) -> None:
        self.code = str(code)
        self.message = str(message)
        super().__init__(f"{self.code}: {self.message}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_staged_input_hashes(
    *,
    snap_path: Path,
    players_path: Path,
    roster_path: Path,
    expected: Optional[Mapping[str, str]] = None,
) -> Dict[str, str]:
    pins = dict(expected or EXPECTED_INPUT_SHA256)
    found = {
        "snap_counts_2026.parquet": sha256_file(Path(snap_path)),
        "players.parquet": sha256_file(Path(players_path)),
        "roster_weekly_2026.parquet": sha256_file(Path(roster_path)),
    }
    for name, digest in found.items():
        want = pins.get(name)
        if want and digest != want:
            raise ResearchExposureReject(
                "INPUT_HASH_MISMATCH",
                f"{name} sha256 {digest} != pinned {want} (no substitute file)",
            )
    return found


def parse_pfr_game_date(pfr_game_id: Any) -> str:
    raw = str(pfr_game_id or "").strip()
    if len(raw) < 8 or not raw[:8].isdigit():
        raise ResearchExposureReject(
            "GAME_DATE_UNRESOLVED",
            f"pfr_game_id {pfr_game_id!r} has no YYYYMMDD prefix (no impute)",
        )
    text = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ResearchExposureReject(
            "GAME_DATE_UNRESOLVED",
            f"pfr_game_id {pfr_game_id!r} is not a valid calendar date",
        ) from exc
    return text


def split_nflverse_game_id(game_id: Any) -> Tuple[int, int, str, str]:
    parts = str(game_id or "").strip().split("_")
    if len(parts) != 4:
        raise ResearchExposureReject(
            "INPUT_INVALID",
            f"game_id {game_id!r} is not season_week_away_home (no impute)",
        )
    try:
        season = int(parts[0])
        week = int(parts[1])
    except ValueError as exc:
        raise ResearchExposureReject(
            "INPUT_INVALID", f"game_id {game_id!r} season/week not int"
        ) from exc
    return season, week, normalize_team(parts[2]), normalize_team(parts[3])


def _finite_nonneg(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        return None
    return number


def _pct_as_fraction(value: Any) -> Optional[float]:
    raw = _finite_nonneg(value)
    if raw is None:
        return None
    if raw > 1.5:
        raw = raw / 100.0
    if raw > 1.0:
        return None
    return raw


def research_side(position: Any) -> Tuple[Optional[str], Optional[str]]:
    pos = normalize_position(position)
    if not pos:
        return None, "POSITION_UNKNOWN"
    try:
        return side_for_position(pos), None
    except ExposureLedgerReject as exc:
        return None, exc.code


def worst_state(states: Iterable[str]) -> str:
    worst = STATE_MEASURED
    worst_rank = STATE_PRIORITY[STATE_MEASURED]
    for state in states:
        rank = STATE_PRIORITY.get(state)
        if rank is None:
            raise ResearchExposureReject(
                "INPUT_INVALID", f"unknown participation state {state!r}"
            )
        if rank > worst_rank:
            worst = state
            worst_rank = rank
    return worst


def table_to_rows(table: Any) -> List[Dict[str, Any]]:
    cols = {name: table.column(name).to_pylist() for name in table.column_names}
    n = table.num_rows
    return [{name: cols[name][i] for name in cols} for i in range(n)]


def load_parquet_rows(path: Path) -> List[Dict[str, Any]]:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise ResearchExposureReject(
            "PYARROW_REQUIRED",
            "pyarrow is required to read staged research parquets",
        ) from exc
    return table_to_rows(pq.read_table(Path(path)))


def _identity_maps(
    player_rows: Sequence[Mapping[str, Any]],
    roster_rows: Sequence[Mapping[str, Any]],
) -> Tuple[Dict[str, str], Dict[str, str], Dict[Tuple[str, str, int], str]]:
    players_pfr: Dict[str, str] = {}
    for row in player_rows:
        pfr = str(row.get("pfr_id") or "").strip()
        gsis = str(row.get("gsis_id") or "").strip()
        if not pfr or not gsis:
            continue
        prior = players_pfr.get(pfr)
        if prior is not None and prior != gsis:
            raise ResearchExposureReject(
                "IDENTITY_COLLISION",
                f"players.pfr_id {pfr} maps to both {prior} and {gsis}",
            )
        players_pfr[pfr] = gsis

    roster_pfr: Dict[str, str] = {}
    roster_tw: Dict[Tuple[str, str, int], str] = {}
    for row in roster_rows:
        pfr = str(row.get("pfr_id") or "").strip()
        gsis = str(row.get("gsis_id") or "").strip()
        team = normalize_team(row.get("team"))
        week = row.get("week")
        if pfr and gsis:
            prior = roster_pfr.get(pfr)
            if prior is not None and prior != gsis:
                raise ResearchExposureReject(
                    "IDENTITY_COLLISION",
                    f"roster.pfr_id {pfr} maps to both {prior} and {gsis}",
                )
            roster_pfr[pfr] = gsis
        if pfr and gsis and team and isinstance(week, int):
            roster_tw[(pfr, team, week)] = gsis
    return players_pfr, roster_pfr, roster_tw


def classify_pfr_identity(
    *,
    pfr_id: str,
    team: str,
    week: int,
    players_pfr: Mapping[str, str],
    roster_pfr: Mapping[str, str],
    roster_tw: Mapping[Tuple[str, str, int], str],
) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """Return (state, gsis_players, gsis_roster, gsis_resolved).

    Do not adjudicate a conflict. Do not name-match an unresolved id.
    """
    gsis_players = players_pfr.get(pfr_id)
    gsis_roster = roster_tw.get((pfr_id, team, week)) or roster_pfr.get(pfr_id)
    if gsis_players and gsis_roster and gsis_players != gsis_roster:
        return STATE_CONFLICT, gsis_players, gsis_roster, None
    if gsis_players and gsis_roster:
        return STATE_MEASURED, gsis_players, gsis_roster, gsis_players
    if gsis_players:
        return STATE_MEASURED, gsis_players, None, gsis_players
    if gsis_roster:
        return STATE_MEASURED, None, gsis_roster, gsis_roster
    return STATE_UNRESOLVED, None, None, None


def infer_schedule_and_dates(
    snap_rows: Sequence[Mapping[str, Any]],
) -> Tuple[List[ScheduleGameRow], Dict[str, str], Dict[Tuple[str, int], str]]:
    games: Dict[str, Dict[str, Any]] = {}
    team_week_game: Dict[Tuple[str, int], str] = {}
    for row in snap_rows:
        game_id = str(row.get("game_id") or "").strip()
        if not game_id:
            raise ResearchExposureReject("INPUT_INVALID", "snap game_id missing")
        season, week, away, home = split_nflverse_game_id(game_id)
        game_date = parse_pfr_game_date(row.get("pfr_game_id"))
        team = normalize_team(row.get("team"))
        prior = games.get(game_id)
        if prior is None:
            games[game_id] = {
                "season": season,
                "week": week,
                "away": away,
                "home": home,
                "game_date": game_date,
            }
        else:
            if (
                prior["season"] != season
                or prior["week"] != week
                or prior["game_date"] != game_date
            ):
                raise ResearchExposureReject(
                    "INPUT_INVALID",
                    f"inconsistent schedule facts for {game_id}",
                )
        key = (team, week)
        existing = team_week_game.get(key)
        if existing is not None and existing != game_id:
            raise ResearchExposureReject(
                "GRAIN_MISMATCH",
                f"{team} w{week} maps to {existing} and {game_id}",
            )
        team_week_game[key] = game_id

    schedule = [
        ScheduleGameRow(
            season=int(meta["season"]),
            week=int(meta["week"]),
            game_id=game_id,
            home_team=str(meta["home"]),
            away_team=str(meta["away"]),
            completed=True,
            game_date=str(meta["game_date"]),
            kickoff_ts=None,
        )
        for game_id, meta in sorted(games.items(), key=lambda kv: (kv[1]["week"], kv[0]))
    ]
    dates = {game_id: str(meta["game_date"]) for game_id, meta in games.items()}
    return schedule, dates, team_week_game


def infer_situational_rows(
    team_week_game: Mapping[Tuple[str, int], str],
    schedule: Sequence[ScheduleGameRow],
) -> List[SituationalWeekRow]:
    season_by_game = {row.game_id: row.season for row in schedule}
    rows: List[SituationalWeekRow] = []
    for (team, week), game_id in sorted(team_week_game.items()):
        rows.append(
            SituationalWeekRow(
                season=int(season_by_game[game_id]),
                week=int(week),
                team=team,
                games_played=1,
                source="snap_presence_completed",
            )
        )
    return rows


def team_game_denoms(
    snap_rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str], Dict[str, Optional[float]]]:
    """Offense/defense denominators from max player snaps (not pct)."""
    acc: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(
        lambda: {"offense": 0.0, "defense": 0.0, "st": 0.0}
    )
    for row in snap_rows:
        key = (str(row.get("game_id") or "").strip(), normalize_team(row.get("team")))
        for side, field in (
            ("offense", "offense_snaps"),
            ("defense", "defense_snaps"),
            ("st", "st_snaps"),
        ):
            value = _finite_nonneg(row.get(field))
            if value is not None and value > acc[key][side]:
                acc[key][side] = value
    return {key: dict(vals) for key, vals in acc.items()}


def _roster_index(
    roster_rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, int], List[Mapping[str, Any]]]:
    out: Dict[Tuple[str, int], List[Mapping[str, Any]]] = defaultdict(list)
    for row in roster_rows:
        team = normalize_team(row.get("team"))
        week = row.get("week")
        if team and isinstance(week, int):
            out[(team, week)].append(row)
    return out


def _snap_index(
    snap_rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str], List[Mapping[str, Any]]]:
    out: Dict[Tuple[str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in snap_rows:
        game_id = str(row.get("game_id") or "").strip()
        team = normalize_team(row.get("team"))
        if game_id and team:
            out[(game_id, team)].append(row)
    return out


def _lineage(
    hashes: Mapping[str, str],
) -> Dict[str, Any]:
    return {
        "source_snap": SOURCE_NFLVERSE_SNAP_COUNTS,
        "source_players": SOURCE_NFLVERSE_PLAYERS,
        "source_roster": SOURCE_NFLVERSE_ROSTER_WEEKLY,
        "source_snap_sha256": hashes["snap_counts_2026.parquet"],
        "source_players_sha256": hashes["players.parquet"],
        "source_roster_sha256": hashes["roster_weekly_2026.parquet"],
        "window_contract": IF_5G_WINDOW_CONTRACT,
        "asof_contract": IF_MATCHUP_ASOF_CONTRACT,
        "schema_version": RESEARCH_LEDGER_SCHEMA_VERSION,
        "research_only": True,
        "admitted": False,
        "return_uncredited": True,
        "cc_by_4_0_research_attribution": True,
        "ticket": RESEARCH_TICKET,
    }


def _base_row(lineage: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "row_grain": None,
        "row_state": None,
        "row_state_reason": None,
        "flag_unresolved_identity": False,
        "flag_conflict": False,
        "flag_unknown": False,
        "season": None,
        "window": WINDOW_LABEL_5G,
        "target_week": None,
        "target_game_id": None,
        "target_game_date": None,
        "rating_week": None,
        "team": None,
        "opponent": None,
        "player_gsis_id": None,
        "player_gsis_id_players": None,
        "player_gsis_id_roster": None,
        "player_pfr_id": None,
        "player_name": None,
        "position": None,
        "side": None,
        "embedded_snap_share": None,
        "starter_label_derived": None,
        "window_game_ids": [],
        "window_weeks": [],
        "window_game_dates": [],
        "game_id": None,
        "game_week": None,
        "game_date": None,
        "game_snap_shares": [],
        "game_participation_status": [],
        "game_offense_snaps": [],
        "game_defense_snaps": [],
        "game_st_snaps": [],
        "offense_denoms": [],
        "defense_denoms": [],
        **dict(lineage),
        "row_fingerprint": None,
    }


def _finish_row(row: Dict[str, Any]) -> Dict[str, Any]:
    row["flag_unresolved_identity"] = row["row_state"] == STATE_UNRESOLVED
    row["flag_conflict"] = row["row_state"] == STATE_CONFLICT
    row["flag_unknown"] = row["row_state"] == STATE_UNKNOWN
    payload = {k: v for k, v in row.items() if k != "row_fingerprint"}
    row["row_fingerprint"] = fingerprint_payload(payload)
    return row


def _player_key(
    *,
    gsis: Optional[str],
    pfr: Optional[str],
    name: Optional[str],
) -> Tuple[str, str]:
    if gsis:
        return ("gsis", gsis)
    if pfr:
        return ("pfr", pfr)
    return ("name", str(name or "").strip() or "UNKNOWN")


def _game_participation(
    *,
    snap_row: Optional[Mapping[str, Any]],
    roster_row: Optional[Mapping[str, Any]],
    identity_state: str,
    side: Optional[str],
) -> Tuple[str, str, Optional[float], Optional[float], Optional[float], Optional[float]]:
    """Return state, reason, snap_share, off_snaps, def_snaps, st_snaps."""
    off_s = _finite_nonneg(snap_row.get("offense_snaps")) if snap_row else None
    def_s = _finite_nonneg(snap_row.get("defense_snaps")) if snap_row else None
    st_s = _finite_nonneg(snap_row.get("st_snaps")) if snap_row else None
    if identity_state == STATE_CONFLICT:
        return STATE_CONFLICT, "pfr_gsis_players_ne_roster", None, off_s, def_s, st_s
    if identity_state == STATE_UNRESOLVED:
        return STATE_UNRESOLVED, "pfr_unmapped_no_name_fallback", None, off_s, def_s, st_s
    if snap_row is None and roster_row is None:
        return STATE_MISSING, "no_snap_no_roster", None, None, None, None
    if snap_row is None:
        status = str(roster_row.get("status") or "").strip().upper() if roster_row else ""
        if status == "ACT":
            return STATE_UNKNOWN, "act_absent_unconfirmed", None, None, None, None
        if status in NON_ACT_ROSTER_STATUSES or status:
            return STATE_VERIFIED_ZERO, f"roster_{status or 'non_act'}_absent", 0.0, None, None, None
        return STATE_UNKNOWN, "roster_status_blank_absent", None, None, None, None
    if side is None:
        return STATE_UNKNOWN, "position_side_unsupported", None, off_s, def_s, st_s
    pct_field = "offense_pct" if side == "offense" else "defense_pct"
    snaps_field = "offense_snaps" if side == "offense" else "defense_snaps"
    pct = _pct_as_fraction(snap_row.get(pct_field))
    snaps = _finite_nonneg(snap_row.get(snaps_field))
    if pct is None:
        return STATE_UNKNOWN, f"{side}_pct_unusable", None, off_s, def_s, st_s
    if snaps == 0.0 or pct == 0.0:
        return STATE_VERIFIED_ZERO, f"{side}_zero_in_snap_file", 0.0, off_s, def_s, st_s
    return STATE_MEASURED, f"{side}_snap_share", pct, off_s, def_s, st_s


def _collect_window_players(
    *,
    team: str,
    window_games: Sequence[Any],
    snaps_by_game: Mapping[Tuple[str, str], Sequence[Mapping[str, Any]]],
    roster_by_tw: Mapping[Tuple[str, int], Sequence[Mapping[str, Any]]],
    players_pfr: Mapping[str, str],
    roster_pfr: Mapping[str, str],
    roster_tw: Mapping[Tuple[str, str, int], str],
) -> Dict[Tuple[str, str, Optional[str]], Dict[str, Any]]:
    """Universe = window snap players ∪ ACT-absent roster in window weeks."""
    found: Dict[Tuple[str, str, Optional[str]], Dict[str, Any]] = {}

    def upsert(
        *,
        gsis: Optional[str],
        pfr: Optional[str],
        name: Optional[str],
        position: Optional[str],
        side: Optional[str],
        gsis_players: Optional[str],
        gsis_roster: Optional[str],
        identity_state: str,
    ) -> None:
        key = (*_player_key(gsis=gsis, pfr=pfr, name=name), side)
        rec = found.setdefault(
            key,
            {
                "player_gsis_id": gsis,
                "player_pfr_id": pfr,
                "player_name": name,
                "position": position,
                "side": side,
                "player_gsis_id_players": gsis_players,
                "player_gsis_id_roster": gsis_roster,
                "identity_state": identity_state,
            },
        )
        if not rec["player_name"] and name:
            rec["player_name"] = name
        if not rec["position"] and position:
            rec["position"] = position
        if rec["identity_state"] != STATE_CONFLICT and identity_state == STATE_CONFLICT:
            rec["identity_state"] = STATE_CONFLICT
            rec["player_gsis_id"] = None
            rec["player_gsis_id_players"] = gsis_players
            rec["player_gsis_id_roster"] = gsis_roster
        elif rec["identity_state"] not in {STATE_CONFLICT, STATE_UNRESOLVED}:
            if identity_state == STATE_UNRESOLVED:
                rec["identity_state"] = STATE_UNRESOLVED
                rec["player_gsis_id"] = None

    for game in window_games:
        for snap in snaps_by_game.get((game.game_id, team), ()):
            pfr = str(snap.get("pfr_player_id") or "").strip()
            ident_state, gsis_p, gsis_r, gsis = classify_pfr_identity(
                pfr_id=pfr,
                team=team,
                week=int(game.week),
                players_pfr=players_pfr,
                roster_pfr=roster_pfr,
                roster_tw=roster_tw,
            )
            if ident_state == STATE_CONFLICT:
                gsis = None
            pos = normalize_position(snap.get("position"))
            side, _ = research_side(pos)
            upsert(
                gsis=gsis,
                pfr=pfr or None,
                name=str(snap.get("player") or "") or None,
                position=pos or None,
                side=side,
                gsis_players=gsis_p,
                gsis_roster=gsis_r,
                identity_state=ident_state,
            )
        for roster in roster_by_tw.get((team, int(game.week)), ()):
            status = str(roster.get("status") or "").strip().upper()
            if status != "ACT":
                continue
            gsis = str(roster.get("gsis_id") or "").strip() or None
            pfr = str(roster.get("pfr_id") or "").strip() or None
            if not gsis and not pfr:
                continue
            ident_state = STATE_MEASURED
            gsis_p = players_pfr.get(pfr) if pfr else None
            gsis_r = gsis
            if pfr:
                ident_state, gsis_p, gsis_r, resolved = classify_pfr_identity(
                    pfr_id=pfr,
                    team=team,
                    week=int(game.week),
                    players_pfr=players_pfr,
                    roster_pfr=roster_pfr,
                    roster_tw=roster_tw,
                )
                if ident_state != STATE_CONFLICT:
                    gsis = resolved
            pos = normalize_position(roster.get("position") or roster.get("depth_chart_position"))
            side, _ = research_side(pos)
            upsert(
                gsis=gsis,
                pfr=pfr,
                name=str(roster.get("full_name") or roster.get("football_name") or "") or None,
                position=pos or None,
                side=side,
                gsis_players=gsis_p,
                gsis_roster=gsis_r,
                identity_state=ident_state,
            )
    return found


def _lookup_snap(
    snaps: Sequence[Mapping[str, Any]],
    *,
    gsis: Optional[str],
    pfr: Optional[str],
    players_pfr: Mapping[str, str],
) -> Optional[Mapping[str, Any]]:
    if pfr:
        matched = [s for s in snaps if str(s.get("pfr_player_id") or "").strip() == pfr]
        if matched:
            return matched[0]
    if gsis:
        matched = [
            s
            for s in snaps
            if players_pfr.get(str(s.get("pfr_player_id") or "").strip()) == gsis
        ]
        if matched:
            return matched[0]
    return None


def _lookup_roster(
    rosters: Sequence[Mapping[str, Any]],
    *,
    gsis: Optional[str],
    pfr: Optional[str],
) -> Optional[Mapping[str, Any]]:
    if gsis:
        matched = [r for r in rosters if str(r.get("gsis_id") or "").strip() == gsis]
        if matched:
            return matched[0]
    if pfr:
        matched = [r for r in rosters if str(r.get("pfr_id") or "").strip() == pfr]
        if matched:
            return matched[0]
    return None


def _opponent(schedule_row: ScheduleGameRow, team: str) -> str:
    if normalize_team(schedule_row.home_team) == team:
        return normalize_team(schedule_row.away_team)
    return normalize_team(schedule_row.home_team)


def build_research_5g_exposure_rows(
    *,
    snap_rows: Sequence[Mapping[str, Any]],
    player_rows: Sequence[Mapping[str, Any]],
    roster_rows: Sequence[Mapping[str, Any]],
    source_hashes: Mapping[str, str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Build window + residual rows. Never invent an exposure number."""
    if not snap_rows:
        raise ResearchExposureReject("INPUT_INVALID", "snap_rows empty")
    players_pfr, roster_pfr, roster_tw = _identity_maps(player_rows, roster_rows)
    schedule, dates, team_week_game = infer_schedule_and_dates(snap_rows)
    situational = infer_situational_rows(team_week_game, schedule)
    denoms = team_game_denoms(snap_rows)
    snaps_by_game = _snap_index(snap_rows)
    roster_by_tw = _roster_index(roster_rows)
    lineage = _lineage(source_hashes)
    sched_by_id = {row.game_id: row for row in schedule}

    skip_targets: List[Dict[str, Any]] = []
    window_rows: List[Dict[str, Any]] = []
    teams = sorted({normalize_team(r.get("team")) for r in snap_rows if r.get("team")})

    for team in teams:
        team_games = [
            row
            for row in schedule
            if team in {normalize_team(row.home_team), normalize_team(row.away_team)}
        ]
        team_games.sort(key=lambda r: (int(r.week), r.game_id))
        for target in team_games:
            if int(target.week) < 6:
                continue
            cutoff = f"{target.game_date}T00:00:00Z"
            try:
                resolved = resolve_if_5g_window(
                    season=int(target.season),
                    target_week=int(target.week),
                    team=team,
                    situational_rows=situational,
                    schedule_rows=schedule,
                    target_game_id=target.game_id,
                    forecast_cutoff_ts=cutoff,
                )
            except ExposureLedgerReject as exc:
                skip_targets.append(
                    {
                        "team": team,
                        "target_week": int(target.week),
                        "target_game_id": target.game_id,
                        "target_game_date": target.game_date,
                        "reject_code": exc.code,
                        "reject_message": exc.message,
                    }
                )
                continue

            window_ids = list(resolved.game_ids)
            if target.game_id in window_ids:
                raise ResearchExposureReject(
                    "AS_OF_VIOLATION",
                    f"target {target.game_id} leaked into its own window",
                )
            window_weeks = [int(g.week) for g in resolved.games]
            window_dates = [dates[g.game_id] for g in resolved.games]
            if any(d >= target.game_date for d in window_dates):
                raise ResearchExposureReject(
                    "AS_OF_VIOLATION",
                    f"window date >= target {target.game_id}",
                )
            if resolved.rating_week != int(target.week) - 1:
                raise ResearchExposureReject(
                    "AS_OF_VIOLATION",
                    f"rating_week {resolved.rating_week} != {int(target.week) - 1}",
                )

            players = _collect_window_players(
                team=team,
                window_games=resolved.games,
                snaps_by_game=snaps_by_game,
                roster_by_tw=roster_by_tw,
                players_pfr=players_pfr,
                roster_pfr=roster_pfr,
                roster_tw=roster_tw,
            )
            off_denoms = [
                (denoms.get((g.game_id, team)) or {}).get("offense")
                for g in resolved.games
            ]
            def_denoms = [
                (denoms.get((g.game_id, team)) or {}).get("defense")
                for g in resolved.games
            ]

            for rec in sorted(
                players.values(),
                key=lambda r: (
                    str(r.get("player_gsis_id") or ""),
                    str(r.get("player_pfr_id") or ""),
                    str(r.get("side") or ""),
                ),
            ):
                statuses: List[str] = []
                reasons: List[str] = []
                shares: List[Optional[float]] = []
                off_snaps: List[Optional[float]] = []
                def_snaps: List[Optional[float]] = []
                st_snaps: List[Optional[float]] = []
                for game in resolved.games:
                    snaps = snaps_by_game.get((game.game_id, team), ())
                    rosters = roster_by_tw.get((team, int(game.week)), ())
                    snap = _lookup_snap(
                        snaps,
                        gsis=rec["player_gsis_id"],
                        pfr=rec["player_pfr_id"],
                        players_pfr=players_pfr,
                    )
                    roster = _lookup_roster(
                        rosters,
                        gsis=rec["player_gsis_id"],
                        pfr=rec["player_pfr_id"],
                    )
                    ident = rec["identity_state"]
                    if snap is not None and rec["player_pfr_id"]:
                        ident, _, _, _ = classify_pfr_identity(
                            pfr_id=str(rec["player_pfr_id"]),
                            team=team,
                            week=int(game.week),
                            players_pfr=players_pfr,
                            roster_pfr=roster_pfr,
                            roster_tw=roster_tw,
                        )
                    state, reason, share, o, d, st = _game_participation(
                        snap_row=snap,
                        roster_row=roster,
                        identity_state=ident,
                        side=rec["side"],
                    )
                    statuses.append(state)
                    reasons.append(reason)
                    shares.append(share)
                    off_snaps.append(o)
                    def_snaps.append(d)
                    st_snaps.append(st)

                row_state = worst_state(statuses)
                shareable = all(s in {STATE_MEASURED, STATE_VERIFIED_ZERO} for s in statuses)
                embedded = None
                starter = None
                if shareable and shares and all(x is not None for x in shares):
                    embedded = sum(float(x) for x in shares) / float(len(shares))
                    starter = bool(embedded >= STARTER_LABEL_THRESHOLD)
                row = _base_row(lineage)
                row.update(
                    {
                        "row_grain": GRAIN_WINDOW,
                        "row_state": row_state,
                        "row_state_reason": "|".join(sorted(set(reasons))),
                        "season": int(target.season),
                        "target_week": int(target.week),
                        "target_game_id": target.game_id,
                        "target_game_date": target.game_date,
                        "rating_week": int(resolved.rating_week),
                        "team": team,
                        "opponent": _opponent(target, team),
                        "player_gsis_id": rec["player_gsis_id"],
                        "player_gsis_id_players": rec["player_gsis_id_players"],
                        "player_gsis_id_roster": rec["player_gsis_id_roster"],
                        "player_pfr_id": rec["player_pfr_id"],
                        "player_name": rec["player_name"],
                        "position": rec["position"],
                        "side": rec["side"],
                        "embedded_snap_share": embedded,
                        "starter_label_derived": starter,
                        "window_game_ids": window_ids,
                        "window_weeks": window_weeks,
                        "window_game_dates": window_dates,
                        "game_snap_shares": shares,
                        "game_participation_status": statuses,
                        "game_offense_snaps": off_snaps,
                        "game_defense_snaps": def_snaps,
                        "game_st_snaps": st_snaps,
                        "offense_denoms": off_denoms,
                        "defense_denoms": def_denoms,
                    }
                )
                window_rows.append(_finish_row(row))

    residual_rows = _build_residual_rows(
        snap_rows=snap_rows,
        roster_rows=roster_rows,
        team_week_game=team_week_game,
        dates=dates,
        sched_by_id=sched_by_id,
        players_pfr=players_pfr,
        roster_pfr=roster_pfr,
        roster_tw=roster_tw,
        lineage=lineage,
    )
    rows = residual_rows + window_rows
    stats = _stats(
        rows=rows,
        skip_targets=skip_targets,
        schedule=schedule,
        snap_rows=snap_rows,
    )
    return rows, stats


def _build_residual_rows(
    *,
    snap_rows: Sequence[Mapping[str, Any]],
    roster_rows: Sequence[Mapping[str, Any]],
    team_week_game: Mapping[Tuple[str, int], str],
    dates: Mapping[str, str],
    sched_by_id: Mapping[str, ScheduleGameRow],
    players_pfr: Mapping[str, str],
    roster_pfr: Mapping[str, str],
    roster_tw: Mapping[Tuple[str, str, int], str],
    lineage: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    residuals: List[Dict[str, Any]] = []
    played = set(team_week_game)
    # Alex 99.82% path: snap → players.pfr_id → gsis. Conflict/unresolved
    # do not contribute a resolved GSIS (do not invent a winner).
    snap_gsis_keys = set()
    for snap in snap_rows:
        pfr = str(snap.get("pfr_player_id") or "").strip()
        team = normalize_team(snap.get("team"))
        week = int(snap.get("week"))
        ident, gsis_p, gsis_r, gsis = classify_pfr_identity(
            pfr_id=pfr,
            team=team,
            week=week,
            players_pfr=players_pfr,
            roster_pfr=roster_pfr,
            roster_tw=roster_tw,
        )
        if gsis:
            snap_gsis_keys.add((gsis, team, week))
        if ident not in {STATE_UNRESOLVED, STATE_CONFLICT}:
            continue
        reason = (
            "pfr_unmapped_no_name_fallback"
            if ident == STATE_UNRESOLVED
            else "pfr_gsis_players_ne_roster"
        )
        game_id = str(snap.get("game_id") or "").strip()
        row = _base_row(lineage)
        season, _, away, home = split_nflverse_game_id(game_id)
        row.update(
            {
                "row_grain": GRAIN_RESIDUAL,
                "row_state": ident,
                "row_state_reason": reason,
                "season": season,
                "team": team,
                "opponent": away if team == home else home,
                "player_gsis_id": None,
                "player_gsis_id_players": gsis_p,
                "player_gsis_id_roster": gsis_r,
                "player_pfr_id": pfr or None,
                "player_name": str(snap.get("player") or "") or None,
                "position": normalize_position(snap.get("position")) or None,
                "side": research_side(snap.get("position"))[0],
                "game_id": game_id,
                "game_week": week,
                "game_date": dates.get(game_id),
            }
        )
        residuals.append(_finish_row(row))

    for roster in roster_rows:
        team = normalize_team(roster.get("team"))
        week = roster.get("week")
        if not isinstance(week, int) or (team, week) not in played:
            continue
        status = str(roster.get("status") or "").strip().upper()
        if status != "ACT":
            continue
        gsis = str(roster.get("gsis_id") or "").strip() or None
        pfr = str(roster.get("pfr_id") or "").strip() or None
        if gsis and (gsis, team, week) in snap_gsis_keys:
            continue
        if not gsis and pfr:
            # no GSIS on an ACT roster row in a played week
            pass
        game_id = team_week_game[(team, week)]
        sched = sched_by_id[game_id]
        row = _base_row(lineage)
        row.update(
            {
                "row_grain": GRAIN_RESIDUAL,
                "row_state": STATE_UNKNOWN,
                "row_state_reason": "act_absent_unconfirmed",
                "season": int(sched.season),
                "team": team,
                "opponent": _opponent(sched, team),
                "player_gsis_id": gsis,
                "player_gsis_id_players": players_pfr.get(pfr) if pfr else None,
                "player_gsis_id_roster": gsis,
                "player_pfr_id": pfr,
                "player_name": str(roster.get("full_name") or "") or None,
                "position": normalize_position(
                    roster.get("position") or roster.get("depth_chart_position")
                )
                or None,
                "side": research_side(
                    roster.get("position") or roster.get("depth_chart_position")
                )[0],
                "game_id": game_id,
                "game_week": week,
                "game_date": dates.get(game_id),
            }
        )
        residuals.append(_finish_row(row))
    return residuals


def _stats(
    *,
    rows: Sequence[Mapping[str, Any]],
    skip_targets: Sequence[Mapping[str, Any]],
    schedule: Sequence[ScheduleGameRow],
    snap_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    window_rows = [r for r in rows if r["row_grain"] == GRAIN_WINDOW]
    residual_rows = [r for r in rows if r["row_grain"] == GRAIN_RESIDUAL]
    state_counts = defaultdict(int)
    for row in window_rows:
        state_counts[str(row["row_state"])] += 1
    residual_states = defaultdict(int)
    residual_reasons = defaultdict(int)
    for row in residual_rows:
        residual_states[str(row["row_state"])] += 1
        residual_reasons[str(row["row_state_reason"])] += 1
    target_ids = sorted(
        {
            (r["team"], r["target_game_id"])
            for r in window_rows
            if r["target_game_id"]
        }
    )
    leak = [
        r["target_game_id"]
        for r in window_rows
        if r["target_game_id"] in set(r["window_game_ids"] or [])
    ]
    return {
        "schema_version": RESEARCH_LEDGER_SCHEMA_VERSION,
        "ticket": RESEARCH_TICKET,
        "n_rows": len(rows),
        "n_window_rows": len(window_rows),
        "n_residual_rows": len(residual_rows),
        "window_state_counts": dict(sorted(state_counts.items())),
        "residual_state_counts": dict(sorted(residual_states.items())),
        "residual_reason_counts": dict(sorted(residual_reasons.items())),
        "n_targets_populated": len(target_ids),
        "n_targets_skipped": len(skip_targets),
        "skipped_targets": list(skip_targets),
        "n_schedule_games": len({s.game_id for s in schedule}),
        "n_snap_rows": len(snap_rows),
        "leakage_target_in_window": leak,
        "alex_expected": {
            "unresolved_snap_rows": 18,
            "conflict_snap_rows": 6,
            "act_absent_unknown": 325,
            "unknown_residual_approx": 367,
        },
    }


def write_research_parquet(rows: Sequence[Mapping[str, Any]], path: Path) -> str:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise ResearchExposureReject(
            "PYARROW_REQUIRED",
            "pyarrow is required to seal the research parquet",
        ) from exc
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(list(rows))
    pq.write_table(table, path, compression="zstd")
    return sha256_file(path)


def materialize_from_paths(
    *,
    snap_path: Path,
    players_path: Path,
    roster_path: Path,
    out_path: Path,
    expected_hashes: Optional[Mapping[str, str]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], str]:
    hashes = verify_staged_input_hashes(
        snap_path=snap_path,
        players_path=players_path,
        roster_path=roster_path,
        expected=expected_hashes,
    )
    snap_rows = load_parquet_rows(Path(snap_path))
    player_rows = load_parquet_rows(Path(players_path))
    roster_rows = load_parquet_rows(Path(roster_path))
    rows, stats = build_research_5g_exposure_rows(
        snap_rows=snap_rows,
        player_rows=player_rows,
        roster_rows=roster_rows,
        source_hashes=hashes,
    )
    digest = write_research_parquet(rows, Path(out_path))
    stats["output_path"] = str(out_path)
    stats["output_sha256"] = digest
    stats["input_sha256"] = hashes
    return rows, stats, digest


def default_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Materialize research-only snap-share `_5g` exposure ledger (t4833u)."
    )
    parser.add_argument("--snap", required=True, type=Path)
    parser.add_argument("--players", required=True, type=Path)
    parser.add_argument("--roster", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = default_arg_parser().parse_args(argv)
    _rows, stats, digest = materialize_from_paths(
        snap_path=args.snap,
        players_path=args.players,
        roster_path=args.roster,
        out_path=args.out,
    )
    print(digest)
    print(f"rows={stats['n_rows']} window={stats['n_window_rows']} residual={stats['n_residual_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
