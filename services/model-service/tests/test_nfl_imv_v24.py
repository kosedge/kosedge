"""47616a70 — IMV v2.4 contracts. Synthetic only. Does not run Mac builder/W7."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
IMV = ROOT / "scripts" / "nfl" / "imv"
sys.path.insert(0, str(IMV))

import nfl_imv_v22 as v22  # noqa: E402
import nfl_imv_v23 as v23  # noqa: E402
import nfl_imv_v24 as v24  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# TEST-ONLY 41-col SELECT. Not the production v3 list. Production columns
# come only from the pinned file at ops/platform/PR_PROD_PARITY_EXPORT_v3.sql.
TEST_V3_SQL = """SELECT
  season,
  week,
  game_id,
  home_team,
  away_team,
  home_off_epa_5g,
  away_off_epa_5g,
  home_def_epa_allowed_5g,
  away_def_epa_allowed_5g,
  home_pass_rate_5g,
  away_pass_rate_5g,
  home_success_offense_5g,
  away_success_offense_5g,
  home_pressure_allowed_5g,
  away_pressure_allowed_5g,
  home_pressure_generated_5g,
  away_pressure_generated_5g,
  home_early_down_pass_rate_5g,
  away_early_down_pass_rate_5g,
  home_red_zone_td_rate_5g,
  away_red_zone_td_rate_5g,
  home_success_defense_allowed_5g,
  away_success_defense_allowed_5g,
  diff_off_epa_5g,
  home_rest_days,
  away_rest_days,
  home_rest_days_raw,
  away_rest_days_raw,
  roof,
  roof_dome,
  roof_vocab_unknown,
  diff_def_epa_allowed_5g,
  diff_pressure_generated_5g,
  diff_pressure_allowed_5g,
  diff_red_zone_td_rate_5g,
  diff_success_rate_5g,
  diff_rest_days,
  surface_turf,
  is_divisional_game,
  home_kav_net_5g,
  away_kav_net_5g
FROM nfl_dp_matchup_features_weekly
WHERE season = 2026
  AND week BETWEEN 3 AND 7
ORDER BY week, game_id;
"""


def _query() -> str:
    return "SELECT 1 -- in-test only"


def _bind_test_v3(tmp: Path) -> tuple[Path, str]:
    sql = tmp / "PR_PROD_PARITY_EXPORT_v3.sql"
    sql.write_text(TEST_V3_SQL, encoding="utf-8")
    pin = hashlib.sha256(sql.read_bytes()).hexdigest()
    v24.configure_sql_bind(sql, pin)
    return sql, pin


def _write_export(tmp: Path, rows: list, *, captured: str = "2026-10-20T00:00:00Z") -> Path:
    csv_path = tmp / "features.csv"
    cols = list(v24.load_sql_columns())
    assert cols, "test must bind a v3 SQL pin before writing an export"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            out = {c: row.get(c, "") for c in cols}
            if out.get("season") in (None, ""):
                out["season"] = 2026
            for c in cols:
                if out.get(c) is None:
                    out[c] = ""
            writer.writerow(out)
    query = _query()
    meta = {
        "kind": v24.PROD_EXPORT_KIND,
        "source": "test-constructed-not-prod",
        "query": query,
        "query_sha": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "sha256": _sha(csv_path),
        "weeks": [5, 6],
        "columns": cols,
        "captured_utc": captured,
        "data_as_of": "2026-10-19T23:00:00Z",
    }
    (tmp / "EXPORT.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return tmp


def _team_row(week: int, home: str, away: str, *, rest_h=6.0, rest_a=7.0, roof=1.0, epa_h=0.03, epa_a=0.02) -> dict:
    return {
        "game_id": f"2026_{week:02d}_{away}_{home}",
        "game_id_product": f"2026-W{week:02d}-{away}@{home}",
        "season": 2026,
        "week": week,
        "home_team": home,
        "away_team": away,
        "home_off_epa_5g": epa_h,
        "away_off_epa_5g": epa_a,
        "home_def_epa_allowed_5g": -0.01,
        "away_def_epa_allowed_5g": -0.015,
        "home_pass_rate_5g": 0.57,
        "away_pass_rate_5g": 0.56,
        "home_success_offense_5g": 0.45,
        "away_success_offense_5g": 0.44,
        "home_pressure_allowed_5g": 0.20,
        "away_pressure_allowed_5g": 0.18,
        "home_rest_days": rest_h,
        "away_rest_days": rest_a,
        "home_rest_days_raw": rest_h,
        "away_rest_days_raw": rest_a,
        "roof": "dome" if roof == 1.0 else "outdoors",
        "roof_dome": roof,
        "roof_vocab_unknown": False,
        "diff_off_epa_5g": epa_h - epa_a,
    }


def test_c5_frozen_helper_pins() -> None:
    assert _sha(IMV / "nfl_imv_v22.py") == v24.V22_PIN
    assert _sha(IMV / "nfl_imv_v23.py") == v24.V23_PIN
    assert v24.V22_PIN.startswith("57a419b4")
    assert v24.V23_PIN.startswith("fe66b374")
    rec = v24.stamp_helper_shas(IMV)
    assert rec["ok"] is True
    assert rec["v22"] == v24.V22_PIN
    assert rec["v23"] == v24.V23_PIN
    assert rec["v21"] == v24.V21_PIN


def test_c5_mismatch_blocks(tmp_path: Path) -> None:
    dest = tmp_path / "imv"
    dest.mkdir()
    for name in ("nfl_imv_v21.py", "nfl_imv_v22.py", "nfl_imv_v23.py", "nfl_imv_v24.py"):
        (dest / name).write_text("not-the-helper\n", encoding="utf-8")
    rec = v24.stamp_helper_shas(dest)
    assert rec["ok"] is False
    assert "HELPER_V22_SHA_MISMATCH" in rec["flags"] or rec["flag"] == "HELPER_V21_SHA_MISMATCH"


def test_c5_refuse_imv_inside_base(tmp_path: Path) -> None:
    base = tmp_path / "base"
    inside = base / "scripts" / "nfl" / "imv"
    inside.mkdir(parents=True)
    assert v24.refuse_imv_inside_base(inside, base)["ok"] is False
    outside = tmp_path / "imv-bundle"
    outside.mkdir()
    assert v24.refuse_imv_inside_base(outside, base)["ok"] is True


def test_c1_zero_matched_rows_fail(tmp_path: Path) -> None:
    _bind_test_v3(tmp_path)
    export = v24.load_prod_export(
        _write_export(tmp_path, [_team_row(5, "GB", "CHI")]),
        build_started_utc="2026-10-22T00:00:00Z",
    )
    local = [_team_row(6, "DEN", "SEA")]  # no prod W-1 SEA/DEN
    doc = v24.parity_local_w_vs_prod_w_minus_1(local, export, week_cap=6, grade="cert")
    assert doc["status"] == "FAIL_ZERO_MATCHED_ROWS"
    assert doc["compared_team_weeks"] == 0
    assert doc["fails_on_zero_matched"] is True


def test_c2_only_ten_of_fourteen_and_separate_keys() -> None:
    assert v24.N_OF_14_COMPARABLE == 10
    assert len(v24.PARITY_TEAM_KEYS) == 10 or len(v24.PARITY_TEAM_KEYS) == 5
    assert set(v24.SEPARATE_CHECK_KEYS) == {
        "home_rest_days",
        "away_rest_days",
        "roof_dome",
        "diff_off_epa_5g",
    }
    assert len(v22.PARITY_KEYS) == 14
    assert set(v24.SEPARATE_CHECK_KEYS).isdisjoint(set(v24.PARITY_TEAM_KEYS))


def test_c3_cert_tighter_than_plumbing(tmp_path: Path) -> None:
    _bind_test_v3(tmp_path)
    prod = [_team_row(5, "GB", "CHI", epa_h=0.030, epa_a=0.020)]
    export = v24.load_prod_export(
        _write_export(tmp_path, prod),
        build_started_utc="2026-10-22T00:00:00Z",
    )
    local = [_team_row(6, "GB", "CHI", epa_h=0.038, epa_a=0.020)]  # delta 0.008
    local[0]["diff_off_epa_5g"] = 0.038 - 0.020
    plumbing = v24.parity_local_w_vs_prod_w_minus_1(local, export, week_cap=6, grade="plumbing")
    cert = v24.parity_local_w_vs_prod_w_minus_1(local, export, week_cap=6, grade="cert")
    assert plumbing["tolerances"]["off_epa_5g"] == 0.02
    assert cert["tolerances"]["off_epa_5g"] == 0.005
    assert plumbing["status"] == "PASS"
    assert cert["status"] == "FAIL_VALUE_MISMATCH"


def test_c3_cert_pass_bar(tmp_path: Path) -> None:
    _bind_test_v3(tmp_path)
    prod = [
        _team_row(5, "GB", "CHI"),
        _team_row(6, "GB", "CHI"),
    ]
    export = v24.load_prod_export(
        _write_export(tmp_path, prod),
        build_started_utc="2026-10-22T00:00:00Z",
    )
    local = [_team_row(6, "GB", "CHI", epa_h=0.032, epa_a=0.021)]
    local[0]["diff_off_epa_5g"] = 0.032 - 0.021
    doc = v24.parity_local_w_vs_prod_w_minus_1(local, export, week_cap=6, grade="cert")
    assert doc["status"] == "PASS"
    assert doc["coverage"] >= 0.90
    assert doc["separate"]["perfect"] is True
    assert doc["comparable_of_14"] == 10


def test_c2_separate_rest_roof_and_diff_identity(tmp_path: Path) -> None:
    _bind_test_v3(tmp_path)
    prod = [_team_row(5, "GB", "CHI"), _team_row(6, "GB", "CHI", rest_h=6.0, roof=1.0)]
    export = v24.load_prod_export(
        _write_export(tmp_path, prod),
        build_started_utc="2026-10-22T00:00:00Z",
    )
    local = [_team_row(6, "GB", "CHI", rest_h=8.0, roof=1.0)]
    bad = v24.parity_local_w_vs_prod_w_minus_1(local, export, week_cap=6, grade="cert")
    assert bad["status"] == "FAIL_SOURCE_CHECK"
    local2 = [_team_row(6, "GB", "CHI")]
    local2[0]["diff_off_epa_5g"] = 9.99
    ident = v24.parity_local_w_vs_prod_w_minus_1(local2, export, week_cap=6, grade="cert")
    assert ident["status"] == "FAIL_INTERNAL_CHECK"
    assert any(f.get("key") == "diff_off_epa_5g" for f in ident["separate"]["fails"])


def test_c4_requires_capture_asof_sqlsha_and_rejects_after_build(tmp_path: Path) -> None:
    _bind_test_v3(tmp_path)
    rows = [_team_row(5, "GB", "CHI")]
    jsonl_only = tmp_path / "jsonl_only"
    jsonl_only.mkdir()
    (jsonl_only / "features.jsonl").write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
    (jsonl_only / "EXPORT.meta.json").write_text(json.dumps({"kind": v24.PROD_EXPORT_KIND}), encoding="utf-8")
    no_csv = v24.load_prod_export(jsonl_only, build_started_utc="2026-10-22T00:00:00Z")
    assert no_csv["status"] == "NOT_RUN_NO_PROD_EXPORT"
    assert "no jsonl converter" in (no_csv.get("reason") or "")

    incomplete = tmp_path / "incomplete"
    incomplete.mkdir()
    _write_export(incomplete, rows)
    meta = json.loads((incomplete / "EXPORT.meta.json").read_text(encoding="utf-8"))
    del meta["captured_utc"]
    (incomplete / "EXPORT.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    missing = v24.load_prod_export(incomplete, build_started_utc="2026-10-22T00:00:00Z")
    assert missing["status"] == "NOT_RUN_NO_PROD_EXPORT"
    assert "captured_utc" in (missing.get("reason") or "")

    late_dir = tmp_path / "late"
    late_dir.mkdir()
    late = v24.load_prod_export(
        _write_export(late_dir, rows, captured="2026-10-23T00:00:00Z"),
        build_started_utc="2026-10-22T00:00:00Z",
    )
    assert late["status"] == "FAIL_EXPORT_CAPTURED_AFTER_BUILD"
    par = v24.parity_local_w_vs_prod_w_minus_1(rows, late, week_cap=6)
    assert par["status"] == "FAIL_EXPORT_CAPTURED_AFTER_BUILD"


def test_c6_sha256sums_written_last(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    (store / "features.jsonl").write_text("{}\n", encoding="utf-8")
    (store / "HELPER_V22.sha256").write_text(v24.V22_PIN + "\n", encoding="utf-8")
    rec = v24.write_store_sha256sums_last(store)
    assert rec["ok"] is True
    assert rec["written_last"] is True
    text = (store / "SHA256SUMS").read_text(encoding="utf-8")
    assert "features.jsonl" in text
    assert "HELPER_V22.sha256" in text
    assert "SHA256SUMS" not in text.split("  ")[-1]


def test_bundle_copies_helpers_and_docs(tmp_path: Path) -> None:
    dest = tmp_path / "bundle"
    rec = v24.write_helper_bundle(IMV, dest)
    assert rec["ok"] is True
    for name in v24.BUNDLE_HELPERS:
        assert (dest / name).is_file()
    assert (dest / "README.md").is_file()
    assert (dest / "nfl-imv-feature-path-v2.4.md").is_file()
    assert _sha(dest / "nfl_imv_v22.py") == v24.V22_PIN
    assert _sha(dest / "nfl_imv_v23.py") == v24.V23_PIN


def test_source_gating_v24_scripts() -> None:
    runner = (IMV / "nfl-imv-sealed-v2.4.sh").read_text(encoding="utf-8")
    builder = (IMV / "nfl-imv-feature-build-v2.4.sh").read_text(encoding="utf-8")
    assert "57a419b4" in runner and "fe66b374" in runner
    assert "57a419b4" in builder and "fe66b374" in builder
    assert "write-store-sums" in builder
    assert "IMV_DIR_INSIDE_BASE" in runner or "inside BASE" in runner
    assert "nfl_imv_v24" in runner
    assert v23.V21_PIN == v24.V21_PIN


def test_c57032db_key_split_and_csv_contract() -> None:
    split = v24.key_split()
    assert split["n"]["parity"] == 10
    assert split["n"]["source_check"] == 3
    assert split["n"]["internal"] == 1
    assert split["n"]["injury_null"] == 3
    assert split["n"]["untested"] == 24
    assert split["n"]["total"] == 41
    assert v24.SQL_V3_PIN == "b10d6cfd90b0586070c5a4ed3df5cd9782d2d7ad6e6145dcc3719f67a3d5e5c0"
    assert v24.SQL_V3_N_COLUMNS == 41
    assert v24.ROOF_AUDIT_COL == "roof_vocab_unknown"
    assert set(v24.SOURCE_CHECK_KEYS) == {"home_rest_days", "away_rest_days", "roof_dome"}
    assert v24.INTERNAL_CHECK_KEYS == ("diff_off_epa_5g",)


def test_73815046_unknown_column_and_duplicates(tmp_path: Path) -> None:
    _bind_test_v3(tmp_path)
    good = tmp_path / "good"
    good.mkdir()
    _write_export(good, [_team_row(5, "GB", "CHI")])
    csv_path = good / "features.csv"
    text = csv_path.read_text(encoding="utf-8")
    bad = tmp_path / "unknown"
    bad.mkdir()
    (bad / "features.csv").write_text(text.replace("roof_dome", "roof_dome,extra_col", 1), encoding="utf-8")
    (bad / "EXPORT.meta.json").write_text((good / "EXPORT.meta.json").read_text(encoding="utf-8"), encoding="utf-8")
    unknown = v24.read_prod_export_csv(bad / "features.csv")
    assert unknown["status"] == "NOT_RUN_NO_PROD_EXPORT"

    dup = tmp_path / "dup"
    dup.mkdir()
    _write_export(dup, [_team_row(5, "GB", "CHI"), _team_row(5, "GB", "CHI")])
    parsed = v24.read_prod_export_csv(dup / "features.csv")
    assert parsed["status"] == "FAIL_DUPLICATE_SCHEDULE_ROWS"
    par = v24.parity_local_w_vs_prod_w_minus_1([_team_row(6, "GB", "CHI")], parsed, week_cap=6)
    assert par["status"] == "FAIL_DUPLICATE_SCHEDULE_ROWS"


def test_v3_sql_missing_or_sha_mismatch_is_not_run(tmp_path: Path) -> None:
    v24.configure_sql_bind(None, None)
    missing = v24.bind_prod_sql()
    assert missing["status"] == "NOT_RUN_NO_PROD_EXPORT"
    assert missing["reason"] == "SQL_V3_MISSING"
    assert missing["pin"] == v24.SQL_V3_PIN

    fake = tmp_path / "PR_PROD_PARITY_EXPORT_v3.sql"
    fake.write_text("SELECT 1\n", encoding="utf-8")
    mismatch = v24.bind_prod_sql(sql_path=fake, sql_pin=v24.SQL_V3_PIN)
    assert mismatch["status"] == "NOT_RUN_NO_PROD_EXPORT"
    assert mismatch["reason"] == "SQL_V3_SHA_MISMATCH"
    parsed = v24.read_prod_export_csv(tmp_path / "features.csv", sql_path=fake, sql_pin=v24.SQL_V3_PIN)
    assert parsed["status"] == "NOT_RUN_NO_PROD_EXPORT"
    assert parsed["reason"] == "SQL_V3_SHA_MISMATCH"


def test_roof_map_and_vocab_unknown_not_run(tmp_path: Path) -> None:
    assert v24.map_roof_dome("dome") == 1.0
    assert v24.map_roof_dome("closed") == 1.0
    assert v24.map_roof_dome("outdoors") == 0.0
    assert v24.map_roof_dome("open") == 0.0
    assert v24.map_roof_dome("retractable") is None
    assert v24.map_roof_dome("") is None
    _bind_test_v3(tmp_path)
    prod = [
        _team_row(5, "GB", "CHI"),
        _team_row(6, "GB", "CHI", roof=0.0),
    ]
    prod[1]["roof"] = "retractable"
    prod[1]["roof_dome"] = None
    prod[1]["roof_vocab_unknown"] = True
    export = v24.load_prod_export(
        _write_export(tmp_path, prod),
        build_started_utc="2026-10-22T00:00:00Z",
    )
    local = [_team_row(6, "GB", "CHI", roof=1.0)]
    doc = v24.parity_local_w_vs_prod_w_minus_1(local, export, week_cap=6, grade="cert")
    assert doc["status"] == "PASS"
    assert doc["separate"]["n_roof_not_run"] == 1
    assert any(r.get("reason") == "roof_vocab_unknown" for r in doc["separate"]["not_run"])


def test_team_code_consistency(tmp_path: Path) -> None:
    _bind_test_v3(tmp_path)
    bad = _team_row(5, "GB", "CHI")
    bad["home_team"] = "XYZ"
    export_dir = tmp_path / "bad_team"
    export_dir.mkdir()
    parsed = v24.read_prod_export_csv(
        _write_export(export_dir, [bad]) / "features.csv"
    )
    assert parsed["status"] == "FAIL_TEAM_CODE"

    alias_dir = tmp_path / "alias"
    alias_dir.mkdir()
    prod = [_team_row(5, "LAR", "SEA"), _team_row(6, "LAR", "SEA")]
    export = v24.load_prod_export(
        _write_export(alias_dir, prod),
        build_started_utc="2026-10-22T00:00:00Z",
    )
    local = [_team_row(6, "LA", "SEA")]
    local[0]["home_team"] = "LA"
    local[0]["diff_off_epa_5g"] = local[0]["home_off_epa_5g"] - local[0]["away_off_epa_5g"]
    doc = v24.parity_local_w_vs_prod_w_minus_1(local, export, week_cap=6, grade="cert")
    assert doc["status"] == "PASS"
    assert doc["separate"]["team_perfect"] is True


def test_rest_raw_and_derived_source_check(tmp_path: Path) -> None:
    _bind_test_v3(tmp_path)
    prod = [_team_row(5, "GB", "CHI"), _team_row(6, "GB", "CHI", rest_h=6.0, rest_a=7.0)]
    export = v24.load_prod_export(
        _write_export(tmp_path, prod),
        build_started_utc="2026-10-22T00:00:00Z",
    )
    local = [_team_row(6, "GB", "CHI", rest_h=6.0, rest_a=7.0)]
    local[0]["home_rest_days_raw"] = 99.0
    doc = v24.parity_local_w_vs_prod_w_minus_1(local, export, week_cap=6, grade="cert")
    assert doc["status"] == "PASS"
    local2 = [_team_row(6, "GB", "CHI", rest_h=9.0, rest_a=7.0)]
    bad = v24.parity_local_w_vs_prod_w_minus_1(local2, export, week_cap=6, grade="cert")
    assert bad["status"] == "FAIL_SOURCE_CHECK"
