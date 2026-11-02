"""t5168u market96 MARKET absolute-error schema correction. CERT=0.

Additive reporting schema only. Reads frozen JOINED_ROWS df24500e.
Does not rewrite EXEC / t5165u addendum scientific bytes.
Does not invoke one-exec / --score / --cos-bind / claim.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from .evaluator import paired_bias, paired_mae, paired_rmse
from .market_arm_freeze import (
    INTERSECTION_BYTES_SHA256,
    INTERSECTION_IDENTITY_SHA256,
    INTERSECTION_N,
)
from .r5_reporting_addendum import (
    EXEC_BIND_ID,
    EXEC_ONE_RUN_PATH,
    EXEC_ONE_RUN_SHA256,
    EXEC_RECEIPT_PATH,
    EXEC_RECEIPT_SHA256,
    EXEC_STAMP,
    EXEC_TIP,
    OUT_DIR as ADDENDUM_DIR,
    REPORT_NAME,
)
from .recon_contract import _finite
from .recon_driver import sha256_file, sha256_text

TICKET = "t5168u"
SCHEMA = "nfl-t5168u-market96-schema-correction-v1"
OWNER_CLEAR_SHA8 = "8e571382"
COS_ORDER_SHA8 = "ca4dac65"
ALEX_STAND_SHA8 = "ebddd100"
COS_STAND_SHA8 = "7548b001"
ADDENDUM_TIP = "fa60e4b6f58669f9c8b914d9945c53e0c9d5bb2c"
ADDENDUM_STAMP = "e317fc05b9f79dd3bee2183dd5622656594aefab"
JOINED_PATH = "data/ops/nfl-t5165u-r5-reporting/JOINED_ROWS.json"
JOINED_SHA256 = "df24500e4366240ca6aa7d1aedab0c8415a8bea17dbfe969d6e9fac96e77a5a0"
ADDENDUM_REPORT_PATH = str(ADDENDUM_DIR / REPORT_NAME)
ADDENDUM_REPORT_SHA256 = "64516e39ac908d75a85ad11e305ad0100afd8e55238750b5c1fd724bb9aaf96c"
LABEL = "RESEARCH_CONSUMED_RETRO"
KIND = "reporting_schema_correction"
CERT_CANDIDATE = 0
OUT_DIR = Path("data/ops/nfl-t5168u-market96-schema")
CORRECTION_NAME = "MARKET96_SCHEMA_CORRECTION.json"
CODE_RELPATHS = (
    "services/model-service/src/services/nfl_t5107u/r5_market96_schema_correction.py",
    "scripts/nfl/run_nfl_t5168u_market96_schema_correction.py",
)
OWNER_MARKET = {
    "overall": {
        "n": 96,
        "mae_market": 10.044270833333334,
        "rmse_market": 12.854023162354009,
        "bias_market": -1.4140625,
    },
    "2020": {
        "n": 41,
        "mae_market": 10.945121951219512,
        "rmse_market": 13.703357697846245,
        "bias_market": 0.5304878048780488,
    },
    "2021": {
        "n": 55,
        "mae_market": 9.372727272727273,
        "rmse_market": 12.18242027005979,
        "bias_market": -2.8636363636363638,
    },
}


class Market96SchemaRefuse(ValueError):
    """Fail-closed MARKET schema correction. Not EXEC. Not a new look."""


def _repo_root(root: Path | None) -> Path:
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[5]


def correction_code_hashes(root: Path | None = None) -> dict[str, str]:
    repo = _repo_root(root)
    return {rel: sha256_file(repo / rel) for rel in CODE_RELPATHS}


def correction_code_sha256(root: Path | None = None) -> str:
    return sha256_text(json.dumps(correction_code_hashes(root), sort_keys=True, separators=(",", ":")))


def correction_input_pin_bundle() -> dict[str, str]:
    return {
        "joined_sha256": JOINED_SHA256,
        "addendum_report_sha256": ADDENDUM_REPORT_SHA256,
        "exec_receipt_sha256": EXEC_RECEIPT_SHA256,
        "exec_one_run_sha256": EXEC_ONE_RUN_SHA256,
        "exec_bind_id": EXEC_BIND_ID,
        "market_bytes_sha256": INTERSECTION_BYTES_SHA256,
        "market_identity_sha256": INTERSECTION_IDENTITY_SHA256,
    }


def correction_input_sha256() -> str:
    return sha256_text(json.dumps(correction_input_pin_bundle(), sort_keys=True, separators=(",", ":")))


def _assert_frozen_bytes(repo: Path) -> None:
    if sha256_file(repo / EXEC_RECEIPT_PATH) != EXEC_RECEIPT_SHA256:
        raise Market96SchemaRefuse("EXEC RECEIPT drifted — do not overwrite")
    if sha256_file(repo / EXEC_ONE_RUN_PATH) != EXEC_ONE_RUN_SHA256:
        raise Market96SchemaRefuse("EXEC ONE_RUN drifted — do not overwrite")
    if sha256_file(repo / JOINED_PATH) != JOINED_SHA256:
        raise Market96SchemaRefuse("JOINED_ROWS drifted — correction reads frozen bytes only")
    if sha256_file(repo / ADDENDUM_REPORT_PATH) != ADDENDUM_REPORT_SHA256:
        raise Market96SchemaRefuse("t5165u REPORTING_ADDENDUM drifted — do not rewrite")


def market_error(row: Mapping[str, Any]) -> float:
    if "market_home_margin" not in row:
        raise Market96SchemaRefuse(f"missing market_home_margin for {row.get('game_id')}")
    margin = row.get("market_home_margin")
    actual = row.get("actual_margin")
    if not _finite(margin) or not _finite(actual):
        raise Market96SchemaRefuse(f"nonfinite market error for {row.get('game_id')}")
    err = float(margin) - float(actual)
    if not math.isfinite(err):
        raise Market96SchemaRefuse(f"nonfinite market error for {row.get('game_id')}")
    return err


def select_market96(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    chosen = [dict(row) for row in rows if row.get("in_market96") is True]
    if len(chosen) != INTERSECTION_N:
        raise Market96SchemaRefuse(f"wrong market cohort n={len(chosen)} != 96")
    seasons = Counter(str(row["season"]) for row in chosen)
    if seasons.get("2020") != 41 or seasons.get("2021") != 55:
        raise Market96SchemaRefuse(f"wrong market cohort seasons {dict(seasons)}")
    for row in chosen:
        market_error(row)
    return chosen


def _abs_block(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    errs = [market_error(row) for row in rows]
    return {
        "n": len(rows),
        "mae_market": paired_mae(errs),
        "rmse_market": paired_rmse(errs),
        "bias_market": paired_bias(errs),
    }


def _match_owner(got: Mapping[str, Any], expected: Mapping[str, float | int], *, label: str) -> None:
    if int(got["n"]) != int(expected["n"]):
        raise Market96SchemaRefuse(f"{label} n {got['n']} != owner {expected['n']}")
    for key in ("mae_market", "rmse_market", "bias_market"):
        if float(got[key]) != float(expected[key]):
            raise Market96SchemaRefuse(f"{label} {key} {got[key]} != owner {expected[key]}")


def build_market96_schema_correction(
    *,
    root: Path | None = None,
    write: bool = True,
    rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(root)
    _assert_frozen_bytes(repo)
    if rows is None:
        payload = json.loads((repo / JOINED_PATH).read_text(encoding="utf-8"))
        rows = list(payload["rows"])
    chosen = select_market96(rows)
    overall = _abs_block(chosen)
    _match_owner(overall, OWNER_MARKET["overall"], label="overall")
    per_season: dict[str, dict[str, Any]] = {}
    for season in ("2020", "2021"):
        subset = [row for row in chosen if str(row["season"]) == season]
        block = _abs_block(subset)
        _match_owner(block, OWNER_MARKET[season], label=season)
        per_season[season] = block
    addendum = json.loads((repo / ADDENDUM_REPORT_PATH).read_text(encoding="utf-8"))
    cited_models = addendum["market96"]
    cited_pairs = cited_models.get("cited_from_exec_receipt") or {}
    report = {
        "schema_version": SCHEMA,
        "ticket": TICKET,
        "owner_clear_sha8": OWNER_CLEAR_SHA8,
        "cos_order_sha8": COS_ORDER_SHA8,
        "alex_stand_sha8": ALEX_STAND_SHA8,
        "cos_stand_sha8": COS_STAND_SHA8,
        "cert_candidate": CERT_CANDIDATE,
        "draft": True,
        "verified": False,
        "self_accept": False,
        "nfl_green": False,
        "real_eval_executed": False,
        "new_scientific_look": False,
        "kind": KIND,
        "label": LABEL,
        "note": (
            "no new scientific look — additive market96 MARKET absolute-error "
            "schema correction under t5168u; Q2 is diagnostic only, not a "
            "market substitute; three arms = candidate / IF / MARKET"
        ),
        "q2_role": "diagnostic_only_not_market_substitute",
        "arms": ["candidate", "IF", "MARKET"],
        "exec_tip": EXEC_TIP,
        "exec_stamp": EXEC_STAMP,
        "exec_bind_id": EXEC_BIND_ID,
        "addendum_tip": ADDENDUM_TIP,
        "addendum_stamp": ADDENDUM_STAMP,
        "joined_path": JOINED_PATH,
        "joined_sha256": JOINED_SHA256,
        "addendum_report_path": ADDENDUM_REPORT_PATH,
        "addendum_report_sha256": ADDENDUM_REPORT_SHA256,
        "exec_receipt_path": EXEC_RECEIPT_PATH,
        "exec_receipt_sha256": EXEC_RECEIPT_SHA256,
        "exec_one_run_path": EXEC_ONE_RUN_PATH,
        "exec_one_run_sha256": EXEC_ONE_RUN_SHA256,
        "market96": {
            "n": INTERSECTION_N,
            "n_by_season": {"2020": 41, "2021": 55},
            "bytes_sha256": INTERSECTION_BYTES_SHA256,
            "identity_sha256": INTERSECTION_IDENTITY_SHA256,
            "reporting_class": "DESCRIPTIVE_ONLY",
            "nfl_green": False,
            "eval": None,
            "mae_if": cited_models["mae_if"],
            "rmse_if": cited_models["rmse_if"],
            "bias_if": cited_models["bias_if"],
            "mae_q2_diagnostic": cited_models["mae_q2"],
            "rmse_q2_diagnostic": cited_models["rmse_q2"],
            "bias_q2_diagnostic": cited_models["bias_q2"],
            "mae_candidate": cited_models["mae_candidate"],
            "rmse_candidate": cited_models["rmse_candidate"],
            "bias_candidate": cited_models["bias_candidate"],
            "mae_market": overall["mae_market"],
            "rmse_market": overall["rmse_market"],
            "bias_market": overall["bias_market"],
            "per_season": {
                season: {
                    "n": per_season[season]["n"],
                    "mae_if": cited_models["per_season"][season]["mae_if"],
                    "rmse_if": cited_models["per_season"][season]["rmse_if"],
                    "bias_if": cited_models["per_season"][season]["bias_if"],
                    "mae_q2_diagnostic": cited_models["per_season"][season]["mae_q2"],
                    "rmse_q2_diagnostic": cited_models["per_season"][season]["rmse_q2"],
                    "bias_q2_diagnostic": cited_models["per_season"][season]["bias_q2"],
                    "mae_candidate": cited_models["per_season"][season]["mae_candidate"],
                    "rmse_candidate": cited_models["per_season"][season]["rmse_candidate"],
                    "bias_candidate": cited_models["per_season"][season]["bias_candidate"],
                    "mae_market": per_season[season]["mae_market"],
                    "rmse_market": per_season[season]["rmse_market"],
                    "bias_market": per_season[season]["bias_market"],
                }
                for season in ("2020", "2021")
            },
            "paired_cited_from_exec_receipt": {
                "path": EXEC_RECEIPT_PATH,
                "sha256": EXEC_RECEIPT_SHA256,
                "mean_signed_diff_if_vs_market": cited_pairs.get("mean_signed_diff_if_vs_market"),
                "mean_signed_diff_candidate_vs_market": cited_pairs.get(
                    "mean_signed_diff_candidate_vs_market"
                ),
                "bootstrap_game": cited_pairs.get("bootstrap_game"),
                "bootstrap_season_week": cited_pairs.get("bootstrap_season_week"),
                "bootstrap_game_candidate": cited_pairs.get("bootstrap_game_candidate"),
                "bootstrap_season_week_candidate": cited_pairs.get(
                    "bootstrap_season_week_candidate"
                ),
            },
            "if_q2_candidate_cited_from_addendum": {
                "path": ADDENDUM_REPORT_PATH,
                "sha256": ADDENDUM_REPORT_SHA256,
            },
        },
        "pins": correction_input_pin_bundle(),
        "runner_code_hashes": correction_code_hashes(repo),
        "runner_code_sha256": correction_code_sha256(repo),
        "runner_input_sha256": correction_input_sha256(),
    }
    canonical = {k: v for k, v in report.items() if k not in {"hashes", "runtime"}}
    report["hashes"] = {
        "code_sha256": report["runner_code_sha256"],
        "input_sha256": report["runner_input_sha256"],
        "output_sha256": sha256_text(
            json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
        ),
    }
    report["runtime"] = {"interpreter": "python3", "invoked_one_exec": False}
    if write:
        dest = repo / OUT_DIR
        dest.mkdir(parents=True, exist_ok=True)
        (dest / CORRECTION_NAME).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        _assert_frozen_bytes(repo)
    return report
