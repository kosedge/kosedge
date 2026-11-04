"""Shared data-injected RETRO_C1 execution engine. CERT=0.

Readers + model callback are injected. Synthetic CLI supplies fictional
adapters. REAL uses the same engine after Root-pinned digest/context and a
non-empty approved reader registry — refused NOW because that registry is
empty. Labels are first read only after every forecast is sealed.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from src.services.nfl_ops_v1_evidence.spy import ForbiddenSurfaceSpy, OutcomeReadSpy
from src.services.nfl_r7_correctness_v1.franchise import franchise_bind, franchise_key
from src.services.nfl_r7_correctness_v1.packets import _cell, _hist
from src.services.nfl_r7_record_date_retro_c1.adapters import (
    LABEL_KEYS,
    LabelVault,
    build_synthetic_readers,
    strip_labels,
)
from src.services.nfl_r7_record_date_retro_c1.authority import AuthorityRegistry
from src.services.nfl_r7_record_date_retro_c1.bootstrap import (
    assert_golden_two_block,
    game_sensitivity_bootstrap,
    season_stratified_pooled_bootstrap,
)
from src.services.nfl_r7_record_date_retro_c1.context import bind_execution_context, require_context
from src.services.nfl_r7_record_date_retro_c1.custody import PHASE_CLAIMED
from src.services.nfl_r7_record_date_retro_c1.fixtures import REAL496_CANNOT_SHRINK
from src.services.nfl_r7_record_date_retro_c1.grant import (
    APPROVED_REAL_READERS,
    ROOT_APPROVED_AUTH_DIGEST,
    load_authorization_document,
)
from src.services.nfl_r7_record_date_retro_c1.history_filter import filter_history_for_target
from src.services.nfl_r7_record_date_retro_c1.metrics import design_25194_metrics, paired_abs_loss_rows
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
    STRICT_LIVE_PROFILE,
    STRICT_LIVE_STATUS,
)
from src.services.nfl_r7_record_date_retro_c1.refuse import RetroHold, RetroRefuse
from src.services.nfl_r7_record_date_retro_c1.rest import project_recorded_date_rest
from src.services.nfl_t5208u.caller import model_spy_counts, reset_model_spy
from src.services.nfl_t5208u.pins import CONTRACT_27
from src.services.nfl_t5208u.validate import packet_content_hash

CrashHook = Callable[[str], None] | None


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
    index_values: Mapping[str, Any],
    stamps: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build THAT target's CONTRACT_27 from recorded-date rest. No ET calendar.

    Stamps come from the injected adapter. Unknown actual/publication stamps
    stay unknown — the engine does not invent historical availability.
    """
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
        "venue_id": str(target.get("venue_id") or "SYNTHETIC_VENUE_RETRO_C1"),
        "identity_kind": str(target.get("identity_kind") or "SYNTHETIC_REG"),
    }
    available_at = None if stamps is None else stamps.get("available_at")
    observed_at = None if stamps is None else stamps.get("observed_at")
    values = {
        "game_id": env["game_id"],
        "home_team": home,
        "away_team": away,
        "matchup_season": int(env["season"]),
        "matchup_week": int(env["week"]),
        "rest_days_home": float(rest_proj["home"]["calendar_days"]),
        "rest_days_away": float(rest_proj["away"]["calendar_days"]),
        **{k: index_values[k] for k in index_values},
    }
    values = {name: values[name] for name in CONTRACT_27}
    source = str(target.get("index_source") or "INJECTED_TARGET27")
    contract_27 = {
        name: _cell(values[name], source=source, available_at=available_at, observed_at=observed_at)
        for name in CONTRACT_27
    }
    franchises = franchise_bind(home, away)
    packet = {
        "channel": str(target.get("channel") or "SYNTHETIC"),
        "packet_class": str(target.get("channel") or "SYNTHETIC"),
        "mode_gate": "SYNTHETIC_ONLY" if str(target.get("channel") or "SYNTHETIC") == "SYNTHETIC" else "REAL_HOLD",
        "real_mode_usable": False,
        "envelope": env,
        "contract_27": contract_27,
        "franchise_bind": franchises,
        "recorded_date_rest": rest_proj,
        "rest_patched_from": CALENDAR_ID,
        "strict_et_calendar_used": False,
        "stamps_unknown": stamps is None or stamps.get("available_at") is None,
    }
    packet["source_byte_hash"] = packet_content_hash(packet)
    return {"packet": packet, "history": list(history), "franchise_bind": franchises}


def _forecast_digest(forecasts: list[Mapping[str, Any]], cohort_ids: list[str]) -> str:
    ids = [str(row["game_id"]) for row in forecasts]
    if ids != list(cohort_ids):
        raise RetroRefuse(f"forecast cohort IDs {ids} != sealed cohort {cohort_ids}")
    if len(forecasts) != len(cohort_ids):
        raise RetroRefuse("forecast count drifted")
    for row in forecasts:
        leaked = sorted(LABEL_KEYS.intersection(row))
        if leaked:
            raise RetroRefuse(f"forecast carried labels before/at seal {leaked}")
    body = [{"game_id": row["game_id"], "if_margin": row["if_margin"], "q2_margin": row["q2_margin"],
             "c_margin": row["c_margin"]} for row in forecasts]
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _assert_sealed_bytes_have_no_labels(raw: bytes) -> None:
    text = raw.decode("utf-8")
    lowered = text.lower()
    for key in LABEL_KEYS:
        if f'"{key}"' in lowered or f'"{key.lower()}"' in lowered:
            raise RetroRefuse(f"sealed forecast bytes contain label field {key}")


def _produce_target(
    *,
    target: Mapping[str, Any],
    claim_id: str,
    bound: Mapping[str, Any],
    registry: AuthorityRegistry,
    cfg: Mapping[str, Any],
    surface: ForbiddenSurfaceSpy,
    schedule: list[Mapping[str, Any]],
    history_rows: list[Mapping[str, Any]],
    model: Callable[..., dict[str, Any]],
    requested_class: str,
) -> dict[str, Any]:
    if LABEL_KEYS.intersection(target):
        raise RetroRefuse("target27 carried labels into forecast produce")
    require_context(bound, str(bound["context_hash"]), reader_role="feature")
    registry.require_before_reader(
        claim_id=claim_id,
        context_hash_expected=str(bound["context_hash"]),
        reader_role="feature",
        requested_class=requested_class,
    )
    rest_proj = project_recorded_date_rest(target=target, schedule=schedule)
    require_context(bound, str(bound["context_hash"]), reader_role="history")
    registry.require_before_reader(
        claim_id=claim_id,
        context_hash_expected=str(bound["context_hash"]),
        reader_role="history",
        requested_class=requested_class,
    )
    hist = filter_history_for_target(
        history_rows,
        target_season=int(target["season"]),
        target_week=int(target["week"]),
        target_game_id=str(target["game_id"]),
        nominal_kickoff_utc=str(target["nominal_kickoff_utc"]),
    )
    if hist["n_kept"] < 1:
        raise RetroRefuse(f"history filter emptied {target['game_id']}")
    typed_hist = [_typed_history_row(row) for row in hist["rows"]]
    index_values = dict(target.get("index_values") or {})
    if not index_values:
        raise RetroRefuse("target27 missing injected index_values")
    stamps = target.get("stamps")
    patched = build_recorded_rest_packet(
        target=target,
        rest_proj=rest_proj,
        history=typed_hist,
        index_values=index_values,
        stamps=stamps,
    )
    require_context(bound, str(bound["context_hash"]), reader_role="model")
    registry.require_before_reader(
        claim_id=claim_id,
        context_hash_expected=str(bound["context_hash"]),
        reader_role="model",
        requested_class=requested_class,
    )
    surface.note("call_r6_point_margin")
    produced = model(patched["packet"], patched["history"], cfg)
    return {
        "game_id": produced["game_id"],
        "season": int(target["season"]),
        "week": int(target["week"]),
        "if_margin": produced["if_margin"],
        "q2_margin": produced["q2_margin"],
        "c_margin": produced["c_margin"],
        "seed": produced["seed"],
        "simulations": produced["simulations"],
        "channel": str(target.get("channel") or CHANNEL_SYNTHETIC),
        "rest_days_home": rest_proj["home"]["calendar_days"],
        "rest_days_away": rest_proj["away"]["calendar_days"],
        "recorded_date_rest": rest_proj,
        "history_n_kept": hist["n_kept"],
        "apply_linear_totals_calibration": produced.get("linear_cal_flag"),
        "immutable_label": True,
        "sealed": False,
    }


def run_engine(
    *,
    root: Path,
    dest: Path,
    readers: Mapping[str, Any],
    requested_class: str,
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
    if requested_class == "REAL":
        registry_probe = AuthorityRegistry(store_dir=custody_dir)
        registry_probe.issue_real_claim(grant=None)
        raise RetroHold("REAL cannot be relabeled SYNTHETIC")
    if requested_class != "SYNTHETIC":
        raise RetroRefuse(f"unsupported requested_class {requested_class}")
    targets = [strip_labels(row) for row in readers["targets"]()]
    for row in targets:
        if LABEL_KEYS.intersection(row):
            raise RetroRefuse("targets reader leaked labels")
    cohort_ids = [str(row["game_id"]) for row in targets]
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
    cfg = readers["config"]()
    reset_model_spy()
    vault: LabelVault = readers["outcomes"]
    schedule = list(readers["schedule"]())
    history_rows = list(readers["history"]())
    model = readers["model"]

    def _maybe_crash(phase: str) -> None:
        if crash is not None:
            crash(phase)
        if crash_after == phase:
            raise RuntimeError(f"injected crash after {phase}")

    try:
        _maybe_crash(PHASE_CLAIMED)
        forecasts: list[dict[str, Any]] = []
        for target in targets:
            forecasts.append(
                _produce_target(
                    target=target,
                    claim_id=claim["claim_id"],
                    bound=bound,
                    registry=registry,
                    cfg=cfg,
                    surface=surface,
                    schedule=schedule,
                    history_rows=history_rows,
                    model=model,
                    requested_class=requested_class,
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
        forecast_path = registry.custody.forecasts_path(claim["claim_id"])
        raw = forecast_path.read_bytes()
        _assert_sealed_bytes_have_no_labels(raw)
        on_disk = json.loads(raw.decode("utf-8"))
        if _forecast_digest(on_disk["forecasts"], cohort_ids) != sealed:
            raise RetroRefuse("forecast bytes tampered")
        if outcome_spy.reads != 0:
            raise RetroRefuse("labels read before forecast seal")
        if getattr(vault, "reads", 0) != 0:
            raise RetroRefuse("label vault read before forecast seal")
        require_context(bound, str(bound["context_hash"]), reader_role="outcome")
        registry.require_before_reader(
            claim_id=claim["claim_id"],
            context_hash_expected=str(bound["context_hash"]),
            reader_role="outcome",
            requested_class=requested_class,
        )
        vault.allow_after_seal()
        if getattr(outcome_spy, "_fn", None) is not None:
            loaded = outcome_spy()
            labels = {gid: float(row["y_margin"]) for gid, row in loaded.items()}
        else:
            labels = vault.read(cohort_ids)
            outcome_spy.reads += 1
        if set(labels) != set(cohort_ids):
            raise RetroRefuse("outcome identity mutation vs sealed forecasts")
        archive = readers["archive"]()
        scored = []
        for row in forecasts:
            y = labels[row["game_id"]]
            signed = float(row["c_margin"]) - y
            scored.append(
                {
                    "game_id": row["game_id"],
                    "season": row["season"],
                    "week": row["week"],
                    "if_margin": row["if_margin"],
                    "q2_margin": row["q2_margin"],
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
        metrics = design_25194_metrics(scored, archive=archive)
        paired_rows = paired_abs_loss_rows(scored, archive=archive)
        boot = season_stratified_pooled_bootstrap(paired_rows)
        sensitivity = game_sensitivity_bootstrap(paired_rows)
        golden = assert_golden_two_block()
        spy_counts = model_spy_counts()
        if spy_counts["produce_if_mu"] != len(cohort_ids):
            raise RetroRefuse(f"IF calls {spy_counts['produce_if_mu']} != one per target {len(cohort_ids)}")
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
            "forecasts": [dict(row) for row in forecasts],
            "forecast_digest": digest,
            "scoring": scored,
            "metrics": metrics,
            "bootstrap": boot,
            "sensitivity": sensitivity,
            "golden_bootstrap": golden,
            "if_calls": spy_counts["produce_if_mu"],
            "replay_second_if": False,
            "model_called": True,
            "outcome_reads": outcome_spy.reads,
            "label_vault_reads": vault.reads,
            "surface_notes": surface.count,
            "env_grant": False,
            "data_injected": True,
            "labels_before_seal": False,
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


def run_synthetic_engine(
    *,
    root: Path,
    dest: Path,
    crash_after: str | None = None,
    crash: CrashHook = None,
    claim_id: str | None = None,
    outcome_spy: OutcomeReadSpy | None = None,
    surface: ForbiddenSurfaceSpy | None = None,
    labels: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    readers = build_synthetic_readers(labels=labels)
    return run_engine(
        root=root,
        dest=dest,
        readers=readers,
        requested_class="SYNTHETIC",
        crash_after=crash_after,
        crash=crash,
        claim_id=claim_id,
        outcome_spy=outcome_spy,
        surface=surface,
    )


def run_real_engine(
    *,
    grant_path: Path | None,
    claim_id: str | None,
    context_hash: str | None,
    root: Path | None = None,
    dest: Path | None = None,
) -> dict[str, Any]:
    """Same engine after Root digest/context. Refused NOW: empty approved registry."""
    grant = load_authorization_document(grant_path) if grant_path is not None else None
    if ROOT_APPROVED_AUTH_DIGEST is None:
        raise RetroHold(
            "REAL refused NOW — approved auth-digest registry empty "
            f"(claim={claim_id} context={context_hash})"
        )
    if grant is None or not grant.get("digest_matches_root"):
        raise RetroHold(
            "REAL denied — Root-pinned auth digest/context mismatch "
            f"(claim={claim_id} context={context_hash})"
        )
    readers = APPROVED_REAL_READERS.get(str(grant["digest"]))
    if not readers:
        raise RetroHold(
            "REAL refused NOW — approved role-bound reader registry empty "
            f"(claim={claim_id} context={context_hash})"
        )
    if dest is None or root is None:
        raise RetroHold("REAL refused NOW — dest/root unbound for same-engine call")
    return run_engine(
        root=root,
        dest=dest,
        readers=readers,
        requested_class="REAL",
        claim_id=claim_id,
    )


def _stamps_before_cutoff(kickoff_utc: str) -> tuple[str, str]:
    """Adapter helper kept for existing timing tests. Not used by the shared engine."""
    from src.services.nfl_r7_record_date_retro_c1.adapters import synthetic_packet_stamps

    stamps = synthetic_packet_stamps(kickoff_utc)
    return str(stamps["available_at"]), str(stamps["observed_at"])
