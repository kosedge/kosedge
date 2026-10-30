"""Synthetic tests for the DRAFT snap-share `_5g` exposure ledger (t4818u).

No live snaps, no IF scoring, no nowcast, no #664 activate.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.services.nfl_snap_share_exposure_ledger import (
    FORBIDDEN_IMPORT_NAMES,
    IF_5G_WINDOW_CONTRACT,
    SOURCE_SYNTH_SNAP_COUNTS,
    WINDOW_LABEL_5G,
    ExposureLedgerReject,
    GameParticipationBundle,
    IdentityLink,
    ScheduleGameRow,
    SituationalWeekRow,
    SnapFact,
    assert_builder_isolated,
    build_snap_share_5g_exposure_ledger,
    latest_five_schedule_game_ids,
    resolve_if_5g_window,
)
from src.services.nfl_snap_share_exposure_ledger.schema import (
    REJECT_FUTURE_GAME_IN_WINDOW,
    REJECT_GAME_NOT_COMPLETED,
    REJECT_GRAIN_MISMATCH,
    REJECT_ID_UNMAPPED,
    REJECT_IDENTITY_COLLISION,
    REJECT_INPUT_INVALID,
    REJECT_INVALID_SNAP_DENOMINATOR,
    REJECT_POSITION_SIDE_UNSUPPORTED,
    REJECT_POSITION_UNKNOWN,
    REJECT_RATING_WEEK_NOT_LAGGED,
    REJECT_RATING_WEEK_STALE,
    REJECT_SCHEDULE_UNRESOLVED,
    REJECT_SNAPS_INCOMPLETE,
    REJECT_SNAPS_MISSING,
    REJECT_SOURCE_UNSUPPORTED,
    REJECT_TARGET_WEEK_INVALID,
    REJECT_WINDOW_INCOMPLETE,
    REJECT_WINDOW_MISMATCH,
    REJECT_WINDOW_SHORT,
    REJECT_AS_OF_VIOLATION,
    REJECT_RATING_WEEK_UNRESOLVED,
)

SEASON = 2099
TEAM = "SYN"
RATING_WEEK = 8
TARGET_WEEK = 9
AS_OF = "2099-11-01T00:00:00Z"
FORECAST_CUTOFF = "2099-11-01T00:00:00Z"
SOURCE = SOURCE_SYNTH_SNAP_COUNTS

# Situational weeks feeding IF `_5g` at rating_week=8 for a Week-9 forecast
# (CURRENT ROW at completed-data week 8 + 4 preceding). Week 5 is on the
# schedule but missing from situational. Week 7 is a bye.
IF_WEEKS = (2, 3, 4, 6, 8)
SCHEDULE_WEEKS = (1, 2, 3, 4, 5, 6, 8, 9)


def _gid(week: int) -> str:
    return f"SYN-2099-{week:02d}"


def _kickoff(week: int) -> str:
    start = datetime(2099, 9, 6, 17, 0, tzinfo=timezone.utc)
    return (start + timedelta(days=7 * (week - 1))).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gdate(week: int) -> str:
    return _kickoff(week)[:10]


def _sit(weeks=IF_WEEKS) -> list[SituationalWeekRow]:
    return [
        SituationalWeekRow(season=SEASON, week=w, team=TEAM, games_played=1, source="synth")
        for w in weeks
    ]


def _sched(weeks=SCHEDULE_WEEKS, *, completed: bool = True) -> list[ScheduleGameRow]:
    return [
        ScheduleGameRow(
            season=SEASON,
            week=w,
            game_id=_gid(w),
            home_team=TEAM,
            away_team="OPP",
            completed=completed if w != 5 else True,
            game_date=_gdate(w),
            kickoff_ts=_kickoff(w),
        )
        for w in weeks
    ]


def _fact(
    week: int,
    pfr: str,
    name: str,
    position: str,
    *,
    offense_pct=None,
    defense_pct=None,
    offense_snaps=None,
    defense_snaps=None,
    source_id: str = SOURCE,
) -> SnapFact:
    return SnapFact(
        game_id=_gid(week),
        team=TEAM,
        player_pfr_id=pfr,
        player_name=name,
        position=position,
        offense_pct=offense_pct,
        defense_pct=defense_pct,
        source_id=source_id,
        as_of_ts=AS_OF,
        offense_snaps=offense_snaps,
        defense_snaps=defense_snaps,
    )


def _bundle(
    week: int,
    facts: list[SnapFact],
    *,
    completeness: str = "complete",
    source_id: str = SOURCE,
) -> GameParticipationBundle:
    return GameParticipationBundle(
        game_id=_gid(week),
        team=TEAM,
        source_id=source_id,
        as_of_ts=AS_OF,
        completeness=completeness,  # type: ignore[arg-type]
        facts=tuple(facts),
    )


def _identity() -> list[IdentityLink]:
    return [
        IdentityLink("PFR-QB1", "GSIS-QB1"),
        IdentityLink("PFR-WR1", "GSIS-WR1"),
        IdentityLink("PFR-CB1", "GSIS-CB1"),
        IdentityLink("PFR-RB1", "GSIS-RB1"),
    ]


def _core_facts(week: int, *, wr_present: bool = True) -> list[SnapFact]:
    facts = [
        _fact(week, "PFR-QB1", "Synth QB", "QB", offense_pct=1.0, offense_snaps=65),
        _fact(week, "PFR-CB1", "Synth CB", "CB", defense_pct=0.90, defense_snaps=55),
        _fact(week, "PFR-RB1", "Synth RB", "RB", offense_pct=0.50, offense_snaps=30),
    ]
    if wr_present:
        facts.append(
            _fact(week, "PFR-WR1", "Synth WR", "WR", offense_pct=0.75, offense_snaps=48)
        )
    return facts


def _complete_bundles(*, wr_absent_week: int | None = 4) -> list[GameParticipationBundle]:
    return [
        _bundle(w, _core_facts(w, wr_present=(wr_absent_week != w)))
        for w in IF_WEEKS
    ]


def _build(**overrides):
    kwargs = {
        "season": SEASON,
        "target_week": TARGET_WEEK,
        "rating_week": RATING_WEEK,
        "team": TEAM,
        "situational_rows": _sit(),
        "schedule_rows": _sched(),
        "participation_bundles": _complete_bundles(),
        "identity_links": _identity(),
        "as_of_ts": AS_OF,
        "forecast_cutoff_ts": FORECAST_CUTOFF,
        "declared_games_in_window_5": 5,
    }
    kwargs.update(overrides)
    return build_snap_share_5g_exposure_ledger(**kwargs)


def _resolve(**kwargs):
    kwargs.setdefault("forecast_cutoff_ts", FORECAST_CUTOFF)
    return resolve_if_5g_window(**kwargs)


def _row(ledger, gsis: str):
    matched = [r for r in ledger.rows if r.player_gsis_id == gsis]
    assert len(matched) == 1, gsis
    return matched[0]


def test_if_5g_window_uses_situational_frame_not_latest_five_schedule():
    window = _resolve(
        season=SEASON,
        target_week=TARGET_WEEK,
        rating_week=RATING_WEEK,
        team=TEAM,
        situational_rows=_sit(),
        schedule_rows=_sched(),
        declared_games_in_window_5=5,
    )
    convenient = latest_five_schedule_game_ids(
        season=SEASON,
        team=TEAM,
        as_of_week=RATING_WEEK,
        schedule_rows=_sched(),
    )
    assert window.game_ids == tuple(_gid(w) for w in IF_WEEKS)
    assert convenient == tuple(_gid(w) for w in (3, 4, 5, 6, 8))
    assert window.game_ids != convenient
    assert _gid(5) in convenient and _gid(5) not in window.game_ids
    assert _gid(2) in window.game_ids and _gid(2) not in convenient
    assert window.window == WINDOW_LABEL_5G
    assert window.contract == IF_5G_WINDOW_CONTRACT


def test_positive_exposure_includes_verified_zero_absence_in_mean():
    ledger = _build()
    assert ledger.window == WINDOW_LABEL_5G
    assert ledger.window_game_ids == tuple(_gid(w) for w in IF_WEEKS)
    assert all(row.window == WINDOW_LABEL_5G for row in ledger.rows)

    qb = _row(ledger, "GSIS-QB1")
    assert qb.side == "offense"
    assert qb.embedded_snap_share == pytest.approx(1.0)
    assert qb.starter_label_derived is True
    assert {e.participation_status for e in qb.game_exposures} == {"measured"}

    wr = _row(ledger, "GSIS-WR1")
    by_week = {e.week: e for e in wr.game_exposures}
    assert by_week[4].participation_status == "verified_zero"
    assert by_week[4].snap_pct == 0.0
    # (0.75 + 0.75 + 0 + 0.75 + 0.75) / 5 = 0.60 — absence is kept in the mean
    assert wr.embedded_snap_share == pytest.approx(0.60)
    assert wr.starter_label_derived is True
    assert by_week[2].snap_pct == pytest.approx(0.75)

    cb = _row(ledger, "GSIS-CB1")
    assert cb.side == "defense"
    assert cb.embedded_snap_share == pytest.approx(0.90)

    rb = _row(ledger, "GSIS-RB1")
    assert rb.starter_label_derived is True
    assert rb.embedded_snap_share == pytest.approx(0.50)


def test_verified_zero_is_not_the_same_as_incomplete_unknown():
    present = _build()
    wr_zero = _row(present, "GSIS-WR1").game_exposures
    zero_game = next(e for e in wr_zero if e.week == 4)
    assert zero_game.participation_status == "verified_zero"
    assert zero_game.snap_pct == 0.0

    incomplete = [
        b
        if b.game_id != _gid(4)
        else GameParticipationBundle(
            game_id=_gid(4),
            team=TEAM,
            source_id=SOURCE,
            as_of_ts=AS_OF,
            completeness="incomplete",
            facts=b.facts,
        )
        for b in _complete_bundles()
    ]
    with pytest.raises(ExposureLedgerReject) as exc:
        _build(participation_bundles=incomplete)
    assert exc.value.code == REJECT_SNAPS_INCOMPLETE
    assert "UNKNOWN" in exc.value.message
    assert "not interchangeable" in exc.value.message


def test_missing_snap_source_is_unknown_not_zero():
    missing = [b for b in _complete_bundles() if b.game_id != _gid(6)]
    with pytest.raises(ExposureLedgerReject) as exc:
        _build(participation_bundles=missing)
    assert exc.value.code == REJECT_SNAPS_MISSING
    assert "UNKNOWN" in exc.value.message


def test_empty_complete_bundle_fails_closed():
    empty = [
        b if b.game_id != _gid(3) else _bundle(3, [])
        for b in _complete_bundles()
    ]
    with pytest.raises(ExposureLedgerReject) as exc:
        _build(participation_bundles=empty)
    assert exc.value.code == REJECT_SNAPS_INCOMPLETE


def test_window_short_weeks_1_4_fail_closed():
    with pytest.raises(ExposureLedgerReject) as exc:
        _resolve(
            season=SEASON,
            target_week=4,
            rating_week=3,
            team=TEAM,
            situational_rows=_sit(weeks=(1, 2, 3)),
            schedule_rows=_sched(weeks=(1, 2, 3, 4)),
        )
    assert exc.value.code == REJECT_WINDOW_SHORT


def test_incomplete_window_after_week_4_fail_closed():
    with pytest.raises(ExposureLedgerReject) as exc:
        _resolve(
            season=SEASON,
            target_week=9,
            rating_week=8,
            team=TEAM,
            situational_rows=_sit(weeks=(6, 8)),
            schedule_rows=_sched(),
        )
    assert exc.value.code == REJECT_WINDOW_INCOMPLETE


def test_rating_week_without_situational_row_fail_closed():
    with pytest.raises(ExposureLedgerReject) as exc:
        _resolve(
            season=SEASON,
            target_week=8,
            rating_week=7,
            team=TEAM,
            situational_rows=_sit(),
            schedule_rows=_sched(),
        )
    assert exc.value.code == REJECT_RATING_WEEK_UNRESOLVED


def test_declared_window_count_mismatch_fail_closed():
    with pytest.raises(ExposureLedgerReject) as exc:
        _build(declared_games_in_window_5=4)
    assert exc.value.code == REJECT_WINDOW_MISMATCH


def test_multi_game_week_grain_mismatch_fail_closed():
    rows = _sit()
    rows[0] = SituationalWeekRow(
        season=SEASON, week=2, team=TEAM, games_played=2, source="synth"
    )
    with pytest.raises(ExposureLedgerReject) as exc:
        _resolve(
            season=SEASON,
            target_week=TARGET_WEEK,
            rating_week=RATING_WEEK,
            team=TEAM,
            situational_rows=rows,
            schedule_rows=_sched(),
        )
    assert exc.value.code == REJECT_GRAIN_MISMATCH


def test_two_schedule_games_same_week_fail_closed():
    sched = _sched() + [
        ScheduleGameRow(
            season=SEASON,
            week=6,
            game_id="SYN-2099-06B",
            home_team=TEAM,
            away_team="ZZZ",
            completed=True,
            game_date=_gdate(6),
            kickoff_ts=_kickoff(6),
        )
    ]
    with pytest.raises(ExposureLedgerReject) as exc:
        _resolve(
            season=SEASON,
            target_week=TARGET_WEEK,
            rating_week=RATING_WEEK,
            team=TEAM,
            situational_rows=_sit(),
            schedule_rows=sched,
        )
    assert exc.value.code == REJECT_GRAIN_MISMATCH


def test_uncompleted_schedule_game_fail_closed():
    sched = [
        ScheduleGameRow(
            season=SEASON,
            week=w,
            game_id=_gid(w),
            home_team=TEAM,
            away_team="OPP",
            completed=(w != 8),
            game_date=_gdate(w),
            kickoff_ts=_kickoff(w),
        )
        for w in SCHEDULE_WEEKS
    ]
    with pytest.raises(ExposureLedgerReject) as exc:
        _resolve(
            season=SEASON,
            target_week=TARGET_WEEK,
            rating_week=RATING_WEEK,
            team=TEAM,
            situational_rows=_sit(),
            schedule_rows=sched,
        )
    assert exc.value.code == REJECT_GAME_NOT_COMPLETED


def test_unmapped_pfr_identity_fail_closed():
    with pytest.raises(ExposureLedgerReject) as exc:
        _build(identity_links=_identity()[:-1])  # drop RB map
    assert exc.value.code == REJECT_ID_UNMAPPED


def test_empty_identity_map_fail_closed():
    with pytest.raises(ExposureLedgerReject) as exc:
        _build(identity_links=[])
    assert exc.value.code == REJECT_ID_UNMAPPED


def test_identity_collision_same_game_fail_closed():
    links = _identity() + [IdentityLink("PFR-QB1-NEW", "GSIS-QB1")]
    bundles = []
    for b in _complete_bundles():
        if b.game_id == _gid(8):
            extra = _fact(8, "PFR-QB1-NEW", "Synth QB", "QB", offense_pct=0.10)
            bundles.append(
                GameParticipationBundle(
                    game_id=b.game_id,
                    team=b.team,
                    source_id=b.source_id,
                    as_of_ts=b.as_of_ts,
                    completeness="complete",
                    facts=b.facts + (extra,),
                )
            )
        else:
            bundles.append(b)
    with pytest.raises(ExposureLedgerReject) as exc:
        _build(identity_links=links, participation_bundles=bundles)
    assert exc.value.code == REJECT_IDENTITY_COLLISION


def test_mid_window_pfr_change_same_gsis_is_one_player():
    links = _identity() + [IdentityLink("PFR-WR1-B", "GSIS-WR1")]
    bundles = []
    for b in _complete_bundles(wr_absent_week=None):
        if b.game_id == _gid(8):
            facts = [
                f
                if f.player_pfr_id != "PFR-WR1"
                else _fact(8, "PFR-WR1-B", "Synth WR", "WR", offense_pct=0.80, offense_snaps=50)
                for f in b.facts
            ]
            bundles.append(
                GameParticipationBundle(
                    game_id=b.game_id,
                    team=b.team,
                    source_id=b.source_id,
                    as_of_ts=b.as_of_ts,
                    completeness="complete",
                    facts=tuple(facts),
                )
            )
        else:
            bundles.append(b)
    ledger = _build(identity_links=links, participation_bundles=bundles)
    wr = _row(ledger, "GSIS-WR1")
    assert set(wr.player_pfr_ids) == {"PFR-WR1", "PFR-WR1-B"}
    assert wr.embedded_snap_share == pytest.approx((0.75 * 4 + 0.80) / 5)


def test_unsupported_provenance_fail_closed():
    bad = [
        b
        if b.game_id != _gid(2)
        else GameParticipationBundle(
            game_id=_gid(2),
            team=TEAM,
            source_id="web_scrape_guess",
            as_of_ts=AS_OF,
            completeness="complete",
            facts=tuple(
                SnapFact(
                    game_id=f.game_id,
                    team=f.team,
                    player_pfr_id=f.player_pfr_id,
                    player_name=f.player_name,
                    position=f.position,
                    offense_pct=f.offense_pct,
                    defense_pct=f.defense_pct,
                    source_id="web_scrape_guess",
                    as_of_ts=f.as_of_ts,
                    offense_snaps=f.offense_snaps,
                    defense_snaps=f.defense_snaps,
                )
                for f in b.facts
            ),
        )
        for b in _complete_bundles()
    ]
    with pytest.raises(ExposureLedgerReject) as exc:
        _build(participation_bundles=bad)
    assert exc.value.code == REJECT_SOURCE_UNSUPPORTED


def test_invalid_snap_denominator_fail_closed():
    bad = [
        b
        if b.game_id != _gid(2)
        else _bundle(
            2,
            [
                f
                if f.player_pfr_id != "PFR-QB1"
                else _fact(2, "PFR-QB1", "Synth QB", "QB", offense_pct=1.2, offense_snaps=65)
                for f in b.facts
            ],
        )
        for b in _complete_bundles()
    ]
    with pytest.raises(ExposureLedgerReject) as exc:
        _build(participation_bundles=bad)
    assert exc.value.code == REJECT_INVALID_SNAP_DENOMINATOR


def test_snaps_zero_with_positive_pct_fail_closed():
    bad = [
        b
        if b.game_id != _gid(2)
        else _bundle(
            2,
            [
                f
                if f.player_pfr_id != "PFR-QB1"
                else _fact(2, "PFR-QB1", "Synth QB", "QB", offense_pct=0.90, offense_snaps=0)
                for f in b.facts
            ],
        )
        for b in _complete_bundles()
    ]
    with pytest.raises(ExposureLedgerReject) as exc:
        _build(participation_bundles=bad)
    assert exc.value.code == REJECT_INVALID_SNAP_DENOMINATOR


def test_missing_side_pct_is_unknown_not_zero():
    bad = [
        b
        if b.game_id != _gid(2)
        else _bundle(
            2,
            [
                f
                if f.player_pfr_id != "PFR-QB1"
                else _fact(2, "PFR-QB1", "Synth QB", "QB", offense_pct=None, offense_snaps=65)
                for f in b.facts
            ],
        )
        for b in _complete_bundles()
    ]
    with pytest.raises(ExposureLedgerReject) as exc:
        _build(participation_bundles=bad)
    assert exc.value.code == REJECT_INVALID_SNAP_DENOMINATOR
    assert "UNKNOWN" in exc.value.message


def test_percent_scale_0_100_normalizes_like_ingest():
    bundles = [
        b
        if b.game_id != _gid(2)
        else _bundle(
            2,
            [
                f
                if f.player_pfr_id != "PFR-QB1"
                else _fact(2, "PFR-QB1", "Synth QB", "QB", offense_pct=100.0, offense_snaps=65)
                for f in b.facts
            ],
        )
        for b in _complete_bundles()
    ]
    ledger = _build(participation_bundles=bundles)
    qb = _row(ledger, "GSIS-QB1")
    assert qb.embedded_snap_share == pytest.approx(1.0)


def test_unknown_position_fail_closed():
    bad = [
        b
        if b.game_id != _gid(2)
        else _bundle(
            2,
            [
                f
                if f.player_pfr_id != "PFR-QB1"
                else _fact(2, "PFR-QB1", "Synth QB", "", offense_pct=1.0, offense_snaps=65)
                for f in b.facts
            ],
        )
        for b in _complete_bundles()
    ]
    with pytest.raises(ExposureLedgerReject) as exc:
        _build(participation_bundles=bad)
    assert exc.value.code == REJECT_POSITION_UNKNOWN


def test_special_teams_position_fail_closed():
    extra_links = _identity() + [IdentityLink("PFR-K1", "GSIS-K1")]
    bundles = [
        GameParticipationBundle(
            game_id=b.game_id,
            team=b.team,
            source_id=b.source_id,
            as_of_ts=b.as_of_ts,
            completeness="complete",
            facts=b.facts
            + (_fact(int(b.game_id[-2:]), "PFR-K1", "Synth K", "K", offense_pct=0.0),),
        )
        for b in _complete_bundles()
    ]
    with pytest.raises(ExposureLedgerReject) as exc:
        _build(identity_links=extra_links, participation_bundles=bundles)
    assert exc.value.code == REJECT_POSITION_SIDE_UNSUPPORTED


def test_as_of_in_the_future_of_ledger_bound_fail_closed():
    future = [
        GameParticipationBundle(
            game_id=b.game_id,
            team=b.team,
            source_id=b.source_id,
            as_of_ts="2099-12-01T00:00:00Z" if b.game_id == _gid(8) else b.as_of_ts,
            completeness="complete",
            facts=b.facts,
        )
        for b in _complete_bundles()
    ]
    with pytest.raises(ExposureLedgerReject) as exc:
        _build(participation_bundles=future)
    assert exc.value.code == REJECT_AS_OF_VIOLATION


def test_ledger_is_deterministic_and_reproducible():
    a = _build()
    b = _build()
    assert a.input_fingerprint == b.input_fingerprint
    assert a.output_fingerprint == b.output_fingerprint
    assert a.ledger_id == b.ledger_id
    assert a.window_fingerprint == b.window_fingerprint
    assert [r.row_fingerprint for r in a.rows] == [r.row_fingerprint for r in b.rows]
    assert a.input_fingerprint != a.output_fingerprint
    assert a.ledger_id.startswith("x5g_")


def test_identity_or_absence_change_changes_fingerprints():
    baseline = _build()
    no_absence = _build(participation_bundles=_complete_bundles(wr_absent_week=None))
    assert no_absence.output_fingerprint != baseline.output_fingerprint
    assert no_absence.input_fingerprint != baseline.input_fingerprint
    assert _row(no_absence, "GSIS-WR1").embedded_snap_share == pytest.approx(0.75)


def test_builder_package_is_isolated_from_live_paths():
    assert_builder_isolated()
    root = Path(__file__).resolve().parents[1] / "src/services/nfl_snap_share_exposure_ledger"
    for path in root.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                for name in FORBIDDEN_IMPORT_NAMES:
                    if name == "nflverse":
                        continue
                    assert name not in stripped, f"{path.name} imports {name}"


def test_current_row_at_rating_week_is_included():
    window = _resolve(
        season=SEASON,
        target_week=TARGET_WEEK,
        rating_week=RATING_WEEK,
        team=TEAM,
        situational_rows=_sit(),
        schedule_rows=_sched(),
    )
    assert window.target_week == TARGET_WEEK
    assert window.games[-1].week == RATING_WEEK
    assert window.games[-1].game_id == _gid(RATING_WEEK)
    assert _gid(TARGET_WEEK) not in window.game_ids


def test_missing_target_week_fail_closed():
    with pytest.raises(TypeError):
        _resolve(
            season=SEASON,
            rating_week=RATING_WEEK,
            team=TEAM,
            situational_rows=_sit(),
            schedule_rows=_sched(),
        )


def test_invalid_target_week_fail_closed():
    with pytest.raises(ExposureLedgerReject) as exc:
        _resolve(
            season=SEASON,
            target_week=0,
            rating_week=RATING_WEEK,
            team=TEAM,
            situational_rows=_sit(),
            schedule_rows=_sched(),
        )
    assert exc.value.code == REJECT_TARGET_WEEK_INVALID


def test_same_week_rating_is_target_leakage_fail_closed():
    with pytest.raises(ExposureLedgerReject) as exc:
        _resolve(
            season=SEASON,
            target_week=RATING_WEEK,
            rating_week=RATING_WEEK,
            team=TEAM,
            situational_rows=_sit(),
            schedule_rows=_sched(),
        )
    assert exc.value.code == REJECT_RATING_WEEK_NOT_LAGGED


def test_target_week_game_cannot_enter_if_window_or_ledger():
    leaked_sit = _sit(weeks=IF_WEEKS + (TARGET_WEEK,))
    leaked_sched = _sched()
    with pytest.raises(ExposureLedgerReject) as exc:
        _resolve(
            season=SEASON,
            target_week=TARGET_WEEK,
            rating_week=TARGET_WEEK,
            team=TEAM,
            situational_rows=leaked_sit,
            schedule_rows=leaked_sched,
        )
    assert exc.value.code == REJECT_RATING_WEEK_NOT_LAGGED

    window = _resolve(
        season=SEASON,
        target_week=TARGET_WEEK,
        rating_week=RATING_WEEK,
        team=TEAM,
        situational_rows=leaked_sit,
        schedule_rows=leaked_sched,
    )
    assert TARGET_WEEK not in {g.week for g in window.games}
    assert _gid(TARGET_WEEK) not in window.game_ids

    leaked_bundles = _complete_bundles() + [
        _bundle(TARGET_WEEK, _core_facts(TARGET_WEEK))
    ]
    ledger = _build(
        situational_rows=leaked_sit,
        schedule_rows=leaked_sched,
        participation_bundles=leaked_bundles,
    )
    assert _gid(TARGET_WEEK) not in ledger.window_game_ids
    for row in ledger.rows:
        assert _gid(TARGET_WEEK) not in row.game_ids


def test_future_week_game_cannot_enter_if_window_or_ledger():
    future_week = 10
    leaked_sit = _sit(weeks=IF_WEEKS + (future_week,))
    leaked_sched = _sched(weeks=SCHEDULE_WEEKS + (future_week,))
    window = _resolve(
        season=SEASON,
        target_week=TARGET_WEEK,
        rating_week=RATING_WEEK,
        team=TEAM,
        situational_rows=leaked_sit,
        schedule_rows=leaked_sched,
    )
    assert future_week not in {g.week for g in window.games}
    assert _gid(future_week) not in window.game_ids

    leaked_bundles = _complete_bundles() + [
        _bundle(future_week, _core_facts(future_week))
    ]
    ledger = _build(
        situational_rows=leaked_sit,
        schedule_rows=leaked_sched,
        participation_bundles=leaked_bundles,
    )
    assert _gid(future_week) not in ledger.window_game_ids


def test_rating_week_target_minus_2_is_stale():
    with pytest.raises(ExposureLedgerReject) as exc:
        _resolve(
            season=SEASON,
            target_week=TARGET_WEEK,
            rating_week=TARGET_WEEK - 2,
            team=TEAM,
            situational_rows=_sit(),
            schedule_rows=_sched(),
        )
    assert exc.value.code == REJECT_RATING_WEEK_STALE


def test_bye_at_target_minus_1_fail_closed_no_substitute():
    # Week 7 is a bye. Forecasting week 8 cannot silently use week 6.
    with pytest.raises(ExposureLedgerReject) as exc:
        _resolve(
            season=SEASON,
            target_week=8,
            team=TEAM,
            situational_rows=_sit(),
            schedule_rows=_sched(),
        )
    assert exc.value.code == REJECT_RATING_WEEK_UNRESOLVED
    assert "not filled" in exc.value.message


def test_target_game_id_stays_out_of_window():
    window = _resolve(
        season=SEASON,
        target_week=TARGET_WEEK,
        rating_week=RATING_WEEK,
        target_game_id=_gid(TARGET_WEEK),
        team=TEAM,
        situational_rows=_sit(),
        schedule_rows=_sched(),
    )
    assert window.target_game_id == _gid(TARGET_WEEK)
    assert _gid(TARGET_WEEK) not in window.game_ids

    with pytest.raises(ExposureLedgerReject) as exc:
        _resolve(
            season=SEASON,
            target_week=TARGET_WEEK,
            rating_week=RATING_WEEK,
            target_game_id=_gid(RATING_WEEK),
            team=TEAM,
            situational_rows=_sit(),
            schedule_rows=_sched(),
        )
    assert exc.value.code == REJECT_INPUT_INVALID


def test_window_game_date_on_or_after_target_fail_closed():
    sched = []
    for w in SCHEDULE_WEEKS:
        sched.append(
            ScheduleGameRow(
                season=SEASON,
                week=w,
                game_id=_gid(w),
                home_team=TEAM,
                away_team="OPP",
                completed=True,
                game_date="2099-11-02" if w == 8 else f"2099-10-{w:02d}",
                kickoff_ts=None,
            )
        )
    with pytest.raises(ExposureLedgerReject) as exc:
        _resolve(
            season=SEASON,
            target_week=TARGET_WEEK,
            rating_week=RATING_WEEK,
            target_game_id=_gid(TARGET_WEEK),
            team=TEAM,
            situational_rows=_sit(),
            schedule_rows=sched,
            forecast_cutoff_ts="2099-11-15T00:00:00Z",
        )
    assert exc.value.code == REJECT_FUTURE_GAME_IN_WINDOW


def test_forecast_cutoff_rejects_ledger_as_of_after_cutoff():
    with pytest.raises(ExposureLedgerReject) as exc:
        _build(forecast_cutoff_ts="2099-10-01T00:00:00Z")
    assert exc.value.code == REJECT_AS_OF_VIOLATION


def test_missing_forecast_cutoff_fail_closed():
    with pytest.raises(TypeError):
        resolve_if_5g_window(
            season=SEASON,
            target_week=TARGET_WEEK,
            rating_week=RATING_WEEK,
            team=TEAM,
            situational_rows=_sit(),
            schedule_rows=_sched(),
        )
    with pytest.raises(TypeError):
        build_snap_share_5g_exposure_ledger(
            season=SEASON,
            target_week=TARGET_WEEK,
            rating_week=RATING_WEEK,
            team=TEAM,
            situational_rows=_sit(),
            schedule_rows=_sched(),
            participation_bundles=_complete_bundles(),
            identity_links=_identity(),
            as_of_ts=AS_OF,
        )


def test_window_game_missing_kickoff_and_date_fail_closed():
    sched = [
        ScheduleGameRow(
            season=SEASON,
            week=w,
            game_id=_gid(w),
            home_team=TEAM,
            away_team="OPP",
            completed=True,
            game_date=None,
            kickoff_ts=None,
        )
        for w in SCHEDULE_WEEKS
    ]
    with pytest.raises(ExposureLedgerReject) as exc:
        _resolve(
            season=SEASON,
            target_week=TARGET_WEEK,
            rating_week=RATING_WEEK,
            team=TEAM,
            situational_rows=_sit(),
            schedule_rows=sched,
        )
    assert exc.value.code == REJECT_AS_OF_VIOLATION
    assert "kickoff_ts" in exc.value.message


def test_missing_target_week_schedule_fail_closed():
    with pytest.raises(ExposureLedgerReject) as exc:
        _resolve(
            season=SEASON,
            target_week=TARGET_WEEK,
            rating_week=RATING_WEEK,
            team=TEAM,
            situational_rows=_sit(),
            schedule_rows=_sched(weeks=IF_WEEKS),
        )
    assert exc.value.code == REJECT_SCHEDULE_UNRESOLVED
    assert "date guard cannot be skipped" in exc.value.message
