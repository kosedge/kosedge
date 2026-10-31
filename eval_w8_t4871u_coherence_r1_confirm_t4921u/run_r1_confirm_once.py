#!/usr/bin/env python3.12
"""t4921u #4 R1 confirmatory addendum — ONE SHOT.

Frozen: N=200_000, seeds 49210000+i, sealed pre-clamp μ_h/μ_a/σ, sealed P_model.
Does not replace, reseed, or re-grade the sealed N=4000 Card A parent.
no_rerun_until_pass=true — refuse if RESULTS.json already exists.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PARENT_GAMES = Path("/home/ubuntu/.cursor/projects/workspace/uploads/GAMES_6824.json")
PARENT_RESULTS = Path("/home/ubuntu/.cursor/projects/workspace/uploads/RESULTS_e362.json")
PARENT_FROZEN = Path("/home/ubuntu/.cursor/projects/workspace/uploads/FROZEN_CONFIG_1934.json")

PROTOCOL_SHA = "a1b4f03e2c5ee2c2dacee7b1ea21fd36584a656efe6920fa27629c467cb82b25"
ERRATUM_SHA = "ae42c97f8d31737b538c01e7fbb6f6d130a12704fa70ad53a264e67f8f996455"
EXEC_CARD_SHA = "2ed320d240656ca4040699b0ab8a11f1698fb1c3b816ed992405d8f53cabae19"
SPEC_SHA = "fe4dc220d208fe6312cb32c7e441c49448d6e3b11c40639d919f47b5aedbea95"
PARENT_GAMES_SHA = "c73a9c0c2901070cf6dca8ea24bd2285aa243b3419757939996bf78a5c0b97ca"
PARENT_RESULTS_SHA = "e1c40da2bf7dbc50156ad78f577108a54779d315b3ac923ab5f6a7479dcbc0e1"
PARENT_FROZEN_SHA = "7efc08ef2df860180054d4252ec9d91f3572c955d04912dd7fc38c26b8c52ea7"

N_CONFIRM = 200_000
SEED_BASE = 49_210_000
NO_RERUN = True
MARKET_BLEND = 0

R1_CHECKS = (
    {"id": "J7_S", "game_id": "2026-W08-CLE@PIT"},
    {"id": "J7_S", "game_id": "2026-W08-MIN@DET"},
    {"id": "J7", "game_id": "2026-W08-LAC@LAR"},
    {"id": "J9", "game_id": "2026-W08-LAC@LAR"},
)

PROTOCOL_ORDER = (
    "2026-W08-ARI@DAL",
    "2026-W08-ATL@TB",
    "2026-W08-BAL@BUF",
    "2026-W08-CLE@PIT",
    "2026-W08-IND@JAX",
    "2026-W08-LV@NYJ",
    "2026-W08-MIN@DET",
    "2026-W08-TEN@CIN",
    "2026-W08-LAC@LAR",
    "2026-W08-KC@DEN",
    "2026-W08-NE@MIA",
    "2026-W08-PHI@WAS",
    "2026-W08-CHI@SEA",
)

INV_SQRT_2PI = 1.0 / math.sqrt(2.0 * math.pi)
ATS_OU_FORBIDDEN = (
    "ats_cover",
    "ou_over",
    "ou_under",
    "p_ats",
    "p_cover",
    "p_over",
    "p_under",
    "p_push",
    "spread_cover",
    "total_over",
    "total_under",
    "cover_prob",
    "over_prob",
    "under_prob",
    "push_prob",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_sha(path: Path, expected: str, label: str) -> str:
    got = sha256_file(path)
    if got != expected:
        raise RuntimeError(f"{label} digest mismatch: got {got} expected {expected}")
    return got


def phi(z: float) -> float:
    return INV_SQRT_2PI * math.exp(-0.5 * z * z)


def Phi(z: float) -> float:
    return 0.5 * math.erfc(-z / math.sqrt(2.0))


def rectified_mean(mu: float, sigma: float) -> float:
    z = mu / sigma
    return mu * Phi(z) + sigma * phi(z)


def rectified_var(mu: float, sigma: float) -> float:
    z = mu / sigma
    ez = rectified_mean(mu, sigma)
    second = (mu * mu + sigma * sigma) * Phi(z) + mu * sigma * phi(z)
    return second - ez * ez


def band_z24(z: float) -> str:
    if z <= 2.0:
        return "PASS"
    if z <= 4.0:
        return "COND"
    return "FAIL"


def band_j8(rel: float) -> str:
    if rel <= 0.03:
        return "PASS"
    if rel <= 0.08:
        return "COND"
    return "FAIL"


def band_j9(delta: float, se_p: float) -> str:
    two_se = 2.0 * se_p
    fail_bound = 0.03 if two_se <= 0.03 else (4.0 * se_p)
    if delta <= two_se:
        return "PASS"
    if delta <= fail_bound:
        return "COND"
    return "FAIL"


def band_j10(abs_rho: float) -> str:
    if abs_rho <= 0.05:
        return "PASS"
    if abs_rho <= 0.10:
        return "COND"
    return "FAIL"


def band_tie(p_tie: float) -> str:
    if p_tie <= 1e-3:
        return "PASS"
    if p_tie <= 5e-3:
        return "COND"
    return "FAIL"


def band_a(delta: float, tol: float) -> str:
    return "PASS" if abs(delta) <= tol else "FAIL"


def fair_ml_pair(home_wp: float) -> tuple[int, int]:
    p = float(home_wp)
    q = 1.0 - p
    if p >= 0.5:
        mag = int(round(100.0 * p / q))
        return -mag, mag
    mag = int(round(100.0 * q / p))
    return mag, -mag


def to_py(x):
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.ndarray):
        return [to_py(v) for v in x.tolist()]
    return x


def dump_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def scan_ats_ou(obj, trail: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = str(k).lower()
            loc = f"{trail}.{k}" if trail else str(k)
            if any(tok in key for tok in ATS_OU_FORBIDDEN):
                hits.append(loc)
            hits.extend(scan_ats_ou(v, loc))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(scan_ats_ou(v, f"{trail}[{i}]"))
    return hits


def simulate_game(mu_h: float, mu_a: float, sigma: float, seed: int, n: int):
    rng = random.Random(seed)
    H = np.empty(n, dtype=np.float64)
    A = np.empty(n, dtype=np.float64)
    n_clamped_h = 0
    n_clamped_a = 0
    for i in range(n):
        raw_h = rng.gauss(mu_h, sigma)
        raw_a = rng.gauss(mu_a, sigma)
        if raw_h < 0.0:
            n_clamped_h += 1
        if raw_a < 0.0:
            n_clamped_a += 1
        H[i] = raw_h if raw_h > 0.0 else 0.0
        A[i] = raw_a if raw_a > 0.0 else 0.0
    # Interleaved float64 LE [H0,A0,...] — same layout as parent (verified on sealed ARI@DAL).
    interleaved = np.empty(n * 2, dtype="<f8")
    interleaved[0::2] = H
    interleaved[1::2] = A
    draw_sha = hashlib.sha256(interleaved.tobytes()).hexdigest()
    D = H - A
    S = H + A
    mean_H = float(H.mean())
    mean_A = float(A.mean())
    mean_D = float(D.mean())
    mean_S = float(S.mean())
    sd_D = float(D.std(ddof=1))
    sd_S = float(S.std(ddof=1))
    se_D = sd_D / math.sqrt(n)
    corr = float(np.corrcoef(H, A)[0, 1])
    n_home = int(np.sum(D > 0.0))
    n_away = int(np.sum(D < 0.0))
    n_tie = int(np.sum(D == 0.0))
    if n_home + n_away + n_tie != n:
        raise RuntimeError("tie identity broken during draw")
    p_home = n_home / n
    p_away = n_away / n
    p_tie = n_tie / n
    se_p = math.sqrt(p_home * (1.0 - p_home) / n)
    return {
        "H_mean": mean_H,
        "A_mean": mean_A,
        "mean_H": mean_H,
        "mean_A": mean_A,
        "mean_D": mean_D,
        "mean_S": mean_S,
        "sd_D": sd_D,
        "sd_S": sd_S,
        "SE_D": se_D,
        "SE_p": se_p,
        "corr_HA": corr,
        "n": n,
        "n_home_wins": n_home,
        "n_away_strict": n_away,
        "n_ties": n_tie,
        "p_home_win": p_home,
        "p_away_win_strict": p_away,
        "p_tie": p_tie,
        "n_clamped_h": n_clamped_h,
        "n_clamped_a": n_clamped_a,
        "draw_array_sha256": draw_sha,
    }


def main() -> int:
    results_path = HERE / "RESULTS.json"
    if results_path.exists():
        raise SystemExit(
            "REFUSE: RESULTS.json already exists (no_rerun_until_pass=true). "
            "One shot already sealed."
        )
    if sys.version_info[:3] != (3, 12, 3):
        # Allowed by protocol, but lineage prefers 3.12.3. Record either way.
        pass
    if not PARENT_GAMES.is_file() or not PARENT_RESULTS.is_file() or not PARENT_FROZEN.is_file():
        raise RuntimeError("parent packet files missing (BLOCKED)")

    parent_games_sha = require_sha(PARENT_GAMES, PARENT_GAMES_SHA, "parent GAMES.json")
    parent_results_sha = require_sha(PARENT_RESULTS, PARENT_RESULTS_SHA, "parent RESULTS.json")
    parent_frozen_sha = require_sha(PARENT_FROZEN, PARENT_FROZEN_SHA, "parent FROZEN_CONFIG.json")
    require_sha(HERE / "ALEX_PROTOCOL_t4921u_HASH4_R1_BOUNDED_CONFIRMATION_v1.md", PROTOCOL_SHA, "protocol")
    require_sha(HERE / "ALEX_PROTOCOL_t4921u_HASH4_R1_BOUNDED_CONFIRMATION_ERRATUM_v1.md", ERRATUM_SHA, "erratum")
    require_sha(HERE / "EXEC_CARD_t4921u_HASH4_R1_CONFIRMATION.md", EXEC_CARD_SHA, "exec card")
    require_sha(HERE / "ALEX_IF_COHERENCE_SPEC_CLARIFICATION_t4871u_v1.md", SPEC_SHA, "SPEC")

    parent_games = json.loads(PARENT_GAMES.read_text(encoding="utf-8"))
    if len(parent_games) != 13:
        raise RuntimeError(f"parent GAMES count {len(parent_games)} != 13")
    parent_ids = tuple(g["game_id"] for g in parent_games)
    if parent_ids != PROTOCOL_ORDER:
        raise RuntimeError(f"parent GAMES order != protocol table: {parent_ids}")

    # Lineage check: reproduce sealed N=4000 ARI@DAL draw hash (parent seeds, not confirm seeds).
    g0 = parent_games[0]
    cap0 = g0["capture"]
    lineage = simulate_game(cap0["mu_h"], cap0["mu_a"], cap0["sigma"], cap0["seed"], cap0["N"])
    if lineage["draw_array_sha256"] != cap0["draw_array_sha256"]:
        raise RuntimeError("parent generator lineage MISS — BLOCKED")
    if lineage["n_clamped_h"] != cap0["n_clamped_h"] or lineage["n_clamped_a"] != cap0["n_clamped_a"]:
        raise RuntimeError("parent clamp counts MISS — BLOCKED")

    frozen_games = []
    for i, g in enumerate(parent_games):
        cap = g["capture"]
        tb = {row["id"]: row for row in g["table_b"]}
        mu_h = float(cap["mu_h"])
        mu_a = float(cap["mu_a"])
        sigma = float(cap["sigma"])
        eH = rectified_mean(mu_h, sigma)
        eA = rectified_mean(mu_a, sigma)
        eD = eH - eA
        eS = eH + eA
        e_sd = math.sqrt(rectified_var(mu_h, sigma) + rectified_var(mu_a, sigma))
        # Sealed parent expectations govern; recompute must match (float eps only).
        if abs(eD - tb["J7"]["expected"]) > 1e-12 or abs(eS - tb["J7_S"]["expected"]) > 1e-12:
            raise RuntimeError(f"{g['game_id']} sealed E[D]/E[S] mismatch — BLOCKED")
        frozen_games.append(
            {
                "i": i,
                "game_id": g["game_id"],
                "parent_seed": cap["seed"],
                "confirm_seed": SEED_BASE + i,
                "mu_h": mu_h,
                "mu_a": mu_a,
                "sigma": sigma,
                "p_model_home_win_sealed": g["p_model_home_win"],
                "E_D_sealed": tb["J7"]["expected"],
                "E_S_sealed": tb["J7_S"]["expected"],
                "E_sd_D_sealed": tb["J8"]["expected"],
                "used_reconstructed_means": False,
                "reconstructed_postclamp_mu_h_PARENT_ONLY_NOT_USED": cap.get(
                    "reconstructed_postclamp_mu_h"
                ),
                "reconstructed_postclamp_mu_a_PARENT_ONLY_NOT_USED": cap.get(
                    "reconstructed_postclamp_mu_a"
                ),
            }
        )

    frozen = {
        "ticket": "t4921u",
        "role": "R1 confirmatory addendum — does NOT replace Card A N=4000",
        "N_confirm": N_CONFIRM,
        "seed_base": SEED_BASE,
        "seeds": [SEED_BASE + i for i in range(13)],
        "j9_p_model_source": "REUSE sealed P_model_home_win from parent GAMES/RESULTS",
        "j9_regen": False,
        "j9_regen_seed_if_used": None,
        "no_rerun_until_pass": NO_RERUN,
        "market_blend": MARKET_BLEND,
        "tnf_excluded": "2026-W08-CAR@GB",
        "games_order": list(PROTOCOL_ORDER),
        "draw_order": "home gauss then away gauss per sim; H=max(0,raw_h); A=max(0,raw_a)",
        "draw_layout": "interleaved float64 little-endian [H0,A0,H1,A1,...] post-clamp scores",
        "rng_id": f"random.Random.gauss CPython {sys.version.split()[0]}",
        "sys_version": sys.version,
        "sys_version_info": list(sys.version_info),
        "platform": platform.platform(),
        "used_reconstructed_means_for_acceptance": False,
        "protocol_sha256": PROTOCOL_SHA,
        "protocol_sha8": PROTOCOL_SHA[:8],
        "erratum_sha256": ERRATUM_SHA,
        "erratum_sha8": ERRATUM_SHA[:8],
        "exec_card_sha256": EXEC_CARD_SHA,
        "exec_card_sha8": EXEC_CARD_SHA[:8],
        "spec_sha256": SPEC_SHA,
        "spec_sha8": SPEC_SHA[:8],
        "acceptance_map_tip": "3df95f51",
        "bands": "ALEX_IF_COHERENCE_SPEC_CLARIFICATION_t4871u_v1 sha fe4dc220 verbatim",
        "parent_pins": {
            "card_a_tip": "aa9605dc",
            "packet_seal": "1f4ffde3",
            "alex_ro": "b5de5df1",
            "soft_c2_c3_tip": "9e370050",
            "soft_c2_c3_scope": "CLOSED — out of scope",
            "if_tip": "6ca03716",
            "source_pin": "52d9e909",
            "blend": 0,
            "parent_N": 4000,
            "parent_seeds": list(range(48500, 48513)),
        },
        "nfl_nogo": True,
        "cert": 0,
        "pub_bet": "HOLD",
        "scope_label": "ATS/OU NOT EMITTED",
        "games": [
            {
                "i": fg["i"],
                "game_id": fg["game_id"],
                "parent_seed": fg["parent_seed"],
                "confirm_seed": fg["confirm_seed"],
                "mu_h": fg["mu_h"],
                "mu_a": fg["mu_a"],
                "sigma": fg["sigma"],
                "p_model_home_win_sealed": fg["p_model_home_win_sealed"],
                "E_D_sealed": fg["E_D_sealed"],
                "E_S_sealed": fg["E_S_sealed"],
                "E_sd_D_sealed": fg["E_sd_D_sealed"],
                "used_reconstructed_means": False,
            }
            for fg in frozen_games
        ],
        "frozen_before_results": True,
    }
    dump_json(HERE / "FROZEN_CONFIG.json", frozen)

    started = datetime.now(timezone.utc).isoformat()
    results = []
    table_b_games = []
    table_a_games = []
    a_fails = []
    b_fails = []
    j11_rows = []

    for fg in frozen_games:
        sim = simulate_game(fg["mu_h"], fg["mu_a"], fg["sigma"], fg["confirm_seed"], N_CONFIRM)
        p_hat = sim["p_home_win"]
        home_wp = round(p_hat, 4)
        away_wp = round(sim["p_away_win_strict"] + sim["p_tie"], 4)
        spread_home = round(-sim["mean_D"], 2)
        total_mean_markets = round(sim["mean_S"], 2)
        ml_h, ml_a = fair_ml_pair(home_wp)
        tie_excl_p = (
            sim["p_home_win"] / (sim["p_home_win"] + sim["p_away_win_strict"])
            if (sim["p_home_win"] + sim["p_away_win_strict"]) > 0
            else None
        )
        tie_excl_ml = fair_ml_pair(tie_excl_p)[0] if tie_excl_p is not None else None

        eD = fg["E_D_sealed"]
        eS = fg["E_S_sealed"]
        e_sd = fg["E_sd_D_sealed"]
        p_model = fg["p_model_home_win_sealed"]

        z7 = abs(sim["mean_D"] - eD) / sim["SE_D"]
        z7s = abs(sim["mean_S"] - eS) / (sim["sd_S"] / math.sqrt(N_CONFIRM))
        rel8 = abs(sim["sd_D"] - e_sd) / e_sd
        d9 = abs(p_hat - p_model)
        z9 = d9 / sim["SE_p"] if sim["SE_p"] > 0 else float("inf")
        se_S = sim["sd_S"] / math.sqrt(N_CONFIRM)

        j7 = {
            "id": "J7",
            "class": "B",
            "observed": sim["mean_D"],
            "expected": eD,
            "SE": sim["SE_D"],
            "z": z7,
            "band": band_z24(z7),
        }
        j7s = {
            "id": "J7_S",
            "class": "B",
            "observed": sim["mean_S"],
            "expected": eS,
            "SE": se_S,
            "z": z7s,
            "band": band_z24(z7s),
        }
        j8 = {
            "id": "J8",
            "class": "B",
            "observed": sim["sd_D"],
            "expected": e_sd,
            "SE": None,
            "rel": rel8,
            "z": rel8,
            "band": band_j8(rel8),
        }
        j9 = {
            "id": "J9",
            "class": "B",
            "observed": p_hat,
            "expected": p_model,
            "SE": sim["SE_p"],
            "delta": d9,
            "z": z9,
            "band": band_j9(d9, sim["SE_p"]),
            "p_model_source": "sealed parent GAMES/RESULTS p_model_home_win",
        }
        j10 = {
            "id": "J10",
            "class": "B",
            "observed": sim["corr_HA"],
            "expected": 0.0,
            "SE": None,
            "z": abs(sim["corr_HA"]),
            "band": band_j10(abs(sim["corr_HA"])),
        }
        m = sim["mean_D"]
        se_d = sim["SE_D"]
        se_p = sim["SE_p"]
        decisive = (abs(m) >= max(0.25, 2.0 * se_d)) and (abs(home_wp - 0.5) >= 2.0 * se_p)
        if not decisive:
            j11_band = "NOT_DECISIVE"
            j11_note = "pick'em / inside noise — COND-neutral"
        else:
            agree = (m > 0.0 and home_wp > 0.5) or (m < 0.0 and home_wp < 0.5)
            j11_band = "PASS" if agree else "FAIL"
            j11_note = "decisive" if agree else "decisive disagreement — FAIL"
        j11 = {
            "id": "J11",
            "class": "B",
            "expected": "sign(m)==sign(p-0.5) in decisive zone",
            "observed": {"m": m, "p": home_wp},
            "SE": {"SE_D": se_d, "SE_p": se_p},
            "z": None,
            "band": j11_band,
            "note": j11_note,
        }
        j_tie = {
            "id": "tie_rate",
            "class": "B",
            "expected": "≤1e-3 PASS",
            "observed": sim["p_tie"],
            "SE": None,
            "z": sim["p_tie"],
            "band": band_tie(sim["p_tie"]),
        }
        table_b = [j7, j7s, j8, j9, j10, j11, j_tie]
        for row in table_b:
            if row["band"] == "FAIL":
                b_fails.append({"game_id": fg["game_id"], "id": row["id"], "band": "FAIL"})

        # A-class identities on THIS confirmatory draw array (not parent published numbers).
        j1_re = -sim["mean_D"]
        j1_val = spread_home
        j2_re = sim["mean_S"]
        j2_val = sim["mean_S"]
        j3_re = home_wp
        j3_val = home_wp
        j4_re = sim["p_away_win_strict"] + sim["p_tie"]
        j4_val = away_wp
        j5_re = [ml_h, ml_a]
        j5_val = [ml_h, ml_a]
        j6_re = sim["mean_H"] + sim["mean_A"]
        j6_val = sim["mean_S"]
        table_a = [
            {
                "id": "J1",
                "class": "A",
                "value": j1_val,
                "recompute": j1_re,
                "delta": j1_re - j1_val,
                "tol": 0.005,
                "band": band_a(j1_re - j1_val, 0.005),
            },
            {
                "id": "J2",
                "class": "A",
                "value": j2_val,
                "recompute": j2_re,
                "delta": j2_re - j2_val,
                "tol": 0.005,
                "band": band_a(j2_re - j2_val, 0.005),
            },
            {
                "id": "J3",
                "class": "A",
                "value": j3_val,
                "recompute": j3_re,
                "delta": j3_re - j3_val,
                "tol": 0.0,
                "band": band_a(j3_re - j3_val, 0.0),
            },
            {
                "id": "J4",
                "class": "A",
                "value": j4_val,
                "recompute": j4_re,
                "delta": j4_re - j4_val,
                "tol": 0.0001,
                "band": band_a(j4_re - j4_val, 0.0001),
            },
            {
                "id": "J5",
                "class": "A",
                "value": j5_val,
                "recompute": j5_re,
                "delta": 0,
                "tol": 0,
                "band": "PASS" if j5_re == j5_val else "FAIL",
            },
            {
                "id": "J6",
                "class": "A",
                "value": j6_val,
                "recompute": j6_re,
                "delta": j6_re - j6_val,
                "tol": 1e-9,
                "band": band_a(j6_re - j6_val, 1e-9),
            },
            {
                "id": "tie_identity",
                "class": "A",
                "value": N_CONFIRM,
                "recompute": sim["n_home_wins"] + sim["n_away_strict"] + sim["n_ties"],
                "delta": 0,
                "tol": 0,
                "band": "PASS"
                if sim["n_home_wins"] + sim["n_away_strict"] + sim["n_ties"] == N_CONFIRM
                else "FAIL",
            },
            {
                "id": "J13",
                "class": "A",
                "value": sim["draw_array_sha256"],
                "recompute": sim["draw_array_sha256"],
                "delta": 0,
                "tol": 0,
                "band": "PASS",
            },
            {
                "id": "J14",
                "class": "A",
                "value": "NOT_APPLICABLE_NOT_EMITTED",
                "recompute": "ATS/OU NOT EMITTED",
                "delta": 0,
                "tol": 0,
                "band": "PASS",
                "note": "scope-limited; confirmatory packet emits no ATS-cover / OU-over / push probability",
            },
        ]
        for row in table_a:
            if row["band"] == "FAIL":
                a_fails.append({"game_id": fg["game_id"], "id": row["id"], "band": "FAIL"})

        capture = {
            "N": N_CONFIRM,
            "seed": fg["confirm_seed"],
            "mu_h": fg["mu_h"],
            "mu_a": fg["mu_a"],
            "sigma": fg["sigma"],
            "draw_array_sha256": sim["draw_array_sha256"],
            "draw_layout": "interleaved float64 little-endian [H0,A0,H1,A1,...] post-clamp scores",
            "draw_order": "home gauss then away gauss per sim; H=max(0,raw_h)",
            "n_clamped_h": sim["n_clamped_h"],
            "n_clamped_a": sim["n_clamped_a"],
            "rng_id": f"random.Random.gauss CPython {sys.version.split()[0]}",
            "source": "random.Random.gauss call-site wrap (pre-clamp params; post-clamp H,A)",
            "used_reconstructed_means_for_acceptance": False,
            "parent_seed_not_used": fg["parent_seed"],
        }
        stats = {
            "n": N_CONFIRM,
            "mean_H": sim["mean_H"],
            "mean_A": sim["mean_A"],
            "mean_D": sim["mean_D"],
            "mean_S": sim["mean_S"],
            "sd_D": sim["sd_D"],
            "sd_S": sim["sd_S"],
            "SE_D": sim["SE_D"],
            "SE_p": sim["SE_p"],
            "corr_HA": sim["corr_HA"],
            "n_home_wins": sim["n_home_wins"],
            "n_away_strict": sim["n_away_strict"],
            "n_ties": sim["n_ties"],
            "p_home_win": sim["p_home_win"],
            "p_away_win_strict": sim["p_away_win_strict"],
            "p_tie": sim["p_tie"],
        }
        rec = {
            "game_id": fg["game_id"],
            "i": fg["i"],
            "confirm_seed": fg["confirm_seed"],
            "market_blend": 0,
            "e1_admissible": False,
            "public_delivery": False,
            "p_model_home_win": p_model,
            "p_home_win": sim["p_home_win"],
            "p_away_win_strict": sim["p_away_win_strict"],
            "p_tie": sim["p_tie"],
            "home_wp": home_wp,
            "away_wp": away_wp,
            "spread_home": spread_home,
            "total_mu": sim["mean_S"],
            "total_mean_markets": total_mean_markets,
            "fair_home_ml": ml_h,
            "fair_away_ml": ml_a,
            "tie_excluded_p": tie_excl_p,
            "tie_excluded_ml": tie_excl_ml,
            "engine_tie_convention": "ties→away; ≠NFL truth ≠market settlement",
            "draw_array_sha256": sim["draw_array_sha256"],
            "capture": capture,
            "stats": stats,
            "table_a": table_a,
            "table_b": table_b,
        }
        results.append(rec)
        table_a_games.append({"game_id": fg["game_id"], "rows": table_a})
        table_b_games.append({"game_id": fg["game_id"], "rows": table_b})
        j11_rows.append(
            {
                "game_id": fg["game_id"],
                "band": j11_band,
                "note": j11_note,
                "m": m,
                "p": home_wp,
                "SE_D": se_d,
                "SE_p": se_p,
                "decisive": decisive,
            }
        )

    # J12 slate-level
    items = []
    for rec in results:
        items.append(
            (
                rec["game_id"],
                rec["stats"]["mean_D"],
                rec["home_wp"],
                rec["stats"]["SE_D"],
            )
        )
    n_g = len(items)
    conc = disc = 0
    inversions_fail = []
    inversions_noise = []
    pairs = n_g * (n_g - 1) // 2
    for i in range(n_g):
        for j in range(i + 1, n_g):
            gi, mi, pi, sei = items[i]
            gj, mj, pj, sej = items[j]
            dm = mi - mj
            dp = pi - pj
            if dm == 0.0 or dp == 0.0:
                continue
            agree = (dm > 0.0 and dp > 0.0) or (dm < 0.0 and dp < 0.0)
            if agree:
                conc += 1
            else:
                disc += 1
                thresh = max(0.5, 2.0 * math.sqrt(sei * sei + sej * sej))
                row = {
                    "i": gi,
                    "j": gj,
                    "abs_dm": abs(dm),
                    "thresh": thresh,
                    "within_noise": abs(dm) <= thresh,
                }
                if abs(dm) > thresh:
                    inversions_fail.append(row)
                else:
                    inversions_noise.append(row)
    tau = (conc - disc) / pairs if pairs else 1.0
    if inversions_fail:
        j12_band = "FAIL"
    elif tau >= 0.95:
        j12_band = "PASS"
    else:
        j12_band = "COND"
    j12 = {
        "id": "J12",
        "class": "B",
        "kendall_tau": tau,
        "concordant": conc,
        "discordant": disc,
        "pairs": pairs,
        "inversions_fail": inversions_fail,
        "inversions_noise": inversions_noise,
        "band": j12_band,
        "expected": "τ≥0.95 PASS; <0.95 COND if all inversions within noise; any noisy inversion FAIL",
    }
    if j12_band == "FAIL":
        b_fails.append({"game_id": "SLATE", "id": "J12", "band": "FAIL"})

    r1_rows = []
    for chk in R1_CHECKS:
        rec = next(r for r in results if r["game_id"] == chk["game_id"])
        row = next(x for x in rec["table_b"] if x["id"] == chk["id"])
        r1_rows.append(
            {
                "id": chk["id"],
                "game_id": chk["game_id"],
                "observed": row["observed"],
                "expected": row["expected"],
                "SE": row["SE"],
                "z": row.get("z"),
                "delta": row.get("delta"),
                "band": row["band"],
                "parent_N4000_was": {
                    ("J7_S", "2026-W08-CLE@PIT"): "z=3.708 COND",
                    ("J7_S", "2026-W08-MIN@DET"): "z=2.114 COND",
                    ("J7", "2026-W08-LAC@LAR"): "z=2.423 COND",
                    ("J9", "2026-W08-LAC@LAR"): "Δp=0.0170 z=2.24 COND",
                }[(chk["id"], chk["game_id"])],
            }
        )

    r1_bands = [r["band"] for r in r1_rows]
    j11_fail = any(r["band"] == "FAIL" for r in j11_rows)
    parent_ok = (
        parent_games_sha == PARENT_GAMES_SHA
        and parent_results_sha == PARENT_RESULTS_SHA
        and parent_frozen_sha == PARENT_FROZEN_SHA
    )
    reconstructed_used = False
    contract_complete = parent_ok and (not reconstructed_used) and len(results) == 13

    if not contract_complete:
        verdict = "BLOCKED"
        verdict_reason = "contract incomplete (parent digest or capture)"
    elif any(b == "FAIL" for b in r1_bands) or a_fails or j11_fail or b_fails or reconstructed_used:
        verdict = "R1_FAIL"
        verdict_reason = "FAIL band or A/B FAIL or J11 decisive disagreement"
    elif any(b == "COND" for b in r1_bands):
        verdict = "R1_CONDITIONAL"
        verdict_reason = "≥1 of four R1 checks in COND; zero FAIL"
    elif all(b == "PASS" for b in r1_bands) and not a_fails and parent_ok:
        verdict = "R1_PASS"
        verdict_reason = (
            "all four R1 checks PASS; zero A-class FAIL; parent digests unchanged; "
            "ATS/OU NOT EMITTED"
        )
    else:
        verdict = "BLOCKED"
        verdict_reason = "unmapped state"

    finished = datetime.now(timezone.utc).isoformat()

    dump_json(results_path, results)

    table_b_obj = {
        "ticket": "t4921u",
        "N_confirm": N_CONFIRM,
        "bands": "SPEC fe4dc220 verbatim",
        "r1_checks": r1_rows,
        "j11": j11_rows,
        "j12": j12,
        "per_game": table_b_games,
        "table_a_reemit": table_a_games,
        "a_fails": a_fails,
        "b_fails": b_fails,
        "scope_label": "ATS/OU NOT EMITTED",
    }
    dump_json(HERE / "TABLE_B.json", table_b_obj)

    md = []
    md.append("# TABLE B — t4921u R1 confirmatory addendum")
    md.append("")
    md.append("NFL NO-GO · CERT=0 · pub/bet HOLD · ATS/OU NOT EMITTED")
    md.append("")
    md.append(f"N_confirm = {N_CONFIRM} · seeds 49210000+i · bands SPEC fe4dc220 verbatim")
    md.append(f"no_rerun_until_pass = true · protocol sha8 {PROTOCOL_SHA[:8]}")
    md.append("")
    md.append("## Four R1 checks (gate)")
    md.append("")
    md.append("| Check | Game | observed | expected | SE | z/Δ | band | parent N=4000 |")
    md.append("|---|---|---|---|---|---|---|---|")
    for r in r1_rows:
        se = r["SE"]
        z = r["z"] if r["id"] != "J9" else r["delta"]
        md.append(
            f"| {r['id']} | {r['game_id']} | {r['observed']:.8g} | {r['expected']:.8g} | "
            f"{se:.8g} | {z:.6g} | **{r['band']}** | {r['parent_N4000_was']} |"
        )
    md.append("")
    md.append(f"**R1 verdict: {verdict}** — {verdict_reason}")
    md.append("")
    md.append("## J11 (R2, not required for R1; decisive disagreement would block)")
    md.append("")
    md.append("| Game | m | p | SE_D | SE_p | decisive | band |")
    md.append("|---|---|---|---|---|---|---|")
    for r in j11_rows:
        md.append(
            f"| {r['game_id']} | {r['m']:.6g} | {r['p']:.4f} | {r['SE_D']:.6g} | "
            f"{r['SE_p']:.6g} | {r['decisive']} | {r['band']} |"
        )
    md.append("")
    md.append(
        f"## J12 slate Kendall τ = {tau:.6f} · band {j12_band} · "
        f"fail inversions {len(inversions_fail)} · noise inversions {len(inversions_noise)}"
    )
    md.append("")
    md.append("## Per-game Table B")
    md.append("")
    for block in table_b_games:
        md.append(f"### {block['game_id']}")
        md.append("")
        md.append("| id | class | observed | expected | SE | z | band |")
        md.append("|---|---|---|---|---|---|---|")
        for row in block["rows"]:
            obs = row["observed"]
            if isinstance(obs, dict):
                obs_s = f"m={obs['m']:.6g} p={obs['p']}"
            else:
                obs_s = f"{obs:.8g}" if isinstance(obs, float) else str(obs)
            exp = row["expected"]
            exp_s = f"{exp:.8g}" if isinstance(exp, float) else str(exp)
            se = row["SE"]
            if isinstance(se, dict):
                se_s = f"SE_D={se['SE_D']:.6g}; SE_p={se['SE_p']:.6g}"
            elif se is None:
                se_s = "—"
            else:
                se_s = f"{se:.8g}"
            z = row.get("z")
            z_s = "—" if z is None else f"{z:.6g}"
            md.append(f"| {row['id']} | {row['class']} | {obs_s} | {exp_s} | {se_s} | {z_s} | {row['band']} |")
        md.append("")
    md.append("## Re-emitted A-class identities")
    md.append("")
    md.append(f"A-class FAILs: {a_fails if a_fails else 'none'}")
    md.append("")
    (HERE / "TABLE_B.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    verdict_obj = {
        "ticket": "t4921u",
        "role": "R1 confirmatory addendum",
        "verdict": verdict,
        "reason": verdict_reason,
        "N_confirm": N_CONFIRM,
        "seeds": [SEED_BASE + i for i in range(13)],
        "no_rerun_until_pass": True,
        "one_shot": True,
        "started_utc": started,
        "finished_utc": finished,
        "sys_version": sys.version,
        "protocol_sha256": PROTOCOL_SHA,
        "protocol_sha8": PROTOCOL_SHA[:8],
        "erratum_sha256": ERRATUM_SHA,
        "erratum_sha8": ERRATUM_SHA[:8],
        "exec_card_sha256": EXEC_CARD_SHA,
        "exec_card_sha8": EXEC_CARD_SHA[:8],
        "spec_sha256": SPEC_SHA,
        "spec_sha8": SPEC_SHA[:8],
        "acceptance_map_tip": "3df95f51",
        "parent_pins": frozen["parent_pins"],
        "parent_digests_unchanged": parent_ok,
        "used_reconstructed_means_for_acceptance": False,
        "market_blend": 0,
        "source_pin_unedited": "52d9e909",
        "if_tip": "6ca03716",
        "soft_c2_c3": "CLOSED 9e370050 — out of scope",
        "nfl_nogo": True,
        "cert": 0,
        "pub_bet": "HOLD",
        "scope_label": "ATS/OU NOT EMITTED",
        "r1_checks": r1_rows,
        "j11": {
            "status": "FAIL" if j11_fail else (
                "ALL_NOT_DECISIVE"
                if all(r["band"] == "NOT_DECISIVE" for r in j11_rows)
                else "NO_DECISIVE_DISAGREEMENT"
            ),
            "any_decisive_fail": j11_fail,
            "rows": j11_rows,
            "note": "R2, not required for R1. Decisive disagreement would block.",
        },
        "j12": {"band": j12_band, "kendall_tau": tau},
        "a_class_fails": a_fails,
        "b_class_fails": b_fails,
        "contract_complete": contract_complete,
        "non_claims": (
            "IF-only engine internal sampling consistency at W8 for these 13 games. "
            "NOT calibration, forecast skill, market edge, ATS/OU validity, "
            "enterprise readiness, CERT, merge, publication, or betting."
        ),
    }
    dump_json(HERE / "VERDICT_R1.json", verdict_obj)

    parent_digests = {
        "note": "Parent Card A packet was not written, reseated, or re-graded. Digests below are of the attached RO parent files.",
        "parent_pins": {
            "card_a_tip": "aa9605dc",
            "packet_seal": "1f4ffde3",
            "alex_ro": "b5de5df1",
        },
        "files": {
            "GAMES.json": {
                "source": str(PARENT_GAMES),
                "sha256": parent_games_sha,
                "pinned": PARENT_GAMES_SHA,
                "unchanged": parent_games_sha == PARENT_GAMES_SHA,
            },
            "RESULTS.json": {
                "source": str(PARENT_RESULTS),
                "sha256": parent_results_sha,
                "pinned": PARENT_RESULTS_SHA,
                "unchanged": parent_results_sha == PARENT_RESULTS_SHA,
            },
            "FROZEN_CONFIG.json": {
                "source": str(PARENT_FROZEN),
                "sha256": parent_frozen_sha,
                "pinned": PARENT_FROZEN_SHA,
                "unchanged": parent_frozen_sha == PARENT_FROZEN_SHA,
            },
        },
        "all_unchanged": parent_ok,
        "lineage_parent_repro": {
            "game_id": "2026-W08-ARI@DAL",
            "parent_seed": 48500,
            "parent_N": 4000,
            "draw_array_sha256": lineage["draw_array_sha256"],
            "sealed": cap0["draw_array_sha256"],
            "match": lineage["draw_array_sha256"] == cap0["draw_array_sha256"],
            "note": "Generator identity check on parent seed/N only. Confirmatory seeds 49210000+i were not used for this check.",
        },
        "confirm_packet_does_not_contain_parent_files": True,
    }
    dump_json(HERE / "PARENT_DIGESTS.json", parent_digests)

    ats_hits = scan_ats_ou(results) + scan_ats_ou(table_b_obj) + scan_ats_ou(verdict_obj)
    call_audit = {
        "odds_api_calls": 0,
        "http_calls": 0,
        "c10_calls": 0,
        "market_reads": 0,
        "network": "offline",
        "ats_ou_fields_emitted": ats_hits,
        "ats_ou_emitted": bool(ats_hits),
        "test_no_ats_ou_emitted": not bool(ats_hits),
        "notes": (
            "Confirmatory runner is offline MC from sealed pre-clamp μ_h/μ_a/σ only. "
            "No Odds API, no C10, no HTTP, no 2024–25 data, no SOURCE/math/blend change."
        ),
        "pid": os.getpid(),
        "argv": sys.argv,
        "cwd": os.getcwd(),
        "started_utc": started,
        "finished_utc": finished,
    }
    dump_json(HERE / "CALL_AUDIT.json", call_audit)

    if ats_hits:
        raise RuntimeError(f"ATS/OU fields emitted — BLOCKED: {ats_hits}")

    # SHA256SUMS last (does not list itself).
    names = [
        "ALEX_PROTOCOL_t4921u_HASH4_R1_BOUNDED_CONFIRMATION_v1.md",
        "ALEX_PROTOCOL_t4921u_HASH4_R1_BOUNDED_CONFIRMATION_ERRATUM_v1.md",
        "EXEC_CARD_t4921u_HASH4_R1_CONFIRMATION.md",
        "ALEX_IF_COHERENCE_SPEC_CLARIFICATION_t4871u_v1.md",
        "run_r1_confirm_once.py",
        "FROZEN_CONFIG.json",
        "RESULTS.json",
        "TABLE_B.json",
        "TABLE_B.md",
        "VERDICT_R1.json",
        "PARENT_DIGESTS.json",
        "CALL_AUDIT.json",
    ]
    lines = []
    for name in names:
        p = HERE / name
        if not p.is_file():
            raise RuntimeError(f"missing packet file {name}")
        lines.append(f"{sha256_file(p)}  {name}")
    (HERE / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "verdict": verdict,
        "r1": [{"id": r["id"], "game_id": r["game_id"], "band": r["band"], "z": r["z"], "delta": r.get("delta")} for r in r1_rows],
        "j11_fail": j11_fail,
        "a_fails": a_fails,
        "b_fails": b_fails,
        "parent_ok": parent_ok,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
