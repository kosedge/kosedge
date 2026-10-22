"""Synthetic-only tests for NFL eval-prep (IMV t4175u / PR #610 C-6..C-8). No real seasons."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.nfl_eval_prep.asof import (
    ASOF_IS_SELF_DECLARED,
    AsOfProof,
    proofs_from_feature_row,
    validate_asof_proofs,
)
from src.services.nfl_eval_prep.harness import build_rebuild_plan
from src.services.nfl_eval_prep.leaks import (
    L1_FIXED_JOIN,
    L1_LEAKY_JOIN,
    L2_FIXED_WEEK_CAP,
    L2_LEAKY_WEEK_CAP,
    apply_strict_week_join,
    flag_l3_defaults,
    leak_fix_diff,
    require_week_cap,
)
from src.services.nfl_eval_prep.local_path import LocalPathError, write_local_input_path
from src.services.nfl_eval_prep.local_tree_check import (
    LOCAL_TREE_CHECKED,
    LocalTreeCheckError,
    check_local_tree,
)
from src.services.nfl_eval_prep.splits import (
    SplitError,
    assert_season_in_rebuild_universe,
    assert_train_only,
    build_expanding_window_folds,
)
from src.services.nfl_eval_prep.synthetic import write_synthetic_bundle


REPO = Path(__file__).resolve().parents[3]


def test_asof_keeps_strictly_before_kickoff() -> None:
    kept = AsOfProof(
        game_id="SYN-1",
        feature_name="home_off_epa_5g",
        as_of="2018-09-13T12:00:00+00:00",
        kickoff_utc="2018-09-13T17:00:00+00:00",
        source="archive:synthetic",
    )
    late = AsOfProof(
        game_id="SYN-1",
        feature_name="home_kav_net_5g",
        as_of="2018-09-13T17:00:00+00:00",
        kickoff_utc="2018-09-13T17:00:00+00:00",
        source="archive:synthetic",
    )
    missing = AsOfProof(
        game_id="SYN-2",
        feature_name="rest_days_home",
        as_of="",
        kickoff_utc="2018-09-13T17:00:00+00:00",
        source="archive:synthetic",
    )
    unnamed = AsOfProof(
        game_id="SYN-3",
        feature_name="home_off_epa_5g",
        as_of="2018-09-13T12:00:00+00:00",
        kickoff_utc="2018-09-13T17:00:00+00:00",
        source="synthetic",
    )
    result = validate_asof_proofs([kept, late, missing, unnamed])
    assert result.kept_n == 1
    assert [v.reason for v in result.excluded] == [
        "as_of_not_before_cutoff",
        "unprovable_as_of",
        "source_not_named_archive",
    ]
    assert ASOF_IS_SELF_DECLARED is True
    assert kept.asof_self_declared is True


def test_asof_refuses_close_or_score_feature_name() -> None:
    result = validate_asof_proofs(
        [
            AsOfProof(
                game_id="SYN-1",
                feature_name="spread_line",
                as_of="2018-09-13T12:00:00+00:00",
                kickoff_utc="2018-09-13T17:00:00+00:00",
                source="archive:synthetic",
            )
        ]
    )
    assert result.kept_n == 0
    assert result.excluded[0].reason == "close_or_score_column_refused_as_feature"


def test_proofs_from_feature_row_refuses_whole_row_as_of() -> None:
    with pytest.raises(ValueError, match="whole-row as-of"):
        proofs_from_feature_row(
            {"game_id": "SYN-1", "home_off_epa_5g": 0.1, "as_of": "2018-09-13T12:00:00+00:00"},
            feature_names=("home_off_epa_5g",),
            kickoff_utc="2018-09-13T17:00:00+00:00",
            allow_row_as_of=True,
        )
    proofs = proofs_from_feature_row(
        {
            "game_id": "SYN-1",
            "home_off_epa_5g": 0.1,
            "as_of": "2018-09-13T12:00:00+00:00",
            "source": "archive:synthetic",
        },
        feature_names=("home_off_epa_5g",),
        kickoff_utc="2018-09-13T17:00:00+00:00",
    )
    assert proofs[0].as_of == ""


def test_l1_rejects_same_week_join() -> None:
    assert apply_strict_week_join(game_week=5, feature_week=4) is True
    assert apply_strict_week_join(game_week=5, feature_week=5) is False
    assert apply_strict_week_join(game_week=5, feature_week=None) is False


def test_l2_refuses_uncapped_and_same_week_cap() -> None:
    with pytest.raises(ValueError, match="week_cap is required"):
        require_week_cap(None, game_week=8)
    with pytest.raises(ValueError, match="must be < game_week"):
        require_week_cap(8, game_week=8)
    assert require_week_cap(7, game_week=8) == 7


def test_l3_flags_unmarked_defaults() -> None:
    flags = flag_l3_defaults(
        {
            "rest_days_home": 7.0,
            "rest_days_away": 7.0,
            "home_injury_impact": 0.0,
            "away_injury_impact": 0.0,
        },
        game_id="SYN-L3",
    )
    assert {f.field for f in flags} >= {
        "rest_days_home",
        "home_injury_impact",
    }
    observed = flag_l3_defaults(
        {
            "rest_days_home": 7.0,
            "rest_days_away": 6.0,
            "home_injury_impact": 0.0,
            "away_injury_impact": 0.2,
            "rest_observed": True,
            "injury_observed": True,
        },
        game_id="SYN-L3-ok",
    )
    assert observed == []


def test_leak_diff_names_production_sites() -> None:
    diff = leak_fix_diff()
    assert "h.week = s.week" in diff["L-1"]["leaky_join"]
    assert "h.week < s.week" in diff["L-1"]["fixed_join"]
    assert "IS NULL" in diff["L-2"]["leaky_predicate"]
    assert "IS NULL" not in diff["L-2"]["fixed_predicate"]
    assert diff["production_rewritten"] is False
    ingest = (
        REPO
        / "services"
        / "model-service"
        / "data_platform_nfl"
        / "ingest.py"
    ).read_text(encoding="utf-8")
    assert "h.week = s.week" in ingest
    tasks = (REPO / "services" / "model-service" / "src" / "tasks.py").read_text(
        encoding="utf-8"
    )
    assert L2_LEAKY_WEEK_CAP in tasks
    assert L1_LEAKY_JOIN.splitlines()[0] in ingest or "h.week = s.week" in ingest
    assert L1_FIXED_JOIN != L1_LEAKY_JOIN
    assert L2_FIXED_WEEK_CAP != L2_LEAKY_WEEK_CAP


def test_expanding_window_is_train_only_by_season() -> None:
    folds = build_expanding_window_folds([2016, 2017, 2018])
    assert [f.eval_season for f in folds] == [2017, 2018]
    assert folds[0].train_seasons == (2016,)
    assert folds[1].train_seasons == (2016, 2017)
    assert_train_only((2016, 2017), 2018)
    with pytest.raises(SplitError, match="CONTAMINATED"):
        assert_train_only((2013, 2023), 2024)
    with pytest.raises(SplitError, match="plumbing"):
        assert_train_only((2013,), 2026, week=4)
    with pytest.raises(SplitError, match="blocked seasons"):
        build_expanding_window_folds([2013, 2024])
    with pytest.raises(SplitError, match="C-7"):
        build_expanding_window_folds([2012, 2013, 2014])


def test_c7_refuses_pre2013_without_ryan_filed_list() -> None:
    with pytest.raises(SplitError, match="C-7"):
        assert_season_in_rebuild_universe(2012, ryan_filed_pre2013=frozenset())
    assert_season_in_rebuild_universe(2012, ryan_filed_pre2013=frozenset({2012}))
    assert_season_in_rebuild_universe(2013)


def test_rebuild_plan_does_not_include_eval_seasons() -> None:
    plan = build_rebuild_plan()
    payload = plan.to_dict()
    assert payload["will_execute_eval"] is False
    assert payload["criteria"]["not_criteria"] == "c57032db"
    assert 2024 not in payload["diagnostic_seasons"]
    assert 2025 not in payload["diagnostic_seasons"]
    assert payload["folds"][-1]["eval_season"] == 2023
    assert max(payload["folds"][-1]["train_seasons"]) == 2022
    assert "local_tree_check" in payload["runner"]
    assert "runner_v2" not in payload["runner"]


def test_local_tree_check_validates_synthetic_bundle(tmp_path: Path) -> None:
    root = write_synthetic_bundle(tmp_path / "bundle")
    out = check_local_tree(str(root))
    assert out.status == LOCAL_TREE_CHECKED
    assert out.status != "PREP_VALIDATED"
    assert out.to_dict()["gate"] is False
    assert out.to_dict()["asof_self_declared"] is True
    assert out.games_kept == 6  # weeks 2–3 × 3 seasons
    assert out.games_seen == 6
    assert [f["eval_season"] for f in out.folds] == [2017, 2018]
    assert out.to_dict()["simulated"] is False
    assert out.to_dict()["certified"] is False


def test_local_tree_check_excludes_same_week_and_late_asof(tmp_path: Path) -> None:
    write_local_input_path(
        tmp_path,
        manifest={"kind": "synthetic"},
        schedule_rows=[
            {
                "game_id": "SYN-2018-W03-AAA-BBB",
                "season": 2018,
                "week": 3,
                "kickoff_utc": "2018-09-15T17:00:00+00:00",
            }
        ],
        feature_rows=[
            {
                "game_id": "SYN-2018-W03-AAA-BBB",
                "feature_week": 3,
                "source": "archive:synthetic",
                "home_off_epa_5g": 0.1,
                "home_off_epa_5g_as_of": "2018-09-15T16:00:00+00:00",
            }
        ],
    )
    out = check_local_tree(str(tmp_path), build_folds=False)
    assert out.games_kept == 0
    assert out.excluded[0]["reason"] == "L-1_same_week_or_missing_feature_week"


def test_local_tree_check_refuses_whole_row_as_of(tmp_path: Path) -> None:
    write_local_input_path(
        tmp_path,
        manifest={"kind": "synthetic"},
        schedule_rows=[
            {
                "game_id": "SYN-2018-W03-AAA-BBB",
                "season": 2018,
                "week": 3,
                "kickoff_utc": "2018-09-15T17:00:00+00:00",
            }
        ],
        feature_rows=[
            {
                "game_id": "SYN-2018-W03-AAA-BBB",
                "feature_week": 2,
                "as_of": "2018-09-15T16:00:00+00:00",
                "source": "archive:synthetic",
                "home_off_epa_5g": 0.1,
            }
        ],
    )
    out = check_local_tree(str(tmp_path), build_folds=False)
    assert out.games_kept == 0
    assert out.excluded[0]["reason"] == "whole_row_as_of_refused"


def test_local_tree_check_refuses_close_column(tmp_path: Path) -> None:
    with pytest.raises(LocalPathError, match="close/score"):
        write_local_input_path(
            tmp_path,
            manifest={"kind": "synthetic"},
            schedule_rows=[
                {
                    "game_id": "SYN-2018-W03-AAA-BBB",
                    "season": 2018,
                    "week": 3,
                    "kickoff_utc": "2018-09-15T17:00:00+00:00",
                }
            ],
            feature_rows=[
                {
                    "game_id": "SYN-2018-W03-AAA-BBB",
                    "feature_week": 2,
                    "source": "archive:synthetic",
                    "home_off_epa_5g": 0.1,
                    "home_off_epa_5g_as_of": "2018-09-15T16:00:00+00:00",
                    "spread_line": -3.5,
                }
            ],
        )


def test_local_tree_check_refuses_pre2013_without_ryan_list(tmp_path: Path) -> None:
    write_local_input_path(
        tmp_path,
        manifest={"kind": "synthetic"},
        schedule_rows=[
            {
                "game_id": "SYN-2012-W03-AAA-BBB",
                "season": 2012,
                "week": 3,
                "kickoff_utc": "2012-09-16T17:00:00+00:00",
            }
        ],
        feature_rows=[],
    )
    with pytest.raises(LocalTreeCheckError, match="C-7"):
        check_local_tree(str(tmp_path), ryan_filed_pre2013=frozenset())


def test_local_tree_check_refuses_contaminated_season(tmp_path: Path) -> None:
    write_local_input_path(
        tmp_path,
        manifest={"kind": "synthetic"},
        schedule_rows=[
            {
                "game_id": "SYN-2024-W01-AAA-BBB",
                "season": 2024,
                "week": 1,
                "kickoff_utc": "2024-09-08T17:00:00+00:00",
            }
        ],
        feature_rows=[],
    )
    with pytest.raises(LocalTreeCheckError, match="contaminated"):
        check_local_tree(str(tmp_path))


def test_local_tree_check_refuses_w4_w6_plumbing_week(tmp_path: Path) -> None:
    write_local_input_path(
        tmp_path,
        manifest={"kind": "synthetic"},
        schedule_rows=[
            {
                "game_id": "SYN-2026-W04-AAA-BBB",
                "season": 2026,
                "week": 4,
                "kickoff_utc": "2026-09-27T17:00:00+00:00",
            }
        ],
        feature_rows=[],
    )
    with pytest.raises(LocalTreeCheckError, match="plumbing"):
        check_local_tree(str(tmp_path))


def test_local_path_refuses_grading_tree(tmp_path: Path) -> None:
    write_local_input_path(
        tmp_path,
        manifest={"kind": "synthetic"},
        feature_rows=[],
        schedule_rows=[],
    )
    (tmp_path / "grading").mkdir()
    (tmp_path / "grading" / "finals.jsonl").write_text("{}\n", encoding="utf-8")
    with pytest.raises(LocalTreeCheckError, match="LC-6"):
        check_local_tree(str(tmp_path))


def test_local_tree_check_refuses_database_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_synthetic_bundle(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql://example.invalid/none")
    with pytest.raises(LocalTreeCheckError, match="DATABASE_URL"):
        check_local_tree(str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)


def test_sha256sums_written_last(tmp_path: Path) -> None:
    root = write_synthetic_bundle(tmp_path)
    sums = (root / "SHA256SUMS").read_text(encoding="utf-8").strip().splitlines()
    assert len(sums) == 3
    names = {line.split("  ", 1)[1] for line in sums}
    assert names == {"manifest.json", "features/rows.jsonl", "schedule/games.jsonl"}
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert "database_url" not in manifest
