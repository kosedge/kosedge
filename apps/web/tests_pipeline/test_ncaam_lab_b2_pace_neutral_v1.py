"""Focused tests for B2-PACE-NEUTRAL-v1 research challenger + venue identity."""

from __future__ import annotations

import math
from datetime import date
from pathlib import Path

import polars as pl
import pytest

from ncaam_lab.fair_b2 import compute_fair_b2
from ncaam_lab.fair_b2_pace_v1 import (
    CANDIDATE_ID as PACE_ID,
    FAIR_COL as PACE_FAIR_COL,
    FROZEN_HCA,
    compute_fair_b2_pace_v1,
    scalar_fair_home_margin as pace_scalar,
)
from ncaam_lab.fair_b2_pace_neutral_v1 import (
    CANDIDATE_ID,
    ELIGIBLE_COL,
    FAIR_COL,
    FROZEN_HCA_HOME,
    FROZEN_HCA_NEUTRAL,
    HCA_COL,
    METHOD_ID,
    assert_parent_immutability_pins,
    compute_fair_b2_pace_neutral_v1,
    resolve_hca_for_venue_status,
    scalar_fair_home_margin,
)
from ncaam_lab.materialize import materialize_lab_fair
from ncaam_lab.neutral_site_identity import (
    VENUE_STATUS_HOME,
    VENUE_STATUS_NEUTRAL,
    VENUE_STATUS_UNKNOWN,
    assert_no_holdout_or_test_a_paths,
    attach_venue_status,
    classify_venue_status,
)


def _base_games(**overrides) -> pl.DataFrame:
    row = {
        "event_id": "e1",
        "tip_date": date(2022, 12, 10),
        "home_team_id": "duke",
        "away_team_id": "kentucky",
        "adjem_home": 30.0,
        "adjem_away": 10.0,
        "adjt_home": 67.5,
        "adjt_away": 67.5,
        "kenpom_as_of_home": date(2022, 12, 4),
        "kenpom_as_of_away": date(2022, 12, 4),
        "adjoe_home": 110.0,
        "adjde_home": 90.0,
        "adjoe_away": 100.0,
        "adjde_away": 100.0,
        "venue_status": VENUE_STATUS_HOME,
    }
    row.update(overrides)
    return pl.DataFrame([row])


def test_neutral_identity_home_away_and_ambiguous() -> None:
    home = classify_venue_status(neutral_site_raw=False)
    assert home["venue_status"] == VENUE_STATUS_HOME
    neut = classify_venue_status(neutral_site_raw=True)
    assert neut["venue_status"] == VENUE_STATUS_NEUTRAL
    unk = classify_venue_status(neutral_site_raw=None)
    assert unk["venue_status"] == VENUE_STATUS_UNKNOWN
    # Postseason venue token mismatch → unknown (fail closed)
    conflict = classify_venue_status(
        neutral_site_raw=False,
        venue_name="Madison Square Garden",
        home_team_id="duke",
        season_type="postseason",
    )
    assert conflict["venue_status"] == VENUE_STATUS_UNKNOWN
    assert conflict["conflict_reason"] == "postseason_venue_home_token_mismatch"


def test_ambiguous_site_fail_closed_on_attach() -> None:
    games = _base_games().drop("venue_status")
    # Empty packs → all unknown
    out, receipt = attach_venue_status(games, pack_paths=[])
    assert out["venue_status"][0] == VENUE_STATUS_UNKNOWN
    assert receipt["n_unknown"] == 1


def test_hca_resolution_and_scalar_home_vs_neutral() -> None:
    assert resolve_hca_for_venue_status(VENUE_STATUS_HOME) == FROZEN_HCA_HOME
    assert resolve_hca_for_venue_status(VENUE_STATUS_NEUTRAL) == FROZEN_HCA_NEUTRAL
    assert resolve_hca_for_venue_status(VENUE_STATUS_UNKNOWN) is None
    assert resolve_hca_for_venue_status(None) is None

    home = scalar_fair_home_margin(
        adjem_home=30.0,
        adjem_away=10.0,
        adjt_home=67.5,
        adjt_away=67.5,
        venue_status=VENUE_STATUS_HOME,
    )
    neut = scalar_fair_home_margin(
        adjem_home=30.0,
        adjem_away=10.0,
        adjt_home=67.5,
        adjt_away=67.5,
        venue_status=VENUE_STATUS_NEUTRAL,
    )
    unk = scalar_fair_home_margin(
        adjem_home=30.0,
        adjem_away=10.0,
        adjt_home=67.5,
        adjt_away=67.5,
        venue_status=VENUE_STATUS_UNKNOWN,
    )
    # 20 * 0.675 + 2.8696 = 16.3696; neutral drops HCA
    assert home == pytest.approx(16.3696)
    assert neut == pytest.approx(13.5)
    assert unk is None
    assert home == pytest.approx(neut + FROZEN_HCA_HOME)


def test_point_in_time_and_non_finite_fail_closed() -> None:
    # Post-tip as-of → ineligible
    games = _base_games(kenpom_as_of_home=date(2022, 12, 11))
    out = compute_fair_b2_pace_neutral_v1(games)
    assert out[ELIGIBLE_COL][0] is False
    assert out[FAIR_COL][0] is None

    for bad in (math.nan, math.inf, -math.inf):
        g = _base_games(adjem_home=bad)
        o = compute_fair_b2_pace_neutral_v1(g)
        assert o[ELIGIBLE_COL][0] is False
        assert o[FAIR_COL][0] is None


def test_unknown_venue_fail_closed_frame() -> None:
    games = _base_games(venue_status=VENUE_STATUS_UNKNOWN)
    out = compute_fair_b2_pace_neutral_v1(games)
    assert out[ELIGIBLE_COL][0] is False
    assert out[FAIR_COL][0] is None
    assert out[HCA_COL][0] is None


def test_home_matches_parent_pace_on_confirmed_home() -> None:
    games = _base_games(venue_status=VENUE_STATUS_HOME)
    incumbent = compute_fair_b2(games, hca=FROZEN_HCA)
    pace = compute_fair_b2_pace_v1(incumbent, hca=FROZEN_HCA)
    neut = compute_fair_b2_pace_neutral_v1(pace)
    assert neut[FAIR_COL][0] == pytest.approx(pace[PACE_FAIR_COL][0])
    assert neut[HCA_COL][0] == pytest.approx(FROZEN_HCA_HOME)
    # Parent columns untouched
    assert neut[PACE_FAIR_COL][0] == pytest.approx(pace[PACE_FAIR_COL][0])


def test_neutral_differs_from_parent_by_exact_hca() -> None:
    games = _base_games(venue_status=VENUE_STATUS_NEUTRAL)
    incumbent = compute_fair_b2(games, hca=FROZEN_HCA)
    pace = compute_fair_b2_pace_v1(incumbent, hca=FROZEN_HCA)
    neut = compute_fair_b2_pace_neutral_v1(pace)
    assert neut[HCA_COL][0] == pytest.approx(0.0)
    assert neut[FAIR_COL][0] == pytest.approx(pace[PACE_FAIR_COL][0] - FROZEN_HCA_HOME)
    # Parent still applied full HCA (immutable under B2-PACE-v1)
    assert pace[PACE_FAIR_COL][0] == pytest.approx(
        pace_scalar(
            adjem_home=30.0,
            adjem_away=10.0,
            adjt_home=67.5,
            adjt_away=67.5,
            hca=FROZEN_HCA,
        )
    )


def test_frozen_candidate_immutability_pins() -> None:
    assert CANDIDATE_ID == "B2-PACE-NEUTRAL-v1"
    assert METHOD_ID == "kenpom_adjem_pit_tempo_gated_hca_v1"
    assert PACE_ID == "B2-PACE-v1"
    assert_parent_immutability_pins()
    # Content hash of parent module must remain the Phase 2.7A math pin when present
    parent = (
        Path(__file__).resolve().parents[1] / "src" / "ncaam_lab" / "fair_b2_pace_v1.py"
    )
    assert parent.exists()
    body = parent.read_bytes()
    # Ensure frozen HCA literal still present (no silent retune of parent)
    assert b"2.8696" in body or b"FROZEN_HCA" in body


def test_deterministic_two_run_output() -> None:
    games = pl.concat(
        [
            _base_games(event_id="a", venue_status=VENUE_STATUS_HOME),
            _base_games(
                event_id="b",
                venue_status=VENUE_STATUS_NEUTRAL,
                adjem_home=12.0,
                adjem_away=18.0,
            ),
        ]
    )
    r1 = compute_fair_b2_pace_neutral_v1(games)
    r2 = compute_fair_b2_pace_neutral_v1(games)
    assert r1[FAIR_COL].to_list() == r2[FAIR_COL].to_list()
    assert r1[HCA_COL].to_list() == r2[HCA_COL].to_list()
    assert r1[ELIGIBLE_COL].to_list() == r2[ELIGIBLE_COL].to_list()


def test_no_holdout_or_test_a_path_access() -> None:
    with pytest.raises(ValueError, match="holdout"):
        assert_no_holdout_or_test_a_paths(
            [Path("data/ops/lab/ncaam/holdout_2024_25/seal/seal_receipt.json")]
        )
    with pytest.raises(ValueError, match="test_a"):
        assert_no_holdout_or_test_a_paths(
            [Path("data/ops/lab/ncaam/ncaam-fair-lab-test_a-latest.parquet")]
        )
    with pytest.raises(ValueError, match="2024_25"):
        assert_no_holdout_or_test_a_paths(
            [
                Path(
                    "services/model-service/src/services/ncaam_schedule/data/"
                    "ncaam_official_schedule_2024_25.json"
                )
            ]
        )


def test_materialize_still_incumbent_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutral challenger must not become materialize default."""
    # Smoke: import path still exposes incumbent materialize; challenger not wired.
    import inspect
    from ncaam_lab import materialize as mat

    src = inspect.getsource(mat.materialize_lab_fair)
    assert "compute_fair_b2_pace_neutral_v1" not in src
    assert "B2-PACE-NEUTRAL" not in src


def test_requires_venue_status_column() -> None:
    games = _base_games().drop("venue_status")
    with pytest.raises(ValueError, match="venue_status"):
        compute_fair_b2_pace_neutral_v1(games)
