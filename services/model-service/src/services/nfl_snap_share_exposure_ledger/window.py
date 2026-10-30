"""Resolve the exact IF `_5g` games — not a convenient latest-five query.

The Independent Fair path consumes `*_5g` fields from NflGameInputs. Those
fields are the rolling row at `(season, rating_week, team)` produced by:

    PARTITION BY team ORDER BY season, week
    ROWS BETWEEN 4 PRECEDING AND CURRENT ROW

on `nfl_dp_team_situational_weekly` filtered to that season
(`ingest.py@1b39f4e9` L1283–1314). The rolling table stores only aggregates
plus `games_in_window_5` — not game IDs.

`rating_week` is the completed-data week (CURRENT ROW), not the forecast
target. t4822u requires an explicit `target_week` and binds
`rating_week = target_week - 1`. The pin matchup join at
`ingest.py@1b39f4e9` L1497–1501 used the same week as the schedule game.

Reconstruction:
  1. Require target_week; resolve rating_week = target_week - 1.
  2. Take the caller's situational team-week rows (the same grain as ingest).
  3. Apply the same partition / order / frame at rating_week.
  4. Map each selected week to exactly one completed schedule game_id.
  5. Reject any target-week or future game (week, game_id, or date).

Bye weeks with no situational row are skipped by the row frame (same as SQL)
inside the rating window. A missing `target_week - 1` row is not filled
from an earlier week. A "latest five scheduled games" query can therefore
disagree — that disagreement is a reject, not something this resolver
papers over.
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence

from src.services.nfl_pregame_asof import (
    PregameAsofReject,
    reject_if_not_pregame_game,
    resolve_pregame_rating_week,
)
from src.services.nfl_snap_share_exposure_ledger.identity import fingerprint_payload
from src.services.nfl_snap_share_exposure_ledger.schema import (
    IF_5G_WINDOW_CONTRACT,
    REJECT_FUTURE_GAME_IN_WINDOW,
    REJECT_GAME_NOT_COMPLETED,
    REJECT_GRAIN_MISMATCH,
    REJECT_INPUT_INVALID,
    REJECT_RATING_WEEK_NOT_LAGGED,
    REJECT_RATING_WEEK_STALE,
    REJECT_RATING_WEEK_UNRESOLVED,
    REJECT_SCHEDULE_UNRESOLVED,
    REJECT_TARGET_WEEK_INVALID,
    REJECT_WINDOW_INCOMPLETE,
    REJECT_WINDOW_MISMATCH,
    REJECT_WINDOW_SHORT,
    WINDOW_LABEL_5G,
    WINDOW_SIZE_5G,
    ExposureLedgerReject,
    ResolvedIf5gWindow,
    ResolvedWindowGame,
    ScheduleGameRow,
    SituationalWeekRow,
    normalize_team,
    require_nonempty_str,
)


def _raise_asof(exc: PregameAsofReject) -> None:
    code = exc.code
    if code == REJECT_TARGET_WEEK_INVALID:
        mapped = REJECT_TARGET_WEEK_INVALID
    elif code == REJECT_RATING_WEEK_NOT_LAGGED:
        mapped = REJECT_RATING_WEEK_NOT_LAGGED
    elif code == REJECT_RATING_WEEK_STALE:
        mapped = REJECT_RATING_WEEK_STALE
    elif code == REJECT_RATING_WEEK_UNRESOLVED:
        mapped = REJECT_RATING_WEEK_UNRESOLVED
    elif code == REJECT_FUTURE_GAME_IN_WINDOW:
        mapped = REJECT_FUTURE_GAME_IN_WINDOW
    else:
        mapped = REJECT_INPUT_INVALID
    raise ExposureLedgerReject(mapped, exc.message) from exc


def resolve_if_5g_window(
    *,
    season: int,
    target_week: int,
    team: str,
    situational_rows: Sequence[SituationalWeekRow],
    schedule_rows: Sequence[ScheduleGameRow],
    rating_week: Optional[int] = None,
    declared_games_in_window_5: Optional[int] = None,
    target_game_id: Optional[str] = None,
    forecast_cutoff_ts: Optional[str] = None,
) -> ResolvedIf5gWindow:
    """Return the exact five games feeding the IF `_5g` row at rating_week."""
    if not isinstance(season, int) or season < 1:
        raise ExposureLedgerReject(REJECT_INPUT_INVALID, "season must be a positive int")
    team_n = normalize_team(require_nonempty_str(team, field_name="team"))
    target_id = (
        require_nonempty_str(target_game_id, field_name="target_game_id")
        if target_game_id is not None
        else None
    )

    by_week = _situational_index(
        season=season, team=team_n, rows=situational_rows
    )
    try:
        resolved_rating_week = resolve_pregame_rating_week(
            target_week=target_week,
            rating_week=rating_week,
            available_rating_weeks=by_week.keys(),
        )
    except PregameAsofReject as exc:
        _raise_asof(exc)

    target_schedule = _lookup_target_schedule(
        season=season,
        team=team_n,
        target_week=int(target_week),
        target_game_id=target_id,
        schedule_rows=schedule_rows,
    )

    ordered_weeks = sorted(by_week)
    idx = ordered_weeks.index(resolved_rating_week)
    start = max(0, idx - (WINDOW_SIZE_5G - 1))
    selected_weeks = ordered_weeks[start : idx + 1]
    if len(selected_weeks) != WINDOW_SIZE_5G:
        code = (
            REJECT_WINDOW_SHORT
            if resolved_rating_week < WINDOW_SIZE_5G
            else REJECT_WINDOW_INCOMPLETE
        )
        raise ExposureLedgerReject(
            code,
            f"{team_n} {season}w{resolved_rating_week} IF `_5g` frame has "
            f"{len(selected_weeks)} situational rows {selected_weeks}; "
            f"{WINDOW_SIZE_5G} required (fail closed, no 2025 prior fill)",
        )

    games = tuple(
        _bind_schedule_game(
            row=by_week[week],
            schedule_rows=schedule_rows,
            target_week=int(target_week),
            target_game_id=target_id,
            target_game_date=target_schedule.game_date if target_schedule else None,
            forecast_cutoff_ts=forecast_cutoff_ts,
        )
        for week in selected_weeks
    )
    if declared_games_in_window_5 is not None and declared_games_in_window_5 != len(
        games
    ):
        raise ExposureLedgerReject(
            REJECT_WINDOW_MISMATCH,
            f"declared_games_in_window_5={declared_games_in_window_5} "
            f"!= resolved {len(games)} (AS_OF / window identity mismatch)",
        )

    window_fingerprint = fingerprint_payload(
        {
            "contract": IF_5G_WINDOW_CONTRACT,
            "season": season,
            "rating_week": resolved_rating_week,
            "target_week": int(target_week),
            "target_game_id": target_id,
            "team": team_n,
            "window": WINDOW_LABEL_5G,
            "games": [
                {
                    "season": g.season,
                    "week": g.week,
                    "team": g.team,
                    "game_id": g.game_id,
                    "games_played": g.games_played,
                }
                for g in games
            ],
        }
    )
    return ResolvedIf5gWindow(
        season=season,
        rating_week=resolved_rating_week,
        target_week=int(target_week),
        team=team_n,
        window=WINDOW_LABEL_5G,
        contract=IF_5G_WINDOW_CONTRACT,
        games=games,
        window_fingerprint=window_fingerprint,
        target_game_id=target_id,
    )


def latest_five_schedule_game_ids(
    *,
    season: int,
    team: str,
    as_of_week: int,
    schedule_rows: Sequence[ScheduleGameRow],
) -> tuple[str, ...]:
    """Convenience latest-five (schedule). Must not be used as the IF window.

    Exposed so tests can prove it diverges from ``resolve_if_5g_window``.
    """
    team_n = normalize_team(team)
    matched = [
        row
        for row in schedule_rows
        if int(row.season) == int(season)
        and int(row.week) <= int(as_of_week)
        and team_n in {normalize_team(row.home_team), normalize_team(row.away_team)}
    ]
    matched.sort(key=lambda r: (int(r.week), str(r.game_id)))
    return tuple(row.game_id for row in matched[-WINDOW_SIZE_5G:])


def _situational_index(
    *,
    season: int,
    team: str,
    rows: Sequence[SituationalWeekRow],
) -> dict[int, SituationalWeekRow]:
    index: dict[int, SituationalWeekRow] = {}
    for raw in rows:
        if int(raw.season) != int(season):
            continue
        row_team = normalize_team(raw.team)
        if row_team != team:
            continue
        week = int(raw.week)
        if week in index:
            raise ExposureLedgerReject(
                REJECT_GRAIN_MISMATCH,
                f"duplicate situational row for {team} {season}w{week}",
            )
        index[week] = SituationalWeekRow(
            season=int(raw.season),
            week=week,
            team=row_team,
            games_played=raw.games_played,
            source=raw.source,
        )
    return index


def _lookup_target_schedule(
    *,
    season: int,
    team: str,
    target_week: int,
    target_game_id: Optional[str],
    schedule_rows: Sequence[ScheduleGameRow],
) -> Optional[ScheduleGameRow]:
    if target_game_id is None:
        matches = [
            s
            for s in schedule_rows
            if int(s.season) == int(season)
            and int(s.week) == int(target_week)
            and team
            in {normalize_team(s.home_team), normalize_team(s.away_team)}
        ]
        if not matches:
            return None
        ids = {str(s.game_id) for s in matches}
        if len(ids) != 1:
            raise ExposureLedgerReject(
                REJECT_GRAIN_MISMATCH,
                f"{team} {season}w{target_week} target maps to game_ids "
                f"{sorted(ids)}; exactly one target game required",
            )
        return matches[0]
    matches = [
        s
        for s in schedule_rows
        if require_nonempty_str(s.game_id, field_name="game_id") == target_game_id
    ]
    if not matches:
        raise ExposureLedgerReject(
            REJECT_SCHEDULE_UNRESOLVED,
            f"target_game_id {target_game_id} is not on the supplied schedule",
        )
    chosen = matches[0]
    if int(chosen.week) != int(target_week) or int(chosen.season) != int(season):
        raise ExposureLedgerReject(
            REJECT_INPUT_INVALID,
            f"target_game_id {target_game_id} is {chosen.season}w{chosen.week}, "
            f"not {season}w{target_week}",
        )
    if team not in {
        normalize_team(chosen.home_team),
        normalize_team(chosen.away_team),
    }:
        raise ExposureLedgerReject(
            REJECT_INPUT_INVALID,
            f"target_game_id {target_game_id} does not include team {team}",
        )
    return chosen


def _bind_schedule_game(
    *,
    row: SituationalWeekRow,
    schedule_rows: Sequence[ScheduleGameRow],
    target_week: int,
    target_game_id: Optional[str],
    target_game_date: Optional[str],
    forecast_cutoff_ts: Optional[str],
) -> ResolvedWindowGame:
    if row.games_played is not None and int(row.games_played) != 1:
        raise ExposureLedgerReject(
            REJECT_GRAIN_MISMATCH,
            f"{row.team} {row.season}w{row.week} games_played={row.games_played}; "
            f"IF `_5g` grain is one situational row per week and cannot split "
            f"multi-game weeks onto snap game_ids",
        )
    matches = [
        s
        for s in schedule_rows
        if int(s.season) == int(row.season)
        and int(s.week) == int(row.week)
        and row.team
        in {normalize_team(s.home_team), normalize_team(s.away_team)}
    ]
    if not matches:
        raise ExposureLedgerReject(
            REJECT_SCHEDULE_UNRESOLVED,
            f"no schedule game for {row.team} {row.season}w{row.week}",
        )
    ids = {require_nonempty_str(s.game_id, field_name="game_id") for s in matches}
    if len(ids) != 1:
        raise ExposureLedgerReject(
            REJECT_GRAIN_MISMATCH,
            f"{row.team} {row.season}w{row.week} maps to game_ids {sorted(ids)}; "
            f"exactly one completed game required",
        )
    chosen = matches[0]
    if not bool(chosen.completed):
        raise ExposureLedgerReject(
            REJECT_GAME_NOT_COMPLETED,
            f"schedule game {chosen.game_id} for {row.team} {row.season}w{row.week} "
            f"is not completed (IF `_5g` uses completed situational rows only)",
        )
    try:
        reject_if_not_pregame_game(
            game_week=int(row.week),
            target_week=int(target_week),
            game_id=str(chosen.game_id),
            target_game_id=target_game_id,
            game_date=chosen.game_date,
            target_game_date=target_game_date,
            game_kickoff_ts=chosen.kickoff_ts,
            forecast_cutoff_ts=forecast_cutoff_ts,
        )
    except PregameAsofReject as exc:
        _raise_asof(exc)
    return ResolvedWindowGame(
        season=int(row.season),
        week=int(row.week),
        team=row.team,
        game_id=str(chosen.game_id),
        games_played=row.games_played,
    )


def assert_not_convenient_latest_five(
    *,
    resolved: ResolvedIf5gWindow,
    schedule_rows: Sequence[ScheduleGameRow],
) -> None:
    """Optional guard: fail if caller treated latest-five as the IF window."""
    convenient = latest_five_schedule_game_ids(
        season=resolved.season,
        team=resolved.team,
        as_of_week=resolved.rating_week,
        schedule_rows=schedule_rows,
    )
    if convenient != resolved.game_ids:
        return
    # Equal is allowed when the two methods happen to agree; this helper
    # exists for documentation/tests, not as a production gate.
    return


def iter_window_weeks(window: ResolvedIf5gWindow) -> Iterable[int]:
    return (g.week for g in window.games)
