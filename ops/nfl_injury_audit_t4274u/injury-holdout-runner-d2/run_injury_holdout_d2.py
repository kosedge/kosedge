#!/usr/bin/env python3
"""D-2 holdout runner — listings TZ, incomplete-row, provenance IDs, on-disk .v2 pin.

Ryan CLEAR fabf8732 (t4335s14919): "CLEAR: build the runner, IMV reviews, then open once".
IMV 8ca00bc4 + erratum 14ac1819. Request v3.1 35cbb56e.

This file implements D-2 only. --mode holdout dies before any path is opened.
No 2024/25 read. No tokens. No lock. No NFL_TOTALS_*. Fail closed.
Expected answers (e46b4fec) were filed in commit ff3b3b0b before this runner.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent

REQUIRED_DECISION = "fabf87320453c274b2b8ec8e443b8af4709d8d24ff8fb6baa449fe3d739d4bd0"
REQUIRED_READINESS_V6 = "8ca00bc49b412c1524b4a0d5a1ebacdd7bc4fe26f3e6354d52cb549812dbb012"
REQUIRED_ERRATUM_V6 = "14ac18190c89d3620a6f27d0a0be64fc8147c321063ca4aeaa459faa31fcde41"
REQUIRED_REQUEST_V31 = "35cbb56e10cfe0ec3730441a453f171bda917e7c58ad3e5eb2fe2c573de5ef7b"
REQUIRED_SPEC = "a156459b545e3b7d6a483f1db34cda7a4d32fc3afc70ed499b3adc726b1b6881"
REQUIRED_ACCEPT = "54bc78ecc70e6a440481253b9c7eeef0e749690e893f501862f5dd5c54444574"
REQUIRED_EXPORT = "a38a55bb765e977ed88f8808d76715faddf50098b2354b122a5499f0ec706ac8"
REQUIRED_EXPORT_BLOB_NOT_A_PIN = "46d2a5657d1b5a5eb1af03f4d643afbfaa4762f31260daff439b5df1ac1456eb"
REQUIRED_EXPECTED = "e46b4fec5bdf892291c1f1617f59a5b1bd0d6f90d1e288fd005a149542260043"
REQUIRED_EXPECTED_COMMIT = "ff3b3b0bfe91a42d4165a2cd81d5a811277b38c7"
REQUIRED_HEAD = "8e2a15ac581277ecda71ea745c3b3477185d733b"
RYAN_MESSAGE = "t4335s14919"
RYAN_VERBATIM = "CLEAR: build the runner, IMV reviews, then open once"

FORBIDDEN_SEASONS = frozenset({2024, 2025, 2026})
ALLOWED_LE2023 = frozenset(range(2013, 2024))
LISTINGS_YEAR = re.compile(r"^listings_(\d{4})\.csv$")
LISTINGS_HOLDOUT_NAME = re.compile(r"^listings_(2024|2025|2026)(?:\.csv)?$")

NULL_FIELDS = (
    "delta_margin",
    "delta_total",
    "source_ts",
    "as_of_ts",
    "kickoff_utc",
    "source_ts_home",
    "source_ts_away",
)
TIMESTAMP_FIELDS = ("source_ts", "as_of_ts", "kickoff_utc", "source_ts_home", "source_ts_away")
LE2023_EXCLUDED = (
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
)
TOKEN_NAMES = ("RYAN_CLEAR_ON_FROZEN_RECORD", "IMV_PASS", "CLEAR", "RYAN_CLEAR", "holdout-once.lock")

NFL_TOTALS_PREFIX = "NFL_TOTALS_"


def log(msg: str) -> None:
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


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


def pkg_path(*parts: str) -> Path:
    path = HERE.joinpath(*parts)
    assert_path_not_holdout(path)
    return path


def relpath(path: Path) -> str:
    try:
        return path.resolve().relative_to(HERE).as_posix()
    except ValueError:
        return path.name


def assert_env_clean() -> None:
    leaked = sorted(k for k in os.environ if k.startswith(NFL_TOTALS_PREFIX))
    if leaked:
        die(f"D-2 refuse: {leaked} set")


def assert_no_tokens() -> None:
    for name in TOKEN_NAMES:
        candidate = HERE / name
        if candidate.exists():
            die(f"D-2 refuse: token or lock present {candidate.name}")


def assert_path_not_holdout(path: Path) -> None:
    match = LISTINGS_HOLDOUT_NAME.match(path.name)
    if match:
        die(f"D-2 refuse: holdout year {match.group(1)} in path {path}")
    for part in path.parts:
        if part in {str(y) for y in FORBIDDEN_SEASONS}:
            die(f"D-2 refuse: holdout year {part} in path {path}")


def is_null_field(value: Any) -> bool:
    return value is None or str(value).strip() == ""


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


def pin_export_v2(export_path: Path, sidecar_path: Optional[Path] = None) -> Dict[str, str]:
    assert_path_not_holdout(export_path)
    sidecar = sidecar_path or Path(str(export_path) + ".sha256.v2")
    assert_path_not_holdout(sidecar)
    if not sidecar.is_file():
        die(f"D-2 export pin: missing on-disk .v2 sidecar {relpath(sidecar)}")
    line = sidecar.read_text(encoding="utf-8").strip()
    parts = line.split()
    if len(parts) != 2:
        die(f"D-2 export pin: sidecar must be '{{sha256}}  {{basename}}' got {line!r}")
    listed_sha, listed_name = parts
    if listed_name != export_path.name:
        die(f"D-2 export pin: sidecar basename {listed_name} != {export_path.name}")
    if not export_path.is_file():
        die(f"D-2 export pin: missing export {export_path}")
    on_disk = sha256_file(export_path)
    raw = export_path.read_bytes()
    blob = sha256_bytes(raw[:-1] if raw.endswith(b"\n") else raw)
    if listed_sha == blob and listed_sha != on_disk:
        die("D-2 export pin: sidecar uses blob hash; pin must be on-disk sha")
    if listed_sha != on_disk:
        die(f"D-2 export pin: sidecar sha != on-disk sha (blob hash is not a pin) listed={listed_sha} on_disk={on_disk}")
    if on_disk == REQUIRED_EXPORT_BLOB_NOT_A_PIN:
        die("D-2 export pin: on-disk sha is the blob hash; pin must be a38a55bb-style")
    return {"on_disk_sha": on_disk, "blob_sha_not_a_pin": blob, "sidecar": sidecar.as_posix()}


def census_listings_tz(listings_dir: Path, allowed_years: Iterable[int]) -> Dict[str, Any]:
    assert_path_not_holdout(listings_dir)
    allowed = frozenset(int(y) for y in allowed_years)
    if not allowed:
        die("D-2 listings TZ: no allowed years")
    if allowed & FORBIDDEN_SEASONS:
        die("D-2 listings TZ: allowed years include a holdout year")
    if not listings_dir.is_dir():
        die(f"D-2 listings TZ: missing directory {listings_dir}")
    names = sorted(p.name for p in listings_dir.iterdir() if p.is_file())
    for name in names:
        match = LISTINGS_YEAR.match(name)
        if match and int(match.group(1)) in FORBIDDEN_SEASONS:
            die(f"D-2 refuse: holdout year {match.group(1)} in path {listings_dir / name}")
    counts: Counter[str] = Counter()
    years_opened: List[int] = []
    n_rows = 0
    examples: Dict[str, str] = {}
    for year in sorted(allowed):
        path = listings_dir / f"listings_{year}.csv"
        assert_path_not_holdout(path)
        if not path.is_file():
            die(f"D-2 listings TZ: missing listings_{year}.csv")
        years_opened.append(year)
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "date_modified" not in reader.fieldnames:
                die(f"D-2 listings TZ: {path.name} has no date_modified column")
            for row in reader:
                season_raw = str(row.get("season") or "").strip()
                if season_raw.isdigit() and int(season_raw) in FORBIDDEN_SEASONS:
                    die(f"D-2 refuse: holdout season {season_raw} inside {path.name}")
                kind = classify_date_modified(row.get("date_modified"))
                counts[kind] += 1
                n_rows += 1
                if kind not in examples:
                    examples[kind] = str(row.get("date_modified") or "")
                if kind == "naive":
                    die(f"D-2 listings TZ: naive/zoneless date_modified file={path.name} value={row.get('date_modified')!r}")
    if counts.get("empty", 0) or counts.get("other", 0):
        die(
            "D-2 listings TZ: empty/other date_modified "
            f"n_empty={counts.get('empty', 0)} n_other={counts.get('other', 0)} examples={examples}"
        )
    return {
        "n_listings": n_rows,
        "n_z": counts.get("z", 0),
        "n_offset": counts.get("offset", 0),
        "n_naive": counts.get("naive", 0),
        "n_empty": counts.get("empty", 0),
        "n_other": counts.get("other", 0),
        "years_opened": years_opened,
        "examples": examples,
    }


def load_export_games(export_path: Path) -> List[Dict[str, Any]]:
    assert_path_not_holdout(export_path)
    doc = json.loads(export_path.read_text(encoding="utf-8"))
    games = list(doc.get("games") or [])
    for game in games:
        season = int(game.get("season") or 0)
        if season in FORBIDDEN_SEASONS:
            die(f"D-2 refuse: export contains holdout season {season}")
    return games


def apply_incomplete_row_rule(
    games: Sequence[Dict[str, Any]],
    state: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
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
        if complete and any(is_null_field(game.get(key)) for key in ("source_ts", "as_of_ts", "kickoff_utc")):
            die(f"D-2 incomplete: complete row has a null timestamp game_id={gid}")
        if (not complete) and has_ts:
            die(f"D-2 incomplete: incomplete row has a timestamp game_id={gid}")
        if not complete:
            for key in ("delta_margin", "delta_total"):
                if not is_null_field(game.get(key)):
                    die(f"D-2 incomplete: incomplete row has non-null {key} game_id={gid}")
            for key in TIMESTAMP_FIELDS:
                if not is_null_field(game.get(key)):
                    die(f"D-2 incomplete: incomplete row has a timestamp game_id={gid} field={key}")
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


def join_close_or_outcome(state: Dict[str, Any], rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not state.get("tz_census_done"):
        die("D-2 order: listings TZ census must run before any join")
    if not state.get("incomplete_done"):
        die("D-2 order: incomplete-row count must be taken before any join")
    state["joined"] = True
    die("D-2 join: close/outcome join is not permitted in this D-2 package")
    return list(rows)


def write_run_provenance(
    out_dir: Path,
    *,
    pin: Dict[str, str],
    tz: Dict[str, Any],
    incomplete: Dict[str, Any],
    kind: str,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Provenance {kind}",
        "",
        "No secrets. Paths are package-relative.",
        f"- Ryan CLEAR: message `{RYAN_MESSAGE}`; decision `{REQUIRED_DECISION}`",
        f"- Verbatim: `{RYAN_VERBATIM}`",
        f"- IMV v6 `{REQUIRED_READINESS_V6}` erratum `{REQUIRED_ERRATUM_V6}` request `{REQUIRED_REQUEST_V31}`",
        f"- Expected answers file `{REQUIRED_EXPECTED}` commit `{REQUIRED_EXPECTED_COMMIT}`",
        f"- Export on-disk pin `{pin['on_disk_sha']}` blob-not-a-pin `{pin['blob_sha_not_a_pin']}`",
        f"- Listings census n={tz['n_listings']} Z={tz['n_z']} offset={tz['n_offset']} naive={tz['n_naive']}",
        f"- Years opened: {tz['years_opened']}",
        f"- n_incomplete={incomplete['n_incomplete']} by_season={incomplete['n_incomplete_by_season']}",
        f"- excluded_game_ids={incomplete['excluded_game_ids']}",
        "- NFL_TOTALS_*: unset. Tokens: none. Lock: not written.",
        "- 2024/25: not opened. Join: not run.",
        "",
    ]
    path = out_dir / "provenance.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    (out_dir / "d2_results.json").write_text(
        json.dumps(
            {
                "kind": kind,
                "decision_sha": REQUIRED_DECISION,
                "export_on_disk_sha": pin["on_disk_sha"],
                "export_blob_sha_not_a_pin": pin["blob_sha_not_a_pin"],
                "tz": tz,
                "incomplete": incomplete,
                "opening_permitted": False,
                "holdout_years_opened": False,
                "joined": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def capture_stop(fn) -> str:
    buf = io.StringIO()
    old = sys.stderr
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
    text = buf.getvalue()
    if "STOP:" not in text:
        die(f"expected STOP log, got {text!r}")
    return text


def require_stop(text: str, needle: str, fixture_id: str) -> str:
    if needle not in text:
        die(f"{fixture_id} missing {needle!r} in {text!r}")
    return text


def load_expected() -> Dict[str, Any]:
    path = pkg_path("t_expected", "D2_EXPECTED.json")
    if sha256_file(path) != REQUIRED_EXPECTED:
        die(f"expected answers sha {sha256_file(path)} != {REQUIRED_EXPECTED}")
    commit_path = pkg_path("inputs", "expected_answers_commit.txt")
    listed = commit_path.read_text(encoding="utf-8").strip()
    if listed != REQUIRED_EXPECTED_COMMIT:
        die(f"expected-answers commit {listed} != {REQUIRED_EXPECTED_COMMIT}")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_seeded() -> None:
    pairs = (
        ("seeded/DECISION_RYAN_t4335s14919_HOLDOUT_CLEAR_v3_1_v1.txt", REQUIRED_DECISION),
        ("seeded/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v6.txt", REQUIRED_READINESS_V6),
        ("seeded/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v6_ERRATUM_v1.txt", REQUIRED_ERRATUM_V6),
        ("seeded/nfl-injury-holdout-request-2024-2025-v3.1.md", REQUIRED_REQUEST_V31),
        ("seeded/IMV_SPEC_NFL_INJURY_ADJUSTMENT_TESTS_v1.txt", REQUIRED_SPEC),
        ("seeded/IMV_SPEC_NFL_INJURY_PRE_HOLDOUT_ACCEPTANCE_v1.txt", REQUIRED_ACCEPT),
        ("seeded/sealed_injury_export_ts_v1.json", REQUIRED_EXPORT),
    )
    for rel, exp in pairs:
        got = sha256_file(pkg_path(*rel.split("/")))
        if got != exp:
            die(f"seeded {rel} sha {got} != {exp}")
    blob_side = pkg_path("seeded", "sealed_injury_export_ts_v1.json.sha256").read_text(encoding="utf-8").split()[0]
    if blob_side != REQUIRED_EXPORT_BLOB_NOT_A_PIN:
        die("seeded blob sidecar drifted")


def run_pipeline(export_path: Path, listings_dir: Path, allowed_years: Iterable[int], out_dir: Path, kind: str) -> Dict[str, Any]:
    state: Dict[str, Any] = {}
    pin = pin_export_v2(export_path)
    tz = census_listings_tz(listings_dir, allowed_years)
    state["tz_census_done"] = True
    games = load_export_games(export_path)
    _kept, incomplete = apply_incomplete_row_rule(games, state)
    write_run_provenance(out_dir, pin=pin, tz=tz, incomplete=incomplete, kind=kind)
    return {"pin": pin, "tz": tz, "incomplete": incomplete, "state": state}


def fixture_dir(name: str) -> Path:
    return pkg_path("fixtures", name)


def run_fixtures(expected: Dict[str, Any], out_dir: Path) -> Dict[str, Any]:
    results: Dict[str, Any] = {}

    def f_naive() -> None:
        run_pipeline(fixture_dir("naive") / "export.json", fixture_dir("naive"), (2022,), out_dir / "naive", "F-NAIVE")

    results["F-NAIVE"] = require_stop(capture_stop(f_naive), expected["F-NAIVE"]["must_contain"], "F-NAIVE")

    def f_inc_ts() -> None:
        run_pipeline(fixture_dir("incomplete-ts") / "export.json", fixture_dir("incomplete-ts"), (2022,), out_dir / "inc-ts", "F-INC-TS")

    results["F-INC-TS"] = require_stop(capture_stop(f_inc_ts), expected["F-INC-TS"]["must_contain"], "F-INC-TS")

    def f_inc_delta() -> None:
        run_pipeline(fixture_dir("incomplete-delta") / "export.json", fixture_dir("incomplete-delta"), (2022,), out_dir / "inc-delta", "F-INC-DELTA")

    results["F-INC-DELTA"] = require_stop(capture_stop(f_inc_delta), expected["F-INC-DELTA"]["must_contain"], "F-INC-DELTA")

    def f_comp_null() -> None:
        run_pipeline(fixture_dir("complete-null") / "export.json", fixture_dir("complete-null"), (2022,), out_dir / "comp-null", "F-COMP-NULL")

    results["F-COMP-NULL"] = require_stop(capture_stop(f_comp_null), expected["F-COMP-NULL"]["must_contain"], "F-COMP-NULL")

    def f_v2_missing() -> None:
        run_pipeline(fixture_dir("v2-missing") / "export.json", fixture_dir("v2-missing"), (2022,), out_dir / "v2-missing", "F-V2-MISSING")

    results["F-V2-MISSING"] = require_stop(capture_stop(f_v2_missing), expected["F-V2-MISSING"]["must_contain"], "F-V2-MISSING")

    def f_v2_blob() -> None:
        run_pipeline(fixture_dir("v2-blob") / "export.json", fixture_dir("v2-blob"), (2022,), out_dir / "v2-blob", "F-V2-BLOB")

    results["F-V2-BLOB"] = require_stop(capture_stop(f_v2_blob), expected["F-V2-BLOB"]["must_contain"], "F-V2-BLOB")

    def f_v2_mismatch() -> None:
        run_pipeline(fixture_dir("v2-mismatch") / "export.json", fixture_dir("v2-mismatch"), (2022,), out_dir / "v2-mismatch", "F-V2-MISMATCH")

    results["F-V2-MISMATCH"] = require_stop(capture_stop(f_v2_mismatch), expected["F-V2-MISMATCH"]["must_contain"], "F-V2-MISMATCH")

    def f_join_first() -> None:
        state: Dict[str, Any] = {"tz_census_done": True}
        join_close_or_outcome(state, [{"season": 2022}])

    results["F-JOIN-FIRST"] = require_stop(capture_stop(f_join_first), expected["F-JOIN-FIRST"]["must_contain"], "F-JOIN-FIRST")

    def f_name() -> None:
        assert_path_not_holdout(Path("listings_2024.csv"))

    results["F-NAME"] = require_stop(capture_stop(f_name), expected["F-NAME"]["must_contain"], "F-NAME")

    def f_holdout() -> None:
        die("D-2 opening blocked: IMV has not passed this runner; lock not written; 2024/25 not opened")

    results["F-HOLDOUT"] = require_stop(capture_stop(f_holdout), expected["F-HOLDOUT"]["must_contain"], "F-HOLDOUT")

    ok = run_pipeline(fixture_dir("ok") / "export.json", fixture_dir("ok"), (2022,), out_dir / "ok", "F-OK")
    exp_ok = expected["F-OK"]
    inc = ok["incomplete"]
    tz = ok["tz"]
    if inc["n_incomplete"] != exp_ok["n_incomplete"]:
        die(f"F-OK n_incomplete {inc['n_incomplete']} != {exp_ok['n_incomplete']}")
    if inc["excluded_game_ids"] != exp_ok["excluded_game_ids"]:
        die(f"F-OK excluded {inc['excluded_game_ids']} != {exp_ok['excluded_game_ids']}")
    if inc["n_incomplete_by_season"] != exp_ok["n_incomplete_by_season"]:
        die(f"F-OK by_season {inc['n_incomplete_by_season']}")
    if tz["n_listings"] != exp_ok["n_listings"] or tz["n_z"] != exp_ok["n_z"] or tz["n_offset"] != exp_ok["n_offset"] or tz["n_naive"] != 0:
        die(f"F-OK tz drifted {tz}")
    results["F-OK"] = {"stop": False, **inc, **{k: tz[k] for k in ("n_listings", "n_z", "n_offset", "n_naive")}}

    log("fixtures: F-NAIVE F-INC-TS F-INC-DELTA F-COMP-NULL F-V2-MISSING F-V2-BLOB F-V2-MISMATCH F-JOIN-FIRST F-NAME F-HOLDOUT STOP; F-OK recorded")
    return results


def run_le2023(expected: Dict[str, Any], out_dir: Path) -> Dict[str, Any]:
    export = pkg_path("seeded", "sealed_injury_export_ts_v1.json")
    listings = pkg_path("seeded", "listings-le2023")
    result = run_pipeline(export, listings, ALLOWED_LE2023, out_dir, "le2023")
    exp = expected["le2023"]
    tz = result["tz"]
    inc = result["incomplete"]
    pin = result["pin"]
    if pin["on_disk_sha"] != REQUIRED_EXPORT:
        die(f"le2023 export pin {pin['on_disk_sha']} != {REQUIRED_EXPORT}")
    if tz["n_listings"] != exp["n_listings"] or tz["n_z"] != exp["n_z"] or tz["n_naive"] != 0:
        die(f"le2023 tz drifted {tz}")
    if tz["years_opened"] != exp["years_opened"]:
        die(f"le2023 years {tz['years_opened']}")
    if inc["n_incomplete"] != exp["n_incomplete"]:
        die(f"le2023 n_incomplete {inc['n_incomplete']}")
    if inc["n_incomplete_by_season"] != exp["n_incomplete_by_season"]:
        die(f"le2023 by_season {inc['n_incomplete_by_season']}")
    if inc["excluded_game_ids"] != exp["excluded_game_ids"]:
        die(f"le2023 excluded {inc['excluded_game_ids']}")
    log(
        "le2023: "
        f"listings={tz['n_listings']} Z={tz['n_z']} naive=0 "
        f"n_incomplete={inc['n_incomplete']} ids={inc['excluded_game_ids']}"
    )
    return result


def mode_holdout() -> None:
    die("D-2 opening blocked: IMV has not passed this runner; lock not written; 2024/25 not opened")


def write_report(out_dir: Path, fixtures: Dict[str, Any], le2023: Optional[Dict[str, Any]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# D-2 runner report",
        "",
        f"Ryan `{RYAN_MESSAGE}` / `{REQUIRED_DECISION[:8]}`: `{RYAN_VERBATIM}`.",
        "IMV review of this runner is still required. 2024/25 was not opened.",
        "",
        "## Fixtures",
        "",
    ]
    for key in (
        "F-NAIVE",
        "F-INC-TS",
        "F-INC-DELTA",
        "F-COMP-NULL",
        "F-V2-MISSING",
        "F-V2-BLOB",
        "F-V2-MISMATCH",
        "F-JOIN-FIRST",
        "F-NAME",
        "F-HOLDOUT",
        "F-OK",
    ):
        val = fixtures.get(key)
        if isinstance(val, str):
            first = next((ln for ln in val.splitlines() if ln.startswith("STOP:")), val.strip())
            lines.append(f"- `{key}` STOP: `{first}`")
        else:
            lines.append(f"- `{key}` recorded n_incomplete={val.get('n_incomplete')} ids={val.get('excluded_game_ids')}")
    if le2023:
        tz = le2023["tz"]
        inc = le2023["incomplete"]
        lines.extend(
            [
                "",
                "## le2023",
                "",
                f"- listings {tz['n_listings']}: Z={tz['n_z']} offset={tz['n_offset']} naive={tz['n_naive']}",
                f"- years {tz['years_opened']}",
                f"- n_incomplete={inc['n_incomplete']} by_season={inc['n_incomplete_by_season']}",
                f"- excluded_game_ids={inc['excluded_game_ids']}",
                f"- export on-disk pin `{le2023['pin']['on_disk_sha']}`",
            ]
        )
    lines.extend(["", "NO-GO. Coming Soon ON. No merge. No lock. No opening.", ""])
    (out_dir / "d2-report.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="D-2 holdout runner (no 2024/25 open)")
    parser.add_argument("--mode", choices=("fixtures", "le2023", "all", "holdout"), required=True)
    args = parser.parse_args(argv)
    assert_env_clean()
    assert_no_tokens()
    if args.mode == "holdout":
        mode_holdout()
    resolve_seeded()
    expected = load_expected()
    out = pkg_path("out")
    fixtures = {}
    le2023 = None
    if args.mode in {"fixtures", "all"}:
        fixtures = run_fixtures(expected, out / "fixtures")
    if args.mode in {"le2023", "all"}:
        le2023 = run_le2023(expected, out / "le2023")
    write_report(out, fixtures, le2023)
    log("D-2 runner ok:true (no 2024/25 open)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
