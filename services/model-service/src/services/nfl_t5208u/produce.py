"""Offline SYNTHETIC demo for t5208u R6. No network, no DB, no real rows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.services.nfl_t5107u.builder import challenger_margin
from src.services.nfl_t5107u.if_produce import seed_for
from src.services.nfl_t5107u.if_produce import sha256_file as algo_sha256_file
from src.services.nfl_t5208u.caller import call_r6_point_margin, replay_call
from src.services.nfl_t5208u.if_tree import in_repo_if_tree, preflight_if_tree
from src.services.nfl_t5208u.packets import build_synthetic_demo
from src.services.nfl_t5208u.pins import (
    ALLOWED_ALGO_MODULES,
    BOUNDARY_CONTRACT,
    CANDIDATE_WEIGHT,
    CONTRACT_27,
    C_FORMULA,
    FW_SHA256,
    IF_TIP,
    OWNER_CLEAR_SHA8,
    PRESERVE_PACKAGE,
    PURE_SOURCE_TIP,
    RETURN_A_ORDER_SHA8,
    RETURN_COS_SHA8,
    RETURN_OWNER_SHA8,
    RETURN_PACKAGE,
    SCHEMA_ID,
    SIM_SHA256,
)
from src.services.nfl_t5208u.schema import schema_document, schema_hash

REPO_ROOT = Path(__file__).resolve().parents[5]
OPS_DIR = REPO_ROOT / "data" / "ops" / "t5208u-r6-caller-v1"
RETURN_OPS_DIR = REPO_ROOT / "data" / "ops" / "t5213u-r6-pure-function"
ALGO_DIR = Path(__file__).resolve().parents[1] / "nfl_t5107u"


def _hash_path(path: Path) -> str:
    return algo_sha256_file(path)


def code_hashes() -> dict[str, str]:
    r6_dir = Path(__file__).resolve().parent
    out = {
        f"r6/{path.name}": _hash_path(path)
        for path in sorted(r6_dir.glob("*.py"))
    }
    for name in ALLOWED_ALGO_MODULES:
        path = ALGO_DIR / f"{name}.py"
        out[f"algo_455a8e43/{name}.py"] = _hash_path(path)
    tree = in_repo_if_tree()
    out["if/nfl_simulator.py"] = _hash_path(tree / "src/services/nfl_simulator.py")
    out["if/nfl_handicapping_framework.py"] = _hash_path(
        tree / "src/services/nfl_handicapping_framework.py"
    )
    return out


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def produce_demo() -> dict[str, Any]:
    preflight = preflight_if_tree()
    demo = build_synthetic_demo()
    schema = schema_document()
    s_hash = schema_hash(schema)
    result = call_r6_point_margin(demo["packet"], demo["history"])
    replay = replay_call(demo["packet"], demo["history"])
    controls = []
    for row in demo["c_formula_controls"]:
        got = challenger_margin(row["if_margin"], row["q2_margin"], w=CANDIDATE_WEIGHT)
        controls.append(
            {
                **row,
                "got_c": got,
                "ok": got == row["expected_c"],
            }
        )
    if not all(row["ok"] for row in controls):
        raise RuntimeError(f"C formula controls failed: {controls}")

    receipt = {
        "package": "t5208u",
        "role": "A_PURE_CALLER",
        "cert": 0,
        "implemented_ne_verified": True,
        "owner_clear_sha8": OWNER_CLEAR_SHA8,
        "schema_id": SCHEMA_ID,
        "schema_hash": s_hash,
        "schema": schema,
        "contract_27": list(CONTRACT_27),
        "contract_27_n": len(CONTRACT_27),
        "c_formula": C_FORMULA,
        "pure_source_tip": PURE_SOURCE_TIP,
        "if_tip": IF_TIP,
        "sim_sha256": SIM_SHA256,
        "fw_sha256": FW_SHA256,
        "if_preflight": preflight,
        "code_hashes": code_hashes(),
        "seed_check": {
            "game_id": result["game_id"],
            "seed": result["seed"],
            "seed_for": seed_for(result["game_id"]),
        },
        "demo_point_margin": {
            "if_margin": result["if_margin"],
            "q2_margin": result["q2_margin"],
            "c_margin": result["c_margin"],
            "seed": result["seed"],
            "simulations": result["simulations"],
            "market_blend": result["market_blend"],
            "replay_ok": replay["replay_ok"],
            "packet_hash": result["packet_hash"],
            "history_hash": result["history_hash"],
            "config_hash": result["config_hash"],
            "code_hash": result["code_hash"],
            "cutoff_utc": result["cutoff_utc"],
            "seal_utc": result["seal_utc"],
        },
        "return_package": RETURN_PACKAGE,
        "return_owner_sha8": RETURN_OWNER_SHA8,
        "return_cos_sha8": RETURN_COS_SHA8,
        "return_a_order_sha8": RETURN_A_ORDER_SHA8,
        "preserve_package": PRESERVE_PACKAGE,
        "boundary_contract": BOUNDARY_CONTRACT,
        "c_formula_controls": controls,
        "output_kind": "POINT_MARGIN",
        "boundaries": [
            "SYNTHETIC packets only; real-mode refuse.",
            "POINT_MARGIN only; no ML/totals/probabilities.",
            "No real data, outcomes scoring, fit, live, network, DB, customer.",
            "No SEALED_SEASONS / T5108U_IF_TREE / ensure_if_tree.",
            "CERT=0. IMPLEMENTED≠VERIFIED≠ACCEPTED. No merge.",
        ],
        "handoff_for_b": {
            "synthetic_packet_path": "data/ops/t5208u-r6-caller-v1/synthetic_demo.json",
            "demo_result_path": "data/ops/t5208u-r6-caller-v1/demo_result.json",
            "invoke": (
                "cd services/model-service && "
                "python -m src.services.nfl_t5208u.produce"
            ),
            "import": "from src.services.nfl_t5208u.caller import call_r6_point_margin",
            "do_not": [
                "fabricate IF means",
                "open real mode",
                "auto-mount the IF tree",
                "score outcomes",
            ],
        },
    }
    write_json(OPS_DIR / "schema.json", schema)
    write_json(OPS_DIR / "synthetic_demo.json", demo)
    write_json(OPS_DIR / "demo_result.json", result)
    write_json(OPS_DIR / "receipt.json", receipt)
    (OPS_DIR / "RECEIPT.md").write_text(_receipt_md(receipt), encoding="utf-8")
    write_json(RETURN_OPS_DIR / "schema.json", schema)
    write_json(RETURN_OPS_DIR / "synthetic_demo.json", demo)
    write_json(RETURN_OPS_DIR / "demo_result.json", result)
    write_json(RETURN_OPS_DIR / "receipt.json", receipt)
    (RETURN_OPS_DIR / "RECEIPT.md").write_text(_receipt_md(receipt), encoding="utf-8")
    return receipt


def _receipt_md(receipt: dict[str, Any]) -> str:
    demo = receipt["demo_point_margin"]
    pre = receipt["if_preflight"]
    return (
        "# t5208u R6_CALLER_V1 A receipt (CERT=0)\n\n"
        "Worker A pure caller. Not integration owner. "
        "IMPLEMENTED≠VERIFIED≠ACCEPTED. No merge.\n\n"
        f"- schema_id: `{receipt['schema_id']}`\n"
        f"- schema_hash: `{receipt['schema_hash']}`\n"
        f"- CONTRACT_27 n={receipt['contract_27_n']} frozen from recon_contract.py@455a8e43\n"
        f"- IF tree: `{pre['tree_path']}` status={pre['status']}\n"
        f"- sim_sha256: `{pre['sim_sha256']}`\n"
        f"- fw_sha256: `{pre['fw_sha256']}`\n"
        f"- DEFAULT_IF_TREES used: `{pre['default_if_trees_used']}` "
        "(ABSENT mounts; not created)\n"
        f"- IF: `{demo['if_margin']}`  Q2: `{demo['q2_margin']}`  C: `{demo['c_margin']}`\n"
        f"- seed: `{demo['seed']}` simulations={demo['simulations']} "
        f"replay_ok={demo['replay_ok']}\n"
        f"- formula: `{receipt['c_formula']}`\n"
        f"- packet_hash: `{demo.get('packet_hash')}`\n"
        f"- history_hash: `{demo.get('history_hash')}`\n"
        f"- config_hash: `{demo.get('config_hash')}`\n"
        f"- code_hash: `{demo.get('code_hash')}`\n"
        f"- cutoff/seal: `{demo.get('cutoff_utc')}` / `{demo.get('seal_utc')}`\n"
        f"- t5213u 79264: cells+metadata+identity validated BEFORE IF; "
        f"binds are actual hashes (not schema_hash).\n\n"
        "B: use `data/ops/t5213u-r6-pure-function/` actual binds + cutoff; "
        "import `call_r6_point_margin`; do not fabricate IF means; "
        "real-mode refuse; CERT=0 DRAFT only. No operational acceptance "
        "from prior t5208 counts.\n"
    )


def main() -> None:
    receipt = produce_demo()
    print(json.dumps(
        {
            "ok": True,
            "schema_hash": receipt["schema_hash"],
            "packet_hash": receipt["demo_point_margin"].get("packet_hash"),
            "history_hash": receipt["demo_point_margin"].get("history_hash"),
            "config_hash": receipt["demo_point_margin"].get("config_hash"),
            "code_hash": receipt["demo_point_margin"].get("code_hash"),
            "if_tree": receipt["if_preflight"]["tree_path"],
            "if_status": receipt["if_preflight"]["status"],
            "if_margin": receipt["demo_point_margin"]["if_margin"],
            "q2_margin": receipt["demo_point_margin"]["q2_margin"],
            "c_margin": receipt["demo_point_margin"]["c_margin"],
            "seed": receipt["demo_point_margin"]["seed"],
            "replay_ok": receipt["demo_point_margin"]["replay_ok"],
        },
        indent=2,
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
