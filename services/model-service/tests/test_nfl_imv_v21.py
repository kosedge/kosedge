"""fd97f103 — IMV v2.1 contracts. Synthetic only. Does not run the builder or W7."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HELPER = ROOT / "scripts" / "nfl" / "imv" / "nfl_imv_v21.py"


def _load():
    spec = importlib.util.spec_from_file_location("nfl_imv_v21", HELPER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_c6_week_slice_is_wxx_not_gid_8_10() -> None:
    v = _load()
    gid = "2026-W04-ARI@NYG"
    assert v.parse_product_week(gid) == 4
    assert v.legacy_week_slice_value(gid) == "-A"
    with pytest.raises(ValueError):
        int(v.legacy_week_slice_value(gid))
    assert v.parse_product_week("2026-W08-CAR@GB") == 8


def test_c2_prior_weeks_only_records_as_of_and_flags_current_week() -> None:
    v = _load()
    gid = "2026-W06-SEA@DEN"
    ok = v.record_as_of_check(
        game_id=gid,
        game_week=6,
        source_weeks=["2026-W02", "2026-W03", "2026-W04", "2026-W05"],
        kickoff_utc="2026-10-19T20:25:00Z",
        feature_as_of_week=5,
    )
    assert ok.status == "PASS"
    assert ok.prior_weeks_only is True
    assert ok.as_of_week == 5
    assert "FLAG_SAME_WEEK_LEAK" not in ok.flags

    leak = v.record_as_of_check(
        game_id=gid,
        game_week=6,
        source_weeks=v.prod_leak_source_weeks(6),  # includes week 6
        kickoff_utc="2026-10-19T20:25:00Z",
        feature_as_of_week=6,
    )
    assert leak.status == "BLOCKED"
    assert "FLAG_SAME_WEEK_LEAK" in leak.flags
    assert "BLOCKED_SAME_WEEK_LEAK" in leak.flags
    assert v.PROD_LEAK_WINDOW_SQL == "ROWS BETWEEN 4 PRECEDING AND CURRENT ROW"
    assert v.LAGGED_WINDOW_SQL == "ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING"
    assert 6 in v.prod_leak_source_weeks(6)
    assert 6 not in v.lagged_source_weeks(6)


def test_c2_2025_tail_is_not_a_future_leak() -> None:
    v = _load()
    rec = v.record_as_of_check(
        game_id="2026-W04-NE@BUF",
        game_week=4,
        source_weeks=["2025-W16", "2025-W17", "2025-W18", "2026-W02", "2026-W03"],
        kickoff_utc="2026-09-27T17:00:00Z",
        feature_as_of_week=3,
    )
    assert rec.status == "PASS"
    assert rec.prior_weeks_only is True


def test_c5_missing_kickoff_blocked_no_fallback() -> None:
    v = _load()
    miss = v.require_kickoff(None, game_id="2026-W08-CAR@GB")
    assert miss["ok"] is False
    assert miss["flag"] == "BLOCKED_MISSING_KICKOFF"
    assert miss["fallback_used"] is False
    rec = v.record_as_of_check(
        game_id="2026-W08-CAR@GB",
        game_week=8,
        source_weeks=["2026-W07"],
        kickoff_utc=None,
        feature_as_of_week=7,
    )
    assert rec.status == "BLOCKED"
    assert "BLOCKED_MISSING_KICKOFF" in rec.flags


def test_c4_injury_null_flagged_no_explicit_zero_no_raw_map() -> None:
    v = _load()
    empty = v.injury_allowed_flagged({})
    assert empty["home_injury_impact"] is None
    assert empty["away_injury_impact"] is None
    assert empty["diff_injury_impact"] is None
    assert empty["explicit_zero_removed"] is True
    assert empty["injury_source"] == "none_not_injuries_2026"
    assert "FLAG_MISSING_KOSEDGE_INJURY_NOWCAST" in empty["flags"]
    assert empty["pass_to_sim"] == {
        "injury_nowcast_impact_home": None,
        "injury_nowcast_impact_away": None,
    }

    zero = v.injury_allowed_flagged(
        {"home_injury_impact": 0.0, "injury_source": "explicit_zero"}
    )
    assert zero["home_injury_impact"] is None
    assert "FLAG_EXPLICIT_ZERO_INJURY_REMOVED" in zero["flags"]
    assert "FLAG_IMPUTED_INJURY_DEFAULT" in zero["flags"]

    raw = v.injury_allowed_flagged(
        {"mapped_from_injuries_2026": True, "home_injury_impact": 1.2, "injury_source": "injuries_2026"}
    )
    assert raw["home_injury_impact"] is None
    assert "FLAG_RAW_INJURIES_2026_REFUSED" in raw["flags"]
    assert "FLAG_IMPUTED_INJURY_DEFAULT" in raw["flags"]


def test_c1_feature_store_sha_blocks_mismatch(tmp_path: Path) -> None:
    v = _load()
    store = tmp_path / "store"
    store.mkdir()
    (store / "features.jsonl").write_text('{"game_id_product":"2026-W06-SEA@DEN"}\n', encoding="utf-8")
    (store / "feature-flags.jsonl").write_text('{"flag":"FLAG_MISSING_EPA"}\n', encoding="utf-8")
    pin = v.write_feature_store_pin(store)
    assert v.assert_feature_store_pin(store, pin["feature_store_sha256"])["status"] == "OK"
    assert v.assert_feature_store_pin(store, None)["status"] == "OK"  # file pin present
    bad = v.assert_feature_store_pin(store, "0" * 64)
    assert bad["status"] == "BLOCKED"
    assert bad["reason"] == "FEATURE_STORE_SHA_MISMATCH"
    empty = tmp_path / "empty"
    empty.mkdir()
    unpinned = v.assert_feature_store_pin(empty, None)
    assert unpinned["status"] == "BLOCKED"
    assert unpinned["reason"] == "FEATURE_STORE_SHA_UNPINNED"


def test_c3_week_cap_and_parity_flags_prod_current_row() -> None:
    v = _load()
    local = [
        {
            "game_id_product": "2026-W05-CHI@GB",
            "week": 5,
            "as_of_week": 4,
            "source_weeks": ["2026-W03", "2026-W04"],
            "home_off_epa_5g": 0.11,
            "away_off_epa_5g": -0.02,
        },
        {
            "game_id_product": "2026-W07-NE@CHI",
            "week": 7,
            "as_of_week": 6,
            "source_weeks": ["2026-W05", "2026-W06"],
            "home_off_epa_5g": 0.20,
            "away_off_epa_5g": 0.01,
        },
    ]
    prod = [
        {
            "game_id_product": "2026-W05-CHI@GB",
            "week": 5,
            "as_of_week": 5,  # CURRENT ROW
            "source_weeks": [3, 4, 5],
            "home_off_epa_5g": 0.15,
            "away_off_epa_5g": -0.02,
        },
        {
            "game_id_product": "2026-W07-NE@CHI",
            "week": 7,
            "as_of_week": 7,
            "home_off_epa_5g": 0.20,
            "away_off_epa_5g": 0.01,
        },
    ]
    capped = v.apply_week_cap(local, 6)
    assert [r["game_id_product"] for r in capped] == ["2026-W05-CHI@GB"]
    report = v.parity_vs_prod(local, prod, week_cap=6)
    assert report["week_cap"] == 6
    assert report["n_local"] == 1
    assert "2026-W05-CHI@GB" in report["prod_same_week_leak"]
    assert report["local_same_week_leak"] == []
    assert report["status"] == "PASS"
    assert any(d.get("key") == "home_off_epa_5g" for d in report["diffs"])


def test_c6_model_execution_label() -> None:
    v = _load()
    assert v.model_execution_label(executed=False) == "BLOCKED_NO_MODEL_EXECUTION"
    assert v.model_execution_label(executed=True) == "BASE_SIMULATE_NFL_GAME"


def test_c7_hfa_from_this_tree_is_1_05() -> None:
    v = _load()
    rec = v.read_and_assert_hfa(ROOT)
    assert rec["ok"] is True
    assert rec["hfa_points"] == 1.05
    assert rec["hfa_source"] == "BASE:nfl_season_engine.calibration.HOME_FIELD_POINTS"


def test_c8_runner_source_sets_env_and_seals_eperm() -> None:
    text = (ROOT / "scripts" / "nfl" / "imv" / "nfl-imv-sealed-v2.1.sh").read_text(encoding="utf-8")
    assert "export PYTHONDONTWRITEBYTECODE=1" in text
    assert "export GIT_OPTIONAL_LOCKS=0" in text
    assert "EPERM_PROBE.json" in text
    assert text.index("mkdir -p \"${FIXED_OUT}\"") < text.index("EPERM_PROBE.json")
    assert 'int(gid[8:10])' not in text
    assert 'feat.get("injury_source") != "explicit_zero"' not in text


def test_c3_builder_synthetic_prior_weeks_and_injury_null(tmp_path: Path) -> None:
    v = _load()
    games = tmp_path / "games.csv"
    games.write_text(
        "season,week,game_type,home_team,away_team,game_id,home_rest,away_rest,roof,surface,div_game,home_score,away_score\n"
        "2026,6,REG,DEN,SEA,2026_06_DEN_SEA,7,7,outdoors,grass,0,24,17\n",
        encoding="utf-8",
    )
    pbp = tmp_path / "pbp.csv"
    # Weeks 2-5 only (cap 5). Week 6 plays must not enter W6 features.
    lines = [
        "season,week,game_id,play_type,posteam,defteam,home_team,away_team,epa,success,pass,rush,down,yardline_100,touchdown,sack,qb_hit\n"
    ]
    for week, epa in ((2, 0.10), (3, 0.20), (4, 0.00), (5, -0.10), (6, 9.99)):
        lines.append(
            f"2026,{week},g{week},pass,SEA,DEN,DEN,SEA,{epa},1,1,0,1,50,0,0,0\n"
        )
        lines.append(
            f"2026,{week},g{week},pass,DEN,SEA,DEN,SEA,{-epa},0,1,0,1,50,0,0,0\n"
        )
    pbp.write_text("".join(lines), encoding="utf-8")
    pack = tmp_path / "pack.json"
    pack.write_text(
        '{"games":[{"game_id":"2026-W06-SEA@DEN","kickoff_utc":"2026-10-19T20:25:00Z","week":6}]}',
        encoding="utf-8",
    )
    out = tmp_path / "store"
    report = v.build_feature_store(
        base=ROOT,
        games_csv=games,
        pbp_paths=[pbp],
        out_dir=out,
        game_week_cap=6,
        pbp_week_cap=5,
        pack_path=pack,
    )
    assert report["game_week_cap"] == 6
    assert report["pbp_week_cap"] == 5
    row = __import__("json").loads((out / "features.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["week"] == 6
    assert row["as_of_week"] == 5
    assert row["home_injury_impact"] is None
    assert 6 not in [int(str(w).split("W")[-1]) for w in row["source_weeks"] if str(w).startswith("2026-")]
    # week-6 epa 9.99 must not be in the SEA offense mean
    assert row["away_off_epa_5g"] is not None
    assert row["away_off_epa_5g"] != 9.99
    assert abs(row["away_off_epa_5g"] - (0.10 + 0.20 + 0.00 - 0.10) / 4) < 1e-9
    pin = (out / "FEATURE_STORE.sha256").read_text(encoding="utf-8").strip()
    assert len(pin) == 64
    assert all(c in "0123456789abcdef" for c in pin)
    assert v.assert_feature_store_pin(out, pin)["status"] == "OK"
