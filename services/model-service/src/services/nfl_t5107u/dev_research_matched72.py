"""t5137u — persist omitted matched72 DEV model-vs-market fields.

The already-approved fixed DEV calculation (``run_market_e2e`` +
``emit_market_contract_fields``) already computes candidate / IF / market
errors, paired diffs, frozen CIs, and per-season tables. The prior writer
saved only market MAE/RMSE/bias on ``MARKET_E2E_R2B_CONSUME.json``.

This path appends a **new** DEV_RESEARCH record for the immutable
matched72 cohort. It does not rewrite the parent receipt, first-case,
DEV437, or t5116u FAILED artifacts.

Recompute is **reporting reproduction** of the approved DEV calculation
(to persist omitted output), not independent confirmation.

CERT=0. No EVAL. No claim. No 94-DEV substitution. Exclusive create.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .dev_research import (
    DEFAULT_FREEZE,
    DEFAULT_SCHEDULE,
    DEV_REG_N,
    DEV_REG_SHA256,
    LABEL,
    DevResearchRefuse,
    _record_body,
    write_dev_research_record,
)
from .evaluator import BOOT_B, BOOT_SEED, reporting_class
from .metric_cohorts import DEV_METRIC_SPLIT
from .outcome_gate import (
    FIRST_CASE_FILE_SHA256,
    FIRST_CASE_GAME_ID,
    FIRST_CASE_RECORD_SHA256,
    refuse_overwrite_first_case_record,
    refuse_preserved_t5116u_path,
)
from .r2_market_e2e import (
    DEFAULT_DEST as PARENT_RECEIPT,
    R2A_DIR,
    SEALED_CONSUME_SHA256,
    SEALED_MANIFEST_SHA256,
    SEALED_QUOTES_SHA256,
    SEALED_TIP,
    MarketE2ERefuse,
    default_outcome_loader,
    run_market_e2e,
    sha256_file,
)

SCHEMA = "nfl-t5137u-dev-research-matched72-v1"
CERT_CANDIDATE = 0
MATCHED72_N = 72
NORMALIZED_94_N = 94
NORMALIZED_94_TIP_REFUSED = "0a49afa3"
REPORTING = "REPORTING_REPRODUCTION"
SPLIT_DEV = "dev_reg"

_PKG_ROOT = Path(__file__).resolve().parents[5]
OPS = _PKG_ROOT / "data/ops/nfl-forecast-builder-t5107u"
MATCHED72_PATH = R2A_DIR / "DEV_MATCHED_GAME_IDS.json"
DEFAULT_DEST = OPS / "DEV_RESEARCH_t5137u_MATCHED72.json"

SEALED_MATCHED72_SHA256 = (
    "9f754b0e1c7680a0051b119ec59e2f0603236be447c483491b90a70af61b81e6"
)
SEALED_PARENT_RECEIPT_SHA256 = (
    "380d530041892043902949ded7382a0f631261c3423565f36b094ccc814d93f0"
)
SEALED_FREEZE_SHA256 = (
    "9e704b980b6ce33acc883725823c39766ea19f8a86a7a781ac2a02d95344a732"
)
SEALED_SCHEDULE_SHA256 = (
    "0853342304d269b55033d3474acda853ce00bdb10590f44b09ae569115148479"
)
SEALED_MARKET_MAE = 9.38888888888889
SEALED_MARKET_RMSE = 11.97791660144247
SEALED_MARKET_BIAS = 0.5486111111111112

FORBIDDEN_DEST_NAMES = frozenset(
    {
        "ONE_RUN.json",
        "ONE_EXEC_RESULT_t5116u.json",
        "CURSOR_ONE_EXEC_RESULT_t5116u.md",
        "DEV_RESEARCH_t5119u_R2B.json",
        "DEV_RESEARCH_t5125u_R2B2_437.json",
        "MARKET_E2E_R2B_CONSUME.json",
        "R2B_CONSUME.json",
        "ADMISSIBLE_QUOTES.jsonl",
        "COVERAGE_MANIFEST.json",
        "OWNED_COVERAGE_t5119u.json",
        "R2A_COVERAGE_MANIFEST.json",
        "DEV_MATCHED_GAME_IDS.json",
    }
)

MATCHED72_OUTPUT_CONTRACT = (
    "schema_version",
    "label",
    "metric_split",
    "split",
    "cohort",
    "cert_candidate",
    "eval",
    "scoring",
    "look",
    "exec_scoring",
    "one_run_claim",
    "eval_invoked",
    "r2_eval_called",
    "reporting",
    "reporting_class",
    "reporting_disclosure",
    "not_normalized_94",
    "n",
    "game_ids",
    "matched72_sha256",
    "input_hashes",
    "parent_receipt",
    "mae_challenger",
    "mae_if",
    "mae_market",
    "rmse_challenger",
    "rmse_if",
    "rmse_market",
    "bias_challenger",
    "bias_if",
    "bias_market",
    "delta_mae_vs_if",
    "delta_mae_vs_market",
    "mean_signed_diff_vs_if",
    "mean_signed_diff_vs_market",
    "bootstrap_game",
    "bootstrap_season_week",
    "bootstrap_game_vs_market",
    "bootstrap_season_week_vs_market",
    "per_season",
    "n_by_season",
    "first_case_preserved",
    "old_72_immutable",
    "record_sha256",
)


class Matched72Refuse(DevResearchRefuse):
    """Fail-closed matched72 persist. Not an EVAL look. Not a claim."""


def _refuse_dest(path: Path | None) -> None:
    if path is None:
        return
    dest = Path(path)
    if dest.name in FORBIDDEN_DEST_NAMES:
        raise Matched72Refuse(f"refusing write to preserved / parent receipt {dest.name}")
    try:
        refuse_preserved_t5116u_path(dest)
        refuse_overwrite_first_case_record(dest)
    except Exception as exc:
        raise Matched72Refuse(str(exc)) from exc
    resolved = dest.resolve()
    if resolved.parent.resolve() == R2A_DIR.resolve():
        raise Matched72Refuse("refusing rewrite of R2-A coverage directory")
    if resolved == PARENT_RECEIPT.resolve():
        raise Matched72Refuse("refusing overwrite of sealed MARKET_E2E_R2B_CONSUME.json")


def load_matched72_ids(path: Path | None = None) -> list[str]:
    dest = Path(path) if path else MATCHED72_PATH
    if not dest.is_file():
        raise Matched72Refuse(f"matched72 game-id list missing: {dest}")
    live = sha256_file(dest)
    ids = json.loads(dest.read_text(encoding="utf-8"))
    if not isinstance(ids, list) or not ids:
        raise Matched72Refuse("matched72 game-id list empty or not a list")
    ids = [str(g) for g in ids]
    if len(ids) == NORMALIZED_94_N:
        raise Matched72Refuse(
            f"refusing silent #694 normalized 94-DEV substitution ({NORMALIZED_94_TIP_REFUSED})"
        )
    if len(ids) != MATCHED72_N or len(set(ids)) != MATCHED72_N:
        raise Matched72Refuse(
            f"matched72 pin is n={MATCHED72_N} unique; got n={len(ids)} unique={len(set(ids))}"
        )
    if dest.resolve() == MATCHED72_PATH.resolve() and live != SEALED_MATCHED72_SHA256:
        raise Matched72Refuse("DEV_MATCHED_GAME_IDS hash mismatch vs sealed 9f754b0e")
    if dest.resolve() != MATCHED72_PATH.resolve():
        if live != SEALED_MATCHED72_SHA256 and len(ids) != MATCHED72_N:
            raise Matched72Refuse("injected matched72 list is not the sealed 72")
    return ids


def _require_market_pin(contract: Mapping[str, Any]) -> None:
    if contract.get("mae_market") != SEALED_MARKET_MAE:
        raise Matched72Refuse(
            "reproduced mae_market drifted from sealed parent receipt 9.38888888888889"
        )
    if contract.get("rmse_market") != SEALED_MARKET_RMSE:
        raise Matched72Refuse(
            "reproduced rmse_market drifted from sealed parent receipt 11.97791660144247"
        )
    if contract.get("bias_market") != SEALED_MARKET_BIAS:
        raise Matched72Refuse(
            "reproduced bias_market drifted from sealed parent receipt 0.5486111111111112"
        )


def _require_bootstrap(name: str, body: Any) -> None:
    if not isinstance(body, Mapping):
        raise Matched72Refuse(f"{name} missing from matched72 persist")
    ci = body.get("ci95")
    if not isinstance(ci, (list, tuple)) or len(ci) != 2:
        raise Matched72Refuse(f"{name} requires frozen ci95 [lo, hi]")
    if body.get("B") != BOOT_B or body.get("seed") != BOOT_SEED:
        raise Matched72Refuse(f"{name} bootstrap is frozen at B={BOOT_B} seed={BOOT_SEED}")


def validate_matched72_record(record: Mapping[str, Any]) -> None:
    missing = [k for k in MATCHED72_OUTPUT_CONTRACT if k not in record]
    if missing:
        raise Matched72Refuse(f"matched72 DEV_RESEARCH contract incomplete: {missing}")
    if record.get("label") != LABEL:
        raise Matched72Refuse("label must be DEV_RESEARCH")
    if record.get("metric_split") != DEV_METRIC_SPLIT:
        raise Matched72Refuse("metric_split must be DEV")
    if record.get("split") != SPLIT_DEV:
        raise Matched72Refuse("split must be dev_reg (explicit DEV; not inherited EVAL)")
    if record.get("cohort") != "matched72":
        raise Matched72Refuse("cohort must be matched72")
    if record.get("reporting") != REPORTING:
        raise Matched72Refuse("reporting must be REPORTING_REPRODUCTION")
    if record.get("not_normalized_94") is not True:
        raise Matched72Refuse("must refuse #694 normalized 94-DEV swap")
    if record.get("n") != MATCHED72_N:
        raise Matched72Refuse("n must be 72")
    if record.get("eval") is not None:
        raise Matched72Refuse("DEV_RESEARCH must not carry eval")
    if record.get("one_run_claim") is not False:
        raise Matched72Refuse("DEV_RESEARCH must not claim a one-run")
    if record.get("eval_invoked") is not False or record.get("r2_eval_called") is not False:
        raise Matched72Refuse("EVAL must not be invoked")
    if record.get("cert_candidate") != CERT_CANDIDATE:
        raise Matched72Refuse("CERT must be 0")
    if list(record.get("game_ids") or []) != load_matched72_ids():
        raise Matched72Refuse("game_ids must be the sealed matched72 list")
    if record.get("matched72_sha256") != SEALED_MATCHED72_SHA256:
        raise Matched72Refuse("matched72_sha256 pin mismatch vs 9f754b0e")
    parent = record.get("parent_receipt") or {}
    if parent.get("file_sha256") != SEALED_PARENT_RECEIPT_SHA256:
        raise Matched72Refuse("parent MARKET_E2E receipt is not the sealed 380d5300 bytes")
    if parent.get("immutable") is not True or record.get("old_72_immutable") is not True:
        raise Matched72Refuse("old 72 / parent receipt must stay immutable")
    _require_market_pin(record)
    for name in (
        "bootstrap_game",
        "bootstrap_season_week",
        "bootstrap_game_vs_market",
        "bootstrap_season_week_vs_market",
    ):
        _require_bootstrap(name, record.get(name))
    seasons = record.get("per_season")
    if not isinstance(seasons, Mapping) or not seasons:
        raise Matched72Refuse("per-season tables required")
    for key in (
        "mae_challenger",
        "mae_if",
        "rmse_challenger",
        "rmse_if",
        "bias_challenger",
        "bias_if",
        "mean_signed_diff_vs_if",
        "mean_signed_diff_vs_market",
        "delta_mae_vs_if",
        "delta_mae_vs_market",
    ):
        if record.get(key) is None:
            raise Matched72Refuse(f"omitted field still missing: {key}")


def build_matched72_dev_research_record(
    *,
    dest: Path | None = None,
    freeze_path: Path | None = None,
    schedule_path: Path | None = None,
    matched72_path: Path | None = None,
    eligible_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Persist omitted matched72 DEV fields. Reporting reproduction only."""
    dest_p = Path(dest) if dest is not None else None
    _refuse_dest(dest_p)
    ids = list(eligible_ids) if eligible_ids is not None else load_matched72_ids(matched72_path)
    if len(ids) == NORMALIZED_94_N:
        raise Matched72Refuse(
            f"refusing silent #694 normalized 94-DEV substitution ({NORMALIZED_94_TIP_REFUSED})"
        )
    if len(ids) != MATCHED72_N or ids != load_matched72_ids(matched72_path):
        raise Matched72Refuse("eligible_ids must be the sealed matched72 list (n=72)")

    parent_sha = sha256_file(PARENT_RECEIPT)
    if parent_sha != SEALED_PARENT_RECEIPT_SHA256:
        raise Matched72Refuse("parent MARKET_E2E_R2B_CONSUME.json mutated — refuse")
    freeze_p = Path(freeze_path) if freeze_path else DEFAULT_FREEZE
    schedule_p = Path(schedule_path) if schedule_path else DEFAULT_SCHEDULE
    freeze_sha = sha256_file(freeze_p)
    schedule_sha = sha256_file(schedule_p)
    if freeze_p.resolve() == DEFAULT_FREEZE.resolve() and freeze_sha != SEALED_FREEZE_SHA256:
        raise Matched72Refuse("forecast freeze hash mismatch vs sealed 9e704b98")
    if schedule_p.resolve() == DEFAULT_SCHEDULE.resolve() and schedule_sha != SEALED_SCHEDULE_SHA256:
        raise Matched72Refuse("schedule hash mismatch vs sealed 08533423")
    matched_sha = sha256_file(Path(matched72_path) if matched72_path else MATCHED72_PATH)

    loader = default_outcome_loader(ids)
    try:
        join = run_market_e2e(
            split=SPLIT_DEV,
            eligible_ids=ids,
            outcome_loader=loader,
            emit_metrics=True,
            freeze_path=freeze_p,
        )
    except MarketE2ERefuse as exc:
        raise Matched72Refuse(str(exc)) from exc
    if join.get("split") != SPLIT_DEV:
        raise Matched72Refuse("matched call did not keep explicit DEV split=dev_reg")
    if join.get("eval_invoked") or join.get("r2_eval_called") or join.get("one_run_claim"):
        raise Matched72Refuse("EVAL / claim leaked into reporting reproduction")
    if join.get("joined_n") != MATCHED72_N or not join.get("bind_ready"):
        raise Matched72Refuse(
            f"matched72 join incomplete: joined={join.get('joined_n')} bind_ready={join.get('bind_ready')}"
        )
    contract = join.get("market_contract") or {}
    _require_market_pin(contract)
    for key in (
        "mae_challenger",
        "mae_if",
        "rmse_challenger",
        "rmse_if",
        "bias_challenger",
        "bias_if",
        "mean_signed_diff_vs_if",
        "mean_signed_diff_vs_market",
        "delta_mae_vs_if",
        "bootstrap_game",
        "bootstrap_season_week",
        "bootstrap_game_vs_market",
        "bootstrap_season_week_vs_market",
        "per_season",
        "n_by_season",
    ):
        if contract.get(key) is None:
            raise Matched72Refuse(f"approved calculation omitted {key} — persist refused")

    parent_body = json.loads(PARENT_RECEIPT.read_text(encoding="utf-8"))
    record = _record_body(
        {
            "schema_version": SCHEMA,
            "label": LABEL,
            "metric_split": DEV_METRIC_SPLIT,
            "split": SPLIT_DEV,
            "cohort": "matched72",
            "cert_candidate": CERT_CANDIDATE,
            "eval": None,
            "scoring": None,
            "look": None,
            "exec_scoring": "REFUSED_DEV_RESEARCH_NOT_EVAL",
            "one_run_claim": False,
            "eval_invoked": False,
            "r2_eval_called": False,
            "g5_loosened": False,
            "g5_status": "DATA_COVERAGE_BLOCKED",
            "reporting": REPORTING,
            "reporting_class": reporting_class(MATCHED72_N),
            "reporting_disclosure": (
                "Reproduced the already-approved fixed DEV calculation solely to "
                "persist omitted market_contract fields (candidate/IF errors, paired "
                "diffs, frozen CIs, per-season tables). Not independent confirmation."
            ),
            "not_normalized_94": True,
            "normalized_94_tip_refused": NORMALIZED_94_TIP_REFUSED,
            "dev_reg_parent_n": DEV_REG_N,
            "dev_reg_parent_sha256": DEV_REG_SHA256,
            "n": MATCHED72_N,
            "joined_n": join["joined_n"],
            "eligible_n": join["eligible_n"],
            "missing_n": join["missing_n"],
            "bind_ready": join["bind_ready"],
            "n_by_season": contract["n_by_season"],
            "game_ids": list(ids),
            "matched72_sha256": matched_sha,
            "input_hashes": {
                "matched72_game_ids": matched_sha,
                "admissible_quotes": SEALED_QUOTES_SHA256,
                "coverage_manifest": SEALED_MANIFEST_SHA256,
                "r2b_consume": SEALED_CONSUME_SHA256,
                "forecast_freeze": freeze_sha,
                "schedule_results": schedule_sha,
                "parent_market_e2e_receipt": parent_sha,
                "dev_reg_437": DEV_REG_SHA256,
                "r2a_tip": SEALED_TIP,
            },
            "parent_receipt": {
                "path": str(PARENT_RECEIPT),
                "file_sha256": parent_sha,
                "immutable": True,
                "schema_version": parent_body.get("schema_version"),
                "mae_market": parent_body["dev_matched_subset"]["mae_market"],
                "rmse_market": parent_body["dev_matched_subset"]["rmse_market"],
                "bias_market": parent_body["dev_matched_subset"]["bias_market"],
            },
            "mae_challenger": contract["mae_challenger"],
            "mae_if": contract["mae_if"],
            "mae_market": contract["mae_market"],
            "rmse_challenger": contract["rmse_challenger"],
            "rmse_if": contract["rmse_if"],
            "rmse_market": contract["rmse_market"],
            "bias_challenger": contract["bias_challenger"],
            "bias_if": contract["bias_if"],
            "bias_market": contract["bias_market"],
            "delta_mae_vs_if": (
                contract.get("delta_mae_vs_if")
                if contract.get("delta_mae_vs_if") is not None
                else contract["mae_challenger"] - contract["mae_if"]
            ),
            "delta_mae_vs_market": (
                contract.get("delta_mae_vs_market")
                if contract.get("delta_mae_vs_market") is not None
                else contract["mae_challenger"] - contract["mae_market"]
            ),
            "mean_signed_diff_vs_if": contract["mean_signed_diff_vs_if"],
            "mean_signed_diff_vs_market": contract["mean_signed_diff_vs_market"],
            "bootstrap_game": contract["bootstrap_game"],
            "bootstrap_season_week": contract["bootstrap_season_week"],
            "bootstrap_game_vs_market": contract["bootstrap_game_vs_market"],
            "bootstrap_season_week_vs_market": contract["bootstrap_season_week_vs_market"],
            "per_season": contract["per_season"],
            "market_points": join["market_points"],
            "first_case_preserved": {
                "game_id": FIRST_CASE_GAME_ID,
                "record_sha256": FIRST_CASE_RECORD_SHA256,
                "file_sha256": FIRST_CASE_FILE_SHA256,
                "in_matched72": FIRST_CASE_GAME_ID in ids,
            },
            "old_72_immutable": True,
            "rng": {
                "bootstrap_B": BOOT_B,
                "bootstrap_seed": BOOT_SEED,
                "source": "approved fixed DEV calculation — reporting reproduction",
            },
            "target_join_phase": join.get("target_join_phase"),
            "r2a_tip": SEALED_TIP,
            "notes": [
                "Append-only persist of omitted matched72 model-vs-market fields.",
                "Parent MARKET_E2E_R2B_CONSUME.json left byte-immutable (380d5300).",
                "Explicit DEV: split=dev_reg, metric_split=DEV, label=DEV_RESEARCH.",
                "REPORTING_REPRODUCTION of the already-approved fixed DEV calculation. Not independent confirmation.",
                "matched72 only (9f754b0e). #694 normalized 94-DEV (0a49afa3) not substituted.",
                "EVAL not invoked. one_run_claim=false. CERT=0. G5 DATA_COVERAGE_BLOCKED.",
            ],
        }
    )
    validate_matched72_record(record)
    if dest_p is not None:
        _refuse_dest(dest_p)
        try:
            write_dev_research_record(record, dest_p)
        except DevResearchRefuse as exc:
            raise Matched72Refuse(str(exc)) from exc
        record["_path"] = str(dest_p)
    return record
