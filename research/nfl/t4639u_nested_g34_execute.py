#!/usr/bin/env python3
"""t4639u Nested chronological G34 EXECUTE (CERT=0).

Authority
  DECISION_RYAN_t4639u CLEAR Nested G34 EXEC ONLY   sha8 c51b4280
  COS_ORDER_CURSOR_t4639u                           sha8 5b8d2482
  Protocol ALEX_NESTED_G34_PROTOCOL_t4634u_v2       sha8 59161fbb (UNCHANGED; do not edit)
  IMV PASS_PROTOCOL                                 sha8 1fc4d103
  Parent DECISION                                   sha8 1cf303e3

Runs EXACTLY protocol 59161fbb. Phases:
  freeze — derive ≤2023 inputs, B1/B2/alt select, seal F (all 12 §6 fields)
  score  — P_score + supportive metrics AFTER F paper exists

Does NOT: edit protocol, Odds, merge, F2, deploy, publish, CERT, redesign,
holdout/2024+ outcome read, Lane A reclass, Exp A/D-R reopen, LOCKED_SCORING.

NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · #648 DRAFT.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MS_SRC = ROOT / "services" / "model-service"
if str(MS_SRC) not in sys.path:
    sys.path.insert(0, str(MS_SRC))
_USER_SITE = Path.home() / ".local/lib/python3.12/site-packages"
if _USER_SITE.is_dir() and str(_USER_SITE) not in sys.path:
    sys.path.insert(0, str(_USER_SITE))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from t4602u_exp_a_ridge_joint import (  # noqa: E402
    ESTIMATOR_ID,
    N0_BASE,
    RidgeParams,
    fit_beta_fold,
    hc1_ci,
    ols_hc1,
    predict_margin_a,
    select_cell,
)

import t4602u_exp_a_execute as exp_a  # noqa: E402

TICKET = "t4639u"
LABEL = "RESEARCH_DIAGNOSTIC_NESTED_G34"
CERT_CANDIDATE = 0
FILE_MODE = 0o444
BOOT_B = 10000
BOOT_SEED = 4141
EPS = 1e-9

DECISION_SHA8 = "c51b4280"
COS_ORDER_SHA8 = "5b8d2482"
PROTOCOL_SHA256 = "59161fbb462eb04ab68810e4de56bef4b4ff36508a3ba742b6316b4376767c30"
PROTOCOL_SHA8 = "59161fbb"
IMV_PASS_SHA8 = "1fc4d103"
PARENT_DECISION_SHA8 = "1cf303e3"
ESTIMATOR_ADDENDUM_SHA8 = "84a28a05"
H2_SHA256 = "db2cf4b24bfa9c441f7eafea19d5c24624541f9cb7225759e9882f61cb6c6463"
EMIT_SHA256 = "02f6b2e2baa425cab7703dd1d3d5064fc0dabfc69e330a846e54d736c49430a2"
ROLLING_SHA256 = "1b07654ea500535ff445e0f3c20acc26a6c3006857951562755e406adff52479"
OOS_SHA256 = "1ee90facf7d44dfd19758cbf89d5518417cbc1fba6faec4e76fb33d8532adaed"
GAMES_SHA256 = "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8"

REF_CELL_ID = "G27"
REF_PARAMS = {"cfg_id": "G27", "rho": 0.95, "lambda": 1.0, "rho_s": 0.67, "hfa_mode": "off", "n0": 4.0}

H2_PATH = HERE / "t4586u_exp_a_h2_manifest_freeze" / "CURSOR_EXP_A_H2_GRID_FOLD_MANIFEST_t4598u_v1.json"
OOS_SRC = HERE / "t4586u_exp_e_inputs" / "historical_oos_games.csv"
GAMES_PATH = HERE / "t4586u_exp_e_inputs" / "games.csv"
CACHE_DIR = Path(os.environ.get("T4639U_CACHE", "/tmp/nflverse-pbp-exp-e"))
OUT_DIR = HERE / "t4639u_nested_g34"

METRIC_DEFS = {
    "MAE_model": "mean |m - margin_A| on P_score; primary",
    "ΔMAE_ref": "MAE_ref - MAE_model; ref = frozen ref_cell_id G27 (ρ=0.95 λ=1 ρ_s=0.67 HFA off); PRIMARY GATE; never vs best/any other cell",
    "ΔMAE_mkt": "MAE_mkt - MAE_model; MAE_mkt = mean |m - mm|; REPORT-ONLY NOTE; no beats-market PASS/claim path; expected sign < 0",
    "c": "OLS (m - mm) = c·(margin_A - mm) + e; intercept-free; HC1 diagnostic; REPORT-ONLY NOTE",
    "bias": "mean(m - margin_A); diagnostic",
    "binding_CI": "Paired game-level bootstrap of per-game Δ (|m−ref|−|m−model|) on B1 2019–2022 pooled, B=10000, seed 4141, percentile 95% CI — only CI that can PASS/FAIL",
    "season_block_CI": "season-block bootstrap; supportive sensitivity; report-only; cannot PASS/FAIL",
    "PASS_RESEARCH": "B1 pooled 2019–2022: ΔMAE_ref ≥ 0.10 vs frozen ref only AND binding CI excludes 0 AND invariants hold; winner==ref ⇒ FAIL_RESEARCH",
}

_FORBIDDEN = ("simulate_nfl_game", "LOCKED_SCORING", "config_overrides", "NflGameInputs")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha8(digest: str) -> str:
    return digest[:8]


def _git_tip() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def _write_readonly(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.chmod(0o644)
    data = text if text.endswith("\n") else text + "\n"
    path.write_text(data, encoding="utf-8")
    os.chmod(path, FILE_MODE)
    return _sha256_file(path)


def _write_json(path: Path, obj: Any) -> str:
    return _write_readonly(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.chmod(0o644)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fieldnames), extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})
    os.chmod(path, FILE_MODE)
    return _sha256_file(path)


def _write_sums(path: Path, items: Mapping[str, str]) -> str:
    lines = [f"{digest}  {name}\n" for name, digest in sorted(items.items())]
    return _write_readonly(path, "".join(lines))


def _assert_no_forbidden() -> None:
    for name in _FORBIDDEN:
        if name in sys.modules:
            raise RuntimeError(f"forbidden import present: {name}")


def _void(reason: str) -> None:
    raise RuntimeError(f"VOID: {reason}")


def count_ge2024_season_only(path: Path) -> int:
    """Count season≥2024 rows without reading outcome/margin/spread values."""
    n = 0
    with path.open(encoding="utf-8") as fh:
        header = fh.readline()
        cols = header.strip().split(",")
        if "season" not in cols:
            _void(f"no season column in {path}")
        idx = cols.index("season")
        for line in fh:
            parts = line.split(",")
            season = int(float(parts[idx]))
            if season >= 2024:
                n += 1
    return n


def derive_le2023(src: Path, dest: Path) -> Tuple[int, int, str]:
    """Write season≤2023 derivative. 2024+ counted via season column only."""
    n_ge = 0
    kept: List[str] = []
    with src.open(encoding="utf-8") as fh:
        header = fh.readline()
        cols = header.strip().split(",")
        idx = cols.index("season")
        for line in fh:
            season = int(float(line.split(",")[idx]))
            if season >= 2024:
                n_ge += 1
                continue
            kept.append(line)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.chmod(0o644)
    dest.write_text(header + "".join(kept), encoding="utf-8")
    os.chmod(dest, FILE_MODE)
    digest = _sha256_file(dest)
    n_keep = assert_no_ge2024(dest, "oos_le2023")
    return n_ge, n_keep, digest


def assert_no_ge2024(path: Path, label: str) -> int:
    n = 0
    with path.open(encoding="utf-8") as fh:
        header = fh.readline()
        cols = header.strip().split(",")
        idx = cols.index("season")
        for line in fh:
            season = int(float(line.split(",")[idx]))
            if season >= 2024:
                _void(f"{label} contains season≥2024 ({path})")
            n += 1
    return n


def assert_panel_no_ge2024(rows: Sequence[Mapping[str, Any]], label: str) -> None:
    n = sum(1 for r in rows if int(r["season"]) >= 2024)
    if n:
        _void(f"{label} panel has n_rows season≥2024={n}")


def _close_h1() -> None:
    exp_a._H1_CLOSED = True
    exp_a._H1_HASHES.clear()


def _extract_emit(dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    raw = subprocess.check_output(["git", "-C", str(ROOT), "show", exp_a.EMIT_GIT_REF])
    dest.write_bytes(raw)
    digest = _sha256_file(dest)
    if digest != EMIT_SHA256:
        _void(f"emit sha mismatch got={digest} want={EMIT_SHA256}")
    return digest


def _mae(pred: Sequence[float], actual: Sequence[float]) -> float:
    return float(sum(abs(p - a) for p, a in zip(pred, actual)) / max(len(pred), 1))


def _panel_csv_rows(panel: Sequence[Mapping[str, Any]], seasons: Sequence[int]) -> List[Dict[str, Any]]:
    want = set(int(s) for s in seasons)
    rows = []
    for g in panel:
        if int(g["season"]) not in want:
            continue
        rows.append(
            {
                "season": g["season"],
                "week": g["week"],
                "game_id": g["game_id"],
                "home": g["home"],
                "away": g["away"],
                "kickoff_utc": g["kickoff_utc"],
                "neutral": int(bool(g["neutral"])),
                "home_ind": g["home_ind"],
                "m": g["m"],
                "mm": g["mm"],
                "pm_epa": g["pm_epa"],
            }
        )
    rows.sort(key=lambda r: (int(r["season"]), int(r["week"]), r["game_id"]))
    return rows


def rating_cache(obs: Mapping[str, Any], panel: Sequence[Mapping[str, Any]], grid: Sequence[Mapping[str, Any]]) -> Dict[Tuple[float, float, float], Dict[str, float]]:
    keys = sorted({(float(c["rho"]), float(c["lambda"]), float(c["rho_s"])) for c in grid})
    cache: Dict[Tuple[float, float, float], Dict[str, float]] = {}
    for i, (rho, lam, rho_s) in enumerate(keys, 1):
        n0 = lam * N0_BASE
        print(f"[ratings] {i}/{len(keys)} rho={rho} lambda={lam} rho_s={rho_s} n0={n0}", flush=True)
        cache[(rho, lam, rho_s)] = exp_a.walk_rating_diffs(
            obs, panel, RidgeParams(n0=n0, rho=rho, rho_s=rho_s)
        )
    return cache


def inner_cv_cells(
    panel: Sequence[Mapping[str, Any]],
    rd_cache: Mapping[Tuple[float, float, float], Mapping[str, float]],
    grid: Sequence[Mapping[str, Any]],
    *,
    validate_ks: Sequence[int],
    burn_in: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Inner expanding CV MAE vs m (not market). Design = seasons in [burn_in, k)."""
    cells: List[Dict[str, Any]] = []
    folds: List[Dict[str, Any]] = []
    for cfg in grid:
        cfg_id = str(cfg["cfg_id"])
        rho, lam, rho_s = float(cfg["rho"]), float(cfg["lambda"]), float(cfg["rho_s"])
        hfa_mode = str(cfg["hfa_mode"])
        rdmap = rd_cache[(rho, lam, rho_s)]
        maes = []
        for k in validate_ks:
            design = [g for g in panel if burn_in <= int(g["season"]) < k]
            eval_g = [g for g in panel if int(g["season"]) == k]
            if not eval_g:
                _void(f"empty eval season {k} for {cfg_id}")
            if not design:
                _void(f"empty design seasons < {k} for {cfg_id}")
            fitb = fit_beta_fold(
                np.array([rdmap[g["game_id"]] for g in design], dtype=np.float64),
                np.array([g["m"] for g in design], dtype=np.float64),
                np.array([g["home_ind"] for g in design], dtype=np.float64),
                hfa_mode=hfa_mode,
            )
            pm = predict_margin_a(
                np.array([rdmap[g["game_id"]] for g in eval_g], dtype=np.float64),
                np.array([g["home_ind"] for g in eval_g], dtype=np.float64),
                beta=fitb["beta"],
                hfa=fitb["hfa"],
            )
            mae = _mae(list(pm), [g["m"] for g in eval_g])
            maes.append((mae, len(eval_g)))
            folds.append(
                {
                    "cfg_id": cfg_id,
                    "k": k,
                    "n_design": fitb["n"],
                    "n_eval": len(eval_g),
                    "mae": mae,
                    "beta": fitb["beta"],
                    "hfa": fitb["hfa"],
                    "hfa_mode": hfa_mode,
                    "rho": rho,
                    "lambda": lam,
                    "rho_s": rho_s,
                }
            )
        n_oof = sum(n for _, n in maes)
        pooled = sum(mae * n for mae, n in maes) / max(n_oof, 1)
        cells.append(
            {
                "cfg_id": cfg_id,
                "rho": rho,
                "lambda": lam,
                "rho_s": rho_s,
                "n0": lam * N0_BASE,
                "hfa_mode": hfa_mode,
                "mae": float(pooled),
                "n_oof": n_oof,
            }
        )
    return cells, folds


def score_cell(
    panel: Sequence[Mapping[str, Any]],
    rd_cache: Mapping[Tuple[float, float, float], Mapping[str, float]],
    cfg: Mapping[str, Any],
    years: Sequence[int],
    *,
    burn_in: int,
    label: str,
) -> List[Dict[str, Any]]:
    rho, lam, rho_s = float(cfg["rho"]), float(cfg["lambda"]), float(cfg["rho_s"])
    hfa_mode = str(cfg["hfa_mode"])
    rdmap = rd_cache[(rho, lam, rho_s)]
    cfg_id = str(cfg["cfg_id"])
    out: List[Dict[str, Any]] = []
    for S in years:
        design = [g for g in panel if burn_in <= int(g["season"]) < S]
        eval_g = [g for g in panel if int(g["season"]) == S]
        if not eval_g:
            _void(f"empty score season {S} for {cfg_id}")
        if not design:
            _void(f"empty score design < {S} for {cfg_id}")
        fitb = fit_beta_fold(
            np.array([rdmap[g["game_id"]] for g in design], dtype=np.float64),
            np.array([g["m"] for g in design], dtype=np.float64),
            np.array([g["home_ind"] for g in design], dtype=np.float64),
            hfa_mode=hfa_mode,
        )
        pm = predict_margin_a(
            np.array([rdmap[g["game_id"]] for g in eval_g], dtype=np.float64),
            np.array([g["home_ind"] for g in eval_g], dtype=np.float64),
            beta=fitb["beta"],
            hfa=fitb["hfa"],
        )
        for g, p in zip(eval_g, pm):
            out.append(
                {
                    "season": g["season"],
                    "week": g["week"],
                    "game_id": g["game_id"],
                    "home": g["home"],
                    "away": g["away"],
                    "neutral": int(bool(g["neutral"])),
                    "home_ind": g["home_ind"],
                    "m": g["m"],
                    "mm": g["mm"],
                    "rating_diff_home": rdmap[g["game_id"]],
                    "pm_A": float(p),
                    "beta": fitb["beta"],
                    "hfa": fitb["hfa"],
                    "cfg_id": cfg_id,
                    "label": label,
                    "n_design": fitb["n"],
                }
            )
    return out


def paired_game_boot(delta: np.ndarray, *, B: int = BOOT_B, seed: int = BOOT_SEED) -> Dict[str, float]:
    rng = np.random.default_rng(seed)
    n = int(delta.size)
    boot = np.empty(B, dtype=np.float64)
    for i in range(B):
        ix = rng.integers(0, n, size=n)
        boot[i] = float(delta[ix].mean())
    lo = float(np.percentile(boot, 2.5))
    hi = float(np.percentile(boot, 97.5))
    point = float(delta.mean()) if n else float("nan")
    return {
        "point": point,
        "ci95_lo": lo,
        "ci95_hi": hi,
        "ci_excludes_0": bool(lo > 0.0 or hi < 0.0),
        "B": B,
        "seed": seed,
        "n": n,
        "method": "paired_game_percentile_95",
    }


def season_block_boot(
    delta: np.ndarray, seasons: Sequence[int], *, B: int = BOOT_B, seed: int = BOOT_SEED
) -> Dict[str, float]:
    rng = np.random.default_rng(seed)
    seas = np.asarray(seasons, dtype=np.int32)
    uniq = np.array(sorted(set(int(s) for s in seasons)), dtype=np.int32)
    boot = np.empty(B, dtype=np.float64)
    for i in range(B):
        sampled = rng.choice(uniq, size=uniq.size, replace=True)
        parts = [delta[seas == s] for s in sampled]
        cat = np.concatenate(parts) if parts else np.array([], dtype=np.float64)
        boot[i] = float(cat.mean()) if cat.size else float("nan")
    lo = float(np.percentile(boot, 2.5))
    hi = float(np.percentile(boot, 97.5))
    return {
        "point": float(delta.mean()) if delta.size else float("nan"),
        "ci95_lo": lo,
        "ci95_hi": hi,
        "ci_excludes_0": bool(lo > 0.0 or hi < 0.0),
        "B": B,
        "seed": seed,
        "n_seasons": int(uniq.size),
        "method": "season_block_percentile_95",
        "role": "report_only_cannot_PASS_FAIL",
    }


def metrics_vs_ref(
    model_rows: Sequence[Mapping[str, Any]],
    ref_rows: Sequence[Mapping[str, Any]],
    *,
    label: str,
    binding: bool,
) -> Dict[str, Any]:
    by_id = {r["game_id"]: r for r in ref_rows}
    aligned_m = []
    aligned_model = []
    aligned_ref = []
    aligned_mm = []
    aligned_season = []
    missing = 0
    for r in model_rows:
        ref = by_id.get(r["game_id"])
        if ref is None:
            missing += 1
            continue
        aligned_m.append(float(r["m"]))
        aligned_model.append(float(r["pm_A"]))
        aligned_ref.append(float(ref["pm_A"]))
        aligned_mm.append(float(r["mm"]))
        aligned_season.append(int(r["season"]))
    if missing:
        _void(f"{label} model/ref game_id mismatch n={missing}")
    n = len(aligned_m)
    mae_model = _mae(aligned_model, aligned_m)
    mae_ref = _mae(aligned_ref, aligned_m)
    mae_mkt = _mae(aligned_mm, aligned_m)
    d_ref = np.array(
        [abs(m - rf) - abs(m - md) for m, md, rf in zip(aligned_m, aligned_model, aligned_ref)],
        dtype=np.float64,
    )
    d_mkt = np.array(
        [abs(m - mm) - abs(m - md) for m, md, mm in zip(aligned_m, aligned_model, aligned_mm)],
        dtype=np.float64,
    )
    boot_ref = paired_game_boot(d_ref)
    boot_mkt = paired_game_boot(d_mkt)
    block = season_block_boot(d_ref, aligned_season)
    y = np.asarray(aligned_m, dtype=np.float64) - np.asarray(aligned_mm, dtype=np.float64)
    x = (np.asarray(aligned_model, dtype=np.float64) - np.asarray(aligned_mm, dtype=np.float64)).reshape(-1, 1)
    fitc = ols_hc1(x, y)
    c_hat = float(fitc["beta"][0])
    c_se = float(fitc["se"][0])
    c_lo, c_hi = hc1_ci(c_hat, c_se)
    bias = float(sum(m - p for m, p in zip(aligned_m, aligned_model)) / max(n, 1))
    return {
        "label": label,
        "role": "binding" if binding else "report_only",
        "n": n,
        "seasons": sorted(set(aligned_season)),
        "MAE_model": mae_model,
        "MAE_ref": mae_ref,
        "MAE_mkt": mae_mkt,
        "ΔMAE_ref": mae_ref - mae_model,
        "ΔMAE_mkt": mae_mkt - mae_model,
        "ΔMAE_mkt_role": "REPORT_ONLY_NOTE",
        "ΔMAE_mkt_expected_sign": "<0",
        "bias": bias,
        "binding_CI": boot_ref,
        "market_CI_report_only": boot_mkt,
        "season_block_CI_report_only": block,
        "c_report_only": {
            "equation": "(m-mm) = c*(margin_A-mm) + e",
            "c": c_hat,
            "c_se_hc1": c_se,
            "c_ci95_lo": c_lo,
            "c_ci95_hi": c_hi,
            "role": "REPORT_ONLY_NOTE_HC1_diagnostic",
        },
        "beats_market_claim": False,
    }


def cfg_by_id(grid: Sequence[Mapping[str, Any]], cfg_id: str) -> Dict[str, Any]:
    for c in grid:
        if str(c["cfg_id"]) == cfg_id:
            return {
                "cfg_id": cfg_id,
                "rho": float(c["rho"]),
                "lambda": float(c["lambda"]),
                "rho_s": float(c["rho_s"]),
                "hfa_mode": str(c["hfa_mode"]),
                "n0": float(c["lambda"]) * N0_BASE,
            }
    _void(f"cfg_id {cfg_id} not in db2cf4b2 grid")
    raise AssertionError


def build_F(
    *,
    name: str,
    winner: Mapping[str, Any],
    p_sel: Sequence[int],
    p_score: Sequence[int],
    burn_in: int,
    tip: str,
    psel_sha: str,
    pscore_sha: str,
    oos_le2023_sha: str,
    n_ge2024_source: int,
) -> Dict[str, Any]:
    return {
        "document": name,
        "label": LABEL,
        "cert_candidate": 0,
        "research_diagnostic": True,
        "protocol_sha256": PROTOCOL_SHA256,
        "protocol_sha8": PROTOCOL_SHA8,
        "selected_cell": {
            "cfg_id": winner["cfg_id"],
            "rho": winner["rho"],
            "lambda": winner["lambda"],
            "rho_s": winner["rho_s"],
            "hfa_mode": winner["hfa_mode"],
            "n0": winner["n0"],
            "inner_cv_mae": winner["mae"],
            "n_oof": winner["n_oof"],
        },
        "ref_cell": dict(REF_PARAMS),
        "n0_base": N0_BASE,
        "grid_hash": H2_SHA256,
        "estimator": ESTIMATOR_ADDENDUM_SHA8,
        "estimator_id": ESTIMATOR_ID,
        "bounds": {
            "burn_in": burn_in,
            "P_sel": list(p_sel),
            "P_score": list(p_score),
        },
        "code_tip": tip,
        "sha256_P_sel_only_filtered_input": psel_sha,
        "sha256_P_score_input": pscore_sha,
        "sha256_le2023_derivative_of_1ee90fac": oos_le2023_sha,
        "upstream_hashes": {
            "epa_wf_features_2013_2023.csv": EMIT_SHA256,
            "rolling_features_weekly_pbp_strict_asof_2013_2023.csv": ROLLING_SHA256,
            "historical_oos_games.csv": OOS_SHA256,
            "games.csv": GAMES_SHA256,
        },
        "n_rows_season_ge_2024_source_counted_only": n_ge2024_source,
        "n_rows_season_ge_2024_derived": 0,
        "seed": BOOT_SEED,
        "B": BOOT_B,
        "metric_definitions_s8": METRIC_DEFS,
        "winner_eq_ref": str(winner["cfg_id"]) == REF_CELL_ID,
        "cut_attestation_s4_1": (
            "B1 cut 2014–2018/2019–2022 pre-specified by Alex on design grounds "
            "(burn-in 2013; ~equal halves; scored window = latest ≤2022 seasons) "
            "before any Lane B score; author attests no per-season Lane A OOF MAE "
            "was used to choose the cut. CoS ACCEPT b63560f2 = Alex-proposed, not Ryan-locked."
        ),
        "scope_line_s2": (
            "PASS_PROTOCOL ≠ CLEAR ≠ PASS_RESEARCH ≠ CERT; Lane B label applies only "
            "to new nested artifacts; does not reclassify Exp A 0d1f4f9b or the "
            "existing G34 ≤2022 OOF (stays Lane A DEVELOPMENT_ONLY)."
        ),
    }


def load_ready() -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[Dict[str, Any]], str, int]:
    if _sha256_file(H2_PATH) != H2_SHA256:
        _void("H2 hash drift")
    if _sha256_file(OOS_SRC) != OOS_SHA256:
        _void("oos 1ee90fac hash drift")
    if _sha256_file(GAMES_PATH) != GAMES_SHA256:
        _void("games 4fe1cdd7 hash drift")
    n_ge = count_ge2024_season_only(OOS_SRC)
    oos_le = OUT_DIR / "oos_le2023.csv"
    n_src, n_keep, oos_sha = derive_le2023(OOS_SRC, oos_le)
    if n_src != n_ge:
        _void(f"2024+ count mismatch season-only={n_ge} derive={n_src}")
    print(f"[d6] source 1ee90fac n_rows season≥2024 counted_only={n_ge}; derived n={n_keep} sha8={_sha8(oos_sha)}", flush=True)

    emit_path = CACHE_DIR / "epa_wf_features_2013_2023.csv"
    _extract_emit(emit_path)
    _close_h1()
    exp_a.OOS_PATH = oos_le
    exp_a.CACHE_DIR = CACHE_DIR
    pack, n_pbp_ge = exp_a.load_team_games()
    if n_pbp_ge:
        _void(f"PBP n_plays season≥2024={n_pbp_ge}")
    obs = exp_a._obs_arrays(pack["rows"])
    panel, n_games_ge, n_oos_ge = exp_a.load_panel(emit_path)
    if n_games_ge or n_oos_ge:
        _void(f"panel 2024+ contact games={n_games_ge} oos={n_oos_ge}")
    assert_panel_no_ge2024(panel, "panel")
    print(f"[panel] n={len(panel)} team_games={len(pack['rows'])}", flush=True)
    return panel, obs, pack["rows"], oos_sha, n_ge


PRED_FIELDS = [
    "season",
    "week",
    "game_id",
    "home",
    "away",
    "neutral",
    "home_ind",
    "m",
    "mm",
    "rating_diff_home",
    "pm_A",
    "beta",
    "hfa",
    "cfg_id",
    "label",
    "n_design",
]


def phase_freeze() -> int:
    _assert_no_forbidden()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tip = _git_tip()
    if len(tip) != 40:
        _void(f"code tip not 40-hex: {tip!r}")
    manifest = json.loads(H2_PATH.read_text(encoding="utf-8"))
    grid = list(manifest["grid"])
    if len(grid) != 54:
        _void(f"grid size {len(grid)}")
    ref = cfg_by_id(grid, REF_CELL_ID)
    if (ref["rho"], ref["lambda"], ref["rho_s"], ref["hfa_mode"]) != (0.95, 1.0, 0.67, "off"):
        _void(f"ref cell params drift {ref}")

    panel, obs, _rows, oos_sha, n_ge = load_ready()
    rd_cache = rating_cache(obs, panel, grid)

    # --- B1 selection (2014–2018; validate 2015–2018) ---
    psel_b1 = list(range(2014, 2019))
    pscore_b1 = list(range(2019, 2023))
    psel_ids = {g["game_id"] for g in panel if int(g["season"]) in psel_b1}
    pscore_ids = {g["game_id"] for g in panel if int(g["season"]) in pscore_b1}
    overlap = psel_ids & pscore_ids
    if overlap:
        _void(f"B1 selection∩scored n={len(overlap)}")
    if max(psel_b1) >= min(pscore_b1):
        _void("B1 seasons(P_sel) not < min P_score")

    psel_rows = _panel_csv_rows(panel, psel_b1)
    pscore_rows = _panel_csv_rows(panel, pscore_b1)
    fields = list(psel_rows[0].keys())
    psel_sha = _write_csv(OUT_DIR / "input_psel_b1.csv", fields, psel_rows)
    pscore_sha = _write_csv(OUT_DIR / "input_pscore_b1.csv", fields, pscore_rows)
    assert_no_ge2024(OUT_DIR / "input_psel_b1.csv", "input_psel_b1")
    assert_no_ge2024(OUT_DIR / "input_pscore_b1.csv", "input_pscore_b1")

    cells, folds = inner_cv_cells(panel, rd_cache, grid, validate_ks=list(range(2015, 2019)), burn_in=2013)
    winner = dict(select_cell(cells, epsilon=EPS))
    print(f"[b1] winner={winner['cfg_id']} mae={winner['mae']:.6f} n_oof={winner['n_oof']} eq_ref={winner['cfg_id']==REF_CELL_ID}", flush=True)
    _write_csv(
        OUT_DIR / "grid_mae_b1.csv",
        ["cfg_id", "rho", "lambda", "rho_s", "n0", "hfa_mode", "mae", "n_oof"],
        cells,
    )
    _write_json(OUT_DIR / "winner_b1.json", winner)
    _write_csv(
        OUT_DIR / "fold_table_b1.csv",
        ["cfg_id", "k", "n_design", "n_eval", "mae", "beta", "hfa", "hfa_mode", "rho", "lambda", "rho_s"],
        folds,
    )

    f_b1 = build_F(
        name="F_B1",
        winner=winner,
        p_sel=psel_b1,
        p_score=pscore_b1,
        burn_in=2013,
        tip=tip,
        psel_sha=psel_sha,
        pscore_sha=pscore_sha,
        oos_le2023_sha=oos_sha,
        n_ge2024_source=n_ge,
    )
    f_b1["selection_n"] = {
        "P_sel_games": len(psel_ids),
        "P_sel_seasons": psel_b1,
        "inner_cv_validate_seasons": list(range(2015, 2019)),
        "inner_cv_n_oof": int(winner["n_oof"]),
        "scored_n_input_games": len(pscore_ids),
        "scored_seasons": pscore_b1,
        "selection_intersect_scored": False,
        "n_overlap": 0,
    }
    required = [
        "selected_cell",
        "ref_cell",
        "n0_base",
        "grid_hash",
        "estimator",
        "bounds",
        "code_tip",
        "sha256_P_sel_only_filtered_input",
        "sha256_P_score_input",
        "sha256_le2023_derivative_of_1ee90fac",
        "seed",
        "metric_definitions_s8",
    ]
    missing = [k for k in required if k not in f_b1]
    if missing:
        _void(f"F_B1 missing fields {missing}")
    if len(f_b1["code_tip"]) != 40:
        _void("F_B1 code_tip not 40-hex")
    f_b1_sha = _write_json(OUT_DIR / "F_B1.json", f_b1)
    print(f"[freeze] F_B1 sha256={f_b1_sha} sha8={_sha8(f_b1_sha)}", flush=True)

    # --- B2 / alt selections (seal all F before any score) ---
    f_shas: Dict[str, str] = {"F_B1.json": f_b1_sha}
    for S in range(2017, 2023):
        psel = list(range(2014, S))
        pscore = [S]
        ids_s = {g["game_id"] for g in panel if int(g["season"]) in psel}
        ids_c = {g["game_id"] for g in panel if int(g["season"]) in pscore}
        if ids_s & ids_c:
            _void(f"B2 S={S} overlap")
        psel_sha_s = _write_csv(OUT_DIR / f"input_psel_b2_{S}.csv", fields, _panel_csv_rows(panel, psel))
        pscore_sha_s = _write_csv(OUT_DIR / f"input_pscore_b2_{S}.csv", fields, _panel_csv_rows(panel, pscore))
        assert_no_ge2024(OUT_DIR / f"input_psel_b2_{S}.csv", f"b2_psel_{S}")
        assert_no_ge2024(OUT_DIR / f"input_pscore_b2_{S}.csv", f"b2_pscore_{S}")
        validate = list(range(2015, S))
        cells_s, _ = inner_cv_cells(panel, rd_cache, grid, validate_ks=validate, burn_in=2013)
        win_s = dict(select_cell(cells_s, epsilon=EPS))
        _write_csv(
            OUT_DIR / f"grid_mae_b2_{S}.csv",
            ["cfg_id", "rho", "lambda", "rho_s", "n0", "hfa_mode", "mae", "n_oof"],
            cells_s,
        )
        f_s = build_F(
            name=f"F_B2_S{S}",
            winner=win_s,
            p_sel=psel,
            p_score=pscore,
            burn_in=2013,
            tip=tip,
            psel_sha=psel_sha_s,
            pscore_sha=pscore_sha_s,
            oos_le2023_sha=oos_sha,
            n_ge2024_source=n_ge,
        )
        f_s["role"] = "B2_supportive_cannot_alone_PASS"
        f_shas[f"F_B2_S{S}.json"] = _write_json(OUT_DIR / f"F_B2_S{S}.json", f_s)
        print(f"[b2] S={S} winner={win_s['cfg_id']} mae={win_s['mae']:.6f} F={_sha8(f_shas[f'F_B2_S{S}.json'])}", flush=True)

    for alt, psel, pscore in (
        ("A1", list(range(2014, 2018)), list(range(2018, 2023))),
        ("A2", list(range(2014, 2020)), list(range(2020, 2023))),
    ):
        if set(psel) & set(pscore):
            _void(f"{alt} season overlap")
        psel_sha_a = _write_csv(OUT_DIR / f"input_psel_{alt}.csv", fields, _panel_csv_rows(panel, psel))
        pscore_sha_a = _write_csv(OUT_DIR / f"input_pscore_{alt}.csv", fields, _panel_csv_rows(panel, pscore))
        assert_no_ge2024(OUT_DIR / f"input_psel_{alt}.csv", f"{alt}_psel")
        assert_no_ge2024(OUT_DIR / f"input_pscore_{alt}.csv", f"{alt}_pscore")
        validate = list(range(2015, max(psel) + 1))
        cells_a, _ = inner_cv_cells(panel, rd_cache, grid, validate_ks=validate, burn_in=2013)
        win_a = dict(select_cell(cells_a, epsilon=EPS))
        _write_csv(
            OUT_DIR / f"grid_mae_{alt}.csv",
            ["cfg_id", "rho", "lambda", "rho_s", "n0", "hfa_mode", "mae", "n_oof"],
            cells_a,
        )
        f_a = build_F(
            name=f"F_{alt}",
            winner=win_a,
            p_sel=psel,
            p_score=pscore,
            burn_in=2013,
            tip=tip,
            psel_sha=psel_sha_a,
            pscore_sha=pscore_sha_a,
            oos_le2023_sha=oos_sha,
            n_ge2024_source=n_ge,
        )
        f_a["role"] = "alt_cut_report_only_cannot_PASS_or_FAIL"
        f_shas[f"F_{alt}.json"] = _write_json(OUT_DIR / f"F_{alt}.json", f_a)
        print(f"[alt] {alt} winner={win_a['cfg_id']} F={_sha8(f_shas[f'F_{alt}.json'])}", flush=True)

    _write_sums(OUT_DIR / "SHA256SUMS.freeze", f_shas)
    _write_json(
        OUT_DIR / "freeze_manifest.json",
        {
            "phase": "freeze",
            "forecast_ts_utc": _utc_now(),
            "code_tip": tip,
            "F_B1_sha256": f_b1_sha,
            "F_B1_sha8": _sha8(f_b1_sha),
            "F_sha256": f_shas,
            "winner_b1": winner["cfg_id"],
            "winner_eq_ref": winner["cfg_id"] == REF_CELL_ID,
            "selection_intersect_scored": False,
            "n_overlap": 0,
            "n_rows_season_ge_2024_derived": 0,
            "n_rows_season_ge_2024_source_counted_only": n_ge,
            "predictions_written": False,
        },
    )

    paper = _freeze_paper(
        tip=tip,
        f_b1_sha=f_b1_sha,
        f_shas=f_shas,
        winner=winner,
        n_ge=n_ge,
        oos_sha=oos_sha,
        psel_sha=psel_sha,
        pscore_sha=pscore_sha,
        n_psel=len(psel_ids),
        n_pscore=len(pscore_ids),
        n_inner=int(winner["n_oof"]),
    )
    paper_sha = _write_readonly(OUT_DIR / "CURSOR_NESTED_G34_FREEZE_t4639u_v1.md", paper)
    ops = ROOT / "research" / "ops" / "CURSOR_NESTED_G34_FREEZE_t4639u_v1.md"
    _write_readonly(ops, paper)
    print(f"[freeze] paper sha8={_sha8(paper_sha)} F_B1={_sha8(f_b1_sha)} — STOP before P_score", flush=True)
    _assert_no_forbidden()
    return 0


def _freeze_paper(
    *,
    tip: str,
    f_b1_sha: str,
    f_shas: Mapping[str, str],
    winner: Mapping[str, Any],
    n_ge: int,
    oos_sha: str,
    psel_sha: str,
    pscore_sha: str,
    n_psel: int,
    n_pscore: int,
    n_inner: int,
) -> str:
    lines = [
        "# CURSOR_NESTED_G34_FREEZE_t4639u_v1",
        "",
        "**FREEZE PAPER · F sealed BEFORE first P_score prediction · CERT=0 · NFL NO-GO · F2 frozen · Coming Soon ON · #648 DRAFT · do not merge**",
        "",
        "Filed to record F sha256 in a CoS-visible paper before any P_score prediction (protocol 59161fbb §6 / D4).",
        "No P_score predictions exist at this filing. Score phase follows this paper.",
        "",
        "## Authority",
        "",
        "| item | sha8 |",
        "|---|---|",
        f"| DECISION_RYAN_t4639u | `{DECISION_SHA8}` |",
        f"| COS_ORDER_CURSOR_t4639u | `{COS_ORDER_SHA8}` |",
        f"| Protocol v2 (unchanged) | `{PROTOCOL_SHA8}` |",
        f"| IMV PASS_PROTOCOL | `{IMV_PASS_SHA8}` |",
        f"| Parent DECISION | `{PARENT_DECISION_SHA8}` |",
        f"| H2 grid | `db2cf4b2` |",
        f"| Estimator addendum | `{ESTIMATOR_ADDENDUM_SHA8}` |",
        f"| Code tip (40-hex) | `{tip}` |",
        "",
        "## F_B1 (binding) sha256 — recorded BEFORE P_score",
        "",
        f"- path: `research/nfl/t4639u_nested_g34/F_B1.json`",
        f"- sha256: `{f_b1_sha}`",
        f"- sha8: `{_sha8(f_b1_sha)}`",
        f"- selected: `{winner['cfg_id']}` ρ={winner['rho']} λ={winner['lambda']} ρ_s={winner['rho_s']} HFA={winner['hfa_mode']} n0={winner['n0']}",
        f"- ref_cell_id: `G27` ρ=0.95 λ=1 ρ_s=0.67 HFA off n0=4",
        f"- winner==ref: `{str(winner['cfg_id']) == REF_CELL_ID}`",
        f"- P_sel 2014–2018 n_games={n_psel}; inner-CV validate 2015–2018 n_oof={n_inner}",
        f"- P_score input 2019–2022 n_games={n_pscore} (hashed; **not predicted yet**)",
        f"- selection∩scored=∅: TRUE (n_overlap=0)",
        f"- sha256 P_sel-only input: `{psel_sha}`",
        f"- sha256 P_score input: `{pscore_sha}`",
        f"- sha256 ≤2023 derivative of 1ee90fac: `{oos_sha}`",
        f"- n_rows season≥2024 source (counted only): {n_ge}",
        f"- n_rows season≥2024 derived: 0",
        "",
        "## Supportive F (also sealed before any score)",
        "",
        "| F | sha8 |",
        "|---|---|",
    ]
    for name, digest in sorted(f_shas.items()):
        lines.append(f"| `{name}` | `{_sha8(digest)}` |")
    lines += [
        "",
        "## Invariants at freeze",
        "",
        "- Protocol 59161fbb text not edited.",
        "- 2024+ outcomes not read. Mixed 1ee90fac existence ≠ abort.",
        "- Existing G34 ≤2022 OOF stays Lane A DEVELOPMENT_ONLY.",
        "- Exp A 0d1f4f9b / Exp D-R 93a79857 untouched.",
        "- No Odds. No merge. No CERT.",
        "",
        "**CERT=0. RESEARCH_DIAGNOSTIC. NFL NO-GO. F2 frozen. Coming Soon ON.**",
        "",
    ]
    return "\n".join(lines)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def phase_score() -> int:
    _assert_no_forbidden()
    f_path = OUT_DIR / "F_B1.json"
    paper = OUT_DIR / "CURSOR_NESTED_G34_FREEZE_t4639u_v1.md"
    if not f_path.is_file() or not paper.is_file():
        _void("F_B1 / freeze paper missing; refuse score")
    pred_path = OUT_DIR / "predictions_b1.csv"
    if pred_path.is_file():
        _void("predictions_b1.csv already exists; no re-run")
    f_b1 = _load_json(f_path)
    f_sha = _sha256_file(f_path)
    paper_txt = paper.read_text(encoding="utf-8")
    if f_sha not in paper_txt:
        _void("F_B1 sha256 not recorded in freeze paper")
    f_mtime = f_path.stat().st_mtime
    paper_mtime = paper.stat().st_mtime
    if paper_mtime < f_mtime:
        _void("freeze paper mtime precedes F_B1 (inversion)")

    required = [
        "selected_cell",
        "ref_cell",
        "n0_base",
        "grid_hash",
        "estimator",
        "bounds",
        "code_tip",
        "sha256_P_sel_only_filtered_input",
        "sha256_P_score_input",
        "sha256_le2023_derivative_of_1ee90fac",
        "seed",
        "metric_definitions_s8",
    ]
    missing = [k for k in required if k not in f_b1]
    if missing:
        _void(f"F_B1 incomplete at score {missing}")

    manifest = json.loads(H2_PATH.read_text(encoding="utf-8"))
    grid = list(manifest["grid"])
    panel, obs, _rows, _oos_sha, n_ge = load_ready()
    rd_cache = rating_cache(obs, panel, grid)

    win_cfg = cfg_by_id(grid, str(f_b1["selected_cell"]["cfg_id"]))
    ref_cfg = cfg_by_id(grid, REF_CELL_ID)
    winner_eq_ref = win_cfg["cfg_id"] == REF_CELL_ID

    psel_ids = {g["game_id"] for g in panel if int(g["season"]) in f_b1["bounds"]["P_sel"]}
    pscore_ids = {g["game_id"] for g in panel if int(g["season"]) in f_b1["bounds"]["P_score"]}
    if psel_ids & pscore_ids:
        _void("B1 overlap at score")

    print("[score] B1 P_score 2019–2022 selected + ref", flush=True)
    pred_model = score_cell(panel, rd_cache, win_cfg, f_b1["bounds"]["P_score"], burn_in=2013, label="B1_selected")
    pred_ref = score_cell(panel, rd_cache, ref_cfg, f_b1["bounds"]["P_score"], burn_in=2013, label="B1_ref")
    if datetime.now().timestamp() < paper_mtime:
        _void("prediction clock inversion vs freeze paper")
    pred_sha = _write_csv(OUT_DIR / "predictions_b1.csv", PRED_FIELDS, pred_model)
    ref_sha = _write_csv(OUT_DIR / "predictions_b1_ref.csv", PRED_FIELDS, pred_ref)
    if OUT_DIR.joinpath("predictions_b1.csv").stat().st_mtime < paper_mtime:
        _void("predictions mtime precedes freeze paper")

    bind = metrics_vs_ref(pred_model, pred_ref, label="B1_2019_2022_pooled", binding=True)
    _write_json(OUT_DIR / "metrics_b1.json", bind)

    invariants_ok = (
        len(psel_ids & pscore_ids) == 0
        and bind["n"] == len(pred_model)
        and n_ge >= 0
    )
    if winner_eq_ref:
        verdict = "FAIL_RESEARCH"
        verdict_note = "winner==ref ⇒ ΔMAE_ref≡0 ⇒ FAIL_RESEARCH"
    elif not invariants_ok:
        verdict = "VOID"
        verdict_note = "invariant fail"
    elif bind["ΔMAE_ref"] >= 0.10 and bind["binding_CI"]["ci_excludes_0"]:
        verdict = "PASS_RESEARCH"
        verdict_note = "B1 ΔMAE_ref≥0.10 vs frozen ref AND §8.1 CI excludes 0"
    else:
        verdict = "FAIL_RESEARCH"
        verdict_note = "invariants hold; B1 criterion not met"

    # --- B2 score (report-only) ---
    b2_model: List[Dict[str, Any]] = []
    b2_ref: List[Dict[str, Any]] = []
    b2_by_s: Dict[str, Any] = {}
    for S in range(2017, 2023):
        f_s = _load_json(OUT_DIR / f"F_B2_S{S}.json")
        cfg_s = cfg_by_id(grid, str(f_s["selected_cell"]["cfg_id"]))
        m_s = score_cell(panel, rd_cache, cfg_s, [S], burn_in=2013, label=f"B2_S{S}_selected")
        r_s = score_cell(panel, rd_cache, ref_cfg, [S], burn_in=2013, label=f"B2_S{S}_ref")
        met_s = metrics_vs_ref(m_s, r_s, label=f"B2_S{S}", binding=False)
        b2_by_s[str(S)] = {"winner": cfg_s["cfg_id"], "metrics": met_s}
        b2_model.extend(m_s)
        b2_ref.extend(r_s)
    _write_csv(OUT_DIR / "predictions_b2.csv", PRED_FIELDS, b2_model)
    b2_pool = metrics_vs_ref(b2_model, b2_ref, label="B2_2017_2022_pooled", binding=False)
    _write_json(OUT_DIR / "metrics_b2.json", {"pooled": b2_pool, "by_S": b2_by_s})
    unstable = bool(verdict == "PASS_RESEARCH" and b2_pool["ΔMAE_ref"] <= 0.0)
    if unstable:
        verdict_note += "; B2 pooled ΔMAE_ref≤0 ⇒ UNSTABLE for IMV"

    # --- 2023 supportive (F_B1 cell; β fit 2013–2022) ---
    pred_23 = score_cell(panel, rd_cache, win_cfg, [2023], burn_in=2013, label="S2023_supportive_selected")
    ref_23 = score_cell(panel, rd_cache, ref_cfg, [2023], burn_in=2013, label="S2023_supportive_ref")
    _write_csv(OUT_DIR / "predictions_2023.csv", PRED_FIELDS, pred_23)
    met_23 = metrics_vs_ref(pred_23, ref_23, label="2023_supportive", binding=False)
    _write_json(OUT_DIR / "metrics_2023.json", met_23)

    # --- alt cuts ---
    alt_metrics = {}
    for alt, years in (("A1", list(range(2018, 2023))), ("A2", list(range(2020, 2023)))):
        f_a = _load_json(OUT_DIR / f"F_{alt}.json")
        cfg_a = cfg_by_id(grid, str(f_a["selected_cell"]["cfg_id"]))
        m_a = score_cell(panel, rd_cache, cfg_a, years, burn_in=2013, label=f"{alt}_selected")
        r_a = score_cell(panel, rd_cache, ref_cfg, years, burn_in=2013, label=f"{alt}_ref")
        _write_csv(OUT_DIR / f"predictions_{alt}.csv", PRED_FIELDS, m_a)
        alt_metrics[alt] = {
            "winner": cfg_a["cfg_id"],
            "metrics": metrics_vs_ref(m_a, r_a, label=alt, binding=False),
        }
    _write_json(OUT_DIR / "metrics_alt.json", alt_metrics)

    counts = {
        "ticket": TICKET,
        "label": LABEL,
        "cert_candidate": 0,
        "nfl_nogo": True,
        "f2_frozen": True,
        "coming_soon": True,
        "verdict": verdict,
        "verdict_note": verdict_note,
        "unstable_b2": unstable,
        "winner_eq_ref": winner_eq_ref,
        "selected_cfg_id": win_cfg["cfg_id"],
        "ref_cell_id": REF_CELL_ID,
        "F_B1_sha256": f_sha,
        "F_B1_sha8": _sha8(f_sha),
        "protocol_sha8": PROTOCOL_SHA8,
        "decision_sha8": DECISION_SHA8,
        "selection_n": {
            "P_sel_games": len(psel_ids),
            "P_sel_seasons": f_b1["bounds"]["P_sel"],
            "inner_cv_validate_seasons": list(range(2015, 2019)),
            "inner_cv_n_oof": f_b1["selected_cell"]["n_oof"],
            "scored_n": bind["n"],
            "scored_seasons": f_b1["bounds"]["P_score"],
            "selection_intersect_scored": False,
            "n_overlap": 0,
        },
        "n_rows_season_ge_2024_source_counted_only": n_ge,
        "n_rows_season_ge_2024_derived": 0,
        "B1": {
            "ΔMAE_ref": bind["ΔMAE_ref"],
            "MAE_model": bind["MAE_model"],
            "MAE_ref": bind["MAE_ref"],
            "binding_CI": bind["binding_CI"],
            "ΔMAE_mkt_REPORT_ONLY": bind["ΔMAE_mkt"],
            "c_REPORT_ONLY": bind["c_report_only"]["c"],
        },
        "B2_pooled_ΔMAE_ref_report_only": b2_pool["ΔMAE_ref"],
        "y2023_ΔMAE_ref_report_only": met_23["ΔMAE_ref"],
        "predictions_b1_sha256": pred_sha,
        "predictions_b1_ref_sha256": ref_sha,
        "odds_api_called": False,
        "simulate_nfl_game_called": False,
        "locked_scoring_touched": False,
        "protocol_edited": False,
        "lane_a_reclassified": False,
        "exp_a_reopened": False,
        "exp_dr_reopened": False,
        "scope_line": f_b1["scope_line_s2"],
    }
    counts_sha = _write_json(OUT_DIR / "counts.json", counts)
    _write_json(
        OUT_DIR / "stop_rule.json",
        {
            "verdict": verdict,
            "note": verdict_note,
            "ΔMAE_ref": bind["ΔMAE_ref"],
            "point_ge_0_10": bool(bind["ΔMAE_ref"] >= 0.10),
            "ci_excludes_0": bind["binding_CI"]["ci_excludes_0"],
            "winner_eq_ref": winner_eq_ref,
            "unstable_b2": unstable,
            "binding_CI_only": True,
        },
    )

    report = _score_report(counts, bind, b2_pool, met_23, alt_metrics, f_sha, counts_sha)
    _write_readonly(OUT_DIR / "REPORT.md", report)
    ops = ROOT / "research" / "ops" / "CURSOR_NESTED_G34_EXECUTE_t4639u_v1.md"
    _write_readonly(ops, report)
    _write_readonly(OUT_DIR / "CURSOR_NESTED_G34_EXECUTE_t4639u_v1.md", report)

    artifacts = {}
    for p in sorted(OUT_DIR.iterdir()):
        if p.is_file():
            artifacts[p.name] = _sha256_file(p)
    _write_sums(OUT_DIR / "SHA256SUMS", artifacts)
    print(
        f"[score] verdict={verdict} F_B1={_sha8(f_sha)} counts={_sha8(counts_sha)} "
        f"dMAE_ref={bind['ΔMAE_ref']:.4f} ci_excl0={bind['binding_CI']['ci_excludes_0']}",
        flush=True,
    )
    _assert_no_forbidden()
    return 0


def _score_report(
    counts: Mapping[str, Any],
    bind: Mapping[str, Any],
    b2: Mapping[str, Any],
    y23: Mapping[str, Any],
    alts: Mapping[str, Any],
    f_sha: str,
    counts_sha: str,
) -> str:
    ci = bind["binding_CI"]
    lines = [
        "# CURSOR_NESTED_G34_EXECUTE_t4639u_v1",
        "",
        "**RESEARCH_DIAGNOSTIC · CERT=0 · NFL NO-GO · F2 FROZEN · Coming Soon ON · #648 DRAFT · do not merge**",
        "",
        f"**VERDICT (protocol 59161fbb stop rules only): `{counts['verdict']}`**",
        "",
        counts["verdict_note"],
        "",
        f"Filed `{_utc_now()}`. Paper/file evidence only. No CERT claim. No beats-market claim.",
        "",
        "## Authority",
        "",
        "| item | sha8 |",
        "|---|---|",
        f"| DECISION_RYAN_t4639u | `{DECISION_SHA8}` |",
        f"| COS_ORDER | `{COS_ORDER_SHA8}` |",
        f"| Protocol v2 unchanged | `{PROTOCOL_SHA8}` |",
        f"| IMV PASS_PROTOCOL | `{IMV_PASS_SHA8}` |",
        f"| F_B1 | `{_sha8(f_sha)}` |",
        f"| counts.json | `{_sha8(counts_sha)}` |",
        "",
        "## B1 binding (2019–2022 pooled)",
        "",
        f"- selected `{counts['selected_cfg_id']}` vs frozen ref `G27`",
        f"- winner==ref: `{counts['winner_eq_ref']}`",
        f"- selection_n P_sel games={counts['selection_n']['P_sel_games']} seasons {counts['selection_n']['P_sel_seasons']}",
        f"- inner-CV n_oof={counts['selection_n']['inner_cv_n_oof']} validate {counts['selection_n']['inner_cv_validate_seasons']}",
        f"- scored_n={counts['selection_n']['scored_n']} seasons {counts['selection_n']['scored_seasons']}",
        f"- selection∩scored=∅: TRUE (n_overlap=0)",
        f"- MAE_model={bind['MAE_model']:.6f} MAE_ref={bind['MAE_ref']:.6f} **ΔMAE_ref={bind['ΔMAE_ref']:.6f}**",
        f"- binding CI (paired game B=10000 seed 4141): [{ci['ci95_lo']:.6f}, {ci['ci95_hi']:.6f}] excludes0={ci['ci_excludes_0']}",
        f"- ΔMAE_mkt={bind['ΔMAE_mkt']:.6f} **REPORT-ONLY NOTE** (no beats-market claim; expected sign < 0)",
        f"- c={bind['c_report_only']['c']:.6f} **REPORT-ONLY NOTE** (HC1 diagnostic)",
        f"- season-block CI report-only: [{bind['season_block_CI_report_only']['ci95_lo']:.6f}, {bind['season_block_CI_report_only']['ci95_hi']:.6f}]",
        f"- n_rows season≥2024 source counted only={counts['n_rows_season_ge_2024_source_counted_only']}; derived=0",
        "",
        "## Supportive (cannot PASS/FAIL)",
        "",
        f"- B2 pooled ΔMAE_ref={b2['ΔMAE_ref']:.6f} (UNSTABLE={counts['unstable_b2']})",
        f"- 2023 ΔMAE_ref={y23['ΔMAE_ref']:.6f}",
        f"- A1 winner={alts['A1']['winner']} ΔMAE_ref={alts['A1']['metrics']['ΔMAE_ref']:.6f}",
        f"- A2 winner={alts['A2']['winner']} ΔMAE_ref={alts['A2']['metrics']['ΔMAE_ref']:.6f}",
        "",
        "## Scope",
        "",
        counts["scope_line"],
        "",
        "Existing G34 ≤2022 OOF stays Lane A DEVELOPMENT_ONLY. Exp A 0d1f4f9b / Exp D-R 93a79857 untouched.",
        "",
        "**CERT=0. RESEARCH_DIAGNOSTIC. NFL NO-GO. F2 frozen. Coming Soon ON.**",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("freeze", "score"), required=True)
    args = ap.parse_args()
    if args.phase == "freeze":
        return phase_freeze()
    return phase_score()


if __name__ == "__main__":
    raise SystemExit(main())
