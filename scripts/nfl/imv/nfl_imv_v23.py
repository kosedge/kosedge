#!/usr/bin/env python3
"""IMV v2.3 (ccecea74). Small layer on v2.2. Do not run Mac/W7 from this checkout.

v2.2 PASS WITH CONDITIONS. Closed: X-1/X-8/X-9, X-2, X-4..X-7.
This file: P-1..P-5 + X-3 lagged parity against a genuine sealed prod export.

Weekly averaging (reconciled): CODE WINS.
  Unweighted mean of weekly rates over last N completed REG team-weeks.
  Play counts are summed for backbone sample size only — not rate weights.
  Docs that said "play-weighted averages" were wrong; v2.3 states the code rule.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import nfl_imv_v21 as v21
import nfl_imv_v22 as v22

RULING = "ccecea74"
SCRIPT_ID = "nfl-imv-v2.3"
CERT_CANDIDATE = v21.CERT_CANDIDATE
V21_PIN = "050271467cd38f5a174043c67f2df9622d7f0b8125f137b822f888846f4c561f"
W8_SEAL_DEADLINE_UTC = "2026-10-30T00:15:00Z"
W8_SEAL_DEADLINE_ET = "2026-10-29 20:15 ET"
PROD_EXPORT_KIND = "sealed_prod_feature_export"
WEEKLY_AVG_RULE = (
    "unweighted mean of weekly rates over last N completed REG team-weeks; "
    "play counts summed for backbone sample size only, not used as rate weights"
)
# Team-form keys compared local week W vs prod week W-1 (same team, either side).
PARITY_TEAM_KEYS = (
    "off_epa_5g",
    "def_epa_allowed_5g",
    "pass_rate_5g",
    "success_offense_5g",
    "pressure_allowed_5g",
)
SIDE_TO_TEAM = {
    "home_off_epa_5g": ("home", "off_epa_5g"),
    "away_off_epa_5g": ("away", "off_epa_5g"),
    "home_def_epa_allowed_5g": ("home", "def_epa_allowed_5g"),
    "away_def_epa_allowed_5g": ("away", "def_epa_allowed_5g"),
    "home_pass_rate_5g": ("home", "pass_rate_5g"),
    "away_pass_rate_5g": ("away", "pass_rate_5g"),
    "home_success_offense_5g": ("home", "success_offense_5g"),
    "away_success_offense_5g": ("away", "success_offense_5g"),
    "home_pressure_allowed_5g": ("home", "pressure_allowed_5g"),
    "away_pressure_allowed_5g": ("away", "pressure_allowed_5g"),
}
TEAM_FROM_SIDE = {
    "off_epa_5g": ("home_off_epa_5g", "away_off_epa_5g"),
    "def_epa_allowed_5g": ("home_def_epa_allowed_5g", "away_def_epa_allowed_5g"),
    "pass_rate_5g": ("home_pass_rate_5g", "away_pass_rate_5g"),
    "success_offense_5g": ("home_success_offense_5g", "away_success_offense_5g"),
    "pressure_allowed_5g": ("home_pressure_allowed_5g", "away_pressure_allowed_5g"),
}
# Plumbing-only tolerances. Not a certification bar.
PARITY_TOLERANCES = {
    "off_epa_5g": 0.02,
    "def_epa_allowed_5g": 0.02,
    "pass_rate_5g": 0.03,
    "success_offense_5g": 0.03,
    "pressure_allowed_5g": 0.03,
}

# Re-export runner names (v22 + v21).
parse_product_week = v22.parse_product_week
require_kickoff = v22.require_kickoff
record_as_of_check = v22.record_as_of_check
read_and_assert_hfa = v22.read_and_assert_hfa
model_execution_label = v22.model_execution_label
injury_allowed_flagged = v22.injury_allowed_flagged
injury_row_record = v22.injury_row_record
run_label = v22.run_label
assert_feature_store_pin = v22.assert_feature_store_pin
enforce_cap_pair = v22.enforce_cap_pair
build_feature_store = v22.build_feature_store
WINDOW_5G_RULE = v22.WINDOW_5G_RULE


def resolve_feature_store(root: Path) -> Path:
    """P-1: runner reads OUT/store when that directory holds features.jsonl."""
    root = Path(root)
    nested = root / "store"
    if nested.is_dir() and (nested / "features.jsonl").is_file():
        return nested
    return root


def stamp_helper_shas(imv_dir: Path) -> Dict[str, Any]:
    """P-3: both helpers. v21 must equal V21_PIN."""
    v21_path = Path(imv_dir) / "nfl_imv_v21.py"
    v22_path = Path(imv_dir) / "nfl_imv_v22.py"
    if not v21_path.is_file() or not v22_path.is_file():
        return {
            "ok": False,
            "flag": "HELPER_FILE_MISSING",
            "v21": None,
            "v22": None,
            "v21_pin": V21_PIN,
        }
    got21 = v21.sha256_file(v21_path)
    got22 = v21.sha256_file(v22_path)
    ok = got21.lower() == V21_PIN.lower()
    return {
        "ok": ok,
        "flag": None if ok else "HELPER_V21_SHA_MISMATCH",
        "v21": got21,
        "v22": got22,
        "v21_pin": V21_PIN,
        "v21_path": str(v21_path),
        "v22_path": str(v22_path),
        "v23": v21.sha256_file(Path(__file__).resolve()) if Path(__file__).is_file() else None,
    }


def write_helper_stamps(out_dir: Path, imv_dir: Path) -> Dict[str, Any]:
    rec = stamp_helper_shas(imv_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "HELPER_V21.sha256").write_text((rec.get("v21") or "") + "\n", encoding="utf-8")
    (out / "HELPER_V22.sha256").write_text((rec.get("v22") or "") + "\n", encoding="utf-8")
    (out / "HELPERS.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return rec


def w8_seal_window(now_utc: Optional[datetime] = None) -> Dict[str, Any]:
    """P-2: W8 seal must start before 2026-10-29 20:15 ET."""
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    deadline = datetime.fromisoformat(W8_SEAL_DEADLINE_UTC.replace("Z", "+00:00"))
    ok = now < deadline
    return {
        "ok": ok,
        "flag": None if ok else "W8_SEAL_AFTER_DEADLINE",
        "now_utc": now.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "deadline_utc": W8_SEAL_DEADLINE_UTC,
        "deadline_et": W8_SEAL_DEADLINE_ET,
        "exclude_kickoff_at_or_before_seal": True,
    }


def game_excluded_at_or_before_seal(kickoff_utc: Optional[str], seal_utc: str) -> bool:
    """P-2: drop any game whose kickoff is at or before the seal timestamp."""
    if not kickoff_utc:
        return False
    try:
        ko = datetime.fromisoformat(str(kickoff_utc).replace("Z", "+00:00"))
        se = datetime.fromisoformat(str(seal_utc).replace("Z", "+00:00"))
    except ValueError:
        return False
    return ko <= se


def refuse_blocked_build(build_report: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """P-5: BLOCKED feature build → no sealed run."""
    if not build_report:
        return {
            "ok": False,
            "flag": "BLOCKED_BUILD_REPORT_MISSING",
            "allow_sealed_run": False,
        }
    status = str(build_report.get("status") or "")
    if status == "BLOCKED":
        return {
            "ok": False,
            "flag": "BLOCKED_BUILD_NO_SEALED_RUN",
            "allow_sealed_run": False,
            "blocked": list(build_report.get("blocked") or []),
        }
    if status not in {"BUILT", "OK"}:
        return {
            "ok": False,
            "flag": "BLOCKED_BUILD_STATUS_UNKNOWN",
            "allow_sealed_run": False,
            "status": status,
        }
    return {"ok": True, "flag": None, "allow_sealed_run": True}


def missing_finals_blocked(missing: Sequence[str], not_final: Sequence[str]) -> Dict[str, Any]:
    """P-5: missing / non-final scores → BLOCKED. Do not invent."""
    miss, nf = list(missing), list(not_final)
    if miss or nf:
        return {
            "ok": False,
            "flag": "BLOCKED_MISSING_FINALS",
            "missing": miss,
            "not_final": nf,
            "rerun_is_new_snapshot": True,
        }
    return {"ok": True, "flag": None, "rerun_is_new_snapshot": True}


def load_prod_export(export_dir: Optional[Path]) -> Dict[str, Any]:
    """Genuine sealed prod export only. Authored samples are not accepted."""
    if export_dir is None:
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "IMV_PROD_EXPORT unset",
            "rows": [],
            "meta": None,
        }
    root = Path(export_dir)
    if not root.is_dir():
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "export dir missing",
            "path": str(root),
            "rows": [],
            "meta": None,
        }
    meta_path = root / "EXPORT.meta.json"
    data_path = root / "features.jsonl"
    if not data_path.is_file():
        alt = root / "matchup-features.jsonl"
        data_path = alt if alt.is_file() else data_path
    if not meta_path.is_file() or not data_path.is_file():
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "EXPORT.meta.json or features.jsonl missing",
            "path": str(root),
            "rows": [],
            "meta": None,
        }
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if str(meta.get("kind") or "") != PROD_EXPORT_KIND:
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "kind is not sealed_prod_feature_export (authored samples refused)",
            "path": str(root),
            "rows": [],
            "meta": meta,
        }
    for req in ("source", "query", "sha256", "weeks", "columns"):
        if not meta.get(req):
            return {
                "status": "NOT_RUN_NO_PROD_EXPORT",
                "reason": f"meta missing {req}",
                "path": str(root),
                "rows": [],
                "meta": meta,
            }
    got = v21.sha256_file(data_path)
    if got.lower() != str(meta["sha256"]).strip().lower():
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "EXPORT sha256 mismatch vs features.jsonl",
            "got": got,
            "expected": meta["sha256"],
            "rows": [],
            "meta": meta,
        }
    rows: List[Dict[str, Any]] = []
    for line in data_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    if not rows:
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": "export jsonl empty",
            "rows": [],
            "meta": meta,
        }
    return {
        "status": "OK",
        "reason": None,
        "rows": rows,
        "meta": meta,
        "path": str(data_path),
        "sha256": got,
    }


def _team_rates_from_matchup(row: Mapping[str, Any], side: str) -> Dict[str, Optional[float]]:
    prefix = "home_" if side == "home" else "away_"
    return {
        "off_epa_5g": v21.parse_num(row.get(prefix + "off_epa_5g")),
        "def_epa_allowed_5g": v21.parse_num(row.get(prefix + "def_epa_allowed_5g")),
        "pass_rate_5g": v21.parse_num(row.get(prefix + "pass_rate_5g")),
        "success_offense_5g": v21.parse_num(row.get(prefix + "success_offense_5g")),
        "pressure_allowed_5g": v21.parse_num(row.get(prefix + "pressure_allowed_5g")),
    }


def _prod_team_week_index(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[int, str], Dict[str, Optional[float]]]:
    idx: Dict[Tuple[int, str], Dict[str, Optional[float]]] = {}
    for row in rows:
        try:
            week = int(row.get("week") or 0)
        except (TypeError, ValueError):
            continue
        home = v21.canon_team(str(row.get("home_team") or ""))
        away = v21.canon_team(str(row.get("away_team") or ""))
        if home:
            idx[(week, home)] = _team_rates_from_matchup(row, "home")
        if away:
            idx[(week, away)] = _team_rates_from_matchup(row, "away")
    return idx


def parity_local_w_vs_prod_w_minus_1(
    local_rows: Sequence[Mapping[str, Any]],
    export: Mapping[str, Any],
    *,
    week_cap: int,
    tolerances: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    """X-3: local week W vs prod week W-1, team-form keys, explicit tolerances.

    Prod CURRENT ROW at week K includes week K. Local week W is lagged
    through W-1. Join is (team, prod.week == local.week - 1), not game_id.
    """
    if export.get("status") != "OK":
        return {
            "status": "NOT_RUN_NO_PROD_EXPORT",
            "reason": export.get("reason"),
            "week_cap": int(week_cap),
            "join": "local.week W team-side vs prod.week W-1 same team",
            "tolerances": dict(PARITY_TOLERANCES),
            "authored_samples_refused": True,
        }
    tols = dict(PARITY_TOLERANCES)
    if tolerances:
        tols.update({k: float(v) for k, v in tolerances.items()})
    local = list(v21.apply_week_cap(local_rows, week_cap))
    prod_idx = _prod_team_week_index(list(export.get("rows") or []))
    diffs: List[Dict[str, Any]] = []
    missing_prod: List[str] = []
    compared = 0
    for lrow in local:
        week = int(lrow["week"])
        gid = str(lrow.get("game_id_product") or lrow.get("game_id") or "")
        home = v21.canon_team(str(lrow.get("home_team") or ""))
        away = v21.canon_team(str(lrow.get("away_team") or ""))
        for side, team in (("home", home), ("away", away)):
            prow = prod_idx.get((week - 1, team))
            if prow is None:
                missing_prod.append(f"{gid}:{team}:prod_w{week - 1}")
                continue
            compared += 1
            for team_key in PARITY_TEAM_KEYS:
                local_col = TEAM_FROM_SIDE[team_key][0 if side == "home" else 1]
                lv = v21.parse_num(lrow.get(local_col))
                pv = prow.get(team_key)
                if lv is None and pv is None:
                    continue
                if lv is None or pv is None:
                    diffs.append(
                        {
                            "game_id": gid,
                            "team": team,
                            "local_week": week,
                            "prod_week": week - 1,
                            "key": team_key,
                            "local": lv,
                            "prod": pv,
                            "tol": tols[team_key],
                            "reason": "null_mismatch",
                        }
                    )
                    continue
                if abs(lv - pv) > tols[team_key]:
                    diffs.append(
                        {
                            "game_id": gid,
                            "team": team,
                            "local_week": week,
                            "prod_week": week - 1,
                            "key": team_key,
                            "local": lv,
                            "prod": pv,
                            "tol": tols[team_key],
                            "abs_delta": abs(lv - pv),
                        }
                    )
    if diffs:
        status = "FAIL_VALUE_MISMATCH"
    else:
        status = "PASS"
    return {
        "status": status,
        "week_cap": int(week_cap),
        "join": "local.week W team-side vs prod.week W-1 same team",
        "keys": list(PARITY_TEAM_KEYS),
        "n_keys": len(PARITY_TEAM_KEYS),
        "tolerances": tols,
        "compared_team_weeks": compared,
        "n_local": len(local),
        "missing_prod_team_week": missing_prod,
        "diffs": diffs,
        "fails_on_value_mismatch": True,
        "export_sha256": export.get("sha256"),
        "export_source": (export.get("meta") or {}).get("source"),
        "export_query": (export.get("meta") or {}).get("query"),
        "weekly_avg_rule": WEEKLY_AVG_RULE,
    }


def _cmd_parity(args: argparse.Namespace) -> int:
    def load_jsonl(path: Path) -> List[Dict[str, Any]]:
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    export_dir = Path(args.prod_export) if str(args.prod_export or "").strip() else None
    export = load_prod_export(export_dir)
    doc = parity_local_w_vs_prod_w_minus_1(
        load_jsonl(Path(args.local)),
        export,
        week_cap=int(args.week_cap),
    )
    print(json.dumps(doc, indent=2))
    if doc["status"] == "NOT_RUN_NO_PROD_EXPORT":
        return 7
    return 0 if doc["status"] == "PASS" else 6


def _cmd_helpers(args: argparse.Namespace) -> int:
    rec = write_helper_stamps(Path(args.out), Path(args.imv_dir))
    print(json.dumps(rec, indent=2))
    return 0 if rec.get("ok") else 6


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="nfl_imv_v23")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("parity")
    p.add_argument("--local", required=True)
    p.add_argument("--prod-export", default="")
    p.add_argument("--week-cap", type=int, required=True)
    p.set_defaults(func=_cmd_parity)
    h = sub.add_parser("stamp-helpers")
    h.add_argument("--imv-dir", required=True)
    h.add_argument("--out", required=True)
    h.set_defaults(func=_cmd_helpers)
    args = parser.parse_args(argv)
    if args.cmd == "parity":
        args.prod_export = (args.prod_export or os.environ.get("IMV_PROD_EXPORT") or "").strip()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
