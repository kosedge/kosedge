#!/usr/bin/env python3
"""T-PIT-1..10 harness + development coverage (Step 2 v2).

Expected answers were committed at the sha in
inputs/expected_answers_commit.txt BEFORE this harness existed.
Receipts are written by this file alone, including harness_commit
read from inputs/harness_commit.txt (D-1).

Does not refit. Does not open 2024/25. Does not write a lock.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parents[1]
FIX = PKG / "leakage" / "fixtures"
EXP = PKG / "leakage" / "expected"
OUT = PKG / "leakage" / "receipts"
CODE = HERE
EXPECTED_COMMIT_FILE = PKG / "inputs" / "expected_answers_commit.txt"
HARNESS_COMMIT_FILE = PKG / "inputs" / "harness_commit.txt"
CITED_FIT = CODE / "cited" / "run_injury_residual_fit.py"
CITED_BUILDER = CODE / "cited" / "holdout_frozen_row_builder.py"
REQUIRED_FIT = "8d188da27d3c9f802acdca76763e1ca05e714040cc5ea3722e4922853f28167c"
REQUIRED_BUILDER = "247744d23fef6f289e11da78523bdb007ada136f070916cf66a2bfee161e9cad"
STOP_MSG = "G-PIT STOP: season-level roster loader forbidden"
SUPERSEDED_MSG = "SUPERSEDED: season-level roster loader invoked without GPIT_MODE"
B2B_FORBIDDEN = (
    "nfl_depth_chart_2024_w1.json",
    "nfl_depth_chart_2025_w1.json",
)

sys.path.insert(0, str(CODE))
from week_aware_roster import (  # noqa: E402
    classify_row,
    defaulted_depth_2,
    depth_order_for,
    imputed_from_season,
    is_member,
    listing_status,
    qb1_id,
    roster_status_applied,
    season_union_would_mark_res,
    x_continuity,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _dump(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _expected_commit() -> str:
    return EXPECTED_COMMIT_FILE.read_text().strip()


def _harness_commit() -> str:
    return HARNESS_COMMIT_FILE.read_text().strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _guard_b2b() -> None:
    for name in B2B_FORBIDDEN:
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
    pid = fx["player_id"]
    out = {"id": "T-PIT-4", "player_id": pid}
    for case in fx["cases"]:
        mem = is_member(
            pid, case["game"]["team"], case["game"], fx["roster_rows"], case["transactions"]
        )
        asg = mem["assignment"]
        out[case["label"]] = {
            "member_53": bool(asg.get("member_53")),
            "promoted_role": bool(asg.get("promoted_role")),
            "missingness": mem["missingness"],
        }
    return out


def run_t_pit_5() -> dict:
    fx = _load(FIX / "T-PIT-5.json")
    game = fx["game"]
    pid = "00-SYN-BEN"
    mem = is_member(pid, game["team"], game, fx["roster_rows"], [])
    listing = listing_status(pid, game, fx["listings"])
    mutated = copy.deepcopy(fx["roster_rows"])
    mutated[0]["week"] = 1
    mutated[0]["game_type"] = "REG"
    mutated[0]["availability_ts"] = "2098-09-07T12:00:00+00:00"
    return {
        "id": "T-PIT-5",
        "player_id": pid,
        "week1_roster_status_applied": roster_status_applied(pid, game, fx["roster_rows"]),
        "mutated_eligible_res_applied": roster_status_applied(pid, game, mutated),
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
    current = [pid] if mem["member"] else None
    return {
        "id": "T-PIT-6",
        "player_id": pid,
        "member": mem["member"],
        "missingness": mem["missingness"],
        "imputed_from_season": imputed_from_season(pid, game, fx["roster_rows"], mem),
        "default_depth_2": defaulted_depth_2(pid, game, fx.get("depth_rows") or []),
        "x_continuity": x_continuity(current, None),
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
    src = (CODE / "week_aware_roster.py").read_text()
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
    live = {
        "injuries": "def listing_status" in src and "report_time" in src,
        "rosters": "def classify_row" in src and "availability_ts" in src,
        "depth": "def depth_order_for" in src and "availability_ts" in src,
        "transactions": "event_type" in src and "availability_ts" in src,
        "qb_changes": (CODE / "qb_changes.py").is_file(),
        "odds": (CODE / "odds.py").is_file(),
        "weather": (CODE / "weather.py").is_file(),
    }
    deferred = [n for n in ("qb_changes", "odds", "weather") if not live[n]]
    return {
        "id": "T-PIT-8",
        "required_classes": required,
        "undeclared_allowed": extra_ok,
        "all_have_availability_ts_or_ryan_exempt": all_ok and not undeclared,
        "live_scan": live,
        "live_scan_deferred": deferred,
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
    cmd = [sys.executable, str(CODE / "run_t_pit.py"), "--dump-payload"]
    runs = [
        subprocess.run(cmd, capture_output=True, text=True, check=False)
        for _ in range(2)
    ]
    identical = (
        runs[0].returncode == 0
        and runs[1].returncode == 0
        and runs[0].stdout == runs[1].stdout
    )
    return {
        "id": "T-PIT-9",
        "bit_identical": identical,
        "n_runs": 2,
        "cross_process": True,
    }


def _run_gpit_loader(*, gpit: bool) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if gpit:
        env["GPIT_MODE"] = "1"
    else:
        env.pop("GPIT_MODE", None)
    return subprocess.run(
        [
            sys.executable,
            str(CODE / "gpit_production_loader.py"),
            str(FIX / "t_pit_10_season"),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _stdout_json(proc: subprocess.CompletedProcess) -> dict:
    lines = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()]
    if not lines:
        return {}
    return json.loads(lines[-1])


def run_t_pit_10() -> dict:
    fit = _sha256(CITED_FIT)
    builder = _sha256(CITED_BUILDER)
    on = _run_gpit_loader(gpit=True)
    off = _run_gpit_loader(gpit=False)
    on_body = _stdout_json(on)
    off_body = _stdout_json(off)
    return {
        "id": "T-PIT-10",
        "cited_fit_sha8": fit[:8],
        "cited_builder_sha8": builder[:8],
        "cited_fit_sha_ok": fit == REQUIRED_FIT,
        "cited_builder_sha_ok": builder == REQUIRED_BUILDER,
        "gpit_on_exit_code": on.returncode,
        "gpit_on_stderr_has_stop": STOP_MSG in (on.stderr or ""),
        "gpit_on_n_members": int(on_body.get("n_members") or 0),
        "gpit_off_exit_code": off.returncode,
        "gpit_off_stderr_has_stop": STOP_MSG in (off.stderr or ""),
        "gpit_off_stderr_has_superseded": SUPERSEDED_MSG in (off.stderr or ""),
        "gpit_off_player_in_season_union": bool(off_body.get("in_aaa")),
        "gpit_off_distinct_from_on": (on.returncode != off.returncode)
        and (STOP_MSG in (on.stderr or ""))
        and (STOP_MSG not in (off.stderr or "")),
    }


def run_dev_coverage() -> dict:
    """Schedule export keys 2013–2023 REG only. Not fold-n.

    Reconstructible stays 0 (no capture-time weekly source). Does not
    read W1 week-label packs as PIT. Does not open B2b 2024/25.
    """
    _guard_b2b()
    keys = _load(FIX / "dev_game_keys_le2023.json")
    games = keys["games"]
    seasons = sorted({int(g["season"]) for g in games})
    holdout_in_file = sorted({int(g["season"]) for g in games if int(g["season"]) >= 2024})
    if holdout_in_file:
        raise RuntimeError(f"holdout years in development keys: {holdout_in_file}")
    counts = Counter(int(g["season"]) for g in games)
    n = len(games)
    if n != int(keys.get("n", n)):
        raise RuntimeError("dev_game_keys n mismatch")
    n_2022 = int(counts.get(2022, 0))
    n_2023 = int(counts.get(2023, 0))
    return {
        "id": "DEV-COVERAGE",
        "population": "schedule_export_keys",
        "not_fold_n": True,
        "n_dev_games": n,
        "seasons": seasons,
        "n_by_season": {str(y): int(counts[y]) for y in seasons},
        "n_2022": n_2022,
        "n_2023": n_2023,
        "note_2022": (
            "2022 REG schedule has 271 games (BUF-CIN W17 cancelled). "
            "2021 and 2023 have 272. Prior fold F1=268/F2=271 (539) is a "
            "different population (fold/exclusion set), not this export key count."
        ),
        "holdout_years_read": [],
        "n_reconstructible": 0,
        "n_ineligible": n,
        "w1_packs_2019_2023_eligible": False,
        "w1_reason": "INELIGIBLE_WEEK_LABEL",
        "b2b_2024_2025_opened": False,
        "refit": False,
        "d4_path": "ii",
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


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    _guard_b2b()
    if argv and argv[0] == "--dump-payload":
        sys.stdout.write(_dump(_synthetic_payload()) + "\n")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    exp_commit = _expected_commit()
    harness_commit = _harness_commit()
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
        "package": "week-aware-roster-step2-v2",
        "kind": "synthetic",
        "expected_answers_commit": exp_commit,
        "harness_commit": harness_commit,
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
        "package": "week-aware-roster-step2-v2",
        "kind": "development_coverage",
        "expected_answers_commit": exp_commit,
        "harness_commit": harness_commit,
        "pass": cov_pass,
        "actual": cov_actual,
        "refit": False,
        "holdout_years_read": [],
        "b2b_2024_2025_opened": False,
        "source_sot_pin": False,
        "d4_path": "ii",
    }
    (OUT / "DEV-COVERAGE.json").write_text(json.dumps(cov, indent=2) + "\n")
    print(
        f"DEV-COVERAGE: {'PASS' if cov_pass else 'FAIL'} "
        f"reconstructible={cov_actual['n_reconstructible']} "
        f"ineligible={cov_actual['n_ineligible']}"
    )
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
