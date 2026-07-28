from __future__ import annotations

from data_platform_nfl.rookie_baselines import SKILL_OFFENSE_POSITIONS, draft_tier_for_pick


def test_draft_tier_boundaries_are_contiguous_and_ordered() -> None:
    assert draft_tier_for_pick(1) == "R1_top10"
    assert draft_tier_for_pick(10) == "R1_top10"
    assert draft_tier_for_pick(11) == "R1_11_32"
    assert draft_tier_for_pick(32) == "R1_11_32"
    assert draft_tier_for_pick(33) == "R2_R3"
    assert draft_tier_for_pick(96) == "R2_R3"
    assert draft_tier_for_pick(97) == "R4_R5"
    assert draft_tier_for_pick(172) == "R4_R5"
    assert draft_tier_for_pick(173) == "R6_R7"
    assert draft_tier_for_pick(300) == "R6_R7"


def test_undrafted_and_out_of_range_picks_fall_to_udfa() -> None:
    assert draft_tier_for_pick(None) == "UDFA"
    assert draft_tier_for_pick(0) == "UDFA"
    assert draft_tier_for_pick(500) == "UDFA"


def test_skill_offense_positions_excludes_defense_and_ol() -> None:
    assert "QB" in SKILL_OFFENSE_POSITIONS
    assert "RB" in SKILL_OFFENSE_POSITIONS
    assert "WR" in SKILL_OFFENSE_POSITIONS
    assert "TE" in SKILL_OFFENSE_POSITIONS
    assert "OL" not in SKILL_OFFENSE_POSITIONS
    assert "DB" not in SKILL_OFFENSE_POSITIONS
    assert "LB" not in SKILL_OFFENSE_POSITIONS
