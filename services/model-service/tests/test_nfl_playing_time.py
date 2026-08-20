from src.services.nfl_playing_time import (
    QB1_SHARE,
    QB2_SHARE,
    allocate_qb_role_shares,
    apply_hard_share_caps,
    depth_target_prior,
    role_from_depth_order,
)
from src.services.nfl_player_projection_engine import compute_qb_starter_shares


def test_role_labels_from_depth() -> None:
    assert role_from_depth_order("QB", 1) == "QB1"
    assert role_from_depth_order("QB", 3) == "QB3+"
    assert role_from_depth_order("WR", 4) == "WR4+"
    assert role_from_depth_order("RB", 3) == "RB3+"
    assert role_from_depth_order("TE", 2) == "TE2+"


def test_qb3_share_is_zero_and_conserved() -> None:
    shares = allocate_qb_role_shares(["qb1", "qb2", "qb3", "qb4"])
    assert shares["qb1"] == QB1_SHARE
    assert shares["qb2"] == QB2_SHARE
    assert shares["qb3"] == 0.0
    assert shares["qb4"] == 0.0
    assert abs(sum(shares.values()) - 1.0) < 1e-9


def test_wr4_target_prior_near_zero() -> None:
    assert depth_target_prior("WR", 1) >= 0.30
    assert depth_target_prior("WR", 4) <= 0.02
    assert depth_target_prior("WR", 6) <= 0.015


def test_hard_caps_move_qb3_volume_to_qb1() -> None:
    raw = {"cousins": 0.06, "mendoza": 0.06, "oconnell": 0.88}
    depths = {"cousins": 1.0, "mendoza": 2.0, "oconnell": 3.0}
    out = apply_hard_share_caps(raw, depths, position="QB")
    assert out["cousins"] >= 0.90
    assert out["oconnell"] <= 0.01
    assert abs(sum(out.values()) - 1.0) < 1e-6


def test_oconnell_class_room_after_sot_caps() -> None:
    shares = compute_qb_starter_shares(
        {"cousins": 0.05, "mendoza": 0.05, "oconnell": 0.55},
        depth_orders={"cousins": 1.0, "mendoza": 2.0, "oconnell": 3.0},
        prior_attempts={"oconnell": 500.0, "cousins": 0.0, "mendoza": 0.0},
    )
    # ~0.94 of team attempts * ~35 att * 17g * ~7 ypa ≈ starter yards, not 3k on QB3.
    assert shares["oconnell"] * 35 * 17 * 7.2 < 80.0
    assert shares["cousins"] * 35 * 17 * 7.2 > 3000.0
