from __future__ import annotations

from src.services.nfl_fantasy_draft_rankings import (
    assign_draft_tier,
    compute_replacement_level_points,
    compute_value_over_replacement,
    rank_season_fantasy_players,
)


def test_assign_draft_tier_qb_elite_boundary() -> None:
    assert assign_draft_tier("QB", 1) == "elite"
    assert assign_draft_tier("QB", 3) == "elite"
    assert assign_draft_tier("QB", 4) == "QB1"
    assert assign_draft_tier("QB", 16) == "QB2"
    assert assign_draft_tier("QB", 17) == "streamer"
    assert assign_draft_tier("QB", 999) == "bench"


def test_assign_draft_tier_is_case_insensitive_and_falls_back_for_unknown_position() -> None:
    assert assign_draft_tier("qb", 1) == "elite"
    assert assign_draft_tier("K", 1) == "starter"
    assert assign_draft_tier("K", 13) == "bench"


def test_assign_draft_tier_rb_wr_te_use_distinct_ladders() -> None:
    # RB/WR share the same ladder shape (flex-eligible), TE has a shorter one.
    assert assign_draft_tier("RB", 24) == "RB2"
    assert assign_draft_tier("RB", 25) == "flex"
    assert assign_draft_tier("WR", 36) == "flex"
    assert assign_draft_tier("WR", 37) == "bench"
    assert assign_draft_tier("TE", 8) == "TE1"
    assert assign_draft_tier("TE", 9) == "streamer"


def test_compute_replacement_level_points_uses_position_specific_rank() -> None:
    qb_points = [220.0, 215.0, 210.0] + [200.0] * 20  # 12th QB (idx 11) = 200.0
    assert compute_replacement_level_points(qb_points, "QB") == 200.0


def test_compute_replacement_level_points_falls_back_to_shallowest_pool_when_thin() -> None:
    # Only 5 RBs projected -- replacement rank 30 doesn't exist, so the
    # worst available RB defines the floor instead of crashing/defaulting to 0.
    rb_points = [300.0, 250.0, 200.0, 150.0, 100.0]
    assert compute_replacement_level_points(rb_points, "RB") == 100.0


def test_compute_value_over_replacement_is_points_minus_replacement() -> None:
    assert compute_value_over_replacement(180.0, 120.0) == 60.0
    assert compute_value_over_replacement(80.0, 120.0) == -40.0


def _player(key: str, position: str, points: float) -> dict:
    return {"player_key": key, "position": position, "total_points": points, "player_name": key}


def test_rank_season_fantasy_players_computes_independent_position_ranks() -> None:
    players = [
        _player("qb1", "QB", 400.0),
        _player("rb1", "RB", 380.0),
        _player("qb2", "QB", 350.0),
        _player("rb2", "RB", 300.0),
    ]
    ranked = rank_season_fantasy_players(players)
    by_key = {p["player_key"]: p for p in ranked}
    assert by_key["qb1"]["rank_position"] == 1
    assert by_key["qb2"]["rank_position"] == 2
    assert by_key["rb1"]["rank_position"] == 1
    assert by_key["rb2"]["rank_position"] == 2


def test_rank_season_fantasy_players_overall_rank_uses_vor_not_raw_points() -> None:
    # A deep QB pool (every QB clustered near the top, mirroring real
    # single-QB scoring behavior) should NOT let a merely-good QB outrank an
    # RB who dominates a shallow RB pool, even though the QB's raw points
    # total is higher -- this is the entire point of VOR-based overall rank.
    qb_pool = [_player(f"qb{i}", "QB", 210.0 - i) for i in range(1, 20)]  # qb1=209..qb19=191
    rb_pool = [_player(f"rb{i}", "RB", 200.0 - (i * 15)) for i in range(1, 6)]  # rb1=185 .. rb5=125
    ranked = rank_season_fantasy_players(qb_pool + rb_pool)
    by_key = {p["player_key"]: p for p in ranked}
    # qb1 has more raw points than rb1 (209 > 185) but sits in a deep QB
    # pool (replacement ~ qb12 => 198), while rb1 dominates a shallow RB
    # pool (replacement = the worst available RB, rb5 = 125) giving rb1 a
    # much larger VOR (60 vs qb1's 11) -- rb1 must rank ABOVE qb1 overall.
    assert by_key["rb1"]["rank_overall"] < by_key["qb1"]["rank_overall"]


def test_rank_season_fantasy_players_assigns_tier_from_position_rank() -> None:
    players = [_player(f"wr{i}", "WR", 300.0 - i) for i in range(1, 40)]
    ranked = rank_season_fantasy_players(players)
    tiers_by_key = {p["player_key"]: p["tier"] for p in ranked}
    assert tiers_by_key["wr1"] == "elite"
    assert tiers_by_key["wr4"] == "WR1"
    assert tiers_by_key["wr39"] == "bench"


def test_rank_season_fantasy_players_breaks_ties_deterministically() -> None:
    players = [_player("z", "RB", 100.0), _player("a", "RB", 100.0)]
    ranked_first = rank_season_fantasy_players(players)
    ranked_second = rank_season_fantasy_players(list(reversed(players)))
    first_order = [p["player_key"] for p in sorted(ranked_first, key=lambda p: p["rank_overall"])]
    second_order = [p["player_key"] for p in sorted(ranked_second, key=lambda p: p["rank_overall"])]
    assert first_order == second_order == ["a", "z"]


def test_rank_season_fantasy_players_does_not_mutate_input() -> None:
    players = [_player("a", "QB", 100.0)]
    rank_season_fantasy_players(players)
    assert "rank_overall" not in players[0]
