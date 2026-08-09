"""Phase 2: general features replace named-team sculpture."""

from __future__ import annotations

from datetime import date

from src.services.nfl_season_engine.calibration import ENGINE_VERSION, LEAGUE_PASS_YARDS_POOL
from src.services.nfl_season_engine.coaching_tendencies import profile_for_team
from src.services.nfl_season_engine.data_integrity import validate_packaged_depth_file
from src.services.nfl_season_engine.loaders import (
    build_packaged_real_universe,
    load_packaged_depth_chart,
)
from src.services.nfl_season_engine.ol_protection import (
    compute_ol_protection,
)
from src.services.nfl_season_engine.qb_rushing_profile import (
    profiles_from_depth_rows,
    resolve_qb1_profile,
)
from src.services.nfl_season_engine.season_budgets import (
    TEAM_PASS_VOLUME_IDENTITY_ADJUSTMENTS,
    TeamVolumeFactors,
    apply_general_volume_features,
    compute_team_season_budgets,
    compute_universe_season_budgets,
    structural_team_budget,
)


def test_engine_version_phase2() -> None:
    assert ENGINE_VERSION.startswith("nfl-season-engine-v1.25")
    assert "phase2-features" in ENGINE_VERSION


def test_named_team_pass_identity_overlays_removed() -> None:
    assert TEAM_PASS_VOLUME_IDENTITY_ADJUSTMENTS == {}


def test_qb_rushing_profile_from_sot_player_id() -> None:
    rows, _ = load_packaged_depth_chart(2026)
    profiles = profiles_from_depth_rows(rows)
    assert profiles["BAL"].tier == "designed_run_heavy"
    assert profiles["BAL"].pass_volume_mult < 1.0
    assert profiles["BAL"].rush_volume_mult > 1.0
    assert profiles["ARI"].tier == "pocket"
    assert profiles["WAS"].tier == "dual_threat"
    assert profiles["SEA"].tier == "pocket"


def test_ol_protection_was_tunsil_allegretti() -> None:
    _, meta = load_packaged_depth_chart(2026)
    feat = compute_ol_protection("WAS", meta.get("ol_roles") or [])
    assert feat.fidelity == "applied"
    assert feat.protection_index < 0.95  # LT out + C out + competition
    assert feat.ypa_mult < 1.0
    assert feat.offense_index_delta < 0.0
    assert any("edge_out" in d for d in feat.drivers)
    assert any("center_out" in d for d in feat.drivers)


def test_coaching_profiles_cover_former_sculpture_teams() -> None:
    for team in ("ARI", "SEA", "WAS", "BAL"):
        p = profile_for_team(team)
        assert p.source == "curated_prior"
        assert p.label != "league_average"


def test_general_volume_features_conserve_after_pool() -> None:
    teams = [
        "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
        "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
        "LA", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG",
        "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
    ]
    factors = {t: TeamVolumeFactors(team=t) for t in teams}
    rows, _ = load_packaged_depth_chart(2026)
    qb = profiles_from_depth_rows(rows)
    budgets = compute_team_season_budgets(factors, qb_profiles=qb)
    assert abs(sum(b.pass_yards for b in budgets.values()) - LEAGUE_PASS_YARDS_POOL) < 1.0
    # Dual-threat BAL should land below pocket SEA on raw structural×feature
    # before pool in typical equal-factor setups — after pool, relative shape holds.
    raw = {t: structural_team_budget(factors[t]) for t in teams}
    adj = apply_general_volume_features(raw, qb_profiles=qb)
    assert adj["BAL"].pass_yards < adj["SEA"].pass_yards
    assert "general_volume_features_v1" in adj["BAL"].notes
    assert "qb_rush_designed_run_heavy" in adj["BAL"].notes


def test_packaged_universe_applies_ol_and_qb_rush() -> None:
    universe = build_packaged_real_universe(2026)
    was = universe.strengths["WAS"]
    assert "ol_protection" in (was.drivers or {})
    assert float(was.drivers["ol_protection"]["protection_index"]) < 0.95
    bal_qb = next(
        r for r in universe.rosters["BAL"] if r.position == "QB" and r.depth_order == 1
    )
    assert bal_qb.rush_share >= 0.15
    budgets = compute_universe_season_budgets(universe)
    assert abs(sum(b.pass_yards for b in budgets.values()) - LEAGUE_PASS_YARDS_POOL) < 1.0


def test_phase1_gate_still_passes() -> None:
    report = validate_packaged_depth_file(
        2026, reference_date=date(2026, 8, 9), max_age_days=7
    )
    assert report.ok is True
    assert report.snapshot_id == "nfl-depth-2026-w1-20260809T190000Z"


def test_resolve_unknown_qb_defaults_pocket() -> None:
    p = resolve_qb1_profile(player_id="00-0099999", player_name="Unknown", team="XXX")
    assert p.tier == "pocket"
    assert abs(p.pass_volume_mult - 1.0) < 0.05
