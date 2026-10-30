"""Research-only `_5g` exposure materializer tests (t4833u).

Coverage, consistency, completeness, leakage. No admit, no scoring.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.services.nfl_research_5g_exposure import (
    EXPECTED_INPUT_SHA256,
    GRAIN_RESIDUAL,
    GRAIN_WINDOW,
    RESEARCH_LEDGER_SCHEMA_VERSION,
    STATE_CONFLICT,
    STATE_MEASURED,
    STATE_MISSING,
    STATE_UNKNOWN,
    STATE_UNRESOLVED,
    STATE_VERIFIED_ZERO,
    ResearchExposureReject,
    build_research_5g_exposure_rows,
    parse_pfr_game_date,
    split_nflverse_game_id,
    verify_staged_input_hashes,
    worst_state,
)
from src.services.nfl_snap_share_exposure_ledger.schema import STARTER_LABEL_THRESHOLD

SEASON = 2026
TEAM = "AAA"
OPP = "BBB"
HASHES = {
    "snap_counts_2026.parquet": "aa" * 32,
    "players.parquet": "bb" * 32,
    "roster_weekly_2026.parquet": "cc" * 32,
}


def _gid(week: int) -> str:
    return f"{SEASON}_{week:02d}_{OPP}_{TEAM}"


def _pfr_gid(week: int) -> str:
    # Sunday slate: week 1 = 2026-09-13, then +7 days.
    day = 13 + 7 * (week - 1)
    month = 9
    if day > 30:
        day -= 30
        month = 10
    return f"2026{month:02d}{day:02d}aaa"


def _snap(
    week: int,
    pfr: str,
    name: str,
    position: str,
    *,
    off_s=10.0,
    off_p=1.0,
    def_s=0.0,
    def_p=0.0,
    st_s=0.0,
    st_p=0.0,
    team: str = TEAM,
    opp: str = OPP,
) -> dict:
    return {
        "game_id": _gid(week),
        "pfr_game_id": _pfr_gid(week),
        "season": SEASON,
        "game_type": "REG",
        "week": week,
        "player": name,
        "pfr_player_id": pfr,
        "position": position,
        "team": team,
        "opponent": opp,
        "offense_snaps": off_s,
        "offense_pct": off_p,
        "defense_snaps": def_s,
        "defense_pct": def_p,
        "st_snaps": st_s,
        "st_pct": st_p,
    }


def _player(pfr: str, gsis: str, name: str, position: str) -> dict:
    return {
        "pfr_id": pfr,
        "gsis_id": gsis,
        "display_name": name,
        "position": position,
    }


def _roster(
    week: int,
    pfr: str,
    gsis: str,
    name: str,
    position: str,
    *,
    status: str = "ACT",
    team: str = TEAM,
) -> dict:
    return {
        "season": SEASON,
        "team": team,
        "week": week,
        "position": position,
        "depth_chart_position": position,
        "status": status,
        "full_name": name,
        "gsis_id": gsis,
        "pfr_id": pfr,
        "game_type": "REG",
    }


def _core_snaps() -> list[dict]:
    rows = []
    for week in range(1, 7):
        rows.append(_snap(week, "QBxxAa00", "Synth QB", "QB", off_s=65.0, off_p=1.0))
        rows.append(
            _snap(week, "WRxxAa00", "Synth WR", "WR", off_s=50.0 if week != 3 else 0.0, off_p=0.8 if week != 3 else 0.0)
        )
        rows.append(_snap(week, "CBxxAa00", "Synth CB", "CB", off_s=0.0, off_p=0.0, def_s=55.0, def_p=0.9))
        # opponent book so the other side exists on the schedule
        rows.append(
            _snap(
                week,
                "QBxxBb00",
                "Opp QB",
                "QB",
                off_s=60.0,
                off_p=1.0,
                team=OPP,
                opp=TEAM,
            )
        )
    return rows


def _core_players() -> list[dict]:
    return [
        _player("QBxxAa00", "00-0000001", "Synth QB", "QB"),
        _player("WRxxAa00", "00-0000002", "Synth WR", "WR"),
        _player("CBxxAa00", "00-0000003", "Synth CB", "CB"),
        _player("QBxxBb00", "00-0000099", "Opp QB", "QB"),
    ]


def _core_roster() -> list[dict]:
    rows = []
    for week in range(1, 7):
        rows.append(_roster(week, "QBxxAa00", "00-0000001", "Synth QB", "QB"))
        rows.append(_roster(week, "WRxxAa00", "00-0000002", "Synth WR", "WR"))
        rows.append(_roster(week, "CBxxAa00", "00-0000003", "Synth CB", "CB"))
        rows.append(_roster(week, "QBxxBb00", "00-0000099", "Opp QB", "QB", team=OPP))
    return rows


def _build(snaps=None, players=None, roster=None):
    return build_research_5g_exposure_rows(
        snap_rows=snaps if snaps is not None else _core_snaps(),
        player_rows=players if players is not None else _core_players(),
        roster_rows=roster if roster is not None else _core_roster(),
        source_hashes=HASHES,
    )


def _window(rows, *, gsis=None, pfr=None, team=TEAM):
    matched = [
        r
        for r in rows
        if r["row_grain"] == GRAIN_WINDOW
        and r["team"] == team
        and (gsis is None or r["player_gsis_id"] == gsis)
        and (pfr is None or r["player_pfr_id"] == pfr)
    ]
    return matched


def test_pfr_game_date_from_pfr_game_id():
    assert parse_pfr_game_date("202609130sdg") == "2026-09-13"
    with pytest.raises(ResearchExposureReject) as exc:
        parse_pfr_game_date("nogood")
    assert exc.value.code == "GAME_DATE_UNRESOLVED"


def test_game_id_split_away_home():
    season, week, away, home = split_nflverse_game_id("2026_01_ARI_LAC")
    assert (season, week, away, home) == (2026, 1, "ARI", "LAC")


def test_worst_state_never_collapses_conflict_into_zero():
    assert worst_state([STATE_MEASURED, STATE_VERIFIED_ZERO]) == STATE_MEASURED
    assert worst_state([STATE_MEASURED, STATE_UNKNOWN]) == STATE_UNKNOWN
    assert worst_state([STATE_UNKNOWN, STATE_UNRESOLVED]) == STATE_UNRESOLVED
    assert worst_state([STATE_UNRESOLVED, STATE_CONFLICT]) == STATE_CONFLICT
    assert worst_state([STATE_MISSING, STATE_VERIFIED_ZERO]) == STATE_MISSING


def test_window_is_five_completed_games_before_target():
    rows, stats = _build()
    windows = [r for r in rows if r["row_grain"] == GRAIN_WINDOW and r["team"] == TEAM]
    assert windows
    assert stats["n_targets_populated"] >= 1
    for row in windows:
        assert row["target_week"] == 6
        assert row["rating_week"] == 5
        assert row["target_game_id"] == _gid(6)
        assert row["window_game_ids"] == [_gid(w) for w in (1, 2, 3, 4, 5)]
        assert row["window_weeks"] == [1, 2, 3, 4, 5]
        assert row["schema_version"] == RESEARCH_LEDGER_SCHEMA_VERSION
        assert row["research_only"] is True
        assert row["admitted"] is False
        assert row["return_uncredited"] is True


def test_leakage_target_game_not_in_own_window():
    rows, stats = _build()
    assert stats["leakage_target_in_window"] == []
    for row in rows:
        if row["row_grain"] != GRAIN_WINDOW:
            continue
        assert row["target_game_id"] not in row["window_game_ids"]
        assert all(w < row["target_week"] for w in row["window_weeks"])
        assert all(d < row["target_game_date"] for d in row["window_game_dates"])
        assert row["rating_week"] == row["target_week"] - 1


def test_bye_week_minus_one_does_not_substitute_latest_five():
    """CIN-style: 6th game after a W-1 bye cannot invent a window."""
    snaps = []
    players = list(_core_players())
    roster = []
    played = (1, 2, 3, 4, 5, 7)
    for week in played:
        gid_week = week
        snaps.append(_snap(gid_week, "QBxxAa00", "Synth QB", "QB", off_s=65.0, off_p=1.0))
        snaps.append(
            _snap(
                gid_week,
                "QBxxBb00",
                "Opp QB",
                "QB",
                off_s=60.0,
                off_p=1.0,
                team=OPP,
                opp=TEAM,
            )
        )
        roster.append(_roster(week, "QBxxAa00", "00-0000001", "Synth QB", "QB"))
        roster.append(_roster(week, "QBxxBb00", "00-0000099", "Opp QB", "QB", team=OPP))
    rows, stats = _build(snaps=snaps, players=players, roster=roster)
    aaa_windows = [
        r
        for r in rows
        if r["row_grain"] == GRAIN_WINDOW and r["team"] == TEAM and r["target_week"] == 7
    ]
    assert aaa_windows == []
    skipped = [s for s in stats["skipped_targets"] if s["team"] == TEAM and s["target_week"] == 7]
    assert skipped
    assert skipped[0]["reject_code"] in {
        "RATING_WEEK_UNRESOLVED",
        "WINDOW_SHORT",
        "WINDOW_INCOMPLETE",
    }


def test_measured_mean_and_starter_label_derived_only():
    rows, _ = _build()
    qb = _window(rows, gsis="00-0000001")
    assert len(qb) == 1
    row = qb[0]
    assert row["row_state"] == STATE_MEASURED
    assert row["embedded_snap_share"] == pytest.approx(1.0)
    assert row["starter_label_derived"] is True
    assert row["starter_label_derived"] is (
        row["embedded_snap_share"] >= STARTER_LABEL_THRESHOLD
    )


def test_verified_zero_in_snap_file_stays_in_mean():
    rows, _ = _build()
    wr = _window(rows, gsis="00-0000002")
    assert len(wr) == 1
    row = wr[0]
    assert row["game_participation_status"][2] == STATE_VERIFIED_ZERO
    assert row["game_snap_shares"][2] == 0.0
    assert row["embedded_snap_share"] == pytest.approx((0.8 + 0.8 + 0.0 + 0.8 + 0.8) / 5.0)
    assert row["row_state"] == STATE_MEASURED


def test_act_absent_is_unknown_not_verified_zero():
    snaps = _core_snaps()
    snaps = [s for s in snaps if not (s["pfr_player_id"] == "WRxxAa00" and s["week"] == 4)]
    roster = _core_roster()
    rows, _ = _build(snaps=snaps, roster=roster)
    wr = _window(rows, gsis="00-0000002")
    assert len(wr) == 1
    row = wr[0]
    assert row["game_participation_status"][3] == STATE_UNKNOWN
    assert row["game_snap_shares"][3] is None
    assert row["embedded_snap_share"] is None
    assert row["starter_label_derived"] is None
    assert row["row_state"] == STATE_UNKNOWN
    residuals = [
        r
        for r in rows
        if r["row_grain"] == GRAIN_RESIDUAL
        and r["row_state_reason"] == "act_absent_unconfirmed"
        and r["player_gsis_id"] == "00-0000002"
    ]
    assert len(residuals) == 1


def test_unresolved_identity_flagged_exposure_null():
    snaps = _core_snaps()
    for week in range(1, 7):
        snaps.append(_snap(week, "AndeAl01", "Alec Anderson", "C", off_s=20.0, off_p=0.4))
    rows, _ = _build(snaps=snaps)
    residuals = [
        r
        for r in rows
        if r["row_grain"] == GRAIN_RESIDUAL and r["player_pfr_id"] == "AndeAl01"
    ]
    assert len(residuals) == 6
    assert all(r["row_state"] == STATE_UNRESOLVED for r in residuals)
    assert all(r["player_gsis_id"] is None for r in residuals)
    window = _window(rows, pfr="AndeAl01")
    assert window
    assert all(r["row_state"] == STATE_UNRESOLVED for r in window)
    assert all(r["embedded_snap_share"] is None for r in window)


def test_conflict_flagged_no_adjudication():
    snaps = _core_snaps()
    players = _core_players() + [_player("WoodPe00", "WOO547869", "Peter Woods", "DL")]
    roster = _core_roster()
    for week in range(1, 7):
        snaps.append(
            _snap(week, "WoodPe00", "Peter Woods", "DL", off_s=0.0, off_p=0.0, def_s=40.0, def_p=0.7)
        )
        roster.append(_roster(week, "WoodPe00", "00-0041545", "Peter Woods", "DL"))
    rows, _ = _build(snaps=snaps, players=players, roster=roster)
    residuals = [
        r
        for r in rows
        if r["row_grain"] == GRAIN_RESIDUAL
        and r["player_pfr_id"] == "WoodPe00"
        and r["row_state"] == STATE_CONFLICT
    ]
    assert len(residuals) == 6
    assert all(r["player_gsis_id"] is None for r in residuals)
    assert all(r["player_gsis_id_players"] == "WOO547869" for r in residuals)
    assert all(r["player_gsis_id_roster"] == "00-0041545" for r in residuals)
    window = _window(rows, pfr="WoodPe00")
    assert window
    assert all(r["row_state"] == STATE_CONFLICT for r in window)
    assert all(r["embedded_snap_share"] is None for r in window)


def test_denominators_from_max_snaps_not_pct():
    rows, _ = _build()
    qb = _window(rows, gsis="00-0000001")[0]
    assert qb["offense_denoms"] == [65.0, 65.0, 65.0, 65.0, 65.0]
    assert qb["defense_denoms"] == [55.0, 55.0, 55.0, 55.0, 55.0]


def test_hash_mismatch_rejected():
    snap = Path("/tmp/t4833u_hash_snap.bin")
    players = Path("/tmp/t4833u_hash_players.bin")
    roster = Path("/tmp/t4833u_hash_roster.bin")
    snap.write_bytes(b"snap")
    players.write_bytes(b"players")
    roster.write_bytes(b"roster")
    with pytest.raises(ResearchExposureReject) as exc:
        verify_staged_input_hashes(
            snap_path=snap,
            players_path=players,
            roster_path=roster,
            expected=EXPECTED_INPUT_SHA256,
        )
    assert exc.value.code == "INPUT_HASH_MISMATCH"


def test_distinct_states_present_in_mixed_universe():
    snaps = _core_snaps()
    players = _core_players() + [_player("WoodPe00", "WOO547869", "Peter Woods", "DL")]
    roster = _core_roster()
    for week in range(1, 7):
        snaps.append(_snap(week, "AndeAl01", "Alec Anderson", "C", off_s=10.0, off_p=0.2))
        snaps.append(
            _snap(week, "WoodPe00", "Peter Woods", "DL", off_s=0.0, off_p=0.0, def_s=30.0, def_p=0.5)
        )
        roster.append(_roster(week, "WoodPe00", "00-0041545", "Peter Woods", "DL"))
        roster.append(_roster(week, "INAxxAa00", "00-0007777", "Inactive Guy", "WR", status="INA"))
    snaps = [s for s in snaps if not (s["pfr_player_id"] == "WRxxAa00" and s["week"] == 2)]
    rows, _ = _build(snaps=snaps, players=players, roster=roster)
    window_states = {r["row_state"] for r in rows if r["row_grain"] == GRAIN_WINDOW}
    residual_states = {r["row_state"] for r in rows if r["row_grain"] == GRAIN_RESIDUAL}
    assert STATE_MEASURED in window_states
    assert STATE_UNRESOLVED in residual_states
    assert STATE_CONFLICT in residual_states
    assert STATE_UNKNOWN in residual_states
    # states stay distinct tokens — never rewritten as 0
    for row in rows:
        if row["row_state"] in {STATE_UNKNOWN, STATE_UNRESOLVED, STATE_CONFLICT, STATE_MISSING}:
            assert row["embedded_snap_share"] is None


def test_st_only_position_is_unknown_not_guessed_side():
    snaps = _core_snaps()
    players = _core_players() + [_player("KxxxAa00", "00-0000044", "Synth K", "K")]
    roster = _core_roster()
    for week in range(1, 7):
        snaps.append(
            _snap(week, "KxxxAa00", "Synth K", "K", off_s=0.0, off_p=0.0, def_s=0.0, def_p=0.0, st_s=8.0, st_p=0.7)
        )
        roster.append(_roster(week, "KxxxAa00", "00-0000044", "Synth K", "K"))
    rows, _ = _build(snaps=snaps, players=players, roster=roster)
    kicker = _window(rows, gsis="00-0000044")
    assert kicker
    assert all(r["side"] is None for r in kicker)
    assert all(r["row_state"] == STATE_UNKNOWN for r in kicker)
    assert all(r["embedded_snap_share"] is None for r in kicker)


@pytest.mark.skipif(
    not Path("/workspace/data/research/nfl/t4833u/snap_share_5g_exposure_ledger.parquet").exists(),
    reason="sealed research parquet not on tree yet",
)
def test_sealed_artifact_coverage_and_no_leakage():
    import pyarrow.parquet as pq

    path = Path("/workspace/data/research/nfl/t4833u/snap_share_5g_exposure_ledger.parquet")
    table = pq.read_table(path)
    rows = table.to_pylist()
    residuals = [r for r in rows if r["row_grain"] == GRAIN_RESIDUAL]
    windows = [r for r in rows if r["row_grain"] == GRAIN_WINDOW]
    unresolved = [r for r in residuals if r["row_state"] == STATE_UNRESOLVED]
    conflicts = [r for r in residuals if r["row_state"] == STATE_CONFLICT]
    act_absent = [r for r in residuals if r["row_state_reason"] == "act_absent_unconfirmed"]
    assert len(unresolved) == 18
    assert len(conflicts) == 6
    assert len(act_absent) == 325
    assert {r["player_pfr_id"] for r in unresolved} == {"AndeAl01", "WhitCo05", "OkoyCJ00"}
    assert {r["player_pfr_id"] for r in conflicts} == {"WoodPe00"}
    for row in windows:
        assert row["target_game_id"] not in (row["window_game_ids"] or [])
        assert row["rating_week"] == row["target_week"] - 1
        assert all(d < row["target_game_date"] for d in (row["window_game_dates"] or []))
        if row["row_state"] in {STATE_UNKNOWN, STATE_UNRESOLVED, STATE_CONFLICT, STATE_MISSING}:
            assert row["embedded_snap_share"] is None
            assert row["starter_label_derived"] is None
