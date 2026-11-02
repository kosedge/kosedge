"""t5155u RETURN-FIX R2 — frozen Phase-2 one-exec runner for DEV_R5_496.

Loads committed FORECASTS (sha 96d3aa6f). Never regenerates produce-μ.
Default / unbound --score refuse target labels (0 reads). Bound
``--score --cos-bind`` verifies code/input pins + exclusive claim, then
the real loader once. FOCUSED_TESTS / verify_integrate use a synthetic
loader only — real schedule_outcome_loader(ROOT) is blocked there.
Q2/candidate stay HOLD. CERT=0. Not EVAL. No Cos bind in this change.
"""

from __future__ import annotations

import csv
import json
import math
import os
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .cohort_enforcement import (
    FEATURE_RECON_REG496_ARTIFACT_SHA256,
    PROFILE_FEATURE_RECON_REG496,
    REG496_IDENTITY_SHA256,
    OutcomeReadSpy,
    check_cohort_before_feature_output_finalization,
    check_cohort_before_target_outcome_loading,
    expected_profile_ids,
)
from .evaluator import (
    BOOT_B,
    BOOT_SEED,
    MIN_N_REPORT,
    bootstrap_ci,
    mean_stat,
    paired_bias,
    paired_mae,
    paired_rmse,
    reporting_class,
    signed_abs_loss,
)
from .last_played_cohort import SCHEDULE_PATH, SCHEDULE_SHA256
from .market_arm_freeze import (
    INTERSECTION_BYTES_SHA256,
    INTERSECTION_IDENTITY_SHA256,
    INTERSECTION_N,
)
from .one_run import (
    OneRunRefuse,
    bind_one_run,
    claim_one_run,
    complete_one_run,
    fail_one_run,
    load_one_run,
    verify_one_run,
)
from .r5_496_freeze import PATH_ID, R3_STOP
from .recon_contract import _finite
from .recon_driver import sha256_file, sha256_text

TICKET = "t5155u"
SCHEMA = "nfl-t5155u-r5-phase2-one-exec-v1"
CERT_CANDIDATE = 0
OWNER_CLEAR_SHA8 = "659cd7d9"
OWNER_T5157U_SHA8 = "e6cc6927"
COS_ORDER_RETURN_FIX_SHA8 = "b51a9a10"
COS_ORDER_T5157U_SHA8 = "7015d5c8"
ALEX_RETURN_FIX_SHA8 = "9332de97"
ALEX_RETURN_T5157U_SHA8 = "42069ef6"
COS_ACCEPT_RETURN_FIX_SHA8 = "c5574733"
LINEAGE_TIP_255ADF78 = "255adf7802830bc25814a739d62f65f095216203"
FORECASTS_PATH = "data/ops/nfl-t5155u-r5-496-freeze/FORECASTS_DEV_R5_496.json"
FORECASTS_SHA256 = "96d3aa6f85e7896df2385df8d025ea0bd4d15d5e2a82edc3f5c9184cd35af407"
Q2_HISTORY_SHA256 = "07bbc340223976ff4d832bb02bce9cae40b2febe3b226f619913241300ec6966"
FREEZE_MANIFEST_SHA256 = "36f051c4f0ecb96abac973f3e43bfc157a1f632e65d5d8b1de7991495eff7f38"
COMPLETED_FORECASTS_PATH = "data/ops/nfl-t5157u-r5-history-id/FORECASTS_DEV_R5_496_Q2_COMPLETED.json"
COMPLETED_FORECASTS_SHA256 = (
    "f4b970f0138a5e2c5f1496711220282650ce4d79f9ae62aeecc6473cae535171"
)
Q2_COMPLETED_PATH = "data/ops/nfl-t5157u-r5-history-id/Q2_COMPLETED_FREEZE.json"
Q2_COMPLETED_SHA256 = "eeb6fff73383289c1e69a1a1b30f6df5eed38c7201c58ca9de16feaa8f06cc04"
CANDIDATE_COMPLETED_PATH = "data/ops/nfl-t5157u-r5-history-id/CANDIDATE_COMPLETED_FREEZE.json"
CANDIDATE_COMPLETED_SHA256 = (
    "2f9a73e68d66878b984d5ae9e2e6fc01cfe16e45b0da4ad5389f90aabe9a87c7"
)
IDENTITY_FREEZE_PATH = "data/ops/nfl-t5157u-r5-history-id/IDENTITY_FREEZE.json"
IDENTITY_FREEZE_SHA256 = "561ae3e1f0a0b99201f3b4a0a00d5da13e75ec7924ad9b6b67218c802aef8b3f"
REG_2013_2019_IDENTITY_SHA256 = (
    "9aad6f473fe6d32bf33466a47d80968dfdf8c8bd8ab8db0bca35e0972d1043a0"
)
POST_2013_2019_IDENTITY_SHA256 = (
    "e43390f94e5b65204014ea588bbc9b6b4b880b6e28227a58e7cbc30ee765444f"
)
HISTORY_CHOICE_SHA256 = "679d24283869ccf6b0a2b434efa200e92fd3e2c12a98c446da7d8f968da913b7"
WORKER_A_HISTORY_TIP = "f7715dce8ffaaee11fb5236c1d7873aed27cd7c1"
WORKER_A_HISTORY_STAMP = "8a7895b9982c155e04298a34fe66e4e59da19fad"
SPLIT_PATH = "data/ops/nfl-t5155u-r5-496-freeze/SPLIT_SCAFFOLDING.json"
MARKET_FREEZE_PATH = "data/ops/nfl-t5155u-r5-phase1/MARKET_ARM_FREEZE.json"
OUT_DIR = Path("data/ops/nfl-t5155u-r5-phase2")
RECEIPT_NAME = "RECEIPT.json"
COMMAND = "PYTHONPATH=services/model-service python scripts/nfl/run_nfl_t5155u_r5_phase2_one_exec.py"
RUNNER_CODE_RELPATHS = (
    "services/model-service/src/services/nfl_t5107u/r5_phase2_one_exec.py",
    "scripts/nfl/run_nfl_t5155u_r5_phase2_one_exec.py",
    "services/model-service/src/services/nfl_t5107u/one_run.py",
    "services/model-service/src/services/nfl_t5107u/evaluator.py",
)
SKIP_NESTED_TESTS_ENV = "T5151U_SKIP_NESTED_TESTS"
ALLOW_REAL_LOADER_ENV = "T5157U_ALLOW_REAL_LOADER"


class Phase2OneExecRefuse(ValueError):
    """Fail-closed Phase-2 one-exec. Not Cos bind. Not EVAL."""


def _repo_root(root: Path | None) -> Path:
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[5]


def _real_loader_blocked() -> bool:
    skip = os.environ.get(SKIP_NESTED_TESTS_ENV) == "1"
    allow = os.environ.get(ALLOW_REAL_LOADER_ENV) == "1"
    return skip and not allow


def runner_code_hashes(root: Path | None = None) -> dict[str, str]:
    repo = _repo_root(root)
    return {rel: sha256_file(repo / rel) for rel in RUNNER_CODE_RELPATHS}


def runner_code_sha256(root: Path | None = None) -> str:
    return sha256_text(json.dumps(runner_code_hashes(root), sort_keys=True, separators=(",", ":")))


def runner_input_pin_bundle() -> dict[str, str]:
    return {
        "forecasts_sha256": FORECASTS_SHA256,
        "q2_history_sha256": Q2_HISTORY_SHA256,
        "freeze_manifest_sha256": FREEZE_MANIFEST_SHA256,
        "completed_forecasts_sha256": COMPLETED_FORECASTS_SHA256,
        "q2_completed_sha256": Q2_COMPLETED_SHA256,
        "candidate_completed_sha256": CANDIDATE_COMPLETED_SHA256,
        "identity_freeze_sha256": IDENTITY_FREEZE_SHA256,
        "reg_2013_2019_identity_sha256": REG_2013_2019_IDENTITY_SHA256,
        "post_2013_2019_identity_sha256": POST_2013_2019_IDENTITY_SHA256,
        "market_bytes_sha256": INTERSECTION_BYTES_SHA256,
        "market_identity_sha256": INTERSECTION_IDENTITY_SHA256,
        "schedule_sha256": SCHEDULE_SHA256,
        "feature_json_sha256": FEATURE_RECON_REG496_ARTIFACT_SHA256,
        "identity_sha256": REG496_IDENTITY_SHA256,
    }


def runner_input_sha256() -> str:
    return sha256_text(json.dumps(runner_input_pin_bundle(), sort_keys=True, separators=(",", ":")))


def runner_spec_sha256() -> str:
    return sha256_text(
        json.dumps(
            {
                "schema_version": SCHEMA,
                "ticket": TICKET,
                "path_id": PATH_ID,
                "forecasts_sha256": FORECASTS_SHA256,
                "q2_history_sha256": Q2_HISTORY_SHA256,
                "freeze_manifest_sha256": FREEZE_MANIFEST_SHA256,
                "q2_completed_sha256": Q2_COMPLETED_SHA256,
                "candidate_completed_sha256": CANDIDATE_COMPLETED_SHA256,
                "identity_freeze_sha256": IDENTITY_FREEZE_SHA256,
                "market_bytes_sha256": INTERSECTION_BYTES_SHA256,
                "identity_sha256": REG496_IDENTITY_SHA256,
                "q2": "COMPLETED",
                "candidate": "COMPLETED",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def bind_phase2_one_exec_fixture(
    *,
    path: Path,
    alex_go_id: str = "ALEX_RETURN_42069EF6",
    root: Path | None = None,
) -> dict[str, Any]:
    """Test-only matching bind. Not a live Cos bind."""
    repo = _repo_root(root)
    return bind_one_run(
        effective_spec_sha256=runner_spec_sha256(),
        code_sha256=runner_code_sha256(repo),
        input_sha256=runner_input_sha256(),
        forecast_sha256=FORECASTS_SHA256,
        cohort_sha256=REG496_IDENTITY_SHA256,
        alex_go_id=alex_go_id,
        path=path,
    )


def _verify_and_claim_cos_bind(
    repo: Path,
    bind_path: Path,
    *,
    code_sha: str,
    input_sha: str,
    spec_sha: str,
) -> dict[str, Any]:
    record = load_one_run(bind_path)
    if not record:
        raise Phase2OneExecRefuse("cos-bind file missing one-run record")
    try:
        verified = verify_one_run(
            record,
            forecast_sha256=FORECASTS_SHA256,
            cohort_sha256=REG496_IDENTITY_SHA256,
            exec_bind=str(record.get("bind_id") or ""),
            alex_go_id=str(record.get("alex_go_id") or ""),
            live_effective_spec_sha256=spec_sha,
            live_code_sha256=code_sha,
            live_input_sha256=input_sha,
            path=bind_path,
        )
        return claim_one_run(bind_path, verified["bind_id"])
    except OneRunRefuse as exc:
        raise Phase2OneExecRefuse(f"cos-bind refused: {exc}") from exc


def load_committed_forecasts(root: Path) -> dict[str, Any]:
    path = Path(root) / FORECASTS_PATH
    digest = sha256_file(path)
    if digest != FORECASTS_SHA256:
        raise Phase2OneExecRefuse(
            f"committed FORECASTS sha {digest} != pin 96d3aa6f — never regenerate"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if int(payload.get("n_if_finite") or 0) != 496:
        raise Phase2OneExecRefuse("forecasts n_if_finite != 496")
    if payload.get("q2_hold") is not True or int(payload.get("n_q2_hold") or 0) != 496:
        raise Phase2OneExecRefuse("forecasts Q2 HOLD drifted")
    if int(payload.get("n_candidate_finite") or 0) != 0:
        raise Phase2OneExecRefuse("forecasts invented candidate — refuse")
    return payload


def load_completed_forecasts(root: Path) -> dict[str, Any]:
    """Completed Q2/candidate overlay. IF bytes copied from pin 96d3aa6f."""
    path = Path(root) / COMPLETED_FORECASTS_PATH
    digest = sha256_file(path)
    if digest != COMPLETED_FORECASTS_SHA256:
        raise Phase2OneExecRefuse(
            f"completed FORECASTS sha {digest} != pin f4b970f0 — do not regenerate"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("if_forecasts_sha256") != FORECASTS_SHA256:
        raise Phase2OneExecRefuse("completed forecasts drifted from IF496 96d3aa6f")
    if payload.get("if_regenerated") is True:
        raise Phase2OneExecRefuse("completed forecasts regenerated IF — refuse")
    if int(payload.get("n_if_finite") or 0) != 496:
        raise Phase2OneExecRefuse("completed n_if_finite != 496")
    if int(payload.get("n_q2_finite") or 0) != 496 or int(payload.get("n_q2_hold") or 0) != 0:
        raise Phase2OneExecRefuse("completed Q2 not 496 finite / 0 HOLD")
    if int(payload.get("n_candidate_finite") or 0) != 496:
        raise Phase2OneExecRefuse("completed candidate n != 496")
    if payload.get("initial_prior_2013") is not None:
        raise Phase2OneExecRefuse("completed initial_prior_2013 must be None")
    if payload.get("candidate") != "0.5*IF+0.5*Q2":
        raise Phase2OneExecRefuse("completed candidate formula drifted")
    hold = load_committed_forecasts(root)
    hold_if = {str(row["game_id"]): row["m_if"] for row in hold["forecasts"]}
    for row in payload["forecasts"]:
        gid = str(row["game_id"])
        if row.get("m_if") != hold_if.get(gid):
            raise Phase2OneExecRefuse(f"completed IF drifted vs 96d3aa6f for {gid}")
        if row.get("m_q2") is None or not _finite(row.get("m_q2")):
            raise Phase2OneExecRefuse(f"completed Q2 missing for {gid}")
        if row.get("m_candidate") is None or not _finite(row.get("m_candidate")):
            raise Phase2OneExecRefuse(f"completed candidate missing for {gid}")
    for rel, expected in (
        (Q2_COMPLETED_PATH, Q2_COMPLETED_SHA256),
        (CANDIDATE_COMPLETED_PATH, CANDIDATE_COMPLETED_SHA256),
        (IDENTITY_FREEZE_PATH, IDENTITY_FREEZE_SHA256),
    ):
        digest = sha256_file(Path(root) / rel)
        if digest != expected:
            raise Phase2OneExecRefuse(f"{rel} sha {digest} != pin {expected[:8]}")
    identity = json.loads((Path(root) / IDENTITY_FREEZE_PATH).read_text(encoding="utf-8"))
    if identity.get("identity_sha256") != REG_2013_2019_IDENTITY_SHA256:
        raise Phase2OneExecRefuse("REG 2013–19 identity drifted from 9aad6f47")
    if identity.get("post_identity_sha256") != POST_2013_2019_IDENTITY_SHA256:
        raise Phase2OneExecRefuse("POST 2013–19 identity drifted from e43390f9")
    return payload


def load_splits(root: Path) -> dict[str, Any]:
    return json.loads((Path(root) / SPLIT_PATH).read_text(encoding="utf-8"))


def load_market_points(root: Path) -> dict[str, Any]:
    payload = json.loads((Path(root) / MARKET_FREEZE_PATH).read_text(encoding="utf-8"))
    inter = payload["intersection"]
    if int(inter["n"]) != INTERSECTION_N:
        raise Phase2OneExecRefuse(f"market n={inter['n']} != 96")
    if inter["bytes_sha256"] != INTERSECTION_BYTES_SHA256:
        raise Phase2OneExecRefuse("market intersection bytes drifted from 072e99e0")
    if inter["identity_sha256"] != INTERSECTION_IDENTITY_SHA256:
        raise Phase2OneExecRefuse("market intersection identity drifted from 558fbfe5")
    return inter


def synthetic_outcome_loader(
    forecasts: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    *,
    root: Path | None = None,
) -> Callable[[], dict[str, dict[str, Any]]]:
    """Deterministic fake scores for REG496 IDs. Never opens schedule_results."""

    if forecasts is None:
        payload = load_committed_forecasts(_repo_root(root))
        rows: Sequence[Mapping[str, Any]] = payload["forecasts"]
    elif isinstance(forecasts, Mapping) and "forecasts" in forecasts:
        rows = forecasts["forecasts"]  # type: ignore[assignment]
    else:
        rows = forecasts  # type: ignore[assignment]

    def _load() -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for row in rows:
            gid = str(row["game_id"])
            seed = sum(ord(ch) for ch in gid)
            home_score = float(10 + (seed % 21))
            away_score = float(10 + ((seed * 7) % 21))
            out[gid] = {
                "game_id": gid,
                "season": int(row["season"]),
                "week": int(row["week"]),
                "home": str(row.get("home") or gid.split("_")[3]),
                "away": str(row.get("away") or gid.split("_")[2]),
                "home_score": home_score,
                "away_score": away_score,
                "source": "synthetic",
            }
        return out

    return _load


def schedule_outcome_loader(root: Path) -> Callable[[], dict[str, dict[str, Any]]]:
    """Repo-relative schedule scores for 2020–21 REG496. Bound command only.

    Refuses inside FOCUSED_TESTS / verify_integrate (T5151U_SKIP_NESTED_TESTS=1)
    unless T5157U_ALLOW_REAL_LOADER=1 after a verified Cos bind.
    """
    if _real_loader_blocked():
        raise Phase2OneExecRefuse(
            "real schedule_outcome_loader(ROOT) refused inside FOCUSED_TESTS / verify_integrate"
        )

    def _load() -> dict[str, dict[str, Any]]:
        if _real_loader_blocked():
            raise Phase2OneExecRefuse(
                "real schedule_outcome_loader(ROOT) refused inside FOCUSED_TESTS / verify_integrate"
            )
        path = Path(root) / SCHEDULE_PATH
        if sha256_file(path) != SCHEDULE_SHA256:
            raise Phase2OneExecRefuse("schedule pin drifted")
        out: dict[str, dict[str, Any]] = {}
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                gid = str(row["game_id"])
                if str(row.get("season_type") or "").upper() != "REG":
                    continue
                season = int(row["season"])
                if season not in (2020, 2021):
                    continue
                hs, aws = row.get("home_score"), row.get("away_score")
                if hs in (None, "") or aws in (None, ""):
                    continue
                out[gid] = {
                    "game_id": gid,
                    "season": season,
                    "week": int(row["week"]),
                    "home": row["home"],
                    "away": row["away"],
                    "home_score": float(hs),
                    "away_score": float(aws),
                }
        return out

    return _load


def _arm_metrics_for_ids(
    forecasts: Sequence[Mapping[str, Any]],
    outcomes: Mapping[str, Mapping[str, Any]],
    ids: Sequence[str],
    *,
    label: str,
) -> dict[str, Any]:
    by = {str(row["game_id"]): row for row in forecasts}
    err_if: list[float] = []
    err_q2: list[float] = []
    err_c: list[float] = []
    n_by: Counter[str] = Counter()
    for gid in ids:
        row = by.get(gid)
        out = outcomes.get(gid)
        if row is None or out is None:
            raise Phase2OneExecRefuse(f"{label} missing forecast or outcome for {gid}")
        if row.get("q2_status") == "HOLD" or row.get("m_q2") is None:
            raise Phase2OneExecRefuse(f"{label} Q2 not completed for {gid}")
        if row.get("m_candidate") is None:
            raise Phase2OneExecRefuse(f"{label} candidate not completed for {gid}")
        m_if, m_q2, m_c = row.get("m_if"), row.get("m_q2"), row.get("m_candidate")
        if m_if is None or not _finite(m_if):
            raise Phase2OneExecRefuse(f"{label} IF not finite for {gid}")
        if not _finite(m_q2) or not _finite(m_c):
            raise Phase2OneExecRefuse(f"{label} Q2/candidate not finite for {gid}")
        actual = float(out["home_score"]) - float(out["away_score"])
        if not math.isfinite(actual):
            raise Phase2OneExecRefuse(f"{label} actual not finite for {gid}")
        err_if.append(float(m_if) - actual)
        err_q2.append(float(m_q2) - actual)
        err_c.append(float(m_c) - actual)
        n_by[str(row["season"])] += 1
    if len(err_if) != len(ids):
        raise Phase2OneExecRefuse(f"{label} n={len(err_if)} != {len(ids)}")
    return {
        "label": label,
        "n": len(err_if),
        "n_by_season": dict(sorted(n_by.items())),
        "mae_if": paired_mae(err_if),
        "rmse_if": paired_rmse(err_if),
        "bias_if": paired_bias(err_if),
        "mae_q2": paired_mae(err_q2),
        "rmse_q2": paired_rmse(err_q2),
        "bias_q2": paired_bias(err_q2),
        "mae_candidate": paired_mae(err_c),
        "rmse_candidate": paired_rmse(err_c),
        "bias_candidate": paired_bias(err_c),
        "q2": "COMPLETED",
        "candidate": "COMPLETED",
        "invented_q2": False,
    }


def _market_if_paired(
    forecasts: Sequence[Mapping[str, Any]],
    outcomes: Mapping[str, Mapping[str, Any]],
    market: Mapping[str, Any],
) -> dict[str, Any]:
    by = {str(row["game_id"]): row for row in forecasts}
    points = {str(row["game_id"]): row for row in market["games"]}
    diffs: list[float] = []
    diffs_c: list[float] = []
    clusters: list[str] = []
    ids = list(market["game_ids"])
    if len(ids) != INTERSECTION_N:
        raise Phase2OneExecRefuse(f"market ids n={len(ids)} != 96")
    for gid in ids:
        row = by[gid]
        out = outcomes[gid]
        point = points[gid]
        actual = float(out["home_score"]) - float(out["away_score"])
        m_if = float(row["m_if"])
        m_c = float(row["m_candidate"])
        m_mkt = float(point["home_margin"])
        diffs.append(signed_abs_loss(m_if, actual) - signed_abs_loss(m_mkt, actual))
        diffs_c.append(signed_abs_loss(m_c, actual) - signed_abs_loss(m_mkt, actual))
        clusters.append(f"{int(row['season'])}-{int(row['week']):02d}")
    game = bootstrap_ci(diffs, stat=mean_stat)
    week = bootstrap_ci(diffs, stat=mean_stat, clusters=clusters)
    game_c = bootstrap_ci(diffs_c, stat=mean_stat)
    week_c = bootstrap_ci(diffs_c, stat=mean_stat, clusters=clusters)
    n_clusters = len(set(clusters))
    klass = reporting_class(len(diffs))
    return {
        "n": len(diffs),
        "n_by_season": dict(sorted(Counter(gid.split("_", 1)[0] for gid in ids).items())),
        "bytes_sha256": INTERSECTION_BYTES_SHA256,
        "identity_sha256": INTERSECTION_IDENTITY_SHA256,
        "mean_signed_diff_if_vs_market": mean_stat(diffs),
        "mean_signed_diff_candidate_vs_market": mean_stat(diffs_c),
        "bootstrap_game": game,
        "bootstrap_season_week": week,
        "bootstrap_game_candidate": game_c,
        "bootstrap_season_week_candidate": week_c,
        "method": "MEAN signed paired absolute-loss difference L_if−L_market",
        "B": BOOT_B,
        "seed": BOOT_SEED,
        "level": 0.95,
        "n_clusters": n_clusters,
        "sparse_limits": {
            "n": len(diffs),
            "n_clusters": n_clusters,
            "min_n_report": MIN_N_REPORT,
            "n_lt_100": len(diffs) < MIN_N_REPORT,
            "note": "n=96 < 100 — DESCRIPTIVE_ONLY; cluster bootstrap can be sparse",
        },
        "reporting_class": klass,
        "n100_guidance": "n<100 DESCRIPTIVE_ONLY — not GREEN",
        "nfl_green": False,
        "q2": "COMPLETED",
        "candidate": "COMPLETED",
        "eval": None,
    }


def _assert_finite_metrics(body: Mapping[str, Any]) -> None:
    for key in (
        "mae_if",
        "rmse_if",
        "bias_if",
        "mae_q2",
        "rmse_q2",
        "bias_q2",
        "mae_candidate",
        "rmse_candidate",
        "bias_candidate",
    ):
        if not _finite(body[key]):
            raise Phase2OneExecRefuse(f"{body.get('label')} {key} not finite")


def run_phase2_one_exec(
    *,
    root: Path | None = None,
    outcome_loader: OutcomeReadSpy | Callable[[], Mapping[str, Mapping[str, Any]]] | None = None,
    invoke_outcome_after_gates: bool = False,
    write: bool = False,
    dest: Path | None = None,
    cos_bind_path: Path | None = None,
    score_flag: bool = False,
) -> dict[str, Any]:
    """Guarded Phase-2 runner. Default: refuse labels. Never regenerate forecasts."""
    repo = _repo_root(root)
    code_hashes = runner_code_hashes(repo)
    code_sha = runner_code_sha256(repo)
    input_sha = runner_input_sha256()
    spec_sha = runner_spec_sha256()
    bind_record: dict[str, Any] | None = None
    bound = False
    allow_prior: str | None = None
    allow_mutated = False

    if score_flag and cos_bind_path is None:
        raise Phase2OneExecRefuse("unbound --score refused — 0 reads")
    if cos_bind_path is not None:
        score_flag = True
        bind_record = _verify_and_claim_cos_bind(
            repo,
            Path(cos_bind_path),
            code_sha=code_sha,
            input_sha=input_sha,
            spec_sha=spec_sha,
        )
        bound = True
        invoke_outcome_after_gates = True
        if outcome_loader is None:
            allow_prior = os.environ.get(ALLOW_REAL_LOADER_ENV)
            os.environ[ALLOW_REAL_LOADER_ENV] = "1"
            allow_mutated = True
            try:
                outcome_loader = OutcomeReadSpy(schedule_outcome_loader(repo))
            except Exception as exc:
                if allow_prior is None:
                    os.environ.pop(ALLOW_REAL_LOADER_ENV, None)
                else:
                    os.environ[ALLOW_REAL_LOADER_ENV] = allow_prior
                fail_one_run(Path(cos_bind_path), bind_record["bind_id"], str(exc))
                raise

    def _restore_allow() -> None:
        nonlocal allow_mutated
        if not allow_mutated:
            return
        if allow_prior is None:
            os.environ.pop(ALLOW_REAL_LOADER_ENV, None)
        else:
            os.environ[ALLOW_REAL_LOADER_ENV] = allow_prior
        allow_mutated = False

    forecasts = load_committed_forecasts(repo)
    completed = load_completed_forecasts(repo)
    splits = load_splits(repo)
    market = load_market_points(repo)
    ids = expected_profile_ids(PROFILE_FEATURE_RECON_REG496, repo)
    if ids != list(forecasts["game_ids"]):
        # Artifact order may differ from schedule order; sets must match.
        if set(ids) != set(forecasts["game_ids"]):
            raise Phase2OneExecRefuse("forecast IDs != FEATURE_RECON_REG496")
    spy = outcome_loader if outcome_loader is not None else OutcomeReadSpy(
        lambda: {"SHOULD_NOT_LOAD": {"home_score": 99}}
    )
    if getattr(spy, "reads", 0) not in (None, 0):
        raise Phase2OneExecRefuse("outcome loader already read — refuse (join-before-gate)")
    loaded: Mapping[str, Mapping[str, Any]] | None = None
    try:
        check_cohort_before_feature_output_finalization(
            PROFILE_FEATURE_RECON_REG496,
            ids,
            candidate_bytes_sha=FEATURE_RECON_REG496_ARTIFACT_SHA256,
            expected_bytes_sha=FEATURE_RECON_REG496_ARTIFACT_SHA256,
            root=repo,
        )
        check_cohort_before_target_outcome_loading(
            PROFILE_FEATURE_RECON_REG496,
            ids,
            frozen_bytes_sha=FEATURE_RECON_REG496_ARTIFACT_SHA256,
            expected_bytes_sha=FEATURE_RECON_REG496_ARTIFACT_SHA256,
            coverage_blocked=not invoke_outcome_after_gates,
            outcome_loader=spy,
            root=repo,
        )
        if getattr(spy, "reads", 0) != 0:
            raise Phase2OneExecRefuse("cohort gate invoked target-outcome loader")
        if invoke_outcome_after_gates:
            loaded = spy()
    except Phase2OneExecRefuse:
        _restore_allow()
        if bound and bind_record is not None:
            fail_one_run(Path(cos_bind_path), bind_record["bind_id"], "phase2 refuse after claim")
        raise
    except Exception as exc:
        _restore_allow()
        if getattr(spy, "reads", 0) != 0:
            if bound and bind_record is not None:
                fail_one_run(Path(cos_bind_path), bind_record["bind_id"], str(exc))
            raise Phase2OneExecRefuse("target scoring outcomes were read on refusal") from exc
        if invoke_outcome_after_gates:
            if bound and bind_record is not None:
                fail_one_run(Path(cos_bind_path), bind_record["bind_id"], str(exc))
            raise
        receipt = _receipt(
            repo,
            forecasts=forecasts,
            completed=completed,
            market=market,
            splits=splits,
            scored=None,
            spy_reads=0,
            invoked=False,
            bound=False,
            score_flag=score_flag,
            code_hashes=code_hashes,
            code_sha=code_sha,
            input_sha=input_sha,
            spec_sha=spec_sha,
        )
        receipt["scoring_refuse"] = {"refused": True, "reason": str(exc), "outcome_loader_reads": 0}
        if write:
            _write_receipt(repo, receipt, dest=dest)
        return receipt
    _restore_allow()
    if not invoke_outcome_after_gates:
        if getattr(spy, "reads", 0) != 0:
            raise Phase2OneExecRefuse("target scoring outcomes were read before Cos bind")
        receipt = _receipt(
            repo,
            forecasts=forecasts,
            completed=completed,
            market=market,
            splits=splits,
            scored=None,
            spy_reads=0,
            invoked=False,
            bound=False,
            score_flag=score_flag,
            code_hashes=code_hashes,
            code_sha=code_sha,
            input_sha=input_sha,
            spec_sha=spec_sha,
        )
        if write:
            _write_receipt(repo, receipt, dest=dest)
        return receipt

    try:
        if getattr(spy, "reads", 0) != 1:
            raise Phase2OneExecRefuse("expected one post-gate outcome read")
        outcomes = dict(loaded)
        if not outcomes:
            raise Phase2OneExecRefuse("positive path loaded zero target labels")
        missing = [gid for gid in forecasts["game_ids"] if gid not in outcomes]
        if missing:
            raise Phase2OneExecRefuse(f"outcomes missing {len(missing)} REG496 ids")
        if_metrics = {
            "full496": _arm_metrics_for_ids(
                completed["forecasts"], outcomes, splits["full496"]["game_ids"], label="full496"
            ),
            "old437": _arm_metrics_for_ids(
                completed["forecasts"], outcomes, splits["old437"]["game_ids"], label="old437"
            ),
            "new59": _arm_metrics_for_ids(
                completed["forecasts"], outcomes, splits["new59"]["game_ids"], label="new59"
            ),
        }
        for body in if_metrics.values():
            _assert_finite_metrics(body)
        market_metrics = _market_if_paired(completed["forecasts"], outcomes, market)
        scored = {
            "if_q2_candidate": if_metrics,
            "if_only": if_metrics,
            "market96": market_metrics,
            "q2": "COMPLETED",
            "candidate": "COMPLETED",
            "r3_stop": R3_STOP,
            "forecasts_sha256": FORECASTS_SHA256,
            "completed_forecasts_sha256": COMPLETED_FORECASTS_SHA256,
            "q2_completed_sha256": Q2_COMPLETED_SHA256,
            "candidate_completed_sha256": CANDIDATE_COMPLETED_SHA256,
            "identity_freeze_sha256": IDENTITY_FREEZE_SHA256,
            "identity_sha256": REG496_IDENTITY_SHA256,
            "feature_json_sha256": FEATURE_RECON_REG496_ARTIFACT_SHA256,
            "regenerated_forecasts": False,
            "real_eval_executed": False,
            "nfl_green": False,
            "cert_candidate": CERT_CANDIDATE,
            "eval": None,
        }
        if bound and bind_record is not None:
            bind_record = complete_one_run(
                Path(cos_bind_path),
                bind_record["bind_id"],
                result={"n": 496, "market_n": INTERSECTION_N, "q2": "HOLD"},
            )
        receipt = _receipt(
            repo,
            forecasts=forecasts,
            completed=completed,
            market=market,
            splits=splits,
            scored=scored,
            spy_reads=1,
            invoked=True,
            bound=bound,
            score_flag=score_flag,
            code_hashes=code_hashes,
            code_sha=code_sha,
            input_sha=input_sha,
            spec_sha=spec_sha,
            bind_record=bind_record,
        )
        if write:
            _write_receipt(repo, receipt, dest=dest)
        return receipt
    except Exception as exc:
        if bound and bind_record is not None:
            fail_one_run(Path(cos_bind_path), bind_record["bind_id"], str(exc))
        raise


def _receipt(
    root: Path,
    *,
    forecasts: Mapping[str, Any],
    completed: Mapping[str, Any] | None = None,
    market: Mapping[str, Any],
    splits: Mapping[str, Any],
    scored: Mapping[str, Any] | None,
    spy_reads: int,
    invoked: bool,
    bound: bool = False,
    score_flag: bool = False,
    code_hashes: Mapping[str, str] | None = None,
    code_sha: str | None = None,
    input_sha: str | None = None,
    spec_sha: str | None = None,
    bind_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if bound and invoked:
        status = "PHASE2_ONE_EXEC_BOUND_SCORED"
        stop = "STOP_BOUND_ONE_EXEC_NOT_EVAL"
        scoring = "phase2_one_exec_bound"
    elif invoked:
        status = "PHASE2_ONE_EXEC_TEST_SCORED"
        stop = "STOP_AWAITING_ALEX_COMPLETED_CANDIDATE_PREFLIGHT"
        scoring = "phase2_one_exec_test"
    else:
        status = "CHECKS_PASSED_AWAITING_ALEX_COMPLETED_CANDIDATE_PREFLIGHT"
        stop = "STOP_AWAITING_ALEX_COMPLETED_CANDIDATE_PREFLIGHT"
        scoring = None
    hashes = dict(code_hashes or runner_code_hashes(root))
    receipt = {
        "schema_version": SCHEMA,
        "ticket": TICKET,
        "path_id": PATH_ID,
        "cert_candidate": CERT_CANDIDATE,
        "draft": True,
        "verified": False,
        "status": status,
        "stop": stop,
        "self_accept": False,
        "nfl_green": False,
        "real_eval_executed": False,
        "cos_bind": bool(bound),
        "score_flag": bool(score_flag),
        "owner_clear_sha8": OWNER_CLEAR_SHA8,
        "owner_t5157u_sha8": OWNER_T5157U_SHA8,
        "cos_order_return_fix_sha8": COS_ORDER_RETURN_FIX_SHA8,
        "cos_order_t5157u_sha8": COS_ORDER_T5157U_SHA8,
        "alex_return_fix_sha8": ALEX_RETURN_FIX_SHA8,
        "alex_return_t5157u_sha8": ALEX_RETURN_T5157U_SHA8,
        "cos_accept_return_fix_sha8": COS_ACCEPT_RETURN_FIX_SHA8,
        "lineage_tip_255adf78": LINEAGE_TIP_255ADF78,
        "command": COMMAND,
        "forecasts_path": FORECASTS_PATH,
        "forecasts_sha256": FORECASTS_SHA256,
        "completed_forecasts_path": COMPLETED_FORECASTS_PATH,
        "completed_forecasts_sha256": COMPLETED_FORECASTS_SHA256,
        "q2_history_sha256": Q2_HISTORY_SHA256,
        "freeze_manifest_sha256": FREEZE_MANIFEST_SHA256,
        "q2_completed_sha256": Q2_COMPLETED_SHA256,
        "candidate_completed_sha256": CANDIDATE_COMPLETED_SHA256,
        "identity_freeze_sha256": IDENTITY_FREEZE_SHA256,
        "reg_2013_2019_identity_sha256": REG_2013_2019_IDENTITY_SHA256,
        "post_2013_2019_identity_sha256": POST_2013_2019_IDENTITY_SHA256,
        "history_choice_sha256": HISTORY_CHOICE_SHA256,
        "worker_a_history_tip": WORKER_A_HISTORY_TIP,
        "worker_a_history_stamp": WORKER_A_HISTORY_STAMP,
        "regenerated_forecasts": False,
        "identity_sha256": REG496_IDENTITY_SHA256,
        "feature_json_sha256": FEATURE_RECON_REG496_ARTIFACT_SHA256,
        "n_if_finite": forecasts["n_if_finite"],
        "n_q2_hold": 0 if completed else forecasts["n_q2_hold"],
        "n_q2_finite": (completed or {}).get("n_q2_finite") or 0,
        "n_candidate_finite": (completed or {}).get("n_candidate_finite") or 0,
        "q2": "COMPLETED",
        "candidate": "COMPLETED",
        "initial_prior_2013": None,
        "end_season_carry": 0.5,
        "r3_stop": R3_STOP,
        "market_n": market["n"],
        "market_bytes_sha256": market["bytes_sha256"],
        "market_identity_sha256": market["identity_sha256"],
        "splits": {
            "full496": splits["full496"]["n"],
            "old437": splits["old437"]["n"],
            "new59": splits["new59"]["n"],
        },
        "outcome_loader_reads": spy_reads,
        "outcome_loader_invoked_after_gates": invoked,
        "runner_code_hashes": hashes,
        "runner_code_sha256": code_sha or runner_code_sha256(root),
        "runner_input_sha256": input_sha or runner_input_sha256(),
        "runner_spec_sha256": spec_sha or runner_spec_sha256(),
        "one_run_bind_id": (bind_record or {}).get("bind_id") if bound else None,
        "one_run_status": (bind_record or {}).get("status") if bound else None,
        "scored": scored,
        "eval": None,
        "scoring": scoring,
    }
    canonical = {
        k: v
        for k, v in receipt.items()
        if k not in {"hashes", "runtime", "tip_sha", "interpreter", "side_metadata"}
    }
    receipt["hashes"] = {
        "output_sha256": sha256_text(
            json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
        ),
        "forecasts_sha256": FORECASTS_SHA256,
        "market_bytes_sha256": INTERSECTION_BYTES_SHA256,
        "runner_code_sha256": receipt["runner_code_sha256"],
        "runner_input_sha256": receipt["runner_input_sha256"],
        "q2_history_sha256": Q2_HISTORY_SHA256,
        "freeze_manifest_sha256": FREEZE_MANIFEST_SHA256,
        "q2_completed_sha256": Q2_COMPLETED_SHA256,
        "candidate_completed_sha256": CANDIDATE_COMPLETED_SHA256,
        "identity_freeze_sha256": IDENTITY_FREEZE_SHA256,
    }
    receipt["runtime"] = {"interpreter": "python3"}
    receipt["side_metadata"] = {"pytest_elapsed_semantic": False}
    return receipt


def _write_receipt(root: Path, receipt: Mapping[str, Any], *, dest: Path | None) -> Path:
    out = Path(dest) if dest is not None else Path(root) / OUT_DIR / RECEIPT_NAME
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return out
