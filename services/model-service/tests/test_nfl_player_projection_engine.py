from __future__ import annotations

from src.services.nfl_player_projection_engine import (
    ROOKIE_EXPERIENCE_CONFIDENCE,
    VETERAN_EXPERIENCE_CONFIDENCE,
    PlayerFeatureInputs,
    baseline_projection_from_features,
    compute_qb_starter_shares,
    compute_rb_rush_shares,
    depth_role_confidence_floor,
    effective_skill_role_confidence,
    evaluate_prop_edge,
    fantasy_points_from_projection,
    merge_depth_orders,
    qb_talent_factor_from_prior_ypg,
    skill_talent_factor_from_prior_ypg,
    usage_rank_depth_orders,
)


def test_baseline_projection_is_bounded_and_deterministic() -> None:
    inputs = PlayerFeatureInputs(
        position="WR",
        snap_proxy=0.78,
        route_proxy=0.72,
        target_proxy=0.30,
        rush_share=0.04,
        red_zone_share=0.22,
        qb_dropback_factor=1.04,
        qb_pressure_factor=0.88,
        team_pace_factor=1.05,
        team_pass_rate_factor=1.08,
        availability_confidence=0.91,
        role_confidence=0.85,
    )
    first = baseline_projection_from_features(inputs)
    second = baseline_projection_from_features(inputs)
    assert first == second
    assert first["receiving_yards_mean"] > 0
    assert first["receptions_mean"] > 0
    assert 0.0 <= first["anytime_td_prob"] <= 1.0


def _rb_inputs(**overrides) -> PlayerFeatureInputs:
    base = dict(
        position="RB",
        snap_proxy=0.45,
        route_proxy=0.30,
        target_proxy=0.15,
        rush_share=0.55,
        red_zone_share=0.20,
        qb_dropback_factor=1.0,
        qb_pressure_factor=1.0,
        team_pace_factor=1.0,
        team_pass_rate_factor=1.0,
        availability_confidence=0.9,
        role_confidence=0.7,
    )
    base.update(overrides)
    return PlayerFeatureInputs(**base)


def test_rookie_experience_confidence_widens_std_not_mean() -> None:
    veteran = baseline_projection_from_features(_rb_inputs(experience_confidence=VETERAN_EXPERIENCE_CONFIDENCE))
    rookie = baseline_projection_from_features(_rb_inputs(experience_confidence=ROOKIE_EXPERIENCE_CONFIDENCE))

    # Same inputs otherwise -> identical means, wider stds for the rookie.
    assert veteran["rush_yards_mean"] == rookie["rush_yards_mean"]
    assert veteran["receiving_yards_mean"] == rookie["receiving_yards_mean"]
    assert rookie["rush_yards_std"] > veteran["rush_yards_std"]
    assert rookie["receiving_yards_std"] > veteran["receiving_yards_std"]
    assert rookie["uncertainty"]["variance_widening"] > veteran["uncertainty"]["variance_widening"]
    assert veteran["uncertainty"]["variance_widening"] == 1.0


def test_experience_confidence_defaults_to_veteran() -> None:
    default_inputs = _rb_inputs()
    assert default_inputs.experience_confidence == VETERAN_EXPERIENCE_CONFIDENCE
    projection = baseline_projection_from_features(default_inputs)
    assert projection["uncertainty"]["variance_widening"] == 1.0


def test_qb_volume_uses_team_snap_share_not_touch_share() -> None:
    # A starting QB's team_snap_share should be near 1.0 (played nearly
    # every offensive snap) even though their touch-share `snap_proxy` is
    # naturally small (a QB's dropbacks are one slice of the team's total
    # skill-position touches). The old formula blended in snap_proxy at 70%
    # weight, crushing passing volume for every real starter.
    starter = PlayerFeatureInputs(
        position="QB",
        snap_proxy=0.22,  # realistic touch-share value for a real starter
        route_proxy=0.0,
        target_proxy=0.0,
        rush_share=0.05,
        red_zone_share=0.2,
        qb_dropback_factor=0.95,
        qb_pressure_factor=1.0,
        team_pace_factor=1.0,
        team_pass_rate_factor=1.0,
        availability_confidence=0.95,
        role_confidence=0.5,
        team_snap_share=0.95,
    )
    projection = baseline_projection_from_features(starter)
    # A real starter with a full workload should project well above 200
    # yards for the game -- the pre-fix formula landed around 100.
    assert projection["pass_yards_mean"] > 200


def test_qb_volume_falls_back_to_snap_proxy_when_team_snap_share_missing() -> None:
    # Backward compatibility: a caller that hasn't wired team_snap_share
    # through yet (still at the 0.0 default) shouldn't crash or silently
    # zero out -- it degrades to the old snap_proxy-based signal.
    inputs = PlayerFeatureInputs(
        position="QB",
        snap_proxy=0.8,
        route_proxy=0.0,
        target_proxy=0.0,
        rush_share=0.05,
        red_zone_share=0.2,
        qb_dropback_factor=0.95,
        qb_pressure_factor=1.0,
        team_pace_factor=1.0,
        team_pass_rate_factor=1.0,
        availability_confidence=0.95,
        role_confidence=0.5,
    )
    projection = baseline_projection_from_features(inputs)
    assert projection["pass_yards_mean"] > 150


def test_opponent_defense_factor_shifts_yards_without_changing_role() -> None:
    base_kwargs = dict(
        position="WR",
        snap_proxy=0.6,
        route_proxy=0.75,
        target_proxy=0.22,
        rush_share=0.0,
        red_zone_share=0.15,
        qb_dropback_factor=1.0,
        qb_pressure_factor=1.0,
        team_pace_factor=1.0,
        team_pass_rate_factor=1.0,
        availability_confidence=0.95,
        role_confidence=0.75,
    )
    vs_bad_defense = baseline_projection_from_features(PlayerFeatureInputs(**base_kwargs, opponent_pass_defense_factor=1.25))
    vs_good_defense = baseline_projection_from_features(PlayerFeatureInputs(**base_kwargs, opponent_pass_defense_factor=0.80))
    assert vs_bad_defense["receiving_yards_mean"] > vs_good_defense["receiving_yards_mean"]
    assert vs_bad_defense["matchup"]["opponent_pass_defense_factor"] == 1.25
    assert vs_good_defense["matchup"]["opponent_pass_defense_factor"] == 0.80


def test_non_offensive_positions_get_zero_projection() -> None:
    # Real bug found via a live production spot-check: 1,998/1,998 OL/DL/LB/
    # DB/K/P-tagged players in the deployed bundle had nonzero receiving
    # yards (some 90+ for a season) because the old bare `else` branch
    # routed every non-QB/RB position through the WR/TE formula, whose
    # additive floors (targets_mean's `1.2 +` base, receiving_yards_mean's
    # `5.5` min yards/catch) guarantee a nonzero projection regardless of
    # real usage. A rare real one-off event (e.g. a trick-play catch by an
    # offensive tackle in a single game) getting treated as that player's
    # "per-game rate" and extrapolated over a season is exactly the
    # scenario that produced this in production.
    for position in ["OL", "DL", "LB", "DB", "K", "P", "LS", "S", "CB", "DE", "DT", "OT", "OG", "C"]:
        inputs = PlayerFeatureInputs(
            position=position,
            snap_proxy=0.5,
            route_proxy=0.3,
            target_proxy=0.05,  # even with a nonzero target_proxy (e.g. from a real rare event)
            rush_share=0.02,
            red_zone_share=0.1,
            qb_dropback_factor=1.0,
            qb_pressure_factor=1.0,
            team_pace_factor=1.0,
            team_pass_rate_factor=1.0,
            availability_confidence=0.9,
            role_confidence=0.5,
        )
        projection = baseline_projection_from_features(inputs)
        assert projection["receiving_yards_mean"] == 0.0, position
        assert projection["receptions_mean"] == 0.0, position
        assert projection["rush_yards_mean"] == 0.0, position
        assert projection["targets_mean"] == 0.0, position
        assert projection["carries_mean"] == 0.0, position


def test_wr_te_still_get_real_projections() -> None:
    # Guard against the fix above accidentally zeroing out real skill
    # positions too.
    for position in ["WR", "TE"]:
        inputs = PlayerFeatureInputs(
            position=position,
            snap_proxy=0.6,
            route_proxy=0.75,
            target_proxy=0.22,
            rush_share=0.0,
            red_zone_share=0.15,
            qb_dropback_factor=1.0,
            qb_pressure_factor=1.0,
            team_pace_factor=1.0,
            team_pass_rate_factor=1.0,
            availability_confidence=0.9,
            role_confidence=0.75,
        )
        projection = baseline_projection_from_features(inputs)
        assert projection["receiving_yards_mean"] > 0.0, position
        assert projection["targets_mean"] > 0.0, position


def _qb_inputs(**overrides) -> PlayerFeatureInputs:
    base = dict(
        position="QB",
        snap_proxy=0.22,
        route_proxy=0.0,
        target_proxy=0.0,
        rush_share=0.05,
        red_zone_share=0.2,
        qb_dropback_factor=0.95,
        qb_pressure_factor=1.0,
        team_pace_factor=1.0,
        team_pass_rate_factor=1.0,
        availability_confidence=0.95,
        role_confidence=0.5,
        team_snap_share=0.4,
    )
    base.update(overrides)
    return PlayerFeatureInputs(**base)


def test_qb_starter_share_default_leaves_starter_unaffected() -> None:
    # The default (1.0, and every caller before this fix) must be
    # completely unchanged -- a team with only one rostered QB, or any
    # caller not yet wired for team context, should see IDENTICAL output
    # to before this fix.
    with_default = baseline_projection_from_features(_qb_inputs())
    with_explicit_one = baseline_projection_from_features(_qb_inputs(qb_starter_share=1.0))
    assert with_default == with_explicit_one


def test_qb_starter_share_suppresses_backup_volume() -> None:
    # Real bug found via a live production spot-check: every rostered QB on
    # a team (not just the real starter) was independently clearing the
    # attempts_mean formula's additive floors regardless of team_snap_share
    # -- a team with 4-5 rostered QBs projected a combined SEASON
    # pass-attempt total of ~2,100-2,500, roughly 4-5x a real starter's
    # season. A clear backup (starter_share close to 0) must project a
    # small fraction of the starter's volume, not a comparable one.
    starter = baseline_projection_from_features(_qb_inputs(qb_starter_share=1.0))
    clear_backup = baseline_projection_from_features(_qb_inputs(qb_starter_share=0.05))
    assert clear_backup["attempts_mean"] < starter["attempts_mean"] * 0.15
    assert clear_backup["pass_yards_mean"] < starter["pass_yards_mean"] * 0.15
    assert clear_backup["carries_mean"] < starter["carries_mean"] * 0.15
    assert clear_backup["pass_tds_mean"] < starter["pass_tds_mean"] * 0.15
    # A team's QB1 with a lone token backup (both real signals present)
    # should never see the starter suppressed at all.
    assert baseline_projection_from_features(_qb_inputs(qb_starter_share=1.0))["attempts_mean"] == starter["attempts_mean"]


def test_qb_starter_share_zero_fully_suppresses_qb_output() -> None:
    fully_suppressed = baseline_projection_from_features(_qb_inputs(qb_starter_share=0.0))
    assert fully_suppressed["attempts_mean"] == 0.0
    assert fully_suppressed["pass_yards_mean"] == 0.0
    assert fully_suppressed["carries_mean"] == 0.0
    assert fully_suppressed["pass_tds_mean"] == 0.0


def test_compute_qb_starter_shares_single_qb_always_gets_full_share() -> None:
    # No depth-chart competition to resolve with only one rostered QB --
    # this must return 1.0 regardless of that lone QB's own team_snap_share
    # value (a rookie's true starter role can still look "low" by raw
    # team_snap_share early on).
    assert compute_qb_starter_shares({"qb1": 0.15}) == {"qb1": 1.0}


def test_compute_qb_starter_shares_ranks_by_team_snap_share() -> None:
    # Mirrors the real BAL-QB-room production numbers this bug was found
    # with: a clear starter plus several backups whose team_snap_share
    # values, post-fix, correctly separate them.
    shares = compute_qb_starter_shares(
        {"lamar": 0.397, "huntley": 0.086, "thompson": 0.052, "fagnano": 0.017, "pavia": 0.017}
    )
    assert shares["lamar"] == 1.0
    assert shares["huntley"] < 0.3
    assert shares["thompson"] < shares["huntley"]
    assert shares["fagnano"] < shares["thompson"]
    assert shares["pavia"] == shares["fagnano"]
    # Monotonic and bounded.
    assert all(0.0 <= v <= 1.0 for v in shares.values())


def test_compute_qb_starter_shares_handles_all_zero_snap_shares() -> None:
    # No real signal to rank by (e.g. every QB hydrated at exactly 0.0
    # before any real usage exists) -- must not divide by zero or crash,
    # and should not arbitrarily suppress anyone the data can't rank.
    shares = compute_qb_starter_shares({"a": 0.0, "b": 0.0})
    assert shares == {"a": 1.0, "b": 1.0}


def test_compute_qb_starter_shares_uses_depth_when_snaps_missing() -> None:
    shares = compute_qb_starter_shares(
        {"backup": 0.0, "starter": 0.0},
        depth_orders={"starter": 1.0, "backup": 2.0},
    )
    assert shares["starter"] >= 0.90
    assert shares["backup"] <= 0.08


def test_compute_qb_starter_shares_prior_beats_stale_depth_and_injury_snaps() -> None:
    # Production failure modes: Flacco > Burrow on 2025 injury snaps,
    # Huntley depth_order=1 over Lamar, Milton depth_order=1 over Dak.
    # Prior attempts must crown the real franchise QB1; winner-take-most
    # must crush the backup below a second full starter season.
    cin = compute_qb_starter_shares(
        {"burrow": 0.28, "flacco": 0.43, "johnson": 0.07},
        depth_orders={"burrow": 1.0, "flacco": 2.0, "johnson": 3.0},
        prior_attempts={"burrow": 979.0, "flacco": 264.0, "johnson": 0.0},
    )
    assert cin["burrow"] >= 0.90
    assert cin["flacco"] <= 0.08
    assert cin["johnson"] <= 0.03

    bal = compute_qb_starter_shares(
        {"lamar": 0.40, "huntley": 0.09},
        depth_orders={"huntley": 1.0, "lamar": 2.0},
        prior_attempts={"lamar": 882.0, "huntley": 74.0},
    )
    assert bal["lamar"] >= 0.90
    assert bal["huntley"] <= 0.08

    dal = compute_qb_starter_shares(
        {"dak": 0.35, "milton": 0.05},
        depth_orders={"milton": 1.0, "dak": 2.0},
        prior_attempts={"dak": 937.0, "milton": 24.0},
    )
    assert dal["dak"] >= 0.90
    assert dal["milton"] <= 0.08


def test_compute_qb_starter_shares_volume_leader_beats_stale_depth2() -> None:
    # MIN-class room: franchise QB threw more last year but depth chart
    # still lists a bridge veteran as QB1.
    shares = compute_qb_starter_shares(
        {"mccarthy": 0.32, "wentz": 0.21, "brosmer": 0.09},
        depth_orders={"wentz": 1.0, "mccarthy": 2.0, "brosmer": 3.0},
        prior_attempts={"mccarthy": 273.0, "wentz": 188.0, "brosmer": 85.0},
    )
    assert shares["mccarthy"] >= 0.90
    assert shares["wentz"] <= 0.08


def test_qb_talent_factor_separates_elite_from_bridge() -> None:
    assert qb_talent_factor_from_prior_ypg(290.0) > qb_talent_factor_from_prior_ypg(210.0)
    assert qb_talent_factor_from_prior_ypg(290.0) > 1.05
    assert qb_talent_factor_from_prior_ypg(200.0) < 0.98


def test_elite_qb_season_scale_above_compressed_ceiling() -> None:
    # Elite primary starter should clear the old ~3.1k compressed "league
    # lead" band when extrapolated over 17 games.
    elite = baseline_projection_from_features(
        _qb_inputs(
            team_snap_share=0.48,
            snap_proxy=0.30,
            qb_starter_share=0.92,
            qb_talent_factor=1.12,
            role_confidence=0.9,
            team_pass_rate_factor=1.05,
            qb_dropback_factor=1.05,
        )
    )
    assert elite["pass_yards_mean"] * 17 > 3800.0


def test_qb_designated_starter_volume_not_crushed_by_mid_team_snap() -> None:
    # Mid involvement (~0.42) for a clear starter should land near book /
    # true-projection pass lines (~220-300), not the pre-rematerialize ~167 crash.
    mid_snap_starter = baseline_projection_from_features(
        _qb_inputs(team_snap_share=0.42, snap_proxy=0.29, qb_starter_share=1.0)
    )
    assert mid_snap_starter["pass_yards_mean"] > 185.0
    assert mid_snap_starter["pass_yards_mean"] < 320.0


def test_qb_cold_start_designated_starter_gets_volume_floor() -> None:
    cold = baseline_projection_from_features(
        _qb_inputs(team_snap_share=0.05, snap_proxy=0.04, qb_starter_share=1.0)
    )
    assert cold["pass_yards_mean"] > 200.0


def test_compute_qb_starter_shares_empty_input() -> None:
    assert compute_qb_starter_shares({}) == {}


def test_compute_rb_rush_shares_bell_cow_winner_take_most() -> None:
    shares = compute_rb_rush_shares(
        {"rb1": 0.55, "rb2": 0.25, "rb3": 0.10},
        depth_orders={"rb1": 1.0, "rb2": 2.0, "rb3": 3.0},
        prior_carries={"rb1": 320.0, "rb2": 110.0, "rb3": 40.0},
        offense_snap_pcts={"rb1": 0.68, "rb2": 0.28, "rb3": 0.10},
    )
    assert abs(sum(shares.values()) - 1.0) < 1e-6
    assert shares["rb1"] >= 0.60
    assert shares["rb2"] < shares["rb1"]
    assert shares["rb3"] < shares["rb2"]


def test_compute_rb_rush_shares_committee_softens_when_usage_close() -> None:
    shares = compute_rb_rush_shares(
        {"rb1": 0.42, "rb2": 0.40, "rb3": 0.10},
        depth_orders={"rb1": 1.0, "rb2": 2.0, "rb3": 3.0},
        prior_carries={"rb1": 160.0, "rb2": 150.0, "rb3": 30.0},
        offense_snap_pcts={"rb1": 0.45, "rb2": 0.42, "rb3": 0.12},
    )
    assert abs(sum(shares.values()) - 1.0) < 1e-6
    # True committees must keep RB2 alive — not crush to QB-style residuals.
    assert shares["rb2"] >= 0.28
    assert shares["rb1"] < 0.62


def test_compute_rb_rush_shares_single_back_full_share() -> None:
    assert compute_rb_rush_shares({"rb1": 0.4}) == {"rb1": 1.0}


def test_elite_wr_target_share_produces_realistic_season_volume() -> None:
    # Real bug found via a live production spot-check: targets_mean used to
    # multiply target_proxy (a real target SHARE) by a small, arbitrary
    # fixed coefficient (11.5) with no connection to a team's real pass
    # volume, so a real elite WR1's genuine ~31% target share projected for
    # only ~5 targets/game instead of a realistic ~12-13. Fixed by deriving
    # a real team-pass-attempts estimate from the already-normalized
    # pace/pass-rate factors and multiplying that by the real target share
    # directly -- the mathematically correct relationship. This is a
    # regression guard on the realistic RANGE, not an exact-value check,
    # since the formula legitimately has other inputs.
    elite_wr1 = PlayerFeatureInputs(
        position="WR", snap_proxy=0.6, route_proxy=0.51, target_proxy=0.31,
        rush_share=0.0, red_zone_share=0.2, qb_dropback_factor=1.0, qb_pressure_factor=1.0,
        team_pace_factor=1.0, team_pass_rate_factor=1.1, availability_confidence=0.95,
        role_confidence=0.88, skill_talent_factor=1.14,
    )
    projection = baseline_projection_from_features(elite_wr1)
    season_yards = projection["receiving_yards_mean"] * 17
    assert projection["targets_mean"] > 9.5
    assert 1300.0 < season_yards < 2100.0


def test_low_role_confidence_does_not_crush_depth1_wr_when_floored() -> None:
    # Chase-class failure: hydrated role_confidence ~0.28 with real 31% target
    # share must still clear ~80 yd/g once depth floor + talent are applied.
    crushed = baseline_projection_from_features(
        PlayerFeatureInputs(
            position="WR", snap_proxy=0.1, route_proxy=0.51, target_proxy=0.314,
            rush_share=0.0, red_zone_share=0.15, qb_dropback_factor=1.0, qb_pressure_factor=1.0,
            team_pace_factor=0.97, team_pass_rate_factor=1.10, availability_confidence=0.9,
            role_confidence=0.28, skill_talent_factor=1.0,
        )
    )
    floored = baseline_projection_from_features(
        PlayerFeatureInputs(
            position="WR", snap_proxy=0.1, route_proxy=0.51, target_proxy=0.314,
            rush_share=0.0, red_zone_share=0.15, qb_dropback_factor=1.0, qb_pressure_factor=1.0,
            team_pace_factor=0.97, team_pass_rate_factor=1.10, availability_confidence=0.9,
            role_confidence=depth_role_confidence_floor("WR", 1.0) or 0.88,
            skill_talent_factor=1.14,
        )
    )
    assert floored["receiving_yards_mean"] > crushed["receiving_yards_mean"]
    assert floored["receiving_yards_mean"] > 80.0
    assert skill_talent_factor_from_prior_ypg(100.0, position="WR") > 1.08


def test_usage_rank_depth_fills_chart_gaps_for_wr1() -> None:
    chart = {"MIN": {"other-wr": 2.0}}
    usage = usage_rank_depth_orders(
        [
            {"team": "MIN", "player_id": "addison", "position": "WR", "target_proxy": 0.22},
            {"team": "MIN", "player_id": "jefferson", "position": "WR", "target_proxy": 0.31},
            {"team": "MIN", "player_id": "other-wr", "position": "WR", "target_proxy": 0.11},
            {"team": "MIN", "player_id": "hock", "position": "TE", "target_proxy": 0.14},
        ],
        positions=("WR", "TE"),
        usage_key="target_proxy",
    )
    merged = merge_depth_orders(chart, usage)
    # Chart depth wins for known ids.
    assert merged["MIN"]["other-wr"] == 2.0
    # Usage rank fills Jefferson as WR1 and Addison as WR2 (WR-only ranking).
    assert merged["MIN"]["jefferson"] == 1.0
    assert merged["MIN"]["addison"] == 2.0
    # TE ranked separately — Hockenson is TE1, not WR3.
    assert merged["MIN"]["hock"] == 1.0
    assert effective_skill_role_confidence(
        position="WR",
        role_confidence=0.16,
        depth_order=merged["MIN"]["jefferson"],
    ) >= 0.88


def test_elite_rb_season_rush_scale() -> None:
    bell = baseline_projection_from_features(
        PlayerFeatureInputs(
            position="RB", snap_proxy=0.55, route_proxy=0.25, target_proxy=0.12,
            rush_share=0.55, red_zone_share=0.35, qb_dropback_factor=1.0, qb_pressure_factor=1.0,
            team_pace_factor=1.0, team_pass_rate_factor=1.0, availability_confidence=0.95,
            role_confidence=0.88, skill_talent_factor=1.15,
        )
    )
    # Phase 2 compresses carry/YPC vs the prior ~1500+ band; still clears a
    # true workhorse season floor without restoring the +11 RB1 residual.
    assert bell["rush_yards_mean"] * 17 > 1300.0
    assert skill_talent_factor_from_prior_ypg(95.0, position="RB") > 1.10


def test_qb_ypa_intercept_matches_real_pressure_adjusted_fit() -> None:
    # Residual pass-yards undercount after volume fixes was YPA (attempts
    # already slightly high). Guard the refit intercept 6.97 - 0.6*pressure.
    qb = baseline_projection_from_features(
        PlayerFeatureInputs(
            position="QB", snap_proxy=0.85, route_proxy=0.0, target_proxy=0.0,
            rush_share=0.05, red_zone_share=0.10, qb_dropback_factor=1.1, qb_pressure_factor=0.5,
            team_pace_factor=1.0, team_pass_rate_factor=1.0, availability_confidence=1.0,
            role_confidence=1.0, team_snap_share=0.95, qb_starter_share=1.0,
        )
    )
    ypa = qb["pass_yards_mean"] / qb["attempts_mean"]
    # At pressure=0.5: 6.97 - 0.3 = 6.67 (opp_pass default 1.0, conf=1.0).
    assert 6.4 < ypa < 6.9
    assert qb["pass_yards_mean"] > 200.0


def test_receiving_ypr_and_catch_rate_match_real_position_fits() -> None:
    # Real bug found while auditing residual receiving-yards undercount
    # after the targets_mean fix: targets were already roughly right, but
    # catch rate / YPR were systematically low (esp. WR YPR ~8.9 vs real
    # ~13; TE/RB catch rates sharing an undercalibrated WR-shaped formula).
    # Guard the position-specific WLS fits shipped against that audit.
    wr = baseline_projection_from_features(
        PlayerFeatureInputs(
            position="WR", snap_proxy=0.7, route_proxy=0.30, target_proxy=0.22,
            rush_share=0.0, red_zone_share=0.15, qb_dropback_factor=1.0, qb_pressure_factor=1.0,
            team_pace_factor=1.0, team_pass_rate_factor=1.0, availability_confidence=1.0, role_confidence=1.0,
        )
    )
    te = baseline_projection_from_features(
        PlayerFeatureInputs(
            position="TE", snap_proxy=0.7, route_proxy=0.30, target_proxy=0.22,
            rush_share=0.0, red_zone_share=0.15, qb_dropback_factor=1.0, qb_pressure_factor=1.0,
            team_pace_factor=1.0, team_pass_rate_factor=1.0, availability_confidence=1.0, role_confidence=1.0,
        )
    )
    rb = baseline_projection_from_features(
        PlayerFeatureInputs(
            position="RB", snap_proxy=0.55, route_proxy=0.12, target_proxy=0.12,
            rush_share=0.40, red_zone_share=0.30, qb_dropback_factor=1.0, qb_pressure_factor=1.0,
            team_pace_factor=1.0, team_pass_rate_factor=1.0, availability_confidence=1.0, role_confidence=1.0,
        )
    )
    wr_ypr = wr["receiving_yards_mean"] / wr["receptions_mean"]
    te_ypr = te["receiving_yards_mean"] / te["receptions_mean"]
    te_cr = te["receptions_mean"] / te["targets_mean"]
    wr_cr = wr["receptions_mean"] / wr["targets_mean"]
    rb_cr = rb["receptions_mean"] / rb["targets_mean"]
    # Flat WR YPR fit is 12.8; TE is 10.3; confidence_scale is 1.0 here so
    # these should land on the fitted constants (opp_pass default = 1.0).
    assert 12.3 < wr_ypr < 13.3
    assert 9.8 < te_ypr < 10.8
    # TE catch rate must exceed WR at the same route_proxy (real TE ~0.74
    # vs WR ~0.64); RB catch rate must clear the old ~0.65 underfit.
    assert te_cr > wr_cr
    assert rb_cr > 0.75


def test_wr_target_volume_scales_down_realistically_by_role() -> None:
    def _proj(target_proxy: float, route_proxy: float, role_confidence: float) -> dict:
        inputs = PlayerFeatureInputs(
            position="WR", snap_proxy=route_proxy, route_proxy=route_proxy, target_proxy=target_proxy,
            rush_share=0.0, red_zone_share=0.15, qb_dropback_factor=1.0, qb_pressure_factor=1.0,
            team_pace_factor=1.0, team_pass_rate_factor=1.0, availability_confidence=0.92, role_confidence=role_confidence,
        )
        return baseline_projection_from_features(inputs)

    wr1 = _proj(0.30, 0.50, 0.75)
    wr3 = _proj(0.10, 0.35, 0.45)
    wr4 = _proj(0.03, 0.15, 0.25)
    assert wr1["targets_mean"] > wr3["targets_mean"] > wr4["targets_mean"]
    assert wr1["receiving_yards_mean"] > wr3["receiving_yards_mean"] > wr4["receiving_yards_mean"]
    # A real depth WR should land at a plausible low-volume season total,
    # not zero and not accidentally still-inflated.
    assert 0.0 < wr4["receiving_yards_mean"] * 17 < 300.0


def test_mobile_qb_rush_share_produces_realistic_season_volume() -> None:
    # Real bug found while re-validating the targets_mean fix: QB
    # carries_mean multiplied the same real, correctly-denominated
    # rush_share signal RB's carries_mean already uses successfully by a
    # coefficient ~7.5x too small (4.0 vs. RB's 24.0) -- a real mobile
    # starter with a genuine ~0.19-0.29 rush_share (real 2023-2025 range for
    # Lamar Jackson/Jalen Hurts/Josh Allen-caliber runners) projected for
    # only ~2-2.4 carries/game instead of a realistic ~6-9, crushing
    # rushing yards/TDs for every mobile QB league-wide. Fixed via a real
    # weighted linear regression against 110 real 2023-2025 QB-seasons
    # (>=8 games): carries_per_game = 0.26 + 29.85*rush_share, R^2=0.857.
    mobile_qb = PlayerFeatureInputs(
        position="QB", snap_proxy=0.38, route_proxy=0.0, target_proxy=0.0,
        rush_share=0.22, red_zone_share=0.10, qb_dropback_factor=1.0, qb_pressure_factor=1.0,
        team_pace_factor=1.0, team_pass_rate_factor=1.0, availability_confidence=0.95, role_confidence=0.75,
        team_snap_share=0.60,
    )
    projection = baseline_projection_from_features(mobile_qb)
    season_rush_yards = projection["rush_yards_mean"] * 17
    assert projection["carries_mean"] > 5.0
    assert 300.0 < season_rush_yards < 800.0


def test_pocket_qb_rush_share_stays_low() -> None:
    # Guard against the fix above accidentally inflating a real pocket
    # passer's negligible rushing role.
    pocket_qb = PlayerFeatureInputs(
        position="QB", snap_proxy=0.38, route_proxy=0.0, target_proxy=0.0,
        rush_share=0.03, red_zone_share=0.05, qb_dropback_factor=1.0, qb_pressure_factor=1.0,
        team_pace_factor=1.0, team_pass_rate_factor=1.0, availability_confidence=0.95, role_confidence=0.75,
        team_snap_share=0.60,
    )
    projection = baseline_projection_from_features(pocket_qb)
    assert projection["carries_mean"] < 2.0


def test_elite_receiver_rec_tds_land_in_realistic_season_range() -> None:
    # Real bug found while re-validating the targets_mean fix (same
    # "evaporating share" pattern, but in TD math): rec_tds_mean's
    # coefficient (0.14 for WR/TE, 0.08 for RB) drastically undercounted
    # real receiving TDs -- a real elite WR1 catching 126 passes for 1,235
    # yards was projecting under 3 receiving TDs for the WHOLE SEASON (real
    # comparable seasons score 9-11). Fixed via a weighted-least-squares fit
    # against real 2023-2025 usage data (receiving TDs vs.
    # receptions*red_zone_share, weighted by volume so real elite
    # performances anchor the fit instead of bench-role noise): WR/TE
    # coefficient ~0.50, RB (receiving-only, isolated from rushing TDs via
    # team pass_touchdowns minus WR/TE touchdowns_scored) ~0.10.
    elite_wr1 = PlayerFeatureInputs(
        position="WR", snap_proxy=0.6, route_proxy=0.46, target_proxy=0.27,
        rush_share=0.0, red_zone_share=0.20, qb_dropback_factor=1.0, qb_pressure_factor=1.0,
        team_pace_factor=1.0, team_pass_rate_factor=1.0, availability_confidence=0.95, role_confidence=0.75,
    )
    projection = baseline_projection_from_features(elite_wr1)
    season_rec_tds = projection["rec_tds_mean"] * 17
    assert 5.0 < season_rec_tds < 14.0


def test_pass_catching_rb_rec_tds_land_in_realistic_season_range() -> None:
    elite_pass_catching_rb = _rb_inputs(target_proxy=0.15, red_zone_share=0.20)
    projection = baseline_projection_from_features(elite_pass_catching_rb)
    season_rec_tds = projection["rec_tds_mean"] * 17
    assert 0.0 < season_rec_tds < 6.0


def test_bellcow_rb_rush_tds_no_longer_cluster_at_extreme_range() -> None:
    # Real bug found via a live 2026 spot-check: 7+ different real bell-cow
    # RBs (J.Taylor, D.Henry, C.McCaffrey, J.Gibbs, J.Williams, C.Brown,
    # B.Robinson) were all simultaneously projecting for 15-19 season
    # rushing TDs at the old 0.16 coefficient -- real NFL seasons rarely see
    # more than 2-3 backs clear 15. Fixed via a real weighted-least-squares
    # fit against 259 real 2023-2025 RB-seasons (weighted by real season
    # carries volume, real rushing TDs isolated from receiving TDs via
    # play-by-play): coefficient 0.098 (R^2=0.489), refit here to 0.10. This
    # locks in the realistic range for a real bell-cow profile (~17
    # carries/game, ~0.42 red_zone_share, matching the real flagged
    # players), which used to land at 18-20 season rush TDs.
    bellcow_rb = _rb_inputs(rush_share=0.60, red_zone_share=0.42, role_confidence=0.80, availability_confidence=0.92)
    projection = baseline_projection_from_features(bellcow_rb)
    season_rush_tds = projection["rush_tds_mean"] * 17
    assert 8.0 < season_rush_tds < 15.0


def test_qb_pass_tds_mean_realistic_season_range() -> None:
    # Real bug found during the same TD-coefficient audit that fixed RB
    # rush_tds_mean above: pass_tds_mean's `0.32 * red_zone_share`
    # interaction term assumed a QB's OWN red_zone_share (overwhelmingly a
    # rushing-share signal for a QB, not a passing-efficiency one) predicts
    # passing-TD rate. Real weighted least squares against 108 real
    # 2023-2025 QB-seasons showed the interaction explains ~zero
    # incremental variance (and its true sign is negative, not +0.32),
    # while the flat base rate (0.72) was itself undercounting real pass
    # TDs by a real weighted-average bias of -0.083 TDs/game (~-1.4/season)
    # for a typical starter. Refit to a flat 0.79 with the red_zone_share
    # term dropped -- locks in a realistic season range for a real
    # full-time starter profile.
    starter_qb = PlayerFeatureInputs(
        position="QB", snap_proxy=0.85, route_proxy=0.0, target_proxy=0.05,
        rush_share=0.05, red_zone_share=0.05, qb_dropback_factor=1.0, qb_pressure_factor=1.0,
        team_pace_factor=1.0, team_pass_rate_factor=1.0, availability_confidence=0.95, role_confidence=0.80,
        team_snap_share=0.95,
    )
    projection = baseline_projection_from_features(starter_qb)
    season_pass_tds = projection["pass_tds_mean"] * 17
    assert 24.0 < season_pass_tds < 42.0


def test_qb_pass_tds_mean_no_longer_depends_on_red_zone_share() -> None:
    # Regression guard for the fix above: real data showed no genuine
    # relationship between a QB's own red_zone_share (a rushing-share
    # proxy) and passing-TD efficiency, so the term was dropped entirely --
    # pass_tds_mean must now be identical regardless of red_zone_share,
    # holding every other real input fixed.
    def _proj(red_zone_share: float) -> dict:
        return baseline_projection_from_features(
            PlayerFeatureInputs(
                position="QB", snap_proxy=0.85, route_proxy=0.0, target_proxy=0.05,
                rush_share=0.20, red_zone_share=red_zone_share, qb_dropback_factor=1.0, qb_pressure_factor=1.0,
                team_pace_factor=1.0, team_pass_rate_factor=1.0, availability_confidence=0.95, role_confidence=0.80,
                team_snap_share=0.95,
            )
        )
    low_rz = _proj(0.02)
    high_rz = _proj(0.30)
    assert low_rz["pass_tds_mean"] == high_rz["pass_tds_mean"]


def test_prop_edge_behaves_directionally() -> None:
    edge = evaluate_prop_edge(
        model_mean=84.0,
        model_std=14.0,
        line=70.5,
        market_over_price=-110,
        market_under_price=-110,
    )
    assert edge["over_prob"] > edge["under_prob"]
    assert edge["edge_over"] is not None and edge["edge_over"] > 0
    assert isinstance(edge["fair_over_price"], int)


def test_fantasy_scoring_profiles_are_ordered() -> None:
    statline = {
        "pass_yards": 0.0,
        "pass_tds": 0.0,
        "rush_yards": 24.0,
        "rush_tds": 0.3,
        "receiving_yards": 84.0,
        "receptions": 7.0,
        "rec_tds": 0.5,
    }
    standard = fantasy_points_from_projection(scoring_profile="standard", **statline)
    half = fantasy_points_from_projection(scoring_profile="half_ppr", **statline)
    ppr = fantasy_points_from_projection(scoring_profile="ppr", **statline)
    assert standard < half < ppr
