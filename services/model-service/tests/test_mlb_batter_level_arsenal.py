from __future__ import annotations

import os
from datetime import date

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

import src.services.mlb_pitch_matchup as pitch


def _contact_metrics(*, pitches: float, hard_whiff: float, hard_contact: float) -> dict:
    return {
        "pitches": pitches,
        "hard_pct_faced": 0.5,
        "break_pct_faced": 0.3,
        "soft_pct_faced": 0.2,
        "hard_whiff_pct": hard_whiff,
        "break_whiff_pct": 0.14,
        "soft_whiff_pct": 0.15,
        "hard_contact_pct": hard_contact,
        "break_contact_pct": 0.72,
        "soft_contact_pct": 0.70,
        "hard_barrel_pct": 0.08,
    }


def test_batter_contact_asof_leakage_cutoff() -> None:
    pitch.clear_pitch_matchup_caches()
    pitch._BATTER_CONTACT_CUMULATIVE[2026] = {
        101: [
            ("2026-05-31", _contact_metrics(pitches=200.0, hard_whiff=0.10, hard_contact=0.78)),
            ("2026-06-01", _contact_metrics(pitches=400.0, hard_whiff=0.25, hard_contact=0.90)),
        ]
    }
    got = pitch.get_batter_contact_as_of(
        101, as_of=date(2026, 6, 1), fetch_if_missing=False
    )
    assert got is not None
    assert float(got["pitches"]) == 200.0
    assert float(got["hard_whiff_pct"]) == 0.10
    assert got["as_of_pitches_through"] == "2026-05-31"
    # Same-day pitches must not leak.
    assert float(got["hard_contact_pct"]) == 0.78
    pitch.clear_pitch_matchup_caches()


def test_lineup_blend_slot_weights() -> None:
    pitch.clear_pitch_matchup_caches()
    as_of = date(2026, 6, 15)
    # Slot 3 weight 1.12 vs slot 9 weight 0.86 → blend closer to slot-3 contact.
    pitch.set_batter_contact_override(
        season=2026,
        batter_id=1001,
        as_of=as_of,
        metrics=_contact_metrics(pitches=500.0, hard_whiff=0.08, hard_contact=0.90),
    )
    pitch.set_batter_contact_override(
        season=2026,
        batter_id=1002,
        as_of=as_of,
        metrics=_contact_metrics(pitches=500.0, hard_whiff=0.18, hard_contact=0.60),
    )
    # Need ≥4 batters for blend — pad with mid-contact bats.
    for i, bid in enumerate((1003, 1004, 1005, 1006), start=3):
        pitch.set_batter_contact_override(
            season=2026,
            batter_id=bid,
            as_of=as_of,
            metrics=_contact_metrics(pitches=300.0, hard_whiff=0.12, hard_contact=0.75),
        )
    blended = pitch.blend_lineup_batter_contact(
        [
            (1001, 3),
            (1002, 9),
            (1003, 1),
            (1004, 2),
            (1005, 4),
            (1006, 5),
        ],
        as_of=as_of,
        fetch_if_missing=False,
    )
    assert blended is not None
    assert blended["source"] == "lineup_batter_blend"
    assert float(blended["batters_used"]) == 6.0
    # Slot-3 high contact should pull mean above equal-weight midpoint of 0.90/0.60.
    assert float(blended["hard_contact_pct"]) > 0.75
    pitch.clear_pitch_matchup_caches()


def test_blend_falls_back_to_team_when_insufficient() -> None:
    pitch.clear_pitch_matchup_caches()
    as_of = date(2026, 6, 15)
    prior = pitch.get_pitch_matchup_batter_level()
    try:
        pitch.apply_pitch_matchup_batter_level(True)
        pitch.set_batter_contact_override(
            season=2026,
            batter_id=2001,
            as_of=as_of,
            metrics=_contact_metrics(pitches=500.0, hard_whiff=0.09, hard_contact=0.80),
        )
        pitch.set_batter_family_override(
            season=2026,
            team_abbr="NYY",
            as_of=as_of,
            metrics={
                **_contact_metrics(pitches=5000.0, hard_whiff=0.11, hard_contact=0.77),
                "source": "team_batter_family",
            },
        )
        # Only one lineup ID → blend fails → team-family.
        got = pitch.resolve_batter_family_for_matchup(
            team_abbr="NYY",
            as_of=as_of,
            lineup_players=[{"id": 2001, "slot": 1, "position": "CF"}],
            fetch_if_missing=False,
            batter_level=True,
        )
        assert got is not None
        assert got.get("source") == "team_batter_family"
        assert float(got["pitches"]) == 5000.0
    finally:
        pitch.apply_pitch_matchup_batter_level(prior)
        pitch.clear_pitch_matchup_caches()


def test_batter_level_flag_off_uses_team_even_with_ids() -> None:
    pitch.clear_pitch_matchup_caches()
    as_of = date(2026, 6, 15)
    prior = pitch.get_pitch_matchup_batter_level()
    try:
        pitch.apply_pitch_matchup_batter_level(False)
        for bid in (3001, 3002, 3003, 3004):
            pitch.set_batter_contact_override(
                season=2026,
                batter_id=bid,
                as_of=as_of,
                metrics=_contact_metrics(pitches=400.0, hard_whiff=0.20, hard_contact=0.55),
            )
        pitch.set_batter_family_override(
            season=2026,
            team_abbr="BOS",
            as_of=as_of,
            metrics={
                **_contact_metrics(pitches=8000.0, hard_whiff=0.10, hard_contact=0.79),
                "source": "team_batter_family",
            },
        )
        players = [
            {"id": 3001, "slot": 1, "position": "LF"},
            {"id": 3002, "slot": 2, "position": "SS"},
            {"id": 3003, "slot": 3, "position": "1B"},
            {"id": 3004, "slot": 4, "position": "DH"},
        ]
        got = pitch.resolve_batter_family_for_matchup(
            team_abbr="BOS",
            as_of=as_of,
            lineup_players=players,
            fetch_if_missing=False,
        )
        assert got is not None
        assert got.get("source") == "team_batter_family"
        assert float(got["hard_contact_pct"]) == 0.79

        # Flag on → lineup blend.
        pitch.apply_pitch_matchup_batter_level(True)
        got_on = pitch.resolve_batter_family_for_matchup(
            team_abbr="BOS",
            as_of=as_of,
            lineup_players=players,
            fetch_if_missing=False,
        )
        assert got_on is not None
        assert got_on.get("source") == "lineup_batter_blend"
        assert abs(float(got_on["hard_contact_pct"]) - 0.55) < 1e-9
    finally:
        pitch.apply_pitch_matchup_batter_level(prior)
        pitch.clear_pitch_matchup_caches()


def test_extract_lineup_skips_pitchers_and_missing_ids() -> None:
    entries = pitch.extract_lineup_batter_entries(
        [
            {"id": 1, "slot": 1, "position": "CF"},
            {"id": 2, "slot": 2, "position": "P", "excluded_from_strength": True},
            {"slot": 3, "name": "No ID", "position": "RF"},
            {"id": 4, "slot": 4, "position": "C"},
        ]
    )
    assert entries == [(1, 1), (4, 4)]


def test_reset_env_batter_level_default_off(monkeypatch) -> None:
    monkeypatch.delenv("MLB_PITCH_MATCHUP_BATTER_LEVEL", raising=False)
    monkeypatch.setenv("MLB_PITCH_MATCHUP_ENABLED", "false")
    monkeypatch.setenv("MLB_PITCH_MATCHUP_STUFF_FALLBACK", "false")
    pitch.reset_pitch_matchup_from_env()
    assert pitch.get_pitch_matchup_batter_level() is False
    assert pitch.get_pitch_matchup_enabled() is False
