#!/usr/bin/env python3
"""Holdout opening runner — O-1..O-7 (b7364186). Does not open 2024/25.

Ryan CLEAR fabf8732 (t4335s14919): "CLEAR: build the runner, IMV reviews, then open once".
D-2 guards PASS WITH CONDITIONS. Lock and opening are NOT allowed yet.

One-process sequence (O-1): lock check -> lock write -> Path 1 export write ->
D-2 guards -> join -> score (import ca98ae0e by sha). No refit.

This package never writes the real lock and never reads a 2024/25 byte.
Expected answers (adbffc54) were filed in commit f835fd32 before this runner.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import re
import stat
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
REAL_LOCK = Path("/workspace/ops/nfl_injury_audit_t4274u/holdout-once.lock")
LOCK_NAME = "holdout-once.lock"

REQUIRED_DECISION = "fabf87320453c274b2b8ec8e443b8af4709d8d24ff8fb6baa449fe3d739d4bd0"
REQUIRED_D2_RULING = "b7364186cc2aa900fd39e2dd22e78e2e69b63d2cac11fd6fa6b234997494b6b8"
REQUIRED_REQUEST = "35cbb56e10cfe0ec3730441a453f171bda917e7c58ad3e5eb2fe2c573de5ef7b"
REQUIRED_READINESS_V6 = "8ca00bc49b412c1524b4a0d5a1ebacdd7bc4fe26f3e6354d52cb549812dbb012"
REQUIRED_ERRATUM_V6 = "14ac18190c89d3620a6f27d0a0be64fc8147c321063ca4aeaa459faa31fcde41"
REQUIRED_SPEC = "a156459b545e3b7d6a483f1db34cda7a4d32fc3afc70ed499b3adc726b1b6881"
REQUIRED_ACCEPT = "54bc78ecc70e6a440481253b9c7eeef0e749690e893f501862f5dd5c54444574"
REQUIRED_SCORER = "ca98ae0e70fcdee77d46aed3c4f9be5644079da6adf08411891e1d5b7970e6c6"
REQUIRED_WRITER = "9947b880bc789192a26b850ee53dc89d4c43a4c107bdf3fc549c65730739d58f"
REQUIRED_FIT = "6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657"
REQUIRED_FROZEN_EXPORT = "d87e6129c451bbdc51d49eb7745a31ebb64ab6108ac58d8f8c4948dcc13e18e8"
REQUIRED_FROZEN_SCRIPT = "8d188da27d3c9f802acdca76763e1ca05e714040cc5ea3722e4922853f28167c"
REQUIRED_NULL_CONTRACT = "ff8e6527f63b0afd727eed30444436ceae320cc336d9113a2634fd66d4aebad2"
REQUIRED_EXPORT = "a38a55bb765e977ed88f8808d76715faddf50098b2354b122a5499f0ec706ac8"
REQUIRED_EXPORT_BLOB_NOT_A_PIN = "46d2a5657d1b5a5eb1af03f4d643afbfaa4762f31260daff439b5df1ac1456eb"
REQUIRED_EXPECTED = "adbffc54ac13725a58d36b0ffd1d46af426f82d4b9364f9869468499e258cc5c"
REQUIRED_EXPECTED_COMMIT = "f835fd32028a392927cb37706991889742c0f6e3"
REQUIRED_HEAD = "8e2a15ac581277ecda71ea745c3b3477185d733b"
RYAN_MESSAGE = "t4335s14919"
RYAN_VERBATIM = "CLEAR: build the runner, IMV reviews, then open once"

FORBIDDEN_SEASONS = frozenset({2024, 2025, 2026})
ALLOWED_LE2023 = frozenset(range(2013, 2024))
LISTINGS_YEAR = re.compile(r"^listings_(\d{4})\.csv$")
LISTINGS_HOLDOUT_NAME = re.compile(r"^listings_(2024|2025|2026)(?:\.csv)?$")
TIMESTAMP_FIELDS = ("source_ts", "as_of_ts", "kickoff_utc", "source_ts_home", "source_ts_away")
LE2023_EXCLUDED = [
    "2013_1_CIN_CHI",
    "2013_1_NYG_DAL",
    "2014_15_SF_SEA",
    "2015_1_NO_ARI",
    "2017_1_IND_LA",
    "2020_1_GB_MIN",
    "2020_6_KC_BUF",
    "2022_2_IND_JAX",
    "2022_7_CHI_NE",
    "2022_12_BAL_JAX",
    "2023_5_HOU_ATL",
]
NFL_TOTALS_PREFIX = "NFL_TOTALS_"
LOG_LINES: List[str] = []


def log(msg: str) -> None:
    line = msg if msg.startswith("STOP:") or msg.startswith("cmd=") or True else msg
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()
    LOG_LINES.append(msg)


def die(msg: str) -> None:
    log("STOP: " + msg)
    raise SystemExit(2)


def sha256_file(path: Path) -> str:
    if not path.is_file():
        die(f"missing file (fail-closed, not a crash): {path}")
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relpath(path: Path) -> str:
    try:
        return path.resolve().relative_to(HERE).as_posix()
    except ValueError:
        return path.name


def assert_path_not_holdout(path: Path) -> None:
    match = LISTINGS_HOLDOUT_NAME.match(path.name)
    if match:
        die(f"D-2 refuse: holdout year {match.group(1)} in path {relpath(path)}")
    for part in path.parts:
        if part in {str(y) for y in FORBIDDEN_SEASONS}:
            die(f"D-2 refuse: holdout year {part} in path {relpath(path)}")


def pkg_path(*parts: str) -> Path:
    path = HERE.joinpath(*parts)
    return path


def is_null_field(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def assert_env_clean() -> None:
    leaked = sorted(k for k in os.environ if k.startswith(NFL_TOTALS_PREFIX))
    if leaked:
        die(f"O-1 refuse: {leaked} set")
    if REAL_LOCK.exists():
        die("O-3 lock: real lock already exists; this package must not use it")


def fixtures_root() -> Path:
    return (HERE / "fixtures").resolve()


def workspace_is_fixture(path: Path) -> bool:
    try:
        path.resolve().relative_to(fixtures_root())
        return True
    except ValueError:
        return False


def assert_pins_before_lock() -> None:
    pairs = (
        ("seeded/fit_object.json", REQUIRED_FIT),
        ("seeded/sealed_injury_export_d87e6129.json", REQUIRED_FROZEN_EXPORT),
        ("seeded/write_sealed_injury_export_ts_v1.py", REQUIRED_WRITER),
        ("seeded/run_injury_residual_fit.py", REQUIRED_FROZEN_SCRIPT),
        ("seeded/nfl_injury_null_contract_8e2a15ac.py", REQUIRED_NULL_CONTRACT),
        ("seeded/ca98ae0e/run_injury_residual_evaluator.py", REQUIRED_SCORER),
        ("seeded/IMV_RULING_NFL_INJURY_HOLDOUT_RUNNER_D2_v1.txt", REQUIRED_D2_RULING),
        ("seeded/DECISION_RYAN_t4335s14919_HOLDOUT_CLEAR_v3_1_v1.txt", REQUIRED_DECISION),
        ("t_expected/HOLDOUT_EXPECTED.json", REQUIRED_EXPECTED),
    )
    for rel, exp in pairs:
        got = sha256_file(pkg_path(*rel.split("/")))
        if got != exp:
            die(f"O-2 pin {rel} sha {got} != {exp}")
    commit = pkg_path("inputs", "expected_answers_commit.txt").read_text(encoding="utf-8").strip()
    if commit != REQUIRED_EXPECTED_COMMIT:
        die(f"expected-answers commit {commit} != {REQUIRED_EXPECTED_COMMIT}")


def load_expected() -> Dict[str, Any]:
    path = pkg_path("t_expected", "HOLDOUT_EXPECTED.json")
    if sha256_file(path) != REQUIRED_EXPECTED:
        die("expected answers drifted")
    return json.loads(path.read_text(encoding="utf-8"))


def lock_path(workspace: Path) -> Path:
    return workspace / LOCK_NAME


def write_lock(workspace: Path) -> Dict[str, Any]:
    path = lock_path(workspace)
    if path.resolve() == REAL_LOCK.resolve():
        die("O-3 lock: refusing to write the real lock")
    if not workspace_is_fixture(path):
        die("O-3 lock: write only allowed under fixtures/ until IMV PASS")
    if path.exists():
        die(f"O-3 lock: existing lock {relpath(path)}")
    payload = {
        "status": "open",
        "statement": "opened once",
        "decision_sha": REQUIRED_DECISION,
        "ryan_message_id": RYAN_MESSAGE,
        "ryan_verbatim": RYAN_VERBATIM,
        "request_sha": REQUIRED_REQUEST,
        "imv_d2_ruling_sha": REQUIRED_D2_RULING,
        "runner_sha": sha256_file(pkg_path("run_injury_holdout_opening.py")),
        "scorer_sha": REQUIRED_SCORER,
        "writer_sha": REQUIRED_WRITER,
        "fit_sha": REQUIRED_FIT,
        "expected_sha": REQUIRED_EXPECTED,
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "operator": "fixture",
        "consumed": False,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")
    os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != 0o444:
        die(f"O-3 lock: mode {oct(mode)} != 0444")
    payload["sha256"] = sha256_file(path)
    payload["path"] = relpath(path)
    payload["mode"] = "0444"
    log(f"lock written {payload['path']} sha={payload['sha256'][:8]} mode=0444")
    return payload


def mark_lock_consumed(workspace: Path, reason: str) -> None:
    path = lock_path(workspace)
    if not path.exists() or path.resolve() == REAL_LOCK.resolve():
        return
    os.chmod(path, stat.S_IWUSR | stat.S_IRUSR)
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["status"] = "consumed"
    doc["consumed"] = True
    doc["consume_reason"] = reason
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    log(f"lock consumed {relpath(path)} reason={reason}")


def classify_date_modified(value: Any) -> str:
    raw = "" if value is None else str(value).strip()
    if not raw:
        return "empty"
    if raw.endswith("Z"):
        try:
            datetime.fromisoformat(raw[:-1] + "+00:00")
        except ValueError:
            return "other"
        return "z"
    try:
        stamp = datetime.fromisoformat(raw)
    except ValueError:
        return "other"
    if stamp.tzinfo is None:
        return "naive"
    return "offset"


def pin_export_v2(export_path: Path) -> Dict[str, str]:
    sidecar = Path(str(export_path) + ".sha256.v2")
    if not sidecar.is_file():
        die(f"D-2 export pin: missing on-disk .v2 sidecar {relpath(sidecar)}")
    line = sidecar.read_text(encoding="utf-8").strip()
    parts = line.split()
    if len(parts) != 2:
        die("D-2 export pin: sidecar must be '{sha256}  {basename}'")
    listed_sha, listed_name = parts
    if listed_name != export_path.name:
        die(f"D-2 export pin: sidecar basename {listed_name} != {export_path.name}")
    on_disk = sha256_file(export_path)
    raw = export_path.read_bytes()
    blob = sha256_bytes(raw[:-1] if raw.endswith(b"\n") else raw)
    if listed_sha == blob and listed_sha != on_disk:
        die("D-2 export pin: sidecar uses blob hash; pin must be on-disk sha")
    if listed_sha != on_disk:
        die(f"D-2 export pin: sidecar sha != on-disk sha listed={listed_sha} on_disk={on_disk}")
    return {"on_disk_sha": on_disk, "blob_sha_not_a_pin": blob}


def census_listings_tz(listings_dir: Path, allowed_years: Iterable[int]) -> Dict[str, Any]:
    allowed = frozenset(int(y) for y in allowed_years)
    if allowed & FORBIDDEN_SEASONS:
        die("D-2 listings TZ: allowed years include a holdout year")
    if not listings_dir.is_dir():
        die(f"D-2 listings TZ: missing directory {relpath(listings_dir)}")
    for child in listings_dir.iterdir():
        match = LISTINGS_YEAR.match(child.name)
        if match and int(match.group(1)) in FORBIDDEN_SEASONS:
            die(f"D-2 refuse: holdout year {match.group(1)} in path {relpath(child)}")
    counts: Counter[str] = Counter()
    years_opened: List[int] = []
    n_rows = 0
    for year in sorted(allowed):
        path = listings_dir / f"listings_{year}.csv"
        assert_path_not_holdout(path)
        if not path.is_file():
            die(f"D-2 listings TZ: missing listings_{year}.csv")
        years_opened.append(year)
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "date_modified" not in reader.fieldnames:
                die(f"D-2 listings TZ: {path.name} has no date_modified")
            for row in reader:
                season_raw = str(row.get("season") or "").strip()
                if season_raw.isdigit() and int(season_raw) in FORBIDDEN_SEASONS:
                    die(f"D-2 refuse: holdout season {season_raw} inside {path.name}")
                kind = classify_date_modified(row.get("date_modified"))
                counts[kind] += 1
                n_rows += 1
                if kind == "naive":
                    die(f"D-2 listings TZ: naive/zoneless date_modified file={path.name} value={row.get('date_modified')!r}")
    if counts.get("empty", 0) or counts.get("other", 0):
        die(f"D-2 listings TZ: empty/other n_empty={counts.get('empty', 0)} n_other={counts.get('other', 0)}")
    return {
        "n_listings": n_rows,
        "n_z": counts.get("z", 0),
        "n_offset": counts.get("offset", 0),
        "n_naive": counts.get("naive", 0),
        "n_empty": counts.get("empty", 0),
        "n_other": counts.get("other", 0),
        "years_opened": years_opened,
    }


def apply_incomplete_row_rule(games: Sequence[Dict[str, Any]], state: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if state.get("joined"):
        die("D-2 order: incomplete-row count must be taken before any join")
    kept: List[Dict[str, Any]] = []
    excluded_ids: List[str] = []
    by_season: Counter[int] = Counter()
    for game in games:
        season = int(game.get("season") or 0)
        if season in FORBIDDEN_SEASONS:
            die(f"D-2 refuse: incomplete-row saw holdout season {season}")
        complete = bool(game.get("complete"))
        gid = str(game.get("game_id") or "")
        has_ts = any(not is_null_field(game.get(key)) for key in TIMESTAMP_FIELDS)
        if complete:
            for key in ("source_ts", "as_of_ts", "kickoff_utc"):
                if is_null_field(game.get(key)):
                    die(f"D-2 incomplete: complete row has a null timestamp game_id={gid}")
            for key in ("source_ts_home", "source_ts_away"):
                if is_null_field(game.get(key)):
                    die(f"O-5 incomplete: complete row has a null per-side timestamp game_id={gid} field={key}")
        if (not complete) and has_ts:
            die(f"D-2 incomplete: incomplete row has a timestamp game_id={gid}")
        if not complete:
            for key in ("delta_margin", "delta_total"):
                if not is_null_field(game.get(key)):
                    die(f"D-2 incomplete: incomplete row has non-null {key} game_id={gid}")
            excluded_ids.append(gid)
            by_season[season] += 1
            continue
        kept.append(dict(game))
    census = {
        "n_incomplete": len(excluded_ids),
        "n_incomplete_by_season": {str(k): int(v) for k, v in sorted(by_season.items())},
        "excluded_game_ids": excluded_ids,
        "n_kept": len(kept),
    }
    state["incomplete_done"] = True
    state["incomplete"] = census
    return kept, census


def write_holdout_export_path1(workspace: Path) -> None:
    """O-1 export step. Pins writer 9947b880. Does not read 2024/25 bytes."""
    writer = pkg_path("seeded", "write_sealed_injury_export_ts_v1.py")
    if sha256_file(writer) != REQUIRED_WRITER:
        die("O-1 export: writer sha drifted")
    listings = workspace / "listings"
    if listings.is_dir():
        for child in listings.iterdir():
            match = LISTINGS_YEAR.match(child.name)
            if match and int(match.group(1)) in FORBIDDEN_SEASONS:
                die(f"O-1 export: holdout listings name present; not opened {child.name}")
    die("O-1 export: holdout listings absent after lock; lock consumed")


def load_export_games(export_path: Path) -> List[Dict[str, Any]]:
    doc = json.loads(export_path.read_text(encoding="utf-8"))
    games = list(doc.get("games") or [])
    for game in games:
        if int(game.get("season") or 0) in FORBIDDEN_SEASONS:
            die(f"D-2 refuse: export contains holdout season {game.get('season')}")
    return games


def join_close(state: Dict[str, Any], games: Sequence[Dict[str, Any]], close_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not state.get("tz_census_done"):
        die("D-2 order: listings TZ census must run before any join")
    if not state.get("incomplete_done"):
        die("D-2 order: incomplete-row count must be taken before any join")
    if not close_path.is_file():
        die(f"O-1 join: missing close file {relpath(close_path)}")
    book: Dict[Tuple[int, int, str, str], Dict[str, Any]] = {}
    with close_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            season = int(row["season"])
            if season in FORBIDDEN_SEASONS:
                die("O-1 join: close file contains holdout season")
            book[(season, int(row["week"]), row["home"], row["away"])] = {
                "close_spread_home": float(row["nflverse_spread_line_home"]),
                "close_total": float(row["nflverse_total_line"]),
                "actual_margin": float(row["home_score"]) - float(row["away_score"]),
                "actual_total": float(row["home_score"]) + float(row["away_score"]),
            }
    universe: List[Dict[str, Any]] = []
    n_missing = 0
    missing_by: Counter[int] = Counter()
    for game in games:
        rec = book.get((int(game["season"]), int(game["week"]), game["home"], game["away"]))
        if rec is None:
            n_missing += 1
            missing_by[int(game["season"])] += 1
        universe.append(
            {
                "season": int(game["season"]),
                "week": int(game["week"]),
                "home": game["home"],
                "away": game["away"],
                "game_id": game["game_id"],
                "residual_complete": True,
                "delta_margin": game.get("delta_margin"),
                "delta_total": game.get("delta_total"),
                "baseline_margin": -3.0,
                "baseline_total": 45.0,
                "close_spread_home": None if rec is None else rec["close_spread_home"],
                "close_total": None if rec is None else rec["close_total"],
                "actual_margin": None if rec is None else rec["actual_margin"],
                "actual_total": None if rec is None else rec["actual_total"],
                "source_ts": game.get("source_ts"),
                "as_of_ts": game.get("as_of_ts"),
                "kickoff_utc": game.get("kickoff_utc"),
                "outcome_joined_before_freeze": False,
                "close_joined_before_freeze": False,
            }
        )
    state["joined"] = True
    missing = {"n_missing_close": n_missing, "n_missing_close_by_season": {str(k): int(v) for k, v in sorted(missing_by.items())}}
    return universe, missing


def import_scorer():
    path = pkg_path("seeded", "ca98ae0e", "run_injury_residual_evaluator.py")
    if sha256_file(path) != REQUIRED_SCORER:
        die("O-1 score: scorer sha drifted")
    spec = importlib.util.spec_from_file_location("scorer_ca98ae0e", path)
    if spec is None or spec.loader is None:
        die("O-1 score: cannot import ca98ae0e")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if getattr(mod, "PINNED_SEED", None) != 20261023:
        die("O-1 score: scorer seed drifted")
    if getattr(mod, "SIGMA_MARGIN", None) != 13.5 or getattr(mod, "SIGMA_TOTAL", None) != 14.0:
        die("O-1 score: scorer sigma drifted")
    return mod


def score_synthetic(universe: List[Dict[str, Any]]) -> Dict[str, Any]:
    scorer = import_scorer()
    result = scorer.score_universe("synthetic-2022", universe, "opening-runner synthetic", dry_run_label=True)
    slim = {k: v for k, v in result.items() if k != "scored_rows"}
    return slim


def flush_log(out_dir: Path) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "runner.log"
    path.write_text("\n".join(LOG_LINES) + ("\n" if LOG_LINES else ""), encoding="utf-8")
    return sha256_file(path)


def capture_stop(fn) -> str:
    buf = io.StringIO()
    old = sys.stderr
    start = len(LOG_LINES)
    try:
        sys.stderr = buf
        fn()
    except SystemExit as exc:
        if int(getattr(exc, "code", 1) or 1) == 0:
            die("expected STOP, process exited 0")
    else:
        die("expected STOP, function returned")
    finally:
        sys.stderr = old
    text = buf.getvalue() + "\n".join(LOG_LINES[start:])
    if "STOP:" not in text:
        die(f"expected STOP log, got {text!r}")
    return text


def require_stop(text: str, needle: str, fixture_id: str) -> str:
    if needle not in text:
        die(f"{fixture_id} missing {needle!r} in {text!r}")
    return text


def run_holdout_workspace(workspace: Path) -> None:
    """O-1 sequence against a fixture workspace. Never reads 2024/25."""
    assert_pins_before_lock()
    if lock_path(workspace).exists():
        die(f"O-3 lock: existing lock {relpath(lock_path(workspace))}")
    write_lock(workspace)
    try:
        write_holdout_export_path1(workspace)
    except SystemExit:
        mark_lock_consumed(workspace, "export STOP")
        raise


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Holdout opening runner (O-1..O-7). No real opening.")
    parser.add_argument("--mode", choices=("fixtures", "le2023", "all", "holdout"), required=True)
    parser.add_argument("--workspace", default="")
    parser.add_argument("--refit", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    assert_env_clean()
    if args.refit:
        die("O-1 refuse: no tuning or refit path")
    if args.mode == "holdout":
        if not args.workspace:
            die("O-1 opening blocked: IMV has not passed this opening runner; real lock not written; 2024/25 not opened")
        workspace = Path(args.workspace)
        if not workspace.is_absolute():
            workspace = (HERE / workspace).resolve()
        if not workspace_is_fixture(workspace):
            die("O-1 opening blocked: workspace is not under fixtures/; real lock not written")
        run_holdout_workspace(workspace)
        die("O-1 opening: sequence returned without STOP (unexpected in this package)")
    expected = load_expected()
    out = pkg_path("out")
    fixtures = {}
    le2023 = None
    if args.mode in {"fixtures", "all"}:
        fixtures = run_fixtures(expected, out)
    if args.mode in {"le2023", "all"}:
        le2023 = run_le2023(expected, out / "le2023")
    log_sha = flush_log(out)
    write_report(out, fixtures, le2023, log_sha)
    log("opening runner ok:true (no 2024/25 open; real lock not written)")
    return 0


def run_fixtures(expected: Dict[str, Any], out_dir: Path) -> Dict[str, Any]:
    results: Dict[str, Any] = {}

    def f_default() -> None:
        main(["--mode", "holdout"])

    results["F-DEFAULT-HOLDOUT"] = require_stop(capture_stop(f_default), expected["F-DEFAULT-HOLDOUT"]["must_contain"], "F-DEFAULT-HOLDOUT")
    if REAL_LOCK.exists():
        die("F-DEFAULT-HOLDOUT wrote the real lock")

    def _reset_fixture_lock(name: str) -> None:
        path = pkg_path("fixtures", name, LOCK_NAME)
        if path.exists() and workspace_is_fixture(path) and path.resolve() != REAL_LOCK.resolve():
            os.chmod(path, stat.S_IWUSR | stat.S_IRUSR)
            path.unlink()

    _reset_fixture_lock("holdout-missing")
    _reset_fixture_lock("double-open")

    def f_holdout() -> None:
        main(["--mode", "holdout", "--workspace", "fixtures/holdout-missing"])

    results["F-HOLDOUT"] = require_stop(capture_stop(f_holdout), expected["F-HOLDOUT"]["must_contain"], "F-HOLDOUT")
    lock = pkg_path("fixtures", "holdout-missing", LOCK_NAME)
    if not lock.is_file():
        die("F-HOLDOUT did not write a fixture lock")
    if stat.S_IMODE(lock.stat().st_mode) != 0o444:
        die("F-HOLDOUT lock is not 0444")
    doc = json.loads(lock.read_text(encoding="utf-8"))
    if doc.get("status") != "consumed" or not doc.get("consumed"):
        die(f"F-HOLDOUT lock not consumed {doc}")
    if REAL_LOCK.exists():
        die("F-HOLDOUT wrote the real lock")

    def f_lock_present() -> None:
        main(["--mode", "holdout", "--workspace", "fixtures/lock-present"])

    results["F-LOCK-PRESENT"] = require_stop(capture_stop(f_lock_present), expected["F-LOCK-PRESENT"]["must_contain"], "F-LOCK-PRESENT")

    def f_double() -> None:
        ws = "fixtures/double-open"
        try:
            main(["--mode", "holdout", "--workspace", ws])
        except SystemExit:
            pass
        main(["--mode", "holdout", "--workspace", ws])

    results["F-DOUBLE-OPEN"] = require_stop(capture_stop(f_double), expected["F-DOUBLE-OPEN"]["must_contain"], "F-DOUBLE-OPEN")

    def f_refit() -> None:
        main(["--mode", "holdout", "--workspace", "fixtures/refit", "--refit"])

    results["F-REFIT"] = require_stop(capture_stop(f_refit), expected["F-REFIT"]["must_contain"], "F-REFIT")
    if (pkg_path("fixtures", "refit") / LOCK_NAME).exists():
        die("F-REFIT wrote a lock")

    def f_per_side() -> None:
        state: Dict[str, Any] = {}
        games = load_export_games(pkg_path("fixtures", "per-side-null", "export.json"))
        apply_incomplete_row_rule(games, state)

    results["F-PER-SIDE"] = require_stop(capture_stop(f_per_side), expected["F-PER-SIDE"]["must_contain"], "F-PER-SIDE")

    # synthetic join+score (2022 only) after D-2 guards — no lock, no 2024/25
    state: Dict[str, Any] = {}
    export = pkg_path("fixtures", "ok-score", "export.json")
    pin = pin_export_v2(export)
    tz = census_listings_tz(pkg_path("fixtures", "ok-score"), (2022,))
    state["tz_census_done"] = True
    games = load_export_games(export)
    kept, incomplete = apply_incomplete_row_rule(games, state)
    joined, missing = join_close(state, kept, pkg_path("fixtures", "ok-score", "close.csv"))
    scored = score_synthetic(joined)
    (out_dir / "synthetic").mkdir(parents=True, exist_ok=True)
    (out_dir / "synthetic" / "score.json").write_text(json.dumps({"pin": pin, "tz": tz, "incomplete": incomplete, "missing": missing, "i4": scored.get("i4")}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    results["F-OK-SCORE"] = {"stop": False, "n_incomplete": incomplete["n_incomplete"], "i4": (scored.get("i4") or {}).get("decision")}
    log("fixtures: F-DEFAULT-HOLDOUT F-HOLDOUT F-LOCK-PRESENT F-DOUBLE-OPEN F-REFIT F-PER-SIDE STOP; F-OK-SCORE recorded")
    return results


def run_le2023(expected: Dict[str, Any], out_dir: Path) -> Dict[str, Any]:
    export = pkg_path("seeded", "sealed_injury_export_ts_v1.json")
    listings = pkg_path("seeded", "listings-le2023")
    state: Dict[str, Any] = {}
    pin = pin_export_v2(export)
    tz = census_listings_tz(listings, ALLOWED_LE2023)
    state["tz_census_done"] = True
    games = load_export_games(export)
    _kept, incomplete = apply_incomplete_row_rule(games, state)
    exp = expected["le2023_guards"]
    if pin["on_disk_sha"] != REQUIRED_EXPORT:
        die("le2023 export pin drifted")
    if tz["n_listings"] != exp["n_listings"] or tz["n_z"] != exp["n_z"] or tz["n_naive"] != 0:
        die(f"le2023 tz drifted {tz}")
    if incomplete["n_incomplete"] != exp["n_incomplete"] or incomplete["excluded_game_ids"] != exp["excluded_game_ids"]:
        die(f"le2023 incomplete drifted {incomplete}")
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": "le2023_guards",
        "opening_permitted": False,
        "holdout_years_opened": False,
        "joined": False,
        "pin": pin,
        "tz": tz,
        "incomplete": incomplete,
    }
    (out_dir / "d2_results.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "provenance.md").write_text(
        "\n".join(
            [
                "# Provenance le2023 (guards only; not an opening)",
                f"- excluded_game_ids={incomplete['excluded_game_ids']}",
                f"- n_incomplete={incomplete['n_incomplete']} by_season={incomplete['n_incomplete_by_season']}",
                f"- listings Z={tz['n_z']}/{tz['n_listings']} naive={tz['n_naive']}",
                "- 2024/25: not opened. Real lock: not written. Join: not run on holdout.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    log(f"le2023 guards: listings={tz['n_listings']} Z={tz['n_z']} n_incomplete={incomplete['n_incomplete']}")
    return payload


def write_report(out_dir: Path, fixtures: Dict[str, Any], le2023: Optional[Dict[str, Any]], log_sha: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Opening runner report (O-1..O-7)",
        "",
        f"Ruling `b7364186`. Ryan `{RYAN_MESSAGE}` / `fabf8732`. Real lock not written. 2024/25 not opened.",
        f"Expected answers commit `{REQUIRED_EXPECTED_COMMIT}` before this runner. Log sha `{log_sha}`.",
        "",
        "## Fixtures",
        "",
    ]
    for key in ("F-DEFAULT-HOLDOUT", "F-HOLDOUT", "F-LOCK-PRESENT", "F-DOUBLE-OPEN", "F-REFIT", "F-PER-SIDE", "F-OK-SCORE"):
        val = fixtures.get(key)
        if isinstance(val, str):
            first = next((ln for ln in val.splitlines() if "STOP:" in ln), val.strip())
            lines.append(f"- `{key}` STOP: `{first}`")
        elif val:
            lines.append(f"- `{key}` recorded n_incomplete={val.get('n_incomplete')} i4={val.get('i4')}")
    if le2023:
        lines.extend(
            [
                "",
                "## le2023 guards",
                "",
                f"- listings {le2023['tz']['n_listings']}: Z={le2023['tz']['n_z']} naive={le2023['tz']['n_naive']}",
                f"- n_incomplete={le2023['incomplete']['n_incomplete']} ids={le2023['incomplete']['excluded_game_ids']}",
            ]
        )
    lines.extend(["", "NO-GO. Coming Soon ON. No merge. No real lock. No opening.", ""])
    (out_dir / "opening-report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
