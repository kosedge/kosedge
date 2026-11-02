"""t5151u scoped research caller + one-command integration owner.

Wires Package A cohort gates (before feature-output finalization and
before target-outcome loading) and Package B numerical checks (before
receipt publication). Synthetic EVAL paths only. Never runs real EVAL.

Nonzero failure prevents VERIFIED/final output. CERT=0. DRAFT≠merge.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .eval_result_contract import (
    ALEX_PASS_RO,
    CERT_CANDIDATE,
    COS_ACCEPT_SCOPED_SHA8,
    COS_ORDER_B_SHA8,
    PACKAGE_A_STAMP,
    PACKAGE_A_TIP,
    DEV_IF437_BY_SEASON,
    DEV_MARKET72_BY_SEASON,
    INTERVAL_CONTRACT,
    OWNER_CLEAR_SHA8,
    PROFILE_DEV_IF437,
    PROFILE_DEV_MARKET72,
    PROFILE_FEATURE_RECON_REG496,
    PROFILES,
    R4_496_ACCEPTED_TIP,
    EvalResultContractRefuse,
    validate_profile_output,
)
from .last_played_cohort import ORIGINAL_502_PATH, ORIGINAL_502_SHA256
from .recon_driver import sha256_file

TICKET = "t5151u"
PACKAGE = "C_VERIFY_INTEGRATE"
SCHEMA = "nfl-t5151u-verify-integrate-receipt-v1"
CERT_CANDIDATE = CERT_CANDIDATE
OUT_DIR = Path("data/ops/nfl-t5151u-verify-integrate")
RECEIPT_NAME = "RECEIPT.json"
REG496_PATH = "data/ops/nfl-t5146u-r4-last-played-dev/DEV_RECON_LAST_PLAYED_2020_2021_REG.json"
REG496_SHA256 = "282f979b52890c7ed943eeb9c0836dd7f50b9a925cf3e82fdfc856834646402c"
FEATURE_RECON_REG496_ARTIFACT_PATH = REG496_PATH
FEATURE_RECON_REG496_ARTIFACT_SHA256 = REG496_SHA256

FOCUSED_TESTS = (
    "services/model-service/tests/test_nfl_t5151u_numerical_output_contract.py",
    "services/model-service/tests/test_nfl_t5151u_verify_integrate.py",
    "services/model-service/tests/test_nfl_t5149u_last_played_reg_cohort.py",
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
}


class VerifyIntegrateRefuse(ValueError):
    """Fail-closed verification/integration. Not ACCEPT. Not EVAL."""


class OutcomeReadSpy:
    """Counts target-outcome reads. Caller/gates must leave this at zero on refuse."""

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


def sha256_paths(paths: Sequence[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


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


def _interval(point: float, n: int, *, unit: str, control: str) -> dict[str, Any]:
    lo = point - 0.25
    hi = point + 0.25
    return {
        "point": point,
        "ci95": [lo, hi],
        "B": INTERVAL_CONTRACT["B"],
        "seed": INTERVAL_CONTRACT["seed"],
        "n": n,
        "unit": unit,
        "control": control,
        "declared_contract_only": True,
        "independently_rerun": False,
    }


def _season_table(rows: Sequence[Mapping[str, Any]], *, market: bool) -> dict[str, Any]:
    from .eval_result_contract import recompute_from_saved_rows

    achieved = recompute_from_saved_rows(rows, require_market=market)
    body = {
        "n": achieved["n"],
        "mae_challenger": achieved["mae_challenger"],
        "mae_if": achieved["mae_if"],
        "rmse_challenger": achieved["rmse_challenger"],
        "rmse_if": achieved["rmse_if"],
        "bias_challenger": achieved["bias_challenger"],
        "bias_if": achieved["bias_if"],
        "mean_signed_diff_vs_if": achieved["mean_signed_diff_vs_if"],
    }
    if market:
        body.update(
            {
                "mae_market": achieved["mae_market"],
                "rmse_market": achieved["rmse_market"],
                "bias_market": achieved["bias_market"],
                "mean_signed_diff_vs_market": achieved["mean_signed_diff_vs_market"],
            }
        )
    return body


def build_synthetic_if437_result(game_ids: Sequence[str] | None = None) -> dict[str, Any]:
    """Synthetic IF-only DEV rows. Not real EVAL. Market explicitly unavailable."""
    ids = list(game_ids) if game_ids else [
        "2020_02_CIN_CLE",
        "2021_02_CLE_CIN",
    ]
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
    from .eval_result_contract import recompute_from_saved_rows

    achieved = recompute_from_saved_rows(rows, require_market=False)
    per_season = {
        season: _season_table([r for r in rows if str(r["season"]) == season], market=False)
        for season in achieved["n_by_season"]
    }
    return {
        "profile": PROFILE_DEV_IF437,
        "n": achieved["n"],
        "n_by_season": achieved["n_by_season"],
        "game_ids": [r["game_id"] for r in rows],
        "games": rows,
        "mae_challenger": achieved["mae_challenger"],
        "mae_if": achieved["mae_if"],
        "rmse_challenger": achieved["rmse_challenger"],
        "rmse_if": achieved["rmse_if"],
        "bias_challenger": achieved["bias_challenger"],
        "bias_if": achieved["bias_if"],
        "delta_mae_vs_if": achieved["delta_mae_vs_if"],
        "mean_signed_diff_vs_if": achieved["mean_signed_diff_vs_if"],
        "per_season": per_season,
        "bootstrap_game": _interval(
            float(achieved["mean_signed_diff_vs_if"]), achieved["n"], unit="game", control="if"
        ),
        "bootstrap_season_week": _interval(
            float(achieved["mean_signed_diff_vs_if"]),
            achieved["n"],
            unit="season_week",
            control="if",
        ),
        "market_unavailable": True,
        "market_status": "UNAVAILABLE",
        "cannot_satisfy_profiles": [PROFILE_DEV_MARKET72],
        "eval": None,
        "synthetic": True,
        "cert_candidate": CERT_CANDIDATE,
    }


def build_synthetic_market72_result(game_ids: Sequence[str] | None = None) -> dict[str, Any]:
    """Synthetic candidate/IF/market rows. Not real EVAL."""
    ids = list(game_ids) if game_ids else [
        "2020_02_CIN_CLE",
        "2021_03_CLE_CIN",
    ]
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
    from .eval_result_contract import recompute_from_saved_rows

    achieved = recompute_from_saved_rows(rows, require_market=True)
    per_season = {
        season: _season_table([r for r in rows if str(r["season"]) == season], market=True)
        for season in achieved["n_by_season"]
    }
    return {
        "profile": PROFILE_DEV_MARKET72,
        "n": achieved["n"],
        "n_by_season": achieved["n_by_season"],
        "game_ids": [r["game_id"] for r in rows],
        "games": rows,
        "mae_challenger": achieved["mae_challenger"],
        "mae_if": achieved["mae_if"],
        "mae_market": achieved["mae_market"],
        "rmse_challenger": achieved["rmse_challenger"],
        "rmse_if": achieved["rmse_if"],
        "rmse_market": achieved["rmse_market"],
        "bias_challenger": achieved["bias_challenger"],
        "bias_if": achieved["bias_if"],
        "bias_market": achieved["bias_market"],
        "delta_mae_vs_if": achieved["delta_mae_vs_if"],
        "delta_mae_vs_market": achieved["delta_mae_vs_market"],
        "mean_signed_diff_vs_if": achieved["mean_signed_diff_vs_if"],
        "mean_signed_diff_vs_market": achieved["mean_signed_diff_vs_market"],
        "per_season": per_season,
        "bootstrap_game": _interval(
            float(achieved["mean_signed_diff_vs_if"]), achieved["n"], unit="game", control="if"
        ),
        "bootstrap_season_week": _interval(
            float(achieved["mean_signed_diff_vs_if"]),
            achieved["n"],
            unit="season_week",
            control="if",
        ),
        "bootstrap_game_vs_market": _interval(
            float(achieved["mean_signed_diff_vs_market"]),
            achieved["n"],
            unit="game",
            control="market",
        ),
        "bootstrap_season_week_vs_market": _interval(
            float(achieved["mean_signed_diff_vs_market"]),
            achieved["n"],
            unit="season_week",
            control="market",
        ),
        "eval": None,
        "synthetic": True,
        "cert_candidate": CERT_CANDIDATE,
    }


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
    enforce_profile_n: bool = False,
) -> dict[str, Any]:
    """One scoped caller: cohort gates, then numerical, then result.

    Never invokes the outcome loader. Refusal paths must keep spy.reads == 0.
    """
    if profile not in PROFILES:
        raise VerifyIntegrateRefuse(f"unknown profile {profile}")
    spy = outcome_loader if outcome_loader is not None else OutcomeReadSpy()
    if getattr(spy, "reads", 0) not in (None, 0):
        raise VerifyIntegrateRefuse("outcome loader already read — refuse (join-before-gate)")
    try:
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
            expected_ids=None if payload.get("synthetic") else candidate_ids,
            enforce_profile_n=enforce_profile_n,
        )
    except Exception:
        if getattr(spy, "reads", 0) != 0:
            raise VerifyIntegrateRefuse(
                "target scoring outcomes were read on refusal — refuse"
            )
        raise
    if getattr(spy, "reads", 0) != 0:
        raise VerifyIntegrateRefuse("target scoring outcomes were read before receipt")
    return {
        "ok": True,
        "profile": profile,
        "feature_gate": dict(feature),
        "outcome_gate": dict(outcome),
        "numerical": dict(numerical),
        "outcome_loader_reads": int(getattr(spy, "reads", 0)),
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
                "path": path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path),
                "sha256": digest,
            }
        )

    pin("FEATURE_RECON_REG496", root / REG496_PATH, REG496_SHA256)
    pin("ORIGINAL_502_HISTORICAL", root / ORIGINAL_502_PATH, ORIGINAL_502_SHA256)
    ce = try_load_cohort_module()
    if ce is not None:
        pin("TASK_MANIFEST", root / ce.TASK_MANIFEST_REL, ce.TASK_MANIFEST_SHA256)
        pin(
            "ACCEPTED_DEV_MARKET72",
            root / ce.ACCEPTED_MARKET72_PATH,
            ce.DEV_MARKET72_FILE_SHA256,
        )
    return {"ok": not errors, "checks": checks, "errors": errors, "cohort_module": ce is not None}


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
        probe = subprocess.run(
            [exe, "-c", "import pytest"],
            capture_output=True,
            text=True,
        )
        if probe.returncode == 0:
            return exe
    raise VerifyIntegrateRefuse("pytest not available on this machine — no new installs")


def run_focused_tests(root: Path) -> dict[str, Any]:
    tests = list(FOCUSED_TESTS)
    if (root / COHORT_TEST).is_file():
        tests.append(COHORT_TEST)
    commands: list[dict[str, Any]] = []
    all_ok = True
    env_pythonpath = str(root / "services" / "model-service")
    python_exe = _python_with_pytest(root)
    for test in tests:
        cmd = [
            python_exe,
            "-m",
            "pytest",
            test,
            "-q",
            "--tb=line",
        ]
        env = os.environ.copy()
        env["PYTHONPATH"] = env_pythonpath
        env["T5151U_SKIP_NESTED_TESTS"] = "1"
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
        )
        ok = proc.returncode == 0
        all_ok = all_ok and ok
        commands.append(
            {
                "command": " ".join(cmd),
                "ok": ok,
                "returncode": proc.returncode,
                "stdout_tail": "\n".join((proc.stdout or "").splitlines()[-20:]),
                "stderr_tail": "\n".join((proc.stderr or "").splitlines()[-20:]),
            }
        )
    return {"ok": all_ok, "commands": commands, "tests": tests}


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
) -> dict[str, Any]:
    code_files = [
        root / "services/model-service/src/services/nfl_t5107u/eval_result_contract.py",
        root / "services/model-service/src/services/nfl_t5107u/verify_integrate.py",
        root / "scripts/nfl/run_nfl_t5151u_verify_integrate.py",
    ]
    ce_path = root / "services/model-service/src/services/nfl_t5107u/cohort_enforcement.py"
    if ce_path.is_file():
        code_files.append(ce_path)
    spec_files = [
        root / "ops/CURSOR_ADDENDUM_t5151u_NUMERICAL_INTEGRATION_v1.md",
    ]
    spec_files = [p for p in spec_files if p.is_file()]
    input_files = [
        root / REG496_PATH,
        root / ORIGINAL_502_PATH,
    ]
    input_files = [p for p in input_files if p.is_file()]
    failed = bool(errors) or not pins.get("ok") or not tests.get("ok")
    for body in profiles.values():
        if not body.get("ok"):
            failed = True
    status = "FAILED" if failed else "CHECKS_PASSED_AWAITING_ALEX_RO"
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
        "cos_order_b_sha8": COS_ORDER_B_SHA8,
        "cos_accept_scoped_sha8": COS_ACCEPT_SCOPED_SHA8,
        "package_a_tip": PACKAGE_A_TIP,
        "package_a_stamp": PACKAGE_A_STAMP,
        "r4_496_accepted_tip": R4_496_ACCEPTED_TIP,
        "alex_pass_ro": ALEX_PASS_RO,
        "tip_sha": git_tip(root),
        "command": (
            "python3 scripts/nfl/run_nfl_t5151u_verify_integrate.py"
        ),
        "receipt_path": f"{OUT_DIR.as_posix()}/{RECEIPT_NAME}",
        "profiles": {name: (profiles[name].get("profile") or name) for name in profiles},
        "hashes": {
            "code_sha256": sha256_paths(code_files),
            "spec_sha256": sha256_paths(spec_files) if spec_files else None,
            "input_sha256": sha256_paths(input_files) if input_files else None,
            "cohort_sha256": (pins.get("cohort_sha256") or None),
        },
        "pinned_artifacts": pins,
        "profile_results": profiles,
        "checks": list(pins.get("checks") or []),
        "errors": list(errors),
        "tests": tests,
        "interval_contract": dict(INTERVAL_CONTRACT),
        "evidence_limits": dict(LIMITATIONS),
        "limitations": dict(LIMITATIONS),
    }
    body = json.dumps(
        {k: v for k, v in receipt.items() if k != "hashes"},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    receipt["hashes"]["output_sha256"] = sha256_text(body)
    return receipt


def write_receipt(receipt: Mapping[str, Any], root: Path) -> Path:
    dest = root / OUT_DIR / RECEIPT_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return dest


def run_one_command(*, root: Path | None = None, hooks: CohortHooks | None = None) -> dict[str, Any]:
    """Complete offline command body. Not two disconnected helpers."""
    repo = _repo_root(root)
    errors: list[str] = []
    pins = verify_pinned_artifacts(repo)
    errors.extend(list(pins.get("errors") or []))
    ce = try_load_cohort_module()
    try:
        active_hooks = hooks or require_cohort_hooks(ce)
    except VerifyIntegrateRefuse as exc:
        errors.append(str(exc))
        active_hooks = None

    profiles: dict[str, Any] = {}
    spy = OutcomeReadSpy(lambda: {"SHOULD_NOT_LOAD": {"home_score": 99}})

    if (repo / REG496_PATH).is_file():
        recon = load_json(repo / REG496_PATH)
        recon_ids = [str(x) for x in recon.get("game_ids") or []]
        try:
            if active_hooks is None:
                numerical = validate_profile_output(PROFILE_FEATURE_RECON_REG496, recon)
                profiles[PROFILE_FEATURE_RECON_REG496] = {
                    "ok": True,
                    "profile": PROFILE_FEATURE_RECON_REG496,
                    "numerical_only": True,
                    "numerical": numerical,
                }
            else:
                profiles[PROFILE_FEATURE_RECON_REG496] = run_scoped_research_verify(
                    PROFILE_FEATURE_RECON_REG496,
                    recon,
                    recon_ids,
                    hooks=active_hooks,
                    outcome_loader=spy,
                    candidate_bytes_sha=sha256_file(repo / REG496_PATH),
                    expected_bytes_sha=REG496_SHA256,
                    root=repo,
                )
        except (VerifyIntegrateRefuse, EvalResultContractRefuse, Exception) as exc:
            errors.append(f"{PROFILE_FEATURE_RECON_REG496}: {exc}")
            profiles[PROFILE_FEATURE_RECON_REG496] = {"ok": False, "error": str(exc)}
            if spy.reads != 0:
                errors.append("FEATURE_RECON_REG496 refusal read target outcomes")

    if active_hooks is not None and ce is not None:
        try:
            if437 = ce.expected_profile_ids(PROFILE_DEV_IF437, repo)
            synthetic_if = build_synthetic_if437_result(if437[:2])
            profiles[PROFILE_DEV_IF437] = run_scoped_research_verify(
                PROFILE_DEV_IF437,
                synthetic_if,
                if437,
                hooks=active_hooks,
                outcome_loader=OutcomeReadSpy(),
                joined_ids=if437,
                root=repo,
            )
        except (VerifyIntegrateRefuse, EvalResultContractRefuse, Exception) as exc:
            errors.append(f"{PROFILE_DEV_IF437}: {exc}")
            profiles[PROFILE_DEV_IF437] = {"ok": False, "error": str(exc)}
        try:
            market72 = ce.expected_profile_ids(PROFILE_DEV_MARKET72, repo)
            synthetic_m = build_synthetic_market72_result(market72[:2])
            if synthetic_m["n_by_season"] == DEV_MARKET72_BY_SEASON:
                pass
            profiles[PROFILE_DEV_MARKET72] = run_scoped_research_verify(
                PROFILE_DEV_MARKET72,
                synthetic_m,
                market72,
                hooks=active_hooks,
                outcome_loader=OutcomeReadSpy(),
                joined_ids=market72,
                root=repo,
            )
        except (VerifyIntegrateRefuse, EvalResultContractRefuse, Exception) as exc:
            errors.append(f"{PROFILE_DEV_MARKET72}: {exc}")
            profiles[PROFILE_DEV_MARKET72] = {"ok": False, "error": str(exc)}
    else:
        try:
            synthetic_if = build_synthetic_if437_result()
            validate_profile_output(PROFILE_DEV_IF437, synthetic_if)
            profiles[PROFILE_DEV_IF437] = {
                "ok": True,
                "profile": PROFILE_DEV_IF437,
                "numerical_only": True,
                "n_by_season_expected": DEV_IF437_BY_SEASON,
            }
            synthetic_m = build_synthetic_market72_result()
            validate_profile_output(PROFILE_DEV_MARKET72, synthetic_m)
            profiles[PROFILE_DEV_MARKET72] = {
                "ok": True,
                "profile": PROFILE_DEV_MARKET72,
                "numerical_only": True,
                "n_by_season_expected": DEV_MARKET72_BY_SEASON,
            }
        except EvalResultContractRefuse as exc:
            errors.append(f"synthetic numerical: {exc}")

    tests = run_focused_tests(repo)
    if not tests["ok"]:
        errors.append("focused tests failed")
    if ce is not None:
        pins["cohort_sha256"] = ce.cohort_identity_sha256(
            ce.expected_profile_ids(PROFILE_FEATURE_RECON_REG496, repo)
        )
    receipt = build_receipt(
        root=repo, pins=pins, profiles=profiles, tests=tests, errors=errors
    )
    path = write_receipt(receipt, repo)
    receipt["receipt_written"] = str(path)
    if receipt["status"] != "CHECKS_PASSED_AWAITING_ALEX_RO":
        raise VerifyIntegrateRefuse(
            "nonzero failure prevented VERIFIED/final output: " + "; ".join(errors[:8])
        )
    return receipt
