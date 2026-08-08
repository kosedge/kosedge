"""Packaged EPA priors for real-mode universe (not demo strength bumps)."""

from __future__ import annotations

from src.services.nfl_season_engine import (
    build_demo_universe,
    build_packaged_real_universe,
    load_packaged_epa_priors,
)
from src.services.nfl_season_engine.loaders import (
    STRENGTH_SOURCE_DEMO,
    STRENGTH_SOURCE_PACKAGED_EPA,
    STRENGTH_SOURCE_PACKAGED_EFFICIENCY,
)

_REAL_PACKAGED_SOURCES = {
    STRENGTH_SOURCE_PACKAGED_EPA,
    STRENGTH_SOURCE_PACKAGED_EFFICIENCY,
}


def test_load_packaged_epa_priors_covers_32_teams() -> None:
    priors, meta = load_packaged_epa_priors(2026)
    assert len(priors) == 32
    assert meta["strength_source"] in _REAL_PACKAGED_SOURCES
    assert int(meta["prior_season"]) == 2025
    for team, row in priors.items():
        assert 0.80 <= float(row["offense_index"]) <= 1.25
        assert 0.80 <= float(row["defense_index"]) <= 1.25


def test_packaged_real_universe_uses_epa_not_demo_bumps() -> None:
    packaged = build_packaged_real_universe(2026)
    demo = build_demo_universe(2026)

    assert packaged.notes.get("strength_source") in _REAL_PACKAGED_SOURCES
    strengths_note = str(packaged.notes.get("strengths") or "").lower()
    assert "packaged" in strengths_note
    assert "demo" not in strengths_note

    for team, state in packaged.strengths.items():
        assert state.source in _REAL_PACKAGED_SOURCES
        # Must not silently reuse demo bump book.
        demo_state = demo.strengths[team]
        assert demo_state.source == STRENGTH_SOURCE_DEMO

    # At least half the league should differ from demo bumps (hierarchy rewrite).
    diffs = sum(
        1
        for t in packaged.strengths
        if abs(packaged.strengths[t].offense_index - demo.strengths[t].offense_index) > 0.02
        or abs(packaged.strengths[t].defense_index - demo.strengths[t].defense_index) > 0.02
    )
    assert diffs >= 16


def test_sea_clearly_above_ari_on_offense_and_defense() -> None:
    packaged = build_packaged_real_universe(2026)
    sea = packaged.strengths["SEA"]
    ari = packaged.strengths["ARI"]
    assert sea.offense_index > ari.offense_index + 0.03
    assert sea.defense_index > ari.defense_index + 0.10
    sea_comp = sea.offense_index + sea.defense_index
    ari_comp = ari.offense_index + ari.defense_index
    assert sea_comp > ari_comp + 0.15


def test_ne_not_bottom_tier_without_cause() -> None:
    packaged = build_packaged_real_universe(2026)
    ranked = sorted(
        packaged.strengths,
        key=lambda t: -(
            packaged.strengths[t].offense_index + packaged.strengths[t].defense_index
        ),
    )
    ne_rank = ranked.index("NE") + 1
    # 2025 season EPA put NE near the top; Past SOS soft-slate deflation is
    # allowed, but must not dump NE to the floor (~29–32).
    assert ne_rank <= 10, f"NE power rank {ne_rank} among {ranked}"
    ne = packaged.strengths["NE"]
    assert ne.offense_index >= 1.02
    assert ne.defense_index >= 1.04

    # Bottom of league should still be weak clubs, not NE.
    bottom = set(ranked[-5:])
    assert "NE" not in bottom
    assert "SEA" not in bottom


def test_demo_universe_keeps_demo_bumps() -> None:
    demo = build_demo_universe(2026)
    assert demo.strengths["NE"].source == STRENGTH_SOURCE_DEMO
    assert demo.strengths["NE"].offense_index < 0.96
    assert "demo" in str(demo.notes.get("strengths") or "").lower()
