"""t5146u R4 last-played T2 selection — isolated opt-in research path.

Selects each team's most recent same-season T2 snapshot with
rating_week < target_week. Does not require exact target_week-1.

KEEP UNCHANGED: recon_driver exact-week lookup_t2(team, week-1), helper
7e77c57f, frozen matrices/forecasts, R2/R3 records. No new scoring or
tuning. T1/T2 trailing-five-played-games, T4, rest, and index formulas
are imported, not rewritten.

Labels: RECONSTRUCTED / RETRO_FIT. Publication/observation timestamps
are unverified. NOT a production-causal or real-time availability claim.

CERT=0. No 2020–21 reconstruction artifact is generated here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping, Sequence

from .recon_contract import _finite
from .recon_driver import LABEL_RECONSTRUCTED, LABEL_RETRO_FIT, t4_from_t2_sides

PATH_ID = "R4_LAST_PLAYED_T2_DEV"
SCHEMA_VERSION = "nfl-t5146u-r4-last-played-t2-v1"
KO_MINUS = timedelta(minutes=60)
T2_METRIC_KEYS = (
    "epa_per_play_offense_5g",
    "epa_per_play_defense_allowed_5g",
    "pass_rate_5g",
    "success_rate_offense_5g",
    "success_rate_defense_allowed_5g",
    "pressure_rate_generated_5g",
    "pressure_rate_allowed_5g",
    "red_zone_td_rate_5g",
)
LABELS = (LABEL_RECONSTRUCTED, LABEL_RETRO_FIT)
TIMESTAMP_UNVERIFIED = "unverified"


class LastPlayedRefuse(ValueError):
    """Fail-closed last-played T2 selection."""


@dataclass(frozen=True)
class LastPlayedSelection:
    team: str
    season: int
    target_week: int
    target_game_id: str
    selected_rating_week: int
    t2_row: dict[str, Any]
    last_five_source_game_ids: tuple[str, ...]
    consumed_game_ids: tuple[str, ...]
    newest_nonfinite: bool
    publication_timestamp_status: str = TIMESTAMP_UNVERIFIED
    observation_timestamp_status: str = TIMESTAMP_UNVERIFIED
    production_causal_claim: bool = False
    realtime_source_availability_claim: bool = False
    labels: tuple[str, ...] = LABELS
    path_id: str = PATH_ID
    notes: tuple[str, ...] = field(default_factory=tuple)


def parse_utc(raw: str) -> datetime:
    """Same contract as helper 7e77c57f parse_utc — naive timestamps refuse."""
    text = str(raw)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise LastPlayedRefuse(f"naive timestamp rejected: {raw!r}")
    return dt.astimezone(timezone.utc)


def ko_minus_60(kickoff_utc: str) -> datetime:
    return parse_utc(kickoff_utc) - KO_MINUS


def table_rows(table: Any) -> list[dict[str, Any]]:
    if table is None:
        return []
    if hasattr(table, "to_dict"):
        return [dict(row) for row in table.to_dict("records")]
    return [dict(row) for row in table]


def _cell(row: Mapping[str, Any], key: str) -> Any:
    return row[key]


def _as_int(value: Any, label: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise LastPlayedRefuse(f"{label} not an int: {value!r}") from exc


def _split_ids(raw: Any) -> list[str]:
    if raw is None:
        return []
    text = str(raw).strip()
    if not text or text.lower() == "nan":
        return []
    return [part for part in text.split("|") if part and part.lower() != "nan"]


def _metric_tuple(row: Mapping[str, Any]) -> tuple[Any, ...]:
    out: list[Any] = []
    for key in T2_METRIC_KEYS:
        value = row.get(key)
        if value is None:
            out.append(None)
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            out.append(("nonnumeric", str(value)))
            continue
        if math.isnan(number):
            out.append("nan")
        else:
            out.append(number)
    out.append(tuple(_split_ids(row.get("source_game_ids"))))
    return tuple(out)


def row_metrics_nonfinite(row: Mapping[str, Any]) -> bool:
    for key in T2_METRIC_KEYS:
        value = row.get(key)
        if value is None:
            return True
        try:
            number = float(value)
        except (TypeError, ValueError):
            return True
        if not _finite(number):
            return True
    return False


def _identity_index(
    games: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for raw in games:
        gid = str(raw["game_id"])
        if gid in index:
            prior = index[gid]
            if (
                prior.get("season") != raw.get("season")
                or prior.get("week") != raw.get("week")
                or prior.get("home") != raw.get("home")
                or prior.get("away") != raw.get("away")
                or prior.get("kickoff_utc") != raw.get("kickoff_utc")
            ):
                raise LastPlayedRefuse(
                    f"ambiguous conflicting game identity for {gid}"
                )
            continue
        index[gid] = dict(raw)
    return index


def last_five_source_game_ids(
    snapshots: Sequence[Mapping[str, Any]],
    *,
    team: str,
    season: int,
    rating_week: int,
) -> tuple[str, ...]:
    """Last five same-season played-game identities at or before rating_week.

    Ordering is T1/T2 played-week chronology (not a new window). Each
    snapshot's source_game_ids is that played week's identity, matching
    helper t1_from_plays / rolling_5g column retention.
    """
    prior = [
        row
        for row in snapshots
        if str(row["team"]) == team
        and _as_int(row["season"], "season") == season
        and _as_int(row["week"], "week") <= rating_week
    ]
    prior.sort(key=lambda row: (_as_int(row["week"], "week"), str(row.get("game_id", ""))))
    window = prior[-5:]
    ids: list[str] = []
    seen_weeks: list[int] = []
    for row in window:
        week = _as_int(row["week"], "week")
        if seen_weeks and week < seen_weeks[-1]:
            raise LastPlayedRefuse("prior-game week order is not chronological")
        seen_weeks.append(week)
        parts = _split_ids(row.get("source_game_ids"))
        if not parts:
            raise LastPlayedRefuse(
                f"unambiguous source-game identity missing team={team} week={week}"
            )
        ids.extend(parts)
    if not ids:
        raise LastPlayedRefuse(
            f"no last-five source-game identities team={team} rating_week={rating_week}"
        )
    return tuple(ids)


def assert_consumed_identities(
    game_ids: Iterable[str],
    *,
    games: Sequence[Mapping[str, Any]],
    target_game_id: str,
    target_kickoff_utc: str,
    target_season: int,
) -> tuple[str, ...]:
    """Consumed IDs must be unique, earlier than target KO−60, and not the target."""
    cutoff = ko_minus_60(target_kickoff_utc)
    index = _identity_index(games)
    ordered: list[tuple[datetime, str]] = []
    seen: set[str] = set()
    for gid in game_ids:
        if gid == target_game_id:
            raise LastPlayedRefuse(
                f"target game {target_game_id} excluded from consumed identities"
            )
        if gid in seen:
            raise LastPlayedRefuse(f"duplicate consumed game identity {gid}")
        seen.add(gid)
        rec = index.get(gid)
        if rec is None:
            raise LastPlayedRefuse(f"consumed game {gid} missing from identity catalog")
        if _as_int(rec["season"], "season") != target_season:
            raise LastPlayedRefuse(
                f"cross-season leakage consumed {gid} season={rec['season']}"
            )
        kick = rec.get("kickoff_utc")
        if not kick:
            raise LastPlayedRefuse(f"consumed game {gid} missing kickoff_utc")
        when = parse_utc(str(kick))
        if when >= cutoff:
            raise LastPlayedRefuse(
                f"KO-60 cutoff: consumed {gid} kickoff={kick} not < {cutoff.isoformat()}"
            )
        ordered.append((when, gid))
    chronological = tuple(gid for _, gid in sorted(ordered, key=lambda item: (item[0], item[1])))
    as_listed = tuple(game_ids)
    if as_listed != chronological:
        raise LastPlayedRefuse(
            f"consumed identities not chronological: {as_listed} vs {chronological}"
        )
    return chronological


def select_last_played_t2(
    t2: Any,
    *,
    team: str,
    season: int,
    target_week: int,
    target_game_id: str,
    target_kickoff_utc: str,
    games: Sequence[Mapping[str, Any]],
    t1: Any | None = None,
) -> LastPlayedSelection:
    """Opt-in last-played T2 snapshot for one side.

    Newest same-season row with week < target_week is selected even when
    nonfinite. Older finite rows are not substituted.
    """
    if target_week <= 1:
        raise LastPlayedRefuse(
            "W1_NO_PRIOR: rating_week < 1 / no last-played same-season snapshot"
        )
    rows = table_rows(t2)
    candidates = [
        row
        for row in rows
        if str(row.get("team")) == team
        and _as_int(row.get("season"), "season") == season
        and _as_int(row.get("week"), "week") < target_week
    ]
    other_season = [
        row
        for row in rows
        if str(row.get("team")) == team
        and _as_int(row.get("season"), "season") != season
    ]
    if not candidates:
        if other_season:
            raise LastPlayedRefuse(
                f"cross-season leakage refuse: team={team} has prior rows "
                f"only in other seasons; no same-season fill"
            )
        raise LastPlayedRefuse(
            f"W1_NO_PRIOR / no history: no same-season T2 with week < {target_week}"
        )
    selected_week = max(_as_int(row["week"], "week") for row in candidates)
    hits = [
        row for row in candidates if _as_int(row["week"], "week") == selected_week
    ]
    if len(hits) != 1:
        signatures = {_metric_tuple(row) for row in hits}
        reason = (
            "DUPLICATE_CONFLICT"
            if len(signatures) > 1
            else "AMBIGUOUS_DUPLICATE"
        )
        raise LastPlayedRefuse(
            f"{reason}: team={team} season={season} rating_week={selected_week} n={len(hits)}"
        )
    selected = dict(hits[0])
    snapshots = table_rows(t1) if t1 is not None else rows
    last_five = last_five_source_game_ids(
        snapshots,
        team=team,
        season=season,
        rating_week=selected_week,
    )
    consumed = assert_consumed_identities(
        last_five,
        games=games,
        target_game_id=target_game_id,
        target_kickoff_utc=target_kickoff_utc,
        target_season=season,
    )
    return LastPlayedSelection(
        team=team,
        season=season,
        target_week=target_week,
        target_game_id=target_game_id,
        selected_rating_week=selected_week,
        t2_row=selected,
        last_five_source_game_ids=last_five,
        consumed_game_ids=consumed,
        newest_nonfinite=row_metrics_nonfinite(selected),
        notes=(
            "RETRO_FIT / RECONSTRUCTED last-played T2; timestamps unverified; "
            "not a production-causal / real-time source-availability claim",
        ),
    )


def select_last_played_sides(
    t2: Any,
    *,
    home: str,
    away: str,
    season: int,
    target_week: int,
    target_game_id: str,
    target_kickoff_utc: str,
    games: Sequence[Mapping[str, Any]],
    t1: Any | None = None,
) -> tuple[LastPlayedSelection, LastPlayedSelection]:
    """Home and away selected independently."""
    home_sel = select_last_played_t2(
        t2,
        team=home,
        season=season,
        target_week=target_week,
        target_game_id=target_game_id,
        target_kickoff_utc=target_kickoff_utc,
        games=games,
        t1=t1,
    )
    away_sel = select_last_played_t2(
        t2,
        team=away,
        season=season,
        target_week=target_week,
        target_game_id=target_game_id,
        target_kickoff_utc=target_kickoff_utc,
        games=games,
        t1=t1,
    )
    return home_sel, away_sel


def t4_from_last_played(
    home_sel: LastPlayedSelection,
    away_sel: LastPlayedSelection,
) -> dict[str, float | None]:
    """Unchanged T4 contract on independently selected T2 rows."""
    return t4_from_t2_sides(home_sel.t2_row, away_sel.t2_row)


def exact_week_t2_row(t2: Any, team: str, rating_week: int) -> dict[str, Any] | None:
    """Mirror helper.lookup_t2 without importing pandas. Unchanged exact-week rule."""
    hits = [
        dict(row)
        for row in table_rows(t2)
        if str(row.get("team")) == team and _as_int(row.get("week"), "week") == rating_week
    ]
    if not hits:
        return None
    if len(hits) != 1:
        raise LastPlayedRefuse(
            f"non-unique exact-week T2 row team={team} week={rating_week}"
        )
    return hits[0]
