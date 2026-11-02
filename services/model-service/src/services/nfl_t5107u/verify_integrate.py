"""t5153u scoped research caller + one-command integration owner.

Wires Package A cohort gates (before feature-output finalization and
before target-outcome loading) and Package B numerical checks (before
receipt publication). Normal command consumes immutable published
DEV437 / matched72 results — no synthetic n=2 path.

Synthetic fixtures exist only as explicit test helpers. Never runs real EVAL.
Nonzero failure prevents VERIFIED/final output. CERT=0. DRAFT≠merge.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .eval_result_contract import (
    ALEX_PASS_RO,
    ALEX_RETURN_ACCEPTED_SHA8,
    ALEX_RETURN_SHA8,
    CERT_CANDIDATE,
    COS_ACCEPT_SCOPED_SHA8,
    COS_ORDER_B_SHA8,
    COS_ORDER_RETURN_SHA8,
    DEV437_RESULT_PATH,
    DEV437_RESULT_SHA256,
    DEV_IF437_BY_SEASON,
    DEV_MARKET72_BY_SEASON,
    INTERVAL_CONTRACT,
    MARKET72_RESULT_PATH,
    MARKET72_RESULT_SHA256,
    MARKET72_SOURCE_TIP,
    OWNER_AMEND_SHA8,
    OWNER_CLEAR_SHA8,
    PACKAGE_A_STAMP,
    PACKAGE_A_TIP,
    PARTIAL_PLUMBING_STAMP,
    PARTIAL_PLUMBING_TIP,
    PROFILE_DEV_IF437,
    PROFILE_DEV_MARKET72,
    PROFILE_FEATURE_RECON_REG496,
    PROFILES,
    R4_496_ACCEPTED_TIP,
    EvalResultContractRefuse,
    refuse_synthetic_flag,
    join_market72_from_if437,
    joined_row_sha256,
    validate_profile_output,
)
from .last_played_cohort import ORIGINAL_502_PATH, ORIGINAL_502_SHA256
from .recon_driver import sha256_file

TICKET = "t5155u"
PACKAGE = "C_VERIFY_INTEGRATE_R5_PHASE1"
SCHEMA = "nfl-t5155u-verify-integrate-receipt-v1"
OUT_DIR = Path("data/ops/nfl-t5151u-verify-integrate")
R5_OUT_DIR = Path("data/ops/nfl-t5155u-r5-phase1")
RECEIPT_NAME = "RECEIPT.json"
OWNER_CLEAR_T5155U_SHA8 = "659cd7d9"
COS_ORDER_T5155U_SHA8 = "3e14602b"
COS_ACCEPT_700_SHA8 = "4b23584a"
ALEX_700_SHA8 = "f4147e76"
TIP_700 = "12ccc482db54dd53bc6d79cea5f4af01c5540950"
B1_UNIVERSE_PATH = (
    "data/ops/nfl-t5119u-r2-owned-coverage/t5136u_B1/ADMISSIBLE_QUOTES_B1.jsonl"
)
B1_UNIVERSE_SHA256 = (
    "b4a3a4dbb8c5404d095b8095ec4018b96ceae532a50600d6d7f29f9d8fe950e6"
)
PYTEST_ELAPSED_RE = re.compile(r"\s+in\s+\d+(?:\.\d+)?s\b")
PYTEST_ELAPSED_CAPTURE_RE = re.compile(r"in\s+(\d+(?:\.\d+)?)s\b")
REG496_PATH = "data/ops/nfl-t5146u-r4-last-played-dev/DEV_RECON_LAST_PLAYED_2020_2021_REG.json"
REG496_SHA256 = "282f979b52890c7ed943eeb9c0836dd7f50b9a925cf3e82fdfc856834646402c"
FEATURE_RECON_REG496_ARTIFACT_PATH = REG496_PATH
FEATURE_RECON_REG496_ARTIFACT_SHA256 = REG496_SHA256
REG496_IDENTITY_SHA256 = (
    "6429f8596a1b605a9f1dc8aec21d81fc4454ff25e985dc77e691ec29d489c640"
)
WORKER_A_TIP = "661df712a804bc1d9662f77008af28f8418cd0a1"
WORKER_A_STAMP = "3fbf5999360433ca46cbe77688daedaedd6a9c9b"
WORKER_A_PR = 702
WORKER_A_BRANCH = "cursor/t5155u-r5-496-freeze-c279"
WORKER_A_COMMAND = (
    "PYTHONPATH=services/model-service python scripts/nfl/run_nfl_r5_496_freeze_t5155u.py"
)
A_FORECASTS_PATH = "data/ops/nfl-t5155u-r5-496-freeze/FORECASTS_DEV_R5_496.json"
A_FORECASTS_SHA256 = (
    "96d3aa6f85e7896df2385df8d025ea0bd4d15d5e2a82edc3f5c9184cd35af407"
)
A_MANIFEST_PATH = "data/ops/nfl-t5155u-r5-496-freeze/FREEZE_MANIFEST.json"
A_MANIFEST_SHA256 = (
    "36f051c4f0ecb96abac973f3e43bfc157a1f632e65d5d8b1de7991495eff7f38"
)
A_Q2_SHA256 = (
    "07bbc340223976ff4d832bb02bce9cae40b2febe3b226f619913241300ec6966"
)
A_COMPARE_PATH = "data/ops/nfl-t5155u-r5-496-freeze/COMPARE_437.json"
A_COMPARE_SHA256 = (
    "a0a54294eb7f05df3d3543b373394a99d438d7faa6b95ef945b59d66f2af5384"
)
A_PHASE2_PATH = "data/ops/nfl-t5155u-r5-496-freeze/PHASE2_POSITIVE_PATH.json"
A_PHASE2_SHA256 = (
    "bca0143f9ae1270193bc5d2a66499f896743eac9e857f40448d21a42b73e0086"
)
A_Q2_PATH = "data/ops/nfl-t5155u-r5-496-freeze/Q2_HISTORY_FREEZE.json"
TASK_MANIFEST_REL = "data/ops/nfl-t5151u-cohort-enforcement/TASK_MANIFEST.json"

PROTECTED_ORIGINALS = frozenset(
    {
        REG496_PATH,
        ORIGINAL_502_PATH,
        DEV437_RESULT_PATH,
        MARKET72_RESULT_PATH,
        TASK_MANIFEST_REL,
        "data/ops/nfl-t5151u-cohort-enforcement/ACCEPTED_DEV_MARKET72_IDS.json",
        B1_UNIVERSE_PATH,
        A_FORECASTS_PATH,
        A_MANIFEST_PATH,
        A_COMPARE_PATH,
        A_PHASE2_PATH,
        A_Q2_PATH,
    }
)

FOCUSED_TESTS = (
    "services/model-service/tests/test_nfl_t5151u_numerical_output_contract.py",
    "services/model-service/tests/test_nfl_t5151u_verify_integrate.py",
    "services/model-service/tests/test_nfl_t5149u_last_played_reg_cohort.py",
    "services/model-service/tests/test_nfl_t5155u_n1_output_hash.py",
    "services/model-service/tests/test_nfl_t5155u_market_arm_freeze.py",
    "services/model-service/tests/test_nfl_t5155u_r5_496_freeze.py",
    "services/model-service/tests/test_nfl_t5155u_r5_combine.py",
    "services/model-service/tests/test_nfl_t5155u_r5_phase2_one_exec.py",
)
COHORT_TEST = "services/model-service/tests/test_nfl_t5151u_cohort_enforcement.py"

LIMITATIONS = {
    "publication_timestamp_status": "unverified",
    "observation_timestamp_status": "unverified",
    "fit_label": "RETRO_FIT",
    "label": "RECONSTRUCTED",
    "production_causal_claim": False,
    "nfl_green": False,
    "eval": None,
    "real_eval_executed": False,
    "cert_candidate": CERT_CANDIDATE,
    "self_accept": False,
    "partial_plumbing_only": {
        "tip": PARTIAL_PLUMBING_TIP,
        "stamp": PARTIAL_PLUMBING_STAMP,
        "not_integrated_verified": True,
    },
}


class VerifyIntegrateRefuse(ValueError):
    """Fail-closed verification/integration. Not ACCEPT. Not EVAL."""


class OutcomeReadSpy:
    """Counts target-outcome reads. Gates must leave this at zero on refuse."""

    def __init__(
        self, fn: Callable[[], Mapping[str, Mapping[str, Any]]] | None = None
    ) -> None:
        self.reads = 0
        self.ids_returned: list[str] = []
        self._fn = fn

    def __call__(self) -> Mapping[str, Mapping[str, Any]]:
        self.reads += 1
        loaded = self._fn() if self._fn is not None else {}
        self.ids_returned = list(loaded)
        return loaded


@dataclass(frozen=True)
class CohortHooks:
    before_feature_output: Callable[..., Mapping[str, Any]]
    before_target_outcome: Callable[..., Mapping[str, Any]]
    source: str


def _repo_root(root: Path | None) -> Path:
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[5]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def strip_pytest_elapsed(text: str) -> str:
    """Drop pytest ``passed in Xs`` duration tokens from semantic text."""
    return PYTEST_ELAPSED_RE.sub("", text or "")


def extract_pytest_elapsed(text: str) -> list[str]:
    return PYTEST_ELAPSED_CAPTURE_RE.findall(text or "")


def semantic_tests_payload(tests: Mapping[str, Any] | None) -> dict[str, Any]:
    """Copy test results without elapsed-timing strings (N1)."""
    body = json.loads(json.dumps(tests or {}, default=str))
    for command in body.get("commands") or []:
        if not isinstance(command, Mapping):
            continue
        if "stdout_tail" in command:
            command["stdout_tail"] = strip_pytest_elapsed(command.get("stdout_tail") or "")
        if "stderr_tail" in command:
            command["stderr_tail"] = strip_pytest_elapsed(command.get("stderr_tail") or "")
        command.pop("elapsed", None)
    body.pop("elapsed", None)
    body.pop("durations", None)
    body.pop("elapsed_side_metadata", None)
    body.pop("_elapsed_for_runtime", None)
    body["timing_excluded_from_output_hash"] = True
    return body


def collect_pytest_elapsed(tests: Mapping[str, Any] | None) -> list[str]:
    elapsed: list[str] = []
    for command in (tests or {}).get("commands") or []:
        if not isinstance(command, Mapping):
            continue
        extra = command.get("elapsed")
        if isinstance(extra, list):
            elapsed.extend(str(item) for item in extra)
        elapsed.extend(extract_pytest_elapsed(command.get("stdout_tail") or ""))
        elapsed.extend(extract_pytest_elapsed(command.get("stderr_tail") or ""))
    elapsed.extend(str(item) for item in (tests or {}).get("elapsed_side_metadata") or [] if not isinstance(item, list))
    for group in (tests or {}).get("elapsed_side_metadata") or []:
        if isinstance(group, list):
            elapsed.extend(str(item) for item in group)
    return elapsed


def repo_relative_posix(root: Path, path: Path) -> str:
    resolved_root = Path(root).resolve()
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(resolved_root).as_posix()
    except ValueError as exc:
        raise VerifyIntegrateRefuse(f"path escapes repo root: {path}") from exc


def hash_file_list(root: Path, paths: Sequence[Path]) -> dict[str, Any]:
    """Repo-relative POSIX paths + per-file sha256. Reproducible across roots."""
    files: list[dict[str, str]] = []
    for path in paths:
        if not Path(path).is_file():
            continue
        files.append(
            {"path": repo_relative_posix(root, path), "sha256": sha256_file(path)}
        )
    files.sort(key=lambda row: row["path"])
    digest = sha256_text(json.dumps(files, separators=(",", ":"), sort_keys=True))
    return {"sha256": digest, "files": files}


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def try_load_cohort_module() -> Any | None:
    try:
        from src.services.nfl_t5107u import cohort_enforcement as ce

        return ce
    except ImportError:
        return None


def require_cohort_hooks(module: Any | None = None) -> CohortHooks:
    ce = module if module is not None else try_load_cohort_module()
    if ce is None:
        raise VerifyIntegrateRefuse(
            "Package A cohort_enforcement not landed — cannot integrate"
        )
    return CohortHooks(
        before_feature_output=ce.check_cohort_before_feature_output_finalization,
        before_target_outcome=ce.check_cohort_before_target_outcome_loading,
        source="src.services.nfl_t5107u.cohort_enforcement",
    )


def build_synthetic_if437_result(game_ids: Sequence[str] | None = None) -> dict[str, Any]:
    """TEST HELPER only. Normal command must not call this."""
    ids = list(game_ids) if game_ids else ["2020_02_CIN_CLE", "2021_02_CLE_CIN"]
    rows = []
    for idx, gid in enumerate(ids):
        season = int(str(gid).split("_", 1)[0])
        week = int(str(gid).split("_")[1])
        actual = 3.0 if idx % 2 == 0 else -2.0
        m_c = actual + (1.0 if idx % 2 == 0 else -1.0)
        m_if = actual + (2.0 if idx % 2 == 0 else 1.5)
        rows.append(
            {
                "game_id": gid,
                "season": season,
                "week": week,
                "season_week": f"{season}-{week:02d}",
                "actual_margin": actual,
                "m_challenger": m_c,
                "m_if": m_if,
                "err_challenger": m_c - actual,
                "err_if": m_if - actual,
                "L_challenger": abs(m_c - actual),
                "L_if": abs(m_if - actual),
                "signed_diff_vs_if": abs(m_c - actual) - abs(m_if - actual),
            }
        )
    return {
        "profile": PROFILE_DEV_IF437,
        "n": len(rows),
        "n_by_season": dict(sorted({str(r["season"]): 1 for r in rows}.items())),
        "game_ids": [r["game_id"] for r in rows],
        "games": rows,
        "market_unavailable": True,
        "market_status": "UNAVAILABLE",
        "cannot_satisfy_profiles": [PROFILE_DEV_MARKET72],
        "synthetic": True,
        "cert_candidate": CERT_CANDIDATE,
    }


def build_synthetic_market72_result(game_ids: Sequence[str] | None = None) -> dict[str, Any]:
    """TEST HELPER only. Normal command must not call this."""
    ids = list(game_ids) if game_ids else ["2020_02_CIN_CLE", "2021_03_CLE_CIN"]
    rows = []
    for idx, gid in enumerate(ids):
        season = int(str(gid).split("_", 1)[0])
        week = int(str(gid).split("_")[1])
        actual = 4.0 if idx % 2 == 0 else -1.0
        m_c = actual + 0.5
        m_if = actual + 1.5
        m_m = actual + 2.0
        rows.append(
            {
                "game_id": gid,
                "season": season,
                "week": week,
                "season_week": f"{season}-{week:02d}",
                "actual_margin": actual,
                "m_challenger": m_c,
                "m_if": m_if,
                "m_market": m_m,
                "err_challenger": m_c - actual,
                "err_if": m_if - actual,
                "err_market": m_m - actual,
                "L_challenger": abs(m_c - actual),
                "L_if": abs(m_if - actual),
                "L_market": abs(m_m - actual),
                "signed_diff_vs_if": abs(m_c - actual) - abs(m_if - actual),
                "signed_diff_vs_market": abs(m_c - actual) - abs(m_m - actual),
            }
        )
    return {
        "profile": PROFILE_DEV_MARKET72,
        "n": len(rows),
        "game_ids": [r["game_id"] for r in rows],
        "games": rows,
        "synthetic": True,
        "cert_candidate": CERT_CANDIDATE,
    }


def guarded_finalize_feature_output(
    dest: Path,
    payload: Mapping[str, Any],
    *,
    profile: str,
    candidate_ids: Sequence[str],
    hooks: CohortHooks,
    root: Path,
    joined_ids: Sequence[str] | None = None,
    requested_arm_ids: Mapping[str, Sequence[str]] | None = None,
    candidate_bytes_sha: str | None = None,
    expected_bytes_sha: str | None = None,
) -> dict[str, Any]:
    """Write feature output only after the A feature-output gate passes.

    Protected originals are never written. Dest must be a temp/out path.
    """
    repo = Path(root)
    dest = Path(dest)
    try:
        rel = dest.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        rel = None
    if rel in PROTECTED_ORIGINALS:
        raise VerifyIntegrateRefuse(f"refusing to write protected original {rel}")
    gate = hooks.before_feature_output(
        profile,
        candidate_ids,
        joined_ids=joined_ids,
        requested_arm_ids=requested_arm_ids,
        candidate_bytes_sha=candidate_bytes_sha,
        expected_bytes_sha=expected_bytes_sha,
        root=repo,
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "schema_version": "nfl-t5153u-feature-output-v1",
        "profile": profile,
        "n": len(list(candidate_ids)),
        "gate": dict(gate),
        "payload_sha256": sha256_text(
            json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        ),
        "cert_candidate": CERT_CANDIDATE,
        "finalized": True,
    }
    dest.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "dest": dest.as_posix(), "gate": dict(gate)}


def run_scoped_research_verify(
    profile: str,
    payload: Mapping[str, Any],
    candidate_ids: Sequence[str],
    *,
    hooks: CohortHooks,
    outcome_loader: OutcomeReadSpy | None = None,
    joined_ids: Sequence[str] | None = None,
    requested_arm_ids: Mapping[str, Sequence[str]] | None = None,
    candidate_bytes_sha: str | None = None,
    expected_bytes_sha: str | None = None,
    coverage_blocked: bool = False,
    root: Path | None = None,
    invoke_outcome_after_gates: bool = False,
    finalize_dest: Path | None = None,
) -> dict[str, Any]:
    """Guarded caller: A feature gate, A outcome-load gate, then numerical.

    ``invoke_outcome_after_gates`` is the synthetic-positive ordering proof.
    Normal command leaves it false (no real EVAL).
    """
    if profile not in PROFILES:
        raise VerifyIntegrateRefuse(f"unknown profile {profile}")
    refuse_synthetic_flag(payload, label=profile)
    spy = outcome_loader if outcome_loader is not None else OutcomeReadSpy()
    if getattr(spy, "reads", 0) not in (None, 0):
        raise VerifyIntegrateRefuse("outcome loader already read — refuse (join-before-gate)")
    try:
        if finalize_dest is not None:
            guarded_finalize_feature_output(
                finalize_dest,
                payload,
                profile=profile,
                candidate_ids=candidate_ids,
                hooks=hooks,
                root=_repo_root(root),
                joined_ids=joined_ids,
                requested_arm_ids=requested_arm_ids,
                candidate_bytes_sha=candidate_bytes_sha,
                expected_bytes_sha=expected_bytes_sha,
            )
        feature = hooks.before_feature_output(
            profile,
            candidate_ids,
            joined_ids=joined_ids,
            requested_arm_ids=requested_arm_ids,
            candidate_bytes_sha=candidate_bytes_sha,
            expected_bytes_sha=expected_bytes_sha,
            root=root,
        )
        outcome = hooks.before_target_outcome(
            profile,
            candidate_ids,
            frozen_bytes_sha=candidate_bytes_sha,
            expected_bytes_sha=expected_bytes_sha,
            coverage_blocked=coverage_blocked,
            outcome_loader=spy,
            joined_ids=joined_ids,
            requested_arm_ids=requested_arm_ids,
            root=root,
        )
        if getattr(spy, "reads", 0) != 0:
            raise VerifyIntegrateRefuse("cohort gate invoked target-outcome loader")
        numerical = validate_profile_output(
            profile,
            payload,
            expected_ids=candidate_ids,
        )
        if invoke_outcome_after_gates:
            spy()
    except Exception:
        if getattr(spy, "reads", 0) != 0:
            raise VerifyIntegrateRefuse(
                "target scoring outcomes were read on refusal — refuse"
            )
        raise
    if invoke_outcome_after_gates:
        if getattr(spy, "reads", 0) != 1:
            raise VerifyIntegrateRefuse("expected one post-gate synthetic outcome read")
    elif getattr(spy, "reads", 0) != 0:
        raise VerifyIntegrateRefuse("target scoring outcomes were read before receipt")
    n_num = int(numerical.get("n") or 0)
    if n_num != len(list(candidate_ids)):
        raise VerifyIntegrateRefuse(
            f"{profile} numerical n={n_num} != cohort n={len(list(candidate_ids))}"
        )
    return {
        "ok": True,
        "profile": profile,
        "feature_gate": dict(feature),
        "outcome_gate": dict(outcome),
        "numerical": dict(numerical),
        "outcome_loader_reads": int(getattr(spy, "reads", 0)),
        "outcome_loader_invoked_after_gates": bool(invoke_outcome_after_gates),
        "real_eval_executed": False,
        "cert_candidate": CERT_CANDIDATE,
        "limitations": dict(LIMITATIONS),
    }


def verify_pinned_artifacts(root: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    errors: list[str] = []

    def pin(name: str, path: Path, expected: str | None) -> None:
        if not path.is_file():
            errors.append(f"{name} missing: {path}")
            checks.append({"name": name, "ok": False, "error": "missing"})
            return
        digest = sha256_file(path)
        ok = expected is None or digest == expected
        if not ok:
            errors.append(f"{name} sha {digest} != pinned {expected}")
        checks.append(
            {
                "name": name,
                "ok": ok,
                "path": repo_relative_posix(root, path),
                "sha256": digest,
            }
        )

    pin("FEATURE_RECON_REG496", root / REG496_PATH, REG496_SHA256)
    pin("ORIGINAL_502_HISTORICAL", root / ORIGINAL_502_PATH, ORIGINAL_502_SHA256)
    pin("DEV437_RESULT_66c3bde1", root / DEV437_RESULT_PATH, DEV437_RESULT_SHA256)
    pin("MATCHED72_RESULT_316345fa", root / MARKET72_RESULT_PATH, MARKET72_RESULT_SHA256)
    pin("B1_UNIVERSE_ADMISSIBLE_QUOTES", root / B1_UNIVERSE_PATH, B1_UNIVERSE_SHA256)
    pin("WORKER_A_FORECASTS_DEV_R5_496", root / A_FORECASTS_PATH, A_FORECASTS_SHA256)
    pin("WORKER_A_FREEZE_MANIFEST", root / A_MANIFEST_PATH, A_MANIFEST_SHA256)
    pin("WORKER_A_Q2_HISTORY_FREEZE", root / A_Q2_PATH, A_Q2_SHA256)
    pin("WORKER_A_COMPARE_437", root / A_COMPARE_PATH, A_COMPARE_SHA256)
    pin("WORKER_A_PHASE2_POSITIVE_PATH", root / A_PHASE2_PATH, A_PHASE2_SHA256)
    ce = try_load_cohort_module()
    if ce is not None:
        pin("TASK_MANIFEST", root / ce.TASK_MANIFEST_REL, ce.TASK_MANIFEST_SHA256)
        pin(
            "ACCEPTED_DEV_MARKET72",
            root / ce.ACCEPTED_MARKET72_PATH,
            ce.DEV_MARKET72_FILE_SHA256,
        )
    return {"ok": not errors, "checks": checks, "errors": errors, "cohort_module": ce is not None}


def bind_worker_a_forecast_freeze(
    root: Path,
    *,
    outcome_loader: OutcomeReadSpy | None = None,
) -> dict[str, Any]:
    """Read-only pin of Worker A freeze. No produce-μ rewrite. No Cos bind."""
    repo = _repo_root(root)
    pins = (
        (A_FORECASTS_PATH, A_FORECASTS_SHA256, "forecasts"),
        (A_MANIFEST_PATH, A_MANIFEST_SHA256, "freeze_manifest"),
        (A_Q2_PATH, A_Q2_SHA256, "q2_history_freeze"),
        (A_COMPARE_PATH, A_COMPARE_SHA256, "compare_437"),
        (A_PHASE2_PATH, A_PHASE2_SHA256, "phase2_positive_path"),
        (REG496_PATH, REG496_SHA256, "feature_json"),
    )
    verified: dict[str, str] = {}
    for rel, expected, name in pins:
        path = repo / rel
        if not path.is_file():
            raise VerifyIntegrateRefuse(f"Worker A {name} missing: {rel}")
        digest = sha256_file(path)
        if digest != expected:
            raise VerifyIntegrateRefuse(f"Worker A {name} sha {digest} != pin {expected}")
        verified[name] = digest

    forecasts = load_json(repo / A_FORECASTS_PATH)
    manifest = load_json(repo / A_MANIFEST_PATH)
    compare = load_json(repo / A_COMPARE_PATH)
    documented_phase2 = load_json(repo / A_PHASE2_PATH)
    q2_history = load_json(repo / A_Q2_PATH) if (repo / A_Q2_PATH).is_file() else {}

    if int(forecasts.get("n_forecasts") or 0) != 496:
        raise VerifyIntegrateRefuse(f"Worker A n_forecasts={forecasts.get('n_forecasts')} != 496")
    if int(forecasts.get("n_if_finite") or 0) != 496:
        raise VerifyIntegrateRefuse(f"Worker A n_if_finite={forecasts.get('n_if_finite')} != 496")
    if int(forecasts.get("n_q2_hold") or 0) != 496:
        raise VerifyIntegrateRefuse(f"Worker A n_q2_hold={forecasts.get('n_q2_hold')} != 496")
    if int(forecasts.get("n_candidate_finite") or 0) != 0:
        raise VerifyIntegrateRefuse("Worker A invented Q2/candidate — refuse")
    if forecasts.get("q2_hold") is not True:
        raise VerifyIntegrateRefuse("Worker A q2_hold must stay explicit HOLD")
    if int(compare.get("n_replayed_within_tol") or 0) != 437:
        raise VerifyIntegrateRefuse("Worker A common437 replay != 437/437")
    if int(compare.get("n_blocker") or 0) != 0:
        raise VerifyIntegrateRefuse("Worker A common437 IF replay BLOCKER")
    if documented_phase2.get("executed") is not False:
        raise VerifyIntegrateRefuse("Worker A Phase 2 must stay documented, not executed")
    if manifest.get("identity_sha256") != REG496_IDENTITY_SHA256:
        raise VerifyIntegrateRefuse(
            f"Worker A manifest identity {manifest.get('identity_sha256')} != 6429f859"
        )

    from .r5_496_freeze import phase2_positive_path, refuse_target_scoring

    spy = outcome_loader if outcome_loader is not None else OutcomeReadSpy(
        lambda: {"SHOULD_NOT_LOAD": {"home_score": 99}}
    )
    scoring_refuse = refuse_target_scoring(
        candidate_ids=[
            str(row.get("game_id")) for row in (forecasts.get("forecasts") or []) if row.get("game_id")
        ],
        root=repo,
        outcome_loader=spy,
        coverage_blocked=True,
    )
    if getattr(spy, "reads", 0) != 0:
        raise VerifyIntegrateRefuse("Worker A bind read target scoring outcomes")
    live_phase2 = phase2_positive_path()
    if live_phase2.get("executed") is not False:
        raise VerifyIntegrateRefuse("Phase 2 positive path executed during bind — refuse")

    hold_reason = (
        forecasts.get("q2_hold_reason")
        or q2_history.get("hold_reason")
        or "2013–19 REG unproven — do not invent Q2"
    )
    return {
        "ok": True,
        "status": "PINNED",
        "tip": WORKER_A_TIP,
        "stamp": WORKER_A_STAMP,
        "pr": WORKER_A_PR,
        "branch": WORKER_A_BRANCH,
        "command": WORKER_A_COMMAND,
        "identity_sha256": REG496_IDENTITY_SHA256,
        "feature_json_sha256": REG496_SHA256,
        "forecasts_sha256": verified["forecasts"],
        "freeze_manifest_sha256": verified["freeze_manifest"],
        "compare_437_sha256": verified["compare_437"],
        "n_forecasts": 496,
        "n_if_finite": 496,
        "n_q2_hold": 496,
        "n_q2_finite": int(forecasts.get("n_q2_finite") or 0),
        "n_candidate_finite": 0,
        "q2": {
            "status": "HOLD",
            "leg": "HOLD",
            "hold_q2": True,
            "n_hold": 496,
            "candidate": "HOLD",
            "invented_q2": False,
            "reason": hold_reason,
            "years_unproven": [2013, 2014, 2015, 2016, 2017, 2018, 2019],
            "reg_unproven": True,
        },
        "common437": {
            "n_common": int(compare.get("n_common") or 437),
            "n_replayed": 437,
            "n_blocker": 0,
        },
        "phase2_positive_path": {
            "status": "READINESS_ONLY",
            "executed": False,
            "cos_bind": False,
            "score_flag": False,
            "target_scoring_loader": False,
            "one_dev_diagnostic": False,
            "invoke_outcome_after_gates_available": True,
            "invoke_outcome_after_gates": False,
            "requires": list(live_phase2.get("requires") or documented_phase2.get("requires") or []),
        },
        "scoring_refuse": {
            "refused": True,
            "outcome_loader_reads": int(scoring_refuse.get("outcome_loader_reads") or 0),
            "target_labels_loaded": int(scoring_refuse.get("target_labels_loaded") or 0),
            "coverage_blocked": True,
            "stop": scoring_refuse.get("stop"),
        },
        "cos_bind": False,
        "scoring": None,
        "eval": None,
        "bytes_verified": verified,
    }


def _python_with_pytest(root: Path) -> str:
    candidates = [
        sys.executable,
        str(root / "services/model-service/.venv/bin/python"),
        str(root / ".venv/bin/python"),
        "/Users/ryankos/kosedge/.venv/bin/python",
        "/Users/ryankos/kosedge/services/model-service/.venv/bin/python",
    ]
    for exe in candidates:
        if not exe or not Path(exe).is_file():
            continue
        probe = subprocess.run([exe, "-c", "import pytest"], capture_output=True, text=True)
        if probe.returncode == 0:
            return exe
    raise VerifyIntegrateRefuse("pytest not available on this machine — no new installs")


def run_focused_tests(root: Path) -> dict[str, Any]:
    tests = list(FOCUSED_TESTS)
    if (root / COHORT_TEST).is_file():
        tests.append(COHORT_TEST)
    commands: list[dict[str, Any]] = []
    all_ok = True
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "services" / "model-service")
    env["T5151U_SKIP_NESTED_TESTS"] = "1"
    python_exe = _python_with_pytest(root)
    for test in tests:
        cmd = [python_exe, "-m", "pytest", test, "-q", "--tb=line"]
        proc = subprocess.run(cmd, cwd=str(root), env=env, capture_output=True, text=True)
        ok = proc.returncode == 0
        all_ok = all_ok and ok
        raw_stdout = "\n".join((proc.stdout or "").splitlines()[-12:])
        raw_stderr = "\n".join((proc.stderr or "").splitlines()[-12:])
        commands.append(
            {
                "command": f"python -m pytest {test} -q --tb=line",
                "ok": ok,
                "returncode": proc.returncode,
                "stdout_tail": strip_pytest_elapsed(raw_stdout),
                "stderr_tail": strip_pytest_elapsed(raw_stderr),
                "elapsed": extract_pytest_elapsed(raw_stdout) + extract_pytest_elapsed(raw_stderr),
            }
        )
    raw_tests = {
        "ok": all_ok,
        "commands": commands,
        "tests": tests,
        "interpreter_excluded_from_output_hash": True,
        "elapsed_side_metadata": [row.get("elapsed") or [] for row in commands],
    }
    semantic = semantic_tests_payload(raw_tests)
    semantic["_elapsed_for_runtime"] = [
        item for row in commands for item in (row.get("elapsed") or [])
    ]
    return semantic


def git_tip(root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return "UNKNOWN"
    return (proc.stdout or "").strip()


def build_receipt(
    *,
    root: Path,
    pins: Mapping[str, Any],
    profiles: Mapping[str, Any],
    tests: Mapping[str, Any],
    errors: Sequence[str],
    interpreter: str | None = None,
    market_arm: Mapping[str, Any] | None = None,
    worker_a: Mapping[str, Any] | None = None,
    phase2_one_exec: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    code_files = [
        root / "services/model-service/src/services/nfl_t5107u/eval_result_contract.py",
        root / "services/model-service/src/services/nfl_t5107u/verify_integrate.py",
        root / "services/model-service/src/services/nfl_t5107u/market_arm_freeze.py",
        root / "services/model-service/src/services/nfl_t5107u/r5_496_freeze.py",
        root / "services/model-service/src/services/nfl_t5107u/r5_phase2_one_exec.py",
        root / "scripts/nfl/run_nfl_t5151u_verify_integrate.py",
        root / "scripts/nfl/freeze_nfl_t5155u_market_arm.py",
        root / "scripts/nfl/run_nfl_r5_496_freeze_t5155u.py",
        root / "scripts/nfl/run_nfl_t5155u_r5_phase2_one_exec.py",
    ]
    ce_path = root / "services/model-service/src/services/nfl_t5107u/cohort_enforcement.py"
    if ce_path.is_file():
        code_files.append(ce_path)
    spec_files = [
        p
        for p in [
            root / "ops/CURSOR_ADDENDUM_t5151u_NUMERICAL_INTEGRATION_v1.md",
            root / "ops/CURSOR_ADDENDUM_t5155u_R5_PHASE1_v1.md",
            root / "ops/CURSOR_ADDENDUM_t5155u_R5_496_FREEZE_v1.md",
        ]
        if p.is_file()
    ]
    input_files = [
        root / REG496_PATH,
        root / ORIGINAL_502_PATH,
        root / DEV437_RESULT_PATH,
        root / MARKET72_RESULT_PATH,
        root / TASK_MANIFEST_REL,
        root / "data/ops/nfl-t5151u-cohort-enforcement/ACCEPTED_DEV_MARKET72_IDS.json",
        root / B1_UNIVERSE_PATH,
        root / A_FORECASTS_PATH,
        root / A_MANIFEST_PATH,
        root / A_Q2_PATH,
        root / A_COMPARE_PATH,
        root / A_PHASE2_PATH,
    ]
    code = hash_file_list(root, code_files)
    spec = hash_file_list(root, spec_files)
    inputs = hash_file_list(root, input_files)
    artifacts = list(pins.get("checks") or [])
    failed = bool(errors) or not pins.get("ok") or not tests.get("ok")
    for name in PROFILES:
        body = profiles.get(name)
        if not isinstance(body, Mapping) or not body.get("ok"):
            failed = True
    if market_arm is not None and not market_arm.get("ok", True):
        failed = True
    if worker_a is not None and not worker_a.get("ok", True):
        failed = True
    if phase2_one_exec is not None and phase2_one_exec.get("error"):
        failed = True
    status = "FAILED" if failed else "CHECKS_PASSED_AWAITING_ALEX_PREFLIGHT"
    elapsed = list((tests or {}).get("_elapsed_for_runtime") or collect_pytest_elapsed(tests))
    semantic_tests = semantic_tests_payload(tests)
    runtime = {
        "interpreter": interpreter or "python3",
        "tip_sha": git_tip(root),
        "pytest_elapsed": elapsed,
    }
    worker_a_summary: Any = worker_a if worker_a else "PENDING"
    if worker_a_summary == "PENDING" and market_arm:
        payload_wa = (market_arm.get("payload") or {}).get("worker_a_forecast_freeze")
        if payload_wa:
            worker_a_summary = payload_wa
    market_summary = {
        "status": "NOT_RUN",
        "worker_a_forecast_freeze": worker_a_summary,
        "scoring": None,
        "eval": None,
    }
    if market_arm:
        market_summary = {
            "status": "FROZEN" if market_arm.get("ok") else "FAILED",
            "ok": bool(market_arm.get("ok")),
            "n": market_arm.get("n"),
            "n_by_season": (market_arm.get("payload") or {}).get("intersection", {}).get(
                "n_by_season"
            ),
            "missing_n": (market_arm.get("payload") or {}).get("intersection", {}).get(
                "missing_n"
            ),
            "one_book_n": (market_arm.get("payload") or {}).get("intersection", {}).get(
                "one_book_n"
            ),
            "two_book_n": (market_arm.get("payload") or {}).get("intersection", {}).get(
                "two_book_n"
            ),
            "bytes_sha256": market_arm.get("bytes_sha256"),
            "identity_sha256": market_arm.get("identity_sha256"),
            "b1_universe_sha256": B1_UNIVERSE_SHA256,
            "r2c_hold_unchanged": True,
            "worker_a_forecast_freeze": worker_a_summary,
            "scoring": None,
            "eval": None,
        }
    receipt = {
        "schema_version": SCHEMA,
        "ticket": TICKET,
        "package": PACKAGE,
        "cert_candidate": CERT_CANDIDATE,
        "draft": True,
        "verified": False,
        "status": status,
        "stop": "STOP_AWAITING_ALEX_INDEPENDENT_RO",
        "self_accept": False,
        "nfl_green": False,
        "real_eval_executed": False,
        "owner_clear_sha8": OWNER_CLEAR_SHA8,
        "owner_amend_sha8": OWNER_AMEND_SHA8,
        "cos_order_b_sha8": COS_ORDER_B_SHA8,
        "cos_order_return_sha8": COS_ORDER_RETURN_SHA8,
        "cos_accept_scoped_sha8": COS_ACCEPT_SCOPED_SHA8,
        "alex_return_sha8": ALEX_RETURN_SHA8,
        "alex_return_accepted_sha8": ALEX_RETURN_ACCEPTED_SHA8,
        "owner_clear_t5155u_sha8": OWNER_CLEAR_T5155U_SHA8,
        "cos_order_t5155u_sha8": COS_ORDER_T5155U_SHA8,
        "cos_accept_700_sha8": COS_ACCEPT_700_SHA8,
        "alex_700_sha8": ALEX_700_SHA8,
        "closed_700_tip": TIP_700,
        "worker_a_tip": WORKER_A_TIP,
        "worker_a_stamp": WORKER_A_STAMP,
        "worker_a_forecast_freeze": worker_a_summary,
        "q2_hold": (worker_a or {}).get("q2")
        if isinstance(worker_a, Mapping)
        else {
            "status": "HOLD",
            "reason": "2013–19 REG unproven — do not invent Q2",
        },
        "phase2_positive_path": (worker_a or {}).get("phase2_positive_path")
        if isinstance(worker_a, Mapping)
        else {
            "status": "READINESS_ONLY",
            "executed": False,
            "cos_bind": False,
        },
        "phase2_one_exec": {
            "status": (phase2_one_exec or {}).get("status")
            if isinstance(phase2_one_exec, Mapping)
            else "NOT_RUN",
            "outcome_loader_reads": (phase2_one_exec or {}).get("outcome_loader_reads")
            if isinstance(phase2_one_exec, Mapping)
            else 0,
            "forecasts_sha256": A_FORECASTS_SHA256,
            "cos_bind": False,
            "score_flag": False,
            "scored": None,
        },
        "package_a_tip": PACKAGE_A_TIP,
        "package_a_stamp": PACKAGE_A_STAMP,
        "partial_plumbing_tip": PARTIAL_PLUMBING_TIP,
        "partial_plumbing_stamp": PARTIAL_PLUMBING_STAMP,
        "partial_plumbing_not_verified": True,
        "r4_496_accepted_tip": R4_496_ACCEPTED_TIP,
        "alex_pass_ro": ALEX_PASS_RO,
        "matched72_source_tip": MARKET72_SOURCE_TIP,
        "command": "python3 scripts/nfl/run_nfl_t5151u_verify_integrate.py",
        "receipt_path": f"{OUT_DIR.as_posix()}/{RECEIPT_NAME}",
        "profiles": {name: name for name in PROFILES},
        "hashes": {
            "code": code,
            "spec": spec,
            "input": inputs,
            "artifacts": artifacts,
            "profiles": {
                name: {
                    "cohort_sha256": (profiles.get(name) or {}).get("feature_gate", {}).get(
                        "identity_sha256"
                    ),
                    "joined_row_sha256": (profiles.get(name) or {})
                    .get("numerical", {})
                    .get("joined_row_sha256"),
                    "n": (profiles.get(name) or {}).get("numerical", {}).get("n"),
                }
                for name in PROFILES
            },
        },
        "pinned_artifacts": pins,
        "profile_results": profiles,
        "checks": artifacts,
        "errors": list(errors),
        "tests": semantic_tests,
        "market_arm": market_summary,
        "interval_contract": dict(INTERVAL_CONTRACT),
        "evidence_limits": dict(LIMITATIONS),
        "limitations": dict(LIMITATIONS),
    }
    receipt["hashes"]["market_intersection"] = {
        "n": market_summary.get("n"),
        "bytes_sha256": market_summary.get("bytes_sha256"),
        "identity_sha256": market_summary.get("identity_sha256"),
        "b1_universe_sha256": market_summary.get("b1_universe_sha256"),
    }
    receipt["hashes"]["worker_a_forecast_freeze"] = {
        "status": (worker_a or {}).get("status") if isinstance(worker_a, Mapping) else "PENDING",
        "identity_sha256": REG496_IDENTITY_SHA256,
        "feature_json_sha256": REG496_SHA256,
        "forecasts_sha256": A_FORECASTS_SHA256,
        "freeze_manifest_sha256": A_MANIFEST_SHA256,
        "n_if_finite": 496 if isinstance(worker_a, Mapping) else None,
        "q2_hold": 496 if isinstance(worker_a, Mapping) else None,
        "n_candidate_finite": 0,
        "common437_replay": "437/437",
        "n_blocker": 0,
    }
    canonical = {
        k: v
        for k, v in receipt.items()
        if k not in {"hashes", "runtime", "tip_sha", "interpreter", "side_metadata"}
    }
    receipt["runtime"] = runtime
    receipt["side_metadata"] = {
        "pytest_elapsed": elapsed,
        "pytest_elapsed_semantic": False,
    }
    receipt["tip_sha"] = runtime["tip_sha"]
    receipt["interpreter"] = runtime["interpreter"]
    receipt["hashes"]["output_sha256"] = sha256_text(
        json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
    )
    return receipt


def write_receipt(receipt: Mapping[str, Any], root: Path) -> Path:
    dest = root / OUT_DIR / RECEIPT_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    r5 = root / R5_OUT_DIR / RECEIPT_NAME
    r5.parent.mkdir(parents=True, exist_ok=True)
    r5.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return dest


def run_one_command(*, root: Path | None = None, hooks: CohortHooks | None = None) -> dict[str, Any]:
    """Complete offline command. Real 496 / 437 / 72 artifacts only."""
    repo = _repo_root(root)
    errors: list[str] = []
    pins = verify_pinned_artifacts(repo)
    errors.extend(list(pins.get("errors") or []))
    ce = try_load_cohort_module()
    try:
        active_hooks = hooks or require_cohort_hooks(ce)
    except VerifyIntegrateRefuse as exc:
        errors.append(str(exc))
        receipt = build_receipt(
            root=repo, pins=pins, profiles={}, tests={"ok": False}, errors=errors
        )
        write_receipt(receipt, repo)
        raise

    if ce is None:
        errors.append("cohort_enforcement required — no partial-result fallback")
    profiles: dict[str, Any] = {}
    out_dir = repo / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    required = (
        (PROFILE_FEATURE_RECON_REG496, repo / REG496_PATH, REG496_SHA256),
        (PROFILE_DEV_IF437, repo / DEV437_RESULT_PATH, DEV437_RESULT_SHA256),
        (PROFILE_DEV_MARKET72, repo / MARKET72_RESULT_PATH, MARKET72_RESULT_SHA256),
    )
    for profile, path, expected in required:
        if not path.is_file():
            errors.append(f"missing profile artifact {profile}: {path}")

    if437_payload = None
    if (repo / DEV437_RESULT_PATH).is_file():
        if437_payload = load_json(repo / DEV437_RESULT_PATH)
        try:
            refuse_synthetic_flag(if437_payload, label=PROFILE_DEV_IF437)
        except EvalResultContractRefuse as exc:
            errors.append(str(exc))

    if (repo / REG496_PATH).is_file() and active_hooks is not None and ce is not None:
        recon = load_json(repo / REG496_PATH)
        recon_ids = ce.expected_profile_ids(PROFILE_FEATURE_RECON_REG496, repo)
        spy = OutcomeReadSpy(lambda: {"SHOULD_NOT_LOAD": {"home_score": 99}})
        dest = out_dir / "FEATURE_OUTPUT_FEATURE_RECON_REG496.json"
        try:
            profiles[PROFILE_FEATURE_RECON_REG496] = run_scoped_research_verify(
                PROFILE_FEATURE_RECON_REG496,
                recon,
                recon_ids,
                hooks=active_hooks,
                outcome_loader=spy,
                candidate_bytes_sha=sha256_file(repo / REG496_PATH),
                expected_bytes_sha=REG496_SHA256,
                root=repo,
                finalize_dest=dest,
            )
        except (VerifyIntegrateRefuse, EvalResultContractRefuse, Exception) as exc:
            errors.append(f"{PROFILE_FEATURE_RECON_REG496}: {exc}")
            profiles[PROFILE_FEATURE_RECON_REG496] = {"ok": False, "error": str(exc)}
            if spy.reads != 0:
                errors.append("FEATURE_RECON_REG496 refusal read target outcomes")

    if if437_payload is not None and active_hooks is not None and ce is not None:
        if437_ids = ce.expected_profile_ids(PROFILE_DEV_IF437, repo)
        spy = OutcomeReadSpy()
        try:
            profiles[PROFILE_DEV_IF437] = run_scoped_research_verify(
                PROFILE_DEV_IF437,
                if437_payload,
                if437_ids,
                hooks=active_hooks,
                outcome_loader=spy,
                joined_ids=if437_ids,
                candidate_bytes_sha=sha256_file(repo / DEV437_RESULT_PATH),
                expected_bytes_sha=DEV437_RESULT_SHA256,
                root=repo,
            )
            profiles[PROFILE_DEV_IF437]["n_by_season"] = dict(DEV_IF437_BY_SEASON)
            profiles[PROFILE_DEV_IF437]["joined_row_sha256"] = (
                profiles[PROFILE_DEV_IF437]
                .get("numerical", {})
                .get("joined_row_sha256")
            )
        except (VerifyIntegrateRefuse, EvalResultContractRefuse, Exception) as exc:
            errors.append(f"{PROFILE_DEV_IF437}: {exc}")
            profiles[PROFILE_DEV_IF437] = {"ok": False, "error": str(exc)}

    if (
        if437_payload is not None
        and (repo / MARKET72_RESULT_PATH).is_file()
        and active_hooks is not None
        and ce is not None
    ):
        market72_ids = ce.expected_profile_ids(PROFILE_DEV_MARKET72, repo)
        market72_raw = load_json(repo / MARKET72_RESULT_PATH)
        spy = OutcomeReadSpy()
        try:
            refuse_synthetic_flag(market72_raw, label=PROFILE_DEV_MARKET72)
            joined = join_market72_from_if437(
                if437_payload, market72_raw, expected_ids=market72_ids
            )
            profiles[PROFILE_DEV_MARKET72] = run_scoped_research_verify(
                PROFILE_DEV_MARKET72,
                joined,
                market72_ids,
                hooks=active_hooks,
                outcome_loader=spy,
                joined_ids=market72_ids,
                candidate_bytes_sha=sha256_file(repo / MARKET72_RESULT_PATH),
                expected_bytes_sha=MARKET72_RESULT_SHA256,
                root=repo,
            )
            profiles[PROFILE_DEV_MARKET72]["joined_row_sha256"] = joined_row_sha256(
                joined["games"]
            )
            profiles[PROFILE_DEV_MARKET72]["n_by_season"] = dict(DEV_MARKET72_BY_SEASON)
        except (VerifyIntegrateRefuse, EvalResultContractRefuse, Exception) as exc:
            errors.append(f"{PROFILE_DEV_MARKET72}: {exc}")
            profiles[PROFILE_DEV_MARKET72] = {"ok": False, "error": str(exc)}

    for name in PROFILES:
        if name not in profiles:
            errors.append(f"missing profile result {name} — no partial-result fallback")
            profiles[name] = {"ok": False, "error": "missing"}

    worker_a: dict[str, Any] | None = None
    try:
        spy_a = OutcomeReadSpy(lambda: {"SHOULD_NOT_LOAD": {"home_score": 99}})
        worker_a = bind_worker_a_forecast_freeze(repo, outcome_loader=spy_a)
        if spy_a.reads != 0:
            raise VerifyIntegrateRefuse("Worker A bind read target scoring outcomes")
    except Exception as exc:
        errors.append(f"WORKER_A_FORECAST_FREEZE: {exc}")
        worker_a = {"ok": False, "status": "FAILED", "error": str(exc)}

    try:
        from .r5_phase2_one_exec import run_phase2_one_exec

        spy_p2 = OutcomeReadSpy(lambda: {"SHOULD_NOT_LOAD": {"home_score": 99}})
        phase2_exec = run_phase2_one_exec(
            root=repo,
            outcome_loader=spy_p2,
            invoke_outcome_after_gates=False,
            write=True,
        )
        if spy_p2.reads != 0:
            raise VerifyIntegrateRefuse("Phase-2 default command read target scoring outcomes")
    except Exception as exc:
        errors.append(f"PHASE2_ONE_EXEC: {exc}")
        phase2_exec = {"ok": False, "error": str(exc)}

    market_arm: dict[str, Any] | None = None
    try:
        from .market_arm_freeze import run_market_arm_freeze

        spy = OutcomeReadSpy(lambda: {"SHOULD_NOT_LOAD": {"home_score": 99}})
        market_arm = run_market_arm_freeze(
            root=repo,
            outcome_loader=spy,
            finalize=True,
            worker_a=worker_a if worker_a and worker_a.get("ok") else None,
        )
        if spy.reads != 0:
            raise VerifyIntegrateRefuse("market-arm freeze read target scoring outcomes")
    except Exception as exc:
        errors.append(f"MARKET_ARM_FREEZE: {exc}")
        market_arm = {"ok": False, "error": str(exc)}

    tests = run_focused_tests(repo)
    if not tests["ok"]:
        errors.append("focused tests failed")
    if ce is not None:
        pins = dict(pins)
        pins["cohort_sha256"] = ce.cohort_identity_sha256(
            ce.expected_profile_ids(PROFILE_FEATURE_RECON_REG496, repo)
        )
    receipt = build_receipt(
        root=repo,
        pins=pins,
        profiles=profiles,
        tests=tests,
        errors=errors,
        interpreter="python3",
        market_arm=market_arm,
        worker_a=worker_a,
        phase2_one_exec=phase2_exec,
    )
    write_receipt(receipt, repo)
    if receipt["status"] != "CHECKS_PASSED_AWAITING_ALEX_PREFLIGHT":
        raise VerifyIntegrateRefuse(
            "nonzero failure prevented VERIFIED/final output: " + "; ".join(errors[:8])
        )
    return receipt
