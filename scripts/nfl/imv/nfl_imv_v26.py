#!/usr/bin/env python3
"""IMV v2.6 reader (04fd87a1 R-1 close). Layer on frozen v21–v25.

Do not edit nfl_imv_v21.py … nfl_imv_v25.py or the v2.4 shells.
v25 = 582eb6ce… (IMV v2.5 review 04fd87a1 RETURN).

PINNED_V3_COLUMNS is the 41 aliases of PR_PROD_PARITY_EXPORT_v3.sql
lines 60–102, sha b10d6cfd…. Do not invent the list.
Restored: game_date, feature_updated_at, schedule_game_type,
schedule_roof, schedule_updated_at, feature_as_of_max_utc,
schedule_as_of_max_utc.
Removed (not in v3): five extra diff_* keys, diff_rest_days, surface_turf.
Every column has a type. EXPORT.sha256 is mandatory.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import nfl_imv_v21 as v21
import nfl_imv_v24 as v24
import nfl_imv_v25 as v25

RULING = "04fd87a1"
PARITY_PROTOCOL = v25.PARITY_PROTOCOL
EXPORT_RULING = "v2.6-r1-sql-tuple"
SCRIPT_ID = "nfl-imv-v2.6"
EVIDENCE_LABEL = v25.EVIDENCE_LABEL
SQL_V3_PATH = v25.SQL_V3_PATH
SQL_V3_PIN = v25.SQL_V3_PIN
SQL_V3_N_COLUMNS = 41
V21_PIN = v25.V21_PIN
V22_PIN = v25.V22_PIN
V23_PIN = v25.V23_PIN
V24_PIN = v25.V24_PIN
V25_PIN = "582eb6cea720ab2e019e7085b731dab682bb61ee2438ccd3c7cf367064161565"
V2_5_SHA256SUMS_PIN = "b0cf91da6cccac015877a6a4bdd7af66b9290085f61fe9b5ca340d7c61f8f8e2"
ROOF_AUDIT_COL = v25.ROOF_AUDIT_COL
RETIRED_TEAM_CODES = v25.RETIRED_TEAM_CODES
TEAM_ALIASES = v25.TEAM_ALIASES
NFL_32 = v25.NFL_32
BOOL_TRUE = v25.BOOL_TRUE
BOOL_FALSE = v25.BOOL_FALSE
REST_DERIVED_KEYS = v25.REST_DERIVED_KEYS
REST_DATE_COLS = v25.REST_DATE_COLS
GAME_DATE_COL = v25.GAME_DATE_COL
DUP_COL = v25.DUP_COL
PER_KEY_COL = v25.PER_KEY_COL
ROW_COUNT_COL = v25.ROW_COUNT_COL

# Exact SELECT aliases from SQL v3 lines 60-102 (parser-confirmed).
PINNED_V3_COLUMNS: Tuple[str, ...] = (
    "season",
    "week",
    "game_id",
    "game_date",
    "home_team",
    "away_team",
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
    "home_pass_rate_5g",
    "away_pass_rate_5g",
    "home_success_offense_5g",
    "away_success_offense_5g",
    "home_pressure_allowed_5g",
    "away_pressure_allowed_5g",
    "home_pressure_generated_5g",
    "away_pressure_generated_5g",
    "home_early_down_pass_rate_5g",
    "away_early_down_pass_rate_5g",
    "home_red_zone_td_rate_5g",
    "away_red_zone_td_rate_5g",
    "home_success_defense_allowed_5g",
    "away_success_defense_allowed_5g",
    "diff_off_epa_5g",
    "feature_updated_at",
    "schedule_game_type",
    "schedule_roof",
    "schedule_game_date",
    "schedule_updated_at",
    "home_rest_days",
    "away_rest_days",
    "home_prev_reg_game_date",
    "away_prev_reg_game_date",
    "roof_dome",
    "roof_vocab_unknown",
    "feature_as_of_max_utc",
    "schedule_as_of_max_utc",
    "export_row_count",
    "export_distinct_week_game_count_per_key",
    "schedule_dup_game_rows",
)
REQUIRED_V3_COLS = PINNED_V3_COLUMNS
CSV_INT_COLS = frozenset(
    {
        "season",
        "week",
        "home_rest_days",
        "away_rest_days",
        "roof_dome",
        DUP_COL,
        PER_KEY_COL,
        ROW_COUNT_COL,
    }
)
CSV_DATE_COLS = frozenset(
    {
        "game_date",
        GAME_DATE_COL,
        "home_prev_reg_game_date",
        "away_prev_reg_game_date",
    }
)
CSV_STR_COLS = frozenset(
    {
        "game_id",
        "home_team",
        "away_team",
        "schedule_game_type",
        "schedule_roof",
    }
)
CSV_BOOL_COLS = frozenset({ROOF_AUDIT_COL})
CSV_TS_COLS = frozenset(
    {
        "feature_updated_at",
        "schedule_updated_at",
        "feature_as_of_max_utc",
        "schedule_as_of_max_utc",
    }
)
CSV_FLOAT_COLS = frozenset(
    {
        "home_off_epa_5g",
        "away_off_epa_5g",
        "home_def_epa_allowed_5g",
        "away_def_epa_allowed_5g",
        "home_pass_rate_5g",
        "away_pass_rate_5g",
        "home_success_offense_5g",
        "away_success_offense_5g",
        "home_pressure_allowed_5g",
        "away_pressure_allowed_5g",
        "home_pressure_generated_5g",
        "away_pressure_generated_5g",
        "home_early_down_pass_rate_5g",
        "away_early_down_pass_rate_5g",
        "home_red_zone_td_rate_5g",
        "away_red_zone_td_rate_5g",
        "home_success_defense_allowed_5g",
        "away_success_defense_allowed_5g",
        "diff_off_epa_5g",
    }
)
_TYPED = (
    CSV_INT_COLS
    | CSV_DATE_COLS
    | CSV_STR_COLS
    | CSV_BOOL_COLS
    | CSV_TS_COLS
    | CSV_FLOAT_COLS
)
if set(PINNED_V3_COLUMNS) != _TYPED:
    raise RuntimeError("v26 type map must cover the 41 v3 columns exactly")

BUNDLE_HELPERS = (
    "nfl_imv_v21.py",
    "nfl_imv_v22.py",
    "nfl_imv_v23.py",
    "nfl_imv_v24.py",
    "nfl_imv_v25.py",
    "nfl_imv_v26.py",
)
BUNDLE_SHELLS = v25.BUNDLE_SHELLS
SHELL_PINS = {
    "nfl-imv-feature-build-v2.4.sh": "105ac5be2daf40b57ccfdfe9a3daa1568e522d3366eb14a1498121096b6c921d",
    "nfl-imv-sealed-v2.4.sh": "3a5da768e1b83c9a213be554f2865bf6b26fa17f21e89a08c337be8ef5898b2a",
    "nfl-imv-prestage-nflverse.sh": "cba5a4032f35a2c727771eda97ea97a661f6caa10f492a60b6aa604612aad059",
}
HELPER_PINS = {
    "nfl_imv_v21.py": V21_PIN,
    "nfl_imv_v22.py": V22_PIN,
    "nfl_imv_v23.py": V23_PIN,
    "nfl_imv_v24.py": V24_PIN,
    "nfl_imv_v25.py": V25_PIN,
}
_SQL_BIND_OVERRIDE: Optional[Tuple[Path, str]] = None

parse_iso_utc = v25.parse_iso_utc
csv_columns_from_sql = v25.csv_columns_from_sql
canon_team_code = v25.canon_team_code
raw_team_code = v25.raw_team_code
parse_game_id_teams = v25.parse_game_id_teams
team_code_check = v25.team_code_check
rest_days_from_dates = v25.rest_days_from_dates
rest_raw_derived_check = v25.rest_raw_derived_check
parity_local_w_vs_prod_w_minus_1 = v25.parity_local_w_vs_prod_w_minus_1
write_store_sha256sums_last = v25.write_store_sha256sums_last
refuse_imv_inside_base = v25.refuse_imv_inside_base
COVERAGE_MIN = v25.COVERAGE_MIN
PARITY_TOLERANCES_CERT = v25.PARITY_TOLERANCES_CERT
PARITY_TOLERANCES_PLUMBING = v25.PARITY_TOLERANCES_PLUMBING
PROD_EXPORT_KIND = v25.PROD_EXPORT_KIND
N_OF_14_COMPARABLE = v25.N_OF_14_COMPARABLE
SEPARATE_CHECK_KEYS = v25.SEPARATE_CHECK_KEYS
SOURCE_CHECK_KEYS = v25.SOURCE_CHECK_KEYS
INTERNAL_CHECK_KEYS = v25.INTERNAL_CHECK_KEYS
PARITY_TEAM_KEYS = v25.PARITY_TEAM_KEYS
WEEKLY_AVG_RULE = v25.WEEKLY_AVG_RULE


def configure_sql_bind(path: Optional[Path], pin: Optional[str]) -> None:
    global _SQL_BIND_OVERRIDE
    if path is None or not pin:
        _SQL_BIND_OVERRIDE = None
        v25.configure_sql_bind(None, None)
        return
    _SQL_BIND_OVERRIDE = (Path(path), str(pin).strip().lower())
    v25.configure_sql_bind(path, pin)


def bind_prod_sql(
    sql_path: Optional[Path] = None,
    sql_pin: Optional[str] = None,
) -> Dict[str, Any]:
    if _SQL_BIND_OVERRIDE is not None and sql_path is None and sql_pin is None:
        sql_path, sql_pin = _SQL_BIND_OVERRIDE
    path = Path(sql_path) if sql_path is not None else SQL_V3_PATH
    pin = str(sql_pin or SQL_V3_PIN).strip().lower()
    base = {
        "path": str(path),
        "pin": pin,
        "columns": [],
        "n_columns": 0,
        "sha256": None,
        "ruling": EXPORT_RULING,
        "pinned_columns": list(PINNED_V3_COLUMNS),
    }
    if not path.is_file():
        return {**base, "ok": False, "status": "NOT_RUN_NO_PROD_EXPORT", "reason": "SQL_V3_MISSING"}
    got = v21.sha256_file(path)
    if got != pin:
        return {
            **base,
            "ok": False,
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "SQL_V3_SHA_MISMATCH",
            "sha256": got,
        }
    cols = csv_columns_from_sql(path.read_text(encoding="utf-8"))
    if len(cols) != SQL_V3_N_COLUMNS:
        return {
            **base,
            "ok": False,
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "SQL_V3_COLUMN_COUNT",
            "sha256": got,
            "columns": list(cols),
            "n_columns": len(cols),
        }
    missing_req = [c for c in REQUIRED_V3_COLS if c not in cols]
    if missing_req:
        return {
            **base,
            "ok": False,
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "SQL_V3_MISSING_REQUIRED_COLS",
            "sha256": got,
            "columns": list(cols),
            "missing_required": missing_req,
            "n_columns": len(cols),
        }
    if tuple(cols) != PINNED_V3_COLUMNS:
        return {
            **base,
            "ok": False,
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "SQL_V3_COLUMN_MISMATCH",
            "sha256": got,
            "columns": list(cols),
            "n_columns": len(cols),
        }
    return {
        **base,
        "ok": True,
        "status": "OK",
        "reason": None,
        "sha256": got,
        "columns": list(cols),
        "n_columns": len(cols),
    }


def load_sql_columns(
    sql_path: Optional[Path] = None,
    sql_pin: Optional[str] = None,
) -> Tuple[str, ...]:
    bound = bind_prod_sql(sql_path=sql_path, sql_pin=sql_pin)
    if not bound.get("ok"):
        return tuple()
    return tuple(bound.get("columns") or ())


def _parse_date(raw: Any) -> Optional[date]:
    return v25._parse_date(raw)


def _parse_ts(col: str, raw: Any) -> Optional[datetime]:
    text = "" if raw is None else str(raw).strip()
    if text == "":
        return None
    dt = parse_iso_utc(text)
    if dt is None:
        raise ValueError(f"{col} timestamp {text!r}")
    return dt


def _parse_csv_cell(col: str, raw: Any) -> Any:
    text = "" if raw is None else str(raw).strip()
    if text == "":
        return None
    if col in CSV_INT_COLS:
        return int(text)
    if col in CSV_DATE_COLS:
        return _parse_date(text)
    if col in CSV_TS_COLS:
        return _parse_ts(col, text)
    if col in CSV_BOOL_COLS:
        token = text.lower()
        if token in BOOL_TRUE:
            return True
        if token in BOOL_FALSE:
            return False
        raise ValueError(f"{col} bool token {text!r} (t/f only)")
    if col in CSV_STR_COLS:
        return text
    if col in CSV_FLOAT_COLS:
        return float(text)
    raise ValueError(f"untyped column {col}")


def _read_sums(path: Path) -> List[Tuple[str, str]]:
    rows: List[Tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        digest, name = text.split(None, 1)
        rows.append((digest.lower(), name.strip()))
    return rows


def stamp_helper_shas(
    imv_dir: Path,
    *,
    sums_v25: Optional[Path] = None,
    sums: Optional[Path] = None,
) -> Dict[str, Any]:
    root = Path(imv_dir)
    flags: List[str] = []
    helpers = {n: (v21.sha256_file(root / n) if (root / n).is_file() else None) for n in BUNDLE_HELPERS}
    for name, pin in HELPER_PINS.items():
        got = helpers.get(name)
        if got is None:
            flags.append(f"HELPER_{name.upper().replace('.', '_')}_MISSING")
        elif got != pin:
            flags.append(f"HELPER_{name.split('.')[0].upper()}_SHA_MISMATCH")
    if helpers.get("nfl_imv_v26.py") is None:
        flags.append("HELPER_V26_MISSING")
    shells = {n: (v21.sha256_file(root / n) if (root / n).is_file() else None) for n in BUNDLE_SHELLS}
    for name, pin in SHELL_PINS.items():
        got = shells.get(name)
        if got is None:
            flags.append("SHELL_FILE_MISSING")
        elif got != pin:
            flags.append(f"SHELL_{name}_SHA_MISMATCH")
    sums_v25_sha = None
    if sums_v25 is not None:
        sp = Path(sums_v25)
        if not sp.is_file():
            flags.append("SUMS_V25_MISSING")
        else:
            sums_v25_sha = v21.sha256_file(sp)
            if sums_v25_sha != V2_5_SHA256SUMS_PIN:
                flags.append("SUMS_V25_SHA_MISMATCH")
            else:
                for digest, name in _read_sums(sp):
                    fp = root / name
                    if not fp.is_file():
                        flags.append("SUMS_V25_ENTRY_MISSING")
                    elif v21.sha256_file(fp) != digest:
                        flags.append("SUMS_V25_ENTRY_MISMATCH")
    sums_sha = None
    if sums is not None:
        sp = Path(sums)
        if not sp.is_file():
            flags.append("SUMS_MISSING")
        else:
            sums_sha = v21.sha256_file(sp)
            for digest, name in _read_sums(sp):
                fp = root / name
                if not fp.is_file():
                    flags.append("SUMS_ENTRY_MISSING")
                elif v21.sha256_file(fp) != digest:
                    flags.append("SUMS_ENTRY_MISMATCH")
    rec = {
        "v21": helpers.get("nfl_imv_v21.py"),
        "v22": helpers.get("nfl_imv_v22.py"),
        "v23": helpers.get("nfl_imv_v23.py"),
        "v24": helpers.get("nfl_imv_v24.py"),
        "v25": helpers.get("nfl_imv_v25.py"),
        "v26": helpers.get("nfl_imv_v26.py"),
        "v21_pin": V21_PIN,
        "v22_pin": V22_PIN,
        "v23_pin": V23_PIN,
        "v24_pin": V24_PIN,
        "v25_pin": V25_PIN,
        "shells": shells,
        "shell_pins": dict(SHELL_PINS),
        "sums_v25_sha": sums_v25_sha,
        "sums_v25_pin": V2_5_SHA256SUMS_PIN,
        "sums_sha": sums_sha,
        "flags": flags,
        "ok": not flags,
        "flag": None if not flags else flags[0],
        "ruling": RULING,
    }
    return rec


def write_helper_stamps(out_dir: Path, imv_dir: Path) -> Dict[str, Any]:
    rec = stamp_helper_shas(imv_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for key in ("v21", "v22", "v23", "v24", "v25", "v26"):
        (out / f"HELPER_{key.upper()}.sha256").write_text((rec.get(key) or "") + "\n", encoding="utf-8")
    (out / "HELPERS.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return rec


def write_helper_bundle(imv_dir: Path, dest: Path) -> Dict[str, Any]:
    rec = v25.write_helper_bundle(imv_dir, dest)
    src = Path(imv_dir)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    copied = list(rec.get("copied") or [])
    for name in (
        "nfl_imv_v26.py",
        "nfl-imv-mac-runbook-v2.4.2.md",
        "nfl-imv-v2.6-r-trace.md",
        "nfl-imv-feature-path-v2.6.md",
        "SHA256SUMS.v2.5",
        "PR_PROD_PARITY_EXPORT_v3.sql",
    ):
        fp = src / name
        if fp.is_file():
            dest.joinpath(name).write_bytes(fp.read_bytes())
            copied.append(name)
    rec = stamp_helper_shas(src)
    rec["copied"] = copied
    rec["bundle_dir"] = str(dest)
    (dest / "BUNDLE.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return rec


def read_prod_export_csv(
    csv_path: Path,
    *,
    sql_path: Optional[Path] = None,
    sql_pin: Optional[str] = None,
) -> Dict[str, Any]:
    bound = bind_prod_sql(sql_path=sql_path, sql_pin=sql_pin)
    if not bound.get("ok"):
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": bound.get("reason") or "SQL_V3_MISSING",
            "sql": bound,
            "rows": [],
            "ruling": EXPORT_RULING,
            "sql_pin": SQL_V3_PIN,
            "evidence_label": EVIDENCE_LABEL,
        }
    expected = tuple(bound.get("columns") or ())
    if not csv_path.is_file():
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "features.csv missing (CSV required; no converter)",
            "rows": [],
            "ruling": EXPORT_RULING,
            "evidence_label": EVIDENCE_LABEL,
        }
    text = csv_path.read_text(encoding="utf-8")
    if not text.strip():
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "empty CSV",
            "rows": [],
            "ruling": EXPORT_RULING,
            "evidence_label": EVIDENCE_LABEL,
        }
    reader = csv.reader(text.splitlines())
    try:
        header = next(reader)
    except StopIteration:
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "CSV header required",
            "rows": [],
            "ruling": EXPORT_RULING,
            "evidence_label": EVIDENCE_LABEL,
        }
    header = [h.strip() for h in header]
    if list(header) != list(expected):
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "CSV columns missing or unknown vs PR_PROD_PARITY_EXPORT_v3.sql",
            "header": header,
            "expected": list(expected),
            "rows": [],
            "ruling": EXPORT_RULING,
            "evidence_label": EVIDENCE_LABEL,
        }
    rows: List[Dict[str, Any]] = []
    seen: Dict[Tuple[Any, ...], int] = {}
    for i, cells in enumerate(reader, start=2):
        if not cells or all(str(c).strip() == "" for c in cells):
            continue
        if len(cells) != len(header):
            return {
                "status": "NOT_RUN_NO_PROD_EXPORT",
                "reason": f"CSV row {i} width {len(cells)} != header {len(header)}",
                "rows": [],
                "ruling": EXPORT_RULING,
                "evidence_label": EVIDENCE_LABEL,
            }
        rec: Dict[str, Any] = {}
        try:
            for col, cell in zip(header, cells):
                rec[col] = _parse_csv_cell(col, cell)
        except (TypeError, ValueError) as exc:
            return {
                "status": "NOT_RUN_NO_PROD_EXPORT",
                "reason": f"CSV type error row {i}: {exc}",
                "rows": [],
                "ruling": EXPORT_RULING,
                "evidence_label": EVIDENCE_LABEL,
            }
        key = (
            rec.get("season"),
            rec.get("week"),
            canon_team_code(str(rec.get("home_team") or "")),
            canon_team_code(str(rec.get("away_team") or "")),
        )
        seen[key] = seen.get(key, 0) + 1
        rows.append(rec)
    if not rows:
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "empty CSV",
            "rows": [],
            "ruling": EXPORT_RULING,
            "evidence_label": EVIDENCE_LABEL,
        }
    dups = [k for k, n in seen.items() if n > 1]
    if dups:
        return {
            "status": "FAIL_DUPLICATE_SCHEDULE_ROWS",
            "reason": "duplicate schedule rows in export CSV",
            "duplicates": [list(k) for k in dups],
            "rows": [],
            "ruling": EXPORT_RULING,
            "evidence_label": EVIDENCE_LABEL,
        }
    exported_dup = any(int(r.get(DUP_COL) or 0) > 0 for r in rows)
    exported_per_key = any(int(r.get(PER_KEY_COL) or 0) > 1 for r in rows)
    if exported_dup or exported_per_key:
        return {
            "status": "FAIL_DUPLICATE_SCHEDULE_ROWS",
            "reason": "exported schedule_dup>0 or per-key count>1",
            "schedule_dup_game_rows": exported_dup,
            "export_distinct_week_game_count_per_key": exported_per_key,
            "rows": [],
            "ruling": EXPORT_RULING,
            "evidence_label": EVIDENCE_LABEL,
        }
    counts = {r.get(ROW_COUNT_COL) for r in rows}
    if None in counts:
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "export_row_count missing",
            "rows": [],
            "ruling": EXPORT_RULING,
            "evidence_label": EVIDENCE_LABEL,
        }
    if counts != {len(rows)}:
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "export_row_count != parsed rows",
            "export_row_count": sorted(counts),
            "parsed_rows": len(rows),
            "rows": [],
            "ruling": EXPORT_RULING,
            "evidence_label": EVIDENCE_LABEL,
        }
    teams = team_code_check(rows)
    if not teams.get("ok"):
        return {
            "status": "FAIL_TEAM_CODE",
            "reason": "team-code consistency failed on export CSV",
            "team_code": teams,
            "rows": [],
            "ruling": EXPORT_RULING,
            "evidence_label": EVIDENCE_LABEL,
        }
    return {
        "status": "OK",
        "reason": None,
        "rows": rows,
        "sha256": v21.sha256_file(csv_path),
        "path": str(csv_path),
        "columns": list(expected),
        "ruling": EXPORT_RULING,
        "sql_pin": bound.get("sha256"),
        "sql": bound,
        "team_code": teams,
        "evidence_label": EVIDENCE_LABEL,
        "n_rows": len(rows),
    }


def load_prod_export(
    export_dir: Optional[Path],
    *,
    build_started_utc: Optional[str] = None,
    sql_path: Optional[Path] = None,
    sql_pin: Optional[str] = None,
) -> Dict[str, Any]:
    """v2.6: v3 tuple + types; EXPORT.sha256 file is mandatory."""
    bound = bind_prod_sql(sql_path=sql_path, sql_pin=sql_pin)
    empty = {
        "rows": [],
        "meta": None,
        "ruling": EXPORT_RULING,
        "sql_pin": SQL_V3_PIN,
        "evidence_label": EVIDENCE_LABEL,
    }
    if not bound.get("ok"):
        return {
            **empty,
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": bound.get("reason") or "SQL_V3_MISSING",
            "sql": bound,
        }
    if not (build_started_utc or "").strip():
        return {**empty, "status": "NOT_RUN_NO_PROD_EXPORT", "reason": "BUILD_STARTED_UTC_REQUIRED"}
    if export_dir is None:
        return {**empty, "status": "NOT_RUN_NO_PROD_EXPORT", "reason": "IMV_PROD_EXPORT unset"}
    root = Path(export_dir)
    csv_path = root / "features.csv"
    if not csv_path.is_file():
        alt = root / "export.csv"
        csv_path = alt if alt.is_file() else csv_path
    if not csv_path.is_file():
        return {
            **empty,
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "features.csv missing (CSV required; no jsonl converter)",
            "path": str(root),
        }
    parsed = read_prod_export_csv(csv_path, sql_path=sql_path, sql_pin=sql_pin)
    if parsed.get("status") != "OK":
        parsed["evidence_label"] = EVIDENCE_LABEL
        return parsed
    meta_path = root / "EXPORT.meta.json"
    if not meta_path.is_file():
        return {**empty, "status": "NOT_RUN_NO_PROD_EXPORT", "reason": "EXPORT.meta.json missing"}
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if str(meta.get("kind") or "") != PROD_EXPORT_KIND:
        return {
            **empty,
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "kind is not sealed_prod_feature_export (authored samples refused)",
            "meta": meta,
        }
    got = parsed.get("sha256")
    meta_sha = str(meta.get("sha256") or "").strip().lower()
    if not meta_sha:
        return {**empty, "status": "NOT_RUN_NO_PROD_EXPORT", "reason": "EXPORT_SHA_REQUIRED", "meta": meta}
    if meta_sha != str(got or "").lower():
        return {
            **empty,
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "EXPORT sha256 mismatch vs features.csv",
            "got": got,
            "expected": meta_sha,
            "meta": meta,
        }
    seal_sha_path = root / "EXPORT.sha256"
    if not seal_sha_path.is_file():
        return {**empty, "status": "NOT_RUN_NO_PROD_EXPORT", "reason": "EXPORT_SHA256_FILE_REQUIRED", "meta": meta}
    seal_sha = seal_sha_path.read_text(encoding="utf-8").strip().split()[0].lower()
    if not seal_sha:
        return {**empty, "status": "NOT_RUN_NO_PROD_EXPORT", "reason": "EXPORT_SHA256_FILE_REQUIRED", "meta": meta}
    if seal_sha != meta_sha:
        return {
            **empty,
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "EXPORT.sha256 mismatch vs meta.sha256",
            "got": seal_sha,
            "expected": meta_sha,
            "meta": meta,
        }
    captured = meta.get("captured_utc") or meta.get("capture_ts")
    data_as_of = meta.get("data_as_of") or meta.get("as_of") or meta.get("data_as_of_utc")
    query_sha = str(meta.get("query_sha") or meta.get("sql_sha") or "").strip().lower()
    missing = [k for k, v in (("captured_utc", captured), ("data_as_of", data_as_of), ("query_sha", query_sha)) if not v]
    if missing:
        return {
            **empty,
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "meta missing " + ",".join(missing),
            "meta": meta,
        }
    if query_sha != SQL_V3_PIN:
        return {
            **empty,
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "SQL_V3_SHA_MISMATCH",
            "got": query_sha,
            "expected": SQL_V3_PIN,
            "meta": meta,
        }
    cap_dt = parse_iso_utc(str(captured))
    build_dt = parse_iso_utc(build_started_utc)
    if cap_dt is None:
        return {**empty, "status": "NOT_RUN_NO_PROD_EXPORT", "reason": "captured_utc unparseable", "meta": meta}
    if build_dt is None:
        return {**empty, "status": "NOT_RUN_NO_PROD_EXPORT", "reason": "BUILD_STARTED_UTC_UNPARSEABLE", "meta": meta}
    if cap_dt > build_dt:
        return {
            "status": "FAIL_EXPORT_CAPTURED_AFTER_BUILD",
            "reason": "C-4 export captured_utc is after build start",
            "captured_utc": captured,
            "build_started_utc": build_started_utc,
            "rows": [],
            "meta": meta,
            "evidence_label": EVIDENCE_LABEL,
        }
    return {
        "status": "OK",
        "reason": None,
        "rows": parsed["rows"],
        "meta": meta,
        "path": parsed.get("path"),
        "sha256": got,
        "ruling": EXPORT_RULING,
        "captured_utc": captured,
        "data_as_of": data_as_of,
        "query_sha": query_sha,
        "build_started_utc": build_started_utc,
        "team_code": parsed.get("team_code"),
        "evidence_label": EVIDENCE_LABEL,
        "sql_pin": SQL_V3_PIN,
        "export_sha256_file": str(seal_sha_path),
    }


def _cmd_parity(args: argparse.Namespace) -> int:
    def load_jsonl(path: Path) -> List[Dict[str, Any]]:
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    export_dir = Path(args.prod_export) if str(args.prod_export or "").strip() else None
    build_started = (args.build_started or os.environ.get("IMV_BUILD_STARTED_UTC") or "").strip() or None
    export = load_prod_export(export_dir, build_started_utc=build_started)
    doc = parity_local_w_vs_prod_w_minus_1(
        load_jsonl(Path(args.local)),
        export,
        week_cap=int(args.week_cap),
        grade=str(args.grade or "cert"),
        build_started_utc=build_started,
    )
    print(json.dumps(doc, indent=2, default=str))
    if str(doc["status"]).startswith("NOT_RUN"):
        return 7
    return 0 if doc["status"] == "PASS" else 6


def _cmd_helpers(args: argparse.Namespace) -> int:
    rec = write_helper_stamps(Path(args.out), Path(args.imv_dir))
    print(json.dumps(rec, indent=2))
    return 0 if rec.get("ok") else 6


def _cmd_bundle(args: argparse.Namespace) -> int:
    rec = write_helper_bundle(Path(args.imv_dir), Path(args.out))
    print(json.dumps(rec, indent=2))
    return 0 if rec.get("ok") else 6


def _cmd_pins(args: argparse.Namespace) -> int:
    rec = stamp_helper_shas(
        Path(args.imv_dir),
        sums_v25=Path(args.sums_v25) if str(args.sums_v25 or "").strip() else None,
        sums=Path(args.sums) if str(args.sums or "").strip() else None,
    )
    print(json.dumps(rec, indent=2))
    return 0 if rec.get("ok") else 6


def _cmd_sums(args: argparse.Namespace) -> int:
    rec = write_store_sha256sums_last(Path(args.store))
    print(json.dumps(rec, indent=2))
    return 0 if rec.get("ok") else 6


def _cmd_sql_pin(args: argparse.Namespace) -> int:
    rec = bind_prod_sql(
        sql_path=Path(args.sql) if str(args.sql or "").strip() else None,
        sql_pin=(args.pin or "").strip() or None,
    )
    print(json.dumps(rec, indent=2))
    return 0 if rec.get("ok") else 7


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="nfl_imv_v26")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("parity")
    p.add_argument("--local", required=True)
    p.add_argument("--prod-export", default="")
    p.add_argument("--week-cap", type=int, required=True)
    p.add_argument("--grade", default="cert", choices=("cert", "plumbing"))
    p.add_argument("--build-started", default="")
    p.set_defaults(func=_cmd_parity)
    h = sub.add_parser("stamp-helpers")
    h.add_argument("--imv-dir", required=True)
    h.add_argument("--out", required=True)
    h.set_defaults(func=_cmd_helpers)
    b = sub.add_parser("write-bundle")
    b.add_argument("--imv-dir", required=True)
    b.add_argument("--out", required=True)
    b.set_defaults(func=_cmd_bundle)
    c = sub.add_parser("check-pins")
    c.add_argument("--imv-dir", required=True)
    c.add_argument("--sums-v25", default="")
    c.add_argument("--sums", default="")
    c.set_defaults(func=_cmd_pins)
    s = sub.add_parser("write-store-sums")
    s.add_argument("--store", required=True)
    s.set_defaults(func=_cmd_sums)
    q = sub.add_parser("check-sql-pin")
    q.add_argument("--sql", default="")
    q.add_argument("--pin", default="")
    q.set_defaults(func=_cmd_sql_pin)
    args = parser.parse_args(argv)
    if args.cmd == "parity":
        args.prod_export = (args.prod_export or os.environ.get("IMV_PROD_EXPORT") or "").strip()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
