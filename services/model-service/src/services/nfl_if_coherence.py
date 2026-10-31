"""IF-only joint score-distribution coherence (OWNER Card A t4871u).

Clarification fe4dc220 governs. No forecast math change. No tolerance retune.
SOURCE ONLY pin 52d9e909 is not rewritten — capture wraps Random.gauss.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import struct
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple
from uuid import uuid4

from src.services.nfl_offline_if_caller import (
    IF_SOURCE_PIN_SHA256,
    OfflineIfCallerReject,
    REJECT_SPORTSBOOK,
    REJECT_THROUGH_W8,
    build_contract_inputs,
    evaluate_caller,
    reject_sportsbook,
    sha256_file,
    verify_asof_module,
    verify_source_pin,
)
from src.services.nfl_offline_if_eval_w8 import (
    EVAL_SEED_BASE,
    EVAL_SIMULATIONS,
    PANEL_SHA256,
    SCHEDULE_SHA256,
    SUPPORTED_GAMES,
    TNF_GAME_ID,
    THROUGH_W7_ACCEPT,
    THROUGH_W7_ACCEPT_SHA256,
    EvalW8Reject,
    build_eval_request,
    history_w1_w7,
    load_panel,
    load_schedule,
)
from src.services.nfl_offline_if_eval_w8_v2 import CallAudit, V2_DIR
from src.services.nfl_offline_if_eval_w8_v3 import V2_PACKET_TIP
from src.services.nfl_simulator import (
    _fair_moneyline_from_prob,
    independent_fair_mus,
    simulate_nfl_game_independent_fair,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
PARENT_PACKET_DIR = (
    REPO_ROOT / "data" / "ops" / "nfl-offline-if-caller-t4838u" / "eval_w8_t4871u_coherence"
)
PACKET_DIR = (
    REPO_ROOT / "data" / "ops" / "nfl-offline-if-caller-t4838u" / "eval_w8_t4871u_coherence_v2"
)
CLI_REL = "scripts/nfl/run_offline_if_coherence_t4871u.py"
CMD = f"PYTHONPATH=services/model-service python3 {CLI_REL} --write-packet"
PARENT_PACKET_TIP = "aa9605dc52dc24d73d73d8e9d0c5588a39e2762a"
PARENT_PACKET_SEAL = "1f4ffde3f8fd0894a50cc1410ce815925ea4acde"
ALEX_RO_CARD_A = "b5de5df1"
# C2 negative fixture only — never a packet-run seed. Distinct from SEED_BASE+0..12.
SECOND_SEED_C2 = 148500
SECOND_SEED_C2_FALLBACKS = (148501, 148502, 148503)
CLARIFICATION_SHA256 = (
    "fe4dc220d208fe6312cb32c7e441c49448d6e3b11c40639d919f47b5aedbea95"
)
PARENT_PAPER_SHA256 = (
    "05222939cc37086f0544063df3a6b66a1238cbc4bf92d7a0b88b2522718f0d3a"
)
OWNER_CLEAR = "t4871u"
N_PACKET = 4000
SEED_BASE = EVAL_SEED_BASE
J9_MC_N = 1_000_000
J9_MC_SEED = 48711001
RNG_ID = f"random.Random.gauss CPython {sys.version.split()[0]}"
DRAW_LAYOUT = "interleaved float64 little-endian [H0,A0,H1,A1,...] post-clamp scores"
ATS_OU_EXACT = {
    "ats",
    "ats_cover",
    "ats_line",
    "p_cover",
    "p_over",
    "p_under",
    "p_push",
    "cover_prob",
    "over_prob",
    "under_prob",
    "push_prob",
    "ou_over",
    "ou_under",
    "ou_push",
    "fair_ats",
    "cover",
    "push",
}
SOURCE_GUARD = (
    "services/model-service/src/services/nfl_if_coherence.py",
    "scripts/nfl/run_offline_if_coherence_t4871u.py",
    "services/model-service/src/services/nfl_simulator.py",
    "services/model-service/tests/test_nfl_if_coherence_t4871u.py",
)
PYTEST_FILES = (
    "services/model-service/tests/test_nfl_if_coherence_t4871u.py",
    "services/model-service/tests/test_nfl_offline_if_caller_t4838u.py",
    "services/model-service/tests/test_nfl_offline_if_eval_w8_t4850u.py",
    "services/model-service/tests/test_nfl_offline_if_eval_w8_t4850u_v2.py",
    "services/model-service/tests/test_nfl_offline_if_eval_w8_t4862u_d2.py",
    "services/model-service/tests/test_nfl_offline_if_eval_w8_t4850u_v3.py",
)


def _phi(z: float) -> float:
    return math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def _Phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def truncated_pos_mean(mu: float, sigma: float) -> float:
    """E[max(0, X)] for X~N(mu, sigma)."""
    if sigma <= 0:
        return max(0.0, mu)
    z = mu / sigma
    return mu * _Phi(z) + sigma * _phi(z)


def truncated_pos_var(mu: float, sigma: float) -> float:
    """Var[max(0, X)] for X~N(mu, sigma)."""
    if sigma <= 0:
        return 0.0
    z = mu / sigma
    mean = truncated_pos_mean(mu, sigma)
    second = (mu * mu + sigma * sigma) * _Phi(z) + mu * sigma * _phi(z)
    return max(0.0, second - mean * mean)


def fair_ml(prob: float) -> int:
    return _fair_moneyline_from_prob(prob)


def pack_ha_sha256(home: Sequence[float], away: Sequence[float]) -> str:
    buf = bytearray()
    for h, a in zip(home, away):
        buf.extend(struct.pack("<d", float(h)))
        buf.extend(struct.pack("<d", float(a)))
    return hashlib.sha256(buf).hexdigest()


class GaussCapture:
    """Call-site wrap of random.Random.gauss. Does not change return values."""

    def __init__(self) -> None:
        self.calls: List[Tuple[float, float, float]] = []
        self._orig = random.Random.gauss

    def __enter__(self) -> "GaussCapture":
        cap = self

        def wrapped(self_rng: random.Random, mu: float = 0.0, sigma: float = 1.0) -> float:
            val = cap._orig(self_rng, mu, sigma)
            cap.calls.append((float(mu), float(sigma), float(val)))
            return val

        random.Random.gauss = wrapped  # type: ignore[method-assign]
        return self

    def __exit__(self, *exc: object) -> None:
        random.Random.gauss = self._orig  # type: ignore[method-assign]


def draws_from_gauss_calls(calls: Sequence[Tuple[float, float, float]]) -> Dict[str, Any]:
    if len(calls) < 2 or len(calls) % 2 != 0:
        raise EvalW8Reject("CAPTURE", f"gauss call count {len(calls)} is not 2N")
    home_mu = {c[0] for c in calls[0::2]}
    away_mu = {c[0] for c in calls[1::2]}
    sigmas = {c[1] for c in calls}
    if len(home_mu) != 1 or len(away_mu) != 1 or len(sigmas) != 1:
        raise EvalW8Reject("CAPTURE", "gauss params were not constant per side")
    mu_h = next(iter(home_mu))
    mu_a = next(iter(away_mu))
    sigma = next(iter(sigmas))
    raw_h = [c[2] for c in calls[0::2]]
    raw_a = [c[2] for c in calls[1::2]]
    home = [max(0.0, x) for x in raw_h]
    away = [max(0.0, x) for x in raw_a]
    return {
        "mu_h": mu_h,
        "mu_a": mu_a,
        "sigma": sigma,
        "n": len(home),
        "n_clamped_h": sum(1 for x in raw_h if x < 0.0),
        "n_clamped_a": sum(1 for x in raw_a if x < 0.0),
        "home": home,
        "away": away,
        "sha256": pack_ha_sha256(home, away),
        "source": "random.Random.gauss call-site wrap (pre-clamp params; post-clamp H,A)",
        "draw_order": "home gauss then away gauss per sim; H=max(0,raw_h)",
        "rng_id": RNG_ID,
        "draw_layout": DRAW_LAYOUT,
    }


def summarize_draws(home: Sequence[float], away: Sequence[float]) -> Dict[str, Any]:
    n = len(home)
    d = [float(h) - float(a) for h, a in zip(home, away)]
    s = [float(h) + float(a) for h, a in zip(home, away)]
    n_home = sum(1 for x in d if x > 0.0)
    n_away_strict = sum(1 for x in d if x < 0.0)
    n_tie = sum(1 for x in d if x == 0.0)
    if n_home + n_away_strict + n_tie != n:
        raise EvalW8Reject("TIE_IDENTITY", "n_home+n_away_strict+n_tie != N")
    mean_h = sum(home) / n
    mean_a = sum(away) / n
    mean_d = sum(d) / n
    mean_s = sum(s) / n
    sd_d = math.sqrt(sum((x - mean_d) ** 2 for x in d) / (n - 1))
    sd_s = math.sqrt(sum((x - mean_s) ** 2 for x in s) / (n - 1))
    sd_h = math.sqrt(sum((x - mean_h) ** 2 for x in home) / (n - 1))
    sd_a = math.sqrt(sum((x - mean_a) ** 2 for x in away) / (n - 1))
    cov = sum((h - mean_h) * (a - mean_a) for h, a in zip(home, away)) / (n - 1)
    corr = cov / (sd_h * sd_a) if sd_h > 0 and sd_a > 0 else 0.0
    p_home = n_home / n
    p_away_strict = n_away_strict / n
    p_tie = n_tie / n
    se_d = sd_d / math.sqrt(n)
    se_p = math.sqrt(p_home * (1.0 - p_home) / n)
    return {
        "n": n,
        "mean_H": mean_h,
        "mean_A": mean_a,
        "mean_D": mean_d,
        "mean_S": mean_s,
        "sd_D": sd_d,
        "sd_S": sd_s,
        "corr_HA": corr,
        "n_home_wins": n_home,
        "n_away_strict": n_away_strict,
        "n_ties": n_tie,
        "p_home_win": p_home,
        "p_away_win_strict": p_away_strict,
        "p_tie": p_tie,
        "SE_D": se_d,
        "SE_p": se_p,
    }


def j7_band(z: float) -> str:
    if z <= 2.0:
        return "PASS"
    if z <= 4.0:
        return "COND"
    return "FAIL"


def j10_band(abs_rho: float) -> str:
    if abs_rho <= 0.05:
        return "PASS"
    if abs_rho <= 0.10:
        return "COND"
    return "FAIL"


def j8_band(rel: float) -> str:
    if rel <= 0.03:
        return "PASS"
    if rel <= 0.08:
        return "COND"
    return "FAIL"


def j9_band(delta: float, se_p: float) -> str:
    fail_bound = 0.03 if (2.0 * se_p) <= 0.03 else (4.0 * se_p)
    if delta <= 2.0 * se_p:
        return "PASS"
    if delta <= fail_bound:
        return "COND"
    return "FAIL"


def tie_rate_band(p_tie: float) -> str:
    if p_tie <= 1e-3:
        return "PASS"
    if p_tie <= 5e-3:
        return "COND"
    return "FAIL"


def p_model_home_win(mu_h: float, mu_a: float, sigma: float) -> float:
    rng = random.Random(J9_MC_SEED)
    wins = 0
    for _ in range(J9_MC_N):
        h = max(0.0, rng.gauss(mu_h, sigma))
        a = max(0.0, rng.gauss(mu_a, sigma))
        if h > a:
            wins += 1
    return wins / J9_MC_N


def invoke_with_capture(req: Any) -> Dict[str, Any]:
    verify_source_pin()
    verify_asof_module()
    inputs = build_contract_inputs(req)
    cap = GaussCapture()
    with cap:
        projection = simulate_nfl_game_independent_fair(
            inputs,
            simulations=req.simulations,
            seed=req.seed,
            market_spread_home=None,
            market_total=None,
        )
    draws = draws_from_gauss_calls(cap.calls)
    if draws["n"] != int(req.simulations):
        raise EvalW8Reject("CAPTURE", f"captured N={draws['n']} != simulations={req.simulations}")
    stats = summarize_draws(draws["home"], draws["away"])
    markets = projection["markets"]
    margin_mu, total_mu = independent_fair_mus(projection)
    reconstructed_mu_h = (stats["mean_S"] + stats["mean_D"]) / 2.0
    reconstructed_mu_a = (stats["mean_S"] - stats["mean_D"]) / 2.0
    capture = {
        "mu_h": draws["mu_h"],
        "mu_a": draws["mu_a"],
        "sigma": draws["sigma"],
        "seed": req.seed,
        "N": draws["n"],
        "rng_id": draws["rng_id"],
        "draw_order": draws["draw_order"],
        "n_clamped_h": draws["n_clamped_h"],
        "n_clamped_a": draws["n_clamped_a"],
        "draw_array_sha256": draws["sha256"],
        "draw_layout": draws["draw_layout"],
        "source": draws["source"],
        "reconstructed_postclamp_mu_h": reconstructed_mu_h,
        "reconstructed_postclamp_mu_a": reconstructed_mu_a,
        "used_reconstructed_means_for_acceptance": False,
    }
    if math.isclose(draws["mu_h"], reconstructed_mu_h, abs_tol=1e-12) and math.isclose(
        draws["mu_a"], reconstructed_mu_a, abs_tol=1e-12
    ):
        raise EvalW8Reject("RECONSTRUCTED_MEANS", "captured μ equals post-clamp reconstructed means")
    p_home_ex = (
        stats["p_home_win"] / (stats["p_home_win"] + stats["p_away_win_strict"])
        if (stats["p_home_win"] + stats["p_away_win_strict"]) > 0
        else None
    )
    return {
        "game_id": req.game_id,
        "projection": projection,
        "markets": markets,
        "margin_mu": margin_mu,
        "total_mu": total_mu,
        "sigma": float(projection["independent_fair"]["sigma"]),
        "market_blend": projection["independent_fair"]["market_blend"],
        "home": draws["home"],
        "away": draws["away"],
        "stats": stats,
        "capture": capture,
        "home_wp": markets["home_win_prob"],
        "away_wp": markets["away_win_prob"],
        "spread_home": markets["spread_home"],
        "total_mean_markets": markets["total_mean"],
        "fair_home_ml": markets["fair_home_ml"],
        "fair_away_ml": markets["fair_away_ml"],
        "p_home_win": stats["p_home_win"],
        "p_away_win_strict": stats["p_away_win_strict"],
        "p_tie": stats["p_tie"],
        "tie_excluded_p": p_home_ex,
        "tie_excluded_ml": fair_ml(p_home_ex) if p_home_ex is not None else None,
        "engine_tie_convention": "ties→away; ≠NFL truth ≠market settlement",
    }


def _row(name: str, value: Any, recompute: Any, delta: float, tol: float, cls: str) -> Dict[str, Any]:
    passed = abs(float(delta)) <= float(tol)
    return {
        "id": name,
        "value": value,
        "recompute": recompute,
        "delta": delta,
        "tol": tol,
        "class": cls,
        "band": "PASS" if passed else "FAIL",
    }


def table_a(game: Mapping[str, Any]) -> List[Dict[str, Any]]:
    st = game["stats"]
    cap = game["capture"]
    rows = []
    rows.append(
        _row(
            "J1",
            game["spread_home"],
            -st["mean_D"],
            float(game["spread_home"]) - (-st["mean_D"]),
            0.005,
            "A",
        )
    )
    rows.append(
        _row(
            "J2",
            game["total_mu"],
            st["mean_S"],
            float(game["total_mu"]) - st["mean_S"],
            0.005,
            "A",
        )
    )
    p_home_4 = round(st["p_home_win"], 4)
    rows.append(
        _row(
            "J3",
            game["home_wp"],
            p_home_4,
            float(game["home_wp"]) - p_home_4,
            0.0,
            "A",
        )
    )
    j3 = rows[-1]
    if float(game["home_wp"]) != p_home_4:
        j3["band"] = "FAIL"
    rows.append(
        _row(
            "J4",
            game["away_wp"],
            1.0 - float(game["home_wp"]),
            float(game["away_wp"]) - (1.0 - float(game["home_wp"])),
            1e-4,
            "A",
        )
    )
    away_from_parts = st["p_away_win_strict"] + st["p_tie"]
    if not math.isclose(float(game["away_wp"]), round(away_from_parts, 4), abs_tol=1e-4):
        rows[-1]["band"] = "FAIL"
        rows[-1]["note"] = "away_wp != p_away_win_strict + p_tie (4dp)"
    ml_h = fair_ml(st["p_home_win"])
    ml_a = fair_ml(1.0 - st["p_home_win"])
    j5_ok = int(game["fair_home_ml"]) == ml_h and int(game["fair_away_ml"]) == ml_a
    rows.append(
        {
            "id": "J5",
            "value": [game["fair_home_ml"], game["fair_away_ml"]],
            "recompute": [ml_h, ml_a],
            "delta": 0 if j5_ok else 1,
            "tol": 0,
            "class": "A",
            "band": "PASS" if j5_ok else "FAIL",
        }
    )
    d_id = abs((st["mean_H"] - st["mean_A"]) - st["mean_D"])
    s_id = abs((st["mean_H"] + st["mean_A"]) - st["mean_S"])
    rows.append(
        _row("J6", st["mean_H"] + st["mean_A"], st["mean_S"], max(d_id, s_id), 1e-9, "A")
    )
    tie_id_ok = st["n_home_wins"] + st["n_away_strict"] + st["n_ties"] == cap["N"]
    rows.append(
        {
            "id": "tie_identity",
            "value": st["n_home_wins"] + st["n_away_strict"] + st["n_ties"],
            "recompute": cap["N"],
            "delta": 0 if tie_id_ok else 1,
            "tol": 0,
            "class": "A",
            "band": "PASS" if tie_id_ok else "FAIL",
        }
    )
    home_ok = math.isclose(float(game["home_wp"]), round(st["p_home_win"], 4), abs_tol=0.0)
    if not home_ok:
        rows.append(
            {
                "id": "tie_wp_home",
                "value": game["home_wp"],
                "recompute": round(st["p_home_win"], 4),
                "delta": 1,
                "tol": 0,
                "class": "A",
                "band": "FAIL",
            }
        )
    return rows


def table_b(game: Mapping[str, Any], *, p_model: float) -> List[Dict[str, Any]]:
    st = game["stats"]
    cap = game["capture"]
    e_d = truncated_pos_mean(cap["mu_h"], cap["sigma"]) - truncated_pos_mean(
        cap["mu_a"], cap["sigma"]
    )
    e_s = truncated_pos_mean(cap["mu_h"], cap["sigma"]) + truncated_pos_mean(
        cap["mu_a"], cap["sigma"]
    )
    z_d = abs(st["mean_D"] - e_d) / st["SE_D"] if st["SE_D"] > 0 else 0.0
    z_s = abs(st["mean_S"] - e_s) / (st["sd_S"] / math.sqrt(st["n"])) if st["sd_S"] > 0 else 0.0
    var_exp = truncated_pos_var(cap["mu_h"], cap["sigma"]) + truncated_pos_var(
        cap["mu_a"], cap["sigma"]
    )
    sd_exp = math.sqrt(var_exp)
    rel = abs(st["sd_D"] - sd_exp) / sd_exp if sd_exp > 0 else 0.0
    delta_p = abs(st["p_home_win"] - p_model)
    abs_rho = abs(st["corr_HA"])
    m = st["mean_D"]
    p_hat = float(game["home_wp"])
    decisive = abs(m) >= max(0.25, 2.0 * st["SE_D"]) and abs(p_hat - 0.5) >= 2.0 * st["SE_p"]
    if decisive:
        j11 = "PASS" if (m > 0) == (p_hat - 0.5 > 0) else "FAIL"
        j11_note = "decisive"
    else:
        j11 = "NOT_DECISIVE"
        j11_note = "pick'em / inside noise — COND-neutral"
    return [
        {
            "id": "J7",
            "observed": st["mean_D"],
            "expected": e_d,
            "SE": st["SE_D"],
            "z": z_d,
            "band": j7_band(z_d),
            "class": "B",
        },
        {
            "id": "J7_S",
            "observed": st["mean_S"],
            "expected": e_s,
            "SE": st["sd_S"] / math.sqrt(st["n"]),
            "z": z_s,
            "band": j7_band(z_s),
            "class": "B",
        },
        {
            "id": "J8",
            "observed": st["sd_D"],
            "expected": sd_exp,
            "SE": None,
            "z": rel,
            "band": j8_band(rel),
            "class": "B",
            "rel": rel,
        },
        {
            "id": "J9",
            "observed": st["p_home_win"],
            "expected": p_model,
            "SE": st["SE_p"],
            "z": delta_p / st["SE_p"] if st["SE_p"] > 0 else 0.0,
            "band": j9_band(delta_p, st["SE_p"]),
            "class": "B",
            "delta": delta_p,
        },
        {
            "id": "J10",
            "observed": st["corr_HA"],
            "expected": 0.0,
            "SE": None,
            "z": abs_rho,
            "band": j10_band(abs_rho),
            "class": "B",
        },
        {
            "id": "J11",
            "observed": {"m": m, "p": p_hat},
            "expected": "sign(m)==sign(p-0.5) in decisive zone",
            "SE": {"SE_D": st["SE_D"], "SE_p": st["SE_p"]},
            "z": None,
            "band": j11,
            "class": "B",
            "note": j11_note,
        },
        {
            "id": "tie_rate",
            "observed": st["p_tie"],
            "expected": "≤1e-3 PASS",
            "SE": None,
            "z": st["p_tie"],
            "band": tie_rate_band(st["p_tie"]),
            "class": "B",
        },
    ]


def j12_across(games: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    ms = [g["stats"]["mean_D"] for g in games]
    ps = [float(g["home_wp"]) for g in games]
    ses = [g["stats"]["SE_D"] for g in games]
    inversions = []
    conc = disc = 0
    n = len(games)
    for i in range(n):
        for j in range(i + 1, n):
            dm = ms[i] - ms[j]
            dp = ps[i] - ps[j]
            prod = dm * dp
            if prod > 0:
                conc += 1
            elif prod < 0:
                disc += 1
                thresh = max(0.5, 2.0 * math.sqrt(ses[i] ** 2 + ses[j] ** 2))
                if abs(dm) > thresh:
                    inversions.append(
                        {
                            "i": games[i]["game_id"],
                            "j": games[j]["game_id"],
                            "dm": dm,
                            "dp": dp,
                            "thresh": thresh,
                        }
                    )
    denom = n * (n - 1) / 2.0
    tau = (conc - disc) / denom if denom else 0.0
    if inversions:
        band = "FAIL"
    elif tau >= 0.95:
        band = "PASS"
    else:
        band = "COND"
    return {
        "id": "J12",
        "kendall_tau": tau,
        "inversions": inversions,
        "band": band,
        "class": "B",
    }


def j13_reproduce(game: Mapping[str, Any], req: Any) -> Dict[str, Any]:
    again = invoke_with_capture(req)
    match = again["capture"]["draw_array_sha256"] == game["capture"]["draw_array_sha256"]
    return {
        "id": "J13",
        "value": game["capture"]["draw_array_sha256"],
        "recompute": again["capture"]["draw_array_sha256"],
        "delta": 0 if match else 1,
        "tol": 0,
        "class": "A",
        "band": "PASS" if match else "FAIL",
    }


def scan_ats_ou(payload: Any, hits: List[str] | None = None, path: str = "") -> List[str]:
    hits = hits if hits is not None else []
    if isinstance(payload, Mapping):
        for key, val in payload.items():
            key_l = str(key).lower()
            here = f"{path}.{key}" if path else str(key)
            parts = set(key_l.replace("-", "_").split("_"))
            if val is not None and (
                key_l in ATS_OU_EXACT or "ats" in parts or ({"ou"} & parts)
            ):
                hits.append(here)
            scan_ats_ou(val, hits, here)
    elif isinstance(payload, list):
        for i, item in enumerate(payload):
            scan_ats_ou(item, hits, f"{path}[{i}]")
    return hits


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=REPO_ROOT, text=True, stderr=subprocess.STDOUT
    ).strip()


def require_clean_for_write() -> str:
    head = _git("rev-parse", "HEAD")
    dirty = _git("diff", "--name-only", "HEAD", "--", *SOURCE_GUARD)
    if dirty:
        raise EvalW8Reject("EXECUTION_TIP_DIRTY", f"dirty vs {head[:8]}: {dirty}")
    if sha256_file(REPO_ROOT / SOURCE_GUARD[2]) != IF_SOURCE_PIN_SHA256:
        raise EvalW8Reject("SOURCE_PIN", "nfl_simulator.py must remain 52d9e909")
    return head


def verdict_from_tables(
    games: Sequence[Mapping[str, Any]],
    j12: Mapping[str, Any],
    j14: Mapping[str, Any],
    contract_ok: bool,
) -> Dict[str, Any]:
    a_fail = []
    b_fail = []
    b_cond = []
    for game in games:
        for row in game["table_a"]:
            if row["band"] == "FAIL":
                a_fail.append(f"{game['game_id']}:{row['id']}")
        if game["j13"]["band"] == "FAIL":
            a_fail.append(f"{game['game_id']}:J13")
        for row in game["table_b"]:
            if row["band"] == "FAIL":
                b_fail.append(f"{game['game_id']}:{row['id']}")
            elif row["band"] == "COND":
                b_cond.append(f"{game['game_id']}:{row['id']}")
    if j12["band"] == "FAIL":
        b_fail.append("J12")
    elif j12["band"] == "COND":
        b_cond.append("J12")
    if j14["band"] == "FAIL":
        a_fail.append("J14")
    if not contract_ok or a_fail or b_fail:
        verdict = "BLOCKED"
        label = "BLOCKED(#4 IF-only; A FAIL or B FAIL or contract missing)"
    elif b_cond:
        verdict = "CONDITIONAL"
        label = (
            "CONDITIONAL(#4 IF-only; scope: spread/total/wp/ML; "
            "ATS/OU NOT EMITTED, NOT TESTED)"
        )
    else:
        verdict = "PASS_RO"
        label = (
            "PASS_RO(#4 IF-only; scope: spread/total/wp/ML; "
            "ATS/OU NOT EMITTED, NOT TESTED)"
        )
    return {
        "verdict": verdict,
        "label": label,
        "a_fail": a_fail,
        "b_fail": b_fail,
        "b_cond": b_cond,
        "j11_not_decisive": [
            g["game_id"]
            for g in games
            if any(r["id"] == "J11" and r["band"] == "NOT_DECISIVE" for r in g["table_b"])
        ],
        "scope": "IF-only internal consistency only; ≠calibration ≠accuracy ≠market ≠enterprise",
    }


def eval_request_at_seed(game_id: str, seed: int) -> Any:
    """Build the frozen-slate request for game_id, then replace seed only."""
    if game_id not in SUPPORTED_GAMES:
        raise EvalW8Reject("GAME", f"{game_id} not on the 13-game diagnostic slate")
    panel = load_panel()
    schedule = load_schedule()
    history = history_w1_w7(schedule)
    by_id = {str(g["game_id"]): g for g in schedule.get("games") or []}
    req, _elig = build_eval_request(
        game_id=game_id,
        schedule_game=by_id[game_id],
        panel=panel,
        history=history,
    )
    return replace(req, seed=int(seed))


def inject_published_wp(game: Mapping[str, Any], home_wp: float) -> Dict[str, Any]:
    """C2: overlay a foreign home_wp on the same-draw game and re-run Table A.

    Draws/stats/capture stay on the original array. Only published wp is swapped.
    The checker must FAIL J3 when the injected wp is not the same-draw p_home.
    """
    tampered = copy.deepcopy(dict(game))
    tampered["home_wp"] = float(home_wp)
    tampered["away_wp"] = round(1.0 - float(home_wp), 4)
    rows = table_a(tampered)
    tampered["table_a"] = rows
    j3 = next(r for r in rows if r["id"] == "J3")
    return {
        "game": tampered,
        "table_a": rows,
        "j3": j3,
        "drives_fail": j3["band"] == "FAIL",
        "injected_home_wp": float(home_wp),
        "original_home_wp": float(game["home_wp"]),
        "same_draw_sha256": game["capture"]["draw_array_sha256"],
    }


def second_seed_injection(game: Mapping[str, Any]) -> Dict[str, Any]:
    """Invoke the same game at a predeclared non-packet seed and inject that wp."""
    seeds = (SECOND_SEED_C2, *SECOND_SEED_C2_FALLBACKS)
    foreign = None
    used_seed = None
    for seed in seeds:
        cand = invoke_with_capture(eval_request_at_seed(str(game["game_id"]), seed))
        if float(cand["home_wp"]) != float(game["home_wp"]):
            foreign = cand
            used_seed = seed
            break
    if foreign is None:
        raise EvalW8Reject(
            "C2_SEED_COLLISION",
            f"all C2 seeds {seeds} matched published wp {game['home_wp']}",
        )
    injected = inject_published_wp(game, float(foreign["home_wp"]))
    injected["second_seed"] = used_seed
    injected["second_seed_draw_sha256"] = foreign["capture"]["draw_array_sha256"]
    injected["second_seed_home_wp"] = float(foreign["home_wp"])
    return injected


def inject_published_st_ml(
    game: Mapping[str, Any],
    *,
    spread_home: float | None = None,
    total_mu: float | None = None,
    fair_home_ml: int | None = None,
    fair_away_ml: int | None = None,
) -> Dict[str, Any]:
    """C2 joint ST+ML: overlay foreign published spread/total/ML on the same-draw game.

    Frozen J1/J2/J5 already require those fields to come from the captured array.
    A second-seed overlay must fail-closed (A FAIL → BLOCKED). No new tolerance.
    """
    tampered = copy.deepcopy(dict(game))
    if spread_home is not None:
        tampered["spread_home"] = float(spread_home)
    if total_mu is not None:
        tampered["total_mu"] = float(total_mu)
    if fair_home_ml is not None:
        tampered["fair_home_ml"] = int(fair_home_ml)
    if fair_away_ml is not None:
        tampered["fair_away_ml"] = int(fair_away_ml)
    rows = table_a(tampered)
    tampered["table_a"] = rows
    by_id = {r["id"]: r for r in rows}
    return {
        "game": tampered,
        "table_a": rows,
        "j1": by_id["J1"],
        "j2": by_id["J2"],
        "j5": by_id["J5"],
        "drives_fail": any(by_id[k]["band"] == "FAIL" for k in ("J1", "J2", "J5")),
        "same_draw_sha256": game["capture"]["draw_array_sha256"],
    }


def second_seed_st_ml_injection(game: Mapping[str, Any]) -> Dict[str, Any]:
    """Same game, predeclared non-packet seed; inject that seed's ST+ML onto draw-1."""
    seeds = (SECOND_SEED_C2, *SECOND_SEED_C2_FALLBACKS)
    foreign = None
    used_seed = None
    for seed in seeds:
        cand = invoke_with_capture(eval_request_at_seed(str(game["game_id"]), seed))
        st_diff = float(cand["spread_home"]) != float(game["spread_home"])
        ml_diff = int(cand["fair_home_ml"]) != int(game["fair_home_ml"])
        if st_diff and ml_diff:
            foreign = cand
            used_seed = seed
            break
    if foreign is None:
        raise EvalW8Reject(
            "C2_ST_ML_COLLISION",
            f"all C2 seeds {seeds} matched published ST or ML for {game['game_id']}",
        )
    injected = inject_published_st_ml(
        game,
        spread_home=float(foreign["spread_home"]),
        total_mu=float(foreign["total_mu"]),
        fair_home_ml=int(foreign["fair_home_ml"]),
        fair_away_ml=int(foreign["fair_away_ml"]),
    )
    injected["second_seed"] = used_seed
    injected["second_seed_draw_sha256"] = foreign["capture"]["draw_array_sha256"]
    injected["second_seed_spread_home"] = float(foreign["spread_home"])
    injected["second_seed_total_mu"] = float(foreign["total_mu"])
    injected["second_seed_fair_home_ml"] = int(foreign["fair_home_ml"])
    return injected


def _assert_parent_packet_untouched() -> None:
    sums = PARENT_PACKET_DIR / "SHA256SUMS"
    if not sums.is_file():
        raise EvalW8Reject("PARENT_PACKET", "parent Card A SHA256SUMS missing")
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        if sha256_file(PARENT_PACKET_DIR / rel) != digest:
            raise EvalW8Reject("PARENT_PACKET", f"parent {rel} mutated")


def write_pytest_evidence(dest: Path) -> Dict[str, Any]:
    """C3: run the IF pytest suite and seal stdout as packet evidence."""
    dest.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pytest", "-q", "--tb=short", *PYTEST_FILES]
    env = dict(os.environ)
    ms = str(REPO_ROOT / "services" / "model-service")
    env["PYTHONPATH"] = ms + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    started = datetime.now(timezone.utc)
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    ended = datetime.now(timezone.utc)
    log = proc.stdout or ""
    # PYTEST.txt (not .log) — repo gitignore is *.log; C3 evidence must be commitable.
    (dest / "PYTEST.txt").write_text(log, encoding="utf-8")
    summary = {
        "cmd": " ".join(cmd),
        "exit_code": proc.returncode,
        "passed": proc.returncode == 0,
        "started_utc": started.isoformat(),
        "ended_utc": ended.isoformat(),
        "files": list(PYTEST_FILES),
        "note": "C3 pytest/CI evidence. Does not change #4 verdict. ≠PASS_RO claim.",
    }
    (dest / "PYTEST.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise EvalW8Reject("PYTEST", f"pytest exit {proc.returncode}\n{log[-2000:]}")
    return summary


def run_coherence_slate(*, write: bool = False) -> Dict[str, Any]:
    execution_tip = require_clean_for_write() if write else _git("rev-parse", "HEAD")
    run_id = (
        f"eval-w8-t4871u-coh-"
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-"
        f"{uuid4().hex[:8]}"
    )
    audit = CallAudit()
    panel = load_panel()
    schedule = load_schedule()
    history = history_w1_w7(schedule)
    by_id = {str(g["game_id"]): g for g in schedule.get("games") or []}
    games: List[Dict[str, Any]] = []
    with audit:
        for game_id in SUPPORTED_GAMES:
            req, elig = build_eval_request(
                game_id=game_id,
                schedule_game=by_id[game_id],
                panel=panel,
                history=history,
            )
            if req.simulations != N_PACKET:
                raise EvalW8Reject("FROZEN_N", f"{req.simulations} != {N_PACKET}")
            if req.seed != SEED_BASE + SUPPORTED_GAMES.index(game_id):
                raise EvalW8Reject("FROZEN_SEED", f"seed {req.seed} not frozen slate seed")
            game = invoke_with_capture(req)
            game["eligibility"] = elig
            p_model = p_model_home_win(
                game["capture"]["mu_h"], game["capture"]["mu_a"], game["capture"]["sigma"]
            )
            game["p_model_home_win"] = p_model
            game["table_a"] = table_a(game)
            game["table_b"] = table_b(game, p_model=p_model)
            game["j13"] = j13_reproduce(game, req)
            # drop raw arrays from packet payload (hash-bound; regen via seed)
            game_out = {k: v for k, v in game.items() if k not in {"home", "away", "projection"}}
            games.append(game_out)
    if audit.forbidden_hits:
        raise EvalW8Reject("FORBIDDEN_CALL", str(audit.forbidden_hits))
    j12 = j12_across(games)
    slim_results = []
    for game in games:
        slim_results.append(
            {
                "game_id": game["game_id"],
                "home_wp": game["home_wp"],
                "away_wp": game["away_wp"],
                "spread_home": game["spread_home"],
                "total_mu": game["total_mu"],
                "total_mean_markets": game["total_mean_markets"],
                "fair_home_ml": game["fair_home_ml"],
                "fair_away_ml": game["fair_away_ml"],
                "p_home_win": game["p_home_win"],
                "p_away_win_strict": game["p_away_win_strict"],
                "p_tie": game["p_tie"],
                "tie_excluded_p": game["tie_excluded_p"],
                "tie_excluded_ml": game["tie_excluded_ml"],
                "market_blend": game["market_blend"],
                "public_delivery": False,
                "e1_admissible": False,
            }
        )
    ats_hits = scan_ats_ou({"results": slim_results, "games": games})
    if ats_hits:
        j14 = {
            "id": "J14",
            "band": "FAIL",
            "class": "A",
            "detail": f"ATS/OU emitted: {ats_hits}",
        }
    else:
        j14 = {
            "id": "J14",
            "band": "NOT_APPLICABLE_NOT_EMITTED",
            "class": "A",
            "detail": "test_no_ats_ou_emitted: no ATS/OU/push fields present",
        }
    caller = evaluate_caller(write=False)
    contract = {
        "execution_tip": execution_tip,
        "source_pin": IF_SOURCE_PIN_SHA256,
        "simulator_sha256": sha256_file(REPO_ROOT / SOURCE_GUARD[2]),
        "panel_sha256": PANEL_SHA256,
        "through_w7_accept_sha256": THROUGH_W7_ACCEPT_SHA256,
        "schedule_sha256": SCHEDULE_SHA256,
        "clarification_sha256": CLARIFICATION_SHA256,
        "parent_paper_sha256": PARENT_PAPER_SHA256,
        "N": N_PACKET,
        "seed_base": SEED_BASE,
        "j9_mc_n": J9_MC_N,
        "j9_mc_seed": J9_MC_SEED,
        "no_rerun_until_pass": True,
        "blend_zero": all(g["market_blend"] == 0 for g in games),
        "public_delivery": False,
        "tnf_excluded": TNF_GAME_ID,
        "through_w7": THROUGH_W7_ACCEPT,
        "baseline_v2_tip": V2_PACKET_TIP,
        "operational_blocked": caller.status == "BLOCKED" and REJECT_THROUGH_W8 in caller.codes,
        "capture_complete": all(
            g["capture"].get("mu_h") is not None
            and g["capture"].get("draw_array_sha256")
            and g["capture"]["used_reconstructed_means_for_acceptance"] is False
            for g in games
        ),
        "j14_proof": j14["band"] == "NOT_APPLICABLE_NOT_EMITTED",
        "call_audit_passed": audit.report()["passed"],
    }
    contract_ok = all(
        [
            contract["blend_zero"],
            contract["capture_complete"],
            contract["j14_proof"],
            contract["operational_blocked"],
            contract["call_audit_passed"],
            contract["no_rerun_until_pass"],
            contract["simulator_sha256"] == IF_SOURCE_PIN_SHA256,
            contract["panel_sha256"] == PANEL_SHA256,
            contract["schedule_sha256"] == SCHEDULE_SHA256,
        ]
    )
    mapped = verdict_from_tables(games, j12, j14, contract_ok)
    # keep raw arrays out; already stripped
    manifest = {
        "run_id": run_id,
        "label": "DIAGNOSTIC / EVAL_ONLY / IF-only coherence",
        "cmd": CMD,
        "execution_tip": execution_tip,
        "execution_tip_short": execution_tip[:8],
        "invoke_head": execution_tip,
        "invoke_head_matches_execution_tip": True,
        "clarification_sha256": CLARIFICATION_SHA256,
        "parent_paper_sha256": PARENT_PAPER_SHA256,
        "owner_clear": OWNER_CLEAR,
        "public_delivery": False,
        "e1_admissible": False,
        "scoring_admissible_now": False,
        "frozen": {
            "N": N_PACKET,
            "seed_base": SEED_BASE,
            "seeds": [SEED_BASE + i for i in range(len(SUPPORTED_GAMES))],
            "j9_mc_n": J9_MC_N,
            "j9_mc_seed": J9_MC_SEED,
            "tolerances": "ALEX_IF_COHERENCE_SPEC_CLARIFICATION_t4871u_v1 sha fe4dc220",
            "no_rerun_until_pass": True,
        },
        "baseline": {
            "packet": "eval_w8_t4850u_v2",
            "packet_tip": V2_PACKET_TIP,
            "coherence_parent": "eval_w8_t4871u_coherence",
            "coherence_parent_tip": PARENT_PACKET_TIP,
            "coherence_parent_seal": PARENT_PACKET_SEAL,
            "alex_ro_card_a": ALEX_RO_CARD_A,
            "note": (
                "Sibling v2 of Card A packet. Parent 1f4ffde3 / tip aa9605dc left sealed. "
                "v3 90bf65ab documented ST/total/ML/wp identical to eval v2; "
                "this run invokes current HEAD for gauss capture. blend=0. "
                "C2/C3 soft notes only. #4 remains CONDITIONAL."
            ),
        },
        "config": {
            "if_blend": 0,
            "rating_week": 7,
            "through_w7": THROUGH_W7_ACCEPT,
            "odds": False,
            "c10": False,
            "railway": False,
            "hl": False,
        },
    }
    packet = {
        "status": mapped["verdict"],
        "verdict": mapped["verdict"],
        "verdict_label": mapped["label"],
        "scope": mapped["scope"],
        "run_id": run_id,
        "execution_tip": execution_tip,
        "n_games": len(games),
        "tnf_excluded": TNF_GAME_ID,
        "e1_admissible": False,
        "public_delivery": False,
        "j14": j14,
        "j12": {k: v for k, v in j12.items() if k != "inversions" or v},
        "a_fail": mapped["a_fail"],
        "b_fail": mapped["b_fail"],
        "b_cond": mapped["b_cond"],
        "j11_not_decisive": mapped["j11_not_decisive"],
    }
    out = {
        "manifest": manifest,
        "packet": packet,
        "games": games,
        "results": slim_results,
        "j12": j12,
        "j14": j14,
        "contract": contract,
        "call_audit": audit.report(),
        "verdict": mapped,
    }
    if write:
        _write_packet(out)
    return out


def _write_packet(artifacts: Mapping[str, Any]) -> None:
    PACKET_DIR.mkdir(parents=True, exist_ok=True)
    dest = PACKET_DIR / "inputs"
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("team_efficiency_current_through_w7.json", "ACCEPT.json"):
        dest.joinpath(name).write_bytes((V2_DIR / "inputs" / name).read_bytes())
    mapping = {
        "MANIFEST.json": artifacts["manifest"],
        "DIAGNOSTIC_PACKET.json": artifacts["packet"],
        "RESULTS.json": artifacts["results"],
        "GAMES.json": artifacts["games"],
        "J12.json": artifacts["j12"],
        "J14.json": artifacts["j14"],
        "CONTRACT.json": artifacts["contract"],
        "CALL_AUDIT.json": artifacts["call_audit"],
        "VERDICT.json": artifacts["verdict"],
        "FROZEN_CONFIG.json": artifacts["manifest"]["frozen"],
    }
    for name, payload in mapping.items():
        (PACKET_DIR / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
    (PACKET_DIR / "TABLES.md").write_text(_render_tables_md(artifacts), encoding="utf-8")
    (PACKET_DIR / "DIAGNOSTIC_PACKET.md").write_text(
        _render_packet_md(artifacts), encoding="utf-8"
    )
    (PACKET_DIR / "COS_NOTE.md").write_text(_render_cos_note(artifacts), encoding="utf-8")
    (PACKET_DIR / "C2_C3.md").write_text(_render_c2_c3_note(), encoding="utf-8")
    _assert_parent_packet_untouched()
    write_pytest_evidence(PACKET_DIR)
    lines = []
    for path in sorted(PACKET_DIR.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            rel = path.relative_to(PACKET_DIR).as_posix()
            lines.append(f"{sha256_file(path)}  {rel}")
    (PACKET_DIR / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _render_packet_md(artifacts: Mapping[str, Any]) -> str:
    p = artifacts["packet"]
    m = artifacts["manifest"]
    return "\n".join(
        [
            "# DIAGNOSTIC PACKET t4871u — IF-only coherence",
            "",
            f"**Verdict:** `{p['verdict']}`",
            f"**Label:** {p['verdict_label']}",
            f"**execution_tip:** `{m['execution_tip']}`",
            f"**clarification:** `{CLARIFICATION_SHA256}`",
            f"**cmd:** `{CMD}`",
            f"**public_delivery:** false · **e1_admissible:** false · blend=0",
            "",
            "PASS (if any) = IF-only internal consistency only.",
            "≠FREE_PUBLIC ≠BETTING ≠E1 ≠merge. NFL NO-GO · CERT=0.",
            "",
        ]
    )


def _render_cos_note(artifacts: Mapping[str, Any]) -> str:
    p = artifacts["packet"]
    m = artifacts["manifest"]
    v = artifacts["verdict"]
    return "\n".join(
        [
            "# CoS note t4871u Card A",
            "",
            f"- tip `{m['execution_tip']}`",
            f"- path `data/ops/nfl-offline-if-caller-t4838u/eval_w8_t4871u_coherence_v2/`",
            f"- parent packet tip `{PARENT_PACKET_TIP}` seal `{PARENT_PACKET_SEAL}` Alex RO `{ALEX_RO_CARD_A}`",
            "- C2: second-seed wp injection now drives Table A J3 → FAIL / packet BLOCKED",
            "- C3: PYTEST.txt + PYTEST.json sealed in this packet",
            "- #4 remains CONDITIONAL; PASS_RO not claimed",
            f"- verdict `{p['verdict']}` · {p['verdict_label']}",
            f"- A FAIL: {v['a_fail'] or 'none'}",
            f"- B FAIL: {v['b_fail'] or 'none'}",
            f"- B COND: {v['b_cond'] or 'none'}",
            f"- J11 NOT_DECISIVE: {v['j11_not_decisive']}",
            "- no forecast math change · no tolerance retune · SOURCE ONLY 52d9e909 unedited",
            "",
        ]
    )


def _render_tables_md(artifacts: Mapping[str, Any]) -> str:
    lines = ["# Table A / B t4871u", ""]
    for game in artifacts["games"]:
        lines.append(f"## {game['game_id']}")
        lines.append("")
        lines.append("### A (deterministic)")
        lines.append("| id | band | delta |")
        lines.append("|---|---|---:|")
        for row in game["table_a"] + [game["j13"]]:
            lines.append(f"| {row['id']} | {row['band']} | {row.get('delta')} |")
        lines.append("")
        lines.append("### B (sampling)")
        lines.append("| id | band | z |")
        lines.append("|---|---|---:|")
        for row in game["table_b"]:
            lines.append(f"| {row['id']} | {row['band']} | {row.get('z')} |")
        lines.append("")
    lines.append("## J12")
    lines.append(f"band `{artifacts['j12']['band']}` τ={artifacts['j12']['kendall_tau']}")
    lines.append("")
    lines.append("## J14")
    lines.append(f"{artifacts['j14']}")
    lines.append("")
    return "\n".join(lines)


def _render_c2_c3_note() -> str:
    return "\n".join(
        [
            "# C2 / C3 soft notes (t4890u)",
            "",
            "Parent Card A packet `eval_w8_t4871u_coherence/` tip `aa9605dc` seal `1f4ffde3` Alex RO `b5de5df1`.",
            "This sibling does not rewrite that packet. #4 remains CONDITIONAL. ≠PASS_RO.",
            "",
            "## C2 — second-seed wp and joint ST+ML injection drive FAIL",
            "",
            "Frozen contract (fe4dc220 §6): same-draw J1/J2/J5; different draw sets → BLOCKED.",
            "No new tolerance. Expected fail-closed of existing checkers:",
            "",
            "- `inject_published_wp` / `test_16`: foreign home_wp → J3 FAIL → BLOCKED.",
            "- `inject_published_st_ml` / `test_c2_joint_st_ml_fail_closed`: foreign",
            "  spread_home + total_mu + fair ML from `SECOND_SEED_C2` onto draw-1 stats →",
            "  J1/J2/J5 FAIL → BLOCKED. Same-draw overlay still PASSes.",
            "",
            "This documents expected fail-closed, not a spec change.",
            "",
            "## C3 — pytest / CI evidence in the packet",
            "",
            "`PYTEST.txt` and `PYTEST.json` are written by `--write-packet` before SHA256SUMS.",
            "Command is the IF caller/eval/coherence suite. Exit 0 required to seal.",
            "Evidence of tests ≠ #4 PASS.",
            "",
            "No forecast math change. No tolerance retune. NFL NO-GO · CERT=0.",
            "",
        ]
    )
