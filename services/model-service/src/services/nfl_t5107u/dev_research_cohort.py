"""t5125u R2-B2 — fixed-candidate DEV diagnostic on all 437 DEV REG games.

Does not overwrite the first-case DEV_RESEARCH record (2020_02_CIN_CLE /
record_sha256 621f0f84). Uses pinned freeze IF + fixed 0.5/0.5. Same
bootstrap B=10000 seed 20261101 and IF produce pins (N=4000, seed_for).
No fit, selection, weight search, EVAL feedback, or invented market compare.

Market status is NOT_READY until an R2-A verified extract/manifest is
present. CERT=0. one_run_claim=false. Exclusive create.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .dev_research import (
    DEV_REG_N,
    DEV_REG_SHA256,
    LABEL,
    NON_REG_WILDCARD_N,
    NON_REG_WILDCARD_SHA256,
    DEFAULT_FREEZE,
    DEFAULT_SCHEDULE,
    DevResearchRefuse,
    _record_body,
    fixed_half_half_candidate,
    freeze_dev_metadata_eligibility,
    r2a_coverage_status,
    write_dev_research_record,
)
from .evaluator import (
    BOOT_B,
    BOOT_SEED,
    bootstrap_ci,
    mean_stat,
    paired_bias,
    paired_mae,
    paired_rmse,
    reporting_class,
    run_paired_margin_eval,
)
from .if_produce import SEED_BASE, SEED_MOD, SIMULATIONS, seed_for
from .outcome_gate import (
    FIRST_CASE_FILE_SHA256,
    FIRST_CASE_GAME_ID,
    FIRST_CASE_RECORD_SHA256,
    ScoringOutcomeLoader,
    invoke_after_gates,
    refuse_overwrite_first_case_record,
    refuse_preloaded_scoring_outcomes,
    refuse_preserved_t5116u_path,
)

SCHEMA = "nfl-t5125u-dev-research-cohort-v1"
CERT_CANDIDATE = 0
DEFAULT_COHORT_RECORD = (
    Path(__file__).resolve().parents[5]
    / "data/ops/nfl-forecast-builder-t5107u/DEV_RESEARCH_t5125u_R2B2_437.json"
)

COHORT_OUTPUT_CONTRACT = (
    "schema_version",
    "label",
    "cert_candidate",
    "eval",
    "scoring",
    "look",
    "exec_scoring",
    "one_run_claim",
    "dev_reg_n",
    "dev_reg_sha256",
    "wildcard_n",
    "wildcard_sha256",
    "wildcard_excluded",
    "first_case_preserved",
    "n",
    "n_by_season",
    "mae_challenger",
    "mae_if",
    "rmse_challenger",
    "rmse_if",
    "bias_challenger",
    "bias_if",
    "delta_mae_vs_if",
    "mean_signed_diff_vs_if",
    "per_season",
    "bootstrap_game",
    "bootstrap_season_week",
    "reporting_class",
    "market",
    "r2a_coverage",
    "rng",
    "target_join_phase",
    "notes",
    "record_sha256",
)


def validate_cohort_record(record: Mapping[str, Any]) -> None:
    missing = [k for k in COHORT_OUTPUT_CONTRACT if k not in record]
    if missing:
        raise DevResearchRefuse(f"DEV_RESEARCH 437 contract incomplete: {missing}")
    if record.get("label") != LABEL:
        raise DevResearchRefuse("label must be DEV_RESEARCH")
    if record.get("eval") is not None:
        raise DevResearchRefuse("DEV_RESEARCH must not carry eval")
    if record.get("one_run_claim") is not False:
        raise DevResearchRefuse("DEV_RESEARCH must not claim a one-run")
    if record.get("cert_candidate") != CERT_CANDIDATE:
        raise DevResearchRefuse("CERT must be 0")
    if record.get("synthetic") is not True:
        if record.get("dev_reg_n") != DEV_REG_N:
            raise DevResearchRefuse("DEV REG n pin 437 required")
        if record.get("dev_reg_sha256") != DEV_REG_SHA256:
            raise DevResearchRefuse("DEV REG pin mismatch vs 92b91585")


def load_dev_reg_outcomes_from_schedule(
    game_ids: Sequence[str],
    schedule_path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """TARGET JOIN: scores for the already-frozen eligible DEV REG ids only."""
    path = Path(schedule_path) if schedule_path else DEFAULT_SCHEDULE
    if not path.is_file():
        raise DevResearchRefuse(f"schedule outcomes missing: {path}")
    want = set(game_ids)
    out: dict[str, dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            gid = str(raw.get("game_id") or "")
            if gid not in want:
                continue
            if str(raw.get("season_type") or "REG").upper() != "REG":
                continue
            out[gid] = {
                "game_id": gid,
                "season": int(raw["season"]),
                "week": int(raw["week"]),
                "home_score": raw.get("home_score"),
                "away_score": raw.get("away_score"),
            }
    return out


def _per_season(games: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in games:
        by[int(row["season"])].append(dict(row))
    out: dict[str, Any] = {}
    for season in sorted(by):
        rows = by[season]
        err_c = [r["err_challenger"] for r in rows]
        err_if = [r["err_if"] for r in rows]
        diffs = [r["signed_diff_vs_if"] for r in rows]
        out[str(season)] = {
            "n": len(rows),
            "mae_challenger": paired_mae(err_c),
            "mae_if": paired_mae(err_if),
            "rmse_challenger": paired_rmse(err_c),
            "rmse_if": paired_rmse(err_if),
            "bias_challenger": paired_bias(err_c),
            "bias_if": paired_bias(err_if),
            "delta_mae_vs_if": paired_mae(err_c) - paired_mae(err_if),
            "mean_signed_diff_vs_if": mean_stat(diffs),
        }
    return out


def _market_not_ready(r2a: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": "NOT_READY",
        "market_margin": None,
        "invented_comparison": False,
        "reason": "R2-A verified quote extract/manifest not supplied — market E2E prerequisite unmet",
        "r2a_coverage": dict(r2a),
        "g5_loosened": False,
        "cutoff_loosened": False,
        "books_loosened": False,
    }


def run_dev_research_cohort(
    forecasts: Sequence[Mapping[str, Any]],
    *,
    outcomes: Mapping[str, Mapping[str, Any]] | None = None,
    outcome_loader: ScoringOutcomeLoader | Callable[[], Mapping[str, Mapping[str, Any]]] | None = None,
    require_dev_reg_pin: bool = True,
    dest: Path | None = None,
    synthetic: bool = False,
) -> dict[str, Any]:
    """All metadata-eligible DEV REG games. Loader runs after eligibility freeze."""
    try:
        refuse_preloaded_scoring_outcomes(outcomes)
    except Exception as exc:
        raise DevResearchRefuse(str(exc)) from exc
    if outcome_loader is None:
        raise DevResearchRefuse("R2 DEV cohort requires outcome_loader (outcomes=None)")
    eligibility = freeze_dev_metadata_eligibility(
        forecasts, require_dev_reg_pin=require_dev_reg_pin
    )
    eligible_ids = list(eligibility["eligible_game_ids"])
    if not eligible_ids:
        raise DevResearchRefuse("no metadata-eligible DEV REG games")
    by_id = {str(r["game_id"]): r for r in forecasts}
    for gid in eligible_ids:
        fixed_half_half_candidate(by_id[gid])
    loaded = invoke_after_gates(None, outcome_loader)
    r2a = r2a_coverage_status()
    scored = run_paired_margin_eval(
        list(forecasts),
        loaded,
        eligible_game_ids=eligible_ids,
        market_points=None,
    )
    games = list(scored["games"])
    err_c = [r["err_challenger"] for r in games]
    err_if = [r["err_if"] for r in games]
    diffs = [r["signed_diff_vs_if"] for r in games]
    compact = [
        {
            "game_id": r["game_id"],
            "season": r["season"],
            "week": r["week"],
            "actual_margin": r["actual_margin"],
            "m_challenger": r["m_challenger"],
            "m_if": r["m_if"],
            "err_challenger": r["err_challenger"],
            "err_if": r["err_if"],
            "L_challenger": r["L_challenger"],
            "L_if": r["L_if"],
            "signed_diff_vs_if": r["signed_diff_vs_if"],
        }
        for r in games
    ]
    first = next((r for r in compact if r["game_id"] == FIRST_CASE_GAME_ID), None)
    record = _record_body(
        {
            "schema_version": SCHEMA,
            "label": LABEL,
            "cert_candidate": CERT_CANDIDATE,
            "eval": None,
            "scoring": None,
            "look": None,
            "exec_scoring": "REFUSED_DEV_RESEARCH_NOT_EVAL",
            "one_run_claim": False,
            "synthetic": synthetic,
            "dev_reg_n": eligibility["dev_reg_n"],
            "dev_reg_sha256": eligibility["dev_reg_sha256"],
            "wildcard_n": eligibility["wildcard_n"],
            "wildcard_sha256": eligibility["wildcard_sha256"],
            "wildcard_excluded": True,
            "eligibility_sha256": eligibility["eligibility_sha256"],
            "eligible_n": eligibility["eligible_n"],
            "joined_n": len(games),
            "first_case_preserved": {
                "game_id": FIRST_CASE_GAME_ID,
                "record_sha256": FIRST_CASE_RECORD_SHA256,
                "file_sha256": FIRST_CASE_FILE_SHA256,
                "in_cohort": first is not None,
                "first_case_err_challenger": None if first is None else first["err_challenger"],
            },
            "n": len(games),
            "n_by_season": _count_seasons(games),
            "mae_challenger": paired_mae(err_c),
            "mae_if": paired_mae(err_if),
            "rmse_challenger": paired_rmse(err_c),
            "rmse_if": paired_rmse(err_if),
            "bias_challenger": paired_bias(err_c),
            "bias_if": paired_bias(err_if),
            "delta_mae_vs_if": paired_mae(err_c) - paired_mae(err_if),
            "mean_signed_diff_vs_if": mean_stat(diffs),
            "per_season": _per_season(games),
            "bootstrap_game": scored["bootstrap_game"],
            "bootstrap_season_week": scored["bootstrap_season_week"],
            "reporting_class": reporting_class(len(games)),
            "market": _market_not_ready(r2a),
            "r2a_coverage": r2a,
            "rng": {
                "bootstrap_B": BOOT_B,
                "bootstrap_seed": BOOT_SEED,
                "if_simulations": SIMULATIONS,
                "if_seed_base": SEED_BASE,
                "if_seed_mod": SEED_MOD,
                "if_seed_first_case": seed_for(FIRST_CASE_GAME_ID),
                "if_mus_reproduced": False,
                "source": "forecast_freeze_pin — mus not re-produced; seed/N disclosed only",
            },
            "target_join_phase": "AFTER_METADATA_ELIGIBILITY_FREEZE",
            "games": compact,
            "notes": [
                "Fixed 0.5/0.5 candidate on all DEV REG identities. No fit/selection/EVAL feedback.",
                "Signed-loss-difference CIs: game-cluster and week-cluster (season_week). B=10000 seed 20261101.",
                "Market NOT_READY until R2-A verified extract/manifest lands. No invented market compare.",
                "First-case DEV_RESEARCH_t5119u_R2B.json preserved (621f0f84). No one-run claim. CERT=0.",
            ],
        }
    )
    validate_cohort_record(record)
    if dest is not None:
        try:
            refuse_preserved_t5116u_path(dest)
            refuse_overwrite_first_case_record(dest)
        except Exception as exc:
            raise DevResearchRefuse(str(exc)) from exc
        write_dev_research_record(record, dest)
    return record


def _count_seasons(games: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in games:
        counts[str(int(row["season"]))] += 1
    return dict(sorted(counts.items()))


def materialize_dev_research_cohort_437(
    *,
    freeze_path: Path | None = None,
    schedule_path: Path | None = None,
    dest: Path | None = None,
) -> dict[str, Any]:
    freeze_p = Path(freeze_path) if freeze_path else DEFAULT_FREEZE
    dest_p = Path(dest) if dest else DEFAULT_COHORT_RECORD
    try:
        refuse_preserved_t5116u_path(dest_p)
        refuse_overwrite_first_case_record(dest_p)
    except Exception as exc:
        raise DevResearchRefuse(str(exc)) from exc
    freeze = json.loads(freeze_p.read_text(encoding="utf-8"))
    forecasts = list(freeze.get("forecasts") or [])
    eligibility = freeze_dev_metadata_eligibility(forecasts, require_dev_reg_pin=True)
    ids = list(eligibility["eligible_game_ids"])

    def _load() -> dict[str, dict[str, Any]]:
        return load_dev_reg_outcomes_from_schedule(ids, schedule_path)

    loader = ScoringOutcomeLoader(_load)
    return run_dev_research_cohort(
        forecasts,
        outcome_loader=loader,
        require_dev_reg_pin=True,
        dest=dest_p,
        synthetic=False,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(Path(path).read_bytes())
    return digest.hexdigest()
