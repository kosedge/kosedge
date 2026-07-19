from __future__ import annotations

import statistics

from src.services.nfl_player_projection_engine import PlayerFeatureInputs, baseline_projection_from_features
from src.services.nfl_player_box_score_simulator import (
    PlayerBoxScoreRole,
    TeamVolumeContext,
    aggregate_game_sims_to_season,
    compute_team_volume_context,
    simulate_team_player_box_scores,
    summarize_distribution,
)


def _baseline(position: str, **overrides) -> dict:
    base = dict(
        position=position,
        snap_proxy=0.5,
        route_proxy=0.5,
        target_proxy=0.2,
        rush_share=0.2,
        red_zone_share=0.2,
        qb_dropback_factor=1.0,
        qb_pressure_factor=1.0,
        team_pace_factor=1.0,
        team_pass_rate_factor=1.0,
        availability_confidence=0.9,
        role_confidence=0.7,
        team_snap_share=0.0,
    )
    base.update(overrides)
    return baseline_projection_from_features(PlayerFeatureInputs(**base))


def _standard_team() -> tuple[TeamVolumeContext, list[PlayerBoxScoreRole]]:
    context = TeamVolumeContext(mean_total_plays=64.0, std_total_plays=5.0, mean_pass_rate=0.58, std_pass_rate=0.05, sample_games=8)
    qb = PlayerBoxScoreRole(
        player_key="qb1",
        player_name="Starter QB",
        position="QB",
        baseline=_baseline("QB", team_snap_share=0.97, rush_share=0.05, role_confidence=0.9),
        role_confidence=0.9,
    )
    rb1 = PlayerBoxScoreRole(
        player_key="rb1",
        player_name="Bell Cow RB",
        position="RB",
        baseline=_baseline("RB", rush_share=0.62, target_proxy=0.14, role_confidence=0.88),
        role_confidence=0.88,
    )
    rb2 = PlayerBoxScoreRole(
        player_key="rb2",
        player_name="Backup RB",
        position="RB",
        baseline=_baseline("RB", rush_share=0.18, target_proxy=0.05, role_confidence=0.45),
        role_confidence=0.45,
    )
    wr1 = PlayerBoxScoreRole(
        player_key="wr1",
        player_name="WR1",
        position="WR",
        baseline=_baseline("WR", target_proxy=0.27, route_proxy=0.85, role_confidence=0.82),
        role_confidence=0.82,
    )
    wr2 = PlayerBoxScoreRole(
        player_key="wr2",
        player_name="WR2",
        position="WR",
        baseline=_baseline("WR", target_proxy=0.16, route_proxy=0.65, role_confidence=0.6),
        role_confidence=0.6,
    )
    te1 = PlayerBoxScoreRole(
        player_key="te1",
        player_name="TE1",
        position="TE",
        baseline=_baseline("TE", target_proxy=0.14, route_proxy=0.55, role_confidence=0.7),
        role_confidence=0.7,
    )
    wr3 = PlayerBoxScoreRole(
        player_key="wr3",
        player_name="WR3",
        position="WR",
        baseline=_baseline("WR", target_proxy=0.08, route_proxy=0.45, role_confidence=0.4),
        role_confidence=0.4,
    )
    # A roster covering essentially the full real target/carry pool (QB +
    # 2 RBs + 3 WRs + 1 TE) -- realistic coverage matters for the box-score
    # engine's team-level coherence property: if the modeled roster only
    # captures a small fraction of a team's real pass-catchers, the
    # unmodeled "other" bucket dominates the allocation noise and swamps
    # the shared team-volume signal. The real production call (tasks.py)
    # supplies every player with real usage that week, which typically
    # captures 85%+ of a team's targets/carries -- this fixture mirrors that.
    return context, [qb, rb1, rb2, wr1, wr2, wr3, te1]


def test_summarize_distribution_bounds_and_shape() -> None:
    dist = summarize_distribution([10.0, 20.0, 30.0, 40.0, 50.0])
    assert dist["mean"] == 30.0
    assert dist["p50"] == 30.0
    assert dist["p10"] <= dist["p50"] <= dist["p90"]
    assert dist["std"] > 0.0


def test_summarize_distribution_empty_is_safe() -> None:
    dist = summarize_distribution([])
    assert dist["mean"] == 0.0
    assert dist["std"] == 0.0


def test_compute_team_volume_context_from_trailing_rows() -> None:
    rows = [
        {"offensive_plays": 60, "pass_rate": 0.55},
        {"offensive_plays": 66, "pass_rate": 0.60},
        {"offensive_plays": 64, "pass_rate": 0.58},
    ]
    ctx = compute_team_volume_context(rows)
    assert 60.0 <= ctx.mean_total_plays <= 66.0
    assert 0.55 <= ctx.mean_pass_rate <= 0.60
    assert ctx.sample_games == 3
    assert ctx.mean_pass_plays > 0
    assert ctx.mean_rush_plays > 0


def test_compute_team_volume_context_falls_back_with_no_trailing_data() -> None:
    ctx = compute_team_volume_context([])
    assert ctx.mean_total_plays > 0
    assert ctx.mean_pass_rate > 0
    assert ctx.sample_games == 0


def test_box_score_sim_produces_nonzero_realistic_distributions() -> None:
    context, players = _standard_team()
    result = simulate_team_player_box_scores(context, players, replicates=1500, seed=42)

    qb_dist = result["qb1"]["pass_yards_dist"]
    assert qb_dist["mean"] > 150.0
    assert qb_dist["std"] > 0.0
    assert qb_dist["p10"] < qb_dist["p50"] < qb_dist["p90"]

    rb1_dist = result["rb1"]["rush_yards_dist"]
    rb2_dist = result["rb2"]["rush_yards_dist"]
    # The bell-cow back's higher rush share should translate into materially
    # more simulated rushing yards than the committee backup.
    assert rb1_dist["mean"] > rb2_dist["mean"]


def test_box_score_sim_is_deterministic_given_seed() -> None:
    context, players = _standard_team()
    first = simulate_team_player_box_scores(context, players, replicates=300, seed=7)
    second = simulate_team_player_box_scores(context, players, replicates=300, seed=7)
    assert first["qb1"]["pass_yards_dist"] == second["qb1"]["pass_yards_dist"]


def test_box_score_sim_shares_team_volume_within_a_replicate() -> None:
    # A team drawing an unusually pass-heavy total_plays/pass_rate combo in
    # one replicate should lift BOTH the QB's attempts and the WRs' targets
    # together, not independently -- verify by checking that across many
    # seeds, QB attempts and the sum of all pass-catchers' targets are
    # clearly positively correlated (not just noise) in the underlying
    # per-replicate draws. The correlation is real but deliberately not
    # ~1.0: each player also carries independent, role-confidence-scaled
    # noise on top of the shared team-volume draw (see
    # `_concentration`/`SHARED_POOL_CONCENTRATION` docstrings) -- that
    # per-player variance is itself a requested property ("a bell-cow RB
    # doesn't get exactly the same share every game"), and it necessarily
    # trades off against a perfectly deterministic team-volume signal.
    context, players = _standard_team()
    reps = 400
    # Re-implement a lightweight correlation check by simulating with many
    # different single-replicate contexts (this indirectly exercises the
    # same shared-draw code path used inside simulate_team_player_box_scores).
    from src.services.nfl_player_box_score_simulator import _simulate_volume_pool, _allocate_shares
    import random as _random

    rng = _random.Random(11)
    qb_role_players = [p for p in players if p.baseline.get("attempts_mean", 0.0) > 0.0]
    receiver_players = [p for p in players if p.baseline.get("targets_mean", 0.0) > 0.0]
    qb_shares = _allocate_shares(qb_role_players, baseline_key="attempts_mean", team_denominator=context.mean_pass_plays)
    target_shares = _allocate_shares(receiver_players, baseline_key="targets_mean", team_denominator=context.mean_pass_plays)

    qb_attempts_series = []
    total_targets_series = []
    for _ in range(reps):
        total_plays_i = max(30.0, rng.gauss(context.mean_total_plays, context.std_total_plays))
        pass_rate_i = max(0.3, min(0.8, rng.gauss(context.mean_pass_rate, context.std_pass_rate)))
        team_pass_plays_i = total_plays_i * pass_rate_i
        qb_attempts_i = _simulate_volume_pool(rng, players=qb_role_players, base_shares=qb_shares, pool_plays=team_pass_plays_i)
        targets_i = _simulate_volume_pool(rng, players=receiver_players, base_shares=target_shares, pool_plays=team_pass_plays_i)
        qb_attempts_series.append(sum(qb_attempts_i))
        total_targets_series.append(sum(targets_i))

    correlation = statistics.correlation(qb_attempts_series, total_targets_series)
    assert correlation > 0.4


def test_qb_competition_is_winner_take_all_per_replicate_not_split() -> None:
    # Real bug found via a live 2026 New Orleans spot-check: two QBs with
    # comparably-sized baseline attempts_mean (a genuinely unsettled real
    # depth chart) were getting their pass attempts CONTINUOUSLY split every
    # single replicate by the shared Dirichlet -- an event that essentially
    # never happens in a real game (one QB plays, not a 50/50 blend of two).
    # Each replicate should award (near) ALL of a team's pass attempts to
    # exactly one of the two QBs, never a meaningful split between both.
    from src.services.nfl_player_box_score_simulator import _simulate_qb_starter_draw
    import random as _random

    context = TeamVolumeContext(mean_total_plays=64.0, std_total_plays=5.0, mean_pass_rate=0.58, std_pass_rate=0.05, sample_games=8)
    qb_a = PlayerBoxScoreRole(
        player_key="qb_a", player_name="QB A", position="QB",
        baseline=_baseline("QB", team_snap_share=0.55, rush_share=0.05, role_confidence=0.5), role_confidence=0.5,
    )
    qb_b = PlayerBoxScoreRole(
        player_key="qb_b", player_name="QB B", position="QB",
        baseline=_baseline("QB", team_snap_share=0.57, rush_share=0.05, role_confidence=0.5), role_confidence=0.5,
    )
    players = [qb_a, qb_b]
    from src.services.nfl_player_box_score_simulator import _allocate_shares

    qb_shares = _allocate_shares(players, baseline_key="attempts_mean", team_denominator=context.mean_pass_plays)
    rng = _random.Random(3)
    both_got_meaningful_attempts = 0
    a_wins = 0
    b_wins = 0
    reps = 500
    for _ in range(reps):
        allocations = _simulate_qb_starter_draw(rng, players=players, base_shares=qb_shares, pool_plays=context.mean_pass_plays)
        nonzero = [a for a in allocations if a > 1.0]
        if len(nonzero) > 1:
            both_got_meaningful_attempts += 1
        if allocations[0] > allocations[1]:
            a_wins += 1
        else:
            b_wins += 1

    # Never a split -- exactly one QB gets meaningful attempts per replicate.
    assert both_got_meaningful_attempts == 0
    # Both QBs should win the starter draw a meaningful share of the time
    # (they have comparable base shares), not one dominating entirely.
    assert a_wins > reps * 0.25
    assert b_wins > reps * 0.25


def test_qb_starter_draw_single_qb_gets_nearly_full_pool() -> None:
    from src.services.nfl_player_box_score_simulator import _simulate_qb_starter_draw

    starter = PlayerBoxScoreRole(
        player_key="qb1", player_name="Starter", position="QB",
        baseline=_baseline("QB", team_snap_share=0.95, rush_share=0.05, role_confidence=0.9), role_confidence=0.9,
    )
    import random as _random

    rng = _random.Random(5)
    allocations = [
        _simulate_qb_starter_draw(rng, players=[starter], base_shares=[0.62], pool_plays=38.0)[0]
        for _ in range(200)
    ]
    mean_allocation = statistics.fmean(allocations)
    # Should land close to the full pool (minus the small reserved "other"
    # bucket for scrambles/trick plays by non-QBs), not the raw 0.62 share.
    assert mean_allocation > 32.0


def test_aggregate_game_sims_to_season_sums_means_and_combines_std() -> None:
    game_rows = [
        {"receiving_yards_dist": {"mean": 60.0, "std": 20.0}},
        {"receiving_yards_dist": {"mean": 80.0, "std": 25.0}},
    ]
    season = aggregate_game_sims_to_season(game_rows)
    assert season["games_aggregated"] == 2
    assert season["receiving_yards_mean"] == 140.0
    expected_std = (20.0 ** 2 + 25.0 ** 2) ** 0.5
    assert abs(season["receiving_yards_std"] - expected_std) < 0.01
