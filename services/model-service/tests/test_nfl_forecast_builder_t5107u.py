"""Causal / fit-vintage / blend tests for the t5107u forecast builder."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.services.nfl_t5107u.builder import (
    BuilderRefuse,
    build_forecasts,
    challenger_margin,
)
from src.services.nfl_t5107u.if_control import (
    IF_TIP,
    LABEL_ARCHIVED,
    REQUIRED_FIELDS,
    resolve_if_margin,
    retained_if_arm,
)
from src.services.nfl_t5107u.manifest import build_frozen_manifest
from src.services.nfl_t5107u.q2 import (
    A_Q2,
    B_Q2,
    FIT_POLICY,
    TRAINING_END_SEASON,
    TRANSFER_MAX_TRAINING_SEASON,
    Game,
    q2_pm_new,
    verify_q2_transfer_policy,
)


def _ko(day: int, hour: int = 17) -> datetime:
    return datetime(2020, 9, day, hour, 0, tzinfo=timezone.utc)


def _game(
    game_id: str,
    *,
    season: int = 2020,
    week: int = 1,
    home: str = "KC",
    away: str = "HOU",
    kickoff: datetime | None = None,
    home_score: float | None = None,
    away_score: float | None = None,
) -> Game:
    return Game(
        season=season,
        week=week,
        game_id=game_id,
        home=home,
        away=away,
        kickoff_utc=kickoff or _ko(13),
        home_score=home_score,
        away_score=away_score,
    )


def _complete_packet(game_id: str = "2020_01_HOU_KC") -> dict:
    packet = {name: {"status": "DERIVED_PREGAME", "reconstructed_value": 0.1} for name in REQUIRED_FIELDS}
    packet["game_id"] = {"status": "DERIVED_PREGAME", "reconstructed_value": game_id}
    packet["home_team"] = {"status": "DERIVED_PREGAME", "reconstructed_value": "KC"}
    packet["away_team"] = {"status": "DERIVED_PREGAME", "reconstructed_value": "HOU"}
    return packet


def test_q2_transfer_policy_verified_no_refit():
    proof = verify_q2_transfer_policy(proposed_refit=False)
    assert proof["transfer_verified"] is True
    assert proof["refit_authorized"] is False
    assert proof["refit_performed"] is False
    assert proof["fit_policy"] == FIT_POLICY
    assert TRAINING_END_SEASON <= TRANSFER_MAX_TRAINING_SEASON
    assert proof["a_q2"] == A_Q2
    assert proof["b_q2"] == B_Q2
    with pytest.raises(Exception, match="refit is not authorized"):
        verify_q2_transfer_policy(proposed_refit=True)
    with pytest.raises(Exception, match="cannot transfer"):
        verify_q2_transfer_policy(training_seasons=(2020, 2021, 2022))


def test_q2_pm_new_frozen_and_refuses_alternate_coeffs():
    assert q2_pm_new(2.0) == pytest.approx(A_Q2 + B_Q2 * 2.0)
    with pytest.raises(Exception, match="frozen"):
        q2_pm_new(2.0, a_q2=0.0, b_q2=1.0)


def test_challenger_blend_and_forbidden_knobs():
    assert challenger_margin(4.0, 8.0) == pytest.approx(6.0)
    with pytest.raises(BuilderRefuse, match="extra HFA"):
        challenger_margin(4.0, 8.0, extra_hfa=1.0)
    with pytest.raises(BuilderRefuse, match="market blending"):
        challenger_margin(4.0, 8.0, market_blend=0.2)
    with pytest.raises(BuilderRefuse, match="weight search"):
        challenger_margin(4.0, 8.0, w=0.6)


def test_asof_is_prior_game_only_and_target_excluded():
    prior = _game(
        "2020_01_HOU_KC",
        week=1,
        kickoff=_ko(13),
        home_score=34,
        away_score=20,
    )
    later = _game(
        "2020_03_BUF_KC",
        week=3,
        home="KC",
        away="BUF",
        kickoff=_ko(27),
        home_score=40,
        away_score=3,
    )
    target = _game(
        "2020_02_LAC_KC",
        week=2,
        home="KC",
        away="LAC",
        kickoff=_ko(20),
    )
    payload = build_forecasts(
        [target],
        history=[prior, later],
        archived_if={
            target.game_id: {
                "if_tip": IF_TIP,
                "if_forecast_label": "independent_fair",
                "if_margin_mu": 5.0,
            }
        },
    )
    row = payload["forecasts"][0]
    assert row["n_asof_games"] == 1
    assert row["m_q2"] is not None
    # Same targets with later game removed must match (later cannot leak backward).
    payload2 = build_forecasts(
        [target],
        history=[prior],
        archived_if={
            target.game_id: {
                "if_tip": IF_TIP,
                "if_forecast_label": "independent_fair",
                "if_margin_mu": 5.0,
            }
        },
    )
    assert payload2["forecasts"][0]["m_q2"] == row["m_q2"]
    assert payload2["forecasts"][0]["rating_diff"] == row["rating_diff"]


def test_history_may_not_include_target_row():
    target = _game("2020_01_HOU_KC", home_score=27, away_score=20)
    with pytest.raises(BuilderRefuse, match="target game"):
        build_forecasts([target], history=[target])


def test_archived_vs_reconstructed_if_labels():
    archived = resolve_if_margin(
        "g1",
        archived={"if_tip": IF_TIP, "if_forecast_label": "independent_fair", "if_margin_mu": 3.25},
    )
    assert archived.status == "archived"
    assert archived.label == LABEL_ARCHIVED
    assert archived.margin_mu == 3.25

    with pytest.raises(Exception, match="produce-μ"):
        resolve_if_margin(
            "g2",
            recon_packet=_complete_packet("g2"),
            reconstructed_margin_mu=2.5,
            if_tree_present=True,
        )

    blocked = resolve_if_margin("g3")
    assert blocked.status == "blocked"
    assert "if_tree_6ca03716" not in blocked.missing_artifacts
    assert "RECON_MATRIX_2020_2023_REG" in blocked.missing_artifacts
    assert set(REQUIRED_FIELDS) <= set(blocked.missing_fields)


def test_silent_if_drop_refused():
    with pytest.raises(Exception, match="silent IF drop"):
        resolve_if_margin("g", allow_silent_drop=True)
    with pytest.raises(Exception, match="IF arm empty"):
        retained_if_arm([])


def test_if_block_retains_control_and_blocks_challenger():
    target = _game("2020_01_HOU_KC")
    payload = build_forecasts([target], history=[])
    row = payload["forecasts"][0]
    assert row["if_status"] == "blocked"
    assert "if" in row["blocked_legs"]
    assert "challenger" in row["blocked_legs"]
    assert payload["if_arm"]["blocked"] == 1
    assert payload["if_arm"]["total"] == 1
    assert row["m_challenger"] is None
    assert row["eval"] is None
    assert row["stage_c"] is None


def test_archived_if_plus_q2_emits_challenger():
    prior = _game(
        "2020_01_HOU_KC",
        kickoff=_ko(13),
        home_score=31,
        away_score=17,
    )
    target = _game(
        "2020_02_LAC_KC",
        week=2,
        home="KC",
        away="LAC",
        kickoff=_ko(20),
    )
    payload = build_forecasts(
        [target],
        history=[prior],
        archived_if={
            target.game_id: {
                "if_tip": "6ca03716fe52930332d5ffba302c312a651980cc",
                "if_forecast_label": "independent_fair",
                "if_margin_mu": 4.0,
            }
        },
    )
    row = payload["forecasts"][0]
    assert row["if_label"] == LABEL_ARCHIVED
    assert row["m_if"] == 4.0
    assert row["m_q2"] is not None
    assert row["m_challenger"] == pytest.approx(0.5 * 4.0 + 0.5 * row["m_q2"])
    assert row["q2_parameter_label"].startswith("FROZEN_Q2PB")


def test_eval_generation_gated_on_sealed_manifest():
    target = _game("2022_01_BUF_LA", season=2022, kickoff=datetime(2022, 9, 11, 17, tzinfo=timezone.utc))
    with pytest.raises(BuilderRefuse, match="FROZEN_MANIFEST"):
        build_forecasts([target], history=[])
    payload = build_forecasts(
        [target],
        history=[],
        allow_eval_generation=True,
        frozen_manifest_sealed=True,
        archived_if={
            target.game_id: {
                "if_tip": IF_TIP,
                "if_forecast_label": "independent_fair",
                "if_margin_mu": 1.0,
            }
        },
    )
    assert payload["forecasts"][0]["split"] == "EVAL"
    assert payload["eval"] is None
    assert payload["scoring"] is None


def test_refuses_2024_and_stage_c_columns():
    with pytest.raises(BuilderRefuse, match="sealed season"):
        build_forecasts(
            [
                {
                    "season": 2024,
                    "week": 1,
                    "game_id": "2024_01_KC_BAL",
                    "home": "KC",
                    "away": "BAL",
                    "kickoff_utc": "2024-09-05T17:00:00Z",
                    "season_type": "REG",
                }
            ]
        )
    with pytest.raises(BuilderRefuse, match="stage_c|Stage C"):
        build_forecasts(
            [
                {
                    "season": 2020,
                    "week": 1,
                    "game_id": "2020_01_HOU_KC",
                    "home": "KC",
                    "away": "HOU",
                    "kickoff_utc": "2020-09-13T17:00:00Z",
                    "season_type": "REG",
                    "stage_c": 1,
                }
            ]
        )


def test_naive_kickoff_refused():
    with pytest.raises(Exception, match="naive"):
        build_forecasts(
            [
                {
                    "season": 2020,
                    "week": 1,
                    "game_id": "2020_01_HOU_KC",
                    "home": "KC",
                    "away": "HOU",
                    "kickoff_utc": "2020-09-13T17:00:00",
                    "season_type": "REG",
                }
            ]
        )


def test_frozen_manifest_seals_design_input_fit_before_eval():
    manifest = build_frozen_manifest()
    assert manifest["sealed"] is True
    assert manifest["sealed_before_eval_generation"] is True
    assert manifest["eval_generation"] == "NOT_RUN"
    assert manifest["exec_scoring"].startswith("REFUSED")
    assert manifest["fit_policy"]["transfer_verified"] is True
    assert manifest["fit_policy"]["dev_2020_21_refit"] is False
    assert manifest["design"]["challenger_weight"] == 0.5
    blockers = {row["artifact"] for row in manifest["blockers"]}
    assert "b41f4b43_hist_inputs" in blockers
    assert "RECON_MATRIX_2020_2023_REG" in blockers
    assert "if_tree_6ca03716" not in blockers
    assert "outcomes_2023_score_only" in blockers
    assert "kickoff_utc_timezone" in blockers
