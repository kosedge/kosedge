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


def call_r6_point_margin(
    packet: Mapping[str, Any],
    history: list[Mapping[str, Any]],
    *,
    mode: str = CHANNEL_SYNTHETIC,
    tree: Path | None = None,
) -> dict[str, Any]:
    refuse_real_mode(mode, packet)
    binds = validate_before_model(packet, history)
    preflight = preflight_if_tree()
    if_tree = Path(tree) if tree is not None else Path(preflight["tree_path"])
    if str(if_tree) != str(preflight["tree_path"]) and tree is not None:
        # Explicit tree still has to pass the same content pins.
        if str(if_tree.resolve()) != str(Path(preflight["tree_path"]).resolve()):
            raise CallerRefuse("explicit tree is not the preflighted in-repo IF tree")

    if_packet = contract_packet_for_if(packet)
    _MODEL_SPY["produce_if_mu"] += 1
    produced = produce_if_mu(if_packet, tree=if_tree)
    if_margin = _finite_number(produced.get("if_margin_mu"), name="if_margin")
    if int(produced.get("market_blend", -1)) != MARKET_BLEND:
        raise CallerRefuse(f"market_blend {produced.get('market_blend')} != 0")
    if int(produced.get("simulations", -1)) != SIMULATIONS:
        raise CallerRefuse(f"simulations {produced.get('simulations')} != {SIMULATIONS}")
    seed = int(produced["seed"])
    expected_seed = seed_for(str(produced["game_id"]))
    if seed != expected_seed:
        raise CallerRefuse(f"seed {seed} != seed_for(game_id) {expected_seed}")

    q2_out = produce_q2_margin(packet, history)
    q2_margin = q2_out["q2_margin"]
    c_margin = _finite_number(
        challenger_margin(if_margin, q2_margin, w=CANDIDATE_WEIGHT),
        name="c_margin",
    )
    expected_c = CANDIDATE_WEIGHT * if_margin + CANDIDATE_WEIGHT * q2_margin
    if abs(c_margin - expected_c) > 1e-12:
        raise CallerRefuse(f"C formula failed: {c_margin} != 0.5*{if_margin}+0.5*{q2_margin}")

    schema_id_hash = schema_hash(schema_document())
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
        "output_kind": OUTPUT_KIND,
        "channel": CHANNEL_SYNTHETIC,
        "cert": 0,
        "game_id": str(produced["game_id"]),
        "if_margin": if_margin,
        "q2_margin": q2_margin,
        "c_margin": c_margin,
        "c_formula": C_FORMULA,
        "candidate_weight": CANDIDATE_WEIGHT,
        "seed": seed,
        "simulations": SIMULATIONS,
        "market_blend": MARKET_BLEND,
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
) -> dict[str, Any]:
    first = call_r6_point_margin(packet, history, mode=mode)
    second = call_r6_point_margin(packet, history, mode=mode)
    for key in ("if_margin", "q2_margin", "c_margin", "seed", "packet_hash", "history_hash"):
        if first[key] != second[key]:
            raise CallerRefuse(f"replay mismatch on {key}: {first[key]} vs {second[key]}")
    return {"first": first, "second": second, "replay_ok": True}
