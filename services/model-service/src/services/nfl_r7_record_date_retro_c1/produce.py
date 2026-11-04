"""Guarded RETRO_C1 diagnostic executor. CERT=0.

Synthetic fixtures only. Real EXEC HOLD. ENV never grants.
Producer→capability/gate is Worker A's obligation.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from src.services.nfl_ops_v1_evidence.spy import (
    ForbiddenSurfaceSpy,
    OutcomeReadSpy,
    assert_zero_forbidden_on_refusal,
    run_spy_positive_control,
)
from src.services.nfl_r7_correctness_v1.calendar import bind_rest_from_et_calendar
from src.services.nfl_r7_correctness_v1.packets import build_typed_synthetic_input
from src.services.nfl_r7_correctness_v1.produce import produce_r7_point_margin, repo_root, write_json
from src.services.nfl_r7_record_date_retro_c1.authority import AuthorityRegistry
from src.services.nfl_r7_record_date_retro_c1.fixtures import (
    ALIAS_SCHEDULE,
    POSTPONE_SCHEDULE,
    SYNTHETIC_TARGET,
    TIE_SCHEDULE,
    synthetic_history,
    synthetic_schedule,
)
from src.services.nfl_r7_record_date_retro_c1.history_filter import filter_history_for_target
from src.services.nfl_r7_record_date_retro_c1.identity import bind_identity_pointers
from src.services.nfl_r7_record_date_retro_c1.pins import (
    ARCHIVED_R5_SHA256,
    BOOTSTRAP_B,
    BOOTSTRAP_GEN,
    BOOTSTRAP_SEED,
    CALENDAR_ID,
    CERT,
    CLARIFICATIONS_REL,
    CLARIFICATIONS_SHA256,
    COS_ACCEPT,
    DESIGN,
    EXPECTED_COMMAND,
    FUTURE_REAL_COMMAND,
    GAMES_SHA256,
    HISTORY_ORDER,
    IDENTITY_REL,
    IDENTITY_SHA256,
    KO_MINUS_MINUTES,
    MARKET_POINT_DIGEST_SHA256,
    N_2020_21,
    N_ASYM,
    N_CHANGED_GAMES,
    N_CHANGED_SIDES,
    N_HISTORY_2013_19,
    N_IDENTITY,
    N_NEW,
    N_OLD,
    N_SAME96,
    N_TARGET,
    NOMINAL_REL,
    NOMINAL_SHA256,
    OPS_REL,
    OUTCOMES_SHA256,
    OWNER_CLEAR,
    PACKAGE,
    PROFILE,
    R4_JSON_SHA256,
    R4_MATRIX_SHA256,
    REST_META_REL,
    REST_META_SHA256,
    SAME96_IDENTITY_SHA256,
    SCHEDULE_SHA256,
    SENSITIVITY_SEED,
    SIMULATIONS,
    SPEC_REL,
    SPEC_SHA256,
    STRICT_LIVE_PROFILE,
    STRICT_LIVE_STATUS,
)
from src.services.nfl_r7_record_date_retro_c1.refuse import RetroHold, RetroRefuse
from src.services.nfl_r7_record_date_retro_c1.rest import project_recorded_date_rest


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_pin(root: Path, rel: str, expected: str) -> dict[str, str]:
    path = Path(root) / rel
    if not path.is_file():
        raise RetroRefuse(f"pin missing {rel}")
    digest = sha256_file(path)
    if digest != expected:
        raise RetroRefuse(f"{rel} sha256 {digest} != {expected}")
    return {"path": rel, "sha256": digest, "match": True}


def real_data_projection_schema() -> dict[str, Any]:
    """Exact future real-data projection schema. Not a grant. Hashes are source pins."""
    return {
        "schema_id": "r7-record-date-retro-c1-real-projection-v1",
        "cert": CERT,
        "authorized_now": False,
        "scores_opened": False,
        "allowed_history_identities": N_IDENTITY,
        "history_2013_19": N_HISTORY_2013_19,
        "reg_2020_21": N_2020_21,
        "targets": N_TARGET,
        "old437": N_OLD,
        "new59": N_NEW,
        "same96": N_SAME96,
        "identity_columns_only": ["season", "week", "home", "away", "game_id", "season_type"],
        "raw_source_pins": {
            "games": {"sha256": GAMES_SHA256, "status": "UNOPENED", "columns": ["season", "week", "home", "away", "nominal_kickoff"]},
            "outcomes": {"sha256": OUTCOMES_SHA256, "status": "UNOPENED", "reason": "label-read not authorized"},
            "schedule_results_2020_2023": {"sha256": SCHEDULE_SHA256, "status": "METADATA_ONLY", "no_target_scores": True},
            "r4_recon_json": {"sha256": R4_JSON_SHA256, "status": "ABSENT_WORKING_TREE", "opened": False},
            "r4_matrix": {"sha256": R4_MATRIX_SHA256, "status": "ABSENT_WORKING_TREE", "opened": False},
            "identity_pointers_2320": {"sha256": IDENTITY_SHA256, "status": "BOUND"},
            "nominal_528": {"sha256": NOMINAL_SHA256, "status": "BOUND"},
            "rest_meta_496": {"sha256": REST_META_SHA256, "status": "BOUND"},
            "same96_identity": {"sha256": SAME96_IDENTITY_SHA256, "status": "SPEC_NAMED_PIN", "working_tree": "ABSENT"},
            "frozen_median_spread_market_point": {"sha256": MARKET_POINT_DIGEST_SHA256, "status": "SPEC_NAMED_PIN", "working_tree": "ABSENT"},
            "archived_r5_reference": {"sha256": ARCHIVED_R5_SHA256, "status": "REFERENCE_ONLY", "regenerate": False},
        },
        "history_filter": {
            "prior_assigned_week_only": True,
            "nominal_ko_minus_minutes": KO_MINUS_MINUTES,
            "same_assigned_week_scored_history": False,
        },
        "future_pass": {
            "if_draws_per_target": SIMULATIONS,
            "unique_targets": N_TARGET,
            "bootstrap_B": BOOTSTRAP_B,
            "bootstrap_gen": BOOTSTRAP_GEN,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "sensitivity_seed": SENSITIVITY_SEED,
            "requires": "distinct Root GO/context AFTER final pins + independent preflight",
        },
        "executable_command_now": EXPECTED_COMMAND,
        "executable_command_when_root_authorizes": FUTURE_REAL_COMMAND,
    }


def n1_n3_nonblocking() -> list[dict[str, str]]:
    return [
        {
            "id": "N1",
            "to": "Codex",
            "blocking": False,
            "note": "Spec L17 cites independent 96 cutoff==kickoff; nominal file reports target496_raw_matrix_field_equals_kickoff=496. Do not treat 96 as the 496 bind.",
        },
        {
            "id": "N2",
            "to": "Codex",
            "blocking": False,
            "note": "Spec cosmetic missing spaces (already-consumed2020/21, found220/496, SHA256 prefixes).",
        },
        {
            "id": "N3",
            "to": "Codex",
            "blocking": False,
            "note": "No W1 targets in the 496 rest cohort is OK — missing prior same-season record refuses; no 7-day fallback.",
        },
    ]


def bind_rest_pin(root: Path) -> dict[str, Any]:
    require_pin(root, REST_META_REL, REST_META_SHA256)
    body = json.loads((Path(root) / REST_META_REL).read_text(encoding="utf-8"))
    if int(body.get("n", -1)) != N_TARGET:
        raise RetroRefuse("rest meta n != 496")
    if int(body.get("changed_games_vs_R4_rest_cells", -1)) != N_CHANGED_GAMES:
        raise RetroRefuse("changed_games drifted")
    if int(body.get("changed_team_sides", -1)) != N_CHANGED_SIDES:
        raise RetroRefuse("changed_team_sides drifted")
    if int(body.get("asymmetric_recorded_date_rest_games", -1)) != N_ASYM:
        raise RetroRefuse("asymmetric count drifted")
    if body.get("no_forecast_fit_outcomes_score_economic_calc") is not True:
        raise RetroRefuse("rest meta claims forbidden calc")
    return {
        "sha256": REST_META_SHA256,
        "n": N_TARGET,
        "changed_games": N_CHANGED_GAMES,
        "changed_team_sides": N_CHANGED_SIDES,
        "asymmetric": N_ASYM,
        "forecasts": False,
    }


def _recompute_rest_pin(root: Path) -> dict[str, Any]:
    """Recompute recorded-date rest from nominal 528 and match pinned 496."""
    nom = json.loads((Path(root) / NOMINAL_REL).read_text(encoding="utf-8"))
    rest = json.loads((Path(root) / REST_META_REL).read_text(encoding="utf-8"))
    schedule = [
        {
            "game_id": row["game_id"],
            "season": int(row["season"]),
            "week": int(row["week"]),
            "season_type": "REG",
            "home": row["home"],
            "away": row["away"],
            "recorded_game_date": row["recorded_game_date"],
        }
        for row in nom["rows"]
    ]
    nom_by = {row["game_id"]: row for row in schedule}
    expected = {row["game_id"]: row for row in rest["rows"]}
    matched = 0
    for row in rest["rows"]:
        src = nom_by[row["game_id"]]
        target = {
            "game_id": row["game_id"],
            "season": src["season"],
            "home": src["home"],
            "away": src["away"],
            "recorded_game_date": row["recorded_target_date"],
            "season_type": "REG",
        }
        got = project_recorded_date_rest(target=target, schedule=schedule)
        exp = expected[row["game_id"]]
        if got["home"]["predecessor_game_id"] != exp["home"]["predecessor_game_id"]:
            raise RetroRefuse(f"home pred mismatch {row['game_id']}")
        if got["away"]["predecessor_game_id"] != exp["away"]["predecessor_game_id"]:
            raise RetroRefuse(f"away pred mismatch {row['game_id']}")
        if got["home"]["calendar_days"] != exp["home"]["calendar_days"]:
            raise RetroRefuse(f"home days mismatch {row['game_id']}")
        if got["away"]["calendar_days"] != exp["away"]["calendar_days"]:
            raise RetroRefuse(f"away days mismatch {row['game_id']}")
        matched += 1
    return {"matched": matched, "n": N_TARGET}


def _score_synthetic(c_margin: float, y_margin: float) -> dict[str, Any]:
    signed = float(c_margin) - float(y_margin)
    return {
        "y_margin": float(y_margin),
        "y_source": "SYNTHETIC_LABEL_NOT_REAL_OUTCOME",
        "c_margin": float(c_margin),
        "signed_c_minus_y": signed,
        "abs_c_minus_y": abs(signed),
        "real_outcomes_joined": False,
        "economic_price_used": False,
    }


def run_invalid_path(
    *,
    registry: AuthorityRegistry,
    outcome_spy: OutcomeReadSpy,
    surface: ForbiddenSurfaceSpy,
    claim_id: str | None,
    context_hash: str | None,
    requested_class: str,
    reader_role: str = "model",
) -> dict[str, Any]:
    try:
        registry.require_before_reader(
            claim_id=claim_id,
            context_hash_expected=context_hash,
            reader_role=reader_role,
            requested_class=requested_class,
        )
        raise RetroRefuse("invalid path unexpectedly authorized")
    except (RetroRefuse, RetroHold) as exc:
        assert_zero_forbidden_on_refusal(outcome_spy=outcome_spy, surface=surface)
        return {
            "refused": True,
            "reason": str(exc),
            "outcome_reads": outcome_spy.reads,
            "surface_notes": surface.count,
            "model_called": False,
        }


def run_synthetic_executor(*, root: Path, dest: Path) -> dict[str, Any]:
    outcome_spy = OutcomeReadSpy()
    surface = ForbiddenSurfaceSpy()
    registry = AuthorityRegistry()
    context = {
        "package": PACKAGE,
        "profile": PROFILE,
        "channel": "SYNTHETIC",
        "spec_sha256": SPEC_SHA256,
        "identity_sha256": IDENTITY_SHA256,
    }
    claim = registry.issue_synthetic_claim(context=context)
    try:
        registry.require_before_reader(
            claim_id=claim["claim_id"],
            context_hash_expected=claim["context_hash"],
            reader_role="feature",
            requested_class="SYNTHETIC",
        )
        registry.require_before_reader(
            claim_id=claim["claim_id"],
            context_hash_expected=claim["context_hash"],
            reader_role="history",
            requested_class="SYNTHETIC",
        )
        rest_proj = project_recorded_date_rest(target=SYNTHETIC_TARGET, schedule=synthetic_schedule())
        hist = filter_history_for_target(
            synthetic_history(),
            target_season=int(SYNTHETIC_TARGET["season"]),
            target_week=int(SYNTHETIC_TARGET["week"]),
            target_game_id=str(SYNTHETIC_TARGET["game_id"]),
            nominal_kickoff_utc=str(SYNTHETIC_TARGET["nominal_kickoff_utc"]),
        )
        if hist["n_kept"] < 1:
            raise RetroRefuse("synthetic history filter emptied the fixture")
        registry.require_before_reader(
            claim_id=claim["claim_id"],
            context_hash_expected=claim["context_hash"],
            reader_role="model",
            requested_class="SYNTHETIC",
        )
        demo = build_typed_synthetic_input()
        filtered_default = filter_history_for_target(
            demo["history"],
            target_season=int(demo["packet"]["envelope"]["season"]),
            target_week=int(demo["packet"]["envelope"]["week"]),
            target_game_id=str(demo["packet"]["envelope"]["game_id"]),
            nominal_kickoff_utc=str(demo["packet"]["envelope"]["kickoff_utc"]),
        )
        demo["history"] = filtered_default["rows"]
        surface.note("produce_r7_point_margin")
        produced = produce_r7_point_margin(
            mode="SYNTHETIC",
            synthetic_input=demo,
            surface=surface,
            outcome_spy=outcome_spy,
        )
        registry.require_before_reader(
            claim_id=claim["claim_id"],
            context_hash_expected=claim["context_hash"],
            reader_role="outcome",
            requested_class="SYNTHETIC",
        )
        scored = _score_synthetic(float(produced["c_margin"]), float(SYNTHETIC_TARGET["y_margin"]))
        forecast = {
            "game_id": produced["game_id"],
            "if_margin": produced["if_margin"],
            "q2_margin": produced["q2_margin"],
            "c_margin": produced["c_margin"],
            "immutable": True,
            "channel": "SYNTHETIC",
            "apply_linear_totals_calibration": produced.get("apply_linear_totals_calibration"),
        }
        spent = registry.spend(claim["claim_id"])
        receipt = {
            "ok": True,
            "cert": CERT,
            "package": PACKAGE,
            "profile": PROFILE,
            "owner_clear": OWNER_CLEAR,
            "design": DESIGN,
            "history_order": HISTORY_ORDER,
            "cos_accept": COS_ACCEPT,
            "channel": "SYNTHETIC",
            "ready_for_real_exec": False,
            "science_hold": True,
            "strict_live_profile": STRICT_LIVE_PROFILE,
            "strict_live_status": STRICT_LIVE_STATUS,
            "calendar_id": CALENDAR_ID,
            "claim": spent,
            "recorded_date_rest": rest_proj,
            "history_filter": {k: hist[k] for k in hist if k != "rows"},
            "forecast": forecast,
            "scoring": scored,
            "metrics": {
                "n": 1,
                "primary_abs_c_minus_y": scored["abs_c_minus_y"],
                "bootstrap_run": False,
                "declared_B": BOOTSTRAP_B,
                "declared_seed": BOOTSTRAP_SEED,
            },
            "model_called": True,
            "outcome_reads": outcome_spy.reads,
            "surface_notes": surface.count,
            "env_grant": False,
        }
        dest.mkdir(parents=True, exist_ok=True)
        write_json(dest / "SYNTHETIC_FORECAST.json", forecast)
        write_json(dest / "receipt.json", receipt)
        return receipt
    except Exception as exc:
        if claim["claim_id"] in (registry.get(claim["claim_id"]) or {}) or registry.get(claim["claim_id"]):
            try:
                registry.fail(claim["claim_id"], reason=str(exc))
            except RetroRefuse:
                pass
        raise


def run_preflight(*, root: Path | None = None) -> dict[str, Any]:
    repo = repo_root() if root is None else Path(root)
    dest = repo / OPS_REL
    dest.mkdir(parents=True, exist_ok=True)
    pins = {
        "spec": require_pin(repo, SPEC_REL, SPEC_SHA256),
        "clarifications": require_pin(repo, CLARIFICATIONS_REL, CLARIFICATIONS_SHA256),
        "nominal": require_pin(repo, NOMINAL_REL, NOMINAL_SHA256),
        "rest_meta": require_pin(repo, REST_META_REL, REST_META_SHA256),
        "identity": require_pin(repo, IDENTITY_REL, IDENTITY_SHA256),
    }
    identity = bind_identity_pointers(repo)
    rest_pin = bind_rest_pin(repo)
    recomputed = _recompute_rest_pin(repo)
    # Strict live-causal profile must still refuse missing actual kickoff.
    live_unchanged = False
    try:
        bind_rest_from_et_calendar(
            home_team="LAC",
            away_team="LAR",
            kickoff_utc="2018-10-12T00:20:00Z",
            physical_schedule=[{"game_id": "X", "season": 2018, "week": 1, "season_type": "REG",
                                "home_team": "LAC", "away_team": "MIA", "kickoff_utc": "2018-09-09T17:00:00Z",
                                "status": "PLAYED", "kickoff_kind": "ACTUAL_KICKOFF", "source": "SYNTHETIC"}],
            target_season=2018,
        )
    except Exception:
        live_unchanged = True
    if not live_unchanged:
        raise RetroRefuse("strict actual-kickoff profile no longer refuses missing actual_kickoff_utc")

    registry = AuthorityRegistry()
    outcome_spy = OutcomeReadSpy()
    surface = ForbiddenSurfaceSpy()
    invalids = {
        "absent_claim": run_invalid_path(
            registry=registry, outcome_spy=outcome_spy, surface=surface,
            claim_id=None, context_hash=None, requested_class="SYNTHETIC",
        ),
        "real_request": run_invalid_path(
            registry=registry, outcome_spy=outcome_spy, surface=surface,
            claim_id="nope", context_hash="0" * 64, requested_class="REAL",
        ),
        "r5_reuse": None,
    }
    try:
        registry.issue_synthetic_claim(context={"x": 1}, claim_id="ARCHIVED_R5_CONSUMED_CLAIM")
        invalids["r5_reuse"] = {"refused": False}
    except RetroRefuse as exc:
        invalids["r5_reuse"] = {"refused": True, "reason": str(exc), "outcome_reads": 0, "model_called": False}

    spy_ctrl = run_spy_positive_control()
    synthetic = run_synthetic_executor(root=repo, dest=dest / "synthetic_chain")

    # spent claim cannot retry
    spent_retry = run_invalid_path(
        registry=AuthorityRegistry(),
        outcome_spy=OutcomeReadSpy(),
        surface=ForbiddenSurfaceSpy(),
        claim_id=synthetic["claim"]["claim_id"],
        context_hash=synthetic["claim"]["context_hash"],
        requested_class="SYNTHETIC",
    )
    # The claim lives on the executor registry, not this fresh one — prove on the same registry via a local replay.
    replay_reg = AuthorityRegistry()
    replay_claim = replay_reg.issue_synthetic_claim(context={"replay": True})
    replay_reg.spend(replay_claim["claim_id"])
    spent_retry = run_invalid_path(
        registry=replay_reg,
        outcome_spy=OutcomeReadSpy(),
        surface=ForbiddenSurfaceSpy(),
        claim_id=replay_claim["claim_id"],
        context_hash=replay_claim["context_hash"],
        requested_class="SYNTHETIC",
    )

    schema = real_data_projection_schema()
    receipt = {
        "ok": True,
        "cert": CERT,
        "status": "SYNTHETIC_EXECUTOR_READY_REAL_EXEC_HOLD",
        "ready_for_real_exec": False,
        "accepted": False,
        "package": PACKAGE,
        "profile": PROFILE,
        "owner_clear": OWNER_CLEAR,
        "design": DESIGN,
        "history_order": HISTORY_ORDER,
        "cos_accept": COS_ACCEPT,
        "pins": pins,
        "identity": {k: identity[k] for k in identity if k != "rows"},
        "rest_pin": rest_pin,
        "rest_recomputed_496": recomputed,
        "strict_live_unchanged": live_unchanged,
        "strict_live_status": STRICT_LIVE_STATUS,
        "invalid_paths": {**invalids, "spent_retry": spent_retry},
        "spy_positive_control": spy_ctrl,
        "synthetic_executor": {
            "ok": synthetic["ok"],
            "game_id": synthetic["forecast"]["game_id"],
            "if_margin": synthetic["forecast"]["if_margin"],
            "q2_margin": synthetic["forecast"]["q2_margin"],
            "c_margin": synthetic["forecast"]["c_margin"],
            "model_called": True,
            "claim_status": synthetic["claim"]["status"],
            "abs_c_minus_y": synthetic["scoring"]["abs_c_minus_y"],
        },
        "real_data_projection_schema": schema,
        "n1_n3_nonblocking": n1_n3_nonblocking(),
        "ntbb_k_integrated": False,
        "kernel_frozen_from_d0bb6bef": False,
        "kernel_frozen_from_a807af22": False,
        "package_accepted": False,
        "direct_paths_open": True,
        "return_58427": "58427",
        "science_hold": True,
        "produced_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "command": EXPECTED_COMMAND,
    }
    write_json(dest / "receipt.json", receipt)
    write_json(dest / "REAL_PROJECTION_SCHEMA.json", schema)
    write_json(dest / "MISSING.json", {
        "n": 2,
        "missing": [
            {
                "locator": "frozen median-spread market-point digest for same96 POINT-ERROR",
                "sha256_pin": MARKET_POINT_DIGEST_SHA256,
                "working_tree": "ABSENT",
                "source": "spec-named pin; not invented prices",
            },
            {
                "locator": "archived R5 comparison artifact",
                "sha256_pin": ARCHIVED_R5_SHA256,
                "working_tree": "ABSENT",
                "role": "reference only — never regenerate",
            },
        ],
    })
    return receipt


def main() -> int:
    receipt = run_preflight()
    print(
        json.dumps(
            {
                "ok": receipt["ok"],
                "status": receipt["status"],
                "ready_for_real_exec": receipt["ready_for_real_exec"],
                "identity_n": receipt["identity"]["n"],
                "rest_matched": receipt["rest_recomputed_496"]["matched"],
                "synthetic_c": receipt["synthetic_executor"]["c_margin"],
                "command": receipt["command"],
            },
            sort_keys=True,
        )
    )
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
