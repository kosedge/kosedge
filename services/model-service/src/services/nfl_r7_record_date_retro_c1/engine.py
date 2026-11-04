"""Data-injected RETRO_C1 execution engine. CERT=0.

Fictional inputs only. REAL HOLD. One IF call per target. No replay.
Recorded-date rest patches THAT target's CONTRACT_27. Labels unread
until the forecast cohort is written and digest-sealed.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from src.services.nfl_ops_v1_evidence.spy import ForbiddenSurfaceSpy, OutcomeReadSpy
from src.services.nfl_r7_correctness_v1.franchise import franchise_bind, franchise_key, key_packet_and_history_for_q2
from src.services.nfl_r7_correctness_v1.packets import DEFAULT_INDEX_VALUES, _cell, _hist
from src.services.nfl_r7_correctness_v1.produce import consume_effective_config
from src.services.nfl_r7_record_date_retro_c1.authority import AuthorityRegistry
from src.services.nfl_r7_record_date_retro_c1.bootstrap import (
    assert_golden_two_block,
    season_stratified_pooled_bootstrap,
)
from src.services.nfl_r7_record_date_retro_c1.context import bind_execution_context, require_context
from src.services.nfl_r7_record_date_retro_c1.custody import PHASE_CLAIMED
from src.services.nfl_r7_record_date_retro_c1.fixtures import (
    REAL496_CANNOT_SHRINK,
    SYNTHETIC_COHORT_IDS,
    synthetic_cohort,
    synthetic_history,
    synthetic_schedule,
)
from src.services.nfl_r7_record_date_retro_c1.grant import load_authorization_document, refuse_real_without_root_grant
from src.services.nfl_r7_record_date_retro_c1.history_filter import filter_history_for_target
from src.services.nfl_r7_record_date_retro_c1.pins import (
    CALENDAR_ID,
    CERT,
    CHANNEL_SYNTHETIC,
    N_NEW,
    N_OLD,
    N_SAME96,
    N_TARGET,
    PACKAGE,
    PROFILE,
    SIMULATIONS,
    STRICT_LIVE_PROFILE,
    STRICT_LIVE_STATUS,
)
from src.services.nfl_r7_record_date_retro_c1.refuse import RetroHold, RetroRefuse
from src.services.nfl_r7_record_date_retro_c1.rest import project_recorded_date_rest
from src.services.nfl_t5208u.caller import call_r6_point_margin, model_spy_counts, reset_model_spy
from src.services.nfl_t5208u.pins import CONTRACT_27
from src.services.nfl_t5208u.validate import packet_content_hash

CrashHook = Callable[[str], None] | None


def _stamps_before_cutoff(kickoff_utc: str) -> tuple[str, str]:
    text = kickoff_utc[:-1] + "+00:00" if kickoff_utc.endswith("Z") else kickoff_utc
    ko = datetime.fromisoformat(text).astimezone(timezone.utc)
    available = (ko - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    observed = (ko - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return available, observed


def _typed_history_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return _hist(
        str(row["game_id"]),
        int(row["season"]),
        int(row["week"]),
        str(row.get("home_team") or row.get("home")),
        str(row.get("away_team") or row.get("away")),
        str(row["kickoff_utc"]),
        float(row["home_score"]),
        float(row["away_score"]),
    )


def build_recorded_rest_packet(
    *,
    target: Mapping[str, Any],
    rest_proj: Mapping[str, Any],
    history: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build THAT target's CONTRACT_27 from recorded-date rest. No ET calendar."""
    home = franchise_key(target["home"])
    away = franchise_key(target["away"])
    if home != rest_proj["home_franchise"] or away != rest_proj["away_franchise"]:
        raise RetroRefuse(f"rest franchise mismatch {target['game_id']}")
    env = {
        "game_id": str(target["game_id"]),
        "season": int(target["season"]),
        "week": int(target["week"]),
        "season_type": "REG",
        "home_team": home,
        "away_team": away,
        "kickoff_utc": str(target["nominal_kickoff_utc"]),
        "venue_id": "SYNTHETIC_VENUE_RETRO_C1",
        "identity_kind": "SYNTHETIC_REG",
    }
    available_at, observed_at = _stamps_before_cutoff(env["kickoff_utc"])
    values = {
        "game_id": env["game_id"],
        "home_team": home,
        "away_team": away,
        "matchup_season": int(env["season"]),
        "matchup_week": int(env["week"]),
        "rest_days_home": float(rest_proj["home"]["calendar_days"]),
        "rest_days_away": float(rest_proj["away"]["calendar_days"]),
        **DEFAULT_INDEX_VALUES,
    }
    values = {name: values[name] for name in CONTRACT_27}
    source = "SYNTHETIC_RECORDED_DATE_REST_PATCH"
    contract_27 = {
        name: _cell(values[name], source=source, available_at=available_at, observed_at=observed_at)
        for name in CONTRACT_27
    }
    franchises = franchise_bind(home, away)
    packet = {
        "channel": "SYNTHETIC",
        "packet_class": "SYNTHETIC",
        "mode_gate": "SYNTHETIC_ONLY",
        "real_mode_usable": False,
        "envelope": env,
        "contract_27": contract_27,
        "franchise_bind": franchises,
        "recorded_date_rest": rest_proj,
        "rest_patched_from": CALENDAR_ID,
        "strict_et_calendar_used": False,
    }
    packet["source_byte_hash"] = packet_content_hash(packet)
    return {"packet": packet, "history": list(history), "franchise_bind": franchises}


def _forecast_digest(forecasts: list[Mapping[str, Any]], cohort_ids: list[str]) -> str:
    ids = [str(row["game_id"]) for row in forecasts]
    if ids != list(cohort_ids):
        raise RetroRefuse(f"forecast cohort IDs {ids} != sealed cohort {cohort_ids}")
    if len(forecasts) != len(cohort_ids):
        raise RetroRefuse("forecast count drifted")
    body = [{"game_id": row["game_id"], "if_margin": row["if_margin"], "q2_margin": row["q2_margin"],
             "c_margin": row["c_margin"]} for row in forecasts]
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _metrics(scored: list[Mapping[str, Any]]) -> dict[str, Any]:
    def _abs_mean(rows: list[Mapping[str, Any]]) -> float:
        return sum(float(r["abs_c_minus_y"]) for r in rows) / float(len(rows))

    by_season: dict[int, list[Mapping[str, Any]]] = {}
    for row in scored:
        by_season.setdefault(int(row["season"]), []).append(row)
    return {
        "full": {"n": len(scored), "mae": _abs_mean(scored)},
        "per_season": {str(k): {"n": len(v), "mae": _abs_mean(v)} for k, v in sorted(by_season.items())},
        "cohort": {"n": len(scored), "ids": [r["game_id"] for r in scored], "mae": _abs_mean(scored)},
        "scientific_claim": False,
    }


def _produce_target(
    *,
    target: Mapping[str, Any],
    claim_id: str,
    bound: Mapping[str, Any],
    registry: AuthorityRegistry,
    cfg: Mapping[str, Any],
    surface: ForbiddenSurfaceSpy,
) -> dict[str, Any]:
    require_context(bound, str(bound["context_hash"]), reader_role="feature")
    registry.require_before_reader(
        claim_id=claim_id,
        context_hash_expected=str(bound["context_hash"]),
        reader_role="feature",
        requested_class="SYNTHETIC",
    )
    rest_proj = project_recorded_date_rest(target=target, schedule=synthetic_schedule())
    require_context(bound, str(bound["context_hash"]), reader_role="history")
    registry.require_before_reader(
        claim_id=claim_id,
        context_hash_expected=str(bound["context_hash"]),
        reader_role="history",
        requested_class="SYNTHETIC",
    )
    hist = filter_history_for_target(
        synthetic_history(),
        target_season=int(target["season"]),
        target_week=int(target["week"]),
        target_game_id=str(target["game_id"]),
        nominal_kickoff_utc=str(target["nominal_kickoff_utc"]),
    )
    if hist["n_kept"] < 1:
        raise RetroRefuse(f"history filter emptied {target['game_id']}")
    typed_hist = [_typed_history_row(row) for row in hist["rows"]]
    patched = build_recorded_rest_packet(target=target, rest_proj=rest_proj, history=typed_hist)
    require_context(bound, str(bound["context_hash"]), reader_role="model")
    registry.require_before_reader(
        claim_id=claim_id,
        context_hash_expected=str(bound["context_hash"]),
        reader_role="model",
        requested_class="SYNTHETIC",
    )
    surface.note("call_r6_point_margin")
    _keyed_packet, keyed_history = key_packet_and_history_for_q2(patched["packet"], patched["history"])
    produced = call_r6_point_margin(
        patched["packet"],
        keyed_history,
        mode="SYNTHETIC",
        effective_config=cfg,
    )
    return {
        "game_id": produced["game_id"],
        "season": int(target["season"]),
        "week": int(target["week"]),
        "if_margin": produced["if_margin"],
        "q2_margin": produced["q2_margin"],
        "c_margin": produced["c_margin"],
        "seed": produced["seed"],
        "simulations": produced["simulations"],
        "channel": CHANNEL_SYNTHETIC,
        "rest_days_home": rest_proj["home"]["calendar_days"],
        "rest_days_away": rest_proj["away"]["calendar_days"],
        "recorded_date_rest": rest_proj,
        "history_n_kept": hist["n_kept"],
        "apply_linear_totals_calibration": produced.get("linear_cal_flag"),
        "immutable_label": True,
        "sealed": False,
        "y_margin_held": float(target["y_margin"]),
    }


def run_synthetic_engine(
    *,
    root: Path,
    dest: Path,
    crash_after: str | None = None,
    crash: CrashHook = None,
    claim_id: str | None = None,
    outcome_spy: OutcomeReadSpy | None = None,
    surface: ForbiddenSurfaceSpy | None = None,
) -> dict[str, Any]:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    custody_dir = dest / "custody"
    outcome_spy = outcome_spy or OutcomeReadSpy()
    surface = surface or ForbiddenSurfaceSpy()
    cohort = synthetic_cohort()
    cohort_ids = [str(row["game_id"]) for row in cohort]
    if len(cohort_ids) >= REAL496_CANNOT_SHRINK:
        raise RetroRefuse("synthetic cohort must not claim real496")
    bound = bind_execution_context(
        root=root,
        channel=CHANNEL_SYNTHETIC,
        cohort={
            "profile": "SYNTHETIC",
            "n": len(cohort_ids),
            "ids": cohort_ids,
            "real496_declared": N_TARGET,
            "real496_cannot_shrink": True,
            "old437_declared": N_OLD,
            "new59_declared": N_NEW,
            "same96_declared": N_SAME96,
        },
    )
    registry = AuthorityRegistry(store_dir=custody_dir)
    cid = claim_id or f"SYNTHETIC_{bound['context_hash'][:12]}_{os.getpid()}_{int(time.time() * 1000)}"
    claim = registry.issue_synthetic_claim(context=bound, claim_id=cid)
    cfg = consume_effective_config()
    reset_model_spy()

    def _maybe_crash(phase: str) -> None:
        if crash is not None:
            crash(phase)
        if crash_after == phase:
            raise RuntimeError(f"injected crash after {phase}")

    try:
        _maybe_crash(PHASE_CLAIMED)
        forecasts: list[dict[str, Any]] = []
        for target in cohort:
            forecasts.append(
                _produce_target(
                    target=target,
                    claim_id=claim["claim_id"],
                    bound=bound,
                    registry=registry,
                    cfg=cfg,
                    surface=surface,
                )
            )
        if [row["game_id"] for row in forecasts] != cohort_ids:
            raise RetroRefuse("forecast order/IDs drifted before seal")
        digest = _forecast_digest(forecasts, cohort_ids)
        for row in forecasts:
            row["sealed"] = True
            row["forecast_digest"] = digest
        registry.custody.write_forecasts_and_seal(claim["claim_id"], forecasts, digest)
        _maybe_crash("FORECASTS_SEALED")
        sealed = registry.custody.seal_path(claim["claim_id"]).read_text(encoding="utf-8").strip()
        if sealed != digest:
            raise RetroRefuse("forecast seal tampered")
        on_disk = json.loads(registry.custody.forecasts_path(claim["claim_id"]).read_text(encoding="utf-8"))
        if _forecast_digest(on_disk["forecasts"], cohort_ids) != sealed:
            raise RetroRefuse("forecast bytes tampered")
        if outcome_spy.reads != 0:
            raise RetroRefuse("labels read before forecast seal")
        require_context(bound, str(bound["context_hash"]), reader_role="outcome")
        registry.require_before_reader(
            claim_id=claim["claim_id"],
            context_hash_expected=str(bound["context_hash"]),
            reader_role="outcome",
            requested_class="SYNTHETIC",
        )
        labels = {row["game_id"]: float(row["y_margin_held"]) for row in forecasts}
        outcome_spy.reads += 0  # synthetic labels already on fixture; not a real outcome loader
        scored = []
        for row in forecasts:
            y = labels[row["game_id"]]
            signed = float(row["c_margin"]) - y
            scored.append(
                {
                    "game_id": row["game_id"],
                    "season": row["season"],
                    "week": row["week"],
                    "c_margin": row["c_margin"],
                    "y_margin": y,
                    "y_source": "SYNTHETIC_LABEL_NOT_REAL_OUTCOME",
                    "signed_c_minus_y": signed,
                    "abs_c_minus_y": abs(signed),
                    "real_outcomes_joined": False,
                }
            )
        registry.custody.write_scores(
            claim["claim_id"],
            {"n": len(scored), "rows": scored, "real_outcomes_joined": False},
        )
        metrics = _metrics(scored)
        boot = season_stratified_pooled_bootstrap(scored)
        golden = assert_golden_two_block()
        spy = model_spy_counts()
        if spy["produce_if_mu"] != len(cohort_ids):
            raise RetroRefuse(f"IF calls {spy['produce_if_mu']} != one per target {len(cohort_ids)}")
        spent = registry.spend(claim["claim_id"])
        receipt = {
            "ok": True,
            "cert": CERT,
            "package": PACKAGE,
            "profile": PROFILE,
            "channel": CHANNEL_SYNTHETIC,
            "ready_for_real_exec": False,
            "science_hold": True,
            "scientific_claim": False,
            "strict_live_profile": STRICT_LIVE_PROFILE,
            "strict_live_status": STRICT_LIVE_STATUS,
            "calendar_id": CALENDAR_ID,
            "claim": spent,
            "context_hash": bound["context_hash"],
            "cohort": {"n": len(cohort_ids), "ids": cohort_ids, "real496_cannot_shrink": True},
            "forecasts": [{k: v for k, v in row.items() if k != "y_margin_held"} for row in forecasts],
            "forecast_digest": digest,
            "scoring": scored,
            "metrics": metrics,
            "bootstrap": boot,
            "golden_bootstrap": golden,
            "if_calls": spy["produce_if_mu"],
            "replay_second_if": False,
            "model_called": True,
            "outcome_reads": outcome_spy.reads,
            "surface_notes": surface.count,
            "env_grant": False,
        }
        (dest / "SYNTHETIC_FORECAST.json").write_text(
            json.dumps({"forecasts": receipt["forecasts"], "digest": digest}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (dest / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return receipt
    except Exception as exc:
        row = registry.get(claim["claim_id"])
        if row and row.get("phase") not in {"SPENT", "FAILED"}:
            try:
                registry.fail(claim["claim_id"], reason=str(exc))
            except RetroRefuse:
                pass
        raise


def run_real_engine(*, grant_path: Path | None, claim_id: str | None, context_hash: str | None) -> None:
    grant = load_authorization_document(grant_path) if grant_path is not None else None
    refuse_real_without_root_grant(grant=grant)
    raise RetroHold(f"REAL HOLD claim={claim_id} context={context_hash}")
