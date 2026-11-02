"""t5155u RETURN-FIX — frozen Phase-2 one-exec runner for DEV_R5_496.

Loads committed FORECASTS (sha 96d3aa6f). Never regenerates produce-μ.
Default command refuses target labels (Alex re-PREFLIGHT). Tests may invoke
the loader once after gates. Q2/candidate stay HOLD. CERT=0. Not EVAL.
"""

from __future__ import annotations

import csv
import json
import math
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
from .r5_496_freeze import PATH_ID, R3_STOP
from .recon_contract import _finite
from .recon_driver import sha256_file, sha256_text

TICKET = "t5155u"
SCHEMA = "nfl-t5155u-r5-phase2-one-exec-v1"
CERT_CANDIDATE = 0
OWNER_CLEAR_SHA8 = "659cd7d9"
COS_ORDER_RETURN_FIX_SHA8 = "b51a9a10"
ALEX_RETURN_FIX_SHA8 = "9332de97"
COS_ACCEPT_RETURN_FIX_SHA8 = "c5574733"
FORECASTS_PATH = "data/ops/nfl-t5155u-r5-496-freeze/FORECASTS_DEV_R5_496.json"
FORECASTS_SHA256 = "96d3aa6f85e7896df2385df8d025ea0bd4d15d5e2a82edc3f5c9184cd35af407"
SPLIT_PATH = "data/ops/nfl-t5155u-r5-496-freeze/SPLIT_SCAFFOLDING.json"
MARKET_FREEZE_PATH = "data/ops/nfl-t5155u-r5-phase1/MARKET_ARM_FREEZE.json"
OUT_DIR = Path("data/ops/nfl-t5155u-r5-phase2")
RECEIPT_NAME = "RECEIPT.json"
COMMAND = "PYTHONPATH=services/model-service python scripts/nfl/run_nfl_t5155u_r5_phase2_one_exec.py"


class Phase2OneExecRefuse(ValueError):
    """Fail-closed Phase-2 one-exec. Not Cos bind. Not EVAL."""


def _repo_root(root: Path | None) -> Path:
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[5]


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


def schedule_outcome_loader(root: Path) -> Callable[[], dict[str, dict[str, Any]]]:
    """Repo-relative schedule scores for 2020–21 REG496. Not a new source."""

    def _load() -> dict[str, dict[str, Any]]:
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


def _if_only_for_ids(
    forecasts: Sequence[Mapping[str, Any]],
    outcomes: Mapping[str, Mapping[str, Any]],
    ids: Sequence[str],
    *,
    label: str,
) -> dict[str, Any]:
    by = {str(row["game_id"]): row for row in forecasts}
    errors: list[float] = []
    n_by: Counter[str] = Counter()
    for gid in ids:
        row = by.get(gid)
        out = outcomes.get(gid)
        if row is None or out is None:
            raise Phase2OneExecRefuse(f"{label} missing forecast or outcome for {gid}")
        if row.get("q2_status") != "HOLD" or row.get("m_q2") is not None:
            raise Phase2OneExecRefuse(f"{label} invented Q2 for {gid}")
        if row.get("m_candidate") is not None:
            raise Phase2OneExecRefuse(f"{label} invented candidate for {gid}")
        m_if = row.get("m_if")
        if m_if is None or not _finite(m_if):
            raise Phase2OneExecRefuse(f"{label} IF not finite for {gid}")
        actual = float(out["home_score"]) - float(out["away_score"])
        if not math.isfinite(actual):
            raise Phase2OneExecRefuse(f"{label} actual not finite for {gid}")
        errors.append(float(m_if) - actual)
        n_by[str(row["season"])] += 1
    if len(errors) != len(ids):
        raise Phase2OneExecRefuse(f"{label} n={len(errors)} != {len(ids)}")
    return {
        "label": label,
        "n": len(errors),
        "n_by_season": dict(sorted(n_by.items())),
        "mae_if": paired_mae(errors),
        "rmse_if": paired_rmse(errors),
        "bias_if": paired_bias(errors),
        "q2": "HOLD",
        "candidate": "HOLD",
        "mae_q2": None,
        "rmse_q2": None,
        "bias_q2": None,
        "mae_candidate": None,
        "rmse_candidate": None,
        "bias_candidate": None,
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
        m_mkt = float(point["home_margin"])
        diffs.append(signed_abs_loss(m_if, actual) - signed_abs_loss(m_mkt, actual))
        clusters.append(f"{int(row['season'])}-{int(row['week']):02d}")
    game = bootstrap_ci(diffs, stat=mean_stat)
    week = bootstrap_ci(diffs, stat=mean_stat, clusters=clusters)
    n_clusters = len(set(clusters))
    klass = reporting_class(len(diffs))
    return {
        "n": len(diffs),
        "n_by_season": dict(sorted(Counter(gid.split("_", 1)[0] for gid in ids).items())),
        "bytes_sha256": INTERSECTION_BYTES_SHA256,
        "identity_sha256": INTERSECTION_IDENTITY_SHA256,
        "mean_signed_diff_if_vs_market": mean_stat(diffs),
        "bootstrap_game": game,
        "bootstrap_season_week": week,
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
        "q2": "HOLD",
        "candidate": "HOLD",
        "eval": None,
    }


def _assert_finite_metrics(body: Mapping[str, Any]) -> None:
    for key in ("mae_if", "rmse_if", "bias_if"):
        if not _finite(body[key]):
            raise Phase2OneExecRefuse(f"{body.get('label')} {key} not finite")


def run_phase2_one_exec(
    *,
    root: Path | None = None,
    outcome_loader: OutcomeReadSpy | Callable[[], Mapping[str, Mapping[str, Any]]] | None = None,
    invoke_outcome_after_gates: bool = False,
    write: bool = False,
    dest: Path | None = None,
) -> dict[str, Any]:
    """Guarded Phase-2 runner. Default: refuse labels. Never regenerate forecasts."""
    repo = _repo_root(root)
    forecasts = load_committed_forecasts(repo)
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
        raise
    except Exception as exc:
        if getattr(spy, "reads", 0) != 0:
            raise Phase2OneExecRefuse("target scoring outcomes were read on refusal") from exc
        if invoke_outcome_after_gates:
            raise
        receipt = _receipt(
            repo,
            forecasts=forecasts,
            market=market,
            splits=splits,
            scored=None,
            spy_reads=0,
            invoked=False,
        )
        receipt["scoring_refuse"] = {"refused": True, "reason": str(exc), "outcome_loader_reads": 0}
        if write:
            _write_receipt(repo, receipt, dest=dest)
        return receipt
    if not invoke_outcome_after_gates:
        if getattr(spy, "reads", 0) != 0:
            raise Phase2OneExecRefuse("target scoring outcomes were read before Cos bind")
        receipt = _receipt(
            repo,
            forecasts=forecasts,
            market=market,
            splits=splits,
            scored=None,
            spy_reads=0,
            invoked=False,
        )
        if write:
            _write_receipt(repo, receipt, dest=dest)
        return receipt

    if getattr(spy, "reads", 0) != 1:
        raise Phase2OneExecRefuse("expected one post-gate outcome read")
    outcomes = dict(loaded)
    if not outcomes:
        raise Phase2OneExecRefuse("positive path loaded zero target labels")
    missing = [gid for gid in forecasts["game_ids"] if gid not in outcomes]
    if missing:
        raise Phase2OneExecRefuse(f"outcomes missing {len(missing)} REG496 ids")
    if_metrics = {
        "full496": _if_only_for_ids(
            forecasts["forecasts"], outcomes, splits["full496"]["game_ids"], label="full496"
        ),
        "old437": _if_only_for_ids(
            forecasts["forecasts"], outcomes, splits["old437"]["game_ids"], label="old437"
        ),
        "new59": _if_only_for_ids(
            forecasts["forecasts"], outcomes, splits["new59"]["game_ids"], label="new59"
        ),
    }
    for body in if_metrics.values():
        _assert_finite_metrics(body)
    market_metrics = _market_if_paired(forecasts["forecasts"], outcomes, market)
    scored = {
        "if_only": if_metrics,
        "market96": market_metrics,
        "q2": "HOLD",
        "candidate": "HOLD",
        "r3_stop": R3_STOP,
        "forecasts_sha256": FORECASTS_SHA256,
        "identity_sha256": REG496_IDENTITY_SHA256,
        "feature_json_sha256": FEATURE_RECON_REG496_ARTIFACT_SHA256,
        "regenerated_forecasts": False,
        "real_eval_executed": False,
        "nfl_green": False,
        "cert_candidate": CERT_CANDIDATE,
        "eval": None,
    }
    receipt = _receipt(
        repo,
        forecasts=forecasts,
        market=market,
        splits=splits,
        scored=scored,
        spy_reads=1,
        invoked=True,
    )
    if write:
        _write_receipt(repo, receipt, dest=dest)
    return receipt


def _receipt(
    root: Path,
    *,
    forecasts: Mapping[str, Any],
    market: Mapping[str, Any],
    splits: Mapping[str, Any],
    scored: Mapping[str, Any] | None,
    spy_reads: int,
    invoked: bool,
) -> dict[str, Any]:
    status = (
        "PHASE2_ONE_EXEC_TEST_SCORED"
        if invoked
        else "CHECKS_PASSED_AWAITING_ALEX_RE_PREFLIGHT"
    )
    receipt = {
        "schema_version": SCHEMA,
        "ticket": TICKET,
        "path_id": PATH_ID,
        "cert_candidate": CERT_CANDIDATE,
        "draft": True,
        "verified": False,
        "status": status,
        "stop": "STOP_AWAITING_ALEX_RE_PREFLIGHT",
        "self_accept": False,
        "nfl_green": False,
        "real_eval_executed": False,
        "cos_bind": False,
        "score_flag": False,
        "owner_clear_sha8": OWNER_CLEAR_SHA8,
        "cos_order_return_fix_sha8": COS_ORDER_RETURN_FIX_SHA8,
        "alex_return_fix_sha8": ALEX_RETURN_FIX_SHA8,
        "cos_accept_return_fix_sha8": COS_ACCEPT_RETURN_FIX_SHA8,
        "command": COMMAND,
        "forecasts_path": FORECASTS_PATH,
        "forecasts_sha256": FORECASTS_SHA256,
        "regenerated_forecasts": False,
        "identity_sha256": REG496_IDENTITY_SHA256,
        "feature_json_sha256": FEATURE_RECON_REG496_ARTIFACT_SHA256,
        "n_if_finite": forecasts["n_if_finite"],
        "n_q2_hold": forecasts["n_q2_hold"],
        "n_candidate_finite": 0,
        "q2": "HOLD",
        "candidate": "HOLD",
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
        "scored": scored,
        "eval": None,
        "scoring": None if not invoked else "phase2_one_exec_test",
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
    }
    receipt["runtime"] = {"interpreter": "python3"}
    receipt["side_metadata"] = {"pytest_elapsed_semantic": False}
    return receipt


def _write_receipt(root: Path, receipt: Mapping[str, Any], *, dest: Path | None) -> Path:
    out = Path(dest) if dest is not None else Path(root) / OUT_DIR / RECEIPT_NAME
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return out
