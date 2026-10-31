"""54ba672b — IMV v2.5 reader contracts. Synthetic only. No Mac / no parity evidence."""

from __future__ import annotations

import csv
import hashlib
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
IMV = ROOT / "scripts" / "nfl" / "imv"
import sys

sys.path.insert(0, str(IMV))

import nfl_imv_v24 as v24  # noqa: E402
import nfl_imv_v25 as v25  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cte_plus_outer_sql(cols: list[str]) -> str:
    outer = ",\n  ".join(cols)
    return f"""WITH sched AS (
  SELECT
    season,
    week,
    game_id,
    home_team,
    away_team,
    gameday,
    roof,
    home_rest,
    away_rest
  FROM nfl_dp_schedules
),
sched_dups AS (
  SELECT game_id AS dup_keys FROM sched GROUP BY 1 HAVING COUNT(*) > 1
)
COPY (
  SELECT
  {outer}
  FROM nfl_dp_matchup_features_weekly f
  WHERE season = 2026
    AND week BETWEEN 3 AND 7
    AND NOT EXISTS (SELECT dup_keys FROM sched_dups)
  ORDER BY week, game_id
) TO STDOUT WITH CSV HEADER;
"""


def _bind(tmp: Path) -> tuple[Path, str]:
    sql = tmp / "PR_PROD_PARITY_EXPORT_v3.sql"
    sql.write_text(_cte_plus_outer_sql(list(v25.PINNED_V3_COLUMNS)), encoding="utf-8")
    pin = _sha(sql)
    v25.configure_sql_bind(sql, pin)
    return sql, pin


def _team_row(week: int, home: str, away: str, *, rest_h=6, rest_a=7, roof=1, epa_h=0.03, epa_a=0.02, n=1) -> dict:
    game = date(2026, 10, 4 + week)
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
        "schedule_game_date": game.isoformat(),
        "home_prev_reg_game_date": date(2026, 10, 4 + week - rest_h).isoformat(),
        "away_prev_reg_game_date": date(2026, 10, 4 + week - rest_a).isoformat(),
        "roof_dome": roof,
        "roof_vocab_unknown": False,
        "schedule_dup_game_rows": 0,
        "export_distinct_week_game_count_per_key": 1,
        "export_row_count": n,
        "diff_off_epa_5g": epa_h - epa_a,
    }


def _write_export(tmp: Path, rows: list, *, captured: str = "2026-10-20T00:00:00Z", query_sha: str | None = None) -> Path:
    csv_path = tmp / "features.csv"
    cols = list(v25.load_sql_columns())
    assert cols
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
                elif out.get(c) is False:
                    out[c] = "f"
                elif out.get(c) is True:
                    out[c] = "t"
            writer.writerow(out)
    meta = {
        "kind": v25.PROD_EXPORT_KIND,
        "source": "test-constructed-not-prod",
        "query_sha": query_sha or v25.SQL_V3_PIN,
        "sha256": _sha(csv_path),
        "weeks": [5, 6],
        "columns": cols,
        "captured_utc": captured,
        "data_as_of": "2026-10-19T23:00:00Z",
    }
    (tmp / "EXPORT.meta.json").write_text(__import__("json").dumps(meta), encoding="utf-8")
    (tmp / "EXPORT.sha256").write_text(meta["sha256"] + "\n", encoding="utf-8")
    return tmp


def test_r1_skips_nine_col_cte(tmp_path: Path) -> None:
    sql, pin = _bind(tmp_path)
    cols = v25.csv_columns_from_sql(sql.read_text(encoding="utf-8"))
    assert len(cols) == 41
    assert cols[0] == "season"
    assert "roof_vocab_unknown" in cols
    assert cols == v25.PINNED_V3_COLUMNS
    bound = v25.bind_prod_sql(sql_path=sql, sql_pin=pin)
    assert bound["ok"] is True


def test_r2_bad_type_is_not_run(tmp_path: Path) -> None:
    _bind(tmp_path)
    rows = [_team_row(5, "GB", "CHI")]
    _write_export(tmp_path, rows)
    text = (tmp_path / "features.csv").read_text(encoding="utf-8")
    bad = text.replace("0.03", "not-a-number", 1)
    (tmp_path / "features.csv").write_text(bad, encoding="utf-8")
    parsed = v25.read_prod_export_csv(tmp_path / "features.csv")
    assert parsed["status"] == "NOT_RUN_NO_PROD_EXPORT"
    assert "type error" in (parsed.get("reason") or "")


def test_r3_roof_flag_blocks_cert(tmp_path: Path) -> None:
    _bind(tmp_path)
    prod = [_team_row(5, "GB", "CHI", n=2), _team_row(6, "GB", "CHI", n=2)]
    prod[1]["roof_vocab_unknown"] = True
    export = v25.load_prod_export(
        _write_export(tmp_path, prod),
        build_started_utc="2026-10-22T00:00:00Z",
    )
    local = [_team_row(6, "GB", "CHI")]
    doc = v25.parity_local_w_vs_prod_w_minus_1(local, export, week_cap=6, grade="cert")
    assert doc["status"] == "NOT_RUN_ROOF_VOCAB"
    assert doc["evidence_label"] == "REPORTED"
    assert doc["separate"]["n_roof_not_run"] == 1


def test_r4_rest_raw_derived_mismatch(tmp_path: Path) -> None:
    _bind(tmp_path)
    prod = [_team_row(5, "GB", "CHI", n=2), _team_row(6, "GB", "CHI", rest_h=6, rest_a=7, n=2)]
    prod[1]["home_rest_days"] = 99
    export = v25.load_prod_export(
        _write_export(tmp_path, prod),
        build_started_utc="2026-10-22T00:00:00Z",
    )
    local = [_team_row(6, "GB", "CHI", rest_h=6, rest_a=7)]
    local[0]["home_rest_days"] = 99
    doc = v25.parity_local_w_vs_prod_w_minus_1(local, export, week_cap=6, grade="cert")
    assert doc["status"] == "FAIL_SOURCE_CHECK"
    assert any(f.get("flag") == "REST_RAW_DERIVED_MISMATCH" for f in doc["separate"]["fails"])


def test_r5_exported_dup_and_row_count(tmp_path: Path) -> None:
    _bind(tmp_path)
    rows = [_team_row(5, "GB", "CHI", n=1)]
    rows[0]["schedule_dup_game_rows"] = 1
    _write_export(tmp_path, rows)
    parsed = v25.read_prod_export_csv(tmp_path / "features.csv")
    assert parsed["status"] == "FAIL_DUPLICATE_SCHEDULE_ROWS"

    rows2 = [_team_row(5, "GB", "CHI", n=9)]
    dest = tmp_path / "count"
    dest.mkdir()
    _bind(dest)
    _write_export(dest, rows2)
    parsed2 = v25.read_prod_export_csv(dest / "features.csv")
    assert parsed2["status"] == "NOT_RUN_NO_PROD_EXPORT"
    assert "export_row_count" in (parsed2.get("reason") or "")


def test_r6_retired_and_unparseable(tmp_path: Path) -> None:
    _bind(tmp_path)
    bad = _team_row(5, "STL", "CHI")
    dest = tmp_path / "retired"
    dest.mkdir()
    _bind(dest)
    _write_export(dest, [bad])
    parsed = v25.read_prod_export_csv(dest / "features.csv")
    assert parsed["status"] == "FAIL_TEAM_CODE"

    dest2 = tmp_path / "gid"
    dest2.mkdir()
    _bind(dest2)
    row = _team_row(5, "GB", "CHI")
    row["game_id"] = "not-a-game-id"
    _write_export(dest2, [row])
    parsed2 = v25.read_prod_export_csv(dest2 / "features.csv")
    assert parsed2["status"] == "FAIL_TEAM_CODE"


def test_r7_tolerance_override_refused(tmp_path: Path) -> None:
    _bind(tmp_path)
    prod = [_team_row(5, "GB", "CHI", n=2), _team_row(6, "GB", "CHI", n=2)]
    export = v25.load_prod_export(
        _write_export(tmp_path, prod),
        build_started_utc="2026-10-22T00:00:00Z",
    )
    local = [_team_row(6, "GB", "CHI")]
    doc = v25.parity_local_w_vs_prod_w_minus_1(
        local, export, week_cap=6, grade="cert", tolerances={"off_epa_5g": 9.0}
    )
    assert doc["status"] == "NOT_RUN_NO_PROD_EXPORT"
    assert doc["reason"] == "TOLERANCE_OVERRIDE_REFUSED"


def test_r8_reported_and_plumbing_status(tmp_path: Path) -> None:
    _bind(tmp_path)
    prod = [_team_row(5, "GB", "CHI", n=2), _team_row(6, "GB", "CHI", n=2)]
    export = v25.load_prod_export(
        _write_export(tmp_path, prod),
        build_started_utc="2026-10-22T00:00:00Z",
    )
    local = [_team_row(6, "GB", "CHI")]
    cert = v25.parity_local_w_vs_prod_w_minus_1(local, export, week_cap=6, grade="cert")
    assert cert["evidence_label"] == "REPORTED"
    assert cert["status"] == "PASS"
    assert cert["plumbing_status"] == "PASS_PLUMBING"
    plumb = v25.parity_local_w_vs_prod_w_minus_1(local, export, week_cap=6, grade="plumbing")
    assert plumb["status"] == "PASS_PLUMBING"
    assert plumb["plumbing_pass_is_not_cert"] is True


def test_r9_query_sha_export_sha_build_start(tmp_path: Path) -> None:
    _bind(tmp_path)
    rows = [_team_row(5, "GB", "CHI")]
    dest = tmp_path / "q"
    dest.mkdir()
    _bind(dest)
    _write_export(dest, rows, query_sha="deadbeef" * 8)
    no = v25.load_prod_export(dest, build_started_utc="2026-10-22T00:00:00Z")
    assert no["status"] == "NOT_RUN_NO_PROD_EXPORT"
    assert no["reason"] == "SQL_V3_SHA_MISMATCH"

    dest2 = tmp_path / "sha"
    dest2.mkdir()
    _bind(dest2)
    _write_export(dest2, rows)
    meta = dest2 / "EXPORT.meta.json"
    text = meta.read_text(encoding="utf-8").replace(_sha(dest2 / "features.csv"), "")
    # wipe sha256 field
    import json

    doc = json.loads((dest2 / "EXPORT.meta.json").read_text(encoding="utf-8"))
    del doc["sha256"]
    meta.write_text(json.dumps(doc), encoding="utf-8")
    missing = v25.load_prod_export(dest2, build_started_utc="2026-10-22T00:00:00Z")
    assert missing["reason"] == "EXPORT_SHA_REQUIRED"

    dest3 = tmp_path / "build"
    dest3.mkdir()
    _bind(dest3)
    _write_export(dest3, rows)
    absent = v25.load_prod_export(dest3, build_started_utc=None)
    assert absent["reason"] == "BUILD_STARTED_UTC_REQUIRED"


def test_v24_pin_unchanged() -> None:
    assert _sha(IMV / "nfl_imv_v24.py") == v25.V24_PIN
    assert _sha(IMV / "nfl_imv_v22.py") == v24.V22_PIN
    assert _sha(IMV / "nfl_imv_v23.py") == v24.V23_PIN
    assert v25.SQL_V3_PIN == "b10d6cfd90b0586070c5a4ed3df5cd9782d2d7ad6e6145dcc3719f67a3d5e5c0"
    assert len(v25.PINNED_V3_COLUMNS) == 41
