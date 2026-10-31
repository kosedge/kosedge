#!/usr/bin/env python3
"""Q2 Phase B EXEC (t5009u) — DEV_RESEARCH.

Hard barrier: FROZEN_CONFIG is sealed before any 2018–22 row is materialized.
DEV early stop may close the run with no EVAL look.
Keep/stop is reported only; no self-ACCEPT. Alex RO → CoS.

CERT=0 · NFL NO-GO · no merge/deploy/pub/bet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from q2pb.constants import (
    BOOT_B,
    BOOT_SEED,
    DEV_RHO_EARLY_STOP,
    DEV_SEASONS,
    DEV_WEEKS,
    EVAL_RHO_KEEP,
    EVAL_SEASONS,
    EVAL_WEEKS,
    EXPECTED_GAMES_SHA256_PREFIX,
    HISTORY_ONLY_SEASONS,
    LABEL,
    LAMBDA_GRID,
    OUTCOME_JOIN_NOTE,
    REGRESS_GRID,
    TIP_ASOF_KICKOFF,
    TIP_DESIGN,
    TIP_EVAL_SPEC,
    TIP_GAMES,
    TIP_GATED_INDEX,
    TIP_ORDER,
)
from q2pb.data import (
    load_games,
    load_outcomes_score_only,
    sha256_file,
    verify_games_pin,
    window_rows,
)
from q2pb.metrics import (
    asof_wl_diff,
    brier,
    cluster_bootstrap,
    home_team_season,
    icc_oneway,
    logistic_mle,
    mae,
    ols,
    pearson,
    record_wl_diff,
    rmse,
    spearman,
    week_cluster,
)
from q2pb.strength import asof_for_targets, assert_asof_leakage, carry_prior


NY = ZoneInfo("America/New_York")


def _write_sealed(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # 0444
    digest = sha256_file(path)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    sidecar.write_text(digest + "  " + path.name + "\n", encoding="utf-8")
    os.chmod(sidecar, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return digest


def _json_sha(obj: object) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(blob).hexdigest()


def _margins(games: list[Game]) -> np.ndarray:
    return np.asarray([g.margin for g in games], dtype=float)


def _fit_maps(feats, wl, games):
    m = _margins(games)
    rd = np.asarray([f.rating_diff for f in feats], dtype=float)
    wl_a = np.asarray(wl, dtype=float)
    ties = m == 0
    n_ties = int(ties.sum())
    q2 = ols(rd, m)
    wl_m = ols(wl_a, m)
    pm_new = q2.predict(rd)
    pm_wl = wl_m.predict(wl_a)
    y_bin = (m[~ties] > 0).astype(float)
    q2_wp = logistic_mle(pm_new[~ties], y_bin, n_ties)
    wl_wp = logistic_mle(wl_a[~ties], y_bin, n_ties)
    const_margin = float(m.mean())
    const_wp = float(y_bin.mean()) if y_bin.size else float("nan")
    return {
        "q2": q2,
        "wl_m": wl_m,
        "q2_wp": q2_wp,
        "wl_wp": wl_wp,
        "pm_new": pm_new,
        "pm_wl": pm_wl,
        "m": m,
        "rd": rd,
        "wl": wl_a,
        "n_fit": int(len(games)),
        "n_ties": n_ties,
        "const_margin": const_margin,
        "const_wp": const_wp,
        "rho": spearman(rd, m),
        "mae_new": mae(pm_new, m),
        "mae_wl": mae(pm_wl, m),
        "mae_const": mae(np.full_like(m, const_margin), m),
    }


def _wl_series(targets: list[Game], history: list[Game]) -> tuple[list[float], list[float]]:
    recomputed = [asof_wl_diff(g, history) for g in targets]
    from_record = [record_wl_diff(g) for g in targets]
    return recomputed, from_record


def phase1_dev(args) -> dict:
    games_path = Path(args.games)
    outcomes_path = Path(args.outcomes)
    games_sha = verify_games_pin(games_path)
    outcomes_sha = sha256_file(outcomes_path)
    outcomes = load_outcomes_score_only(outcomes_path, DEV_SEASONS)
    history = load_games(games_path, outcomes, DEV_SEASONS, phase="phase1_dev")
    targets = window_rows(history, DEV_SEASONS, DEV_WEEKS)
    if not targets:
        raise SystemExit("DEV window empty — STOP")

    grid_rows = []
    best = None
    for lam in LAMBDA_GRID:
        for r in REGRESS_GRID:
            persist: dict[int, dict[str, float]] = {}
            feats = asof_for_targets(history, targets, lam, r, persist_season_end=persist)
            feats = sorted(feats, key=lambda f: (f.game.kickoff_utc, f.game.game_id))
            targets_s = [f.game for f in feats]
            wl, wl_rec = _wl_series(targets_s, history)
            fitted = _fit_maps(feats, wl, targets_s)
            row = {
                "lam": lam,
                "regress_frac": r,
                "rho": fitted["rho"],
                "mae_new": fitted["mae_new"],
                "mae_wl": fitted["mae_wl"],
                "n": fitted["n_fit"],
            }
            grid_rows.append(row)
            key = (fitted["rho"], -fitted["mae_new"])
            if best is None or key > best[0]:
                best = (key, lam, r, feats, fitted, persist, wl, wl_rec, targets_s)

    assert best is not None
    _, lam, r, feats, fitted, persist, wl, wl_rec, targets_s = best
    assert_asof_leakage(history, feats)
    rec_corr = pearson(wl, wl_rec)

    resid = fitted["m"] - fitted["pm_new"]
    groups = [home_team_season(g) for g in targets_s]
    icc = icc_oneway(resid.tolist(), groups)

    early_stop_rho = fitted["rho"] < DEV_RHO_EARLY_STOP
    early_stop_mae = fitted["mae_new"] >= fitted["mae_wl"]
    early_stop = bool(early_stop_rho or early_stop_mae)

    fit_obj = {
        "label": LABEL,
        "tip_order": TIP_ORDER,
        "tip_design": TIP_DESIGN,
        "tip_eval_spec": TIP_EVAL_SPEC,
        "tip_games": TIP_GAMES,
        "tip_asof": TIP_ASOF_KICKOFF,
        "games_sha256": games_sha,
        "outcomes_sha256": outcomes_sha,
        "outcome_join_note": OUTCOME_JOIN_NOTE,
        "lam": lam,
        "regress_frac": r,
        "a": fitted["wl_m"].a,
        "b": fitted["wl_m"].b,
        "c_WL": fitted["wl_wp"].c,
        "d_WL": fitted["wl_wp"].d,
        "a_q2": fitted["q2"].a,
        "b_q2": fitted["q2"].b,
        "c": fitted["q2_wp"].c,
        "d": fitted["q2_wp"].d,
        "const_margin": fitted["const_margin"],
        "const_wp": fitted["const_wp"],
        "n_fit": fitted["n_fit"],
        "n_ties_excluded": fitted["n_ties"],
        "dev_spearman_rho": fitted["rho"],
        "dev_mae_pm_new": fitted["mae_new"],
        "dev_mae_wl_margin": fitted["mae_wl"],
        "dev_mae_const": fitted["mae_const"],
        "dev_icc_home_team_season": icc,
        "wl_diff_column_in_games_csv": None,
        "wl_diff_definition": (
            "home current-season as-of win% minus away current-season as-of "
            "win%; win%=(W+0.5T)/(W+L+T); 0-0 → 0.5; as-of games have "
            f"kickoff < target ({TIP_ASOF_KICKOFF}). games.csv has no wl_diff "
            "column; record_entering_home/away is a W-L mapping cross-check only."
        ),
        "wl_recomputed_vs_record_entering_pearson": rec_corr,
        "lambda_grid": list(LAMBDA_GRID),
        "regress_grid": list(REGRESS_GRID),
        "selection": "max DEV Spearman rho(rating_diff, m); tie-break min DEV MAE(pm_new,m)",
        "grid": grid_rows,
        "season_end_ratings": {str(k): v for k, v in persist.items()},
        "epa_status": "SKIPPED/UNAVAILABLE — no PBP 6ee24b44 on this VM; primary is margin strength",
        "gated_index_1ee90fac": "not loaded as experiment frame; score-only 2013-2022 extract only",
        "early_stop": early_stop,
        "early_stop_rho": early_stop_rho,
        "early_stop_mae": early_stop_mae,
        "eval_rows_read": False,
        "k_looks_eval": 0,
    }
    fit_sha = _json_sha(fit_obj)
    freeze_ts = datetime.now(NY).isoformat()
    config = {
        **fit_obj,
        "fit_object_sha256": fit_sha,
        "freeze_timestamp_america_new_york": freeze_ts,
    }
    config_sha = _json_sha(config)
    config["config_sha256"] = config_sha
    return {
        "games_path": str(games_path),
        "outcomes_path": str(outcomes_path),
        "games_sha": games_sha,
        "outcomes_sha": outcomes_sha,
        "fit_obj": fit_obj,
        "config": config,
        "fit_sha": fit_sha,
        "config_sha": config_sha,
        "freeze_ts": freeze_ts,
        "early_stop": early_stop,
        "feats": feats,
        "fitted": fitted,
        "targets": targets_s,
        "history": history,
        "lam": lam,
        "regress_frac": r,
        "persist": persist,
        "wl": wl,
    }


def _eval_stat_pack(feats, wl, fitted_maps, games) -> dict:
    m = _margins(games)
    rd = np.asarray([f.rating_diff for f in feats], dtype=float)
    wl_a = np.asarray(wl, dtype=float)
    pm_new = fitted_maps["q2"].predict(rd)
    pm_wl = fitted_maps["wl_m"].predict(wl_a)
    ties = m == 0
    n_ties = int(ties.sum())
    y = (m[~ties] > 0).astype(float)
    p_new = fitted_maps["q2_wp"].predict(pm_new[~ties])
    p_wl = fitted_maps["wl_wp"].predict(wl_a[~ties])
    p_const = np.full_like(y, fitted_maps["const_wp"])
    rho = spearman(rd, m)
    mae_new = mae(pm_new, m)
    mae_wl = mae(pm_wl, m)
    mae_c = mae(np.full_like(m, fitted_maps["const_margin"]), m)
    rmse_new = rmse(pm_new, m)
    rmse_wl = rmse(pm_wl, m)
    rmse_c = rmse(np.full_like(m, fitted_maps["const_margin"]), m)
    brier_new = brier(p_new, y)
    brier_wl = brier(p_wl, y)
    brier_c = brier(p_const, y)
    kill = pearson((pm_new - pm_wl), (m - pm_wl))
    d_mae = np.abs(m - pm_new) - np.abs(m - pm_wl)
    clusters = [home_team_season(g) for g in games]
    week_c = [week_cluster(g) for g in games]

    def mean_stat(arr: np.ndarray) -> float:
        return float(arr.mean())

    boot_dmae = cluster_bootstrap(d_mae, clusters, mean_stat, B=BOOT_B, seed=BOOT_SEED)

    # Spearman cluster CI: bootstrap mean of per-replicate spearman
    paired = np.column_stack([rd, m])

    def spear_stat(arr: np.ndarray) -> float:
        return spearman(arr[:, 0], arr[:, 1])

    boot_rho = cluster_bootstrap(paired, clusters, spear_stat, B=BOOT_B, seed=BOOT_SEED)
    boot_rho_week = cluster_bootstrap(paired, week_c, spear_stat, B=BOOT_B, seed=BOOT_SEED)

    loso = []
    for season in EVAL_SEASONS:
        idx = [i for i, g in enumerate(games) if g.season == season]
        if len(idx) < 8:
            continue
        ii = np.asarray(idx)
        loso.append(
            {
                "season": season,
                "n": int(len(idx)),
                "rho": spearman(rd[ii], m[ii]),
                "delta_mae": float(np.mean(d_mae[ii])),
                "kill": pearson((pm_new[ii] - pm_wl[ii]), (m[ii] - pm_wl[ii])),
            }
        )

    keep_rho = rho >= EVAL_RHO_KEEP and boot_rho["ci_lo"] > 0
    keep_mae = boot_dmae["ci_hi"] < 0  # new-WL abs-err mean CI entirely negative
    keep_kill = kill > 0
    keep = bool(keep_rho and keep_mae and keep_kill)

    return {
        "n": int(len(games)),
        "n_ties": n_ties,
        "spearman_rho": rho,
        "spearman_cluster_boot": boot_rho,
        "spearman_week_cluster_boot": boot_rho_week,
        "mae_pm_new": mae_new,
        "mae_wl_margin": mae_wl,
        "mae_const": mae_c,
        "delta_mae_new_minus_wl": float(d_mae.mean()),
        "delta_mae_cluster_boot": boot_dmae,
        "rmse_pm_new": rmse_new,
        "rmse_wl_margin": rmse_wl,
        "rmse_const": rmse_c,
        "delta_rmse_new_minus_wl": rmse_new - rmse_wl,
        "delta_rmse_new_minus_const": rmse_new - rmse_c,
        "brier_new": brier_new,
        "brier_wl_wp": brier_wl,
        "brier_const": brier_c,
        "delta_brier_new_minus_wl": brier_new - brier_wl,
        "delta_brier_new_minus_const": brier_new - brier_c,
        "kill_pearson_corr": kill,
        "loso": loso,
        "keep_rho": keep_rho,
        "keep_mae": keep_mae,
        "keep_kill": keep_kill,
        "keep_all": keep,
        "post_eval_tuning": False,
        "k_looks_eval": 1,
    }


def phase2_eval(args, phase1: dict) -> dict:
    games_path = Path(args.games)
    outcomes_path = Path(args.outcomes)
    # First read of 2017 (history) and 2018–22 (EVAL). Never 2023+.
    seasons = HISTORY_ONLY_SEASONS + EVAL_SEASONS
    outcomes = load_outcomes_score_only(outcomes_path, seasons)
    later = load_games(games_path, outcomes, seasons, phase="phase2_eval")
    # DEV history already in memory from phase1; concatenate for as-of chain
    history = list(phase1["history"]) + list(later)
    targets = window_rows(later, EVAL_SEASONS, EVAL_WEEKS)
    persist = {int(k) if not isinstance(k, int) else k: v for k, v in phase1["persist"].items()}
    feats = asof_for_targets(
        history,
        targets,
        phase1["lam"],
        phase1["regress_frac"],
        persist_season_end=persist,
    )
    feats = sorted(feats, key=lambda f: (f.game.kickoff_utc, f.game.game_id))
    targets_s = [f.game for f in feats]
    assert_asof_leakage(history, feats)
    wl, _ = _wl_series(targets_s, history)
    pack = _eval_stat_pack(feats, wl, phase1["fitted"], targets_s)
    pack["eval_rows_read"] = True
    pack["eval_seasons"] = list(EVAL_SEASONS)
    pack["history_only_seasons"] = list(HISTORY_ONLY_SEASONS)
    pack["n_history_2017"] = sum(1 for g in later if g.season == 2017)
    return pack


def render_frozen_md(cfg: dict) -> str:
    icc = cfg["dev_icc_home_team_season"]
    lines = [
        f"# FROZEN_CONFIG_Q2PB_t5009u — {LABEL}",
        "",
        f"**CERT=0 · NFL NO-GO · {LABEL} · no merge/deploy/pub/bet**",
        "",
        "Sealed **before** any EVAL 2018–22 row was read.",
        "",
        "## Identity",
        "",
        f"- ORDER tip `{TIP_ORDER}` · design `{TIP_DESIGN}` · eval spec `{TIP_EVAL_SPEC}`",
        f"- games.csv sha256 `{cfg['games_sha256']}` (prefix `{EXPECTED_GAMES_SHA256_PREFIX}`)",
        f"- outcomes extract sha256 `{cfg['outcomes_sha256']}`",
        f"- as-of rule `{TIP_ASOF_KICKOFF}` (kickoff < target)",
        f"- freeze timestamp (America/New_York): `{cfg['freeze_timestamp_america_new_york']}`",
        f"- fit object sha256: `{cfg['fit_object_sha256']}`",
        f"- config sha256: `{cfg['config_sha256']}`",
        "",
        "## Hyperparameters (DEV 2013–16 REG W2–17 only)",
        "",
        f"- λ = `{cfg['lam']}`",
        f"- regression fraction r = `{cfg['regress_frac']}`",
        f"- selection: {cfg['selection']}",
        "",
        "## Comparator / Q2 maps (DEV OLS / logistic)",
        "",
        f"- WL_MARGIN: pm_WL = {cfg['a']:.8f} + {cfg['b']:.8f} · wl_diff",
        f"- WL_WP: σ({cfg['c_WL']:.8f} + {cfg['d_WL']:.8f} · wl_diff)",
        f"- Q2: pm_new = {cfg['a_q2']:.8f} + {cfg['b_q2']:.8f} · rating_diff",
        f"- Q2 WP: P_new = σ({cfg['c']:.8f} + {cfg['d']:.8f} · pm_new)",
        f"- CONST_MARGIN = {cfg['const_margin']:.8f}",
        f"- CONST_WP = {cfg['const_wp']:.8f}",
        "",
        "## Fit counts",
        "",
        f"- n_fit = {cfg['n_fit']}",
        f"- n_ties_excluded = {cfg['n_ties_excluded']}",
        "",
        "## DEV screens (invention; not EVAL)",
        "",
        f"- Spearman ρ(rating_diff, m) = {cfg['dev_spearman_rho']:.6f}",
        f"- MAE(pm_new, m) = {cfg['dev_mae_pm_new']:.6f}",
        f"- MAE(WL_MARGIN, m) = {cfg['dev_mae_wl_margin']:.6f}",
        f"- MAE(CONST, m) = {cfg['dev_mae_const']:.6f}",
        f"- residual ICC (home team-season) = {icc.get('icc')} (k={icc.get('k')}, N={icc.get('N')}, n0={icc.get('n0')})",
        "",
        "## wl_diff",
        "",
        f"- column in games.csv: `{cfg['wl_diff_column_in_games_csv']}` (absent; mapping not definition)",
        f"- definition: {cfg['wl_diff_definition']}",
        f"- Pearson(recomputed, record_entering mapping) = {cfg['wl_recomputed_vs_record_entering_pearson']}",
        "",
        "## EPA / PBP",
        "",
        f"- {cfg['epa_status']}",
        f"- S1/EPA-trail revive: not attempted (kill {cfg.get('gated_index_1ee90fac')})",
        "",
        "## Outcome join",
        "",
        cfg["outcome_join_note"],
        "",
        "## Early-stop flags (DEV)",
        "",
        f"- early_stop = {cfg['early_stop']}",
        f"- rho < 0.10 = {cfg['early_stop_rho']}",
        f"- MAE_new ≥ MAE_WL = {cfg['early_stop_mae']}",
        f"- eval_rows_read at seal = {cfg['eval_rows_read']}",
        "",
        "No self-ACCEPT of keep. Result returns via Alex RO → CoS.",
        "",
    ]
    return "\n".join(lines)


def render_early_stop(cfg: dict) -> str:
    return "\n".join(
        [
            f"# DEV_EARLY_STOP_Q2PB_t5009u — {LABEL}",
            "",
            f"**CERT=0 · NFL NO-GO · {LABEL}**",
            "",
            "EVAL 2018–22 was **not** opened.",
            "",
            f"- DEV Spearman ρ = {cfg['dev_spearman_rho']:.6f} (gate ≥ +0.10)",
            f"- DEV MAE(pm_new) = {cfg['dev_mae_pm_new']:.6f}",
            f"- DEV MAE(WL_MARGIN) = {cfg['dev_mae_wl_margin']:.6f}",
            f"- rho_fail = {cfg['early_stop_rho']}",
            f"- mae_fail = {cfg['early_stop_mae']}",
            f"- fit_object_sha256 = `{cfg['fit_object_sha256']}`",
            f"- config_sha256 = `{cfg['config_sha256']}`",
            f"- freeze = {cfg['freeze_timestamp_america_new_york']}",
            "",
            "No self-ACCEPT. Alex RO → CoS.",
            "",
        ]
    )


def render_eval(cfg: dict, ev: dict) -> str:
    boot = ev["delta_mae_cluster_boot"]
    rho_b = ev["spearman_cluster_boot"]
    verdict = "KEEP_CANDIDATE (not self-ACCEPTED)" if ev["keep_all"] else "STOP_FAMILY"
    lines = [
        f"# EVAL_ONELOOK_Q2PB_t5009u — {LABEL}",
        "",
        f"**CERT=0 · NFL NO-GO · {LABEL} · k: 0→1 · no post-EVAL tuning**",
        "",
        f"## Verdict (reported, not accepted): **{verdict}**",
        "",
        "Keep requires ALL of 349e081e §6. This file does **not** self-ACCEPT.",
        "Next: Alex RO → CoS.",
        "",
        "## Identity",
        "",
        f"- frozen fit sha256 `{cfg['fit_object_sha256']}`",
        f"- frozen config sha256 `{cfg['config_sha256']}`",
        f"- freeze {cfg['freeze_timestamp_america_new_york']}",
        f"- λ={cfg['lam']} r={cfg['regress_frac']}",
        f"- n={ev['n']} n_ties={ev['n_ties']}",
        "",
        "## §6 keep gates",
        "",
        f"- Spearman ρ = {ev['spearman_rho']:.6f} (need ≥ +0.15)",
        f"- cluster bootstrap ρ CI = [{rho_b['ci_lo']:.6f}, {rho_b['ci_hi']:.6f}] (need lo>0)",
        f"- keep_rho = {ev['keep_rho']}",
        f"- ΔMAE (new−WL) = {ev['delta_mae_new_minus_wl']:.6f} (need improvement ⇒ mean<0)",
        f"- ΔMAE cluster CI = [{boot['ci_lo']:.6f}, {boot['ci_hi']:.6f}] (need hi<0)",
        f"- keep_mae = {ev['keep_mae']}",
        f"- kill Pearson corr(pm_new−pm_WL, m−pm_WL) = {ev['kill_pearson_corr']:.6f} (need >0)",
        f"- keep_kill = {ev['keep_kill']}",
        f"- post_eval_tuning = {ev['post_eval_tuning']}",
        f"- keep_all = {ev['keep_all']}",
        "",
        "## Prediction quality vs WL / constant",
        "",
        f"- MAE new/WL/const = {ev['mae_pm_new']:.6f} / {ev['mae_wl_margin']:.6f} / {ev['mae_const']:.6f}",
        f"- RMSE new/WL/const = {ev['rmse_pm_new']:.6f} / {ev['rmse_wl_margin']:.6f} / {ev['rmse_const']:.6f}",
        f"- ΔRMSE new−WL = {ev['delta_rmse_new_minus_wl']:.6f}; new−const = {ev['delta_rmse_new_minus_const']:.6f}",
        f"- Brier new/WL/const = {ev['brier_new']:.6f} / {ev['brier_wl_wp']:.6f} / {ev['brier_const']:.6f}",
        f"- ΔBrier new−WL = {ev['delta_brier_new_minus_wl']:.6f}; new−const = {ev['delta_brier_new_minus_const']:.6f}",
        "",
        "## Sensitivity",
        "",
        f"- week-cluster Spearman boot CI = [{ev['spearman_week_cluster_boot']['ci_lo']:.6f}, {ev['spearman_week_cluster_boot']['ci_hi']:.6f}]",
        f"- bootstrap B={int(boot['B'])} seed={int(boot['seed'])} n_clusters={int(boot['n_clusters'])}",
        "",
        "## Leave-one-season-out (sign stability; not a re-threshold)",
        "",
    ]
    for row in ev["loso"]:
        lines.append(
            f"- {row['season']}: n={row['n']} ρ={row['rho']:.4f} "
            f"ΔMAE={row['delta_mae']:.4f} kill={row['kill']:.4f}"
        )
    lines += [
        "",
        "## Prohibited (honored)",
        "",
        "- no 2017 / 2023 / 2024–25 in fits or EVAL rows (2017 history-only for 2018 prior)",
        f"- no scored reuse of hist index `{TIP_GATED_INDEX}` as experiment frame",
        "- no trailing_* / S1 / EPA-trail revive; EPA SKIPPED/UNAVAILABLE",
        "- no math/eval rule change; no merge/deploy/pub/bet",
        "",
        "No self-ACCEPT of keep. Alex RO → CoS.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="Q2 Phase B EXEC t5009u DEV_RESEARCH")
    p.add_argument(
        "--games",
        default=str(ROOT / "data" / "games_4fe1cdd7.csv"),
    )
    p.add_argument(
        "--outcomes",
        default=str(ROOT / "data" / "outcomes_2013_2022_score_only.csv"),
    )
    p.add_argument(
        "--out",
        default="/workspace/ops/nfl_enterprise_green_t4359u",
    )
    args = p.parse_args()
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    phase1 = phase1_dev(args)
    cfg = phase1["config"]
    _write_sealed(outdir / "FROZEN_CONFIG_Q2PB_t5009u.json", json.dumps(cfg, indent=2, sort_keys=True))
    _write_sealed(outdir / "FROZEN_CONFIG_Q2PB_t5009u.md", render_frozen_md(cfg))
    print(
        f"SEALED FROZEN_CONFIG fit={phase1['fit_sha'][:12]} "
        f"cfg={phase1['config_sha'][:12]} early_stop={phase1['early_stop']} "
        f"eval_rows_read={cfg['eval_rows_read']}"
    )

    if phase1["early_stop"]:
        _write_sealed(outdir / "DEV_EARLY_STOP_Q2PB_t5009u.md", render_early_stop(cfg))
        print("DEV_EARLY_STOP — EVAL not opened")
        return 0

    ev = phase2_eval(args, phase1)
    _write_sealed(outdir / "EVAL_ONELOOK_Q2PB_t5009u.json", json.dumps(ev, indent=2, sort_keys=True, default=str))
    _write_sealed(outdir / "EVAL_ONELOOK_Q2PB_t5009u.md", render_eval(cfg, ev))
    print(
        f"EVAL k=1 keep_all={ev['keep_all']} rho={ev['spearman_rho']:.4f} "
        f"dMAE={ev['delta_mae_new_minus_wl']:.4f} kill={ev['kill_pearson_corr']:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
