"""t5141u R3-DEV-CALIBRATION — bounded exploratory DEV experiment.

CERT=0. DRAFT≠merge. NOT EVAL. NOT clean confirmation.
DEV outcomes on the sealed 437 rows are ALREADY CONSUMED.
RETRO_FIT / forecast-vintage limitations remain; calibration cannot repair them.
R2-C stays DATA_COVERAGE_BLOCKED. G5 unchanged. No Stage C / merge / deploy.

Chain: implement + tests → freeze protocol/code/input/identity hashes
BEFORE any fit → STOP for Alex pre-computation GO → one diagnostic
execution only after that GO is relayed.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping, Sequence

from .dev_research import LABEL, DevResearchRefuse, _record_body, write_dev_research_record
from .dev_research_matched72 import MATCHED72_N, SEALED_MATCHED72_SHA256, load_matched72_ids
from .evaluator import (
    BOOT_B,
    BOOT_SEED,
    EvalRefuse,
    bootstrap_ci,
    mean_stat,
    paired_bias,
    paired_mae,
    paired_rmse,
    reporting_class,
    signed_abs_loss,
)
from .metric_cohorts import DEV_METRIC_SPLIT
from .outcome_gate import (
    FIRST_CASE_FILE_SHA256,
    FIRST_CASE_GAME_ID,
    FIRST_CASE_RECORD_SHA256,
    refuse_overwrite_first_case_record,
    refuse_preserved_t5116u_path,
)
from .q2 import SEALED_SEASONS, T5107U_DEV_SEASONS
from .r2_market_e2e import (
    R2A_DIR,
    SEALED_MANIFEST_SHA256,
    SEALED_QUOTES_SHA256,
    join_market_points,
    load_conflicts,
    load_sealed_quotes,
    sha256_file,
)

SCHEMA = "nfl-t5141u-r3-dev-calibration-v1"
CERT_CANDIDATE = 0
SPLIT_DEV = "dev_reg"
COHORT = "r3_dev_calibration_437"
EXPERIMENT = "R3-DEV-CALIBRATION"
TICKET = "t5141u"

DEV437_N = 437
DEV437_N_2020 = 210
DEV437_N_2021 = 227
MATCHED37_N = 37
NORMALIZED_94_N = 94
NORMALIZED_94_TIP_REFUSED = "0a49afa3"

SEALED_DEV437_FILE_SHA256 = (
    "66c3bde18fd6b1a4766f1001403deb68b9f625ccd00372f280f187ef95a54e50"
)
SEALED_DEV437_RECORD_SHA256 = (
    "0550ef9b498a2240919d8cf570ccb7c94b67f6815ba3625789901f8390143637"
)
OWNER_CLEAR_SHA8 = "714ced10"
COS_ORDER_SHA8 = "1155f43f"
PREFLIGHT_SHA8 = "a23e01dd"

BLEND_REPRODUCE_TOL = 1e-9
W_GRID = tuple(round(i / 100.0, 2) for i in range(101))
HALF = 0.5
REQUIRED_FIELDS = ("game_id", "season", "week", "actual_margin", "m_if", "m_challenger")

ALEX_PRECOMP_GO_TOKEN = "t5141u-alex-precomp-go"
GO_ENV = "T5141U_ALEX_PRECOMP_GO"

_PKG_ROOT = Path(__file__).resolve().parents[5]
PARENT_OPS = _PKG_ROOT / "data/ops/nfl-forecast-builder-t5107u"
ISOLATED_OPS = _PKG_ROOT / "data/ops/nfl-t5141u-r3-dev-calibration"
DEV437_PATH = PARENT_OPS / "DEV_RESEARCH_t5125u_R2B2_437.json"
MATCHED72_PATH = R2A_DIR / "DEV_MATCHED_GAME_IDS.json"
DEFAULT_DEST = ISOLATED_OPS / "DEV_RESEARCH_t5141u_R3_DEV_CALIBRATION.json"
C3_SELECTION_DEST = ISOLATED_OPS / "C3_SELECTION_FREEZE.json"
STOP_DEST = ISOLATED_OPS / "STOP_AWAITING_ALEX_PRECOMP_GO.json"

Q2_LINEAGE_NOTE = (
    "DEV_RESEARCH_t5125u_R2B2_437.json has no separate m_q2 column. "
    "m_challenger on these rows is the frozen 50/50 blend "
    "x(0.5)=(1-0.5)*IF_margin + 0.5*Q2_complete_margin from prior R2-B2. "
    "Algebraic recovery Q2=2*m_challenger-m_if is permitted solely after that "
    "lineage is documented. Recovered Q2 is NOT a newly generated forecast "
    "and is not an original-Q2 / 2017 look or IF/Q2 refit."
)

OUTCOMES_ALREADY_CONSUMED_NOTE = (
    "These DEV outcomes are ALREADY CONSUMED. RETRO_FIT / forecast-vintage "
    "limitations remain. Calibration cannot repair them. NOT EVAL. CERT=0."
)

MARKET_N37_NOTE = (
    "n=37 is the 2021 intersection of the OLD matched72 list (9f754b0e). "
    "Selection-limited. Not representative market validation. "
    "Do not substitute normalized 94. Do not invent probabilities."
)

FORBIDDEN_DEST_NAMES = frozenset(
    {
        "ONE_RUN.json",
        "ONE_EXEC_RESULT_t5116u.json",
        "CURSOR_ONE_EXEC_RESULT_t5116u.md",
        "DEV_RESEARCH_t5119u_R2B.json",
        "DEV_RESEARCH_t5125u_R2B2_437.json",
        "DEV_RESEARCH_t5137u_MATCHED72.json",
        "MARKET_E2E_R2B_CONSUME.json",
        "R2B_CONSUME.json",
        "ADMISSIBLE_QUOTES.jsonl",
        "COVERAGE_MANIFEST.json",
        "OWNED_COVERAGE_t5119u.json",
        "R2A_COVERAGE_MANIFEST.json",
        "DEV_MATCHED_GAME_IDS.json",
    }
)

OUTPUT_CONTRACT = (
    "schema_version",
    "label",
    "metric_split",
    "split",
    "cohort",
    "experiment",
    "cert_candidate",
    "eval",
    "scoring",
    "look",
    "exec_scoring",
    "one_run_claim",
    "eval_invoked",
    "r2_eval_called",
    "winner",
    "selected_from_2021",
    "retune_from_2021",
    "outcomes_already_consumed",
    "g5_status",
    "g5_loosened",
    "n",
    "n_by_season",
    "input_hashes",
    "q2_lineage",
    "c3_selection",
    "training_2020",
    "diagnostic_2021",
    "market_n37",
    "record_sha256",
)


class CalibrationRefuse(DevResearchRefuse):
    """Fail-closed R3 DEV calibration. Not an EVAL look. Not a claim."""


@dataclass(frozen=True)
class CalibRow:
    game_id: str
    season: int
    week: int
    actual_margin: float
    m_if: float
    m_challenger: float
    m_q2: float
    q2_source: str

    def season_week(self) -> str:
        return f"{self.season}-{self.week:02d}"


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _repo_rel(path: Path) -> str:
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(_PKG_ROOT.resolve()))
    except ValueError:
        return str(resolved)


def _ids_sha256(game_ids: Sequence[str]) -> str:
    return hashlib.sha256(
        json.dumps({"game_ids": list(game_ids)}, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def protocol_spec() -> dict[str, Any]:
    """Frozen protocol. Hashed before any C2/C3 fit."""
    return {
        "schema_version": SCHEMA,
        "ticket": TICKET,
        "experiment": EXPERIMENT,
        "cert_candidate": CERT_CANDIDATE,
        "eval": None,
        "label": LABEL,
        "authority": {
            "owner_clear_sha8": OWNER_CLEAR_SHA8,
            "cos_order_sha8": COS_ORDER_SHA8,
            "preflight_sha8": PREFLIGHT_SHA8,
        },
        "model": {
            "x_w": "x(w)=(1-w)*IF_margin + w*Q2_complete_margin (home-away points)",
            "extra_hfa": False,
            "inputs_already_include_intercept_hfa": True,
            "blend_reproduce_tol": BLEND_REPRODUCE_TOL,
            "q2_recovery": "Q2=2*m_challenger-m_if after lineage that m_challenger is frozen 50/50",
            "q2_not_newly_generated": True,
            "no_imputation": True,
            "no_original_q2_2017_look": True,
            "no_if_q2_refit": True,
        },
        "arms": {
            "C0": "unchanged IF (m_if)",
            "C1": "unchanged frozen 50/50 (m_challenger = x(0.5))",
            "C2": "x(0.5)+b ; b=median(actual_margin-x(0.5)) fit on 2020 only",
            "C3": (
                "w in {0,0.01,...,1}; b(w)=median(actual-x(w)) on 2020 only; "
                "select minimum unrounded 2020 MAE; exact ties prefer w closest "
                "to 0.5 then smaller w; freeze (w,b) and ALL candidate training "
                "losses BEFORE any 2021 calculation"
            ),
            "no_2021_or_market_tuning": True,
            "no_extra_families": True,
        },
        "diagnostic_2021": {
            "n": DEV437_N_2021,
            "comparisons": ["C2 vs C0", "C2 vs C1", "C3 vs C0", "C3 vs C1"],
            "metrics": ["MAE", "RMSE", "mean_signed_bias", "per_game", "paired_mean_signed_abs_loss_diff"],
            "intervals": "game + season-week cluster 95% CI; B=10000 seed 20261101",
            "interval_conditioning": "conditional_on_fitted_parameters_not_full_fitting_uncertainty",
            "negative_diff_favors": "calibrated arm",
            "crossing_zero_or_mixed": "INCONCLUSIVE",
            "no_winner_selection": True,
            "no_refit_from_2021": True,
            "training_2020_reported_separately": True,
        },
        "market_n37": {
            "n": MATCHED37_N,
            "source": "matched72 ∩ 2021",
            "matched72_sha256": SEALED_MATCHED72_SHA256,
            "quotes_sha256": SEALED_QUOTES_SHA256,
            "manifest_sha256": SEALED_MANIFEST_SHA256,
            "selection_limited": True,
            "representative_market_validation": False,
            "normalized_94_refused": NORMALIZED_94_TIP_REFUSED,
            "no_invented_probabilities": True,
            "same_cutoff_dk_fd_sign_rules_as_market_e2e": True,
        },
        "rng": {"bootstrap_B": BOOT_B, "bootstrap_seed": BOOT_SEED},
        "stops": [
            "No EVAL bind/claim",
            "No post-result retune",
            "No gate waiver",
            "No Stage C release",
            "No production merge/deploy",
            "No enterprise/edge claim",
            "R2-C remains DATA_COVERAGE_BLOCKED",
            "G5 unchanged",
        ],
        "outcomes_already_consumed": True,
        "retro_fit_limitations_preserved": True,
    }


def require_alex_precomp_go(go: str | None = None) -> None:
    token = go if go is not None else os.environ.get(GO_ENV)
    if token != ALEX_PRECOMP_GO_TOKEN:
        raise CalibrationRefuse(
            "STOP — awaiting Alex pre-computation GO; 2021 diagnostic not executed"
        )


def _refuse_dest(path: Path | None) -> None:
    if path is None:
        return
    dest = Path(path)
    if dest.name in FORBIDDEN_DEST_NAMES:
        raise CalibrationRefuse(f"refusing write to preserved / parent file {dest.name}")
    try:
        refuse_preserved_t5116u_path(dest)
        refuse_overwrite_first_case_record(dest)
    except Exception as exc:
        raise CalibrationRefuse(str(exc)) from exc
    resolved = dest.resolve()
    if resolved.parent.resolve() == R2A_DIR.resolve():
        raise CalibrationRefuse("refusing rewrite of R2-A coverage directory")
    if resolved.parent.resolve() == PARENT_OPS.resolve():
        raise CalibrationRefuse("refusing write into parent R2 ops directory — isolated R3 only")


def refuse_eval_bind(eval_payload: Any = None) -> None:
    if eval_payload not in (None, {}):
        raise CalibrationRefuse("EVAL bind refused — R3 is DEV_RESEARCH exploratory calibration")


def refuse_normalized_94(game_ids: Sequence[str]) -> None:
    if len(game_ids) == NORMALIZED_94_N:
        raise CalibrationRefuse(
            f"refusing silent #694 normalized 94-DEV substitution ({NORMALIZED_94_TIP_REFUSED})"
        )


def refuse_imputation(row: Mapping[str, Any], *, where: str) -> None:
    missing = [name for name in REQUIRED_FIELDS if row.get(name) in (None, "")]
    if missing:
        raise CalibrationRefuse(f"missing required fields {missing} at {where} — no imputation")
    for name in ("actual_margin", "m_if", "m_challenger"):
        if not _finite(row.get(name)):
            raise CalibrationRefuse(f"nonfinite {name} at {where} — no imputation")
    season = int(row["season"])
    if season in SEALED_SEASONS:
        raise CalibrationRefuse(f"refusing sealed 2022–26 scoring {row.get('game_id')}")
    if season not in T5107U_DEV_SEASONS:
        raise CalibrationRefuse(f"season {season} is not DEV 2020/2021")


def blend_x(w: float, m_if: float, m_q2: float, *, extra_hfa: float = 0.0) -> float:
    """x(w)=(1-w)*IF + w*Q2. Inputs already include intercept/HFA — add none."""
    if extra_hfa != 0.0:
        raise CalibrationRefuse("add NO separate HFA; inputs already include intercept/HFA")
    if not _finite(w) or not _finite(m_if) or not _finite(m_q2):
        raise CalibrationRefuse("nonfinite blend inputs — no imputation")
    if w < 0.0 or w > 1.0:
        raise CalibrationRefuse(f"w={w} outside [0,1]")
    return (1.0 - float(w)) * float(m_if) + float(w) * float(m_q2)


def recover_q2_from_frozen_blend(m_if: float, m_challenger: float) -> float:
    if not _finite(m_if) or not _finite(m_challenger):
        raise CalibrationRefuse("nonfinite IF/blend — cannot recover Q2")
    return 2.0 * float(m_challenger) - float(m_if)


def verify_frozen_half_half(m_if: float, m_q2: float, m_challenger: float) -> float:
    reconstructed = blend_x(HALF, m_if, m_q2)
    residual = abs(reconstructed - float(m_challenger))
    if residual > BLEND_REPRODUCE_TOL:
        raise CalibrationRefuse(
            f"frozen 50/50 identity failed 1e-9 check: residual={residual}"
        )
    return residual


def break_c3_ties(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Min unrounded 2020 MAE; ties → w closest to 0.5 then smaller w."""
    if not candidates:
        raise CalibrationRefuse("C3 candidate list empty")
    ranked = sorted(
        candidates,
        key=lambda c: (float(c["mae_2020"]), abs(float(c["w"]) - HALF), float(c["w"])),
    )
    return dict(ranked[0])


def select_c3(
    train_rows: Sequence[CalibRow],
    *,
    holdout_rows: Sequence[CalibRow] | None = None,
    allow_non_2020: bool = False,
) -> dict[str, Any]:
    """Fit b(w) on 2020 only. Freeze all candidate losses before 2021."""
    if holdout_rows:
        raise CalibrationRefuse("C3 selection must not see 2021/holdout — freeze-before-2021")
    if not train_rows:
        raise CalibrationRefuse("C3 train rows empty")
    if not allow_non_2020 and any(row.season != 2020 for row in train_rows):
        raise CalibrationRefuse("C3 fit is 2020 only — refuse non-2020 train rows")
    candidates: list[dict[str, Any]] = []
    for w in W_GRID:
        xs = [blend_x(w, row.m_if, row.m_q2) for row in train_rows]
        resid = [row.actual_margin - x for row, x in zip(train_rows, xs)]
        b = float(median(resid))
        preds = [x + b for x in xs]
        errors = [p - row.actual_margin for p, row in zip(preds, train_rows)]
        candidates.append(
            {
                "w": w,
                "b": b,
                "mae_2020": paired_mae(errors),
                "rmse_2020": paired_rmse(errors),
                "bias_2020": paired_bias(errors),
            }
        )
    chosen = break_c3_ties(candidates)
    return {
        "w": chosen["w"],
        "b": chosen["b"],
        "mae_2020": chosen["mae_2020"],
        "grid": list(W_GRID),
        "n_candidates": len(candidates),
        "candidates": candidates,
        "tie_break": "min unrounded 2020 MAE; then |w-0.5|; then smaller w",
        "frozen_before_2021": True,
        "trained_seasons": sorted({row.season for row in train_rows}),
        "n_train": len(train_rows),
    }


def fit_c2(train_rows: Sequence[CalibRow]) -> dict[str, Any]:
    if not train_rows:
        raise CalibrationRefuse("C2 train rows empty")
    if any(row.season != 2020 for row in train_rows):
        raise CalibrationRefuse("C2 fit is 2020 only")
    xs = [row.m_challenger for row in train_rows]
    resid = [row.actual_margin - x for row, x in zip(train_rows, xs)]
    b = float(median(resid))
    preds = [x + b for x in xs]
    errors = [p - row.actual_margin for p, row in zip(preds, train_rows)]
    return {
        "w": HALF,
        "b": b,
        "mae_2020": paired_mae(errors),
        "rmse_2020": paired_rmse(errors),
        "bias_2020": paired_bias(errors),
        "n_train": len(train_rows),
        "frozen_before_2021": True,
    }


def predict_arm(row: CalibRow, arm: str, *, c2: Mapping[str, Any], c3: Mapping[str, Any]) -> float:
    if arm == "C0":
        return float(row.m_if)
    if arm == "C1":
        return float(row.m_challenger)
    if arm == "C2":
        return float(row.m_challenger) + float(c2["b"])
    if arm == "C3":
        return blend_x(float(c3["w"]), row.m_if, row.m_q2) + float(c3["b"])
    raise CalibrationRefuse(f"unknown arm {arm}")


def _arm_block(rows: Sequence[CalibRow], preds: Sequence[float], *, name: str) -> dict[str, Any]:
    if len(rows) != len(preds):
        raise CalibrationRefuse("arm predictions not aligned to rows")
    errors = [p - row.actual_margin for p, row in zip(preds, rows)]
    return {
        "arm": name,
        "n": len(rows),
        "mae": paired_mae(errors),
        "rmse": paired_rmse(errors),
        "bias": paired_bias(errors),
        "errors": errors,
        "preds": list(preds),
    }


def _paired_block(
    rows: Sequence[CalibRow],
    pred_a: Sequence[float],
    pred_b: Sequence[float],
    *,
    name: str,
) -> dict[str, Any]:
    diffs = [
        signed_abs_loss(a, row.actual_margin) - signed_abs_loss(b, row.actual_margin)
        for a, b, row in zip(pred_a, pred_b, rows)
    ]
    clusters = [row.season_week() for row in rows]
    game = bootstrap_ci(diffs, stat=mean_stat, b=BOOT_B, seed=BOOT_SEED)
    week = bootstrap_ci(diffs, stat=mean_stat, b=BOOT_B, seed=BOOT_SEED, clusters=clusters)
    return {
        "name": name,
        "n": len(rows),
        "mean_signed_abs_loss_diff": mean_stat(diffs),
        "diffs": diffs,
        "bootstrap_game": game,
        "bootstrap_season_week": week,
        "negative_favors": name.split("_vs_")[0],
        "interval_conditioning": "conditional_on_fitted_parameters_not_full_fitting_uncertainty",
        "crossing_zero_note": "CI crossing zero / mixed = INCONCLUSIVE (not retune permission)",
    }


def score_arms(
    rows: Sequence[CalibRow],
    *,
    c2: Mapping[str, Any],
    c3: Mapping[str, Any],
    market_by_id: Mapping[str, float] | None = None,
    require_c3_frozen: bool = True,
) -> dict[str, Any]:
    if require_c3_frozen and not c3.get("frozen_before_2021"):
        raise CalibrationRefuse("C3 selection was not frozen before 2021 scoring")
    pred = {arm: [predict_arm(row, arm, c2=c2, c3=c3) for row in rows] for arm in ("C0", "C1", "C2", "C3")}
    arms = {arm: _arm_block(rows, pred[arm], name=arm) for arm in pred}
    compares = {
        "C2_vs_C0": _paired_block(rows, pred["C2"], pred["C0"], name="C2_vs_C0"),
        "C2_vs_C1": _paired_block(rows, pred["C2"], pred["C1"], name="C2_vs_C1"),
        "C3_vs_C0": _paired_block(rows, pred["C3"], pred["C0"], name="C3_vs_C0"),
        "C3_vs_C1": _paired_block(rows, pred["C3"], pred["C1"], name="C3_vs_C1"),
    }
    games = []
    for i, row in enumerate(rows):
        item = {
            "game_id": row.game_id,
            "season": row.season,
            "week": row.week,
            "actual_margin": row.actual_margin,
            "m_if": row.m_if,
            "m_challenger": row.m_challenger,
            "pred_C0": pred["C0"][i],
            "pred_C1": pred["C1"][i],
            "pred_C2": pred["C2"][i],
            "pred_C3": pred["C3"][i],
            "err_C0": pred["C0"][i] - row.actual_margin,
            "err_C1": pred["C1"][i] - row.actual_margin,
            "err_C2": pred["C2"][i] - row.actual_margin,
            "err_C3": pred["C3"][i] - row.actual_margin,
        }
        if market_by_id is not None:
            if row.game_id not in market_by_id or not _finite(market_by_id[row.game_id]):
                raise CalibrationRefuse(f"market margin missing/nonfinite for {row.game_id} — no imputation")
            mkt = float(market_by_id[row.game_id])
            item["m_market"] = mkt
            item["err_market"] = mkt - row.actual_margin
        games.append(item)
    out: dict[str, Any] = {
        "n": len(rows),
        "n_by_season": _count_seasons(rows),
        "arms": {k: {kk: vv for kk, vv in v.items() if kk not in {"errors", "preds"}} for k, v in arms.items()},
        "comparisons": {
            k: {kk: vv for kk, vv in v.items() if kk != "diffs"} for k, v in compares.items()
        },
        "games": games,
        "winner": None,
        "selected_from_holdout": False,
    }
    if market_by_id is not None:
        mkt_preds = [float(market_by_id[row.game_id]) for row in rows]
        out["arms"]["market"] = {
            kk: vv for kk, vv in _arm_block(rows, mkt_preds, name="market").items() if kk not in {"errors", "preds"}
        }
        out["comparisons"]["C0_vs_market"] = {
            kk: vv for kk, vv in _paired_block(rows, pred["C0"], mkt_preds, name="C0_vs_market").items() if kk != "diffs"
        }
        out["comparisons"]["C1_vs_market"] = {
            kk: vv for kk, vv in _paired_block(rows, pred["C1"], mkt_preds, name="C1_vs_market").items() if kk != "diffs"
        }
        out["comparisons"]["C2_vs_market"] = {
            kk: vv for kk, vv in _paired_block(rows, pred["C2"], mkt_preds, name="C2_vs_market").items() if kk != "diffs"
        }
        out["comparisons"]["C3_vs_market"] = {
            kk: vv for kk, vv in _paired_block(rows, pred["C3"], mkt_preds, name="C3_vs_market").items() if kk != "diffs"
        }
    return out


def _count_seasons(rows: Iterable[CalibRow | Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        season = str(int(row.season if isinstance(row, CalibRow) else row["season"]))
        counts[season] = counts.get(season, 0) + 1
    return dict(sorted(counts.items()))


def _record_sha_without_field(record: Mapping[str, Any]) -> str:
    body = dict(record)
    body.pop("record_sha256", None)
    return _canonical_sha256(body)


def load_dev437_rows(
    path: Path | None = None,
    *,
    expect_file_sha256: str | None = None,
    expect_record_sha256: str | None = None,
) -> tuple[list[CalibRow], dict[str, Any]]:
    dest = Path(path) if path else DEV437_PATH
    if not dest.is_file():
        raise CalibrationRefuse(f"DEV437 missing: {dest}")
    live = sha256_file(dest)
    expect_file = expect_file_sha256 or SEALED_DEV437_FILE_SHA256
    if dest.resolve() == DEV437_PATH.resolve() and live != SEALED_DEV437_FILE_SHA256:
        raise CalibrationRefuse("DEV437 file hash mismatch vs sealed 66c3bde1")
    if dest.resolve() != DEV437_PATH.resolve() and expect_file_sha256 and live != expect_file:
        raise CalibrationRefuse("injected DEV437 file hash mismatch")
    record = json.loads(dest.read_text(encoding="utf-8"))
    if record.get("label") != LABEL:
        raise CalibrationRefuse("DEV437 label must be DEV_RESEARCH")
    if record.get("eval") is not None:
        raise CalibrationRefuse("DEV437 must not carry eval")
    expect_rec = expect_record_sha256 or SEALED_DEV437_RECORD_SHA256
    live_rec = record.get("record_sha256")
    recomputed = _record_sha_without_field(record)
    if dest.resolve() == DEV437_PATH.resolve():
        if live_rec != SEALED_DEV437_RECORD_SHA256:
            raise CalibrationRefuse("DEV437 record_sha256 mismatch vs sealed 0550ef9b")
        if recomputed != SEALED_DEV437_RECORD_SHA256:
            raise CalibrationRefuse("DEV437 record body hash drifted from 0550ef9b")
    elif expect_record_sha256 and live_rec != expect_rec:
        raise CalibrationRefuse("injected DEV437 record_sha256 mismatch")
    n_by = record.get("n_by_season") or {}
    if dest.resolve() == DEV437_PATH.resolve():
        if int(record.get("n") or 0) != DEV437_N:
            raise CalibrationRefuse(f"DEV437 n pin {DEV437_N} failed")
        if int(n_by.get("2020") or 0) != DEV437_N_2020 or int(n_by.get("2021") or 0) != DEV437_N_2021:
            raise CalibrationRefuse("DEV437 n_by_season must be 210/227")
    games = list(record.get("games") or [])
    if not games:
        raise CalibrationRefuse("DEV437 games empty")
    rows: list[CalibRow] = []
    seen: set[str] = set()
    residuals: list[float] = []
    for raw in games:
        refuse_imputation(raw, where=str(raw.get("game_id") or "?"))
        gid = str(raw["game_id"])
        if gid in seen:
            raise CalibrationRefuse(f"duplicate game_id {gid}")
        seen.add(gid)
        m_if = float(raw["m_if"])
        m_c = float(raw["m_challenger"])
        if raw.get("m_q2") not in (None, ""):
            if not _finite(raw.get("m_q2")):
                raise CalibrationRefuse(f"nonfinite supplied m_q2 at {gid} — no imputation")
            m_q2 = float(raw["m_q2"])
            q2_source = "supplied_column_verified_against_frozen_blend"
        else:
            m_q2 = recover_q2_from_frozen_blend(m_if, m_c)
            q2_source = "algebraic_recovery_Q2_eq_2_blend_minus_IF"
        residuals.append(verify_frozen_half_half(m_if, m_q2, m_c))
        rows.append(
            CalibRow(
                game_id=gid,
                season=int(raw["season"]),
                week=int(raw["week"]),
                actual_margin=float(raw["actual_margin"]),
                m_if=m_if,
                m_challenger=m_c,
                m_q2=m_q2,
                q2_source=q2_source,
            )
        )
    meta = {
        "path": _repo_rel(dest),
        "file_sha256": live,
        "record_sha256": live_rec,
        "n": len(rows),
        "n_by_season": _count_seasons(rows),
        "q2_lineage": {
            "note": Q2_LINEAGE_NOTE,
            "json_lacks_m_q2": all(raw.get("m_q2") in (None, "") for raw in games),
            "recovery": "Q2=2*m_challenger-m_if",
            "not_newly_generated_forecast": True,
            "max_abs_blend_residual": max(residuals) if residuals else None,
            "n_checked": len(residuals),
            "tol": BLEND_REPRODUCE_TOL,
            "outcomes_already_consumed": True,
        },
        "outcomes_already_consumed": True,
        "eval": None,
    }
    return rows, meta


def freeze_matched37_ids(matched72_path: Path | None = None) -> list[str]:
    ids = load_matched72_ids(matched72_path)
    refuse_normalized_94(ids)
    if len(ids) != MATCHED72_N:
        raise CalibrationRefuse("matched72 pin drifted")
    ids37 = [gid for gid in ids if gid.startswith("2021_")]
    if len(ids37) != MATCHED37_N or len(set(ids37)) != MATCHED37_N:
        raise CalibrationRefuse(
            f"matched72∩2021 expected n={MATCHED37_N}; got {len(ids37)} unique={len(set(ids37))}"
        )
    return ids37


def freeze_market_n37_identity(
    ids37: Sequence[str],
    *,
    quotes_path: Path | None = None,
    rows_by_id: Mapping[str, CalibRow] | None = None,
) -> dict[str, Any]:
    refuse_normalized_94(ids37)
    if len(ids37) != MATCHED37_N:
        raise CalibrationRefuse("market identity must be the frozen n=37 list")
    quotes = load_sealed_quotes(quotes_path)
    conflicts = load_conflicts()
    join = join_market_points(list(ids37), quotes, conflicts=conflicts)
    if join["joined_n"] != MATCHED37_N or not join["bind_ready"] or join["missing_n"]:
        raise CalibrationRefuse(
            f"market n=37 join incomplete: joined={join['joined_n']} missing={join['missing_game_ids']}"
        )
    points = list(join["points"])
    if [p["game_id"] for p in points] != list(ids37):
        raise CalibrationRefuse("market points order/identity drifted from frozen 37 IDs")
    for point in points:
        if not _finite(point.get("market_margin")):
            raise CalibrationRefuse(f"nonfinite market_margin for {point.get('game_id')} — no imputation")
        if rows_by_id is not None and point["game_id"] not in rows_by_id:
            raise CalibrationRefuse(f"market id {point['game_id']} not in DEV437 2021 identities")
    return {
        "n": MATCHED37_N,
        "game_ids": list(ids37),
        "ids_sha256": _ids_sha256(ids37),
        "points": [
            {
                "game_id": p["game_id"],
                "season": p.get("season"),
                "week": p.get("week"),
                "market_margin": p["market_margin"],
                "spread_home": p.get("spread_home"),
                "books_used": p.get("books_used"),
                "book_count": p.get("book_count"),
            }
            for p in points
        ],
        "quotes_sha256": SEALED_QUOTES_SHA256,
        "manifest_sha256": SEALED_MANIFEST_SHA256,
        "matched72_sha256": SEALED_MATCHED72_SHA256,
        "selection_limited": True,
        "representative_market_validation": False,
        "note": MARKET_N37_NOTE,
        "frozen_before_fit": True,
        "no_invented_probabilities": True,
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> str:
    _refuse_dest(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    text = json.dumps(payload, indent=2, default=str) + "\n"
    try:
        fd = os.open(str(path), flags, 0o644)
    except FileExistsError as exc:
        raise CalibrationRefuse(f"exclusive create refused — {path.name} exists") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    return sha256_file(path)


def build_pre_fit_freeze_package(
    dest_dir: Path | None = None,
    *,
    dev437_path: Path | None = None,
    matched72_path: Path | None = None,
    quotes_path: Path | None = None,
    include_market_join: bool = True,
) -> dict[str, Any]:
    """Pin protocol / code / input / identity hashes. Does not fit C2/C3."""
    out_dir = Path(dest_dir) if dest_dir else ISOLATED_OPS
    if out_dir.resolve() == PARENT_OPS.resolve() or out_dir.resolve() == R2A_DIR.resolve():
        raise CalibrationRefuse("freeze package must be an isolated R3 directory")
    rows, meta = load_dev437_rows(dev437_path)
    ids_all = [row.game_id for row in rows]
    ids_2020 = [row.game_id for row in rows if row.season == 2020]
    ids_2021 = [row.game_id for row in rows if row.season == 2021]
    if len(ids_2020) != DEV437_N_2020 or len(ids_2021) != DEV437_N_2021:
        if Path(dev437_path or DEV437_PATH).resolve() == DEV437_PATH.resolve():
            raise CalibrationRefuse("DEV437 season counts drifted from 210/227")
    ids37 = freeze_matched37_ids(matched72_path)
    missing37 = [gid for gid in ids37 if gid not in set(ids_2021)]
    if missing37:
        raise CalibrationRefuse(f"matched72∩2021 IDs missing from DEV437 2021: {missing37[:5]}")
    market = (
        freeze_market_n37_identity(
            ids37,
            quotes_path=quotes_path,
            rows_by_id={row.game_id: row for row in rows if row.season == 2021},
        )
        if include_market_join
        else {
            "n": MATCHED37_N,
            "game_ids": list(ids37),
            "ids_sha256": _ids_sha256(ids37),
            "frozen_before_fit": True,
            "points": None,
            "note": MARKET_N37_NOTE,
        }
    )
    protocol = protocol_spec()
    code_path = Path(__file__).resolve()
    identity = {
        "frozen_before_fit": True,
        "dev437_n": len(ids_all),
        "dev437_game_ids": ids_all,
        "dev437_ids_sha256": _ids_sha256(ids_all),
        "season_2020_n": len(ids_2020),
        "season_2020_game_ids": ids_2020,
        "season_2020_ids_sha256": _ids_sha256(ids_2020),
        "season_2021_n": len(ids_2021),
        "season_2021_game_ids": ids_2021,
        "season_2021_ids_sha256": _ids_sha256(ids_2021),
        "matched72_intersect_2021_n": len(ids37),
        "matched72_intersect_2021_game_ids": ids37,
        "matched72_intersect_2021_ids_sha256": _ids_sha256(ids37),
        "selection_limited_market_note": MARKET_N37_NOTE,
        "outcomes_already_consumed": True,
    }
    pins = {
        "frozen_before_fit": True,
        "dev437_path": meta["path"],
        "dev437_file_sha256": meta["file_sha256"],
        "dev437_record_sha256": meta["record_sha256"],
        "matched72_sha256": SEALED_MATCHED72_SHA256,
        "admissible_quotes_sha256": SEALED_QUOTES_SHA256,
        "coverage_manifest_sha256": SEALED_MANIFEST_SHA256,
        "first_case_game_id": FIRST_CASE_GAME_ID,
        "first_case_record_sha256": FIRST_CASE_RECORD_SHA256,
        "first_case_file_sha256": FIRST_CASE_FILE_SHA256,
        "code_path": _repo_rel(code_path),
        "code_sha256": sha256_file(code_path),
        "protocol_canonical_sha256": _canonical_sha256(protocol),
        "identity_canonical_sha256": _canonical_sha256(identity),
        "q2_lineage_max_abs_residual": meta["q2_lineage"]["max_abs_blend_residual"],
    }
    stop = {
        "status": "STOP_AWAITING_ALEX_PRECOMP_GO",
        "ticket": TICKET,
        "experiment": EXPERIMENT,
        "cert_candidate": CERT_CANDIDATE,
        "eval": None,
        "diagnostic_executed": False,
        "c2_c3_fitted": False,
        "go_token_required": ALEX_PRECOMP_GO_TOKEN,
        "go_env": GO_ENV,
        "hard_end": "00:35 UTC / 19:35 America/New_York",
        "notes": [
            OUTCOMES_ALREADY_CONSUMED_NOTE,
            "Protocol/code/input/identity hashes frozen before any C2/C3 fit.",
            "C3 (w,b) and candidate training losses are NOT computed until Alex GO.",
            "One 2021 DEV diagnostic + n=37 market diagnostic after GO only.",
            "R2-C remains DATA_COVERAGE_BLOCKED. G5 unchanged. Isolated new directory.",
        ],
    }
    written = {
        "PROTOCOL.json": protocol,
        "INPUT_PINS.json": pins,
        "IDENTITY_FREEZE.json": identity,
        "Q2_LINEAGE.json": meta["q2_lineage"],
        "MARKET_N37_IDENTITY.json": market,
        "STOP_AWAITING_ALEX_PRECOMP_GO.json": stop,
    }
    file_hashes: dict[str, str] = {}
    for name, payload in written.items():
        file_hashes[name] = _write_json(out_dir / name, payload)
    manifest = {
        "schema_version": SCHEMA,
        "label": LABEL,
        "experiment": EXPERIMENT,
        "cert_candidate": CERT_CANDIDATE,
        "eval": None,
        "isolated_dir": _repo_rel(out_dir),
        "frozen_before_fit": True,
        "c2_c3_fitted": False,
        "diagnostic_executed": False,
        "file_sha256": file_hashes,
        "input_pins": pins,
        "outcomes_already_consumed": True,
        "g5_status": "DATA_COVERAGE_BLOCKED",
        "g5_loosened": False,
        "status": "STOP_AWAITING_ALEX_PRECOMP_GO",
    }
    file_hashes["FREEZE_MANIFEST.json"] = _write_json(out_dir / "FREEZE_MANIFEST.json", manifest)
    manifest["file_sha256"] = file_hashes
    return manifest


def persist_c3_selection(selection: Mapping[str, Any], dest: Path | None = None) -> dict[str, Any]:
    if not selection.get("frozen_before_2021"):
        raise CalibrationRefuse("C3 selection missing frozen_before_2021 flag")
    body = _record_body(
        {
            "schema_version": "nfl-t5141u-c3-selection-v1",
            "label": LABEL,
            "cert_candidate": CERT_CANDIDATE,
            "eval": None,
            "frozen_before_2021": True,
            "selection": {
                "w": selection["w"],
                "b": selection["b"],
                "mae_2020": selection["mae_2020"],
                "n_train": selection["n_train"],
                "n_candidates": selection["n_candidates"],
                "tie_break": selection["tie_break"],
            },
            "candidates": selection["candidates"],
            "note": "C3 (w,b) + ALL candidate 2020 training losses frozen before 2021.",
        }
    )
    if dest is not None:
        _refuse_dest(Path(dest))
        _write_json(Path(dest), body)
    return body


def run_r3_calibration(
    *,
    go: str | None = None,
    dest: Path | None = None,
    dest_dir: Path | None = None,
    dev437_path: Path | None = None,
    matched72_path: Path | None = None,
    quotes_path: Path | None = None,
    c3_dest: Path | None = None,
    rows: Sequence[CalibRow] | None = None,
    market_by_id: Mapping[str, float] | None = None,
    market_ids: Sequence[str] | None = None,
    expect_file_sha256: str | None = None,
    expect_record_sha256: str | None = None,
    eval_payload: Any = None,
    persist_record: bool = True,
) -> dict[str, Any]:
    """One diagnostic execution. Requires Alex pre-computation GO. No winner."""
    refuse_eval_bind(eval_payload)
    require_alex_precomp_go(go)
    if rows is None:
        loaded, meta = load_dev437_rows(
            dev437_path,
            expect_file_sha256=expect_file_sha256,
            expect_record_sha256=expect_record_sha256,
        )
    else:
        loaded = list(rows)
        if any(not isinstance(row, CalibRow) for row in loaded):
            raise CalibrationRefuse("injected rows must be CalibRow")
        meta = {
            "path": "injected",
            "file_sha256": None,
            "record_sha256": None,
            "n": len(loaded),
            "n_by_season": _count_seasons(loaded),
            "q2_lineage": {
                "note": Q2_LINEAGE_NOTE,
                "not_newly_generated_forecast": True,
                "outcomes_already_consumed": True,
            },
            "outcomes_already_consumed": True,
            "eval": None,
        }
    train = [row for row in loaded if row.season == 2020]
    holdout = [row for row in loaded if row.season == 2021]
    if not train or not holdout:
        raise CalibrationRefuse("both 2020 train and 2021 holdout rows are required")
    if rows is None and Path(dev437_path or DEV437_PATH).resolve() == DEV437_PATH.resolve():
        if len(train) != DEV437_N_2020 or len(holdout) != DEV437_N_2021:
            raise CalibrationRefuse("sealed DEV437 season split drifted")
        ids37 = freeze_matched37_ids(matched72_path)
    else:
        ids37 = list(market_ids) if market_ids is not None else [row.game_id for row in holdout]
        refuse_normalized_94(ids37)
    # Fit C2/C3 on 2020 only — persist C3 freeze BEFORE 2021 scoring.
    c2 = fit_c2(train)
    c3 = select_c3(train)
    selection_path = Path(c3_dest) if c3_dest is not None else (
        (Path(dest_dir) / C3_SELECTION_DEST.name) if dest_dir is not None else C3_SELECTION_DEST
    )
    c3_freeze = persist_c3_selection(c3, dest=selection_path)
    training = score_arms(train, c2=c2, c3=c3, require_c3_frozen=True)
    diagnostic = score_arms(holdout, c2=c2, c3=c3, require_c3_frozen=True)
    if market_by_id is None and rows is None:
        market_identity = freeze_market_n37_identity(
            ids37,
            quotes_path=quotes_path,
            rows_by_id={row.game_id: row for row in holdout},
        )
        market_by_id = {p["game_id"]: float(p["market_margin"]) for p in market_identity["points"]}
    else:
        market_identity = {
            "n": len(ids37),
            "game_ids": list(ids37),
            "ids_sha256": _ids_sha256(ids37),
            "selection_limited": True,
            "representative_market_validation": False,
            "note": MARKET_N37_NOTE,
            "frozen_before_fit": True,
        }
        market_by_id = dict(market_by_id or {})
    market_rows = [row for row in holdout if row.game_id in set(ids37)]
    if [row.game_id for row in market_rows] != list(ids37):
        by = {row.game_id: row for row in holdout}
        try:
            market_rows = [by[gid] for gid in ids37]
        except KeyError as exc:
            raise CalibrationRefuse(f"market id not in 2021 holdout: {exc}") from exc
    if len(market_rows) != len(ids37):
        raise CalibrationRefuse("market n37 identity mismatch vs 2021 holdout")
    if set(market_by_id) != set(ids37):
        raise CalibrationRefuse("market_by_id keys must be exactly the frozen n37 IDs")
    market = score_arms(
        market_rows,
        c2=c2,
        c3=c3,
        market_by_id=market_by_id,
        require_c3_frozen=True,
    )
    record = _record_body(
        {
            "schema_version": SCHEMA,
            "label": LABEL,
            "metric_split": DEV_METRIC_SPLIT,
            "split": SPLIT_DEV,
            "cohort": COHORT,
            "experiment": EXPERIMENT,
            "ticket": TICKET,
            "cert_candidate": CERT_CANDIDATE,
            "eval": None,
            "scoring": None,
            "look": None,
            "exec_scoring": "REFUSED_DEV_RESEARCH_NOT_EVAL",
            "one_run_claim": False,
            "eval_invoked": False,
            "r2_eval_called": False,
            "winner": None,
            "selected_from_2021": False,
            "retune_from_2021": False,
            "outcomes_already_consumed": True,
            "retro_fit_limitations_preserved": True,
            "g5_status": "DATA_COVERAGE_BLOCKED",
            "g5_loosened": False,
            "reporting_class": reporting_class(len(holdout)),
            "n": len(loaded),
            "n_by_season": _count_seasons(loaded),
            "input_hashes": {
                "dev437_file": meta.get("file_sha256"),
                "dev437_record": meta.get("record_sha256"),
                "matched72": SEALED_MATCHED72_SHA256,
                "admissible_quotes": SEALED_QUOTES_SHA256,
                "coverage_manifest": SEALED_MANIFEST_SHA256,
                "protocol": _canonical_sha256(protocol_spec()),
                "code": sha256_file(Path(__file__)),
            },
            "q2_lineage": meta.get("q2_lineage"),
            "c2": {"w": c2["w"], "b": c2["b"], "frozen_before_2021": True},
            "c3_selection": {
                "w": c3["w"],
                "b": c3["b"],
                "mae_2020": c3["mae_2020"],
                "n_candidates": c3["n_candidates"],
                "frozen_before_2021": True,
                "selection_sha256": c3_freeze.get("record_sha256"),
            },
            "training_2020": training,
            "diagnostic_2021": diagnostic,
            "market_n37": {
                **market,
                "identity": {
                    k: market_identity[k]
                    for k in (
                        "n",
                        "game_ids",
                        "ids_sha256",
                        "selection_limited",
                        "representative_market_validation",
                        "note",
                        "frozen_before_fit",
                    )
                    if k in market_identity
                },
            },
            "rng": {
                "bootstrap_B": BOOT_B,
                "bootstrap_seed": BOOT_SEED,
                "interval_conditioning": "conditional_on_fitted_parameters_not_full_fitting_uncertainty",
            },
            "first_case_preserved": {
                "game_id": FIRST_CASE_GAME_ID,
                "record_sha256": FIRST_CASE_RECORD_SHA256,
                "file_sha256": FIRST_CASE_FILE_SHA256,
            },
            "notes": [
                OUTCOMES_ALREADY_CONSUMED_NOTE,
                Q2_LINEAGE_NOTE,
                MARKET_N37_NOTE,
                "C3 (w,b) and all candidate 2020 losses frozen before 2021.",
                "Unfavorable results reported unchanged. No winner. No 2021/market retune.",
                "EVAL not invoked. one_run_claim=false. CERT=0. G5 DATA_COVERAGE_BLOCKED.",
            ],
        }
    )
    validate_r3_record(record)
    dest_p = Path(dest) if dest is not None else (
        (Path(dest_dir) / DEFAULT_DEST.name) if dest_dir is not None else DEFAULT_DEST
    )
    if persist_record:
        _refuse_dest(dest_p)
        try:
            write_dev_research_record(record, dest_p)
        except DevResearchRefuse as exc:
            raise CalibrationRefuse(str(exc)) from exc
        record["_path"] = str(dest_p)
    return record


def validate_r3_record(record: Mapping[str, Any]) -> None:
    missing = [k for k in OUTPUT_CONTRACT if k not in record]
    if missing:
        raise CalibrationRefuse(f"R3 DEV_RESEARCH contract incomplete: {missing}")
    if record.get("label") != LABEL:
        raise CalibrationRefuse("label must be DEV_RESEARCH")
    if record.get("eval") is not None:
        raise CalibrationRefuse("DEV_RESEARCH must not carry eval")
    if record.get("one_run_claim") is not False:
        raise CalibrationRefuse("DEV_RESEARCH must not claim a one-run")
    if record.get("cert_candidate") != 0:
        raise CalibrationRefuse("CERT must be 0")
    if record.get("winner") is not None:
        raise CalibrationRefuse("winner selection is forbidden")
    if record.get("selected_from_2021") or record.get("retune_from_2021"):
        raise CalibrationRefuse("2021/market retune is forbidden")
    if record.get("eval_invoked") or record.get("r2_eval_called"):
        raise CalibrationRefuse("EVAL invoke flags must be false")
    if record.get("g5_status") != "DATA_COVERAGE_BLOCKED" or record.get("g5_loosened"):
        raise CalibrationRefuse("G5 must remain DATA_COVERAGE_BLOCKED / not loosened")
    if record.get("outcomes_already_consumed") is not True:
        raise CalibrationRefuse("must record that DEV outcomes are already consumed")
    c3 = record.get("c3_selection") or {}
    if not c3.get("frozen_before_2021"):
        raise CalibrationRefuse("C3 selection must be frozen before 2021")
    market = record.get("market_n37") or {}
    identity = market.get("identity") or {}
    if identity.get("representative_market_validation"):
        raise CalibrationRefuse("n=37 must not be labeled representative market validation")


def pre_fit_status(dest_dir: Path | None = None) -> dict[str, Any]:
    out_dir = Path(dest_dir) if dest_dir else ISOLATED_OPS
    stop = out_dir / STOP_DEST.name
    record = out_dir / DEFAULT_DEST.name
    return {
        "isolated_dir": str(out_dir),
        "freeze_present": (out_dir / "FREEZE_MANIFEST.json").is_file(),
        "stop_present": stop.is_file(),
        "diagnostic_record_present": record.is_file(),
        "c3_selection_present": (out_dir / C3_SELECTION_DEST.name).is_file(),
        "status": (
            "DIAGNOSTIC_EXECUTED"
            if record.is_file()
            else "STOP_AWAITING_ALEX_PRECOMP_GO"
            if stop.is_file()
            else "FREEZE_MISSING"
        ),
    }


def as_public_row(row: CalibRow) -> dict[str, Any]:
    return asdict(row)
