"""NCAAM Lab results densify — join honesty + B7 fail-closed."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import polars as pl
import pytest

WEB_ROOT = Path(__file__).resolve().parent.parent
SRC = WEB_ROOT / "src"
for p in (str(WEB_ROOT), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from ncaam_lab.results_attach import (
    attach_lab_outcomes,
    coverage_vs_event_id_only,
    load_schedule_pack_results,
)
from ncaam_lab.scorecard import attach_outcomes, build_scorecard


def _lab_rows() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "event_id": ["e1", "e2", "e3", "e4"],
            "tip_date": [
                date(2023, 12, 10),
                date(2023, 12, 11),
                date(2024, 1, 10),
                date(2024, 1, 11),
            ],
            "home_team_id": ["nevada", "purdue", "duke", "miami fl"],
            "away_team_id": ["air force", "duke", "unc", "miami oh"],
            "home_team": ["Nevada", "Purdue", "Duke", "Miami Hurricanes"],
            "away_team": ["Air Force", "Duke", "UNC", "Miami (OH)"],
            "fair_spread_home": [10.0, -3.0, 5.0, 12.0],
            "b1_consensus_close_spread": [-9.0, 2.5, -4.0, -11.0],
            "open_snapshot_honest": [True, True, True, True],
            "open_consensus_spread": [-8.5, 2.0, -3.5, -10.5],
            "continuity_state": ["PRIOR", "PRIOR", "PRIOR", "PRIOR"],
        }
    )


def _pack_df(rows: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(rows).with_columns(
        [
            pl.col("tip_date").cast(pl.Date),
            pl.col("actual_margin").cast(pl.Float64),
        ]
    )


def test_pack_join_attaches_margin_on_tip_and_b7_ids(tmp_path: Path) -> None:
    lab = _lab_rows()
    pack = _pack_df(
        [
            {
                "tip_date": date(2023, 12, 10),
                "home_team_id": "nevada",
                "away_team_id": "air force",
                "actual_margin": 13.0,
                "espn_game_id": "g1",
                "source_pack": "test.json",
            },
            {
                "tip_date": date(2023, 12, 11),
                "home_team_id": "purdue",
                "away_team_id": "duke",
                "actual_margin": -5.0,
                "espn_game_id": "g2",
                "source_pack": "test.json",
            },
        ]
    )
    out, receipt = attach_lab_outcomes(
        lab,
        pack_results=pack,
        event_actuals=pl.DataFrame(
            {"event_id": pl.Series([], dtype=pl.Utf8), "actual_margin": pl.Series([], dtype=pl.Float64)}
        ),
    )
    assert receipt["n_with_actual"] == 2
    assert abs(receipt["outcome_coverage"] - 0.5) < 1e-9
    by_id = {r["event_id"]: r["actual_margin"] for r in out.iter_rows(named=True)}
    assert by_id["e1"] == 13.0
    assert by_id["e2"] == -5.0
    assert by_id["e3"] is None
    assert by_id["e4"] is None


def test_missing_b7_on_pack_row_never_attaches(tmp_path: Path) -> None:
    """Unresolved / null B7 identity on results side → omit (fail-closed)."""
    pack_path = tmp_path / "pack.json"
    pack_path.write_text(
        json.dumps(
            {
                "games": [
                    {
                        "tipoff": "2023-12-10T03:00Z",
                        "date": "2023-12-10",
                        "home": None,  # unresolved B7
                        "away": "air force",
                        "home_score": 80,
                        "away_score": 67,
                        "espn_game_id": "bad1",
                    },
                    {
                        "tipoff": "2023-12-10T03:00Z",
                        "date": "2023-12-10",
                        "home": "nevada",
                        "away": "air force",
                        "home_score": 80,
                        "away_score": 67,
                        "espn_game_id": "ok1",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    pack, receipt = load_schedule_pack_results([pack_path])
    assert receipt["n_omitted_missing_b7"] == 1
    assert receipt["n_unique_keys"] == 1
    assert pack.height == 1
    assert pack["home_team_id"].to_list() == ["nevada"]


def test_ambiguous_pack_key_omits_all_copies() -> None:
    pack = _pack_df(
        [
            {
                "tip_date": date(2023, 12, 10),
                "home_team_id": "nevada",
                "away_team_id": "air force",
                "actual_margin": 13.0,
                "espn_game_id": "g1",
                "source_pack": "a.json",
            },
            {
                "tip_date": date(2023, 12, 10),
                "home_team_id": "nevada",
                "away_team_id": "air force",
                "actual_margin": 99.0,  # conflicting — must omit, not invent/pick
                "espn_game_id": "g1b",
                "source_pack": "b.json",
            },
        ]
    )
    counts = pack.group_by(["tip_date", "home_team_id", "away_team_id"]).len()
    amb = counts.filter(pl.col("len") > 1).select(["tip_date", "home_team_id", "away_team_id"])
    clean = pack.join(amb, on=["tip_date", "home_team_id", "away_team_id"], how="anti")
    assert clean.height == 0

    lab = _lab_rows()
    out, receipt = attach_lab_outcomes(
        lab,
        pack_results=clean,
        event_actuals=pl.DataFrame(
            {"event_id": pl.Series([], dtype=pl.Utf8), "actual_margin": pl.Series([], dtype=pl.Float64)}
        ),
    )
    assert receipt["n_with_actual"] == 0
    assert out.filter(pl.col("event_id") == "e1")["actual_margin"].to_list() == [None]


def test_load_pack_drops_ambiguous_keys(tmp_path: Path) -> None:
    pack_path = tmp_path / "amb.json"
    pack_path.write_text(
        json.dumps(
            {
                "games": [
                    {
                        "tipoff": "2023-12-10T03:00Z",
                        "home": "nevada",
                        "away": "air force",
                        "home_score": 80,
                        "away_score": 67,
                        "espn_game_id": "a",
                    },
                    {
                        "tipoff": "2023-12-10T03:00Z",
                        "home": "nevada",
                        "away": "air force",
                        "home_score": 70,
                        "away_score": 60,
                        "espn_game_id": "b",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    pack, receipt = load_schedule_pack_results([pack_path])
    assert receipt["n_omitted_ambiguous_key"] == 1
    assert pack.height == 0


def test_never_invent_margin_without_join() -> None:
    lab = _lab_rows()
    empty_pack = pl.DataFrame(
        {
            "tip_date": pl.Series([], dtype=pl.Date),
            "home_team_id": pl.Series([], dtype=pl.Utf8),
            "away_team_id": pl.Series([], dtype=pl.Utf8),
            "actual_margin": pl.Series([], dtype=pl.Float64),
            "espn_game_id": pl.Series([], dtype=pl.Utf8),
            "source_pack": pl.Series([], dtype=pl.Utf8),
        }
    )
    out, receipt = attach_lab_outcomes(
        lab,
        pack_results=empty_pack,
        event_actuals=pl.DataFrame(
            {"event_id": pl.Series([], dtype=pl.Utf8), "actual_margin": pl.Series([], dtype=pl.Float64)}
        ),
    )
    assert receipt["n_with_actual"] == 0
    assert out["actual_margin"].null_count() == len(out)


def test_event_id_fill_only_when_pack_misses() -> None:
    lab = _lab_rows()
    pack = _pack_df(
        [
            {
                "tip_date": date(2023, 12, 10),
                "home_team_id": "nevada",
                "away_team_id": "air force",
                "actual_margin": 13.0,
                "espn_game_id": "g1",
                "source_pack": "test.json",
            },
        ]
    )
    event_actuals = pl.DataFrame(
        {
            "event_id": ["e1", "e3"],
            "actual_margin": [999.0, 7.0],  # e1 already has pack — pack wins
        }
    )
    out, receipt = attach_lab_outcomes(lab, pack_results=pack, event_actuals=event_actuals)
    by_id = {r["event_id"]: r["actual_margin"] for r in out.iter_rows(named=True)}
    assert by_id["e1"] == 13.0  # pack preferred; no invent/override to 999
    assert by_id["e3"] == 7.0
    assert receipt["n_with_actual_pack"] == 1
    assert receipt["n_with_actual_event_id_fill"] == 1
    assert receipt["n_with_actual"] == 2


def test_miami_fl_oh_do_not_cross_join() -> None:
    """Miami FL home ≠ Miami OH; wrong-side pack must not attach."""
    lab = _lab_rows()
    # Wrong: miami oh hosting miami fl on e4's tip — different ids than lab e4
    pack = _pack_df(
        [
            {
                "tip_date": date(2024, 1, 11),
                "home_team_id": "miami oh",
                "away_team_id": "miami fl",
                "actual_margin": 3.0,
                "espn_game_id": "wrong",
                "source_pack": "test.json",
            },
        ]
    )
    out, receipt = attach_lab_outcomes(
        lab,
        pack_results=pack,
        event_actuals=pl.DataFrame(
            {"event_id": pl.Series([], dtype=pl.Utf8), "actual_margin": pl.Series([], dtype=pl.Float64)}
        ),
    )
    assert out.filter(pl.col("event_id") == "e4")["actual_margin"].to_list() == [None]
    assert receipt["n_with_actual"] == 0


def test_scorecard_attach_outcomes_densify_flag() -> None:
    lab = _lab_rows().select(
        ["event_id", "tip_date", "home_team_id", "away_team_id"]
    )
    # Thin path with empty actuals → all null
    thin = attach_outcomes(lab, pl.DataFrame({"event_id": [], "actual_margin": []}), densify=False)
    assert thin["actual_margin"].null_count() == len(thin)


def test_coverage_before_helper_event_id_only(tmp_path: Path) -> None:
    lab = _lab_rows()
    am = tmp_path / "actual_margins.parquet"
    pl.DataFrame({"event_id": ["e1"], "actual_margin": [4.0]}).write_parquet(am)
    before = coverage_vs_event_id_only(lab, actuals_path=am)
    assert before["n_with_actual"] == 1
    assert before["method"] == "event_id_actual_margins_only"


@pytest.mark.skipif(
    not (WEB_ROOT.parent.parent / "data" / "ops" / "lab" / "ncaam" / "ncaam-fair-lab-test_a-latest.parquet").exists(),
    reason="Lab fair parquet not present",
)
def test_live_lab_densify_lifts_test_a_coverage() -> None:
    """Integration: densify must lift Test-A off the frozen ~13% thin path."""
    out_dir = WEB_ROOT.parent.parent / "data" / "ops" / "lab" / "ncaam"
    lab = pl.read_parquet(out_dir / "ncaam-fair-lab-test_a-latest.parquet")
    before = coverage_vs_event_id_only(lab)
    densified, after = attach_lab_outcomes(lab)
    assert before["n_with_actual"] == 80  # frozen v1 receipt
    assert after["n_with_actual"] >= 500  # Lab-honest densify target
    assert after["outcome_coverage"] > 0.85
    assert densified.filter(pl.col("actual_margin").is_not_null()).height == after["n_with_actual"]
    # No SETTLED invent
    if "continuity_state" in densified.columns:
        assert "SETTLED" not in set(densified["continuity_state"].drop_nulls().unique().to_list())


@pytest.mark.skipif(
    not (WEB_ROOT.parent.parent / "data" / "ops" / "lab" / "ncaam" / "ncaam-fair-lab-test_a-latest.parquet").exists(),
    reason="Lab fair parquet not present",
)
def test_build_scorecard_no_densify_preserves_thin_n() -> None:
    card = build_scorecard(densify_results=False)
    pred = (card.get("cuts") or {}).get("test_a", {}).get("predictive") or {}
    assert pred.get("n_with_actual") == 80
    assert abs(float(pred.get("outcome_coverage") or 0) - 0.1314) < 1e-3
