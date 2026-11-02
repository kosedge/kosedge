#!/usr/bin/env python3
"""IMV v2.5 reader (R-1..R-9) + C-3/C-4 close. Layer on frozen v21/v22/v23/v24.

Do not edit nfl_imv_v22.py, nfl_imv_v23.py, or the reviewed v24 pin.
v24 = 7c3f4dc7… (IMV v2.4 review 54ba672b).

R-1 outermost 41-col SELECT (not the 9-col CTE)
R-2 per-column types; bad cell → NOT_RUN; bool is t/f only
R-3 any roof_vocab_unknown row blocks cert PASS (NOT_RUN_ROOF_VOCAB)
R-4 rest raw = schedule_game_date − *_prev_reg_game_date; mismatch flags
R-5 exported schedule_dup / per-key count / row-count
R-6 FAIL_TEAM_CODE on STL/SD/OAK and unparseable game_id
R-7 refuse cert tolerance override
R-8 evidence_label REPORTED; plumbing status is PASS_PLUMBING
R-9 query_sha == v3 pin only; export sha required; build-start required
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import nfl_imv_v21 as v21
import nfl_imv_v24 as v24

RULING = "54ba672b"
PARITY_PROTOCOL = v24.PARITY_PROTOCOL
EXPORT_RULING = "v2.5-r1-r9"
SCRIPT_ID = "nfl-imv-v2.5"
EVIDENCE_LABEL = "REPORTED"
SQL_V3_PATH = v24.SQL_V3_PATH
SQL_V3_PIN = "b10d6cfd90b0586070c5a4ed3df5cd9782d2d7ad6e6145dcc3719f67a3d5e5c0"
SQL_V3_N_COLUMNS = 41
V21_PIN = v24.V21_PIN
V22_PIN = v24.V22_PIN
V23_PIN = v24.V23_PIN
V24_PIN = "7c3f4dc779f08f4c18fe60b4bf417f14a53f6c64eb7db2a0b843d0cb2ecd0c0e"
ROOF_AUDIT_COL = "roof_vocab_unknown"
RETIRED_TEAM_CODES = frozenset({"STL", "SD", "OAK"})
TEAM_ALIASES = {"LA": "LAR", "WSH": "WAS", "JAC": "JAX"}
NFL_32 = v24.NFL_32
BOOL_TRUE = frozenset({"t", "true"})
BOOL_FALSE = frozenset({"f", "false"})
REST_DERIVED_KEYS = ("home_rest_days", "away_rest_days")
REST_DATE_COLS = {
    "home_rest_days": "home_prev_reg_game_date",
    "away_rest_days": "away_prev_reg_game_date",
}
GAME_DATE_COL = "schedule_game_date"
DUP_COL = "schedule_dup_game_rows"
PER_KEY_COL = "export_distinct_week_game_count_per_key"
ROW_COUNT_COL = "export_row_count"
REQUIRED_V3_COLS = (
    "season",
    "week",
    "game_id",
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
    "diff_off_epa_5g",
    "home_rest_days",
    "away_rest_days",
    GAME_DATE_COL,
    "home_prev_reg_game_date",
    "away_prev_reg_game_date",
    "roof_dome",
    ROOF_AUDIT_COL,
    DUP_COL,
    PER_KEY_COL,
    ROW_COUNT_COL,
)
# Pinned 41-name order (v1 27 + IMV-named rest/audit + 7 FEATURE_KEYS).
# Live bind uses the outermost parsed SELECT; mismatch vs this tuple is
# SQL_V3_COLUMN_MISMATCH (NOT_RUN) until the file's aliases are confirmed.
PINNED_V3_COLUMNS: Tuple[str, ...] = (
    "season",
    "week",
    "game_id",
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
    "home_rest_days",
    "away_rest_days",
    "schedule_game_date",
    "home_prev_reg_game_date",
    "away_prev_reg_game_date",
    "roof_dome",
    "roof_vocab_unknown",
    "schedule_dup_game_rows",
    "export_distinct_week_game_count_per_key",
    "export_row_count",
    "diff_def_epa_allowed_5g",
    "diff_pressure_generated_5g",
    "diff_pressure_allowed_5g",
    "diff_red_zone_td_rate_5g",
    "diff_success_rate_5g",
    "diff_rest_days",
    "surface_turf",
)
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
    {GAME_DATE_COL, "home_prev_reg_game_date", "away_prev_reg_game_date"}
)
CSV_STR_COLS = frozenset({"game_id", "home_team", "away_team", "roof"})
CSV_BOOL_COLS = frozenset({ROOF_AUDIT_COL})
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
        "diff_def_epa_allowed_5g",
        "diff_pressure_generated_5g",
        "diff_pressure_allowed_5g",
        "diff_red_zone_td_rate_5g",
        "diff_success_rate_5g",
        "diff_rest_days",
        "surface_turf",
        "is_divisional_game",
    }
)
BUNDLE_HELPERS = (
    "nfl_imv_v21.py",
    "nfl_imv_v22.py",
    "nfl_imv_v23.py",
    "nfl_imv_v24.py",
    "nfl_imv_v25.py",
)
BUNDLE_SHELLS = (
    "nfl-imv-feature-build-v2.4.sh",
    "nfl-imv-sealed-v2.4.sh",
    "nfl-imv-prestage-nflverse.sh",
)
_SQL_BIND_OVERRIDE: Optional[Tuple[Path, str]] = None

parse_iso_utc = v24.parse_iso_utc
key_split = v24.key_split
write_store_sha256sums_last = v24.write_store_sha256sums_last
refuse_imv_inside_base = v24.refuse_imv_inside_base
map_roof_dome = v24.map_roof_dome
COVERAGE_MIN = v24.COVERAGE_MIN
PARITY_TOLERANCES_CERT = dict(v24.PARITY_TOLERANCES_CERT)
PARITY_TOLERANCES_PLUMBING = dict(v24.PARITY_TOLERANCES_PLUMBING)
PROD_EXPORT_KIND = v24.PROD_EXPORT_KIND
N_OF_14_COMPARABLE = v24.N_OF_14_COMPARABLE
SEPARATE_CHECK_KEYS = v24.SEPARATE_CHECK_KEYS
SOURCE_CHECK_KEYS = v24.SOURCE_CHECK_KEYS
INTERNAL_CHECK_KEYS = v24.INTERNAL_CHECK_KEYS
PARITY_TEAM_KEYS = v24.PARITY_TEAM_KEYS
WEEKLY_AVG_RULE = v24.WEEKLY_AVG_RULE


def configure_sql_bind(path: Optional[Path], pin: Optional[str]) -> None:
    global _SQL_BIND_OVERRIDE
    if path is None or not pin:
        _SQL_BIND_OVERRIDE = None
        v24.configure_sql_bind(None, None)
        return
    _SQL_BIND_OVERRIDE = (Path(path), str(pin).strip().lower())
    v24.configure_sql_bind(path, pin)


def _strip_sql_comments(sql_text: str) -> str:
    return "\n".join(raw.split("--", 1)[0] for raw in sql_text.splitlines())


def _select_alias(expr: str) -> str:
    text = " ".join(str(expr or "").split())
    match = re.search(r"\bAS\s+([A-Za-z_][A-Za-z0-9_]*)\s*$", text, re.I)
    if match:
        return match.group(1)
    token = text.split()[-1] if text else ""
    return token.split(".")[-1]


def _find_word(upper: str, word: str, start: int = 0) -> int:
    n = len(word)
    i = start
    while True:
        i = upper.find(word, i)
        if i < 0:
            return -1
        before = upper[i - 1] if i > 0 else " "
        after = upper[i + n] if i + n < len(upper) else " "
        if not before.isalnum() and before != "_" and not after.isalnum() and after != "_":
            return i
        i += n


def csv_columns_from_sql(sql_text: str) -> Tuple[str, ...]:
    """R-1: outermost / COPY SELECT list. Skip CTE SELECTs. Depth-aware FROM."""
    stripped = _strip_sql_comments(sql_text)
    upper = stripped.upper()
    copy_at = _find_word(upper, "COPY")
    target_depth = None
    if copy_at >= 0:
        paren = stripped.find("(", copy_at)
        if paren >= 0:
            target_depth = 1
            scan_from = paren
        else:
            scan_from = copy_at
    else:
        scan_from = 0
        target_depth = 0
    depth = 0
    i = 0
    main_start = None
    main_depth = None
    while i < len(upper):
        ch = stripped[i]
        if ch == "(":
            depth += 1
            i += 1
            continue
        if ch == ")":
            depth = max(0, depth - 1)
            i += 1
            continue
        if i < scan_from:
            i += 1
            continue
        if main_start is None:
            sel = _find_word(upper, "SELECT", i)
            if sel < 0:
                break
            # depth at sel
            d = 0
            for j, c in enumerate(stripped[:sel]):
                if c == "(":
                    d += 1
                elif c == ")":
                    d = max(0, d - 1)
            if target_depth is None or d == target_depth:
                main_start = sel + 6
                main_depth = d
                i = main_start
                continue
            i = sel + 6
            continue
        frm = _find_word(upper, "FROM", i)
        if frm < 0:
            break
        d = 0
        for j, c in enumerate(stripped[:frm]):
            if c == "(":
                d += 1
            elif c == ")":
                d = max(0, d - 1)
        if d == main_depth:
            body = stripped[main_start:frm]
            return _split_select_aliases(body)
        i = frm + 4
    return tuple()


def _split_select_aliases(body: str) -> Tuple[str, ...]:
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


def canon_team_code(team: Optional[str]) -> str:
    raw = (team or "").strip().upper()
    if raw in RETIRED_TEAM_CODES:
        return raw
    mapped = v21.canon_team(raw)
    return TEAM_ALIASES.get(mapped, mapped)


def raw_team_code(team: Optional[str]) -> str:
    return (team or "").strip().upper()


def parse_game_id_teams(game_id: Optional[str]) -> Optional[Tuple[str, str]]:
    text = str(game_id or "").strip()
    if not text:
        return None
    product = v24.GAME_ID_PRODUCT.match(text)
    if product:
        return canon_team_code(product.group(1)), canon_team_code(product.group(2))
    under = v24.GAME_ID_UNDERSCORE.match(text)
    if under:
        return canon_team_code(under.group(2)), canon_team_code(under.group(3))
    return None


def team_code_check(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    fails: List[Dict[str, Any]] = []
    checked = 0
    for row in rows:
        try:
            season = int(row.get("season") or 0)
        except (TypeError, ValueError):
            season = 0
        gid = str(row.get("game_id") or row.get("game_id_product") or "")
        raw_home = raw_team_code(row.get("home_team"))
        raw_away = raw_team_code(row.get("away_team"))
        home = canon_team_code(raw_home)
        away = canon_team_code(raw_away)
        checked += 1
        if season >= 2020 and raw_home in RETIRED_TEAM_CODES:
            fails.append({"game_id": gid, "key": "home_team", "code": raw_home, "reason": "retired_team_code"})
        if season >= 2020 and raw_away in RETIRED_TEAM_CODES:
            fails.append({"game_id": gid, "key": "away_team", "code": raw_away, "reason": "retired_team_code"})
        if home not in NFL_32:
            fails.append({"game_id": gid, "key": "home_team", "code": home, "reason": "unknown_team_code"})
        if away not in NFL_32:
            fails.append({"game_id": gid, "key": "away_team", "code": away, "reason": "unknown_team_code"})
        if home and away and home == away:
            fails.append({"game_id": gid, "key": "home_away", "home": home, "away": away, "reason": "same_team"})
        parsed = parse_game_id_teams(gid)
        if parsed is None:
            fails.append({"game_id": gid, "key": "game_id", "reason": "unparseable_game_id"})
        else:
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


def _parse_date(raw: Any) -> Optional[date]:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    text = str(raw).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise ValueError(f"date {text!r}") from exc


def _parse_csv_cell(col: str, raw: Any) -> Any:
    text = "" if raw is None else str(raw).strip()
    if text == "":
        return None
    if col in CSV_INT_COLS:
        return int(text)
    if col in CSV_DATE_COLS:
        return _parse_date(text)
    if col in CSV_BOOL_COLS:
        token = text.lower()
        if token in BOOL_TRUE:
            return True
        if token in BOOL_FALSE:
            return False
        raise ValueError(f"{col} bool token {text!r} (t/f only)")
    if col in CSV_STR_COLS:
        return text
    if col in CSV_FLOAT_COLS or col.endswith("_5g") or col.startswith("diff_"):
        return float(text)
    raise ValueError(f"untyped column {col}")


def rest_days_from_dates(game_date: Any, prev_date: Any) -> Optional[int]:
    g = _parse_date(game_date)
    p = _parse_date(prev_date)
    if g is None or p is None:
        return None
    return int((g - p).days)


def rest_raw_derived_check(row: Mapping[str, Any]) -> Dict[str, Any]:
    flags: List[Dict[str, Any]] = []
    for derived_key in REST_DERIVED_KEYS:
        prev_col = REST_DATE_COLS[derived_key]
        derived = row.get(derived_key)
        recomputed = rest_days_from_dates(row.get(GAME_DATE_COL), row.get(prev_col))
        if row.get(prev_col) is None:
            flags.append(
                {
                    "key": derived_key,
                    "class": "SOURCE-CHECK",
                    "flag": "REST_RAW_DERIVED_MISMATCH",
                    "reason": "null_prev_reg_game_date",
                    "derived": derived,
                    "recomputed": None,
                }
            )
            continue
        if recomputed is None or derived is None or int(derived) != int(recomputed):
            flags.append(
                {
                    "key": derived_key,
                    "class": "SOURCE-CHECK",
                    "flag": "REST_RAW_DERIVED_MISMATCH",
                    "reason": "raw_derived_disagree",
                    "derived": derived,
                    "recomputed": recomputed,
                    "schedule_game_date": str(row.get(GAME_DATE_COL) or ""),
                    "prev": str(row.get(prev_col) or ""),
                }
            )
    return {"ok": not flags, "flags": flags}


def stamp_helper_shas(imv_dir: Path) -> Dict[str, Any]:
    rec = v24.stamp_helper_shas(imv_dir)
    root = Path(imv_dir)
    v24_got = v21.sha256_file(root / "nfl_imv_v24.py") if (root / "nfl_imv_v24.py").is_file() else None
    v25_got = v21.sha256_file(root / "nfl_imv_v25.py") if (root / "nfl_imv_v25.py").is_file() else None
    shells = {n: (v21.sha256_file(root / n) if (root / n).is_file() else None) for n in BUNDLE_SHELLS}
    flags = list(rec.get("flags") or [])
    if v24_got != V24_PIN:
        flags.append("HELPER_V24_SHA_MISMATCH")
    if v25_got is None:
        flags.append("HELPER_V25_MISSING")
    missing_shells = [n for n, sha in shells.items() if not sha]
    if missing_shells:
        flags.append("SHELL_FILE_MISSING")
    rec["v24"] = v24_got
    rec["v24_pin"] = V24_PIN
    rec["v25"] = v25_got
    rec["shells"] = shells
    rec["flags"] = flags
    rec["ok"] = not flags
    rec["flag"] = None if not flags else flags[0]
    rec["ruling"] = RULING
    return rec


def write_helper_stamps(out_dir: Path, imv_dir: Path) -> Dict[str, Any]:
    rec = stamp_helper_shas(imv_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "HELPER_V21.sha256").write_text((rec.get("v21") or "") + "\n", encoding="utf-8")
    (out / "HELPER_V22.sha256").write_text((rec.get("v22") or "") + "\n", encoding="utf-8")
    (out / "HELPER_V23.sha256").write_text((rec.get("v23") or "") + "\n", encoding="utf-8")
    (out / "HELPER_V24.sha256").write_text((rec.get("v24") or "") + "\n", encoding="utf-8")
    (out / "HELPER_V25.sha256").write_text((rec.get("v25") or "") + "\n", encoding="utf-8")
    (out / "HELPERS.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return rec


def write_helper_bundle(imv_dir: Path, dest: Path) -> Dict[str, Any]:
    rec = v24.write_helper_bundle(imv_dir, dest)
    src = Path(imv_dir)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    copied = list(rec.get("copied") or [])
    for name in ("nfl_imv_v25.py",) + BUNDLE_SHELLS + (
        "nfl-imv-mac-runbook-v2.4.1.md",
        "nfl-imv-v2.5-r-trace.md",
        "nfl-imv-feature-path-v2.5.md",
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
    """C-4 closed: v3 pin only, export sha required, build-start required."""
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
    if seal_sha_path.is_file():
        seal_sha = seal_sha_path.read_text(encoding="utf-8").strip().split()[0].lower()
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
    }


def _exact(a: Any, b: Any) -> bool:
    return v24._exact(a, b)


def _prod_game_index(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[int, str, str], Mapping[str, Any]]:
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
    prod_idx = _prod_game_index(prod_rows)
    fails: List[Dict[str, Any]] = []
    not_run: List[Dict[str, Any]] = []
    team_fails: List[Dict[str, Any]] = []
    rest_flags: List[Dict[str, Any]] = []
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
        raw_check = rest_raw_derived_check(prow)
        if not raw_check.get("ok"):
            rest_flags.extend([{"game_id": gid, **f} for f in raw_check.get("flags") or []])
            fails.extend([{"game_id": gid, **f} for f in raw_check.get("flags") or []])
        for key in REST_DERIVED_KEYS:
            rest_checked += 1
            if not _exact(lrow.get(key), prow.get(key)):
                fails.append(
                    {
                        "game_id": gid,
                        "key": key,
                        "class": "SOURCE-CHECK",
                        "local": lrow.get(key),
                        "prod": prow.get(key),
                        "reason": "exact_mismatch",
                    }
                )
        roof_flagged = bool(prow.get(ROOF_AUDIT_COL) is True or lrow.get(ROOF_AUDIT_COL) is True)
        if roof_flagged:
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
            roof_checked += 1
            if not _exact(lrow.get("roof_dome"), prow.get("roof_dome")):
                fails.append(
                    {
                        "game_id": gid,
                        "key": "roof_dome",
                        "class": "SOURCE-CHECK",
                        "local": lrow.get("roof_dome"),
                        "prod": prow.get("roof_dome"),
                        "reason": "exact_mismatch",
                    }
                )
    source_fails = [f for f in fails if f.get("class") == "SOURCE-CHECK" or f.get("key") == "same_game_join"]
    internal_fails = [f for f in fails if f.get("key") == "diff_off_epa_5g"]
    return {
        "keys": list(SEPARATE_CHECK_KEYS),
        "n_same_game_joined": checked,
        "n_identity_checked": identity_checked,
        "n_rest_checked": rest_checked,
        "n_roof_checked": roof_checked,
        "n_roof_not_run": roof_not_run,
        "n_fails": len(fails) + len(team_fails),
        "n_source_fails": len(source_fails),
        "n_internal_fails": len(internal_fails),
        "n_team_fails": len(team_fails),
        "perfect": not fails and not team_fails and identity_checked >= 1 and roof_not_run == 0,
        "source_perfect": not source_fails and checked >= 1 and roof_not_run == 0,
        "internal_perfect": not internal_fails and identity_checked >= 1,
        "team_perfect": not team_fails and identity_checked >= 1,
        "roof_blocks_cert": roof_not_run > 0,
        "fails": fails + team_fails,
        "not_run": not_run,
        "rest_raw_derived_flags": rest_flags,
        "team_code": local_team,
    }


def _reported(doc: Dict[str, Any], *, grade: str, plumbing_status: str) -> Dict[str, Any]:
    doc["evidence_label"] = EVIDENCE_LABEL
    doc["grade"] = grade
    doc["plumbing_status"] = plumbing_status
    doc["plumbing_pass_is_not_cert"] = True
    doc["ruling"] = RULING
    doc["protocol"] = PARITY_PROTOCOL
    return doc


def parity_local_w_vs_prod_w_minus_1(
    local_rows: Sequence[Mapping[str, Any]],
    export: Mapping[str, Any],
    *,
    week_cap: int,
    grade: str = "cert",
    build_started_utc: Optional[str] = None,
    tolerances: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    g = str(grade or "cert").strip().lower()
    if g not in {"cert", "plumbing"}:
        g = "cert"
    if g == "cert" and tolerances is not None:
        return _reported(
            {
                "status": "NOT_RUN_NO_PROD_EXPORT",
                "reason": "TOLERANCE_OVERRIDE_REFUSED",
                "week_cap": int(week_cap),
                "key_split": key_split(),
            },
            grade=g,
            plumbing_status="NOT_RUN",
        )
    if export.get("status") in {
        "FAIL_DUPLICATE_SCHEDULE_ROWS",
        "FAIL_TEAM_CODE",
        "FAIL_EXPORT_CAPTURED_AFTER_BUILD",
    }:
        return _reported(
            {
                "status": export.get("status"),
                "reason": export.get("reason"),
                "week_cap": int(week_cap),
                "key_split": key_split(),
                "team_code": export.get("team_code"),
            },
            grade=g,
            plumbing_status=str(export.get("status")),
        )
    if export.get("status") != "OK":
        return _reported(
            {
                "status": "NOT_RUN_NO_PROD_EXPORT",
                "reason": export.get("reason"),
                "week_cap": int(week_cap),
                "authored_samples_refused": True,
                "key_split": key_split(),
            },
            grade=g,
            plumbing_status="NOT_RUN",
        )
    tols = dict(PARITY_TOLERANCES_CERT if g == "cert" else PARITY_TOLERANCES_PLUMBING)
    team = v24.v23.parity_local_w_vs_prod_w_minus_1(
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
    if matched < 1:
        status = "FAIL_ZERO_MATCHED_ROWS"
    elif diffs:
        status = "FAIL_VALUE_MISMATCH"
    elif g == "cert":
        if coverage < COVERAGE_MIN:
            status = "FAIL_COVERAGE"
        elif separate.get("roof_blocks_cert"):
            status = "NOT_RUN_ROOF_VOCAB"
        elif not separate.get("source_perfect"):
            status = "FAIL_SOURCE_CHECK"
        elif not separate.get("internal_perfect"):
            status = "FAIL_INTERNAL_CHECK"
        elif not separate.get("team_perfect"):
            status = "FAIL_TEAM_CODE"
        else:
            status = "PASS"
    else:
        status = "PASS_PLUMBING" if not diffs and matched >= 1 else "FAIL_VALUE_MISMATCH"
    plumbing_status = (
        "PASS_PLUMBING"
        if (not diffs and matched >= 1)
        else status
    )
    return _reported(
        {
            "status": status,
            "week_cap": int(week_cap),
            "join": "local.week W team-side vs prod.week W-1 same team",
            "keys": list(PARITY_TEAM_KEYS),
            "comparable_of_14": N_OF_14_COMPARABLE,
            "key_split": key_split(),
            "tolerances": tols,
            "tolerances_cert": dict(PARITY_TOLERANCES_CERT),
            "tolerances_plumbing": dict(PARITY_TOLERANCES_PLUMBING),
            "compared_team_weeks": matched,
            "attempted_team_weeks": attempted,
            "coverage": coverage,
            "coverage_min": COVERAGE_MIN,
            "diffs": diffs,
            "separate": separate,
            "fails_on_zero_matched": True,
            "export_sha256": export.get("sha256"),
            "export_captured_utc": export.get("captured_utc"),
            "export_data_as_of": export.get("data_as_of"),
            "export_query_sha": export.get("query_sha"),
            "build_started_utc": build_started_utc or export.get("build_started_utc"),
            "weekly_avg_rule": WEEKLY_AVG_RULE,
        },
        grade=g,
        plumbing_status=plumbing_status if g == "cert" else status,
    )


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
    parser = argparse.ArgumentParser(prog="nfl_imv_v25")
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
