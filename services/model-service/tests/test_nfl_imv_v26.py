"""04fd87a1 — IMV v2.6 reader. Synthetic only. No Mac / no parity evidence."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
IMV = ROOT / "scripts" / "nfl" / "imv"
SQL_UPLOAD = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/PR_PROD_PARITY_EXPORT_v3_621d.sql"
)
import sys

sys.path.insert(0, str(IMV))

import nfl_imv_v24 as v24  # noqa: E402
import nfl_imv_v25 as v25  # noqa: E402
import nfl_imv_v26 as v26  # noqa: E402

EXPECTED_41 = v26.PINNED_V3_COLUMNS


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _real_sql_bytes() -> bytes:
    repo = ROOT / "ops" / "platform" / "PR_PROD_PARITY_EXPORT_v3.sql"
    if repo.is_file():
        return repo.read_bytes()
    return SQL_UPLOAD.read_bytes()


def _bind_real(tmp: Path) -> tuple[Path, str]:
    sql = tmp / "PR_PROD_PARITY_EXPORT_v3.sql"
    sql.write_bytes(_real_sql_bytes())
    pin = _sha(sql)
    v26.configure_sql_bind(sql, pin)
    return sql, pin


def _team_row(week: int, home: str, away: str, *, rest_h=6, rest_a=7, roof=1, epa_h=0.03, epa_a=0.02, n=1) -> dict:
    game = date(2026, 10, 4 + week)
    ts = "2026-10-19T23:00:00Z"
    return {
        "game_id": f"2026_{week:02d}_{away}_{home}",
        "season": 2026,
        "week": week,
        "game_date": game.isoformat(),
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
        "home_pressure_generated_5g": 0.22,
        "away_pressure_generated_5g": 0.21,
        "home_early_down_pass_rate_5g": 0.58,
        "away_early_down_pass_rate_5g": 0.55,
        "home_red_zone_td_rate_5g": 0.50,
        "away_red_zone_td_rate_5g": 0.48,
        "home_success_defense_allowed_5g": 0.40,
        "away_success_defense_allowed_5g": 0.39,
        "diff_off_epa_5g": epa_h - epa_a,
        "feature_updated_at": ts,
        "schedule_game_type": "REG",
        "schedule_roof": "outdoors",
        "schedule_game_date": game.isoformat(),
        "schedule_updated_at": ts,
        "home_rest_days": rest_h,
        "away_rest_days": rest_a,
        "home_prev_reg_game_date": date(2026, 10, 4 + week - rest_h).isoformat(),
        "away_prev_reg_game_date": date(2026, 10, 4 + week - rest_a).isoformat(),
        "roof_dome": roof,
        "roof_vocab_unknown": False,
        "feature_as_of_max_utc": ts,
        "schedule_as_of_max_utc": ts,
        "export_row_count": n,
        "export_distinct_week_game_count_per_key": 1,
        "schedule_dup_game_rows": 0,
    }


def _write_export(tmp: Path, rows: list, *, captured: str = "2026-10-20T00:00:00Z", query_sha: str | None = None) -> Path:
    csv_path = tmp / "features.csv"
    cols = list(v26.load_sql_columns())
    assert cols
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            out = {c: row.get(c, "") for c in cols}
            for c in cols:
                if out.get(c) is None:
                    out[c] = ""
                elif out.get(c) is False:
                    out[c] = "f"
                elif out.get(c) is True:
                    out[c] = "t"
            writer.writerow(out)
    meta = {
        "kind": v26.PROD_EXPORT_KIND,
        "source": "test-constructed-not-prod",
        "query_sha": query_sha or v26.SQL_V3_PIN,
        "sha256": _sha(csv_path),
        "weeks": [5, 6],
        "columns": cols,
        "captured_utc": captured,
        "data_as_of": "2026-10-19T23:00:00Z",
    }
    (tmp / "EXPORT.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (tmp / "EXPORT.sha256").write_text(meta["sha256"] + "\n", encoding="utf-8")
    return tmp


def test_r1_real_sql_tuple() -> None:
    sql_text = _real_sql_bytes().decode("utf-8")
    parsed = v26.csv_columns_from_sql(sql_text)
    assert parsed == EXPECTED_41
    assert parsed == v26.PINNED_V3_COLUMNS
    assert len(parsed) == 41
    assert "game_date" in parsed
    assert "feature_updated_at" in parsed
    assert "schedule_game_type" in parsed
    assert "schedule_roof" in parsed
    assert "schedule_updated_at" in parsed
    assert "feature_as_of_max_utc" in parsed
    assert "schedule_as_of_max_utc" in parsed
    assert "diff_rest_days" not in parsed
    assert "surface_turf" not in parsed
    assert "diff_def_epa_allowed_5g" not in parsed
    assert "schedule_game_date" in parsed
    assert hashlib.sha256(_real_sql_bytes()).hexdigest() == v26.SQL_V3_PIN


def test_r1_bind_real_sql(tmp_path: Path) -> None:
    sql, pin = _bind_real(tmp_path)
    bound = v26.bind_prod_sql(sql_path=sql, sql_pin=pin)
    assert bound["ok"] is True
    assert bound["columns"] == list(EXPECTED_41)


def test_types_cover_all_41() -> None:
    typed = (
        v26.CSV_INT_COLS
        | v26.CSV_DATE_COLS
        | v26.CSV_STR_COLS
        | v26.CSV_BOOL_COLS
        | v26.CSV_TS_COLS
        | v26.CSV_FLOAT_COLS
    )
    assert typed == set(v26.PINNED_V3_COLUMNS)


def test_bad_type_and_timestamp(tmp_path: Path) -> None:
    _bind_real(tmp_path)
    rows = [_team_row(5, "GB", "CHI")]
    _write_export(tmp_path, rows)
    text = (tmp_path / "features.csv").read_text(encoding="utf-8")
    bad = text.replace("0.03", "not-a-number", 1)
    (tmp_path / "features.csv").write_text(bad, encoding="utf-8")
    parsed = v26.read_prod_export_csv(tmp_path / "features.csv")
    assert parsed["status"] == "NOT_RUN_NO_PROD_EXPORT"
    assert "type error" in (parsed.get("reason") or "")

    dest = tmp_path / "ts"
    dest.mkdir()
    _bind_real(dest)
    rows2 = [_team_row(5, "GB", "CHI")]
    rows2[0]["feature_updated_at"] = "not-a-timestamp"
    _write_export(dest, rows2)
    parsed2 = v26.read_prod_export_csv(dest / "features.csv")
    assert parsed2["status"] == "NOT_RUN_NO_PROD_EXPORT"
    assert "timestamp" in (parsed2.get("reason") or "")


def test_export_sha256_file_required(tmp_path: Path) -> None:
    _bind_real(tmp_path)
    rows = [_team_row(5, "GB", "CHI")]
    _write_export(tmp_path, rows)
    (tmp_path / "EXPORT.sha256").unlink()
    missing = v26.load_prod_export(tmp_path, build_started_utc="2026-10-22T00:00:00Z")
    assert missing["reason"] == "EXPORT_SHA256_FILE_REQUIRED"


def test_cert_still_pass_on_typed_row(tmp_path: Path) -> None:
    _bind_real(tmp_path)
    prod = [_team_row(5, "GB", "CHI", n=2), _team_row(6, "GB", "CHI", n=2)]
    export = v26.load_prod_export(
        _write_export(tmp_path, prod),
        build_started_utc="2026-10-22T00:00:00Z",
    )
    assert export["status"] == "OK"
    local = [_team_row(6, "GB", "CHI")]
    doc = v26.parity_local_w_vs_prod_w_minus_1(local, export, week_cap=6, grade="cert")
    assert doc["status"] == "PASS"
    assert doc["evidence_label"] == "REPORTED"


def test_frozen_pins() -> None:
    assert _sha(IMV / "nfl_imv_v25.py") == v26.V25_PIN
    assert _sha(IMV / "nfl_imv_v24.py") == v26.V24_PIN
    assert _sha(IMV / "nfl_imv_v22.py") == v24.V22_PIN
    assert _sha(IMV / "nfl_imv_v23.py") == v24.V23_PIN
    assert v26.SQL_V3_PIN == "b10d6cfd90b0586070c5a4ed3df5cd9782d2d7ad6e6145dcc3719f67a3d5e5c0"
    assert v26.V2_5_SHA256SUMS_PIN == (
        "b0cf91da6cccac015877a6a4bdd7af66b9290085f61fe9b5ca340d7c61f8f8e2"
    )
    assert v25.PINNED_V3_COLUMNS != v26.PINNED_V3_COLUMNS
    pins = v26.stamp_helper_shas(IMV, sums_v25=IMV / "SHA256SUMS.v2.5")
    assert pins["ok"] is True
    assert pins["v26"] == _sha(IMV / "nfl_imv_v26.py")
