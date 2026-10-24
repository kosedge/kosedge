#!/usr/bin/env python3
"""Holdout opening runner v3 — 77d9c00a B-1..B-10. Does not open 2024/25.

Expected answers filed first in commit fd2ed658. Ryan CLEAR fabf8732
(t4335s14919): "CLEAR: build the runner, IMV reviews, then open once".

Production main() is only run_holdout_workspace: pins → lock → chain →
consumed → receipt. No real lock this package (IMV PASS file absent).
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
import shutil
import stat
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

REAL_LOCK = Path("/workspace/ops/nfl_injury_audit_t4274u/holdout-once.lock")
LOCK_NAME = "holdout-once.lock"
CONSUMED_NAME = "holdout-once.lock.consumed"
FIXTURE_MARKER = ".opening_fixture_workspace"
IMV_RULING_DIR = Path("/workspace/fg-repair/imv-gate1-review-2026-10-02")
IMV_OPENING_RULING_GLOB = "IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v*.txt"

REQUIRED_DECISION = "fabf87320453c274b2b8ec8e443b8af4709d8d24ff8fb6baa449fe3d739d4bd0"
REQUIRED_D2_RULING = "b7364186cc2aa900fd39e2dd22e78e2e69b63d2cac11fd6fa6b234997494b6b8"
REQUIRED_OPENING_RETURN_V1 = "a8958e850cd75cce5a24feda95a865e86ca39a2afaff5144748f70cfe4dcbeaa"
REQUIRED_OPENING_RETURN_V2 = "77d9c00a306d1399aeeab6558a522182aa52d63c42c0b1f8cc4d350c1b0c3d0d"
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
REQUIRED_EXPECTED = "1cffb97927095930f675963a9656524435f36bd1d79077ab3245d403f6cd2fcd"
REQUIRED_EXPECTED_COMMIT = "fd2ed658166c068c088bb8d971e899da87017ab9"
REQUIRED_HEAD = "8e2a15ac581277ecda71ea745c3b3477185d733b"
REQUIRED_RECORD_BASELINE_CSV = "502110cfc9293d96fd5635fbfdd3fad2c19367fa043ce3770cfbae05f2cdbe12"
REQUIRED_NFLVERSE_CLOSE = "634d8e730b20c31cafe925ab674a38076d124d619242efdfae140347ff212fc9"
RYAN_MESSAGE = "t4335s14919"
RYAN_VERBATIM = "CLEAR: build the runner, IMV reviews, then open once"
REQUEST_FOLD_RE = re.compile(r"season ∈ \{(\d{4}), (\d{4})\}")
ALWAYS_FORBIDDEN = frozenset({2026})
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
HOLM_NINE = (
    "spread_clv_delta",
    "spread_ats_delta",
    "spread_logloss_delta",
    "total_clv_delta",
    "total_ats_delta",
    "total_logloss_delta",
    "ml_clv_implied_prob_delta",
    "ml_ats_delta",
    "ml_logloss_delta",
)
NFL_TOTALS_PREFIX = "NFL_TOTALS_"
LOG_LINES: List[str] = []
_BASELINE = None
_PRODUCER = None
_EXPECTED: Optional[Dict[str, Any]] = None


def log(msg: str) -> None:
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
        return str(path)


def pkg_path(*parts: str) -> Path:
    return HERE.joinpath(*parts)


def is_null_field(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def runner_sha() -> str:
    return sha256_file(pkg_path("run_injury_holdout_opening.py"))


def code_tag() -> str:
    recorded = pkg_path("inputs", "runner_commit.txt")
    if recorded.is_file():
        return recorded.read_text(encoding="utf-8").strip()
    return REQUIRED_EXPECTED_COMMIT


def load_expected() -> Dict[str, Any]:
    global _EXPECTED
    path = pkg_path("t_expected", "HOLDOUT_EXPECTED.json")
    if sha256_file(path) != REQUIRED_EXPECTED:
        die("expected answers drifted")
    if _EXPECTED is None:
        _EXPECTED = json.loads(path.read_text(encoding="utf-8"))
    return _EXPECTED


def parse_request_fold_years() -> Tuple[int, int]:
    """B-3: fold years from request v3.1, not literals."""
    path = pkg_path("seeded", "nfl-injury-holdout-request-2024-2025-v3.1.md")
    if sha256_file(path) != REQUIRED_REQUEST:
        die("B-3 request sha drifted")
    text = path.read_text(encoding="utf-8")
    match = REQUEST_FOLD_RE.search(text)
    if not match:
        die("B-3 cannot parse season ∈ {YYYY, YYYY} from request v3.1")
    return int(match.group(1)), int(match.group(2))


def request_holdout_years() -> frozenset:
    f1, f2 = parse_request_fold_years()
    return frozenset({f1, f2})


def synthetic_holdout_years() -> frozenset:
    syn = load_expected()["synthetic_holdout_years"]
    return frozenset({int(syn["F1"]), int(syn["F2"])})


def verified_opening_pass_sha() -> Optional[str]:
    """B-8: exact IMV path, sidecar + 0444 + VERDICT: PASS + this runner_sha().

    No REQUIRED_OPENING_PASS constant. Does not read seeded/.
    """
    if not IMV_RULING_DIR.is_dir():
        return None
    self_sha = runner_sha()
    for path in sorted(IMV_RULING_DIR.glob(IMV_OPENING_RULING_GLOB)):
        sidecar = Path(str(path) + ".abs.sha256")
        if not sidecar.is_file():
            continue
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode != 0o444:
            continue
        listed = sidecar.read_text(encoding="utf-8").strip().split()
        if not listed:
            continue
        got = sha256_file(path)
        if listed[0] != got:
            continue
        text = path.read_text(encoding="utf-8")
        if "VERDICT: PASS" not in text:
            continue
        if self_sha not in text:
            continue
        return got
    return None


def holdout_season_allowed(season: int, state: Dict[str, Any]) -> bool:
    """B-2: 2024/25 only production lock AND verified PASS. Marker never admits them."""
    year = int(season)
    if year in ALWAYS_FORBIDDEN:
        return False
    if year in request_holdout_years():
        return bool(state.get("lock_is_production") and verified_opening_pass_sha())
    if year in synthetic_holdout_years():
        return bool(state.get("lock_written"))
    if year in ALLOWED_LE2023:
        return True
    return False


def may_open_holdout_listings(state: Dict[str, Any]) -> bool:
    """listings_2024/2025 only after production lock + verified PASS. Marker is irrelevant."""
    return bool(state.get("lock_written") and state.get("lock_is_production") and verified_opening_pass_sha())


def opening_permitted_computed(state: Dict[str, Any]) -> bool:
    return bool(state.get("lock_is_production") and verified_opening_pass_sha())


def holdout_years_opened_computed(state: Dict[str, Any], tz: Optional[Dict[str, Any]]) -> bool:
    opened = set(int(y) for y in ((tz or {}).get("years_opened") or []))
    opened.update(int(y) for y in (state.get("opened_seasons") or []))
    return bool(opened & request_holdout_years())


def assert_path_not_holdout(path: Path, state: Optional[Dict[str, Any]] = None) -> None:
    match = LISTINGS_HOLDOUT_NAME.match(path.name)
    if match:
        year = int(match.group(1))
        if year in ALWAYS_FORBIDDEN:
            die(f"D-2 refuse: year {year} in path {relpath(path)}")
        if not (state and may_open_holdout_listings(state)):
            die(f"D-2 refuse: holdout year {year} in path {relpath(path)} (not opened)")
    for part in path.parts:
        if part == "2026":
            die(f"D-2 refuse: holdout year {part} in path {relpath(path)}")
        if part in {"2024", "2025"} and not (state and may_open_holdout_listings(state)):
            die(f"D-2 refuse: holdout year {part} in path {relpath(path)} (not opened)")


def assert_env_clean() -> None:
    leaked = sorted(k for k in os.environ if k.startswith(NFL_TOTALS_PREFIX))
    if leaked:
        die(f"O-1 refuse: {leaked} set")
    if REAL_LOCK.exists():
        die("O-3 lock: real lock already exists; this package must not use it")


def fixtures_root() -> Path:
    return (HERE / "fixtures").resolve()


def workspace_is_package_fixture(path: Path) -> bool:
    try:
        path.resolve().relative_to(fixtures_root())
        return True
    except ValueError:
        return False


def workspace_is_review_fixture(path: Path) -> bool:
    if workspace_is_package_fixture(path):
        return True
    return (path / FIXTURE_MARKER).is_file()


def copy_fixture_to_temp(name: str) -> Path:
    """R-9: copy fixtures to a temp dir; never unlink in-package locks."""
    src = pkg_path("fixtures", name)
    dest_root = Path(tempfile.mkdtemp(prefix=f"opening-v3-{name}-"))
    dest = dest_root / name
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", FIXTURE_MARKER))
    (dest / FIXTURE_MARKER).write_text("copied\n", encoding="utf-8")
    return dest


def _load_py(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        die(f"cannot import {name}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def import_baseline_method():
    """B-5: sha vs expected answers BEFORE import."""
    global _BASELINE
    if _BASELINE is not None:
        return _BASELINE
    expected = load_expected()
    path = pkg_path("record_hfa_baseline_method.py")
    got = sha256_file(path)
    want = expected["baseline_method_sha"]
    if got != want:
        die(f"B-5 baseline method sha {got} != expected {want}")
    _BASELINE = _load_py("baseline_method_v3", path)
    return _BASELINE


def import_producer():
    """B-4: producer sha vs expected answers BEFORE import."""
    global _PRODUCER
    if _PRODUCER is not None:
        return _PRODUCER
    expected = load_expected()
    path = pkg_path("holdout_delta_producer.py")
    got = sha256_file(path)
    want = expected["delta_producer_sha"]
    if got != want:
        die(f"B-4 producer sha {got} != expected {want}")
    _PRODUCER = _load_py("holdout_delta_producer_v3", path)
    return _PRODUCER


def assert_pins_before_lock() -> None:
    """ALL pins, including method/producer sha, before any lock write (B-1/B-5)."""
    pairs = (
        ("seeded/fit_object.json", REQUIRED_FIT),
        ("seeded/sealed_injury_export_d87e6129.json", REQUIRED_FROZEN_EXPORT),
        ("seeded/write_sealed_injury_export_ts_v1.py", REQUIRED_WRITER),
        ("seeded/run_injury_residual_fit.py", REQUIRED_FROZEN_SCRIPT),
        ("seeded/nfl_injury_null_contract_8e2a15ac.py", REQUIRED_NULL_CONTRACT),
        ("seeded/ca98ae0e/run_injury_residual_evaluator.py", REQUIRED_SCORER),
        ("seeded/IMV_RULING_NFL_INJURY_HOLDOUT_RUNNER_D2_v1.txt", REQUIRED_D2_RULING),
        ("seeded/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v1.txt", REQUIRED_OPENING_RETURN_V1),
        ("seeded/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v2.txt", REQUIRED_OPENING_RETURN_V2),
        ("seeded/DECISION_RYAN_t4335s14919_HOLDOUT_CLEAR_v3_1_v1.txt", REQUIRED_DECISION),
        ("seeded/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v6.txt", REQUIRED_READINESS_V6),
        ("seeded/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v6_ERRATUM_v1.txt", REQUIRED_ERRATUM_V6),
        ("seeded/IMV_SPEC_NFL_INJURY_ADJUSTMENT_TESTS_v1.txt", REQUIRED_SPEC),
        ("seeded/IMV_SPEC_NFL_INJURY_PRE_HOLDOUT_ACCEPTANCE_v1.txt", REQUIRED_ACCEPT),
        ("seeded/nfl-injury-holdout-request-2024-2025-v3.1.md", REQUIRED_REQUEST),
        ("t_expected/HOLDOUT_EXPECTED.json", REQUIRED_EXPECTED),
        ("inputs/record_baseline_le2023.csv", REQUIRED_RECORD_BASELINE_CSV),
        ("inputs/nflverse_close_le2023.csv", REQUIRED_NFLVERSE_CLOSE),
    )
    for rel, exp in pairs:
        got = sha256_file(pkg_path(*rel.split("/")))
        if got != exp:
            die(f"O-2 pin {rel} sha {got} != {exp}")
    commit = pkg_path("inputs", "expected_answers_commit.txt").read_text(encoding="utf-8").strip()
    if commit != REQUIRED_EXPECTED_COMMIT:
        die(f"expected-answers commit {commit} != {REQUIRED_EXPECTED_COMMIT}")
    expected = load_expected()
    method_sha = sha256_file(pkg_path("record_hfa_baseline_method.py"))
    if method_sha != expected["baseline_method_sha"]:
        die(f"B-5 method sha {method_sha} != expected {expected['baseline_method_sha']}")
    producer_sha = sha256_file(pkg_path("holdout_delta_producer.py"))
    if producer_sha != expected["delta_producer_sha"]:
        die(f"B-4 producer sha {producer_sha} != expected {expected['delta_producer_sha']}")
    method = import_baseline_method()
    import_producer()
    check = method.assert_reproduces_le2023_csv(
        str(pkg_path("inputs", "nflverse_close_le2023.csv")),
        str(pkg_path("inputs", "record_baseline_le2023.csv")),
        REQUIRED_NFLVERSE_CLOSE,
        REQUIRED_RECORD_BASELINE_CSV,
    )
    spread, total = method.week1_identity()
    if abs(spread - 1.05) > 1e-12 or abs(total - 44.8435) > 1e-12:
        die(f"R-3 week-1 identity drifted spread={spread} total={total}")
    f1, f2 = parse_request_fold_years()
    if (f1, f2) != (expected["fold_years"]["F1"], expected["fold_years"]["F2"]):
        die(f"B-3 request fold years {(f1, f2)} != expected")
    log(f"pins ok before lock method={method_sha[:8]} producer={producer_sha[:8]} folds={f1}/{f2} b9={check['dal_car_2015_12_total']}")


def lock_path(workspace: Path) -> Path:
    return workspace / LOCK_NAME


def consumed_path(workspace: Path) -> Path:
    return workspace / CONSUMED_NAME


def lock_payload() -> Dict[str, Any]:
    expected = load_expected()
    return {
        "status": "open",
        "statement": "opened once",
        "consumed": False,
        "decision_sha": REQUIRED_DECISION,
        "ryan_message_id": RYAN_MESSAGE,
        "ryan_verbatim": RYAN_VERBATIM,
        "request_sha": REQUIRED_REQUEST,
        "readiness_sha": REQUIRED_READINESS_V6,
        "erratum_sha": REQUIRED_ERRATUM_V6,
        "imv_d2_ruling_sha": REQUIRED_D2_RULING,
        "opening_runner_return_v2_sha": REQUIRED_OPENING_RETURN_V2,
        "opening_runner_pass_sha": verified_opening_pass_sha(),
        "spec_sha": REQUIRED_SPEC,
        "acceptance_sha": REQUIRED_ACCEPT,
        "runner_sha": runner_sha(),
        "scorer_sha": REQUIRED_SCORER,
        "writer_sha": REQUIRED_WRITER,
        "frozen_script_sha": REQUIRED_FROZEN_SCRIPT,
        "null_contract_sha": REQUIRED_NULL_CONTRACT,
        "fit_sha": REQUIRED_FIT,
        "frozen_export_sha": REQUIRED_FROZEN_EXPORT,
        "le2023_export_sha": REQUIRED_EXPORT,
        "head_sha": REQUIRED_HEAD,
        "expected_sha": REQUIRED_EXPECTED,
        "expected_commit": REQUIRED_EXPECTED_COMMIT,
        "baseline_method_sha": expected["baseline_method_sha"],
        "delta_producer_sha": expected["delta_producer_sha"],
        "path1_export_composition": expected["path1_export_composition"]["statement"],
        "code_tag": code_tag(),
        "utc": now_utc(),
        "operator": "fixture",
    }


def write_lock(workspace: Path, state: Dict[str, Any]) -> Dict[str, Any]:
    path = lock_path(workspace)
    is_real = path.resolve() == REAL_LOCK.resolve()
    if is_real:
        if not verified_opening_pass_sha():
            die("O-3 lock: production lock requires verified IMV opening-runner PASS sha")
        state["lock_is_production"] = True
    elif workspace_is_review_fixture(workspace):
        state["lock_is_production"] = False
    else:
        die("O-3 lock: write only allowed under fixtures/ or a copied fixture workspace until IMV PASS")
    if path.exists():
        die(f"O-3 lock: existing lock {relpath(path)}")
    payload = lock_payload()
    if is_real:
        payload["operator"] = "production"
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")
    os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != 0o444:
        die(f"O-3 lock: mode {oct(mode)} != 0444")
    payload["sha256"] = sha256_file(path)
    payload["path"] = relpath(path)
    payload["mode"] = "0444"
    state["lock_written"] = True
    state["lock"] = payload
    log(f"lock written {payload['path']} sha={payload['sha256'][:8]} mode=0444")
    return payload


def mark_lock_consumed(workspace: Path, reason: str) -> None:
    path = lock_path(workspace)
    if not path.exists():
        return
    if path.resolve() == REAL_LOCK.resolve() and not verified_opening_pass_sha():
        return
    lock_sha = sha256_file(path)
    sidecar = consumed_path(workspace)
    doc = {"reason": reason, "utc": now_utc(), "lock_sha": lock_sha}
    sidecar.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(sidecar, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    mode = stat.S_IMODE(sidecar.stat().st_mode)
    if mode != 0o444:
        die(f"O-3 lock.consumed: mode {oct(mode)} != 0444")
    lock_mode = stat.S_IMODE(path.stat().st_mode)
    if lock_mode != 0o444:
        die(f"O-3 lock: mutated after write mode={oct(lock_mode)}")
    log(f"lock consumed sidecar {relpath(sidecar)} reason={reason} lock_sha={lock_sha[:8]}")


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


def import_writer():
    path = pkg_path("seeded", "write_sealed_injury_export_ts_v1.py")
    if sha256_file(path) != REQUIRED_WRITER:
        die("O-1 export: writer sha drifted")
    mod = _load_py("writer_9947b880", path)
    if not hasattr(mod, "timestamps_for_game") or not hasattr(mod, "write_sidecar_chain"):
        die("O-1 export: writer 9947b880 missing timestamps_for_game/write_sidecar_chain")
    if hasattr(mod, "main"):
        log("writer.main present and not invoked (B-10 le2023 Path 1 entrypoint)")
    log(f"writer invoked sha={REQUIRED_WRITER}")
    return mod


def write_holdout_export_path1(workspace: Path, state: Dict[str, Any]) -> Path:
    """B-10: apply_params producer + timestamps_for_game + write_sidecar_chain."""
    writer = import_writer()
    producer = import_producer()
    listings = workspace / "listings"
    if listings.is_dir():
        for child in listings.iterdir():
            match = LISTINGS_YEAR.match(child.name)
            if match and int(match.group(1)) in ALWAYS_FORBIDDEN:
                die(f"O-1 export: 2026 listings name present; not opened {child.name}")
            if match and int(match.group(1)) in request_holdout_years():
                if not may_open_holdout_listings(state):
                    die(f"O-1 export: holdout listings name present; not opened {child.name}")
    games_path = workspace / "games.json"
    if not games_path.is_file():
        die("O-1 export: fixture games.json absent after lock")
    source = json.loads(games_path.read_text(encoding="utf-8"))
    raw_games = list(source.get("games") or [])
    for game in raw_games:
        season = int(game.get("season") or 0)
        if not holdout_season_allowed(season, state):
            die(f"O-1 export: season {season} not allowed")
        state.setdefault("opened_seasons", []).append(season)
    applied, pins = producer.produce_deltas(HERE, raw_games)
    if len(applied) != len(raw_games):
        die("B-4 producer row count drifted")
    state["producer_pins"] = pins
    state["producer_invoked"] = True
    games_export: List[Dict[str, Any]] = []
    for raw, app in zip(raw_games, applied):
        complete = bool(app.get("complete"))
        merged = dict(raw)
        merged.update(app)
        ts = writer.timestamps_for_game(merged, complete)
        gid = raw.get("game_id") or f"{int(raw['season'])}_{raw['week']}_{raw['away']}_{raw['home']}"
        games_export.append(
            {
                "game_id": gid,
                "season": int(raw["season"]),
                "week": int(raw["week"]),
                "home": raw["home"],
                "away": raw["away"],
                "applied": False,
                "complete": complete,
                "delta_margin": app.get("delta_margin"),
                "delta_total": app.get("delta_total"),
                **ts,
            }
        )
    export_path = workspace / "export.json"
    text = json.dumps({"games": games_export}, indent=2, sort_keys=True) + "\n"
    export_path.write_text(text, encoding="utf-8")
    on_disk = sha256_file(export_path)
    raw_bytes = export_path.read_bytes()
    blob = sha256_bytes(raw_bytes[:-1] if raw_bytes.endswith(b"\n") else raw_bytes)
    writer.write_sidecar_chain(export_path, workspace / "SIDECAR_CHAIN_NOTE.md", blob, on_disk)
    state["writer_invoked"] = True
    state["export_path"] = export_path
    log(f"export written {relpath(export_path)} on_disk={on_disk[:8]} producer=apply_params writer=9947b880")
    return export_path


def census_listings_tz(listings_dir: Path, allowed_years: Iterable[int], state: Dict[str, Any]) -> Dict[str, Any]:
    allowed = frozenset(int(y) for y in allowed_years)
    if any(y in ALWAYS_FORBIDDEN for y in allowed):
        die("D-2 listings TZ: allowed years include 2026")
    for year in allowed:
        if year in request_holdout_years() and not holdout_season_allowed(year, state):
            die("D-2 listings TZ: holdout year before production+PASS")
    if not listings_dir.is_dir():
        die(f"D-2 listings TZ: missing directory {relpath(listings_dir)}")
    for child in listings_dir.iterdir():
        match = LISTINGS_YEAR.match(child.name)
        if match and int(match.group(1)) in request_holdout_years().union(ALWAYS_FORBIDDEN):
            assert_path_not_holdout(child, state)
    counts: Counter[str] = Counter()
    years_opened: List[int] = []
    n_rows = 0
    for year in sorted(allowed):
        path = listings_dir / f"listings_{year}.csv"
        assert_path_not_holdout(path, state)
        if not path.is_file():
            die(f"D-2 listings TZ: missing listings_{year}.csv")
        years_opened.append(year)
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "date_modified" not in reader.fieldnames:
                die(f"D-2 listings TZ: {path.name} has no date_modified")
            for row in reader:
                season_raw = str(row.get("season") or "").strip()
                if season_raw.isdigit() and not holdout_season_allowed(int(season_raw), state):
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
        if not holdout_season_allowed(season, state):
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


def load_export_games(export_path: Path, state: Dict[str, Any]) -> List[Dict[str, Any]]:
    doc = json.loads(export_path.read_text(encoding="utf-8"))
    games = list(doc.get("games") or [])
    for game in games:
        season = int(game.get("season") or 0)
        if not holdout_season_allowed(season, state):
            die(f"D-2 refuse: export contains holdout season {game.get('season')}")
    return games


def load_schedule(path: Path, state: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not path.is_file():
        die(f"O-1 join: missing schedule {relpath(path)}")
    rows: List[Dict[str, Any]] = []
    method = import_baseline_method()
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            season = int(row["season"])
            if not holdout_season_allowed(season, state):
                die("O-1 join: schedule contains a season that is not lock-allowed")
            rec = {
                "season": season,
                "week": int(row["week"]),
                "home": method.alias(row["home"]),
                "away": method.alias(row["away"]),
            }
            if row.get("home_score") not in (None, "") and row.get("away_score") not in (None, ""):
                rec["home_score"] = float(row["home_score"])
                rec["away_score"] = float(row["away_score"])
            rows.append(rec)
    return rows


def join_close(state: Dict[str, Any], games: Sequence[Dict[str, Any]], close_path: Path, schedule_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not state.get("tz_census_done"):
        die("D-2 order: listings TZ census must run before any join")
    if not state.get("incomplete_done"):
        die("D-2 order: incomplete-row count must be taken before any join")
    if not close_path.is_file():
        die(f"O-1 join: missing close file {relpath(close_path)}")
    method = import_baseline_method()
    book_base = method.build_record_book(load_schedule(schedule_path, state))
    close_book: Dict[Tuple[int, int, str, str], Dict[str, Any]] = {}
    with close_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            season = int(row["season"])
            if not holdout_season_allowed(season, state):
                die("O-1 join: close file contains a season that is not lock-allowed")
            home = method.alias(row["home"])
            away = method.alias(row["away"])
            close_book[(season, int(row["week"]), home, away)] = {
                "close_spread_home": float(row["nflverse_spread_line_home"]),
                "close_total": float(row["nflverse_total_line"]),
                "actual_margin": float(row["home_score"]) - float(row["away_score"]),
                "actual_total": float(row["home_score"]) + float(row["away_score"]),
            }
    universe: List[Dict[str, Any]] = []
    n_missing = 0
    missing_by: Counter[int] = Counter()
    for game in games:
        season = int(game["season"])
        week = int(game["week"])
        home = method.alias(game["home"])
        away = method.alias(game["away"])
        rec = close_book.get((season, week, home, away))
        base = method.lookup_baseline(book_base, season, week, home, away)
        if rec is None:
            n_missing += 1
            missing_by[season] += 1
        dm, dt = game.get("delta_margin"), game.get("delta_total")
        residual_complete = bool(game.get("complete")) and (not is_null_field(dm)) and (not is_null_field(dt))
        universe.append(
            {
                "season": season,
                "week": week,
                "home": home,
                "away": away,
                "game_id": game["game_id"],
                "residual_complete": residual_complete,
                "delta_margin": dm,
                "delta_total": dt,
                "baseline_margin": None if base is None else base[0],
                "baseline_total": None if base is None else base[1],
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
    mod = _load_py("scorer_ca98ae0e", path)
    if getattr(mod, "PINNED_SEED", None) != 20261023:
        die("O-1 score: scorer seed drifted")
    if getattr(mod, "SIGMA_MARGIN", None) != 13.5 or getattr(mod, "SIGMA_TOTAL", None) != 14.0:
        die("O-1 score: scorer sigma drifted")
    return mod


def fold_year_map(state: Dict[str, Any]) -> Tuple[int, int, bool]:
    expected = load_expected()
    if state.get("lock_is_production") and verified_opening_pass_sha():
        return (*parse_request_fold_years(), False)
    syn = expected["synthetic_holdout_years"]
    return int(syn["F1"]), int(syn["F2"]), True


def fold_slim(result: Dict[str, Any], year: Optional[int]) -> Dict[str, Any]:
    i4 = result.get("i4") or {}
    boot = (result.get("bootstrap") or {}).get("spread_clv_delta") or {}
    metrics = result.get("metrics") or {}
    holm = result.get("holm") or []
    holm_adj: Dict[str, Any] = {}
    holm_full: List[Dict[str, Any]] = []
    for item in holm:
        rank = int(item.get("holm_rank") or 0)
        raw_p = item.get("p")
        adj = None if raw_p is None else min(1.0, float(raw_p) * (9 - rank + 1))
        holm_adj[item["test_id"]] = adj
        holm_full.append({**item, "p_holm_adj": adj})
    for key in HOLM_NINE:
        holm_adj.setdefault(key, None)
    return {
        "year": year,
        "n": int((result.get("missing") or {}).get("n_universe") or 0),
        "i1": {key: metrics.get(key) for key in HOLM_NINE},
        "i2": result.get("i2"),
        "i3_holm_adjusted_p": holm_adj,
        "i3_holm": holm_full,
        "i4": i4.get("decision"),
        "k2": {
            "mean_brier_base": metrics.get("mean_brier_base"),
            "mean_brier_adj": metrics.get("mean_brier_adj"),
            "mean_logloss_base": metrics.get("mean_logloss_base"),
            "mean_logloss_adj": metrics.get("mean_logloss_adj"),
            "reliability": result.get("reliability"),
        },
        "k4": result.get("k4"),
        "primary": {
            "holm": i4.get("primary_significant_after_holm"),
            "ci_lo_gt_0": i4.get("primary_ci_lo_gt_0"),
            "ci_lo": boot.get("ci_lo"),
            "ci_hi": boot.get("ci_hi"),
        },
    }


def score_folds(universe: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
    scorer = import_scorer()
    f1, f2, dry = fold_year_map(state)
    by = {
        "F1": ([row for row in universe if int(row["season"]) == f1], f1),
        "F2": ([row for row in universe if int(row["season"]) == f2], f2),
        "pooled": (list(universe), None),
    }
    out: Dict[str, Any] = {}
    label = "opening-runner v3 fixture" if dry else "opening-runner v3"
    for name, (rows, year) in by.items():
        result = scorer.score_universe(name, rows, label, dry_run_label=dry)
        out[name] = fold_slim(result, year)
    return out


def write_receipt_manifest(workspace: Path, receipt_path: Path) -> Tuple[Optional[str], Optional[str]]:
    names = [
        LOCK_NAME,
        CONSUMED_NAME,
        "export.json",
        "export.json.sha256.v2",
        "receipt.json",
        "runner.log",
        "SIDECAR_CHAIN_NOTE.md",
    ]
    lines = []
    for name in names:
        path = workspace / name
        if path.is_file():
            lines.append(f"{sha256_file(path)}  {name}")
    if not lines:
        return None, None
    man = workspace / "RECEIPT_MANIFEST"
    man.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sums = workspace / "RECEIPT_SHA256SUMS"
    sums.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sha256_file(man), sha256_file(sums)


def write_receipt(
    workspace: Path,
    state: Dict[str, Any],
    pin: Optional[Dict[str, str]],
    tz: Optional[Dict[str, Any]],
    incomplete: Optional[Dict[str, Any]],
    missing: Optional[Dict[str, Any]],
    folds: Optional[Dict[str, Any]],
    stop: Optional[str],
    log_sha: Optional[str],
) -> Dict[str, Any]:
    lock = dict(state.get("lock") or {})
    if consumed_path(workspace).is_file():
        lock["status"] = "consumed"
    expected = load_expected()
    receipt = {
        "kind": "opening_receipt",
        "opening_permitted": opening_permitted_computed(state),
        "holdout_years_opened": holdout_years_opened_computed(state, tz),
        "runner_sha": runner_sha(),
        "scorer_sha": REQUIRED_SCORER,
        "delta_producer_sha": expected["delta_producer_sha"],
        "baseline_method_sha": expected["baseline_method_sha"],
        "writer_sha": REQUIRED_WRITER,
        "writer_invoked": bool(state.get("writer_invoked")),
        "producer_invoked": bool(state.get("producer_invoked")),
        "path1_export_composition": expected["path1_export_composition"]["statement"],
        "lock": lock,
        "export_on_disk_sha": None if pin is None else pin.get("on_disk_sha"),
        "tz": tz,
        "incomplete": None
        if incomplete is None
        else {
            "n_incomplete": incomplete.get("n_incomplete"),
            "n_incomplete_by_season": incomplete.get("n_incomplete_by_season"),
            "excluded_game_ids": incomplete.get("excluded_game_ids"),
        },
        "n_missing_close": None if missing is None else missing.get("n_missing_close"),
        "n_missing_close_by_season": None if missing is None else missing.get("n_missing_close_by_season"),
        "folds": folds,
        "log_sha": log_sha,
        "manifest_sha": sha256_file(pkg_path("MANIFEST")) if pkg_path("MANIFEST").is_file() else None,
        "sums_sha": sha256_file(pkg_path("SHA256SUMS")) if pkg_path("SHA256SUMS").is_file() else None,
        "receipt_manifest_sha": None,
        "receipt_sums_sha": None,
        "stop": stop,
        "consumed": consumed_path(workspace).is_file(),
    }
    path = workspace / "receipt.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    man_sha, sums_sha = write_receipt_manifest(workspace, path)
    receipt["receipt_manifest_sha"] = man_sha
    receipt["receipt_sums_sha"] = sums_sha
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != 0o444:
        die(f"B-6 receipt: mode {oct(mode)} != 0444")
    receipt["mode"] = "0444"
    log(f"receipt written {relpath(path)} mode=0444")
    state["receipt"] = receipt
    return receipt


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


def run_holdout_workspace(workspace: Path) -> Dict[str, Any]:
    """B-1: pins → lock → chain → consumed → receipt. Never reads 2024/25."""
    state: Dict[str, Any] = {"lock_written": False, "lock_is_production": False, "opened_seasons": []}
    assert_pins_before_lock()
    if lock_path(workspace).exists():
        die(f"O-3 lock: existing lock {relpath(lock_path(workspace))}")
    write_lock(workspace, state)
    pin = tz = incomplete = missing = folds = None
    try:
        export_path = write_holdout_export_path1(workspace, state)
        pin = pin_export_v2(export_path)
        listings = workspace / "listings"
        years = []
        if listings.is_dir():
            for child in listings.iterdir():
                match = LISTINGS_YEAR.match(child.name)
                if match:
                    years.append(int(match.group(1)))
        tz = census_listings_tz(listings, years, state)
        state["tz_census_done"] = True
        games = load_export_games(export_path, state)
        kept, incomplete = apply_incomplete_row_rule(games, state)
        joined, missing = join_close(state, kept, workspace / "close.csv", workspace / "schedule.csv")
        folds = score_folds(joined, state)
        mark_lock_consumed(workspace, "opened once")
        ws_log = workspace / "runner.log"
        ws_log.write_text("\n".join(LOG_LINES) + ("\n" if LOG_LINES else ""), encoding="utf-8")
        receipt = write_receipt(workspace, state, pin, tz, incomplete, missing, folds, None, sha256_file(ws_log))
        week1 = [row for row in joined if int(row["week"]) == 1]
        if week1:
            if abs(float(week1[0]["baseline_margin"]) - 1.05) > 1e-12:
                die(f"R-3 E2E week-1 baseline_margin {week1[0]['baseline_margin']} != 1.05")
            if abs(float(week1[0]["baseline_total"]) - 44.8435) > 1e-12:
                die(f"R-3 E2E week-1 baseline_total {week1[0]['baseline_total']} != 44.8435")
        log("sequence ok: pins lock export guards join score receipt")
        return receipt
    except SystemExit:
        if lock_path(workspace).exists():
            mark_lock_consumed(workspace, "STOP after lock")
            write_receipt(workspace, state, pin, tz, incomplete, missing, folds, (LOG_LINES[-1] if LOG_LINES else "STOP"), None)
        raise


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Holdout opening runner v3 (B-1..B-10). No real opening.")
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
        run_holdout_workspace(workspace)
        return 0
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
    log("opening runner v3 ok:true (no 2024/25 open; real lock not written)")
    return 0


def run_fixtures(expected: Dict[str, Any], out_dir: Path) -> Dict[str, Any]:
    results: Dict[str, Any] = {}

    def f_default() -> None:
        main(["--mode", "holdout"])

    results["F-DEFAULT-HOLDOUT"] = require_stop(capture_stop(f_default), expected["F-DEFAULT-HOLDOUT"]["must_contain"], "F-DEFAULT-HOLDOUT")
    if REAL_LOCK.exists():
        die("F-DEFAULT-HOLDOUT wrote the real lock")

    def f_production() -> None:
        main(["--mode", "holdout", "--workspace", str(REAL_LOCK.parent)])

    prod_text = capture_stop(f_production)
    results["F-PRODUCTION-LOCK-BLOCKED"] = require_stop(
        prod_text, expected["F-PRODUCTION-LOCK-BLOCKED"]["must_contain"], "F-PRODUCTION-LOCK-BLOCKED"
    )
    if "pins ok before lock" not in prod_text:
        die("B-1 F-PRODUCTION did not check pins before lock attempt")
    if REAL_LOCK.exists():
        die("F-PRODUCTION-LOCK-BLOCKED wrote the real lock")
    if (REAL_LOCK.parent / "receipt.json").exists():
        die("F-PRODUCTION-LOCK-BLOCKED wrote a receipt into the audit dir")

    e2e = copy_fixture_to_temp("e2e")

    def f_e2e() -> int:
        return main(["--mode", "holdout", "--workspace", str(e2e)])

    rc = f_e2e()
    if rc != 0:
        die("F-E2E did not return 0")
    lock = e2e / LOCK_NAME
    consumed = e2e / CONSUMED_NAME
    receipt_path = e2e / "receipt.json"
    export_path = e2e / "export.json"
    if not lock.is_file() or stat.S_IMODE(lock.stat().st_mode) != 0o444:
        die("F-E2E lock missing or not 0444")
    if not consumed.is_file() or stat.S_IMODE(consumed.stat().st_mode) != 0o444:
        die("F-E2E lock.consumed missing or not 0444")
    lock_doc = json.loads(lock.read_text(encoding="utf-8"))
    if lock_doc.get("status") != "open" or lock_doc.get("consumed"):
        die(f"F-E2E lock was rewritten {lock_doc}")
    if lock_doc.get("delta_producer_sha") != expected["delta_producer_sha"]:
        die("F-E2E lock missing B-4 producer pin")
    if not receipt_path.is_file() or stat.S_IMODE(receipt_path.stat().st_mode) != 0o444:
        die("F-E2E receipt missing or not 0444")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("kind") != "opening_receipt" or not receipt.get("consumed"):
        die(f"F-E2E receipt {receipt}")
    if not receipt.get("writer_invoked") or not receipt.get("producer_invoked"):
        die("F-E2E writer/producer not invoked")
    if receipt.get("holdout_years_opened") or receipt.get("opening_permitted"):
        die("F-E2E opened real holdout")
    if receipt.get("runner_sha") != runner_sha() or receipt.get("scorer_sha") != REQUIRED_SCORER:
        die("F-E2E receipt missing top-level runner/scorer sha")
    pooled = (receipt.get("folds") or {}).get("pooled") or {}
    if "i1" not in pooled or "i3_holm_adjusted_p" not in pooled or "k2" not in pooled:
        die("F-E2E fold_slim missing I-1 / Holm / K-2")
    if set((pooled.get("i3_holm_adjusted_p") or {})) != set(HOLM_NINE):
        die("F-E2E Holm keys != HOLM_NINE")
    if not (e2e / "RECEIPT_MANIFEST").is_file() or not (e2e / "RECEIPT_SHA256SUMS").is_file():
        die("F-E2E receipt MANIFEST/SUMS missing")
    export = json.loads(export_path.read_text(encoding="utf-8"))
    for game in export.get("games") or []:
        if int(game["season"]) in request_holdout_years():
            die("F-E2E export contains real holdout year")
    if REAL_LOCK.exists():
        die("F-E2E wrote the real lock")
    (out_dir / "synthetic").mkdir(parents=True, exist_ok=True)
    shutil.copy2(receipt_path, out_dir / "synthetic" / "receipt.json")
    results["F-E2E"] = {
        "stop": False,
        "writer_invoked": True,
        "producer_invoked": True,
        "receipt_kind": receipt.get("kind"),
        "export_on_disk_sha": receipt.get("export_on_disk_sha"),
        "n_incomplete": (receipt.get("incomplete") or {}).get("n_incomplete"),
        "i4": pooled.get("i4"),
        "fold_years": {"F1": (receipt.get("folds") or {}).get("F1", {}).get("year"), "F2": (receipt.get("folds") or {}).get("F2", {}).get("year")},
        "workspace": str(e2e),
    }

    marker_state: Dict[str, Any] = {"lock_written": True, "lock_is_production": False}
    if holdout_season_allowed(2024, marker_state) or holdout_season_allowed(2025, marker_state):
        die("B-2 fixture marker/lock_written admitted 2024/25")
    if not holdout_season_allowed(2098, marker_state) or not holdout_season_allowed(2099, marker_state):
        die("B-2 synthetic holdout years not allowed after lock")
    if may_open_holdout_listings(marker_state):
        die("B-2 fixture marker admitted listings_2024/2025")
    results["F-MARKER-NO-2024"] = {"stop": False, "admitted_2024_2025": False, "synthetic_after_lock": True}
    log("F-E2E lock export guards join score receipt ok; F-MARKER-NO-2024 ok")

    present = copy_fixture_to_temp("lock-present")

    def f_lock_present() -> None:
        main(["--mode", "holdout", "--workspace", str(present)])

    results["F-LOCK-PRESENT"] = require_stop(capture_stop(f_lock_present), expected["F-LOCK-PRESENT"]["must_contain"], "F-LOCK-PRESENT")

    double = copy_fixture_to_temp("e2e")

    def f_double() -> None:
        try:
            main(["--mode", "holdout", "--workspace", str(double)])
        except SystemExit:
            pass
        main(["--mode", "holdout", "--workspace", str(double)])

    results["F-DOUBLE-OPEN"] = require_stop(capture_stop(f_double), expected["F-DOUBLE-OPEN"]["must_contain"], "F-DOUBLE-OPEN")

    refit = copy_fixture_to_temp("refit")

    def f_refit() -> None:
        main(["--mode", "holdout", "--workspace", str(refit), "--refit"])

    results["F-REFIT"] = require_stop(capture_stop(f_refit), expected["F-REFIT"]["must_contain"], "F-REFIT")
    if (refit / LOCK_NAME).exists():
        die("F-REFIT wrote a lock")

    def f_per_side() -> None:
        state: Dict[str, Any] = {"lock_written": True, "lock_is_production": False}
        games = load_export_games(pkg_path("fixtures", "per-side-null", "export.json"), state)
        apply_incomplete_row_rule(games, state)

    results["F-PER-SIDE"] = require_stop(capture_stop(f_per_side), expected["F-PER-SIDE"]["must_contain"], "F-PER-SIDE")
    log("fixtures: F-DEFAULT-HOLDOUT F-PRODUCTION-LOCK-BLOCKED F-LOCK-PRESENT F-DOUBLE-OPEN F-REFIT F-PER-SIDE STOP; F-E2E F-MARKER-NO-2024 recorded")
    return results


def run_le2023(expected: Dict[str, Any], out_dir: Path) -> Dict[str, Any]:
    export = pkg_path("seeded", "sealed_injury_export_ts_v1.json")
    listings = pkg_path("seeded", "listings-le2023")
    state: Dict[str, Any] = {"lock_written": False, "lock_is_production": False}
    pin = pin_export_v2(export)
    tz = census_listings_tz(listings, ALLOWED_LE2023, state)
    state["tz_census_done"] = True
    games = load_export_games(export, state)
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
        "opening_permitted": opening_permitted_computed(state),
        "holdout_years_opened": holdout_years_opened_computed(state, tz),
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
        "# Opening runner v3 report (77d9c00a B-1..B-10)",
        "",
        f"RETURN `77d9c00a`. Ryan `{RYAN_MESSAGE}` / `fabf8732`. Real lock not written. 2024/25 not opened.",
        f"Expected answers commit `{REQUIRED_EXPECTED_COMMIT}` before this runner. Log sha `{log_sha}`.",
        "",
        "## Fixtures",
        "",
    ]
    for key in ("F-DEFAULT-HOLDOUT", "F-PRODUCTION-LOCK-BLOCKED", "F-LOCK-PRESENT", "F-DOUBLE-OPEN", "F-REFIT", "F-PER-SIDE", "F-E2E", "F-MARKER-NO-2024"):
        val = fixtures.get(key)
        if isinstance(val, str):
            first = next((ln for ln in val.splitlines() if "STOP:" in ln), val.strip())
            lines.append(f"- `{key}` STOP: `{first}`")
        elif val:
            lines.append(f"- `{key}` recorded {val}")
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
