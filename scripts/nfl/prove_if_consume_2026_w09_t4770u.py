#!/usr/bin/env python3
"""Prove Independent Fair consumes t4770u staged inputs (t4776u add-on).

Diagnostic only. Not an E1 emit. market_blend=0 asserted. No C10/API.

t4776u: the 20 required efficiency fields must be shown as consumed by the
intended Independent Fair calculation path (call graph + input-hash
perturbation), not merely present on the dataset row.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
OPS = ROOT / "data" / "ops" / "nfl-efficiency-2026-w1-w8-t4770u"
PACK = OPS / "w09_consume_pack.json"
OUT_PROOF = OPS / "if_consume_proof.json"
OUT_CONSUMED = OPS / "if_required_20_consumed.json"

SIM_PY = MS / "src" / "services" / "nfl_simulator.py"
HF_PY = MS / "src" / "services" / "nfl_handicapping_framework.py"

DECISION_SHA8 = "751dd63c"
ALEX_CONTRACT_V2_SHA8 = "b41f4b43"
ALEX_CONTRACT_V2_SHA256 = (
    "b41f4b43e1367bd5658c743475b9b84535c65395630a0b06c804f8b3552b81f4"
)
ALEX_CONTRACT_V1_SHA8 = "24600552"
IMV_PASS_CONTRACT_SHA8 = "1a53bbd3"
IMV_PASS_CONTRACT_SHA256 = (
    "1a53bbd33f32fec8d25a102f2abea7b975a92fbd55edbaaaafe020055c25b9f8"
)
IMV_RETURN_PARENT_SHA8 = "d2587de7"
CONTRACT_BIND = "BOUND_TO_V2_PASS_CONTRACT_1a53bbd3"
IF_CODE_COMMIT = "1b39f4e9f6b2e04c264a41831f3bb7273e475011"

REQUIRED_20 = (
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
    "home_pass_rate_5g",
    "away_pass_rate_5g",
    "home_success_offense_5g",
    "away_success_offense_5g",
    "home_success_defense_allowed_5g",
    "away_success_defense_allowed_5g",
    "matchup_diff_off_epa_5g",
    "matchup_diff_def_epa_allowed_5g",
    "matchup_diff_success_rate_5g",
    "matchup_diff_pressure_generated_5g",
    "matchup_diff_pressure_allowed_5g",
    "matchup_diff_red_zone_td_rate_5g",
)

REQUIRED_CONTEXT = (
    "game_id",
    "home_team",
    "away_team",
    "matchup_season",
    "matchup_week",
    "rest_days_home",
    "rest_days_away",
)

# Intended IF path readers per Alex v2 §3. Echo into result["inputs"] is NOT
# counted as consumption.
FIELD_READERS: Dict[str, Tuple[Tuple[str, str], ...]] = {
    "offense_index_home": (
        ("nfl_simulator.py", "simulate_nfl_game"),
        ("nfl_handicapping_framework.py", "compute_nfl_projection_decomposition"),
    ),
    "offense_index_away": (
        ("nfl_simulator.py", "simulate_nfl_game"),
        ("nfl_handicapping_framework.py", "compute_nfl_projection_decomposition"),
    ),
    "defense_index_home": (
        ("nfl_simulator.py", "simulate_nfl_game"),
        ("nfl_handicapping_framework.py", "compute_nfl_projection_decomposition"),
    ),
    "defense_index_away": (
        ("nfl_simulator.py", "simulate_nfl_game"),
        ("nfl_handicapping_framework.py", "compute_nfl_projection_decomposition"),
    ),
    "home_off_epa_5g": (
        ("nfl_simulator.py", "_build_matchup_adjustments"),
        ("nfl_simulator.py", "_build_totals_adjustments"),
    ),
    "away_off_epa_5g": (
        ("nfl_simulator.py", "_build_matchup_adjustments"),
        ("nfl_simulator.py", "_build_totals_adjustments"),
    ),
    "home_def_epa_allowed_5g": (("nfl_simulator.py", "_build_totals_adjustments"),),
    "away_def_epa_allowed_5g": (("nfl_simulator.py", "_build_totals_adjustments"),),
    "home_pass_rate_5g": (
        ("nfl_simulator.py", "_build_matchup_adjustments"),
        ("nfl_simulator.py", "_build_totals_adjustments"),
    ),
    "away_pass_rate_5g": (
        ("nfl_simulator.py", "_build_matchup_adjustments"),
        ("nfl_simulator.py", "_build_totals_adjustments"),
    ),
    "home_success_offense_5g": (("nfl_simulator.py", "_build_totals_adjustments"),),
    "away_success_offense_5g": (("nfl_simulator.py", "_build_totals_adjustments"),),
    "home_success_defense_allowed_5g": (
        ("nfl_simulator.py", "_build_totals_adjustments"),
    ),
    "away_success_defense_allowed_5g": (
        ("nfl_simulator.py", "_build_totals_adjustments"),
    ),
    "matchup_diff_off_epa_5g": (("nfl_simulator.py", "_build_matchup_adjustments"),),
    "matchup_diff_def_epa_allowed_5g": (
        ("nfl_simulator.py", "_build_matchup_adjustments"),
    ),
    "matchup_diff_success_rate_5g": (
        ("nfl_simulator.py", "_build_matchup_adjustments"),
    ),
    "matchup_diff_pressure_generated_5g": (
        ("nfl_simulator.py", "_build_matchup_adjustments"),
    ),
    "matchup_diff_pressure_allowed_5g": (
        ("nfl_simulator.py", "_build_matchup_adjustments"),
    ),
    "matchup_diff_red_zone_td_rate_5g": (
        ("nfl_simulator.py", "_build_matchup_adjustments"),
    ),
}

SOURCE_FILES = {
    "nfl_simulator.py": SIM_PY,
    "nfl_handicapping_framework.py": HF_PY,
}

# Perturbations sized to move the bounded component without hitting a no-op
# clamp against typical 2026 through-W7 values.
FIELD_DELTA: Dict[str, float] = {
    "offense_index_home": 0.06,
    "offense_index_away": 0.06,
    "defense_index_home": 0.06,
    "defense_index_away": 0.06,
    "home_off_epa_5g": 0.08,
    "away_off_epa_5g": 0.08,
    "home_def_epa_allowed_5g": 0.08,
    "away_def_epa_allowed_5g": 0.08,
    "home_pass_rate_5g": 0.08,
    "away_pass_rate_5g": 0.08,
    "home_success_offense_5g": 0.06,
    "away_success_offense_5g": 0.06,
    "home_success_defense_allowed_5g": 0.06,
    "away_success_defense_allowed_5g": 0.06,
    "matchup_diff_off_epa_5g": 0.08,
    "matchup_diff_def_epa_allowed_5g": 0.08,
    "matchup_diff_success_rate_5g": 0.06,
    "matchup_diff_pressure_generated_5g": 0.04,
    "matchup_diff_pressure_allowed_5g": 0.04,
    "matchup_diff_red_zone_td_rate_5g": 0.06,
}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash_obj(obj: Any) -> str:
    return _sha256_bytes(_canonical(obj).encode("utf-8"))


def _write_json(path: Path, obj: Any) -> str:
    text = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")
    return _sha256_bytes(text.encode("utf-8"))


def _function_nodes(tree: ast.AST, name: str) -> List[ast.AST]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    ]


def _field_hits_in_function(func: ast.AST, field: str) -> List[int]:
    hits: List[int] = []
    for child in ast.walk(func):
        if isinstance(child, ast.Attribute) and child.attr == field:
            hits.append(int(getattr(child, "lineno", 0) or 0))
        if isinstance(child, ast.keyword) and child.arg == field:
            hits.append(int(getattr(child, "lineno", 0) or 0))
        if isinstance(child, ast.Name) and child.id == field:
            hits.append(int(getattr(child, "lineno", 0) or 0))
    return sorted({line for line in hits if line})


def _calls_function(func: ast.AST, callee: str) -> List[int]:
    lines: List[int] = []
    for child in ast.walk(func):
        if not isinstance(child, ast.Call):
            continue
        target = child.func
        name = None
        if isinstance(target, ast.Name):
            name = target.id
        elif isinstance(target, ast.Attribute):
            name = target.attr
        if name == callee:
            lines.append(int(getattr(child, "lineno", 0) or 0))
    return sorted({line for line in lines if line})


def _kwarg_true(func: ast.AST, callee: str, keyword: str) -> bool:
    for child in ast.walk(func):
        if not isinstance(child, ast.Call):
            continue
        target = child.func
        name = None
        if isinstance(target, ast.Name):
            name = target.id
        elif isinstance(target, ast.Attribute):
            name = target.attr
        if name != callee:
            continue
        for kw in child.keywords:
            if kw.arg != keyword:
                continue
            if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                return True
    return False


def extract_call_graph() -> Dict[str, Any]:
    trees = {name: ast.parse(path.read_text(encoding="utf-8")) for name, path in SOURCE_FILES.items()}
    sim_tree = trees["nfl_simulator.py"]
    entry = _function_nodes(sim_tree, "simulate_nfl_game_independent_fair")
    sim = _function_nodes(sim_tree, "simulate_nfl_game")
    if not entry or not sim:
        raise RuntimeError("IF entrypoint or simulate_nfl_game missing from source")
    entry_fn, sim_fn = entry[0], sim[0]
    chain = {
        "entrypoint": "simulate_nfl_game_independent_fair",
        "calls_simulate_nfl_game": _calls_function(entry_fn, "simulate_nfl_game"),
        "independent_fair_kwarg_true": _kwarg_true(
            entry_fn, "simulate_nfl_game", "independent_fair"
        ),
        "simulate_nfl_game_calls": {
            "_build_matchup_adjustments": _calls_function(sim_fn, "_build_matchup_adjustments"),
            "_build_totals_adjustments": _calls_function(sim_fn, "_build_totals_adjustments"),
            "compute_nfl_projection_decomposition": _calls_function(
                sim_fn, "compute_nfl_projection_decomposition"
            ),
        },
        "source_sha256": {
            name: _sha256_file(path) for name, path in SOURCE_FILES.items()
        },
        "code_commit": IF_CODE_COMMIT,
    }
    if not chain["calls_simulate_nfl_game"] or not chain["independent_fair_kwarg_true"]:
        raise RuntimeError("entrypoint does not call simulate_nfl_game(independent_fair=True)")
    for callee, lines in chain["simulate_nfl_game_calls"].items():
        if not lines:
            raise RuntimeError(f"simulate_nfl_game does not call {callee}")

    fields: Dict[str, Any] = {}
    missing: List[str] = []
    for field, readers in FIELD_READERS.items():
        cites = []
        for filename, func_name in readers:
            nodes = _function_nodes(trees[filename], func_name)
            if not nodes:
                missing.append(f"{field}:{filename}:{func_name}:missing_fn")
                continue
            hits = _field_hits_in_function(nodes[0], field)
            if not hits:
                missing.append(f"{field}:{filename}:{func_name}:no_read")
            cites.append(
                {
                    "file": filename,
                    "function": func_name,
                    "lines": hits,
                    "path_role": (
                        "decomposition"
                        if func_name == "compute_nfl_projection_decomposition"
                        else (
                            "matchup"
                            if func_name == "_build_matchup_adjustments"
                            else (
                                "totals"
                                if func_name == "_build_totals_adjustments"
                                else "entrypoint_pass_through"
                            )
                        )
                    ),
                }
            )
        fields[field] = {
            "in_call_graph": all(cite["lines"] for cite in cites),
            "readers": cites,
        }
    if missing:
        raise RuntimeError(f"call-graph gaps: {missing}")
    return {"chain": chain, "fields": fields, "missing": missing}


def required_20_payload(game: Dict[str, Any]) -> Dict[str, float]:
    payload: Dict[str, float] = {}
    for name in REQUIRED_20:
        value = game.get(name)
        if value is None:
            raise RuntimeError(f"{game.get('game_id')} missing required field {name}")
        payload[name] = float(value)
    return payload


def build_inputs(game: Dict[str, Any], NflGameInputs, overrides: Optional[Dict[str, float]] = None):
    payload = required_20_payload(game)
    if overrides:
        payload.update(overrides)
    kwargs = {
        "game_id": str(game["game_id"]),
        "home_team": str(game["home_team"]),
        "away_team": str(game["away_team"]),
        "rest_days_home": float(game["rest_days_home"]),
        "rest_days_away": float(game["rest_days_away"]),
        "matchup_season": 2026,
        "matchup_week": 9,
        **payload,
        "weather_available": None,
        "injury_nowcast_impact_home": None,
        "injury_nowcast_impact_away": None,
        "travel_available": None,
        "travel_miles_home": None,
        "travel_miles_away": None,
        "travel_timezone_delta_home": None,
        "travel_timezone_delta_away": None,
        "info_velocity_home": None,
        "info_velocity_away": None,
        "hours_since_change_home": None,
        "hours_since_change_away": None,
    }
    return NflGameInputs(**kwargs), payload


def run_if(inputs, simulate_nfl_game_independent_fair, independent_fair_mus, *, seed: int):
    out = simulate_nfl_game_independent_fair(
        inputs,
        simulations=400,
        seed=seed,
        market_spread_home=None,
        market_total=None,
    )
    margin_mu, total_mu = independent_fair_mus(out)
    decomp = out.get("decomposition") or {}
    core = {
        "forecast_label": out.get("forecast_label"),
        "market_blend": (out.get("independent_fair") or {}).get("market_blend"),
        "margin_mu": margin_mu,
        "total_mu": total_mu,
        "predicted_margin": decomp.get("predicted_margin"),
        "predicted_total": decomp.get("predicted_total"),
        "expected_home_points": decomp.get("expected_home_points"),
        "expected_away_points": decomp.get("expected_away_points"),
    }
    return out, core, _hash_obj(core)


def assert_outside_none(inputs, NflGameInputs) -> List[str]:
    allowed = set(REQUIRED_20) | set(REQUIRED_CONTEXT)
    populated = []
    for name in NflGameInputs.__dataclass_fields__:
        if name in allowed:
            continue
        if getattr(inputs, name) is not None:
            populated.append(name)
    return populated


def prove_field_consumed(
    game: Dict[str, Any],
    field: str,
    baseline_core: Dict[str, Any],
    baseline_hash: str,
    NflGameInputs,
    simulate_nfl_game_independent_fair,
    independent_fair_mus,
) -> Dict[str, Any]:
    base_value = float(game[field])
    deltas: Iterable[float] = (FIELD_DELTA[field], -FIELD_DELTA[field], 0.15, -0.15)
    last: Dict[str, Any] = {}
    for delta in deltas:
        trial = base_value + delta
        inputs, payload = build_inputs(game, NflGameInputs, {field: trial})
        _, core, out_hash = run_if(
            inputs,
            simulate_nfl_game_independent_fair,
            independent_fair_mus,
            seed=4776,
        )
        last = {
            "field": field,
            "baseline_value": base_value,
            "perturbed_value": trial,
            "delta_applied": delta,
            "input_hash": _hash_obj(payload),
            "baseline_output_hash": baseline_hash,
            "perturbed_output_hash": out_hash,
            "baseline_core": baseline_core,
            "perturbed_core": core,
            "delta_margin_mu": float(core["margin_mu"]) - float(baseline_core["margin_mu"]),
            "delta_total_mu": float(core["total_mu"]) - float(baseline_core["total_mu"]),
            "delta_predicted_margin": float(core["predicted_margin"])
            - float(baseline_core["predicted_margin"]),
            "delta_predicted_total": float(core["predicted_total"])
            - float(baseline_core["predicted_total"]),
        }
        changed = (
            last["perturbed_output_hash"] != last["baseline_output_hash"]
            or abs(last["delta_predicted_margin"]) > 0.0
            or abs(last["delta_predicted_total"]) > 0.0
            or abs(last["delta_margin_mu"]) > 0.0
            or abs(last["delta_total_mu"]) > 0.0
        )
        last["consumed"] = bool(changed)
        if changed:
            return last
    last["consumed"] = False
    return last


def seal_ops_packet() -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    for path in sorted(OPS.iterdir()):
        if not path.is_file() or path.name == "SHA256SUMS":
            continue
        hashes[path.name] = _sha256_file(path)
    sums = "".join(f"{digest}  {name}\n" for name, digest in hashes.items())
    (OPS / "SHA256SUMS").write_text(sums, encoding="utf-8")
    return hashes


def main() -> int:
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("LAUNCH_RESEARCH_DATABASE_URL", None)
    sys.path.insert(0, str(MS))

    from src.services.nfl_simulator import (
        INDEPENDENT_FAIR_FORECAST_LABEL,
        NFL_INDEPENDENT_FAIR_PATH,
        NflGameInputs,
        independent_fair_mus,
        simulate_nfl_game_independent_fair,
    )

    pack = json.loads(PACK.read_text(encoding="utf-8"))
    call_graph = extract_call_graph()
    rows = []
    consume_probe = None
    for game in pack.get("games") or []:
        if game.get("row_status") != "ACCEPT":
            rows.append(
                {
                    "game_id": game.get("game_id"),
                    "consumed": False,
                    "row_status": game.get("row_status"),
                    "reject_reasons": game.get("reject_reasons"),
                }
            )
            continue
        inputs, payload = build_inputs(game, NflGameInputs)
        outside = assert_outside_none(inputs, NflGameInputs)
        if outside:
            raise RuntimeError(f"{game['game_id']} OUTSIDE populated: {outside}")
        # Echo-vs-consume: hash the 20-field payload actually passed into NflGameInputs.
        input_hash = _hash_obj(payload)
        out, core, out_hash = run_if(
            inputs,
            simulate_nfl_game_independent_fair,
            independent_fair_mus,
            seed=4770,
        )
        if core["forecast_label"] != INDEPENDENT_FAIR_FORECAST_LABEL:
            raise RuntimeError("IF label missing")
        if core["market_blend"] != 0:
            raise RuntimeError("market_blend must be 0")
        echoed = out.get("inputs") or {}
        echoed_20 = {name: echoed.get(name) for name in REQUIRED_20}
        rows.append(
            {
                "game_id": game["game_id"],
                "consumed": True,
                "row_status": "ACCEPT",
                "forecast_label": core["forecast_label"],
                "market_blend": core["market_blend"],
                "margin_mu": core["margin_mu"],
                "total_mu": core["total_mu"],
                "as_of_week": game.get("as_of_week"),
                "rolling_as_of_week": game.get("rolling_as_of_week"),
                "required_20_input_hash": input_hash,
                "if_output_hash": out_hash,
                "echoed_20_matches_input": echoed_20 == payload,
            }
        )
        if consume_probe is None:
            consume_probe = {
                "game": game,
                "payload": payload,
                "input_hash": input_hash,
                "baseline_core": core,
                "baseline_output_hash": out_hash,
            }

    if consume_probe is None:
        raise RuntimeError("no ACCEPT W9 row to probe 20-field consumption")

    field_proofs = []
    for field in REQUIRED_20:
        static = call_graph["fields"][field]
        runtime = prove_field_consumed(
            consume_probe["game"],
            field,
            consume_probe["baseline_core"],
            consume_probe["baseline_output_hash"],
            NflGameInputs,
            simulate_nfl_game_independent_fair,
            independent_fair_mus,
        )
        record = {
            "field": field,
            "in_call_graph": static["in_call_graph"],
            "readers": static["readers"],
            "present_in_dataset": True,
            "passed_into_NflGameInputs": True,
            "baseline_value": runtime["baseline_value"],
            "perturbed_value": runtime["perturbed_value"],
            "delta_applied": runtime["delta_applied"],
            "input_hash_baseline": consume_probe["input_hash"],
            "input_hash_perturbed": runtime["input_hash"],
            "input_hash_changed": runtime["input_hash"] != consume_probe["input_hash"],
            "output_hash_baseline": consume_probe["baseline_output_hash"],
            "output_hash_perturbed": runtime["perturbed_output_hash"],
            "output_hash_changed": runtime["perturbed_output_hash"]
            != consume_probe["baseline_output_hash"],
            "delta_margin_mu": runtime["delta_margin_mu"],
            "delta_total_mu": runtime["delta_total_mu"],
            "delta_predicted_margin": runtime["delta_predicted_margin"],
            "delta_predicted_total": runtime["delta_predicted_total"],
            "consumed_by_if_path": bool(
                static["in_call_graph"]
                and runtime["consumed"]
                and runtime["input_hash"] != consume_probe["input_hash"]
            ),
        }
        if not record["consumed_by_if_path"]:
            raise RuntimeError(f"{field} present but not consumed by IF path: {record}")
        field_proofs.append(record)

    consumed_n = sum(1 for row in field_proofs if row["consumed_by_if_path"])
    consume_doc = {
        "ticket": "t4770u",
        "addon_ticket": "t4776u",
        "decision": DECISION_SHA8,
        "alex_contract_sha8": ALEX_CONTRACT_V2_SHA8,
        "alex_contract_sha256": ALEX_CONTRACT_V2_SHA256,
        "alex_contract_version": "v2",
        "alex_contract_parent_v1_sha8": ALEX_CONTRACT_V1_SHA8,
        "contract_bind": CONTRACT_BIND,
        "imv_pass_contract": IMV_PASS_CONTRACT_SHA8,
        "imv_pass_contract_sha256": IMV_PASS_CONTRACT_SHA256,
        "imv_return_parent": IMV_RETURN_PARENT_SHA8,
        "code_commit": IF_CODE_COMMIT,
        "entrypoint": "simulate_nfl_game_independent_fair",
        "path": (
            "simulate_nfl_game_independent_fair → "
            "simulate_nfl_game(independent_fair=True) → "
            "_build_matchup_adjustments + _build_totals_adjustments + "
            "compute_nfl_projection_decomposition → Independent Fair mus"
        ),
        "market_blend": 0,
        "NFL_INDEPENDENT_FAIR_PATH": NFL_INDEPENDENT_FAIR_PATH,
        "DATABASE_URL_used": False,
        "c10_used": False,
        "scoring_admissible": False,
        "label": (
            "DIAGNOSTIC t4776u: 20/20 required fields consumed by IF path "
            "(call graph + input-hash perturbation). Not an E1 emit."
        ),
        "probe_game_id": consume_probe["game"]["game_id"],
        "probe_as_of_week": consume_probe["game"].get("as_of_week"),
        "probe_rolling_as_of_week": consume_probe["game"].get("rolling_as_of_week"),
        "probe_required_20_input_hash": consume_probe["input_hash"],
        "probe_if_output_hash": consume_probe["baseline_output_hash"],
        "n_required": len(REQUIRED_20),
        "n_consumed_by_if_path": consumed_n,
        "all_20_consumed": consumed_n == 20,
        "call_graph": call_graph["chain"],
        "fields": field_proofs,
    }
    _write_json(OUT_CONSUMED, consume_doc)

    proof = {
        "ticket": "t4770u",
        "addon_ticket": "t4776u",
        "decision": DECISION_SHA8,
        "alex_contract_sha8": ALEX_CONTRACT_V2_SHA8,
        "alex_contract_sha256": ALEX_CONTRACT_V2_SHA256,
        "alex_contract_version": "v2",
        "alex_contract_parent_v1_sha8": ALEX_CONTRACT_V1_SHA8,
        "contract_bind": CONTRACT_BIND,
        "imv_pass_contract": IMV_PASS_CONTRACT_SHA8,
        "imv_pass_contract_sha256": IMV_PASS_CONTRACT_SHA256,
        "imv_return_parent": IMV_RETURN_PARENT_SHA8,
        "code_commit": IF_CODE_COMMIT,
        "entrypoint": "simulate_nfl_game_independent_fair",
        "market_blend": 0,
        "NFL_INDEPENDENT_FAIR_PATH": NFL_INDEPENDENT_FAIR_PATH,
        "DATABASE_URL_used": False,
        "c10_used": False,
        "scoring_admissible": False,
        "label": (
            "DIAGNOSTIC consume proof on through-W7 panel; t4776u 20-field "
            "IF-path consumption attached. Not an E1 emit."
        ),
        "n_consumed": sum(1 for r in rows if r.get("consumed")),
        "n_games": len(rows),
        "required_20_consumed_by_if_path": consumed_n == 20,
        "required_20_consumed_path": str(OUT_CONSUMED.relative_to(ROOT)),
        "games": rows,
    }
    _write_json(OUT_PROOF, proof)
    hashes = seal_ops_packet()
    print(
        json.dumps(
            {
                "ok": True,
                "n_consumed": proof["n_consumed"],
                "all_20_consumed": consumed_n == 20,
                "bind": CONTRACT_BIND,
                "status_packet": str(OPS),
                "proof": str(OUT_PROOF),
                "consumed20": str(OUT_CONSUMED),
                "sha256_count": len(hashes),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
