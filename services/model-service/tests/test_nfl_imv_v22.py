"""f9b25e81 — IMV v2.2 contracts. Synthetic + committed fixtures. Does not run Mac builder/W7."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
IMV = ROOT / "scripts" / "nfl" / "imv"
sys.path.insert(0, str(IMV))

import nfl_imv_v22 as v22  # noqa: E402


def _weekly_team(team: str, weeks_2025, weeks_2026, *, bye_week=None):
    weekly = {}
    for w, epa in weeks_2025:
        weekly[(2025, w, team)] = {
            "off_epa_per_play": epa,
            "def_epa_allowed_per_play": -epa / 2,
            "success_rate_offense": 0.45,
            "success_rate_defense_allowed": 0.43,
            "pass_rate": 0.58,
            "red_zone_td_rate": 0.55,
            "pressure_rate_generated": 0.18,
            "pressure_rate_allowed": 0.16,
            "early_down_pass_rate": 0.52,
            "off_plays": 60,
            "def_plays": 60,
            "n_weeks": 1,
            "game_type": "REG",
        }
    for w, epa in weeks_2026:
        if bye_week is not None and w == bye_week:
            continue
        weekly[(2026, w, team)] = {
            "off_epa_per_play": epa,
            "def_epa_allowed_per_play": -epa / 3,
            "success_rate_offense": 0.46,
            "success_rate_defense_allowed": 0.42,
            "pass_rate": 0.57,
            "red_zone_td_rate": 0.56,
            "pressure_rate_generated": 0.19,
            "pressure_rate_allowed": 0.15,
            "early_down_pass_rate": 0.51,
            "off_plays": 62,
            "def_plays": 61,
            "n_weeks": 1,
            "game_type": "REG",
        }
    return weekly


def test_x1_pin_requires_external_sha_no_file_fallback(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    (store / "features.jsonl").write_text("{}\n", encoding="utf-8")
    (store / "feature-flags.jsonl").write_text("{}\n", encoding="utf-8")
    pin = v22.v21.write_feature_store_pin(store)
    # File pin exists inside the store — v2.2 must still refuse if expected is omitted.
    unpinned = v22.assert_feature_store_pin(store, None)
    assert unpinned["status"] == "BLOCKED"
    assert unpinned["reason"] == "FEATURE_STORE_SHA_UNPINNED_EXTERNAL"
    assert unpinned["fallback_used"] is False
    ok = v22.assert_feature_store_pin(store, pin["feature_store_sha256"])
    assert ok["status"] == "OK"
    assert ok["fallback_used"] is False
    bad = v22.assert_feature_store_pin(store, "ab" * 32)
    assert bad["status"] == "BLOCKED"
    assert bad["reason"] == "FEATURE_STORE_SHA_MISMATCH"


def test_x5_cap_pair_and_w7_refused() -> None:
    assert v22.enforce_cap_pair(6, 5)["ok"] is True
    assert v22.enforce_cap_pair(8, 7)["ok"] is True
    assert v22.enforce_cap_pair(6, 6)["ok"] is False
    assert v22.enforce_cap_pair(6, 6)["flag"] == "CAP_PAIR_MISMATCH"
    assert v22.enforce_cap_pair(7, 6)["ok"] is False
    assert v22.enforce_cap_pair(7, 6)["flag"] == "W7_REFUSED"


def test_x6_five_game_window_skips_bye_and_postseason() -> None:
    weekly = _weekly_team("SEA", [(16, 0.1), (17, 0.1), (18, 0.1)], [(1, 0.2), (2, 0.2), (3, 0.2), (4, 0.2), (5, 0.2), (6, 9.9)], bye_week=4)
    weekly[(2026, 22, "SEA")] = {**weekly[(2026, 5, "SEA")], "off_epa_per_play": 8.8}  # postseason-shaped week
    played = v22.last_n_played_reg(weekly, team="SEA", before_season=2026, before_week=6, n=5)
    assert (2026, 6) not in played
    assert (2026, 4) not in played  # bye
    assert (2026, 22) not in played
    assert played[-1] == (2026, 5)
    # last 5 played REG before W6: 2025-W18 + 2026 W1,W2,W3,W5 (W4 bye)
    assert (2026, 1) in played or (2025, 18) in played
    roll, src = v22.attach_lagged_rolling_played(weekly, season=2026, team="SEA", game_week=6)
    assert 6 not in [int(s.split("W")[-1]) for s in src if s.startswith("2026-")]
    assert roll["off_epa_per_play_5g"] != 9.9


def test_x7_lag_only_and_run_label() -> None:
    assert 6 in v22.v21.prod_leak_source_weeks(6)
    assert 6 not in v22.v21.lagged_source_weeks(6)
    weekly = _weekly_team("DEN", [(18, 0.0)], [(2, 0.1), (3, 0.1), (4, 0.1), (5, 0.1), (6, 0.9)])
    _, src = v22.attach_lagged_rolling_played(weekly, season=2026, team="DEN", game_week=6)
    assert "2026-W06" not in src
    assert v22.run_label(blocked=[], any_null=True, mode="retrospective-w4w6", model_calls_ok=0) == "BLOCKED_NO_MODEL_EXECUTION"
    assert v22.run_label(blocked=[], any_null=False, mode="retrospective-w4w6", model_calls_ok=14) == "RETROSPECTIVE"
    assert v22.run_label(blocked=[], any_null=False, mode="w8-pregame", model_calls_ok=14) == "PROSPECTIVE-RESEARCH"


def test_x4_injury_record_not_hardcoded_false() -> None:
    empty = v22.injury_row_record({})
    assert empty["recorded"] is True
    assert empty["defaulted_injury"] is False
    assert empty["missing_nowcast"] is True
    imputed = v22.injury_row_record({"home_injury_impact": 0.0, "injury_source": "explicit_zero"})
    assert imputed["defaulted_injury"] is True
    assert imputed["home_injury_impact"] is None


def test_x2_section_53_rebuild_non_null_lag_only() -> None:
    weekly = {}
    weekly.update(_weekly_team("SEA", [(w, 0.08) for w in range(1, 19)], [(w, 0.05) for w in range(1, 6)]))
    rec = v22.rebuild_strength_indices(
        base=ROOT,
        weekly=weekly,
        team="SEA",
        game_week=6,
    )
    assert rec["ok"] is True
    assert rec["offense_index"] is not None
    assert rec["defense_index"] is not None
    assert rec["prior_source"] == "pbp_rolling_backbone"
    assert rec["as_of_week"] == 5
    assert rec["offense_index"] != 1.0 or rec["w_current"] is not None
    missing = v22.rebuild_strength_indices(
        base=ROOT,
        weekly={},
        team="ZZZ",
        game_week=6,
    )
    assert missing["ok"] is False
    assert missing["offense_index"] is None
    assert missing["flag"] == "FLAG_MISSING_TRUE_PR_PRIOR"


def test_x3_parity_real_fixture_fails_on_value_mismatch() -> None:
    local = [json.loads(l) for l in (IMV / "fixtures" / "parity-local-w6-sample.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    prod = [json.loads(l) for l in (IMV / "fixtures" / "parity-prod-w6-sample.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    report = v22.parity_vs_prod(local, prod, week_cap=6)
    assert report["n_keys"] >= 12
    assert report["week_cap"] == 6
    assert "2026-W07-NE@CHI" not in [r.get("game_id_product") for r in v22.v21.apply_week_cap(local, 6)]
    assert report["status"] == "FAIL_VALUE_MISMATCH"
    assert report["fails_on_value_mismatch"] is True
    assert report["diffs"]
    assert "2026-W05-CHI@GB" in report["prod_same_week_leak"]
    # Identical local vs local → PASS
    same = v22.parity_vs_prod(local, local, week_cap=6)
    assert same["status"] == "PASS"


def test_x3_too_few_keys_refused() -> None:
    doc = v22.parity_vs_prod(
        [{"game_id_product": "2026-W06-SEA@DEN", "week": 6, "as_of_week": 5, "home_off_epa_5g": 0.1}],
        [{"game_id_product": "2026-W06-SEA@DEN", "week": 6, "as_of_week": 5, "home_off_epa_5g": 0.1}],
        week_cap=6,
        keys=("home_off_epa_5g", "away_off_epa_5g"),
    )
    assert doc["status"] == "FAIL_TOO_FEW_KEYS"


def test_x8_x9_builder_source_gating() -> None:
    text = (IMV / "nfl-imv-feature-build-v2.2.sh").read_text(encoding="utf-8")
    assert "deny network" in text
    assert "EPERM_PROBE.json" in text
    assert 'if [[ -e "${OUT}" ]]' in text
    assert "HELPER.sha256" in text
    assert "sandbox-exec" in text
    runner = (IMV / "nfl-imv-sealed-v2.2.sh").read_text(encoding="utf-8")
    assert "FEATURE_STORE_SHA_UNPINNED_EXTERNAL" in runner
    assert '"defaulted_injury": False' not in runner
    assert "run_label" in runner


def test_x2_builder_writes_indices_not_null(tmp_path: Path) -> None:
    games = tmp_path / "games.csv"
    games.write_text(
        "season,week,game_type,home_team,away_team,game_id,home_rest,away_rest,roof,surface,div_game,home_score,away_score\n"
        "2026,6,REG,DEN,SEA,2026_06_DEN_SEA,10,7,outdoors,grass,0,24,17\n",
        encoding="utf-8",
    )
    pbp = tmp_path / "pbp.csv"
    lines = [
        "season,week,season_type,game_id,play_type,posteam,defteam,home_team,away_team,epa,success,pass,rush,down,yardline_100,touchdown,sack,qb_hit\n"
    ]
    for week, epa in [(16, 0.08), (17, 0.07), (18, 0.06)]:
        lines.append(f"2025,{week},REG,g25{week},pass,SEA,DEN,DEN,SEA,{epa},1,1,0,1,50,0,0,0\n")
        lines.append(f"2025,{week},REG,g25{week},pass,DEN,SEA,DEN,SEA,{-epa},0,1,0,1,50,0,0,0\n")
    for week, epa in [(1, 0.04), (2, 0.05), (3, 0.03), (4, 0.02), (5, 0.01), (6, 9.99)]:
        lines.append(f"2026,{week},REG,g26{week},pass,SEA,DEN,DEN,SEA,{epa},1,1,0,1,50,0,0,0\n")
        lines.append(f"2026,{week},REG,g26{week},pass,DEN,SEA,DEN,SEA,{-epa},0,1,0,1,50,0,0,0\n")
    pbp.write_text("".join(lines), encoding="utf-8")
    pack = tmp_path / "pack.json"
    pack.write_text(
        '{"games":[{"game_id":"2026-W06-SEA@DEN","kickoff_utc":"2026-10-19T20:25:00Z","week":6}]}',
        encoding="utf-8",
    )
    out = tmp_path / "fresh-store"
    report = v22.build_feature_store(
        base=ROOT,
        games_csv=games,
        pbp_paths=[pbp],
        out_dir=out,
        game_week_cap=6,
        pbp_week_cap=5,
        pack_path=pack,
        helper_sha="abc123",
    )
    assert report["caps"]["ok"] is True
    row = json.loads((out / "features.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["offense_index_home"] is not None
    assert row["offense_index_away"] is not None
    assert row["defense_index_home"] is not None
    assert row["prior_source"] == "pbp_rolling_backbone"
    assert row["as_of_week"] == 5
    assert row["defaulted_injury"] is False
    assert "injury_record" in row
    assert 6 not in [int(str(w).split("W")[-1]) for w in row["source_weeks"] if str(w).startswith("2026-")]
    assert (out / "HELPER.sha256").read_text(encoding="utf-8").strip() == "abc123"
    again = v22.build_feature_store(
        base=ROOT,
        games_csv=games,
        pbp_paths=[pbp],
        out_dir=out,
        game_week_cap=6,
        pbp_week_cap=5,
        pack_path=pack,
    )
    assert again["status"] == "BLOCKED"
    assert "OUT_DIR_EXISTS" in again["blocked"]
