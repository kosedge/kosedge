"""t5335u R7 followthrough metadata preflight. CERT=0.

Manifest + identity/readiness only. Does not implement NTBB-K.
Does not open score-bearing labels or run real science.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from src.services.nfl_ops_v1_evidence.spy import ForbiddenSurfaceSpy, OutcomeReadSpy
from src.services.nfl_ops_v1_evidence.verify import git_tip
from src.services.nfl_r7_correctness_v1.pins import (
    CALENDAR_ID,
    CALENDAR_TZ,
    CERT,
    CODE_FILES,
    FW_SHA256,
    IF_TIP,
    KO_MINUS_MINUTES,
    SIM_SHA256,
    WORKER_A_ID,
)
from src.services.nfl_r7_correctness_v1.produce import r7_code_hash, r7_config_hash, repo_root, write_json
from src.services.nfl_t5208u.pins import CANDIDATE_WEIGHT, MARKET_BLEND, SEED_BASE, SEED_MOD, SIMULATIONS


class FollowthroughRefuse(ValueError):
    """Fail-closed followthrough preflight."""


SCHEMA_ID = "nfl-t5335u-r7-followthrough-preflight-v1"
PACKAGE = "R7_FOLLOWTHROUGH_PREFLIGHT"
OWNER_CLEAR = "92861"
AUTHORITY = "t5335u"
SCOPE_ID = "chief-nflgreen-followthrough-20261103"
SPEC_REL = "research/nfl_followthrough_20261103/NTBB_K_V1_SPEC.md"
FOLLOWTHROUGH_FILES = (
    "services/model-service/src/services/nfl_r7_correctness_v1/followthrough_preflight.py",
    "scripts/nfl/run_nfl_r7_followthrough_preflight.py",
)
SPEC_SHA256 = "2f3c215d7680dd5aa33a0a77690ece4ef70a0a8dbbebaac880750dd776ec66d7"
START_TIP = "d3f2c56adcbb684db20af9c29a55e656371e605e"
SPEC_COMMIT = "2a2c91c9b839da2246a01596b203318295581914"
ARCHIVED_IDENTITY_COMMIT = "255adf7802830bc25814a739d62f65f095216203"
ARCHIVED_IDENTITY_REL = "data/ops/nfl-t5155u-r5-496-freeze/IDENTITY_MANIFEST.json"
OLD_IF_FREEZE_REL = "data/ops/nfl-forecast-builder-t5107u/FORECAST_FREEZE_t5112u.json"
OPS_REL = "data/ops/t5335u-r7-followthrough"

EXACT_496 = 496
N_2020 = 240
N_2021 = 256
N_OLD_437 = 437
N_NEW_59 = 59
N_SAME_96 = 96
BOOTSTRAP_B = 10000
BOOTSTRAP_SEED = 20261103
SENSITIVITY_SEED = 20261104
BOOTSTRAP_GEN = "PCG64"

# Working-tree locators required for per-target timing/rest. Absent here.
CLOUD_LOCATORS = (
    {
        "locator": "data/ops/nfl-t5146u-r4-last-played-dev/DEV_RECON_LAST_PLAYED_2020_2021_REG.json",
        "role": "FEATURE_RECON_REG496 artifact",
        "sha256_pin": "282f979b52890c7ed943eeb9c0836dd7f50b9a925cf3e82fdfc856834646402c",
        "opened": False,
    },
    {
        "locator": "data/ops/nfl-t5146u-r4-last-played-dev/DEV_RECON_LAST_PLAYED_2020_2021_REG_MATRIX.csv",
        "role": "feature matrix",
        "sha256_pin": "a3b9d8ecb94902078ddcb89206a5a1ff16d5f1a3b4e8080186238d6578c52409",
        "opened": False,
    },
    {
        "locator": "data/ops/nfl-forecast-builder-t5107u/inputs/schedule_results_2020_2023.csv",
        "role": "schedule / actual-versus-scheduled (UNOPENED — may carry results)",
        "sha256_pin": "0853342304d269b55033d3474acda853ce00bdb10590f44b09ae569115148479",
        "opened": False,
    },
    {
        "locator": "data/ops/nfl-forecast-builder-t5107u/FORECAST_FREEZE_t5112u.json",
        "role": "old IF freeze working-tree copy",
        "sha256_pin": "9e704b980b6ce33acc883725823c39766ea19f8a86a7a781ac2a02d95344a732",
        "opened": False,
    },
    {
        "locator": "same96 market offered-line/price/timing/rule evidence",
        "role": "exact96 market comparison (Worker B owned historically)",
        "sha256_pin": None,
        "opened": False,
    },
)

UNOPENED_LABEL_POINTERS = (
    {
        "locator": "outcomes @ SOURCE_PINS.outcomes",
        "sha256_pin": "50bda875daa8bf1aadd56dd0a3bc19f1bb52dafe42b6a9c921a5816c7d7dc081",
        "status": "UNOPENED",
        "reason": "label-read not authorized this turn",
    },
    {
        "locator": "games @ SOURCE_PINS.games",
        "sha256_pin": "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8",
        "status": "UNOPENED",
        "reason": "history payload not authorized this turn",
    },
)

FORBIDDEN_SCORE_KEYS = (
    "actual_margin",
    "actual_total",
    "home_score",
    "away_score",
    "error",
    "abs_error",
    "signed_error",
    "ats",
    "cover",
    "look",
    "eval_score",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _scan_forbidden(payload: Any, *, where: str) -> None:
    """Refuse score-bearing mapping keys. String deny-lists are allowed."""
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if str(key).casefold() in FORBIDDEN_SCORE_KEYS:
                raise FollowthroughRefuse(f"{where} contains forbidden score-bearing key {key}")
            _scan_forbidden(value, where=where)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            _scan_forbidden(item, where=where)


def require_spec(root: Path) -> dict[str, str]:
    path = root / SPEC_REL
    if not path.is_file():
        raise FollowthroughRefuse(f"NTBB-K spec missing {SPEC_REL}")
    digest = sha256_file(path)
    if digest != SPEC_SHA256:
        raise FollowthroughRefuse(f"NTBB-K spec sha256 {digest} != {SPEC_SHA256}")
    return {"path": SPEC_REL, "sha256": digest, "opened": "read_bind_only", "kernel_implemented": False}


def bind_working_tree_sources(root: Path) -> dict[str, Any]:
    rows = []
    for rel in (SPEC_REL, *CODE_FILES, *FOLLOWTHROUGH_FILES):
        path = root / rel
        if not path.is_file():
            raise FollowthroughRefuse(f"source bind missing {rel}")
        rows.append({"path": rel, "sha256": sha256_file(path), "present": True})
    return {"n": len(rows), "files": rows}


def _git_show(root: Path, commit: str, rel: str) -> bytes:
    proc = subprocess.run(
        ["git", "show", f"{commit}:{rel}"],
        cwd=str(root),
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise FollowthroughRefuse(f"archived pointer {commit}:{rel} unreadable: {proc.stderr.decode()[:200]}")
    return proc.stdout


def bind_archived_identity(root: Path) -> dict[str, Any]:
    """Identity-only bind from archived git object. Does not open labels."""
    raw = _git_show(root, ARCHIVED_IDENTITY_COMMIT, ARCHIVED_IDENTITY_REL)
    digest = sha256_bytes(raw)
    body = json.loads(raw.decode("utf-8"))
    _scan_forbidden(body, where="archived identity")
    game_ids = [str(x) for x in body.get("game_ids") or []]
    n_by = body.get("n_by_season") or {}
    if len(game_ids) != EXACT_496:
        raise FollowthroughRefuse(f"archived identity n={len(game_ids)} != {EXACT_496}")
    if int(n_by.get("2020", -1)) != N_2020 or int(n_by.get("2021", -1)) != N_2021:
        raise FollowthroughRefuse(f"archived n_by_season {n_by} != {N_2020}+{N_2021}")
    if N_2020 + N_2021 != EXACT_496:
        raise FollowthroughRefuse("240+256 != 496")
    return {
        "opened": "identity_manifest_git_object_only",
        "commit": ARCHIVED_IDENTITY_COMMIT,
        "path": ARCHIVED_IDENTITY_REL,
        "bytes": len(raw),
        "sha256": digest,
        "n": EXACT_496,
        "n_by_season": {"2020": N_2020, "2021": N_2021},
        "identity_sha256_pin": body.get("identity_sha256"),
        "membership_rule": body.get("membership_rule"),
        "week_le_18_proxy": body.get("week_le_18_proxy"),
        "reg_week18_2021_retained": list(body.get("reg_week18_2021_retained") or []),
        "wildcard_2020_refused": list(body.get("wildcard_2020_refused") or []),
        "game_ids": game_ids,
        "working_tree_present": (root / ARCHIVED_IDENTITY_REL).is_file(),
    }


def bind_old437_new59(root: Path, game_ids: list[str]) -> dict[str, Any]:
    raw = _git_show(root, ARCHIVED_IDENTITY_COMMIT, OLD_IF_FREEZE_REL)
    digest = sha256_bytes(raw)
    old = json.loads(raw.decode("utf-8"))
    old_ids = [str(x) for x in old.get("game_ids") or []]
    # Do not persist forecasts. IDs only.
    new_set = set(game_ids)
    old_set = set(old_ids)
    common = sorted(new_set & old_set)
    only_new = sorted(new_set - old_set)
    if len(common) != N_OLD_437 or len(only_new) != N_NEW_59:
        raise FollowthroughRefuse(
            f"old437+new59 mismatch common={len(common)} new={len(only_new)}"
        )
    if len(common) + len(only_new) != EXACT_496:
        raise FollowthroughRefuse("437+59 != 496")
    return {
        "opened": "old_freeze_game_ids_only",
        "commit": ARCHIVED_IDENTITY_COMMIT,
        "path": OLD_IF_FREEZE_REL,
        "sha256": digest,
        "old_freeze_n_game_ids": len(old_set),
        "n_common_437": len(common),
        "n_new_59": len(only_new),
        "new_59_ids": only_new,
        "forecasts_copied": False,
        "working_tree_present": (root / OLD_IF_FREEZE_REL).is_file(),
    }


def project_targets(game_ids: list[str]) -> list[dict[str, Any]]:
    """Identity + readiness slots only. Unknown timing stays unknown."""
    rows: list[dict[str, Any]] = []
    for gid in game_ids:
        parts = str(gid).split("_")
        if len(parts) != 4:
            raise FollowthroughRefuse(f"identity parse refused: {gid}")
        season, week_s, away, home = parts
        week = int(week_s)
        rows.append(
            {
                "game_id": gid,
                "season": int(season),
                "week": week,
                "season_type": "REG",
                "away_team": away,
                "home_team": home,
                "identity_ready": True,
                "actual_kickoff_utc": None,
                "scheduled_kickoff_utc": None,
                "actual_versus_scheduled": "UNKNOWN",
                "played": "UNKNOWN",
                "predecessor_ready": False,
                "rest_ready": False,
                "previous_week_history_pointer_eligible": week >= 2,
                "previous_week_history_pointer": "UNOPENED",
                "availability": "UNKNOWN",
                "score_bearing_payload": False,
            }
        )
    return rows


def missing_locators(root: Path) -> list[dict[str, Any]]:
    missing = []
    for row in CLOUD_LOCATORS:
        locator = str(row["locator"])
        present = (root / locator).is_file() if not locator.startswith("same96") else False
        if not present:
            missing.append(
                {
                    "locator": locator,
                    "role": row["role"],
                    "sha256_pin": row["sha256_pin"],
                    "working_tree": "ABSENT",
                    "count_blocked": (
                        N_SAME_96 if locator.startswith("same96") else EXACT_496
                    ),
                }
            )
    return missing


def runtime_versions() -> dict[str, Any]:
    numpy_ver = None
    scipy_ver = None
    try:
        import numpy

        numpy_ver = numpy.__version__
    except Exception:
        numpy_ver = None
    try:
        import scipy

        scipy_ver = scipy.__version__
    except Exception:
        scipy_ver = "ABSENT"
    return {
        "python": sys.version.split()[0],
        "python_full": sys.version,
        "platform": platform.platform(),
        "numpy": numpy_ver,
        "scipy": scipy_ver,
        "tz": CALENDAR_TZ,
        "calendar_id": CALENDAR_ID,
        "ko_minus_minutes": KO_MINUS_MINUTES,
        "simulations": SIMULATIONS,
        "seed_base": SEED_BASE,
        "seed_mod": SEED_MOD,
        "market_blend": MARKET_BLEND,
        "candidate_weight": CANDIDATE_WEIGHT,
        "if_tip": IF_TIP,
        "sim_sha256": SIM_SHA256,
        "fw_sha256": FW_SHA256,
        "apply_linear_totals_calibration": False,
        "bootstrap_B": BOOTSTRAP_B,
        "bootstrap_gen": BOOTSTRAP_GEN,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "sensitivity_seed": SENSITIVITY_SEED,
        "scipy_required_for_kernel": True,
        "kernel_authorized": False,
    }


def build_candidate(*, root: Path | None = None) -> dict[str, Any]:
    repo = repo_root() if root is None else Path(root)
    runtime_source_revision = git_tip(repo)
    spec = require_spec(repo)
    sources = bind_working_tree_sources(repo)
    identity = bind_archived_identity(repo)
    split = bind_old437_new59(repo, identity["game_ids"])
    targets = project_targets(identity["game_ids"])
    missing = missing_locators(repo)
    ready = len(missing) == 0
    candidate = {
        "schema_id": SCHEMA_ID,
        "package": PACKAGE,
        "owner_clear": OWNER_CLEAR,
        "authority": AUTHORITY,
        "scope_id": SCOPE_ID,
        "cert": CERT,
        "channel": "METADATA_PREFLIGHT",
        "opt_in": True,
        "implemented_ne_verified": True,
        "kernel_implemented": False,
        "ready_for_real_exec": False,
        "science_hold": True,
        "runtime_source_revision": runtime_source_revision,
        "packaging_revision": None,
        "packaging_revision_claimed_as_executed": False,
        "start_tip": START_TIP,
        "spec_commit": SPEC_COMMIT,
        "spec": spec,
        "counts": {
            "exact496": EXACT_496,
            "n_2020": N_2020,
            "n_2021": N_2021,
            "sum_240_256": N_2020 + N_2021,
            "old437": N_OLD_437,
            "new59": N_NEW_59,
            "sum_437_59": N_OLD_437 + N_NEW_59,
            "same96": N_SAME_96,
            "same96_ids_present": False,
        },
        "consumed_sources": sources,
        "r7_config_hash": r7_config_hash(),
        "r7_code_hash": r7_code_hash(repo),
        "runtime": runtime_versions(),
        "archived_control": {
            "identity": {
                k: identity[k]
                for k in identity
                if k != "game_ids"
            },
            "old437_new59": {k: split[k] for k in split if k != "new_59_ids"},
            "unopened_label_history_pointers": list(UNOPENED_LABEL_POINTERS),
        },
        "game_ids": identity["game_ids"],
        "new_59_ids": split["new_59_ids"],
        "targets": targets,
        "missing": missing,
        "missing_n": len(missing),
        "projection_request": {
            "needed": True,
            "reason": "working-tree cloud files absent; per-target actual kickoff/played/rest stay UNKNOWN",
            "locators": [row["locator"] for row in missing],
            "do_not_include": [
                "home_score",
                "away_score",
                "actual_margin",
                "labels",
                "outcomes",
            ],
            "permitted_fields": [
                "game_id",
                "season",
                "week",
                "season_type",
                "home_team",
                "away_team",
                "actual_kickoff_utc",
                "scheduled_kickoff_utc",
                "status",
                "kickoff_kind",
                "predecessor_game_id",
                "rest_days_home",
                "rest_days_away",
                "available_at",
                "observed_at",
            ],
        },
        "readiness": "NOT_READY" if not ready else "READY",
        "score_bearing_payload_returned": False,
        "causal_to_retrospective_bypass": False,
        "worker_id": WORKER_A_ID,
        "produced_utc": _utc_now(),
    }
    _scan_forbidden(candidate, where="candidate")
    return candidate


def run_fictional_chain(*, root: Path, dest: Path) -> dict[str, Any]:
    """One actual fictional producer→gate→consumer→atomic readback."""
    from src.services.nfl_r7_correctness_v1.run import run_r7_integrated
    from src.services.nfl_ops_v1_evidence.validate_r7 import dest_is_actually_temp, readback_and_rehash
    from src.services.nfl_t5208u.hashing import sha256_file as sha_file
    from src.services.nfl_t5208u.caller import model_spy_counts, reset_model_spy

    outcome_spy = OutcomeReadSpy()
    surface = ForbiddenSurfaceSpy()
    reset_model_spy()
    receipt = run_r7_integrated(root=root, dest=dest)
    result_path = Path(dest) / "demo_result.json"
    if not result_path.is_file():
        raise FollowthroughRefuse("fictional chain did not write demo_result.json")
    expected = sha_file(result_path)
    readback_and_rehash(result_path, expected)
    if outcome_spy.reads not in (None, 0):
        raise FollowthroughRefuse("fictional chain read outcomes")
    return {
        "ok": bool(receipt.get("ok")),
        "exit": receipt.get("exit"),
        "exit_source": receipt.get("exit_source"),
        "game_id": receipt["produce"]["game_id"],
        "if_margin": receipt["produce"]["if_margin"],
        "q2_margin": receipt["produce"]["q2_margin"],
        "c_margin": receipt["produce"]["c_margin"],
        "pair_hash": receipt["pair"]["pair_hash"],
        "r7_config_hash": receipt["produce"]["r7_config_hash"],
        "r7_code_hash": receipt["produce"]["r7_code_hash"],
        "apply_linear_totals_calibration": receipt["produce"].get("apply_linear_totals_calibration"),
        "demo_result_sha256": expected,
        "final_dest_is_temp": dest_is_actually_temp(dest),
        "model_spy": model_spy_counts(),
        "outcome_reads": outcome_spy.reads,
        "surface_notes": surface.count,
        "command": "PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_r7_followthrough_preflight.py",
    }


def run_direct_boundary_controls() -> dict[str, Any]:
    from src.services.nfl_ops_v1_evidence.spy import run_spy_positive_control

    spy = run_spy_positive_control()
    negatives: list[dict[str, Any]] = []
    try:
        _scan_forbidden({"home_score": 21}, where="negative")
        negatives.append({"name": "score_key", "refused": False})
    except FollowthroughRefuse:
        negatives.append({"name": "score_key", "refused": True})
    try:
        require_spec(Path("/nonexistent/repo-root"))
        negatives.append({"name": "missing_spec", "refused": False})
    except FollowthroughRefuse:
        negatives.append({"name": "missing_spec", "refused": True})
    if not all(item["refused"] for item in negatives):
        raise FollowthroughRefuse(f"direct-boundary negatives failed: {negatives}")
    return {"spy_positive_control": dict(spy), "negatives": negatives}


def run_followthrough_preflight(*, root: Path | None = None) -> dict[str, Any]:
    repo = repo_root() if root is None else Path(root)
    dest = repo / OPS_REL
    dest.mkdir(parents=True, exist_ok=True)
    candidate = build_candidate(root=repo)
    fictional_dest = dest / "fictional_r7_chain"
    fictional = run_fictional_chain(root=repo, dest=fictional_dest)
    boundaries = run_direct_boundary_controls()
    receipt = {
        "ok": True,
        "cert": CERT,
        "status": "PREFLIGHT_NOT_READY_AWAITING_CLOUD_FILES",
        "ready_for_review": False,
        "accepted": False,
        "package": PACKAGE,
        "owner_clear": OWNER_CLEAR,
        "runtime_source_revision": candidate["runtime_source_revision"],
        "packaging_revision": None,
        "counts": candidate["counts"],
        "readiness": candidate["readiness"],
        "missing_n": candidate["missing_n"],
        "spec_sha256": candidate["spec"]["sha256"],
        "r7_config_hash": candidate["r7_config_hash"],
        "r7_code_hash": candidate["r7_code_hash"],
        "fictional_chain": fictional,
        "boundaries": boundaries,
        "kernel_implemented": False,
    }
    _scan_forbidden(receipt, where="receipt")
    write_json(dest / "CANDIDATE.json", candidate)
    write_json(dest / "MISSING.json", {"n": candidate["missing_n"], "missing": candidate["missing"]})
    write_json(dest / "receipt.json", receipt)
    projection = {
        "schema_id": SCHEMA_ID,
        "request": candidate["projection_request"],
        "counts": candidate["counts"],
    }
    write_json(dest / "PROJECTION_REQUEST.json", projection)
    return receipt


def main() -> int:
    receipt = run_followthrough_preflight()
    print(
        json.dumps(
            {
                "ok": receipt["ok"],
                "status": receipt["status"],
                "runtime_source_revision": receipt["runtime_source_revision"],
                "readiness": receipt["readiness"],
                "missing_n": receipt["missing_n"],
                "exact496": receipt["counts"]["exact496"],
                "fictional_exit": receipt["fictional_chain"]["exit"],
            },
            sort_keys=True,
        )
    )
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
