#!/usr/bin/env python3
"""Driver: 141-game research.q2s.joint consume. CERT=0. No outcomes / LOOK read."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

JOINT = Path(__file__).resolve().parent
PACKET = JOINT.parent
PHASE4 = PACKET / "phase4"
if str(JOINT) not in sys.path:
    sys.path.insert(0, str(JOINT))
if str(PHASE4) not in sys.path:
    sys.path.insert(0, str(PHASE4))

from gates import evaluate_game, worst_status  # noqa: E402
from pins import (  # noqa: E402
    FW_SHA,
    HISTORY_FREEZE_SHA,
    IF_MUS_SHA,
    IF_TIP,
    MATRIX_SHA,
    N_DRAWS,
    N_GAMES,
    PARENT_FREEZE_SHA,
    Q2S_SHA,
    SIM_SHA,
    T5055U_FREEZE_SHA,
    PinRefuse,
    load_if_mus,
    load_q2s_rows,
    verify_input_pins,
)
from score_if_w7w17 import (  # noqa: E402
    EXAMINED_70,
    SEALED_T2,
    assemble_sample,
    build_inputs,
    seed_for,
)
from sim_q2s_joint import (  # noqa: E402
    JointRefuse,
    _load_sim,
    assert_pinned_generator,
    official_if_mus,
    simulate_q2s_joint,
)

ARTIFACTS = JOINT / "artifacts"
OUT_JSON = ARTIFACTS / "Q2S_JOINT_W7W17.json"
OUT_NPZ = ARTIFACTS / "Q2S_JOINT_DRAWS_W7W17.npz"


def _row_public(result, gates: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "game_id": result.game_id,
        "season": meta["season"],
        "week": meta["week"],
        "home": meta["home"],
        "away": meta["away"],
        "margin_mu_q2s": meta["margin_mu_q2s"],
        "if_margin_mu": meta["if_margin_mu"],
        "d": result.d,
        "mu_h": result.mu_h,
        "mu_a": result.mu_a,
        "mu_h_p": result.mu_h_p,
        "mu_a_p": result.mu_a_p,
        "sigma": result.sigma,
        "seed": result.seed,
        "N": result.N,
        "mean_D": result.mean_D,
        "mean_S": result.mean_S,
        "sd_D": result.sd_D,
        "corr_HA": result.corr_HA,
        "tie_count": result.tie_count,
        "home_wp": result.home_wp,
        "away_wp": result.away_wp,
        "fair_home_ml": result.fair_home_ml,
        "fair_away_ml": result.fair_away_ml,
        "spread_home": result.spread_home,
        "total_raw": result.total_raw,
        "draw_hash": result.draw_hash,
        "home_wins": result.home_wins,
        "ats_ou": "NOT_EMITTED",
        "gates": gates,
        "worst_gate": worst_status(gates),
        "q5_diag": gates.get("Q5_diag"),
    }


def run(*, write_files: bool = True) -> dict[str, Any]:
    pins = verify_input_pins()
    sim = _load_sim()
    assert_pinned_generator(sim)
    games, sealed = assemble_sample()
    if len(games) != N_GAMES:
        raise JointRefuse(f"assembled {len(games)} != {N_GAMES}")
    if {p["game_id"] for p in sealed} != SEALED_T2:
        raise JointRefuse("T2 set drifted")
    ids = {g["game_id"] for g in games}
    if ids & EXAMINED_70:
        raise JointRefuse("examined 70 in score set")
    if ids & SEALED_T2:
        raise JointRefuse("T2 in score set")

    q2s_payload = load_q2s_rows()
    if_payload = load_if_mus()
    q2s_by = {r["game_id"]: r for r in q2s_payload["rows"]}
    if_by = {r["game_id"]: r for r in if_payload["rows"]}
    if set(q2s_by) != ids or set(if_by) != ids:
        raise JointRefuse("identity mismatch vs frozen 141")

    rows_out: list[dict[str, Any]] = []
    H_all = np.empty((N_GAMES, N_DRAWS), dtype=np.float64)
    A_all = np.empty((N_GAMES, N_DRAWS), dtype=np.float64)
    game_ids: list[str] = []
    q1_ok = True
    q1_details: list[dict[str, Any]] = []

    ordered = sorted(games, key=lambda g: (int(g["matchup_week"]), g["game_id"]))
    for i, game in enumerate(ordered):
        gid = game["game_id"]
        qrow = q2s_by[gid]
        irow = if_by[gid]
        q2s_m = float(qrow["research"]["q2s"]["margin_mu_q2s"])
        if_m = float(irow["if_margin_mu"])
        d = q2s_m - if_m
        inputs = build_inputs(sim, game)
        result = simulate_q2s_joint(inputs, gid, d, sim=sim)
        if result.seed != seed_for(gid) or result.seed != int(irow["seed"]):
            raise JointRefuse(f"{gid} seed mismatch")
        # Q1 / J13 d=0 vs official IF replay + frozen mus (legacy WP/ML precision)
        z0 = simulate_q2s_joint(inputs, gid, 0.0, sim=sim)
        off_m, off_t, off_proj = official_if_mus(inputs, gid, sim=sim)
        markets = off_proj.get("markets") or {}
        raw_wp = z0.home_wins / float(z0.N)
        legacy_wp = round(raw_wp, 4)
        frozen_wp = float(irow["if_forecast_wp_home"])
        official_wp = float(markets["home_win_prob"])
        official_ml_h = int(markets["fair_home_ml"])
        official_ml_a = int(markets["fair_away_ml"])
        q1_game = {
            "game_id": gid,
            "mean_D_match_official": abs(z0.mean_D - off_m) <= 1e-12,
            "mean_S_match_official": abs(z0.mean_S - off_t) <= 1e-12,
            "mean_D_match_frozen": abs(z0.mean_D - if_m) <= 1e-12,
            "mean_S_match_frozen": abs(z0.mean_S - float(irow["if_total_mu"])) <= 1e-12,
            "legacy_wp": legacy_wp,
            "frozen_wp": frozen_wp,
            "official_wp": official_wp,
            "legacy_wp_match": legacy_wp == frozen_wp == official_wp,
            "legacy_ml_home": z0.fair_home_ml,
            "official_ml_home": official_ml_h,
            "legacy_ml_away": z0.fair_away_ml,
            "official_ml_away": official_ml_a,
            "legacy_ml_match": z0.fair_home_ml == official_ml_h
            and z0.fair_away_ml == official_ml_a,
            "home_wins_d0": z0.home_wins,
            "tie_count_d0": z0.tie_count,
        }
        q1_pass = all(
            [
                q1_game["mean_D_match_official"],
                q1_game["mean_S_match_official"],
                q1_game["mean_D_match_frozen"],
                q1_game["mean_S_match_frozen"],
                q1_game["legacy_wp_match"],
                q1_game["legacy_ml_match"],
            ]
        )
        if not q1_pass:
            q1_ok = False
        q1_details.append(q1_game)

        gates = evaluate_game(
            result,
            margin_mu_q2s=q2s_m,
            if_margin_mu=if_m,
            if_total_mu=float(irow["if_total_mu"]),
            if_wp_home=frozen_wp,
            sim=sim,
        )
        gates["J13"] = {"status": "PASS" if q1_pass else "FAIL", **q1_game}
        meta = {
            "season": int(qrow["season"]),
            "week": int(qrow["week"]),
            "home": qrow["home"],
            "away": qrow["away"],
            "margin_mu_q2s": q2s_m,
            "if_margin_mu": if_m,
        }
        rows_out.append(_row_public(result, gates, meta))
        H_all[i] = result.H
        A_all[i] = result.A
        game_ids.append(gid)

    counts: dict[str, int] = {
        "PASS": 0,
        "COND": 0,
        "FAIL": 0,
        "REFUSE": 0,
        "NOT_EMITTED": 0,
    }
    per_gate: dict[str, dict[str, int]] = {}
    for row in rows_out:
        for gname, g in row["gates"].items():
            st = g.get("status")
            per_gate.setdefault(gname, {})
            per_gate[gname][st] = per_gate[gname].get(st, 0) + 1
            if gname == "J14":
                counts["NOT_EMITTED"] += 1 if st == "NOT_EMITTED" else 0
            elif st in counts:
                counts[st] += 1

    # J12 diagnostic Kendall across 141
    x = np.array([r["margin_mu_q2s"] for r in rows_out], dtype=float)
    y = np.array([r["mean_D"] for r in rows_out], dtype=float)
    conc = disc = 0
    inversions = 0
    n = len(x)
    for i in range(n):
        for j in range(i + 1, n):
            p = (x[i] - x[j]) * (y[i] - y[j])
            if p > 0:
                conc += 1
            elif p < 0:
                disc += 1
                inversions += 1
    den = conc + disc
    tau = (conc - disc) / den if den else 0.0

    pins_after = verify_input_pins()
    if pins_after != pins:
        raise PinRefuse("input pins drifted during run")

    payload = {
        "namespace": "research.q2s.joint",
        "ticket": "t5065u",
        "label": "RETRO_FIT / DEV_RESEARCH",
        "cert": 0,
        "nfl": "NO-GO",
        "research_only": True,
        "scored": False,
        "totals_cal": False,
        "blend": 0,
        "weight": 0.5,
        "n": N_GAMES,
        "N": N_DRAWS,
        "if_tip": IF_TIP,
        "simulator_sha256": SIM_SHA,
        "framework_sha256": FW_SHA,
        "pins": {
            "q2s": Q2S_SHA,
            "if_mus": IF_MUS_SHA,
            "matrix": MATRIX_SHA,
            "parent_freeze": PARENT_FREEZE_SHA,
            "t5055u_freeze": T5055U_FREEZE_SHA,
            "history_freeze": HISTORY_FREEZE_SHA,
        },
        "construction": (
            "pre-floor symmetric shift d=q2s-IF; mu_h'=mu_h+d/2; "
            "mu_a'=mu_a-d/2; H,A=max(0,N(mu',sigma)); N=4000; blend=0"
        ),
        "cite": [
            "dad9eb89",
            "a091ce1a",
            "22f2c33f",
            "5d07dc49",
            "475b84a1",
            "d7e0a6bc",
        ],
        "draws_path": "joint/artifacts/Q2S_JOINT_DRAWS_W7W17.npz",
        "draw_order": "rows sorted by (week, game_id); draw index i=0..3999 = i=1..4000; pair (H,A)",
        "q1_d0": {
            "ok": q1_ok,
            "n": len(q1_details),
            "n_pass": sum(1 for g in q1_details if g.get("legacy_wp_match") and g.get("legacy_ml_match") and g.get("mean_D_match_frozen")),
            "originals_byte_identical": True,
        },
        "q1_details": q1_details,
        "j12_diagnostic": {
            "kendall_tau_margin_mu_q2s_vs_mean_D": tau,
            "inversions": inversions,
            "conc": conc,
            "disc": disc,
            "role": "diagnostic_only",
        },
        "worst_gate_counts": {
            k: sum(1 for r in rows_out if r["worst_gate"] == k)
            for k in ("PASS", "COND", "FAIL", "REFUSE")
        },
        "gate_counts_cellwise": counts,
        "gate_counts_by_name": per_gate,
        "ats_ou": "NOT_EMITTED",
        "look_run": False,
        "opened_50bda875": False,
        "rows": rows_out,
        "game_ids": game_ids,
    }

    if write_files:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            OUT_NPZ,
            game_ids=np.array(game_ids),
            H=H_all,
            A=A_all,
        )
        draws_sha = __import__("hashlib").sha256(OUT_NPZ.read_bytes()).hexdigest()
        payload["draws_file_sha256"] = draws_sha
        catalog = __import__("hashlib").sha256()
        for i, gid in enumerate(game_ids):
            catalog.update(gid.encode())
            catalog.update(H_all[i].tobytes())
            catalog.update(A_all[i].tobytes())
        payload["draws_catalog_sha256"] = catalog.hexdigest()
        OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        digest = __import__("hashlib").sha256(OUT_JSON.read_bytes()).hexdigest()
        OUT_JSON.with_suffix(".json.sha256").write_text(f"{digest}  {OUT_JSON.name}\n")
        OUT_JSON.with_suffix(".json.sha8").write_text(digest[:8] + "\n")
        OUT_NPZ.with_suffix(".npz.sha256").write_text(f"{draws_sha}  {OUT_NPZ.name}\n")
        OUT_NPZ.with_suffix(".npz.sha8").write_text(draws_sha[:8] + "\n")
        payload["artifact_sha256"] = digest

    return payload


def main() -> int:
    try:
        payload = run(write_files=True)
    except (JointRefuse, PinRefuse) as exc:
        print(f"JOINT_REFUSE: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "ok": True,
                "n": payload["n"],
                "q1_ok": payload["q1_d0"]["ok"],
                "artifact": str(OUT_JSON.relative_to(PACKET)),
                "artifact_sha256": payload.get("artifact_sha256"),
                "draws_sha256": payload.get("draws_file_sha256"),
                "gate_counts_cellwise": payload["gate_counts_cellwise"],
                "j12_tau": payload["j12_diagnostic"]["kendall_tau_margin_mu_q2s_vs_mean_D"],
                "opened_50bda875": False,
                "cert": 0,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
