"""R6 pure caller: frozen IF + Q2 → POINT_MARGIN only. SYNTHETIC packets."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping

from src.services.nfl_t5107u.builder import challenger_margin
from src.services.nfl_t5107u.if_produce import produce_if_mu, seed_for
from src.services.nfl_t5107u.q2 import (
    A_Q2,
    B_Q2,
    asof_for_targets,
    assert_asof_no_self_target,
    q2_pm_new,
    verify_q2_transfer_policy,
)
from src.services.nfl_t5208u.if_tree import preflight_if_tree
from src.services.nfl_t5208u.packets import (
    PacketRefuse,
    contract_packet_for_if,
    history_games_for_q2,
    refuse_real_mode,
)
from src.services.nfl_t5208u.pins import (
    CANDIDATE_WEIGHT,
    C_FORMULA,
    CHANNEL_SYNTHETIC,
    FORBIDDEN_OUTPUT_KEYS,
    MARKET_BLEND,
    OUTPUT_KIND,
    SCHEMA_ID,
    SIMULATIONS,
)
from src.services.nfl_t5208u.schema import schema_document, schema_hash
from src.services.nfl_t5208u.validate import validate_before_model

_MODEL_SPY = {
    "produce_if_mu": 0,
    "asof_for_targets": 0,
}


def reset_model_spy() -> None:
    for key in _MODEL_SPY:
        _MODEL_SPY[key] = 0


def model_spy_counts() -> dict[str, int]:
    return dict(_MODEL_SPY)


class CallerRefuse(ValueError):
    """Fail-closed R6 caller."""


def _finite_number(value: Any, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CallerRefuse(f"{name} is not a number")
    number = float(value)
    if not math.isfinite(number):
        raise CallerRefuse(f"{name} is not finite")
    return number


def _strip_forbidden(payload: Mapping[str, Any]) -> None:
    keys = {str(k).casefold() for k in payload}
    blob = " ".join(keys)
    for token in FORBIDDEN_OUTPUT_KEYS:
        if token in keys or token in blob:
            raise CallerRefuse(f"POINT_MARGIN output contains forbidden key {token}")


def produce_q2_margin(
    packet: Mapping[str, Any],
    history: list[Mapping[str, Any]],
) -> dict[str, Any]:
    transfer = verify_q2_transfer_policy(proposed_refit=False)
    target, hist = history_games_for_q2(packet, history)
    _MODEL_SPY["asof_for_targets"] += 1
    feats = asof_for_targets(hist, [target])
    assert_asof_no_self_target(hist, feats)
    if len(feats) != 1:
        raise PacketRefuse(f"expected 1 Q2 feature row, got {len(feats)}")
    feat = feats[0]
    margin = q2_pm_new(feat.rating_diff)
    return {
        "q2_margin": _finite_number(margin, name="q2_margin"),
        "rating_diff": _finite_number(feat.rating_diff, name="rating_diff"),
        "n_asof_games": int(feat.n_asof_games),
        "a_q2": A_Q2,
        "b_q2": B_Q2,
        "transfer": transfer,
    }


def _require_consumed_config(effective_config: Mapping[str, Any]) -> Mapping[str, Any]:
    meta = effective_config.get("meta")
    if not isinstance(meta, Mapping) or meta.get("consumed") is not True:
        raise CallerRefuse("effective_config was not consumed")
    if meta.get("immutable") is not True:
        raise CallerRefuse("effective_config is not immutable")
    if meta.get("ambient_env_reread") is not False:
        raise CallerRefuse("effective_config allows ambient env reread")
    helper = effective_config.get("helper")
    simulator = effective_config.get("simulator")
    framework = effective_config.get("framework")
    if not isinstance(helper, Mapping) or not isinstance(simulator, Mapping) or not isinstance(framework, Mapping):
        raise CallerRefuse("effective_config missing framework/simulator/helper")
    return effective_config


def _framework_overrides(cfg: Mapping[str, Any]) -> dict[str, Any]:
    fw = cfg["framework"]
    settings = fw.get("settings") if isinstance(fw.get("settings"), Mapping) else {}
    return {
        "priors": {
            "base_total_points": float(settings.get("prior_total_points", 45.3)),
            "base_margin_points": float(settings.get("prior_margin_points", 1.5)),
            "home_field_points": float(settings.get("home_field_points", 1.05)),
            "base_score_stdev": float(settings.get("base_score_stdev", 9.8)),
        },
        "factors": {
            "rest_travel": {
                "margin_per_day": float(settings.get("rest_margin_per_day", 0.18)),
                "total_per_day_abs": float(settings.get("rest_total_per_day_abs", 0.12)),
            },
            "base_efficiency": {
                "margin_weight": float(settings.get("base_eff_margin_weight", 16.0)),
                "total_weight": float(settings.get("base_eff_total_weight", 10.5)),
            },
        },
    }


def call_r6_point_margin(
    packet: Mapping[str, Any],
    history: list[Mapping[str, Any]],
    *,
    mode: str = CHANNEL_SYNTHETIC,
    tree: Path | None = None,
    effective_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    refuse_real_mode(mode, packet)
    binds = validate_before_model(packet, history)
    preflight = preflight_if_tree()
    if_tree = Path(tree) if tree is not None else Path(preflight["tree_path"])
    if str(if_tree) != str(preflight["tree_path"]) and tree is not None:
        # Explicit tree still has to pass the same content pins.
        if str(if_tree.resolve()) != str(Path(preflight["tree_path"]).resolve()):
            raise CallerRefuse("explicit tree is not the preflighted in-repo IF tree")

    cfg = _require_consumed_config(effective_config) if effective_config is not None else None
    sims = int(cfg["simulator"]["simulations"]) if cfg is not None else SIMULATIONS
    blend = int(cfg["simulator"]["market_blend"]) if cfg is not None else MARKET_BLEND
    weight = float(cfg["helper"]["candidate_weight"]) if cfg is not None else CANDIDATE_WEIGHT
    c_formula = str(cfg["helper"]["c_formula"]) if cfg is not None else C_FORMULA
    overrides = _framework_overrides(cfg) if cfg is not None else None

    if_packet = contract_packet_for_if(packet)
    _MODEL_SPY["produce_if_mu"] += 1
    produced = produce_if_mu(if_packet, tree=if_tree, simulations=sims, config_overrides=overrides)
    if_margin = _finite_number(produced.get("if_margin_mu"), name="if_margin")
    if int(produced.get("market_blend", -1)) != blend:
        raise CallerRefuse(f"market_blend {produced.get('market_blend')} != {blend}")
    if int(produced.get("simulations", -1)) != sims:
        raise CallerRefuse(f"simulations {produced.get('simulations')} != {sims}")
    seed = int(produced["seed"])
    expected_seed = seed_for(str(produced["game_id"]))
    if seed != expected_seed:
        raise CallerRefuse(f"seed {seed} != seed_for(game_id) {expected_seed}")

    if cfg is not None and cfg["helper"].get("canonical_state_slots") is True:
        from src.services.nfl_r7_correctness_v1.q2_canonical import produce_q2_margin_canonical

        _MODEL_SPY["asof_for_targets"] += 1
        q2_out = produce_q2_margin_canonical(
            packet,
            history,
            lam=float(cfg["helper"]["ridge"]),
            regress_frac=float(cfg["helper"]["prior_carry"]),
        )
    else:
        q2_out = produce_q2_margin(packet, history)
    q2_margin = q2_out["q2_margin"]
    c_margin = _finite_number(
        challenger_margin(if_margin, q2_margin, w=weight),
        name="c_margin",
    )
    expected_c = weight * if_margin + weight * q2_margin
    if abs(c_margin - expected_c) > 1e-12:
        raise CallerRefuse(f"C formula failed: {c_margin} != {weight}*{if_margin}+{weight}*{q2_margin}")

    schema_id_hash = schema_hash(schema_document())
    if binds["seal_utc"] != binds["cutoff_utc"]:
        raise CallerRefuse("seal_utc must equal cutoff_utc (KO−60)")
    for key in ("packet_hash", "history_hash", "config_hash", "code_hash"):
        digest = binds[key]
        if not digest or digest == schema_id_hash or digest == "0" * 64:
            raise CallerRefuse(f"{key} must be an actual bind, not schema_hash/empty")

    out = {
        "schema_id": SCHEMA_ID,
        "schema_hash": schema_id_hash,
        "packet_hash": binds["packet_hash"],
        "history_hash": binds["history_hash"],
        "config_hash": binds["config_hash"],
        "code_hash": binds["code_hash"],
        "cutoff_utc": binds["cutoff_utc"],
        "seal_utc": binds["seal_utc"],
        "kickoff_utc": binds["kickoff_utc"],
        "output_kind": OUTPUT_KIND,
        "channel": CHANNEL_SYNTHETIC,
        "cert": 0,
        "game_id": str(produced["game_id"]),
        "if_margin": if_margin,
        "q2_margin": q2_margin,
        "c_margin": c_margin,
        "c_formula": c_formula,
        "candidate_weight": weight,
        "seed": seed,
        "simulations": sims,
        "market_blend": blend,
        "effective_config_bound": cfg is not None,
        "if_tip": produced.get("if_tip"),
        "if_tree": str(if_tree),
        "if_preflight": preflight,
        "q2": {
            "rating_diff": q2_out["rating_diff"],
            "n_asof_games": q2_out["n_asof_games"],
            "a_q2": q2_out["a_q2"],
            "b_q2": q2_out["b_q2"],
            "parameter_label": q2_out["transfer"]["parameter_label"],
            "fit_policy": q2_out["transfer"]["fit_policy"],
            "refit_performed": q2_out["transfer"]["refit_performed"],
        },
        "envelope": dict(packet.get("envelope") or {}),
        "binds": {
            "packet_hash": binds["packet_hash"],
            "history_hash": binds["history_hash"],
            "config_hash": binds["config_hash"],
            "code_hash": binds["code_hash"],
            "schema_hash_is_not_an_input_bind": True,
        },
    }
    _strip_forbidden(out)
    return out


def replay_call(
    packet: Mapping[str, Any],
    history: list[Mapping[str, Any]],
    *,
    mode: str = CHANNEL_SYNTHETIC,
    effective_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    first = call_r6_point_margin(packet, history, mode=mode, effective_config=effective_config)
    second = call_r6_point_margin(packet, history, mode=mode, effective_config=effective_config)
    for key in ("if_margin", "q2_margin", "c_margin", "seed", "packet_hash", "history_hash"):
        if first[key] != second[key]:
            raise CallerRefuse(f"replay mismatch on {key}: {first[key]} vs {second[key]}")
    return {"first": first, "second": second, "replay_ok": True}
