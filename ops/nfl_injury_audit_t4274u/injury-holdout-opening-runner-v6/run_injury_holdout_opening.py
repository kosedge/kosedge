#!/usr/bin/env python3
"""Holdout opening runner v6 — 2c71e4d0 L-1/B-4b(R)/B-4b(P)/B-4b(n). Does not open 2024/25.

Expected answers filed first in commit daf94a7d. Ryan CLEAR fabf8732
(t4335s14919): "CLEAR: build the runner, IMV reviews, then open once".
Ryan t4340s14953 / 592e0bb9: "Yes: allow scorer v6.2 for the opening,
only if IMV passes the diff as holdout-allowance-only with no metric change".
V62_DIFF_VERDICT PASS on 755d30a8. L-1 final pin is 8b482cb9 (docstring-only).

Exactly one scorer sha is pinned below (8b482cb9 = v6.2 FINAL).
No runtime switch. DIFF 280d9785 vs 755d30a8 is docstring-only.

Production main() is only run_holdout_workspace: pins → B-13 exist/size →
B-4b(P) raw shas → headers → lock → chain → week-1 → consumed → receipt.
No real lock this package.
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
AUDIT_DIR = Path("/workspace/ops/nfl_injury_audit_t4274u")
PRODUCTION_GAMES = AUDIT_DIR / "games.json"
PRODUCTION_CLOSE = AUDIT_DIR / "close.csv"
PRODUCTION_SCHEDULE = AUDIT_DIR / "schedule.csv"
PRODUCTION_LISTINGS = AUDIT_DIR / "listings"
PRODUCTION_ROSTERS = AUDIT_DIR / "rosters"
LOCK_NAME = "holdout-once.lock"
CONSUMED_NAME = "holdout-once.lock.consumed"
FIXTURE_MARKER = ".opening_fixture_workspace"
IMV_RULING_DIR = Path("/workspace/fg-repair/imv-gate1-review-2026-10-02")
IMV_OPENING_RULING_GLOB = "IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v*.txt"
# Ryan decision dir is the audit dir, not the IMV ruling dir (B-14).
RYAN_SCORER_DECISION = AUDIT_DIR / "DECISION_RYAN_SCORER_V6_2.txt"

REQUIRED_DECISION = "fabf87320453c274b2b8ec8e443b8af4709d8d24ff8fb6baa449fe3d739d4bd0"
REQUIRED_D2_RULING = "b7364186cc2aa900fd39e2dd22e78e2e69b63d2cac11fd6fa6b234997494b6b8"
REQUIRED_OPENING_RETURN_V1 = "a8958e850cd75cce5a24feda95a865e86ca39a2afaff5144748f70cfe4dcbeaa"
REQUIRED_OPENING_RETURN_V2 = "77d9c00a306d1399aeeab6558a522182aa52d63c42c0b1f8cc4d350c1b0c3d0d"
REQUIRED_OPENING_RETURN_V3 = "4fd6cfbe0adeaa7ff0152d8833e15d6b4e49a64cf47350fe595f3d35acef2867"
REQUIRED_OPENING_RETURN_V3_ERRATUM = "b746e5eba9c781f5f0586161b42d942a546b94224c24be8253f9cdd6a6d9ccf0"
REQUIRED_OPENING_RETURN_V4 = "0505e49295df6c0d3b3ddd2256607325da67baf561cc5d3b8a5a477fb669d508"
REQUIRED_OPENING_RETURN_V5 = "2c71e4d0baa0da16ef48f5f4560f1b151c742bb176226335b922d649aebf7a66"
REQUIRED_REQUEST = "35cbb56e10cfe0ec3730441a453f171bda917e7c58ad3e5eb2fe2c573de5ef7b"
REQUIRED_READINESS_V6 = "8ca00bc49b412c1524b4a0d5a1ebacdd7bc4fe26f3e6354d52cb549812dbb012"
REQUIRED_ERRATUM_V6 = "14ac18190c89d3620a6f27d0a0be64fc8147c321063ca4aeaa459faa31fcde41"
REQUIRED_SPEC = "a156459b545e3b7d6a483f1db34cda7a4d32fc3afc70ed499b3adc726b1b6881"
REQUIRED_ACCEPT = "54bc78ecc70e6a440481253b9c7eeef0e749690e893f501862f5dd5c54444574"
REQUIRED_SCORER_CA98 = "ca98ae0e70fcdee77d46aed3c4f9be5644079da6adf08411891e1d5b7970e6c6"
# ---------------------------------------------------------------------------
# B-14: exactly ONE scorer sha. Set only after Ryan's decision file exists.
# Decision path: /workspace/ops/nfl_injury_audit_t4274u/DECISION_RYAN_SCORER_V6_2.txt
# Decision sha:  592e0bb9e57ef4c7d997d48b336cb37594f7353a891b8ab56d6a70b55492e021
# Ryan t4340s14953 verbatim: "Yes: allow scorer v6.2 for the opening, only if
# IMV passes the diff as holdout-allowance-only with no metric change"
# V62_DIFF_VERDICT PASS on 755d30a8. L-1 FINAL is 8b482cb9 (docstring-only).
# No runtime switch.
# ---------------------------------------------------------------------------
ACTIVE_SCORER_SHA = "8b482cb9ddf46ea3bfb80cbfc429978467cbccc126fb0d9d7ca8013ef2f34b37"
ACTIVE_SCORER_RELPATH = "seeded/v6.2/run_injury_residual_evaluator.py"
REQUIRED_SCORER = ACTIVE_SCORER_SHA
REQUIRED_SCORER_V6_2 = ACTIVE_SCORER_SHA
REQUIRED_SCORER_V62_BASELINE = "755d30a8ce0dde7cd31b2e5ded9d4e06240e73f963b68a6ae4bd9af30d90ea5f"
REQUIRED_V62_DIFF = "280d9785ffc1a313e9415e0b3cf8f75f7d0156908aba29a9902e4bb8a8788c55"
REQUIRED_RYAN_SCORER_DECISION = "592e0bb9e57ef4c7d997d48b336cb37594f7353a891b8ab56d6a70b55492e021"
REQUIRED_WRITER = "9947b880bc789192a26b850ee53dc89d4c43a4c107bdf3fc549c65730739d58f"
REQUIRED_FIT = "6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657"
REQUIRED_FROZEN_EXPORT = "d87e6129c451bbdc51d49eb7745a31ebb64ab6108ac58d8f8c4948dcc13e18e8"
REQUIRED_FROZEN_SCRIPT = "8d188da27d3c9f802acdca76763e1ca05e714040cc5ea3722e4922853f28167c"
REQUIRED_NULL_CONTRACT = "ff8e6527f63b0afd727eed30444436ceae320cc336d9113a2634fd66d4aebad2"
REQUIRED_INJURY_PATHS = "ebd3dac083562afb4928e2ed756f617248894e636356f7426f0bc6ae58344e8b"
REQUIRED_BUILDER = "247744d23fef6f289e11da78523bdb007ada136f070916cf66a2bfee161e9cad"
REQUIRED_LE2023_DELTAS = "8af44a7eaa96ff695e10a61c827f942020c534f578ee36893701409857429394"
REQUIRED_LE2023_COMPARE = "bc89721f170be3c5b4435c70597565e515d52fd662eb522516c35e1087be7501"
REQUIRED_EXPORT = "a38a55bb765e977ed88f8808d76715faddf50098b2354b122a5499f0ec706ac8"
REQUIRED_EXPECTED = "0c31243dc3016610ece4cca53ee1fd3cfe0cdcded7e5c16d3ac966260367cd10"
REQUIRED_EXPECTED_COMMIT = "daf94a7d7383400cac78c5b8adf6ee4096ea83dd"
REQUIRED_HEAD = "8e2a15ac581277ecda71ea745c3b3477185d733b"
REQUIRED_RECORD_BASELINE_CSV = "502110cfc9293d96fd5635fbfdd3fad2c19367fa043ce3770cfbae05f2cdbe12"
REQUIRED_NFLVERSE_CLOSE = "634d8e730b20c31cafe925ab674a38076d124d619242efdfae140347ff212fc9"
RYAN_MESSAGE = "t4335s14919"
RYAN_VERBATIM = "CLEAR: build the runner, IMV reviews, then open once"
REQUEST_FOLD_RE = re.compile(r"season ∈ \{(\d{4}), (\d{4})\}")
VERDICT_ANCHORED = re.compile(r"^VERDICT: (PASS|RETURN|PASS WITH CONDITIONS|FAIL)$")
RUNNER_SHA_ANCHORED = re.compile(r"^RUNNER_SHA: ([0-9a-f]{64})$")
ALWAYS_FORBIDDEN = frozenset({2026})
ALLOWED_LE2023 = frozenset(range(2013, 2024))
LISTINGS_YEAR = re.compile(r"^listings_(\d{4})\.csv$")
ROSTER_YEAR = re.compile(r"^roster_(\d{4})\.csv$")
LISTINGS_HOLDOUT_NAME = re.compile(r"^listings_(2024|2025|2026)(?:\.csv)?$")
TIMESTAMP_FIELDS = ("source_ts", "as_of_ts", "kickoff_utc", "source_ts_home", "source_ts_away")
CLOSE_HEADERS = {
    "season",
    "week",
    "home",
    "away",
    "nflverse_spread_line_home",
    "nflverse_total_line",
    "home_score",
    "away_score",
}
SCHEDULE_HEADERS = {"season", "week", "home", "away", "gameday", "gametime"}
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
_BUILDER = None
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


def opening_pass_text_ok(text: str, self_sha: str) -> bool:
    """B-8a: exactly one anchored VERDICT line equal to PASS, plus RUNNER_SHA."""
    verdicts = [ln for ln in text.splitlines() if VERDICT_ANCHORED.match(ln)]
    if len(verdicts) != 1 or verdicts[0] != "VERDICT: PASS":
        return False
    runners: List[str] = []
    for ln in text.splitlines():
        match = RUNNER_SHA_ANCHORED.match(ln)
        if match:
            runners.append(match.group(1))
    return len(runners) == 1 and runners[0] == self_sha


def verified_opening_pass_sha() -> Optional[str]:
    """B-8a: exact IMV path, sidecar + 0444 + anchored VERDICT + RUNNER_SHA.

    No REQUIRED_OPENING_PASS constant. Does not read seeded/. Not a substring test.
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
        if not opening_pass_text_ok(text, self_sha):
            continue
        return got
    return None


def _file_0444_sidecar_ok(path: Path) -> bool:
    sidecar = Path(str(path) + ".abs.sha256")
    if not path.is_file() or not sidecar.is_file():
        return False
    if stat.S_IMODE(path.stat().st_mode) != 0o444:
        return False
    listed = sidecar.read_text(encoding="utf-8").strip().split()
    if not listed:
        return False
    return listed[0] == sha256_file(path)


def active_scorer_spec() -> Tuple[str, str]:
    """B-14: exactly one pinned scorer. No runtime switch."""
    return ACTIVE_SCORER_RELPATH, ACTIVE_SCORER_SHA


def active_scorer_sha() -> str:
    return ACTIVE_SCORER_SHA


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


def is_production_workspace(workspace: Path) -> bool:
    return workspace.resolve() == AUDIT_DIR.resolve()


def copy_fixture_to_temp(name: str) -> Path:
    """R-9: copy fixtures to a temp dir; never unlink in-package locks."""
    src = pkg_path("fixtures", name)
    dest_root = Path(tempfile.mkdtemp(prefix=f"opening-v6-{name}-"))
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
    _BASELINE = _load_py("baseline_method_v6", path)
    return _BASELINE


def import_builder():
    """B-4b: builder sha vs expected answers BEFORE import."""
    global _BUILDER
    if _BUILDER is not None:
        return _BUILDER
    expected = load_expected()
    path = pkg_path("holdout_frozen_row_builder.py")
    got = sha256_file(path)
    want = expected["frozen_row_builder_sha"]
    if got != want:
        die(f"B-4b builder sha {got} != expected {want}")
    if got != REQUIRED_BUILDER:
        die(f"B-4b builder sha {got} != REQUIRED_BUILDER")
    _BUILDER = _load_py("holdout_frozen_row_builder_v6", path)
    return _BUILDER


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
    _PRODUCER = _load_py("holdout_delta_producer_v6", path)
    return _PRODUCER


def assert_pins_before_lock() -> None:
    """ALL pins, including method/producer sha, before any lock write (B-1/B-5)."""
    pairs = (
        ("seeded/fit_object.json", REQUIRED_FIT),
        ("seeded/sealed_injury_export_d87e6129.json", REQUIRED_FROZEN_EXPORT),
        ("seeded/write_sealed_injury_export_ts_v1.py", REQUIRED_WRITER),
        ("seeded/run_injury_residual_fit.py", REQUIRED_FROZEN_SCRIPT),
        ("seeded/nfl_injury_null_contract_8e2a15ac.py", REQUIRED_NULL_CONTRACT),
        ("seeded/ca98ae0e/run_injury_residual_evaluator.py", REQUIRED_SCORER_CA98),
        ("seeded/v6.2/run_injury_residual_evaluator.py", ACTIVE_SCORER_SHA),
        ("seeded/v6.2-755d30a8/run_injury_residual_evaluator.py", REQUIRED_SCORER_V62_BASELINE),
        ("seeded/v6.2/DIFF_vs_755d30a8.txt", REQUIRED_V62_DIFF),
        ("seeded/injury_paths_8e2a15ac.py", REQUIRED_INJURY_PATHS),
        ("holdout_frozen_row_builder.py", REQUIRED_BUILDER),
        ("seeded/DECISION_RYAN_SCORER_V6_2.txt", REQUIRED_RYAN_SCORER_DECISION),
        ("seeded/IMV_RULING_NFL_INJURY_HOLDOUT_RUNNER_D2_v1.txt", REQUIRED_D2_RULING),
        ("seeded/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v1.txt", REQUIRED_OPENING_RETURN_V1),
        ("seeded/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v2.txt", REQUIRED_OPENING_RETURN_V2),
        ("seeded/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v3.txt", REQUIRED_OPENING_RETURN_V3),
        ("seeded/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v3_ERRATUM_v1.txt", REQUIRED_OPENING_RETURN_V3_ERRATUM),
        ("seeded/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v4.txt", REQUIRED_OPENING_RETURN_V4),
        ("seeded/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v5.txt", REQUIRED_OPENING_RETURN_V5),
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
    builder_sha = sha256_file(pkg_path("holdout_frozen_row_builder.py"))
    if builder_sha != expected["frozen_row_builder_sha"]:
        die(f"B-4b builder sha {builder_sha} != expected {expected['frozen_row_builder_sha']}")
    if expected["scorer_pin_active"] != ACTIVE_SCORER_SHA:
        die("active scorer pin in expected answers is not the single v6.2 sha")
    if expected["scorer_v6_2_status"] != "AUTHORIZED":
        die("v6.2 status drifted from AUTHORIZED")
    if expected["scorer_v6_2_sha"] != ACTIVE_SCORER_SHA:
        die("v6.2 sha drifted from the single pinned scorer")
    if expected.get("scorer_v6_2_imv_diff") != "DOCSTRING_ONLY_RECHECK":
        die("v6.2 IMV diff status drifted from DOCSTRING_ONLY_RECHECK")
    if expected.get("opening_runner_return_v5_sha") != REQUIRED_OPENING_RETURN_V5:
        die("v5 RETURN sha drifted")
    if expected.get("v62_sha_755d30a8") != REQUIRED_SCORER_V62_BASELINE:
        die("755d30a8 baseline drifted")
    if expected.get("scorer_v6_2_diff_vs_755d30a8_sha") != REQUIRED_V62_DIFF:
        die("L-1 DIFF sha drifted")
    if expected["runtime_scorer_switch"] is not False:
        die("B-14 expected answers still allow a runtime scorer switch")
    decision = expected["ryan_scorer_decision"]
    if decision["exact_path"] != str(RYAN_SCORER_DECISION):
        die("Ryan scorer decision path drifted")
    if decision["sha"] != REQUIRED_RYAN_SCORER_DECISION:
        die("Ryan scorer decision sha drifted")
    if sha256_file(RYAN_SCORER_DECISION) != REQUIRED_RYAN_SCORER_DECISION:
        die("Ryan scorer decision file at audit-dir path drifted")
    if expected["qb1_index_units"] != 0.12:
        die("QB1_INDEX_UNITS drifted")
    if expected["naive_timestamp"] != "STOP":
        die("B-4c naive_timestamp is not STOP")
    if expected["i3_field_name"] != "i3_holm_scorer":
        die("B-15 i3 field name drifted")
    method = import_baseline_method()
    import_builder()
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
    log(
        f"pins ok before lock method={method_sha[:8]} producer={producer_sha[:8]} "
        f"folds={f1}/{f2} b9={check['dal_car_2015_12_total']} scorer={active_scorer_sha()[:8]}"
    )


def hash_raw_inputs_before_parse(workspace: Path) -> Dict[str, str]:
    """B-4b(P): whole-file sha256 of every raw input before any row is parsed.

    Hashes listings_*.csv, schedule.csv, roster_*.csv, close.csv, games.json.
    Whole-file sha256 is not a row parse. Called after existence/stat and
    before csv.DictReader / json.loads of those files.
    """
    production = is_production_workspace(workspace)
    if production:
        games, close, schedule, listings, rosters = (
            PRODUCTION_GAMES,
            PRODUCTION_CLOSE,
            PRODUCTION_SCHEDULE,
            PRODUCTION_LISTINGS,
            PRODUCTION_ROSTERS,
        )
    else:
        games = workspace / "games.json"
        close = workspace / "close.csv"
        schedule = workspace / "schedule.csv"
        listings = workspace / "listings"
        rosters = workspace / "rosters"
    out: Dict[str, str] = {}
    for path, key in ((games, "games.json"), (close, "close.csv"), (schedule, "schedule.csv")):
        if path.is_file():
            out[key] = sha256_file(path)
    if listings.is_dir():
        for child in sorted(listings.iterdir()):
            if child.is_file() and LISTINGS_YEAR.match(child.name):
                out[child.name] = sha256_file(child)
    if rosters.is_dir():
        for child in sorted(rosters.iterdir()):
            if child.is_file() and ROSTER_YEAR.match(child.name):
                out[child.name] = sha256_file(child)
    required = {"games.json", "close.csv", "schedule.csv"}
    missing = sorted(k for k in required if k not in out)
    if missing:
        die(f"B-4b(P) raw_input_shas missing {missing}")
    if not any(k.startswith("listings_") for k in out):
        die("B-4b(P) raw_input_shas: no listings_*.csv hashed")
    if not any(k.startswith("roster_") for k in out):
        die("B-4b(P) raw_input_shas: no roster_*.csv hashed")
    log(f"B-4b(P) raw_input_shas n={len(out)} before any row parse production={production}")
    return out


def allowed_roster_years_for(workspace: Path) -> List[int]:
    years = load_expected()["allowed_roster_years"]
    if is_production_workspace(workspace):
        return list(years["production"])
    return list(years["synthetic"])


def _csv_header_only(path: Path) -> List[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle), None)
    if not header:
        die(f"B-13 header: empty {relpath(path)}")
    return [h.strip() for h in header]


def _json_games_probe(path: Path) -> None:
    with path.open("rb") as handle:
        raw = handle.read(4096)
    if not raw.lstrip().startswith(b"{"):
        die(f"B-13 header: {relpath(path)} is not a JSON object")
    if b'"games"' not in raw:
        die(f"B-13 header: {relpath(path)} missing games key in first 4096 bytes")


def assert_workspace_inputs_pre_lock(workspace: Path) -> Dict[str, str]:
    """B-13 existence/size, then B-4b(P) whole-file hash, then B-13 headers.

    Missing file STOPs before lock write. Raw shas are computed before any
    data row is parsed.
    """
    production = is_production_workspace(workspace)
    if production:
        games, close, schedule, listings, rosters = (
            PRODUCTION_GAMES,
            PRODUCTION_CLOSE,
            PRODUCTION_SCHEDULE,
            PRODUCTION_LISTINGS,
            PRODUCTION_ROSTERS,
        )
        label = "B-13 production input"
    else:
        games, close, schedule, listings, rosters = (
            workspace / "games.json",
            workspace / "close.csv",
            workspace / "schedule.csv",
            workspace / "listings",
            workspace / "rosters",
        )
        label = "B-13 workspace input"
    for path, kind in ((games, "file"), (close, "file"), (schedule, "file"), (listings, "dir"), (rosters, "dir")):
        if kind == "dir":
            if not path.is_dir():
                die(f"{label}: missing {path}")
            size = path.stat().st_size
            log(f"{label} size {relpath(path)}={size} (stat, not opened)")
            continue
        if not path.is_file():
            die(f"{label}: missing {path}")
        size = path.stat().st_size
        if size <= 0:
            die(f"{label}: empty {path}")
        log(f"{label} size {relpath(path)}={size} (stat, not opened)")
    raw_shas = hash_raw_inputs_before_parse(workspace)
    _json_games_probe(games)
    close_header = set(_csv_header_only(close))
    if not CLOSE_HEADERS.issubset(close_header):
        die(f"{label}: close headers {sorted(close_header)} missing {sorted(CLOSE_HEADERS - close_header)}")
    sched_header = set(_csv_header_only(schedule))
    if not SCHEDULE_HEADERS.issubset(sched_header):
        die(f"{label}: schedule headers {sorted(sched_header)} missing {sorted(SCHEDULE_HEADERS - sched_header)}")
    for child in sorted(listings.iterdir()):
        match = LISTINGS_YEAR.match(child.name)
        if not match:
            continue
        year = int(match.group(1))
        child_size = child.stat().st_size
        log(f"{label} size {child.name}={child_size} (stat, not opened)")
        if year in {2024, 2025, 2026}:
            continue
        header = set(_csv_header_only(child))
        if "date_modified" not in header:
            die(f"{label}: {child.name} header missing date_modified")
    log(f"{label} ok before lock production={production} raw_shas={len(raw_shas)}")
    return raw_shas


def lock_path(workspace: Path) -> Path:
    return workspace / LOCK_NAME


def consumed_path(workspace: Path) -> Path:
    return workspace / CONSUMED_NAME


def receipt_path(workspace: Path) -> Path:
    return workspace / "receipt.json"


def is_0444(path: Path) -> bool:
    return path.is_file() and stat.S_IMODE(path.stat().st_mode) == 0o444


def lock_payload(raw_input_shas: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
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
        "opening_runner_return_v3_sha": REQUIRED_OPENING_RETURN_V3,
        "opening_runner_return_v3_erratum_sha": REQUIRED_OPENING_RETURN_V3_ERRATUM,
        "opening_runner_return_v4_sha": REQUIRED_OPENING_RETURN_V4,
        "opening_runner_return_v5_sha": REQUIRED_OPENING_RETURN_V5,
        "opening_runner_pass_sha": verified_opening_pass_sha(),
        "spec_sha": REQUIRED_SPEC,
        "acceptance_sha": REQUIRED_ACCEPT,
        "runner_sha": runner_sha(),
        "scorer_sha": ACTIVE_SCORER_SHA,
        "scorer_v6_2_status": "AUTHORIZED",
        "scorer_v6_2_imv_diff": "DOCSTRING_ONLY_RECHECK",
        "scorer_v6_2_sha": ACTIVE_SCORER_SHA,
        "scorer_v6_2_baseline_755d30a8": REQUIRED_SCORER_V62_BASELINE,
        "scorer_v6_2_diff_vs_755d30a8_sha": REQUIRED_V62_DIFF,
        "ryan_scorer_decision_path": str(RYAN_SCORER_DECISION),
        "ryan_scorer_decision_sha": REQUIRED_RYAN_SCORER_DECISION,
        "frozen_row_builder_sha": expected["frozen_row_builder_sha"],
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
        "qb1_index_units": expected["qb1_index_units"],
        "raw_input_shas": dict(raw_input_shas or {}),
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
    payload = lock_payload(state.get("raw_input_shas"))
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
    sidecar = consumed_path(workspace)
    if is_0444(sidecar):
        log(f"lock consumed sidecar already 0444; not rewritten {relpath(sidecar)}")
        return
    lock_sha = sha256_file(path)
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
    schedule_path = workspace / "schedule.csv"
    rosters_dir = workspace / "rosters"
    if not games_path.is_file():
        die("O-1 export: fixture games.json absent after lock")
    if not schedule_path.is_file():
        die("O-1 export: schedule.csv absent after lock")
    if not rosters_dir.is_dir():
        die("O-1 export: rosters/ absent after lock")
    applied, built, pins = producer.produce_deltas(
        HERE,
        listings_dir=listings,
        schedule_path=schedule_path,
        rosters_dir=rosters_dir,
        games_json=games_path,
        allowed_roster_years=allowed_roster_years_for(workspace),
    )
    if len(applied) != len(built):
        die("B-4 producer row count drifted")
    if abs(float(pins.get("qb1_index_units") or 0) - 0.12) > 1e-12:
        die(f"B-4 QB1_INDEX_UNITS {pins.get('qb1_index_units')} != 0.12")
    for game in built:
        season = int(game.get("season") or 0)
        if not holdout_season_allowed(season, state):
            die(f"O-1 export: season {season} not allowed")
        state.setdefault("opened_seasons", []).append(season)
    state["producer_pins"] = pins
    state["producer_invoked"] = True
    state["builder_invoked"] = True
    games_export: List[Dict[str, Any]] = []
    for raw, app in zip(built, applied):
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
                "home": method.alias(row.get("home") or row.get("home_team") or ""),
                "away": method.alias(row.get("away") or row.get("away_team") or ""),
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
    rel, sha = active_scorer_spec()
    path = pkg_path(*rel.split("/"))
    if sha256_file(path) != sha:
        die("O-1 score: scorer sha drifted")
    mod = _load_py("scorer_active_" + sha[:8], path)
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
    """B-6: report the scorer holm list only. No runner p*(9-rank+1)."""
    i4 = result.get("i4") or {}
    boot = (result.get("bootstrap") or {}).get("spread_clv_delta") or {}
    metrics = result.get("metrics") or {}
    holm = result.get("holm") or []
    holm_map: Dict[str, Any] = {}
    holm_copy: List[Dict[str, Any]] = []
    for item in holm:
        copied = {
            "test_id": item.get("test_id"),
            "p": item.get("p"),
            "holm_rank": item.get("holm_rank"),
            "holm_threshold": item.get("holm_threshold"),
            "significant": item.get("significant"),
        }
        holm_copy.append(copied)
        holm_map[item["test_id"]] = copied
    for key in HOLM_NINE:
        holm_map.setdefault(key, None)
    return {
        "year": year,
        "n": int((result.get("missing") or {}).get("n_universe") or 0),
        "i1": {key: metrics.get(key) for key in HOLM_NINE},
        "i2": result.get("i2"),
        "i3_holm_scorer": holm_map,
        "i3_holm": holm_copy,
        "i3_holm_source": "scorer holm list only",
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
    if hasattr(scorer, "permit_holdout_scoring"):
        scorer.permit_holdout_scoring(
            lock_is_production=bool(state.get("lock_is_production")),
            pass_verified=bool(verified_opening_pass_sha()),
        )
    f1, f2, dry = fold_year_map(state)
    by = {
        "F1": ([row for row in universe if int(row["season"]) == f1], f1),
        "F2": ([row for row in universe if int(row["season"]) == f2], f2),
        "pooled": (list(universe), None),
    }
    out: Dict[str, Any] = {}
    label = "opening-runner v6 fixture" if dry else "opening-runner v6"
    for name, (rows, year) in by.items():
        result = scorer.score_universe(name, rows, label, dry_run_label=dry)
        out[name] = fold_slim(result, year)
    return out


def write_receipt_manifest(workspace: Path) -> Tuple[Optional[str], Optional[str]]:
    """B-6: MANIFEST after receipt 0444. SUMS = MANIFEST lines + MANIFEST hash. Both 0444."""
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
    sums = workspace / "RECEIPT_SHA256SUMS"
    if is_0444(man) or is_0444(sums):
        log("RECEIPT_MANIFEST/SUMS already 0444; not rewritten")
        return sha256_file(man) if man.is_file() else None, sha256_file(sums) if sums.is_file() else None
    man.write_text("\n".join(lines) + "\n", encoding="utf-8")
    man_sha = sha256_file(man)
    sums.write_text("\n".join(lines + [f"{man_sha}  RECEIPT_MANIFEST"]) + "\n", encoding="utf-8")
    os.chmod(man, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    os.chmod(sums, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    if stat.S_IMODE(man.stat().st_mode) != 0o444 or stat.S_IMODE(sums.stat().st_mode) != 0o444:
        die("B-6 RECEIPT_MANIFEST/SUMS mode != 0444")
    if man.read_text(encoding="utf-8") == sums.read_text(encoding="utf-8"):
        die("B-6 RECEIPT_MANIFEST and RECEIPT_SHA256SUMS must not be identical")
    return man_sha, sha256_file(sums)


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
    path = receipt_path(workspace)
    if is_0444(path):
        log(f"receipt already 0444; not rewritten {relpath(path)}")
        return json.loads(path.read_text(encoding="utf-8"))
    lock = dict(state.get("lock") or {})
    if consumed_path(workspace).is_file():
        lock["status"] = "consumed"
    expected = load_expected()
    receipt = {
        "kind": "opening_receipt",
        "opening_permitted": opening_permitted_computed(state),
        "holdout_years_opened": holdout_years_opened_computed(state, tz),
        "runner_sha": runner_sha(),
        "scorer_sha": ACTIVE_SCORER_SHA,
        "scorer_v6_2_status": "AUTHORIZED",
        "scorer_v6_2_imv_diff": "DOCSTRING_ONLY_RECHECK",
        "ryan_scorer_decision_sha": REQUIRED_RYAN_SCORER_DECISION,
        "frozen_row_builder_sha": expected["frozen_row_builder_sha"],
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
        "raw_input_shas": dict((state.get("lock") or {}).get("raw_input_shas") or state.get("raw_input_shas") or {}),
    }
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != 0o444:
        die(f"B-6 receipt: mode {oct(mode)} != 0444")
    man_sha, sums_sha = write_receipt_manifest(workspace)
    receipt["receipt_manifest_sha"] = man_sha
    receipt["receipt_sums_sha"] = sums_sha
    receipt["mode"] = "0444"
    log(f"receipt written {relpath(path)} mode=0444 manifest_after=true not_rewritten=true")
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


def _cleanup_after_lock(workspace: Path, state: Dict[str, Any], pin, tz, incomplete, missing, folds) -> None:
    """Every post-lock exception path: consume + receipt if not already 0444."""
    if not lock_path(workspace).exists():
        return
    try:
        mark_lock_consumed(workspace, "STOP after lock")
    except BaseException as exc:
        log(f"consume failed after lock: {exc!r}")
    try:
        if not is_0444(receipt_path(workspace)):
            write_receipt(
                workspace,
                state,
                pin,
                tz,
                incomplete,
                missing,
                folds,
                (LOG_LINES[-1] if LOG_LINES else "STOP after lock"),
                None,
            )
    except BaseException as exc:
        log(f"receipt failed after lock: {exc!r}")


def assert_week1_identity(joined: Sequence[Dict[str, Any]]) -> None:
    week1 = [row for row in joined if int(row["week"]) == 1]
    if not week1:
        return
    if abs(float(week1[0]["baseline_margin"]) - 1.05) > 1e-12:
        die(f"R-3 E2E week-1 baseline_margin {week1[0]['baseline_margin']} != 1.05")
    if abs(float(week1[0]["baseline_total"]) - 44.8435) > 1e-12:
        die(f"R-3 E2E week-1 baseline_total {week1[0]['baseline_total']} != 44.8435")
    log("week1 identity ok before receipt")


def run_holdout_workspace(workspace: Path) -> Dict[str, Any]:
    """B-1: pins → B-13 inputs → lock → chain → week-1 → consumed → receipt."""
    state: Dict[str, Any] = {"lock_written": False, "lock_is_production": False, "opened_seasons": []}
    assert_pins_before_lock()
    if lock_path(workspace).exists():
        die(f"O-3 lock: existing lock {relpath(lock_path(workspace))}")
    raw_shas = assert_workspace_inputs_pre_lock(workspace)
    state["raw_input_shas"] = raw_shas
    pin = tz = incomplete = missing = folds = None
    try:
        write_lock(workspace, state)
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
        assert_week1_identity(joined)
        mark_lock_consumed(workspace, "opened once")
        ws_log = workspace / "runner.log"
        ws_log.write_text("\n".join(LOG_LINES) + ("\n" if LOG_LINES else ""), encoding="utf-8")
        receipt = write_receipt(workspace, state, pin, tz, incomplete, missing, folds, None, sha256_file(ws_log))
        log("sequence ok: pins inputs lock export guards join score week1 consumed receipt")
        return receipt
    except BaseException:
        _cleanup_after_lock(workspace, state, pin, tz, incomplete, missing, folds)
        raise


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Holdout opening runner v6 (2c71e4d0 L-1/B-4b). No real opening.")
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
    log("opening runner v6 ok:true (no 2024/25 open; real lock not written; scorer pin 8b482cb9)")
    return 0


def run_fixtures(expected: Dict[str, Any], out_dir: Path) -> Dict[str, Any]:
    results: Dict[str, Any] = {}

    def f_default() -> None:
        main(["--mode", "holdout"])

    results["F-DEFAULT-HOLDOUT"] = require_stop(capture_stop(f_default), expected["F-DEFAULT-HOLDOUT"]["must_contain"], "F-DEFAULT-HOLDOUT")
    if REAL_LOCK.exists():
        die("F-DEFAULT-HOLDOUT wrote the real lock")

    def f_production_inputs() -> None:
        main(["--mode", "holdout", "--workspace", str(REAL_LOCK.parent)])


    prod_input_text = capture_stop(f_production_inputs)
    results["F-PRODUCTION-INPUTS-MISSING"] = require_stop(
        prod_input_text, expected["F-PRODUCTION-INPUTS-MISSING"]["must_contain"], "F-PRODUCTION-INPUTS-MISSING"
    )
    if "pins ok before lock" not in prod_input_text:
        die("B-13 F-PRODUCTION-INPUTS-MISSING did not check pins before lock attempt")
    if REAL_LOCK.exists():
        die("F-PRODUCTION-INPUTS-MISSING wrote the real lock")
    if (REAL_LOCK.parent / "receipt.json").exists():
        die("F-PRODUCTION-INPUTS-MISSING wrote a receipt into the audit dir")

    def f_production_lock() -> None:
        state: Dict[str, Any] = {"lock_written": False, "lock_is_production": False}
        write_lock(REAL_LOCK.parent, state)

    prod_lock_text = capture_stop(f_production_lock)
    results["F-PRODUCTION-LOCK-BLOCKED"] = require_stop(
        prod_lock_text, expected["F-PRODUCTION-LOCK-BLOCKED"]["must_contain"], "F-PRODUCTION-LOCK-BLOCKED"
    )
    if REAL_LOCK.exists():
        die("F-PRODUCTION-LOCK-BLOCKED wrote the real lock")

    e2e = copy_fixture_to_temp("e2e")

    def f_e2e() -> int:
        return main(["--mode", "holdout", "--workspace", str(e2e)])

    rc = f_e2e()
    if rc != 0:
        die("F-E2E did not return 0")
    lock = e2e / LOCK_NAME
    consumed = e2e / CONSUMED_NAME
    receipt_path_e2e = e2e / "receipt.json"
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
    if lock_doc.get("qb1_index_units") != 0.12:
        die("F-E2E lock missing QB1_INDEX_UNITS 0.12")
    if not receipt_path_e2e.is_file() or stat.S_IMODE(receipt_path_e2e.stat().st_mode) != 0o444:
        die("F-E2E receipt missing or not 0444")
    receipt = json.loads(receipt_path_e2e.read_text(encoding="utf-8"))
    if receipt.get("kind") != "opening_receipt" or not receipt.get("consumed"):
        die(f"F-E2E receipt {receipt}")
    if not receipt.get("writer_invoked") or not receipt.get("producer_invoked"):
        die("F-E2E writer/producer not invoked")
    if receipt.get("frozen_row_builder_sha") != expected["frozen_row_builder_sha"]:
        die("F-E2E receipt missing builder pin")
    if lock_doc.get("frozen_row_builder_sha") != expected["frozen_row_builder_sha"]:
        die("F-E2E lock missing builder pin")
    if lock_doc.get("scorer_sha") != ACTIVE_SCORER_SHA:
        die("F-E2E lock scorer is not the single v6.2 pin")
    if lock_doc.get("ryan_scorer_decision_sha") != REQUIRED_RYAN_SCORER_DECISION:
        die("F-E2E lock missing Ryan scorer decision sha")
    raw_lock = lock_doc.get("raw_input_shas") or {}
    raw_receipt = receipt.get("raw_input_shas") or {}
    need_raw = ["listings_2098.csv", "listings_2099.csv", "schedule.csv", "roster_2098.csv", "roster_2099.csv", "close.csv", "games.json"]
    for key in need_raw:
        if key not in raw_lock:
            die(f"F-E2E lock raw_input_shas missing {key}")
        if raw_lock[key] != raw_receipt.get(key):
            die(f"F-E2E receipt raw_input_shas drifted {key}")
        if key.startswith("listings_"):
            path = e2e / "listings" / key
        elif key.startswith("roster_"):
            path = e2e / "rosters" / key
        else:
            path = e2e / key
        if sha256_file(path) != raw_lock[key]:
            die(f"F-E2E raw_input_shas {key} != on-disk")
    if receipt.get("holdout_years_opened") or receipt.get("opening_permitted"):
        die("F-E2E opened real holdout")
    if receipt.get("runner_sha") != runner_sha() or receipt.get("scorer_sha") != REQUIRED_SCORER:
        die("F-E2E receipt missing top-level runner/scorer sha")
    if receipt.get("scorer_sha") != REQUIRED_SCORER:
        die("F-E2E scorer pin is not the single v6.2 sha")
    pooled = (receipt.get("folds") or {}).get("pooled") or {}
    if "i1" not in pooled or "i3_holm_scorer" not in pooled or "k2" not in pooled:
        die("F-E2E fold_slim missing I-1 / Holm / K-2")
    if set((pooled.get("i3_holm_scorer") or {})) != set(HOLM_NINE):
        die("F-E2E Holm keys != HOLM_NINE")
    if "i3_holm_adjusted_p" in pooled:
        die("F-E2E still uses i3_holm_adjusted_p")
    if pooled.get("i3_holm_source") != "scorer holm list only":
        die("F-E2E holm source is not scorer-only")
    for item in pooled.get("i3_holm") or []:
        if "p_holm_adj" in item:
            die("F-E2E runner reimplemented Holm-adjusted p")
    man = e2e / "RECEIPT_MANIFEST"
    sums = e2e / "RECEIPT_SHA256SUMS"
    if not man.is_file() or not sums.is_file():
        die("F-E2E receipt MANIFEST/SUMS missing")
    if stat.S_IMODE(man.stat().st_mode) != 0o444 or stat.S_IMODE(sums.stat().st_mode) != 0o444:
        die("F-E2E RECEIPT_MANIFEST/SUMS not 0444")
    if man.read_text(encoding="utf-8") == sums.read_text(encoding="utf-8"):
        die("F-E2E RECEIPT_MANIFEST identical to SUMS")
    if "week1 identity ok before receipt" not in "\n".join(LOG_LINES):
        die("F-E2E week-1 identity did not run before receipt")
    export = json.loads(export_path.read_text(encoding="utf-8"))
    for game in export.get("games") or []:
        if int(game["season"]) in request_holdout_years():
            die("F-E2E export contains real holdout year")
    if REAL_LOCK.exists():
        die("F-E2E wrote the real lock")
    (out_dir / "synthetic").mkdir(parents=True, exist_ok=True)
    dest_receipt = out_dir / "synthetic" / "receipt.json"
    if dest_receipt.exists():
        dest_receipt.chmod(stat.S_IWUSR | stat.S_IRUSR)
    shutil.copy2(receipt_path_e2e, dest_receipt)
    dest_receipt.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    results["F-E2E"] = {
        "stop": False,
        "writer_invoked": True,
        "producer_invoked": True,
        "receipt_kind": receipt.get("kind"),
        "export_on_disk_sha": receipt.get("export_on_disk_sha"),
        "n_incomplete": (receipt.get("incomplete") or {}).get("n_incomplete"),
        "i4": pooled.get("i4"),
        "fold_years": {"F1": (receipt.get("folds") or {}).get("F1", {}).get("year"), "F2": (receipt.get("folds") or {}).get("F2", {}).get("year")},
        "scorer_sha": receipt.get("scorer_sha"),
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

    src = pkg_path("run_injury_holdout_opening.py").read_text(encoding="utf-8")
    if re.search(r"^def ryan_scorer_v62_authorized\(", src, re.M):
        die("F-SCORER-PINNED-V62: runtime switch function still present")
    if active_scorer_sha() != ACTIVE_SCORER_SHA or ACTIVE_SCORER_SHA != REQUIRED_SCORER:
        die("F-SCORER-PINNED-V62: active pin is not the single v6.2 sha")
    if expected["ryan_scorer_decision"]["sha"] != REQUIRED_RYAN_SCORER_DECISION:
        die("F-SCORER-PINNED-V62: decision sha drifted")
    scorer_text = pkg_path("seeded", "v6.2", "run_injury_residual_evaluator.py").read_text(encoding="utf-8")
    doc = scorer_text.split('"""', 2)
    header = doc[1] if len(doc) > 2 else scorer_text[:800]
    if "DRAFT" in header or "PENDING_RYAN" in header:
        die("F-SCORER-PINNED-V62: active scorer docstring still says DRAFT/PENDING_RYAN")
    if sha256_file(pkg_path("seeded", "v6.2", "run_injury_residual_evaluator.py")) != ACTIVE_SCORER_SHA:
        die("F-SCORER-PINNED-V62: on-disk scorer sha drifted")
    if sha256_file(pkg_path("seeded", "v6.2-755d30a8", "run_injury_residual_evaluator.py")) != REQUIRED_SCORER_V62_BASELINE:
        die("F-SCORER-PINNED-V62: 755d30a8 baseline drifted")
    if sha256_file(pkg_path("seeded", "v6.2", "DIFF_vs_755d30a8.txt")) != REQUIRED_V62_DIFF:
        die("F-SCORER-PINNED-V62: DIFF sha drifted")
    if (HERE / "seeded" / "v6.2-draft").exists():
        die("F-SCORER-PINNED-V62: seeded/v6.2-draft still present")
    results["F-SCORER-PINNED-V62"] = {
        "stop": False,
        "active": ACTIVE_SCORER_SHA,
        "baseline_755d30a8": REQUIRED_SCORER_V62_BASELINE,
        "diff_sha": REQUIRED_V62_DIFF,
        "decision_sha": REQUIRED_RYAN_SCORER_DECISION,
        "runtime_switch": False,
        "docstring_draft": False,
    }

    v2_text = pkg_path("seeded", "IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v2.txt").read_text(encoding="utf-8")
    if opening_pass_text_ok(v2_text, runner_sha()):
        die("F-B8A-SUBSTRING-REJECT accepted RETURN v2 substring")
    fake_pass = "VERDICT: PASS\nRUNNER_SHA: " + ("0" * 64) + "\n"
    if opening_pass_text_ok(fake_pass, runner_sha()):
        die("F-B8A-SUBSTRING-REJECT accepted mismatched RUNNER_SHA")
    two_verdicts = "VERDICT: RETURN\nVERDICT: PASS\nRUNNER_SHA: " + runner_sha() + "\n"
    if opening_pass_text_ok(two_verdicts, runner_sha()):
        die("F-B8A-SUBSTRING-REJECT accepted two VERDICT lines")
    exact = "header\nVERDICT: PASS\nRUNNER_SHA: " + runner_sha() + "\n"
    if not opening_pass_text_ok(exact, runner_sha()):
        die("F-B8A-SUBSTRING-REJECT rejected a well-formed PASS")
    results["F-B8A-SUBSTRING-REJECT"] = {"stop": False, "substring_rejected": True, "exact_accepted": True}

    ca98 = _load_py("scorer_guard_ca98ae0e", pkg_path("seeded", "ca98ae0e", "run_injury_residual_evaluator.py"))
    v62 = _load_py("scorer_guard_v62", pkg_path("seeded", "v6.2", "run_injury_residual_evaluator.py"))
    if not {2024, 2025, 2026}.issubset(set(ca98.FORBIDDEN)):
        die("F-SCORER-GUARDS-CLOSED ca98ae0e FORBIDDEN drifted")
    for year in (2024, 2025, 2026):
        if not v62._season_blocked(year):
            die(f"F-SCORER-GUARDS-CLOSED v6.2 default admitted {year}")
    if v62._season_blocked(2023) or v62._season_blocked(2098):
        die("F-SCORER-GUARDS-CLOSED v6.2 default blocked a non-holdout year")
    v62.permit_holdout_scoring(lock_is_production=True, pass_verified=True)
    if v62._season_blocked(2024) or v62._season_blocked(2025):
        die("F-SCORER-GUARDS-CLOSED v6.2 permit still blocks 2024/2025")
    if not v62._season_blocked(2026):
        die("F-SCORER-GUARDS-CLOSED v6.2 permit admitted 2026")
    results["F-SCORER-GUARDS-CLOSED"] = {"stop": False, "default_closed": True, "permit_2024_2025": True, "year_2026": "never"}
    producer = import_producer()
    naive_dir = Path(tempfile.mkdtemp(prefix="opening-v6-naive-"))
    naive_listings = naive_dir / "listings"
    naive_listings.mkdir()
    text = pkg_path("fixtures", "e2e", "listings", "listings_2098.csv").read_text(encoding="utf-8")
    (naive_listings / "listings_2098.csv").write_text(text.replace("Z", ""), encoding="utf-8")
    try:
        producer.produce_deltas(
            HERE,
            listings_dir=naive_listings,
            schedule_path=pkg_path("fixtures", "e2e", "schedule.csv"),
            rosters_dir=pkg_path("fixtures", "e2e", "rosters"),
            allowed_roster_years=load_expected()["allowed_roster_years"]["synthetic"],
        )
    except AssertionError as exc:
        if "B-4c refuse: naive/zoneless timestamp" not in str(exc):
            die(f"F-NAIVE-TIMESTAMP wrong error {exc}")
    else:
        die("F-NAIVE-TIMESTAMP did not STOP")
    results["F-NAIVE-TIMESTAMP"] = {"stop": True, "naive": "STOP"}

    bad_games = naive_dir / "games.json"
    bad_games.write_text('{"games":[{"season":2098,"week":1,"home":"AAA","away":"BBB","delta_margin":1}]}\n', encoding="utf-8")
    try:
        producer.produce_deltas(
            HERE,
            listings_dir=pkg_path("fixtures", "e2e", "listings"),
            schedule_path=pkg_path("fixtures", "e2e", "schedule.csv"),
            rosters_dir=pkg_path("fixtures", "e2e", "rosters"),
            games_json=bad_games,
            allowed_roster_years=load_expected()["allowed_roster_years"]["synthetic"],
        )
    except AssertionError as exc:
        if "games.json carries deltas" not in str(exc):
            die(f"F-GAMES-JSON-VALUES wrong error {exc}")
    else:
        die("F-GAMES-JSON-VALUES did not STOP")
    results["F-GAMES-JSON-VALUES"] = {"stop": True, "games_json_values": "refused"}

    log("F-E2E lock export guards join score week1 receipt ok; F-MARKER-NO-2024 F-SCORER-PINNED-V62 F-B8A F-SCORER-GUARDS F-NAIVE F-GAMES-JSON ok")

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

    boom = copy_fixture_to_temp("e2e")
    original_score = score_folds

    def boom_score(*_a, **_k):
        raise ValueError("injected post-lock BaseException")

    globals()["score_folds"] = boom_score
    try:

        def f_boom() -> None:
            main(["--mode", "holdout", "--workspace", str(boom)])

        try:
            f_boom()
        except ValueError:
            pass
        else:
            die("F-POST-LOCK-BASEEXCEPTION did not raise ValueError")
        if not is_0444(boom / CONSUMED_NAME):
            die("F-POST-LOCK-BASEEXCEPTION missing consumed 0444")
        if not is_0444(boom / "receipt.json"):
            die("F-POST-LOCK-BASEEXCEPTION missing receipt 0444")
        if not is_0444(boom / LOCK_NAME):
            die("F-POST-LOCK-BASEEXCEPTION lock not left 0444")
        first_receipt = (boom / "receipt.json").read_bytes()
        _cleanup_after_lock(boom, {"lock": json.loads((boom / LOCK_NAME).read_text(encoding="utf-8"))}, None, None, None, None, None)
        if (boom / "receipt.json").read_bytes() != first_receipt:
            die("F-POST-LOCK-BASEEXCEPTION rewrote 0444 receipt")
        results["F-POST-LOCK-BASEEXCEPTION"] = {"stop": True, "consumed": True, "receipt_0444": True, "lock_unrewritten": True}
    finally:
        globals()["score_folds"] = original_score

    log(
        "fixtures: F-DEFAULT-HOLDOUT F-PRODUCTION-INPUTS-MISSING F-PRODUCTION-LOCK-BLOCKED "
        "F-LOCK-PRESENT F-DOUBLE-OPEN F-REFIT F-PER-SIDE F-POST-LOCK-BASEEXCEPTION STOP; "
        "F-E2E F-MARKER-NO-2024 F-SCORER-PINNED-V62 F-B8A-SUBSTRING-REJECT F-SCORER-GUARDS-CLOSED F-NAIVE-TIMESTAMP F-GAMES-JSON-VALUES recorded"
    )
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
    builder = import_builder()
    compare = builder.deposit_le2023_rebuild(HERE, out_dir)
    deltas_path = out_dir / "rebuilt_le2023_deltas.json"
    compare_path = out_dir / "rebuilt_le2023_compare.json"
    deltas_sha = sha256_file(deltas_path)
    compare_sha = sha256_file(compare_path)
    if deltas_sha != REQUIRED_LE2023_DELTAS:
        die(f"B-4b(R) rebuilt deltas sha {deltas_sha} != {REQUIRED_LE2023_DELTAS}")
    if compare_sha != REQUIRED_LE2023_COMPARE:
        die(f"B-4b(R) compare sha {compare_sha} != {REQUIRED_LE2023_COMPARE}")
    if compare.get("verdict") != "0_DIFF":
        die(f"B-4b(R) compare verdict {compare.get('verdict')} != 0_DIFF")
    if int(compare.get("n_delta_margin_diff") or 1) or int(compare.get("n_delta_total_diff") or 1):
        die("B-4b(R) compare is not 0-diff")
    deposited = json.loads(deltas_path.read_text(encoding="utf-8"))
    if deposited.get("n") != 2863 or len(deposited.get("games") or []) != 2863:
        die(f"B-4b(R) deposited n={deposited.get('n')} games={len(deposited.get('games') or [])}")
    payload["le2023_rebuild"] = {
        "deposited_deltas_relpath": "out/le2023/rebuilt_le2023_deltas.json",
        "deposited_deltas_sha": deltas_sha,
        "deposited_compare_relpath": "out/le2023/rebuilt_le2023_compare.json",
        "deposited_compare_sha": compare_sha,
        "verdict": compare.get("verdict"),
        "n_rows": deposited.get("n"),
        "export_sha": compare.get("export_sha"),
    }
    (out_dir / "d2_results.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "provenance.md").write_text(
        "\n".join(
            [
                "# Provenance le2023 (guards + B-4b(R) rebuild; not an opening)",
                f"- excluded_game_ids={incomplete['excluded_game_ids']}",
                f"- n_incomplete={incomplete['n_incomplete']} by_season={incomplete['n_incomplete_by_season']}",
                f"- listings Z={tz['n_z']}/{tz['n_listings']} naive={tz['n_naive']}",
                f"- rebuilt_le2023_deltas.json sha={deltas_sha} n={deposited.get('n')}",
                f"- rebuilt_le2023_compare.json sha={compare_sha} verdict={compare.get('verdict')} vs a38a55bb",
                "- 2024/25: not opened. Real lock: not written. Join: not run on holdout.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    log(f"le2023 guards: listings={tz['n_listings']} Z={tz['n_z']} n_incomplete={incomplete['n_incomplete']} rebuild={compare.get('verdict')} n={deposited.get('n')}")
    return payload


def write_report(out_dir: Path, fixtures: Dict[str, Any], le2023: Optional[Dict[str, Any]], log_sha: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Opening runner v6 report (2c71e4d0 L-1/B-4b(R)/B-4b(P)/B-4b(n))",
        "",
        f"RETURN `2c71e4d0`. Ryan `{RYAN_MESSAGE}` / `fabf8732`. Scorer decision t4340s14953 / `592e0bb9`. V62 PASS on `755d30a8`. Real lock not written. 2024/25 not opened.",
        f"Expected answers commit `{REQUIRED_EXPECTED_COMMIT}` before this runner. Active scorer `8b482cb9`. L-1 DIFF `280d9785`. Log sha `{log_sha}`.",
        "",
        "## Fixtures",
        "",
    ]
    for key in (
        "F-DEFAULT-HOLDOUT",
        "F-PRODUCTION-INPUTS-MISSING",
        "F-PRODUCTION-LOCK-BLOCKED",
        "F-LOCK-PRESENT",
        "F-DOUBLE-OPEN",
        "F-REFIT",
        "F-PER-SIDE",
        "F-POST-LOCK-BASEEXCEPTION",
        "F-E2E",
        "F-MARKER-NO-2024",
        "F-SCORER-PINNED-V62",
        "F-B8A-SUBSTRING-REJECT",
        "F-SCORER-GUARDS-CLOSED",
        "F-NAIVE-TIMESTAMP",
        "F-GAMES-JSON-VALUES",
    ):
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
                f"- B-4b(R) rebuild { (le2023.get('le2023_rebuild') or {}).get('verdict') } n={(le2023.get('le2023_rebuild') or {}).get('n_rows')} deltas={(le2023.get('le2023_rebuild') or {}).get('deposited_deltas_sha')}",
            ]
        )
    lines.extend(["", "NO-GO. Coming Soon ON. No merge. No real lock. No opening.", ""])
    (out_dir / "opening-report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
