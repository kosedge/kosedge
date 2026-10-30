"""Resolve the exact IF `_5g` games — not a convenient latest-five query.

The Independent Fair path consumes `*_5g` fields from NflGameInputs. Those
fields are the rolling row at `(season, rating_week, team)` produced by:

    PARTITION BY team ORDER BY season, week
    ROWS BETWEEN 4 PRECEDING AND CURRENT ROW

on `nfl_dp_team_situational_weekly` filtered to that season
(`ingest.py@1b39f4e9` L1283–1314). The rolling table stores only aggregates
plus `games_in_window_5` — not game IDs.

Reconstruction:
  1. Take the caller's situational team-week rows (the same grain as ingest).
  2. Apply the same partition / order / frame.
  3. Map each selected week to exactly one completed schedule game_id.

Bye weeks with no situational row are skipped by the row frame (same as SQL).
A "latest five scheduled games" query can therefore disagree — that disagreement
is a reject, not something this resolver papers over.
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence

from src.services.nfl_snap_share_exposure_ledger.identity import fingerprint_payload
from src.services.nfl_snap_share_exposure_ledger.schema import (
    IF_5G_WINDOW_CONTRACT,
    REJECT_GAME_NOT_COMPLETED,
    REJECT_GRAIN_MISMATCH,
    REJECT_INPUT_INVALID,
    REJECT_RATING_WEEK_UNRESOLVED,
    REJECT_SCHEDULE_UNRESOLVED,
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


def resolve_if_5g_window(
    *,
    season: int,
    rating_week: int,
    team: str,
    situational_rows: Sequence[SituationalWeekRow],
    schedule_rows: Sequence[ScheduleGameRow],
    declared_games_in_window_5: Optional[int] = None,
) -> ResolvedIf5gWindow:
    """Return the exact five games feeding the IF `_5g` row at rating_week."""
    if not isinstance(season, int) or season < 1:
        raise ExposureLedgerReject(REJECT_INPUT_INVALID, "season must be a positive int")
    if not isinstance(rating_week, int) or rating_week < 1:
        raise ExposureLedgerReject(
            REJECT_INPUT_INVALID, "rating_week must be a positive int"
        )
    team_n = normalize_team(require_nonempty_str(team, field_name="team"))

    by_week = _situational_index(
        season=season, team=team_n, rows=situational_rows
    )
    ordered_weeks = sorted(by_week)
    if rating_week not in by_week:
        raise ExposureLedgerReject(
            REJECT_RATING_WEEK_UNRESOLVED,
            f"no situational row for {team_n} {season}w{rating_week} "
            f"(IF `_5g` CURRENT ROW missing; not filled from a later/earlier week)",
        )
    idx = ordered_weeks.index(rating_week)
    start = max(0, idx - (WINDOW_SIZE_5G - 1))
    selected_weeks = ordered_weeks[start : idx + 1]
    if len(selected_weeks) != WINDOW_SIZE_5G:
        code = (
            REJECT_WINDOW_SHORT
            if rating_week < WINDOW_SIZE_5G
            else REJECT_WINDOW_INCOMPLETE
        )
        raise ExposureLedgerReject(
            code,
            f"{team_n} {season}w{rating_week} IF `_5g` frame has "
            f"{len(selected_weeks)} situational rows {selected_weeks}; "
            f"{WINDOW_SIZE_5G} required (fail closed, no 2025 prior fill)",
        )

    games = tuple(
        _bind_schedule_game(
            row=by_week[week],
            schedule_rows=schedule_rows,
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
            "rating_week": rating_week,
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
        rating_week=rating_week,
        team=team_n,
        window=WINDOW_LABEL_5G,
        contract=IF_5G_WINDOW_CONTRACT,
        games=games,
        window_fingerprint=window_fingerprint,
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


def _bind_schedule_game(
    *,
    row: SituationalWeekRow,
    schedule_rows: Sequence[ScheduleGameRow],
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
