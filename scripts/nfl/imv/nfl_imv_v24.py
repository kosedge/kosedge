#!/usr/bin/env python3
"""IMV v2.4 (47616a70 + c57032db + 73815046 + v3 SQL pin). Layer on frozen v21/v22/v23.

Do not edit nfl_imv_v22.py or nfl_imv_v23.py. Pins:
  v22 = 57a419b4…  (full V22_PIN)
  v23 = fe66b374…  (full V23_PIN)
Mismatch → BLOCK.

C-1 zero matched rows → FAIL
C-2 only 10 of 14 keys on the W vs W-1 team join; rest/roof/EPA-diff separate
C-3 cert tolerances (0.005) pre-registered, separate from plumbing
C-4 export requires captured_utc, data_as_of, query_sha; reject after build start
C-5 pin v22 + v23; BLOCK on mismatch
C-6 write store SHA256SUMS last

c57032db PASS (cert): zero OOT AND ≥1 matched team-week AND ≥90% coverage
AND 100% on separate-check keys.

73815046: native CSV reader (no converter). rest/roof = SOURCE-CHECK.
diff_off_epa = internal. 10 / 3 / 1 / 3 / 24 key split.

v3 SQL pin: ops/platform/PR_PROD_PARITY_EXPORT_v3.sql
  sha256 = b10d6cfd90b0586070c5a4ed3df5cd9782d2d7ad6e6145dcc3719f67a3d5e5c0
Missing file or sha mismatch → NOT_RUN. Do not invent the SQL bytes.
roof_vocab_unknown=true → that row's roof SOURCE-CHECK = NOT_RUN.
Rest raw + derived. Team-code consistency required.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import nfl_imv_v21 as v21
import nfl_imv_v22 as v22
import nfl_imv_v23 as v23

RULING = "47616a70"
PARITY_PROTOCOL = "c57032db"
EXPORT_RULING = "73815046"
SQL_V3_RULING = "v3-sql-pin"
SCRIPT_ID = "nfl-imv-v2.4"
SQL_V3_PATH = Path("/workspace/ops/platform/PR_PROD_PARITY_EXPORT_v3.sql")
SQL_V3_PIN = "b10d6cfd90b0586070c5a4ed3df5cd9782d2d7ad6e6145dcc3719f67a3d5e5c0"
SQL_V3_N_COLUMNS = 41
ROOF_AUDIT_COL = "roof_vocab_unknown"
CERT_CANDIDATE = v21.CERT_CANDIDATE
V21_PIN = v23.V21_PIN
V22_PIN = "57a419b42f743dafb590d3dff8b40b7f89769db04d38ce2f48453bc0f85b1843"
V23_PIN = "fe66b374905817b1e991bc7260554dc8c706d8a487baf4876bc04bc1436d0470"
V22_PIN_PREFIX = "57a419b4"
V23_PIN_PREFIX = "fe66b374"
W8_SEAL_DEADLINE_UTC = v23.W8_SEAL_DEADLINE_UTC
W8_SEAL_DEADLINE_ET = v23.W8_SEAL_DEADLINE_ET
PROD_EXPORT_KIND = v23.PROD_EXPORT_KIND
WEEKLY_AVG_RULE = v23.WEEKLY_AVG_RULE
PARITY_TEAM_KEYS = v23.PARITY_TEAM_KEYS
PARITY_KEYS_14 = v22.PARITY_KEYS
# C-2 / c57032db: 10 feature-parity keys. 73815046 reclassifies the rest.
SOURCE_CHECK_KEYS = (
    "home_rest_days",
    "away_rest_days",
    "roof_dome",
)
INTERNAL_CHECK_KEYS = ("diff_off_epa_5g",)
SEPARATE_CHECK_KEYS = SOURCE_CHECK_KEYS + INTERNAL_CHECK_KEYS
PARITY_FEATURE_KEYS = (
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
)
INJURY_NULL_KEYS = (
    "home_injury_impact",
    "away_injury_impact",
    "diff_injury_impact",
)
UNTESTED_KEYS = (
    "week",
    "home_pressure_generated_5g",
    "away_pressure_generated_5g",
    "home_early_down_pass_rate_5g",
    "away_early_down_pass_rate_5g",
    "home_red_zone_td_rate_5g",
    "away_red_zone_td_rate_5g",
    "home_success_defense_allowed_5g",
    "away_success_defense_allowed_5g",
    "diff_def_epa_allowed_5g",
    "diff_pressure_generated_5g",
    "diff_pressure_allowed_5g",
    "diff_red_zone_td_rate_5g",
    "diff_success_rate_5g",
    "home_kav_offense_5g",
    "away_kav_offense_5g",
    "home_kav_defense_5g",
    "away_kav_defense_5g",
    "home_kav_net_5g",
    "away_kav_net_5g",
    "diff_kav_net_5g",
    "diff_rest_days",
    "surface_turf",
    "is_divisional_game",
)
N_OF_14_COMPARABLE = 10
# Production columns come only from the pinned v3 SQL. Never invent the list.
CSV_COLUMNS: Tuple[str, ...] = ()
CSV_INT_COLS = frozenset({"season", "week"})
CSV_STR_COLS = frozenset(
    {"game_id", "home_team", "away_team", "roof", "roof_raw", "roof_vocab"}
)
CSV_BOOL_COLS = frozenset({ROOF_AUDIT_COL})
REST_DERIVED_KEYS = ("home_rest_days", "away_rest_days")
REST_RAW_ALIASES = {
    "home_rest_days": (
        "home_rest_days_raw",
        "home_rest_raw",
        "home_rest",
        "rest_days_home_raw",
        "rest_home_raw",
    ),
    "away_rest_days": (
        "away_rest_days_raw",
        "away_rest_raw",
        "away_rest",
        "rest_days_away_raw",
        "rest_away_raw",
    ),
}
ROOF_DOME_VOCAB = frozenset({"dome", "closed"})
ROOF_OPEN_VOCAB = frozenset({"outdoors", "open"})
NFL_32 = frozenset(
    {
        "ARI",
        "ATL",
        "BAL",
        "BUF",
        "CAR",
        "CHI",
        "CIN",
        "CLE",
        "DAL",
        "DEN",
        "DET",
        "GB",
        "HOU",
        "IND",
        "JAX",
        "KC",
        "LAC",
        "LAR",
        "LV",
        "MIA",
        "MIN",
        "NE",
        "NO",
        "NYG",
        "NYJ",
        "PHI",
        "PIT",
        "SEA",
        "SF",
        "TB",
        "TEN",
        "WAS",
    }
)
TEAM_ALIASES = {"LA": "LAR", "WSH": "WAS", "JAC": "JAX", "STL": "LAR", "SD": "LAC", "OAK": "LV"}
GAME_ID_UNDERSCORE = re.compile(r"^\d{4}_(\d{1,2})_([A-Za-z]{2,3})_([A-Za-z]{2,3})$")
GAME_ID_PRODUCT = re.compile(r"^\d{4}-W\d{2}-([A-Za-z]{2,3})@([A-Za-z]{2,3})$")
BOOL_TRUE = frozenset({"true", "t", "1", "yes", "y"})
BOOL_FALSE = frozenset({"false", "f", "0", "no", "n"})
_SQL_BIND_OVERRIDE: Optional[Tuple[Path, str]] = None
COVERAGE_MIN = 0.90
# C-3: plumbing (v2.3) vs pre-registered cert (c57032db).
PARITY_TOLERANCES_PLUMBING = dict(v23.PARITY_TOLERANCES)
PARITY_TOLERANCES_CERT = {
    "off_epa_5g": 0.005,
    "def_epa_allowed_5g": 0.005,
    "pass_rate_5g": 0.005,
    "success_offense_5g": 0.005,
    "pressure_allowed_5g": 0.005,
}
BUNDLE_HELPERS = (
    "nfl_imv_v21.py",
    "nfl_imv_v22.py",
    "nfl_imv_v23.py",
    "nfl_imv_v24.py",
)
BUNDLE_DOCS = (
    "README.md",
    "nfl-imv-feature-path-v2.md",
    "nfl-imv-feature-path-v2.1.md",
    "nfl-imv-feature-path-v2.2.md",
    "nfl-imv-feature-path-v2.3.md",
    "nfl-imv-feature-path-v2.4.md",
    "nfl-imv-parity-protocol-c57032db.md",
    "nfl-imv-deviation-register-t4149u.md",
    "nfl-imv-mac-runbook-v2.4.md",
    "nfl-imv-v2.4-c-trace.md",
    "nfl-imv-prod-export-spec-v2.4.md",
    "PR_PROD_PARITY_EXPORT_v1.sql",
    "PR_PROD_PARITY_EXPORT_v3.sha256",
)

# Re-export runner names.
parse_product_week = v23.parse_product_week
require_kickoff = v23.require_kickoff
record_as_of_check = v23.record_as_of_check
read_and_assert_hfa = v23.read_and_assert_hfa
model_execution_label = v23.model_execution_label
injury_allowed_flagged = v23.injury_allowed_flagged
injury_row_record = v23.injury_row_record
run_label = v23.run_label
assert_feature_store_pin = v23.assert_feature_store_pin
enforce_cap_pair = v23.enforce_cap_pair
build_feature_store = v23.build_feature_store
resolve_feature_store = v23.resolve_feature_store
w8_seal_window = v23.w8_seal_window
game_excluded_at_or_before_seal = v23.game_excluded_at_or_before_seal
refuse_blocked_build = v23.refuse_blocked_build
missing_finals_blocked = v23.missing_finals_blocked
WINDOW_5G_RULE = v23.WINDOW_5G_RULE


def parse_iso_utc(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def refuse_imv_inside_base(imv_dir: Path, base: Path) -> Dict[str, Any]:
    """Returned runbook (1): helpers live outside BASE, never copied into $BASE/scripts."""
    imv = Path(imv_dir).resolve()
    root = Path(base).resolve()
    inside = False
    try:
        imv.relative_to(root)
        inside = True
    except ValueError:
        inside = False
    return {
        "ok": not inside,
        "flag": "IMV_DIR_INSIDE_BASE" if inside else None,
        "imv_dir": str(imv),
        "base": str(root),
    }


def stamp_helper_shas(imv_dir: Path) -> Dict[str, Any]:
    """C-5: v21 + v22=57a419b4… + v23=fe66b374…. BLOCK on mismatch."""
    root = Path(imv_dir)
    paths = {name: root / name for name in BUNDLE_HELPERS}
    missing = [n for n, p in paths.items() if not p.is_file()]
    got = {n: (v21.sha256_file(p) if p.is_file() else None) for n, p in paths.items()}
    flags: List[str] = []
    if missing:
        flags.append("HELPER_FILE_MISSING")
    if got.get("nfl_imv_v21.py") != V21_PIN:
        flags.append("HELPER_V21_SHA_MISMATCH")
    if got.get("nfl_imv_v22.py") != V22_PIN:
        flags.append("HELPER_V22_SHA_MISMATCH")
    if got.get("nfl_imv_v23.py") != V23_PIN:
        flags.append("HELPER_V23_SHA_MISMATCH")
    v22_got = got.get("nfl_imv_v22.py") or ""
    v23_got = got.get("nfl_imv_v23.py") or ""
    if v22_got and not v22_got.startswith(V22_PIN_PREFIX):
        flags.append("HELPER_V22_PREFIX_MISMATCH")
    if v23_got and not v23_got.startswith(V23_PIN_PREFIX):
        flags.append("HELPER_V23_PREFIX_MISMATCH")
    ok = not flags
    return {
        "ok": ok,
        "flag": None if ok else flags[0],
        "flags": flags,
        "v21": got.get("nfl_imv_v21.py"),
        "v22": got.get("nfl_imv_v22.py"),
        "v23": got.get("nfl_imv_v23.py"),
        "v24": got.get("nfl_imv_v24.py"),
        "v21_pin": V21_PIN,
        "v22_pin": V22_PIN,
        "v23_pin": V23_PIN,
        "v22_pin_prefix": V22_PIN_PREFIX,
        "v23_pin_prefix": V23_PIN_PREFIX,
        "missing": missing,
        "ruling": RULING,
    }


def write_helper_stamps(out_dir: Path, imv_dir: Path) -> Dict[str, Any]:
    rec = stamp_helper_shas(imv_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "HELPER_V21.sha256").write_text((rec.get("v21") or "") + "\n", encoding="utf-8")
    (out / "HELPER_V22.sha256").write_text((rec.get("v22") or "") + "\n", encoding="utf-8")
    (out / "HELPER_V23.sha256").write_text((rec.get("v23") or "") + "\n", encoding="utf-8")
    (out / "HELPERS.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return rec


def write_helper_bundle(imv_dir: Path, dest: Path) -> Dict[str, Any]:
    """Copy every imported helper + feature-path docs + README into dest."""
    src = Path(imv_dir)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    copied: List[str] = []
    missing: List[str] = []
    for name in BUNDLE_HELPERS + BUNDLE_DOCS:
        fp = src / name
        if not fp.is_file():
            missing.append(name)
            continue
        shutil.copy2(fp, dest / name)
        copied.append(name)
    rec = stamp_helper_shas(src)
    rec["copied"] = copied
    rec["bundle_missing"] = missing
    rec["bundle_dir"] = str(dest)
    (dest / "BUNDLE.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return rec


def write_store_sha256sums_last(store: Path) -> Dict[str, Any]:
    """C-6: SHA256SUMS is the last file written in the store."""
    store = Path(store)
    if not store.is_dir():
        return {"ok": False, "flag": "STORE_MISSING", "path": str(store)}
    sums = store / "SHA256SUMS"
    if sums.exists():
        sums.unlink()
    names = sorted(p.name for p in store.iterdir() if p.is_file() and p.name != "SHA256SUMS")
    with sums.open("w", encoding="utf-8") as fh:
        for name in names:
            fh.write(f"{v21.sha256_file(store / name)}  {name}\n")
    # Confirm nothing was written after SHA256SUMS in this function.
    return {
        "ok": True,
        "flag": None,
        "path": str(sums),
        "n_files": len(names),
        "sha256": v21.sha256_file(sums),
        "written_last": True,
    }


def configure_sql_bind(path: Optional[Path], pin: Optional[str]) -> None:
    """Test-only override. Production always uses SQL_V3_PATH + SQL_V3_PIN."""
    global _SQL_BIND_OVERRIDE
    if path is None or not pin:
        _SQL_BIND_OVERRIDE = None
        return
    _SQL_BIND_OVERRIDE = (Path(path), str(pin).strip().lower())


def _select_alias(expr: str) -> str:
    text = " ".join(str(expr or "").split())
    match = re.search(r"\bAS\s+([A-Za-z_][A-Za-z0-9_]*)\s*$", text, re.I)
    if match:
        return match.group(1)
    token = text.split()[-1] if text else ""
    return token.split(".")[-1]


def csv_columns_from_sql(sql_text: str) -> Tuple[str, ...]:
    """Ordered SELECT aliases from the pinned v3 SQL (CASE AS name safe)."""
    stripped = "\n".join(raw.split("--", 1)[0] for raw in sql_text.splitlines())
    upper = stripped.upper()
    start = upper.find("SELECT")
    end = upper.find("FROM", start + 6) if start >= 0 else -1
    if start < 0 or end < 0:
        return tuple()
    body = stripped[start + 6 : end]
    cols: List[str] = []
    buf: List[str] = []
    depth = 0
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            piece = "".join(buf).strip()
            if piece:
                cols.append(_select_alias(piece))
            buf = []
        else:
            buf.append(ch)
    piece = "".join(buf).strip()
    if piece:
        cols.append(_select_alias(piece))
    return tuple(c for c in cols if c)


def bind_prod_sql(
    sql_path: Optional[Path] = None,
    sql_pin: Optional[str] = None,
) -> Dict[str, Any]:
    """Pin v3 SQL. Missing file or sha mismatch → NOT_RUN. Do not invent bytes."""
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
        "ruling": SQL_V3_RULING,
        "export_ruling": EXPORT_RULING,
    }
    if not path.is_file():
        return {
            **base,
            "ok": False,
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "SQL_V3_MISSING",
        }
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
    if ROOF_AUDIT_COL not in cols:
        return {
            **base,
            "ok": False,
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "SQL_V3_MISSING_ROOF_AUDIT_COL",
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


def canon_team_code(team: Optional[str]) -> str:
    raw = v21.canon_team(str(team or ""))
    return TEAM_ALIASES.get(raw, raw)


def map_roof_dome(raw: Any) -> Optional[float]:
    """dome/closed → 1; outdoors/open → 0; anything else → NULL."""
    if raw is None:
        return None
    text = str(raw).strip()
    if text == "":
        return None
    token = text.lower()
    if token in ROOF_DOME_VOCAB:
        return 1.0
    if token in ROOF_OPEN_VOCAB:
        return 0.0
    return None


def roof_vocab_unknown_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    text = str(value).strip().lower()
    return text in BOOL_TRUE


def rest_values(row: Mapping[str, Any], derived_key: str) -> Dict[str, Any]:
    derived = row.get(derived_key)
    raw = None
    raw_col = None
    for alias in REST_RAW_ALIASES.get(derived_key, ()):
        if alias in row:
            raw_col = alias
            raw = row.get(alias)
            break
    value = derived if derived is not None else raw
    return {
        "derived": derived,
        "raw": raw,
        "raw_col": raw_col,
        "value": value,
    }


def parse_game_id_teams(game_id: Optional[str]) -> Optional[Tuple[str, str]]:
    text = str(game_id or "").strip()
    if not text:
        return None
    product = GAME_ID_PRODUCT.match(text)
    if product:
        return canon_team_code(product.group(1)), canon_team_code(product.group(2))
    under = GAME_ID_UNDERSCORE.match(text)
    if under:
        return canon_team_code(under.group(2)), canon_team_code(under.group(3))
    return None


def team_code_check(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """home/away must be the 32-team set after alias; game_id must agree."""
    fails: List[Dict[str, Any]] = []
    checked = 0
    for row in rows:
        home = canon_team_code(str(row.get("home_team") or ""))
        away = canon_team_code(str(row.get("away_team") or ""))
        gid = str(row.get("game_id") or row.get("game_id_product") or "")
        checked += 1
        if home not in NFL_32:
            fails.append({"game_id": gid, "key": "home_team", "code": home, "reason": "unknown_team_code"})
        if away not in NFL_32:
            fails.append({"game_id": gid, "key": "away_team", "code": away, "reason": "unknown_team_code"})
        if home and away and home == away:
            fails.append({"game_id": gid, "key": "home_away", "home": home, "away": away, "reason": "same_team"})
        parsed = parse_game_id_teams(gid)
        if parsed is not None:
            # product: away@home; underscore nflverse: away_home
            gid_away, gid_home = parsed
            if gid_home != home or gid_away != away:
                fails.append(
                    {
                        "game_id": gid,
                        "key": "game_id_teams",
                        "home": home,
                        "away": away,
                        "game_id_home": gid_home,
                        "game_id_away": gid_away,
                        "reason": "game_id_team_mismatch",
                    }
                )
    ok = not fails
    return {
        "ok": ok,
        "status": "OK" if ok else "FAIL_TEAM_CODE",
        "n_checked": checked,
        "n_fails": len(fails),
        "fails": fails,
    }


def _parse_csv_cell(col: str, raw: str) -> Any:
    text = "" if raw is None else str(raw).strip()
    if text == "":
        return None
    if col in CSV_INT_COLS:
        return int(text)
    if col in CSV_BOOL_COLS:
        token = text.lower()
        if token in BOOL_TRUE:
            return True
        if token in BOOL_FALSE:
            return False
        return text
    if col in CSV_STR_COLS:
        return text
    try:
        return float(text)
    except ValueError:
        return text


def read_prod_export_csv(
    csv_path: Path,
    *,
    sql_path: Optional[Path] = None,
    sql_pin: Optional[str] = None,
) -> Dict[str, Any]:
    """73815046 + v3 pin: native CSV. Header + types. Sha mismatch → NOT_RUN."""
    bound = bind_prod_sql(sql_path=sql_path, sql_pin=sql_pin)
    if not bound.get("ok"):
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": bound.get("reason") or "SQL_V3_MISSING",
            "sql": bound,
            "rows": [],
            "ruling": EXPORT_RULING,
            "sql_pin": SQL_V3_PIN,
        }
    expected = tuple(bound.get("columns") or ())
    if not csv_path.is_file():
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "features.csv missing (CSV required; no converter)",
            "rows": [],
            "ruling": EXPORT_RULING,
            "sql_pin": bound.get("sha256"),
        }
    text = csv_path.read_text(encoding="utf-8")
    if not text.strip():
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "empty CSV",
            "rows": [],
            "ruling": EXPORT_RULING,
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
        }
    header = [h.strip() for h in header]
    if not header:
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "CSV header required",
            "rows": [],
            "ruling": EXPORT_RULING,
        }
    unknown = [c for c in header if c not in expected]
    missing = [c for c in expected if c not in header]
    if unknown or missing or list(header) != list(expected):
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "CSV columns missing or unknown vs PR_PROD_PARITY_EXPORT_v3.sql",
            "unknown": unknown,
            "missing": missing,
            "header": header,
            "expected": list(expected),
            "rows": [],
            "ruling": EXPORT_RULING,
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
            }
        rec: Dict[str, Any] = {}
        try:
            for col, cell in zip(header, cells):
                rec[col] = _parse_csv_cell(col, cell)
            if rec.get("roof_dome") is None and rec.get("roof") is not None:
                rec["roof_dome"] = map_roof_dome(rec.get("roof"))
            elif isinstance(rec.get("roof_dome"), str):
                rec["roof_dome"] = map_roof_dome(rec.get("roof_dome"))
        except (TypeError, ValueError) as exc:
            return {
                "status": "NOT_RUN_NO_PROD_EXPORT",
                "reason": f"CSV type error row {i}: {exc}",
                "rows": [],
                "ruling": EXPORT_RULING,
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
        }
    dups = [k for k, n in seen.items() if n > 1]
    if dups:
        return {
            "status": "FAIL_DUPLICATE_SCHEDULE_ROWS",
            "reason": "duplicate schedule rows in export CSV",
            "duplicates": [list(k) for k in dups],
            "rows": [],
            "ruling": EXPORT_RULING,
            "sql_pin": bound.get("sha256"),
        }
    teams = team_code_check(rows)
    if not teams.get("ok"):
        return {
            "status": "FAIL_TEAM_CODE",
            "reason": "team-code consistency failed on export CSV",
            "team_code": teams,
            "rows": [],
            "ruling": EXPORT_RULING,
            "sql_pin": bound.get("sha256"),
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
    }


def load_prod_export(
    export_dir: Optional[Path],
    *,
    build_started_utc: Optional[str] = None,
    sql_path: Optional[Path] = None,
    sql_pin: Optional[str] = None,
) -> Dict[str, Any]:
    """C-4 + 73815046 CSV (no converter). v3 SQL pin; reject post-build."""
    bound = bind_prod_sql(sql_path=sql_path, sql_pin=sql_pin)
    if not bound.get("ok"):
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": bound.get("reason") or "SQL_V3_MISSING",
            "sql": bound,
            "rows": [],
            "meta": None,
            "ruling": EXPORT_RULING,
            "sql_pin": SQL_V3_PIN,
        }
    if export_dir is None:
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "IMV_PROD_EXPORT unset",
            "rows": [],
            "meta": None,
            "ruling": EXPORT_RULING,
        }
    root = Path(export_dir)
    csv_path = root / "features.csv"
    if not csv_path.is_file():
        alt = root / "export.csv"
        csv_path = alt if alt.is_file() else csv_path
    if not csv_path.is_file():
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "features.csv missing (CSV required; no jsonl converter)",
            "path": str(root),
            "rows": [],
            "ruling": EXPORT_RULING,
        }
    parsed = read_prod_export_csv(csv_path, sql_path=sql_path, sql_pin=sql_pin)
    if parsed.get("status") != "OK":
        return parsed
    meta_path = root / "EXPORT.meta.json"
    meta: Dict[str, Any] = {}
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if str(meta.get("kind") or "") != PROD_EXPORT_KIND:
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "kind is not sealed_prod_feature_export (authored samples refused)",
            "path": str(root),
            "rows": [],
            "meta": meta,
            "ruling": EXPORT_RULING,
        }
    base = {
        "status": "OK",
        "reason": None,
        "rows": parsed["rows"],
        "meta": meta,
        "path": parsed.get("path"),
        "sha256": parsed.get("sha256"),
        "ruling": EXPORT_RULING,
    }
    got = parsed.get("sha256")
    if meta.get("sha256") and str(meta["sha256"]).strip().lower() != str(got or "").lower():
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "EXPORT sha256 mismatch vs features.csv",
            "got": got,
            "expected": meta["sha256"],
            "rows": [],
            "meta": meta,
            "ruling": EXPORT_RULING,
        }
    meta = dict(base.get("meta") or {})
    captured = meta.get("captured_utc") or meta.get("capture_ts")
    data_as_of = meta.get("data_as_of") or meta.get("as_of") or meta.get("data_as_of_utc")
    query_sha = meta.get("query_sha") or meta.get("sql_sha")
    missing = []
    if not captured:
        missing.append("captured_utc")
    if not data_as_of:
        missing.append("data_as_of")
    if not query_sha:
        missing.append("query_sha")
    if missing:
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "meta missing " + ",".join(missing),
            "rows": [],
            "meta": meta,
            "c4_required": ["captured_utc", "data_as_of", "query_sha"],
        }
    query_text = str(meta.get("query") or "")
    if query_text:
        got_q = hashlib.sha256(query_text.encode("utf-8")).hexdigest()
        if str(query_sha).strip().lower() != got_q.lower():
            return {
                "status": "NOT_RUN_NO_PROD_EXPORT",
                "reason": "query_sha mismatch vs meta.query",
                "got": got_q,
                "expected": query_sha,
                "rows": [],
                "meta": meta,
            }
    pin = str(bound.get("sha256") or SQL_V3_PIN).strip().lower()
    qsha = str(query_sha or "").strip().lower()
    if qsha and qsha not in {pin, hashlib.sha256(query_text.encode("utf-8")).hexdigest()}:
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "SQL_V3_SHA_MISMATCH",
            "got": qsha,
            "expected": pin,
            "rows": [],
            "meta": meta,
        }
    cap_dt = parse_iso_utc(str(captured))
    build_dt = parse_iso_utc(build_started_utc)
    if cap_dt is None:
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "captured_utc unparseable",
            "rows": [],
            "meta": meta,
        }
    if build_dt is not None and cap_dt > build_dt:
        return {
            "status": "FAIL_EXPORT_CAPTURED_AFTER_BUILD",
            "reason": "C-4 export captured_utc is after build start",
            "captured_utc": captured,
            "build_started_utc": build_started_utc,
            "rows": [],
            "meta": meta,
        }
    base["captured_utc"] = captured
    base["data_as_of"] = data_as_of
    base["query_sha"] = query_sha
    base["build_started_utc"] = build_started_utc
    return base


def key_split() -> Dict[str, Any]:
    """73815046: 10 parity / 3 source-check / 1 internal / 3 injury null / 24 untested."""
    return {
        "parity": list(PARITY_FEATURE_KEYS),
        "source_check": list(SOURCE_CHECK_KEYS),
        "internal": list(INTERNAL_CHECK_KEYS),
        "injury_null": list(INJURY_NULL_KEYS),
        "untested": list(UNTESTED_KEYS),
        "n": {
            "parity": len(PARITY_FEATURE_KEYS),
            "source_check": len(SOURCE_CHECK_KEYS),
            "internal": len(INTERNAL_CHECK_KEYS),
            "injury_null": len(INJURY_NULL_KEYS),
            "untested": len(UNTESTED_KEYS),
            "total": (
                len(PARITY_FEATURE_KEYS)
                + len(SOURCE_CHECK_KEYS)
                + len(INTERNAL_CHECK_KEYS)
                + len(INJURY_NULL_KEYS)
                + len(UNTESTED_KEYS)
            ),
        },
    }


def _exact(a: Any, b: Any) -> bool:
    if a is None and b is None:
        return True
    na, nb = v21.parse_num(a), v21.parse_num(b)
    if na is not None and nb is not None:
        return abs(na - nb) <= 1e-12
    return str(a).strip() == str(b).strip()


def _prod_game_index(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[int, str, str], Mapping[str, Any]]:
    idx: Dict[Tuple[int, str, str], Mapping[str, Any]] = {}
    for row in rows:
        try:
            week = int(row.get("week") or 0)
        except (TypeError, ValueError):
            continue
        home = canon_team_code(str(row.get("home_team") or ""))
        away = canon_team_code(str(row.get("away_team") or ""))
        if home and away:
            idx[(week, home, away)] = row
    return idx


def _separate_game_checks(
    local_rows: Sequence[Mapping[str, Any]],
    prod_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """C-2 / c57032db: rest raw+derived + roof exact; roof_vocab_unknown → NOT_RUN."""
    prod_idx = _prod_game_index(prod_rows)
    fails: List[Dict[str, Any]] = []
    not_run: List[Dict[str, Any]] = []
    team_fails: List[Dict[str, Any]] = []
    checked = 0
    identity_checked = 0
    roof_checked = 0
    roof_not_run = 0
    rest_checked = 0
    local_team = team_code_check(local_rows)
    if not local_team.get("ok"):
        team_fails.extend(list(local_team.get("fails") or []))
    for lrow in local_rows:
        try:
            week = int(lrow.get("week") or 0)
        except (TypeError, ValueError):
            continue
        gid = str(lrow.get("game_id_product") or lrow.get("game_id") or "")
        home = canon_team_code(str(lrow.get("home_team") or ""))
        away = canon_team_code(str(lrow.get("away_team") or ""))
        ho = v21.parse_num(lrow.get("home_off_epa_5g"))
        ao = v21.parse_num(lrow.get("away_off_epa_5g"))
        diff = v21.parse_num(lrow.get("diff_off_epa_5g"))
        identity_checked += 1
        if ho is None or ao is None or diff is None or abs((ho - ao) - diff) > 1e-9:
            fails.append(
                {
                    "game_id": gid,
                    "key": "diff_off_epa_5g",
                    "class": "INTERNAL",
                    "reason": "not_home_minus_away",
                    "home_off_epa_5g": ho,
                    "away_off_epa_5g": ao,
                    "diff_off_epa_5g": diff,
                }
            )
        prow = prod_idx.get((week, home, away))
        if prow is None:
            fails.append(
                {
                    "game_id": gid,
                    "key": "same_game_join",
                    "reason": "missing_prod_same_game",
                    "week": week,
                    "home": home,
                    "away": away,
                }
            )
            continue
        checked += 1
        prod_home = canon_team_code(str(prow.get("home_team") or ""))
        prod_away = canon_team_code(str(prow.get("away_team") or ""))
        if prod_home != home or prod_away != away:
            team_fails.append(
                {
                    "game_id": gid,
                    "key": "team_code",
                    "class": "TEAM-CODE",
                    "reason": "local_vs_export_mismatch",
                    "local_home": home,
                    "local_away": away,
                    "prod_home": prod_home,
                    "prod_away": prod_away,
                }
            )
        for key in REST_DERIVED_KEYS:
            local_rest = rest_values(lrow, key)
            prod_rest = rest_values(prow, key)
            rest_checked += 1
            if not _exact(local_rest["value"], prod_rest["value"]):
                fails.append(
                    {
                        "game_id": gid,
                        "key": key,
                        "class": "SOURCE-CHECK",
                        "local": local_rest["value"],
                        "prod": prod_rest["value"],
                        "local_raw": local_rest["raw"],
                        "prod_raw": prod_rest["raw"],
                        "local_derived": local_rest["derived"],
                        "prod_derived": prod_rest["derived"],
                        "reason": "exact_mismatch",
                    }
                )
        if roof_vocab_unknown_true(prow.get(ROOF_AUDIT_COL)) or roof_vocab_unknown_true(
            lrow.get(ROOF_AUDIT_COL)
        ):
            roof_not_run += 1
            not_run.append(
                {
                    "game_id": gid,
                    "key": "roof_dome",
                    "class": "SOURCE-CHECK",
                    "status": "NOT_RUN",
                    "reason": "roof_vocab_unknown",
                }
            )
        else:
            local_roof = lrow.get("roof_dome")
            if local_roof is None and lrow.get("roof") is not None:
                local_roof = map_roof_dome(lrow.get("roof"))
            prod_roof = prow.get("roof_dome")
            if prod_roof is None and prow.get("roof") is not None:
                prod_roof = map_roof_dome(prow.get("roof"))
            elif isinstance(prod_roof, str):
                prod_roof = map_roof_dome(prod_roof)
            roof_checked += 1
            if not _exact(local_roof, prod_roof):
                fails.append(
                    {
                        "game_id": gid,
                        "key": "roof_dome",
                        "class": "SOURCE-CHECK",
                        "local": local_roof,
                        "prod": prod_roof,
                        "reason": "exact_mismatch",
                    }
                )
    source_fails = [f for f in fails if f.get("class") == "SOURCE-CHECK" or f.get("key") == "same_game_join"]
    internal_fails = [f for f in fails if f.get("key") == "diff_off_epa_5g"]
    n_required = identity_checked + rest_checked + roof_checked
    n_fail = len(fails) + len(team_fails)
    pct = 1.0 if n_required and n_fail == 0 else (0.0 if not n_required else max(0.0, 1.0 - n_fail / max(n_required, 1)))
    return {
        "keys": list(SEPARATE_CHECK_KEYS),
        "source_check_keys": list(SOURCE_CHECK_KEYS),
        "internal_check_keys": list(INTERNAL_CHECK_KEYS),
        "n_local": len(list(local_rows)),
        "n_same_game_joined": checked,
        "n_identity_checked": identity_checked,
        "n_rest_checked": rest_checked,
        "n_roof_checked": roof_checked,
        "n_roof_not_run": roof_not_run,
        "n_fails": n_fail,
        "n_source_fails": len(source_fails),
        "n_internal_fails": len(internal_fails),
        "n_team_fails": len(team_fails),
        "pct": pct,
        "perfect": n_fail == 0 and identity_checked >= 1,
        "source_perfect": len(source_fails) == 0 and checked >= 1,
        "internal_perfect": len(internal_fails) == 0 and identity_checked >= 1,
        "team_perfect": len(team_fails) == 0 and identity_checked >= 1,
        "fails": fails + team_fails,
        "not_run": not_run,
        "team_code": local_team,
        "rule": (
            "SOURCE-CHECK rest raw+derived and roof_dome exact vs export; "
            "roof_vocab_unknown=true → that row roof NOT_RUN; "
            "INTERNAL diff_off_epa == home-away; team codes must be NFL-32"
        ),
    }


def parity_local_w_vs_prod_w_minus_1(
    local_rows: Sequence[Mapping[str, Any]],
    export: Mapping[str, Any],
    *,
    week_cap: int,
    tolerances: Optional[Mapping[str, float]] = None,
    grade: str = "cert",
    build_started_utc: Optional[str] = None,
) -> Dict[str, Any]:
    """C-1/C-2/C-3 + c57032db. 10 keys vs prod W-1; rest/roof/diff separate."""
    if export.get("status") == "FAIL_DUPLICATE_SCHEDULE_ROWS":
        return {
            "status": "FAIL_DUPLICATE_SCHEDULE_ROWS",
            "reason": export.get("reason"),
            "week_cap": int(week_cap),
            "comparable_of_14": N_OF_14_COMPARABLE,
            "key_split": key_split(),
            "grade": grade,
            "protocol": PARITY_PROTOCOL,
            "export_ruling": EXPORT_RULING,
        }
    if export.get("status") == "FAIL_TEAM_CODE":
        return {
            "status": "FAIL_TEAM_CODE",
            "reason": export.get("reason"),
            "week_cap": int(week_cap),
            "team_code": export.get("team_code"),
            "comparable_of_14": N_OF_14_COMPARABLE,
            "key_split": key_split(),
            "grade": grade,
            "protocol": PARITY_PROTOCOL,
            "export_ruling": EXPORT_RULING,
        }
    if export.get("status") == "FAIL_EXPORT_CAPTURED_AFTER_BUILD":
        return {
            "status": "FAIL_EXPORT_CAPTURED_AFTER_BUILD",
            "reason": export.get("reason"),
            "week_cap": int(week_cap),
            "comparable_of_14": N_OF_14_COMPARABLE,
            "separate_keys": list(SEPARATE_CHECK_KEYS),
            "grade": grade,
        }
    if export.get("status") != "OK":
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": export.get("reason"),
            "week_cap": int(week_cap),
            "join": "local.week W team-side vs prod.week W-1 same team",
            "comparable_of_14": N_OF_14_COMPARABLE,
            "of_14_not_on_team_join": list(SEPARATE_CHECK_KEYS),
            "tolerances_plumbing": dict(PARITY_TOLERANCES_PLUMBING),
            "tolerances_cert": dict(PARITY_TOLERANCES_CERT),
            "grade": grade,
            "authored_samples_refused": True,
            "protocol": PARITY_PROTOCOL,
        }
    g = str(grade or "cert").strip().lower()
    if g not in {"cert", "plumbing"}:
        g = "cert"
    tols = dict(PARITY_TOLERANCES_CERT if g == "cert" else PARITY_TOLERANCES_PLUMBING)
    if tolerances:
        tols.update({k: float(v) for k, v in tolerances.items()})
    team = v23.parity_local_w_vs_prod_w_minus_1(
        local_rows, export, week_cap=week_cap, tolerances=tols
    )
    local = list(v21.apply_week_cap(local_rows, week_cap))
    attempted = 0
    for lrow in local:
        home = canon_team_code(str(lrow.get("home_team") or ""))
        away = canon_team_code(str(lrow.get("away_team") or ""))
        attempted += int(bool(home)) + int(bool(away))
    matched = int(team.get("compared_team_weeks") or 0)
    coverage = (matched / attempted) if attempted else 0.0
    separate = _separate_game_checks(local, list(export.get("rows") or []))
    diffs = list(team.get("diffs") or [])
    status = str(team.get("status") or "")
    # C-1: zero matched rows is FAIL even if there are no diffs.
    if matched < 1:
        status = "FAIL_ZERO_MATCHED_ROWS"
    elif diffs:
        status = "FAIL_VALUE_MISMATCH"
    elif g == "cert":
        if coverage < COVERAGE_MIN:
            status = "FAIL_COVERAGE"
        elif not separate.get("source_perfect"):
            status = "FAIL_SOURCE_CHECK"
        elif not separate.get("internal_perfect"):
            status = "FAIL_INTERNAL_CHECK"
        elif not separate.get("team_perfect"):
            status = "FAIL_TEAM_CODE"
        elif not separate.get("perfect"):
            status = "FAIL_SEPARATE_CHECKS"
        else:
            status = "PASS"
    else:
        # plumbing: C-1 already applied; value diffs already applied.
        status = "PASS" if not diffs and matched >= 1 else status
    return {
        "status": status,
        "week_cap": int(week_cap),
        "join": "local.week W team-side vs prod.week W-1 same team",
        "keys": list(PARITY_TEAM_KEYS),
        "n_keys": len(PARITY_TEAM_KEYS),
        "comparable_of_14": N_OF_14_COMPARABLE,
        "of_14_not_on_team_join": list(SEPARATE_CHECK_KEYS),
        "key_split": key_split(),
        "grade": g,
        "tolerances": tols,
        "tolerances_plumbing": dict(PARITY_TOLERANCES_PLUMBING),
        "tolerances_cert": dict(PARITY_TOLERANCES_CERT),
        "compared_team_weeks": matched,
        "attempted_team_weeks": attempted,
        "coverage": coverage,
        "coverage_min": COVERAGE_MIN,
        "n_local": len(local),
        "missing_prod_team_week": team.get("missing_prod_team_week"),
        "diffs": diffs,
        "separate": separate,
        "fails_on_value_mismatch": True,
        "fails_on_zero_matched": True,
        "pass_rule": (
            "zero OOT AND >=1 matched team-week AND coverage>=0.90 "
            "AND 100% separate-check keys"
            if g == "cert"
            else "zero OOT AND >=1 matched team-week (plumbing tols)"
        ),
        "export_sha256": export.get("sha256"),
        "export_source": (export.get("meta") or {}).get("source"),
        "export_query": (export.get("meta") or {}).get("query"),
        "export_captured_utc": export.get("captured_utc"),
        "export_data_as_of": export.get("data_as_of"),
        "export_query_sha": export.get("query_sha"),
        "build_started_utc": build_started_utc or export.get("build_started_utc"),
        "weekly_avg_rule": WEEKLY_AVG_RULE,
        "protocol": PARITY_PROTOCOL,
        "ruling": RULING,
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
    print(json.dumps(doc, indent=2))
    if doc["status"] == "NOT_RUN_NO_PROD_EXPORT":
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
    rec = stamp_helper_shas(Path(args.imv_dir))
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
    parser = argparse.ArgumentParser(prog="nfl_imv_v24")
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
