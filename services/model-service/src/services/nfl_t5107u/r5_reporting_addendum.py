"""t5165u reporting-arithmetic addendum. CERT=0.

No new scientific look. Reconstructs the already-consumed EXEC join from
frozen forecasts + pinned schedule-score bytes + identity splits.
Does not invoke the one-exec runner, --score, or --cos-bind.
Does not write phase-2 RECEIPT / ONE_RUN*.
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

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
from .r5_phase2_one_exec import (
    CANDIDATE_COMPLETED_SHA256,
    COMPLETED_FORECASTS_PATH,
    COMPLETED_FORECASTS_SHA256,
    FORECASTS_PATH,
    FORECASTS_SHA256,
    IDENTITY_FREEZE_SHA256,
    MARKET_FREEZE_PATH,
    Q2_COMPLETED_SHA256,
    REG496_IDENTITY_SHA256,
    SPLIT_PATH,
)
from .recon_contract import _finite
from .recon_driver import sha256_file, sha256_text

TICKET = "t5165u"
SCHEMA = "nfl-t5165u-r5-reporting-addendum-v1"
OWNER_CLEAR_SHA8 = "0ac66543"
COS_ORDER_SHA8 = "9ad857bb"
TRACKER = "46283"
LABEL = "RESEARCH_CONSUMED_RETRO"
KIND = "reporting_reconstruction"
CERT_CANDIDATE = 0
EXEC_TIP = "093a51dc9d6ef4c18fb16101a02c7395ce074096"
EXEC_STAMP = "3001dcc32f4425596727a3c0ebb4a052bc1bd37f"
EXEC_BIND_ID = "4eef5d1f843bb17327d0d81d3cdae3a8d7d91917d9763691b55808c365d0caa6"
EXEC_ONE_RUN_SHA256 = "9a72c55be94e0fc04778da22748a70b2e159c4c95e4803c41449cbb8abfc13cc"
EXEC_RECEIPT_SHA256 = "f8da3deab88858405fc55c0af829fde53ef4a689b697cd7a773442e564355869"
EXEC_RECEIPT_PATH = "data/ops/nfl-t5155u-r5-phase2/RECEIPT.json"
EXEC_ONE_RUN_PATH = "data/ops/nfl-t5155u-r5-phase2/ONE_RUN.json"
OUT_DIR = Path("data/ops/nfl-t5165u-r5-reporting")
JOIN_NAME = "JOINED_ROWS.json"
REPORT_NAME = "REPORTING_ADDENDUM.json"
CODE_RELPATHS = (
    "services/model-service/src/services/nfl_t5107u/r5_reporting_addendum.py",
    "scripts/nfl/run_nfl_t5165u_r5_reporting_addendum.py",
)


class ReportingAddendumRefuse(ValueError):
    """Fail-closed reporting reconstruction. Not EXEC. Not EVAL."""


def _repo_root(root: Path | None) -> Path:
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[5]


def reporting_code_hashes(root: Path | None = None) -> dict[str, str]:
    repo = _repo_root(root)
    return {rel: sha256_file(repo / rel) for rel in CODE_RELPATHS}


def reporting_code_sha256(root: Path | None = None) -> str:
    return sha256_text(json.dumps(reporting_code_hashes(root), sort_keys=True, separators=(",", ":")))


def reporting_input_pin_bundle() -> dict[str, str]:
    return {
        "completed_forecasts_sha256": COMPLETED_FORECASTS_SHA256,
        "forecasts_sha256": FORECASTS_SHA256,
        "q2_completed_sha256": Q2_COMPLETED_SHA256,
        "candidate_completed_sha256": CANDIDATE_COMPLETED_SHA256,
        "identity_freeze_sha256": IDENTITY_FREEZE_SHA256,
        "reg496_identity_sha256": REG496_IDENTITY_SHA256,
        "schedule_sha256": SCHEDULE_SHA256,
        "market_bytes_sha256": INTERSECTION_BYTES_SHA256,
        "market_identity_sha256": INTERSECTION_IDENTITY_SHA256,
        "exec_receipt_sha256": EXEC_RECEIPT_SHA256,
        "exec_one_run_sha256": EXEC_ONE_RUN_SHA256,
        "exec_bind_id": EXEC_BIND_ID,
    }


def reporting_input_sha256() -> str:
    return sha256_text(json.dumps(reporting_input_pin_bundle(), sort_keys=True, separators=(",", ":")))


def _assert_exec_untouched(repo: Path) -> None:
    if sha256_file(repo / EXEC_RECEIPT_PATH) != EXEC_RECEIPT_SHA256:
        raise ReportingAddendumRefuse("EXEC RECEIPT drifted — do not overwrite")
    if sha256_file(repo / EXEC_ONE_RUN_PATH) != EXEC_ONE_RUN_SHA256:
        raise ReportingAddendumRefuse("EXEC ONE_RUN drifted — do not overwrite")
    record = json.loads((repo / EXEC_ONE_RUN_PATH).read_text(encoding="utf-8"))
    if record.get("bind_id") != EXEC_BIND_ID or record.get("status") != "CONSUMED":
        raise ReportingAddendumRefuse("EXEC bind/status drifted")


def _load_completed(repo: Path) -> list[dict[str, Any]]:
    path = repo / COMPLETED_FORECASTS_PATH
    if sha256_file(path) != COMPLETED_FORECASTS_SHA256:
        raise ReportingAddendumRefuse("completed forecasts pin drifted")
    if sha256_file(repo / FORECASTS_PATH) != FORECASTS_SHA256:
        raise ReportingAddendumRefuse("IF496 pin drifted")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("if_forecasts_sha256") != FORECASTS_SHA256:
        raise ReportingAddendumRefuse("completed IF pin drifted")
    if payload.get("if_regenerated") is True:
        raise ReportingAddendumRefuse("completed forecasts regenerated IF")
    return list(payload["forecasts"])


def _load_splits(repo: Path) -> dict[str, Any]:
    return json.loads((repo / SPLIT_PATH).read_text(encoding="utf-8"))


def _load_market(repo: Path) -> dict[str, Any]:
    payload = json.loads((repo / MARKET_FREEZE_PATH).read_text(encoding="utf-8"))
    inter = payload["intersection"]
    if int(inter["n"]) != INTERSECTION_N:
        raise ReportingAddendumRefuse("market n != 96")
    if inter["bytes_sha256"] != INTERSECTION_BYTES_SHA256:
        raise ReportingAddendumRefuse("market bytes drifted")
    if inter["identity_sha256"] != INTERSECTION_IDENTITY_SHA256:
        raise ReportingAddendumRefuse("market identity drifted")
    return inter


def _load_schedule_scores(repo: Path) -> dict[str, dict[str, Any]]:
    """Reporting reconstruction of already-consumed schedule-score bytes."""
    path = repo / SCHEDULE_PATH
    if sha256_file(path) != SCHEDULE_SHA256:
        raise ReportingAddendumRefuse("schedule pin drifted")
    out: dict[str, dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if str(row.get("season_type") or "").upper() != "REG":
                continue
            season = int(row["season"])
            if season not in (2020, 2021):
                continue
            hs, aws = row.get("home_score"), row.get("away_score")
            if hs in (None, "") or aws in (None, ""):
                continue
            gid = str(row["game_id"])
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


def _join_rows(
    forecasts: Sequence[Mapping[str, Any]],
    outcomes: Mapping[str, Mapping[str, Any]],
    splits: Mapping[str, Any],
    market: Mapping[str, Any],
) -> list[dict[str, Any]]:
    full = set(splits["full496"]["game_ids"])
    old = set(splits["old437"]["game_ids"])
    new = set(splits["new59"]["game_ids"])
    market_by = {str(row["game_id"]): row for row in market["games"]}
    rows: list[dict[str, Any]] = []
    for fc in forecasts:
        gid = str(fc["game_id"])
        if gid not in full:
            continue
        out = outcomes.get(gid)
        if out is None:
            raise ReportingAddendumRefuse(f"schedule score missing for {gid}")
        m_if, m_q2, m_c = fc.get("m_if"), fc.get("m_q2"), fc.get("m_candidate")
        if not (_finite(m_if) and _finite(m_q2) and _finite(m_c)):
            raise ReportingAddendumRefuse(f"non-finite forecast for {gid}")
        actual = float(out["home_score"]) - float(out["away_score"])
        if not math.isfinite(actual):
            raise ReportingAddendumRefuse(f"non-finite actual for {gid}")
        err_if = float(m_if) - actual
        err_q2 = float(m_q2) - actual
        err_c = float(m_c) - actual
        l_if = signed_abs_loss(float(m_if), actual)
        l_q2 = signed_abs_loss(float(m_q2), actual)
        l_c = signed_abs_loss(float(m_c), actual)
        mkt = market_by.get(gid)
        row = {
            "game_id": gid,
            "season": int(fc["season"]),
            "week": int(fc["week"]),
            "home": str(fc.get("home") or out["home"]),
            "away": str(fc.get("away") or out["away"]),
            "m_if": float(m_if),
            "m_q2": float(m_q2),
            "m_candidate": float(m_c),
            "home_score": float(out["home_score"]),
            "away_score": float(out["away_score"]),
            "actual_margin": actual,
            "err_if": err_if,
            "err_q2": err_q2,
            "err_candidate": err_c,
            "L_if": l_if,
            "L_q2": l_q2,
            "L_candidate": l_c,
            "L_candidate_minus_L_if": l_c - l_if,
            "in_full496": gid in full,
            "in_old437": gid in old,
            "in_new59": gid in new,
            "in_market96": mkt is not None,
            "kind": KIND,
        }
        if mkt is not None:
            m_mkt = float(mkt["home_margin"])
            row["market_home_margin"] = m_mkt
            row["L_market"] = signed_abs_loss(m_mkt, actual)
            row["L_if_minus_L_market"] = l_if - row["L_market"]
            row["L_candidate_minus_L_market"] = l_c - row["L_market"]
        rows.append(row)
    rows.sort(key=lambda item: str(item["game_id"]))
    if len(rows) != 496:
        raise ReportingAddendumRefuse(f"joined n={len(rows)} != 496")
    if {row["game_id"] for row in rows} != full:
        raise ReportingAddendumRefuse("joined IDs != full496 identity")
    return rows


def _metrics_for(
    rows: Sequence[Mapping[str, Any]],
    ids: Sequence[str],
    *,
    label: str,
) -> dict[str, Any]:
    by = {str(row["game_id"]): row for row in rows}
    chosen = [by[gid] for gid in ids]
    if len(chosen) != len(ids):
        raise ReportingAddendumRefuse(f"{label} missing joined rows")
    err_if = [float(row["err_if"]) for row in chosen]
    err_q2 = [float(row["err_q2"]) for row in chosen]
    err_c = [float(row["err_candidate"]) for row in chosen]
    diffs_c_if = [float(row["L_candidate_minus_L_if"]) for row in chosen]
    clusters = [f"{int(row['season'])}-{int(row['week']):02d}" for row in chosen]
    n_clusters = len(set(clusters))
    per_season: dict[str, dict[str, Any]] = {}
    for season, n in sorted(Counter(str(row["season"]) for row in chosen).items()):
        subset = [row for row in chosen if str(row["season"]) == season]
        per_season[season] = {
            "n": n,
            "mae_if": paired_mae([float(row["err_if"]) for row in subset]),
            "rmse_if": paired_rmse([float(row["err_if"]) for row in subset]),
            "bias_if": paired_bias([float(row["err_if"]) for row in subset]),
            "mae_q2": paired_mae([float(row["err_q2"]) for row in subset]),
            "rmse_q2": paired_rmse([float(row["err_q2"]) for row in subset]),
            "bias_q2": paired_bias([float(row["err_q2"]) for row in subset]),
            "mae_candidate": paired_mae([float(row["err_candidate"]) for row in subset]),
            "rmse_candidate": paired_rmse([float(row["err_candidate"]) for row in subset]),
            "bias_candidate": paired_bias([float(row["err_candidate"]) for row in subset]),
        }
    finite = all(
        math.isfinite(v)
        for row in chosen
        for v in (row["m_if"], row["m_q2"], row["m_candidate"], row["actual_margin"])
    )
    return {
        "label": label,
        "n": len(chosen),
        "n_by_season": dict(sorted(Counter(str(row["season"]) for row in chosen).items())),
        "n_clusters": n_clusters,
        "finite": finite,
        "mae_if": paired_mae(err_if),
        "rmse_if": paired_rmse(err_if),
        "bias_if": paired_bias(err_if),
        "mae_q2": paired_mae(err_q2),
        "rmse_q2": paired_rmse(err_q2),
        "bias_q2": paired_bias(err_q2),
        "mae_candidate": paired_mae(err_c),
        "rmse_candidate": paired_rmse(err_c),
        "bias_candidate": paired_bias(err_c),
        "per_season": per_season,
        "candidate_minus_if": {
            "mean_signed_abs_loss_diff": mean_stat(diffs_c_if),
            "bootstrap_game": bootstrap_ci(diffs_c_if, stat=mean_stat),
            "bootstrap_season_week": bootstrap_ci(diffs_c_if, stat=mean_stat, clusters=clusters),
            "B": BOOT_B,
            "seed": BOOT_SEED,
            "n_clusters": n_clusters,
            "method": "MEAN signed paired absolute-loss difference L_candidate−L_if",
        },
        "q2": "COMPLETED",
        "candidate": "COMPLETED",
        "label_status": LABEL,
        "kind": KIND,
    }


def _market_reporting(
    rows: Sequence[Mapping[str, Any]],
    market: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    ids = list(market["game_ids"])
    by = {str(row["game_id"]): row for row in rows}
    chosen = [by[gid] for gid in ids]
    if len(chosen) != INTERSECTION_N:
        raise ReportingAddendumRefuse(f"market joined n={len(chosen)} != 96")
    scored = (receipt.get("scored") or {}).get("market96") or {}
    diffs_c_if = [float(row["L_candidate_minus_L_if"]) for row in chosen]
    clusters = [f"{int(row['season'])}-{int(row['week']):02d}" for row in chosen]
    body = _metrics_for(rows, ids, label="market96")
    body.update(
        {
            "bytes_sha256": INTERSECTION_BYTES_SHA256,
            "identity_sha256": INTERSECTION_IDENTITY_SHA256,
            "reporting_class": reporting_class(len(chosen)),
            "n100_guidance": "n<100 DESCRIPTIVE_ONLY — not GREEN",
            "nfl_green": False,
            "sparse_limits": {
                "n": len(chosen),
                "n_clusters": len(set(clusters)),
                "min_n_report": MIN_N_REPORT,
                "n_lt_100": True,
                "note": "n=96 < 100 — DESCRIPTIVE_ONLY; cluster bootstrap can be sparse",
            },
            "candidate_minus_if_market96": {
                "mean_signed_abs_loss_diff": mean_stat(diffs_c_if),
                "bootstrap_game": bootstrap_ci(diffs_c_if, stat=mean_stat),
                "bootstrap_season_week": bootstrap_ci(diffs_c_if, stat=mean_stat, clusters=clusters),
                "B": BOOT_B,
                "seed": BOOT_SEED,
                "n_clusters": len(set(clusters)),
                "method": "MEAN signed paired absolute-loss difference L_candidate−L_if",
            },
            "cited_from_exec_receipt": {
                "path": EXEC_RECEIPT_PATH,
                "sha256": EXEC_RECEIPT_SHA256,
                "mean_signed_diff_if_vs_market": scored.get("mean_signed_diff_if_vs_market"),
                "mean_signed_diff_candidate_vs_market": scored.get(
                    "mean_signed_diff_candidate_vs_market"
                ),
                "bootstrap_game": scored.get("bootstrap_game"),
                "bootstrap_season_week": scored.get("bootstrap_season_week"),
                "bootstrap_game_candidate": scored.get("bootstrap_game_candidate"),
                "bootstrap_season_week_candidate": scored.get("bootstrap_season_week_candidate"),
            },
            "eval": None,
        }
    )
    return body


def _cite_exec_arm(receipt: Mapping[str, Any], name: str) -> dict[str, Any]:
    body = ((receipt.get("scored") or {}).get("if_q2_candidate") or {}).get(name) or {}
    return {
        "path": EXEC_RECEIPT_PATH,
        "sha256": EXEC_RECEIPT_SHA256,
        "n": body.get("n"),
        "n_by_season": body.get("n_by_season"),
        "mae_if": body.get("mae_if"),
        "rmse_if": body.get("rmse_if"),
        "bias_if": body.get("bias_if"),
        "mae_q2": body.get("mae_q2"),
        "rmse_q2": body.get("rmse_q2"),
        "bias_q2": body.get("bias_q2"),
        "mae_candidate": body.get("mae_candidate"),
        "rmse_candidate": body.get("rmse_candidate"),
        "bias_candidate": body.get("bias_candidate"),
    }


def build_reporting_addendum(*, root: Path | None = None, write: bool = True) -> dict[str, Any]:
    repo = _repo_root(root)
    _assert_exec_untouched(repo)
    receipt = json.loads((repo / EXEC_RECEIPT_PATH).read_text(encoding="utf-8"))
    forecasts = _load_completed(repo)
    splits = _load_splits(repo)
    market = _load_market(repo)
    outcomes = _load_schedule_scores(repo)
    rows = _join_rows(forecasts, outcomes, splits, market)
    join_payload = {
        "schema_version": "nfl-t5165u-r5-joined-rows-v1",
        "ticket": TICKET,
        "kind": KIND,
        "label": LABEL,
        "cert_candidate": CERT_CANDIDATE,
        "n": len(rows),
        "schedule_path": SCHEDULE_PATH,
        "schedule_sha256": SCHEDULE_SHA256,
        "completed_forecasts_path": COMPLETED_FORECASTS_PATH,
        "completed_forecasts_sha256": COMPLETED_FORECASTS_SHA256,
        "forecasts_sha256": FORECASTS_SHA256,
        "exec_bind_id": EXEC_BIND_ID,
        "exec_receipt_sha256": EXEC_RECEIPT_SHA256,
        "not_persisted_at_exec": True,
        "rows": rows,
    }
    join_sha = sha256_text(json.dumps(join_payload, sort_keys=True, separators=(",", ":"), default=str))
    arms = {
        name: _metrics_for(rows, splits[name]["game_ids"], label=name)
        for name in ("full496", "old437", "new59")
    }
    for name, body in arms.items():
        cited = _cite_exec_arm(receipt, name)
        if cited.get("n") != body["n"]:
            raise ReportingAddendumRefuse(f"{name} n drifted vs EXEC RECEIPT")
        if abs(float(cited["mae_if"]) - float(body["mae_if"])) > 1e-12:
            raise ReportingAddendumRefuse(f"{name} mae_if drifted vs EXEC RECEIPT")
        body["cited_exec_overall"] = cited
    market_body = _market_reporting(rows, market, receipt)
    report = {
        "schema_version": SCHEMA,
        "ticket": TICKET,
        "owner_clear_sha8": OWNER_CLEAR_SHA8,
        "cos_order_sha8": COS_ORDER_SHA8,
        "tracker": TRACKER,
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
            "no new scientific look — reporting-arithmetic completion under t5165u/46283 "
            "on already-consumed frozen rows"
        ),
        "exec_tip": EXEC_TIP,
        "exec_stamp": EXEC_STAMP,
        "exec_bind_id": EXEC_BIND_ID,
        "exec_one_run_status": "CONSUMED",
        "exec_one_run_path": EXEC_ONE_RUN_PATH,
        "exec_one_run_sha256": EXEC_ONE_RUN_SHA256,
        "exec_receipt_path": EXEC_RECEIPT_PATH,
        "exec_receipt_sha256": EXEC_RECEIPT_SHA256,
        "joined_path": str(OUT_DIR / JOIN_NAME),
        "joined_sha256": join_sha,
        "joined_n": len(rows),
        "joined_not_persisted_at_exec": True,
        "if_q2_candidate": arms,
        "market96": market_body,
        "consistency": {
            "full496_n": arms["full496"]["n"],
            "old437_n": arms["old437"]["n"],
            "new59_n": arms["new59"]["n"],
            "market96_n": market_body["n"],
            "old_plus_new": arms["old437"]["n"] + arms["new59"]["n"],
            "finite_full496": arms["full496"]["finite"],
            "finite_old437": arms["old437"]["finite"],
            "finite_new59": arms["new59"]["finite"],
            "finite_market96": market_body["finite"],
            "mae_if_matches_exec_receipt": True,
        },
        "pins": reporting_input_pin_bundle(),
        "runner_code_hashes": reporting_code_hashes(repo),
        "runner_code_sha256": reporting_code_sha256(repo),
        "runner_input_sha256": reporting_input_sha256(),
        "eval": None,
        "scoring": None,
    }
    canonical = {k: v for k, v in report.items() if k not in {"hashes", "runtime"}}
    report["hashes"] = {
        "code_sha256": report["runner_code_sha256"],
        "input_sha256": report["runner_input_sha256"],
        "join_sha256": join_sha,
        "output_sha256": sha256_text(
            json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
        ),
    }
    report["runtime"] = {"interpreter": "python3", "invoked_one_exec": False}
    if write:
        dest = repo / OUT_DIR
        dest.mkdir(parents=True, exist_ok=True)
        (dest / JOIN_NAME).write_text(json.dumps(join_payload, indent=2) + "\n", encoding="utf-8")
        (dest / REPORT_NAME).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        _assert_exec_untouched(repo)
    return report
