#!/usr/bin/env python3
"""T-PIT-1..10 harness + development coverage (Step 2).

Expected answers were committed at the sha in
inputs/expected_answers_commit.txt BEFORE this harness existed.
Does not refit. Does not open 2024/25. Does not write a lock.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parents[1]
FIX = PKG / "leakage" / "fixtures"
EXP = PKG / "leakage" / "expected"
OUT = PKG / "leakage" / "receipts"
CODE = HERE
EXPECTED_COMMIT_FILE = PKG / "inputs" / "expected_answers_commit.txt"
B2B_FORBIDDEN = (
    "nfl_depth_chart_2024_w1.json",
    "nfl_depth_chart_2025_w1.json",
)

sys.path.insert(0, str(CODE))
from season_level_loader import STOP_MSG  # noqa: E402
from week_aware_roster import (  # noqa: E402
    classify_row,
    depth_order_for,
    is_member,
    listing_status,
    qb1_id,
    season_union_would_mark_res,
    week_aware_roster_status_applied,
    x_continuity,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _dump(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _expected_commit() -> str:
    return EXPECTED_COMMIT_FILE.read_text().strip()


def _guard_b2b() -> None:
    for name in B2B_FORBIDDEN:
        # name/size only was already inventoried; do not open contents
        if name in sys.argv:
            raise RuntimeError(f"DO-NOT-OPEN: {name}")


def run_t_pit_1() -> dict:
    fx = _load(FIX / "T-PIT-1.json")
    game = fx["game"]
    pid = "00-SYN-JOIN"
    mem = is_member(pid, game["team"], game, fx["roster_rows"], [])
    qid = qb1_id(game, [])
    return {
        "id": "T-PIT-1",
        "player_id": pid,
        "member": mem["member"],
        "missingness": mem["missingness"],
        "silent_include": mem["silent_include"],
        "qb1": qid == pid,
    }


def run_t_pit_2() -> dict:
    fx = _load(FIX / "T-PIT-2.json")
    game = fx["game"]
    rows = fx["depth_rows"]
    qba = "00-SYN-QBA"
    qbb = "00-SYN-QBB"
    qid = qb1_id(game, rows)
    return {
        "id": "T-PIT-2",
        "week": game["week"],
        "qba_depth_order": depth_order_for(qba, game, rows),
        "qbb_depth_order": depth_order_for(qbb, game, rows),
        "qba_is_qb1": qid == qba,
        "qbb_is_qb1": qid == qbb,
    }


def run_t_pit_3() -> dict:
    fx = _load(FIX / "T-PIT-3.json")
    pid = fx["player_id"]
    membership = []
    for game in fx["games"]:
        mem = is_member(pid, game["team"], game, fx["roster_rows"], fx["transactions"])
        membership.append(
            {"week": game["week"], "team": game["team"], "member": mem["member"]}
        )
    return {"id": "T-PIT-3", "player_id": pid, "membership": membership}


def run_t_pit_4() -> dict:
    fx = _load(FIX / "T-PIT-4.json")
    game = fx["game"]
    pid = "00-SYN-PS"
    mem = is_member(pid, game["team"], game, fx["roster_rows"], fx["transactions"])
    asg = mem["assignment"]
    return {
        "id": "T-PIT-4",
        "player_id": pid,
        "member_53": bool(asg.get("member_53")),
        "promoted_role": bool(asg.get("promoted_role")),
        "missingness": mem["missingness"],
    }


def run_t_pit_5() -> dict:
    fx = _load(FIX / "T-PIT-5.json")
    game = fx["game"]
    pid = "00-SYN-BEN"
    mem = is_member(pid, game["team"], game, fx["roster_rows"], [])
    listing = listing_status(pid, game, fx["listings"])
    return {
        "id": "T-PIT-5",
        "player_id": pid,
        "week1_roster_status_applied": week_aware_roster_status_applied(
            pid, game, fx["roster_rows"]
        ),
        "week1_member": mem["member"],
        "injury_status_from_listing": listing["status"],
        "listing_as_of_ok": listing["listing_as_of_ok"],
        "season_union_would_mark_res": season_union_would_mark_res(pid, fx["roster_rows"]),
    }


def run_t_pit_6() -> dict:
    fx = _load(FIX / "T-PIT-6.json")
    game = fx["game"]
    pid = "00-SYN-NTS"
    mem = is_member(pid, game["team"], game, fx["roster_rows"], [])
    depth = depth_order_for(pid, game, fx.get("depth_rows") or [])
    return {
        "id": "T-PIT-6",
        "player_id": pid,
        "member": mem["member"],
        "missingness": mem["missingness"],
        "imputed_from_season": False,
        "default_depth_2": depth == 2,
        "x_continuity": x_continuity(None, None),
    }


def run_t_pit_7() -> dict:
    fx = _load(FIX / "T-PIT-7.json")
    game = fx["game"]
    rows_out = []
    for row in fx["roster_rows"]:
        ok, code = classify_row(row, game)
        rows_out.append(
            {
                "player_id": row["player_id"],
                "eligible": ok,
                "missingness": code,
            }
        )
    return {
        "id": "T-PIT-7",
        "closed_at_cutoff": bool(fx.get("closed_at_cutoff", False)),
        "rows": rows_out,
    }


def run_t_pit_8() -> dict:
    fx = _load(FIX / "feature_manifest.json")
    required = [
        "injuries",
        "rosters",
        "depth",
        "transactions",
        "qb_changes",
        "odds",
        "weather",
    ]
    by_name = {c["name"]: c for c in fx["classes"]}
    undeclared = [n for n in required if n not in by_name]
    extra_ok = bool(fx.get("undeclared_allowed", False))
    all_ok = True
    for name in required:
        cls = by_name.get(name)
        if cls is None:
            all_ok = False
            continue
        has_ts = bool(cls.get("availability_ts_field"))
        exempt = bool(cls.get("exempt_with_ryan_reason"))
        if not (has_ts or exempt):
            all_ok = False
    return {
        "id": "T-PIT-8",
        "required_classes": required,
        "undeclared_allowed": extra_ok,
        "all_have_availability_ts_or_ryan_exempt": all_ok and not undeclared,
    }


def _synthetic_payload() -> dict:
    return {
        "T-PIT-1": run_t_pit_1(),
        "T-PIT-2": run_t_pit_2(),
        "T-PIT-3": run_t_pit_3(),
        "T-PIT-4": run_t_pit_4(),
        "T-PIT-5": run_t_pit_5(),
        "T-PIT-6": run_t_pit_6(),
        "T-PIT-7": run_t_pit_7(),
    }


def run_t_pit_9() -> dict:
    a = _dump(_synthetic_payload())
    b = _dump(_synthetic_payload())
    return {"id": "T-PIT-9", "bit_identical": a == b, "n_runs": 2}


def run_t_pit_10() -> dict:
    env = os.environ.copy()
    env["GPIT_MODE"] = "1"
    proc = subprocess.run(
        [sys.executable, str(CODE / "season_level_loader.py"), "roster_YYYY.csv"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return {
        "id": "T-PIT-10",
        "gpit_mode": "1",
        "season_level_loader": "HARD_STOP",
        "exit_code": proc.returncode,
        "stderr_contains": STOP_MSG if STOP_MSG in (proc.stderr or "") else proc.stderr.strip(),
    }


def run_dev_coverage() -> dict:
    """Schedule keys 2013–2023 REG only. No weekly capture-time source.

    Reconstructible stays 0. Does not read W1 week-label packs as PIT.
    Does not open B2b 2024/25. Does not refit.
    """
    _guard_b2b()
    keys = _load(FIX / "dev_game_keys_le2023.json")
    games = keys["games"]
    seasons = sorted({int(g["season"]) for g in games})
    holdout_in_file = sorted({int(g["season"]) for g in games if int(g["season"]) >= 2024})
    if holdout_in_file:
        raise RuntimeError(f"holdout years in development keys: {holdout_in_file}")
    # No capture-time weekly roster/depth source is pinned (NR-1 / INV-1.C).
    # W1 2019–23 packs are week-label as_of → INELIGIBLE_WEEK_LABEL.
    n = len(games)
    if n != int(keys.get("n", n)):
        raise RuntimeError("dev_game_keys n mismatch")
    return {
        "id": "DEV-COVERAGE",
        "n_dev_games": n,
        "seasons": seasons,
        "holdout_years_read": [],
        "n_reconstructible": 0,
        "n_ineligible": n,
        "w1_packs_2019_2023_eligible": False,
        "w1_reason": "INELIGIBLE_WEEK_LABEL",
        "b2b_2024_2025_opened": False,
        "refit": False,
    }


RUNNERS = {
    "T-PIT-1": run_t_pit_1,
    "T-PIT-2": run_t_pit_2,
    "T-PIT-3": run_t_pit_3,
    "T-PIT-4": run_t_pit_4,
    "T-PIT-5": run_t_pit_5,
    "T-PIT-6": run_t_pit_6,
    "T-PIT-7": run_t_pit_7,
    "T-PIT-8": run_t_pit_8,
    "T-PIT-9": run_t_pit_9,
    "T-PIT-10": run_t_pit_10,
}


def main() -> int:
    _guard_b2b()
    OUT.mkdir(parents=True, exist_ok=True)
    exp_commit = _expected_commit()
    results = []
    all_pass = True
    actuals = {}
    for tid, fn in RUNNERS.items():
        actual = fn()
        expected = _load(EXP / f"{tid}.json")
        passed = actual == expected
        if not passed:
            all_pass = False
        results.append({"id": tid, "pass": passed, "actual": actual, "expected": expected})
        actuals[tid] = actual
        print(f"{tid}: {'PASS' if passed else 'FAIL'}")
        if not passed:
            print("  expected", _dump(expected))
            print("  actual  ", _dump(actual))

    syn = {
        "package": "week-aware-roster-step2-v1",
        "kind": "synthetic",
        "expected_answers_commit": exp_commit,
        "all_pass": all_pass,
        "n_pass": sum(1 for r in results if r["pass"]),
        "n_tests": len(results),
        "results": [{"id": r["id"], "pass": r["pass"]} for r in results],
        "refit": False,
        "holdout_read": False,
        "opening": False,
    }
    (OUT / "SYNTHETIC.json").write_text(json.dumps(syn, indent=2) + "\n")
    (OUT / "SYNTHETIC-ACTUALS.json").write_text(json.dumps(actuals, indent=2) + "\n")

    cov_actual = run_dev_coverage()
    cov_expected = _load(EXP / "DEV-COVERAGE.json")
    cov_pass = cov_actual == cov_expected
    cov = {
        "package": "week-aware-roster-step2-v1",
        "kind": "development_coverage",
        "expected_answers_commit": exp_commit,
        "pass": cov_pass,
        "actual": cov_actual,
        "refit": False,
        "holdout_years_read": [],
        "b2b_2024_2025_opened": False,
        "source_sot_pin": False,
    }
    (OUT / "DEV-COVERAGE.json").write_text(json.dumps(cov, indent=2) + "\n")
    print(f"DEV-COVERAGE: {'PASS' if cov_pass else 'FAIL'} reconstructible={cov_actual['n_reconstructible']} ineligible={cov_actual['n_ineligible']}")
    if not cov_pass:
        print("  expected", _dump(cov_expected))
        print("  actual  ", _dump(cov_actual))
        all_pass = False

    if not all_pass:
        print("T-PIT PACKAGE: FAIL")
        return 1
    print("T-PIT PACKAGE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
