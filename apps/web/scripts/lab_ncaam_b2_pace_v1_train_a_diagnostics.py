#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import polars as pl

REPO = Path("/workspace")
sys.path.insert(0, str(REPO / "apps" / "web" / "src"))

from ncaam_lab.fair_b2 import compute_fair_b2
from ncaam_lab.fair_b2_pace_v1 import (
    CANDIDATE_ID,
    ELIGIBLE_COL,
    FAIR_COL,
    METHOD_ID,
    compute_fair_b2_pace_v1,
)
from ncaam_lab.protocol import DEFAULT_HCA
from ncaam_lab.results_attach import attach_lab_outcomes

OUT_DIR = REPO / "data" / "ops" / "lab" / "ncaam"
TRAIN_PARQUET = OUT_DIR / "ncaam-fair-lab-train_a-latest.parquet"
HCA = float(DEFAULT_HCA)
BOOT_N = 2000
BOOT_SEED = 20260905


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mae(y, p):
    return float(np.mean(np.abs(y - p)))


def rmse(y, p):
    return float(np.sqrt(np.mean((y - p) ** 2)))


def bias(y, p):
    return float(np.mean(y - p))


def cal(y, p):
    x = np.column_stack([p, np.ones(len(p))])
    coef, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    return float(coef[0]), float(coef[1])


def paired_boot(y, pred_a, pred_b):
    rng = np.random.default_rng(BOOT_SEED)
    n = len(y)
    abs_a = np.abs(y - pred_a)
    abs_b = np.abs(y - pred_b)
    point = float(abs_a.mean() - abs_b.mean())
    idx = rng.integers(0, n, size=(BOOT_N, n))
    deltas = abs_a[idx].mean(axis=1) - abs_b[idx].mean(axis=1)
    lo, hi = np.quantile(deltas, [0.025, 0.975])
    return {
        "grain": "game_row",
        "n_games": int(n),
        "n_bootstrap": BOOT_N,
        "seed": BOOT_SEED,
        "point_delta_mae_a_minus_b": point,
        "ci95": [float(lo), float(hi)],
        "share_delta_lt_0": float(np.mean(deltas < 0.0)),
    }


def join_neutral(df: pl.DataFrame):
    packs = [
        REPO / "services/model-service/src/services/ncaam_schedule/data/ncaam_official_schedule_2022_23.json",
        REPO / "services/model-service/src/services/ncaam_schedule/data/ncaam_official_schedule_2023_24.json",
    ]
    rows = []
    receipt = {
        "packs": [],
        "reliable_pit_neutral_flag_in_lab_inputs": False,
        "reason": (
            "neutral_site exists on Schedule SoT packs but is NOT a Lab fair-engine "
            "input. Incumbent C0 applies HCA to every game unconditionally."
        ),
    }
    for path in packs:
        info = {"path": str(path.relative_to(REPO)), "exists": path.exists()}
        if not path.exists():
            receipt["packs"].append(info)
            continue
        games = json.loads(path.read_text(encoding="utf-8")).get("games") or []
        kept = 0
        for g in games:
            tip_raw = (g.get("tipoff") or g.get("kickoff") or g.get("date") or "")[:10]
            try:
                tip = date.fromisoformat(tip_raw)
            except ValueError:
                continue
            hid, aid = g.get("home"), g.get("away")
            if not hid or not aid or "neutral_site" not in g:
                continue
            rows.append(
                {
                    "tip_date": tip,
                    "home_team_id": str(hid),
                    "away_team_id": str(aid),
                    "neutral_site": bool(g["neutral_site"]),
                }
            )
            kept += 1
        info["n_games"] = len(games)
        info["n_with_neutral_flag"] = kept
        receipt["packs"].append(info)

    if not rows:
        return df.with_columns(pl.lit(None).cast(pl.Boolean).alias("neutral_site")), receipt

    neut = pl.DataFrame(rows)
    counts = neut.group_by(["tip_date", "home_team_id", "away_team_id"]).len()
    amb = counts.filter(pl.col("len") > 1).select(["tip_date", "home_team_id", "away_team_id"])
    receipt["n_ambiguous_keys_dropped"] = int(amb.height)
    if amb.height:
        neut = neut.join(amb, on=["tip_date", "home_team_id", "away_team_id"], how="anti")
    neut = neut.unique(subset=["tip_date", "home_team_id", "away_team_id"], keep="first")
    out = df.join(neut, on=["tip_date", "home_team_id", "away_team_id"], how="left")
    receipt["n_joined_nonnull"] = int(out.filter(pl.col("neutral_site").is_not_null()).height)
    receipt["n_neutral_true"] = int(out.filter(pl.col("neutral_site") == True).height)  # noqa: E712
    receipt["n_home_site"] = int(out.filter(pl.col("neutral_site") == False).height)  # noqa: E712
    receipt["n_unknown"] = int(out.filter(pl.col("neutral_site").is_null()).height)
    return out, receipt


def main():
    lab = pl.read_parquet(TRAIN_PARQUET)
    n_lab = len(lab)
    coverage = {
        "n_lab": n_lab,
        "n_with_both_adjem": int(lab.filter(pl.col("adjem_home").is_not_null() & pl.col("adjem_away").is_not_null()).height),
        "n_with_both_adjt_positive": int(lab.filter(
            pl.col("adjt_home").is_not_null() & pl.col("adjt_away").is_not_null() & (pl.col("adjt_home") > 0) & (pl.col("adjt_away") > 0)
        ).height),
        "n_with_valid_pit_asof": int(lab.filter(
            pl.col("kenpom_as_of_home").is_not_null() & pl.col("kenpom_as_of_away").is_not_null()
            & (pl.col("kenpom_as_of_home") <= pl.col("tip_date")) & (pl.col("kenpom_as_of_away") <= pl.col("tip_date"))
        ).height),
        "n_missing_adjt_either_side": int(lab.filter(
            pl.col("adjt_home").is_null() | pl.col("adjt_away").is_null() | (pl.col("adjt_home") <= 0) | (pl.col("adjt_away") <= 0)
        ).height),
        "fail_closed_on_missing_adjt": True,
        "national_average_tempo_fallback": False,
    }

    pace = compute_fair_b2_pace_v1(lab, hca=HCA)
    coverage["n_b2_pace_v1_eligible"] = int(pace.filter(pl.col(ELIGIBLE_COL)).height)
    coverage["b2_pace_v1_eligibility_rate"] = round(coverage["n_b2_pace_v1_eligible"] / n_lab, 6)

    scored, attach_receipt = attach_lab_outcomes(pace)
    scored = scored.filter(pl.col("actual_margin").is_not_null())
    scored = compute_fair_b2(scored, hca=HCA)

    dup = scored.group_by("event_id").len().filter(pl.col("len") > 1)
    grain = {
        "bootstrap_resample_grain": "game_row",
        "n_rows_with_actual": len(scored),
        "n_unique_event_id": int(scored["event_id"].n_unique()),
        "n_duplicate_event_id_groups": int(dup.height),
        "repeated_event_ids_impossible_in_this_frame": dup.height == 0,
    }

    elig = scored[ELIGIBLE_COL].to_numpy().astype(bool)
    y_all = scored["actual_margin"].to_numpy()
    p0_all = scored["fair_spread_home"].to_numpy()
    pp_all = scored[FAIR_COL].to_numpy()
    b1_all = (-scored["b1_consensus_close_spread"]).to_numpy()
    tips_all = scored["tip_date"].to_list()
    homes_all = scored["home_team_id"].to_list()
    aways_all = scored["away_team_id"].to_list()
    mask = elig & np.isfinite(p0_all) & np.isfinite(pp_all) & np.isfinite(b1_all)
    y, p0, pp, b1 = y_all[mask], p0_all[mask], pp_all[mask], b1_all[mask]
    tips = [t for t, m in zip(tips_all, mask) if m]
    homes = [h for h, m in zip(homes_all, mask) if m]
    aways = [a for a, m in zip(aways_all, mask) if m]

    def metrics(pred):
        slope, intercept = cal(y, pred)
        return {"n": int(len(y)), "mae": mae(y, pred), "rmse": rmse(y, pred), "signed_bias": bias(y, pred), "cal_slope": slope, "cal_intercept": intercept}

    overall = {
        "C0_incumbent_b2": metrics(p0),
        "B2_PACE_v1": metrics(pp),
        "B1_close_consensus": metrics(b1),
    }
    boot_c0 = paired_boot(y, pp, p0); boot_c0["definition"] = "MAE(B2-PACE-v1) - MAE(C0)"
    boot_b1 = paired_boot(y, pp, b1); boot_b1["definition"] = "MAE(B2-PACE-v1) - MAE(B1)"

    months = sorted({(t.year, t.month) for t in tips})
    monthly = []
    for yy, mm in months:
        msk = np.array([t.year == yy and t.month == mm for t in tips])
        monthly.append({"month": f"{yy:04d}-{mm:02d}", "n": int(msk.sum()), "mae_c0": mae(y[msk], p0[msk]), "mae_b2_pace_v1": mae(y[msk], pp[msk]), "mae_b1": mae(y[msk], b1[msk])})

    folds = []
    for i in range(1, len(months)):
        yy, mm = months[i]
        test_start = date(yy, mm, 1)
        train_end = test_start - timedelta(days=1)
        test_end = date(yy, 12, 31) if mm == 12 else date(yy, mm + 1, 1) - timedelta(days=1)
        te = np.array([test_start <= t <= test_end for t in tips])
        tr = np.array([t <= train_end for t in tips])
        if int(te.sum()) < 30 or int(tr.sum()) < 50:
            continue
        folds.append({
            "fold": f"roll_{yy:04d}-{mm:02d}",
            "train_end": train_end.isoformat(),
            "test_start": test_start.isoformat(),
            "test_end": test_end.isoformat(),
            "n_train_prior_rows": int(tr.sum()),
            "n_test": int(te.sum()),
            "mae_c0": mae(y[te], p0[te]),
            "mae_b2_pace_v1": mae(y[te], pp[te]),
            "mae_b1": mae(y[te], b1[te]),
            "rmse_c0": rmse(y[te], p0[te]),
            "rmse_b2_pace_v1": rmse(y[te], pp[te]),
            "rmse_b1": rmse(y[te], b1[te]),
            "bias_c0": bias(y[te], p0[te]),
            "bias_b2_pace_v1": bias(y[te], pp[te]),
            "bias_b1": bias(y[te], b1[te]),
        })

    frame = pl.DataFrame({"tip_date": tips, "home_team_id": homes, "away_team_id": aways, "y": y, "p0": p0, "pp": pp})
    frame, neut_receipt = join_neutral(frame)

    def split_bias(filt):
        sub = frame.filter(filt)
        if len(sub) == 0:
            return {"n": 0}
        yy = sub["y"].to_numpy()
        return {
            "n": len(sub),
            "c0_signed_bias": bias(yy, sub["p0"].to_numpy()),
            "b2_pace_v1_signed_bias": bias(yy, sub["pp"].to_numpy()),
            "c0_mae": mae(yy, sub["p0"].to_numpy()),
            "b2_pace_v1_mae": mae(yy, sub["pp"].to_numpy()),
        }

    hca_audit = {
        "hca_value": HCA,
        "c0_applies_hca_to_all_games": True,
        "c0_neutral_site_branch_exists": False,
        "b2_pace_v1_changes_neutral_treatment": False,
        "neutral_join_receipt": neut_receipt,
        "train_a_bias_split": {
            "home_site": split_bias(pl.col("neutral_site") == False),
            "neutral_site": split_bias(pl.col("neutral_site") == True),
            "unknown_site": split_bias(pl.col("neutral_site").is_null()),
        },
        "known_limitation": "Neutral games currently receive HCA under both C0 and B2-PACE-v1. Fixing that is a separate future atomic challenger.",
        "future_challenger_stub": {"candidate_id": "B2-NEUTRAL-HCA-v1", "status": "registered_not_implemented"},
    }

    recon = ((scored["adjem_home"] - scored["adjem_away"]).clip(-30, 30) + HCA).clip(-28, 28)
    incumbent_parity = {
        "max_abs_fair_minus_recon": float((scored["fair_spread_home"] - recon).abs().max()),
        "challenger_does_not_overwrite_fair_spread_home": True,
    }

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_id": CANDIDATE_ID,
        "method_id": METHOD_ID,
        "research_alias": "C3",
        "window": "train_a_only",
        "hca": HCA,
        "formula": {
            "adjem_diff": "clip(home_adjem - away_adjem, -30, +30)",
            "expected_possessions": "(home_adjt + away_adjt) / 2",
            "raw_home_margin": "adjem_diff * (expected_possessions / 100) + 2.8696",
            "fair_home_margin": "clip(raw_home_margin, -28, +28)",
            "sign_convention": "positive fair_spread_home => home predicted to win by that many points",
        },
        "input_manifest": {
            "train_parquet": str(TRAIN_PARQUET.relative_to(REPO)),
            "train_parquet_sha256": sha256_file(TRAIN_PARQUET),
        },
        "coverage_missingness": coverage,
        "outcome_attach": attach_receipt,
        "bootstrap_grain": grain,
        "overall_train_a_eligible": overall,
        "paired_bootstrap": {"b2_pace_v1_minus_c0": boot_c0, "b2_pace_v1_minus_b1": boot_b1},
        "monthly_mae": monthly,
        "rolling_origin_folds": folds,
        "hca_neutral_audit": hca_audit,
        "incumbent_parity": incumbent_parity,
        "selection_rationale": "Chosen for game-specific PIT-tempo coherence versus fixed-tempo C1 (~0.002 MAE); not a claim of statistical superiority over C1.",
        "governance": {
            "test_a_scored": False,
            "pocket_2025_scored": False,
            "open_shrink_run": False,
            "board_play": False,
            "gate_changes": False,
            "production_default_changed": False,
        },
    }

    out_json = OUT_DIR / "ncaam-b2-pace-v1-train-a-diagnostics.json"
    out_md = OUT_DIR / "ncaam-b2-pace-v1-train-a-diagnostics.md"
    out_json.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")

    lines = [
        "# B2-PACE-v1 Train-A diagnostics",
        "",
        f"Candidate: `{CANDIDATE_ID}` / `{METHOD_ID}` (research alias C3)",
        f"HCA frozen: `{HCA}`",
        f"n eligible with actual: `{len(y)}`",
        "",
        "## Coverage",
        "",
        f"- Lab rows: {coverage['n_lab']}",
        f"- B2-PACE-v1 eligible: {coverage['n_b2_pace_v1_eligible']} ({coverage['b2_pace_v1_eligibility_rate']})",
        f"- Missing/invalid AdjT either side: {coverage['n_missing_adjt_either_side']}",
        "",
        "## Paired bootstrap (game grain)",
        "",
        f"- MAE(B2-PACE-v1)-MAE(C0): {boot_c0['point_delta_mae_a_minus_b']:.4f} 95% CI {boot_c0['ci95']}",
        f"- MAE(B2-PACE-v1)-MAE(B1): {boot_b1['point_delta_mae_a_minus_b']:.4f} 95% CI {boot_b1['ci95']}",
        "",
        "## Monthly MAE",
        "",
        "| month | n | C0 | B2-PACE-v1 | B1 |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in monthly:
        lines.append(f"| {r['month']} | {r['n']} | {r['mae_c0']:.4f} | {r['mae_b2_pace_v1']:.4f} | {r['mae_b1']:.4f} |")
    lines += ["", "## Rolling-origin folds", "", "| fold | n_test | C0 | B2-PACE-v1 | B1 |", "|---|---:|---:|---:|---:|"]
    for r in folds:
        lines.append(f"| {r['fold']} | {r['n_test']} | {r['mae_c0']:.4f} | {r['mae_b2_pace_v1']:.4f} | {r['mae_b1']:.4f} |")
    lines += [
        "",
        "Test-A is development-exposed for this unit-correction family and is not an untouched confirmation set.",
        "",
        "No Test-A or 2025 pocket performance was scored in this run.",
        "",
    ]
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": [str(out_json), str(out_md)], "n": len(y), "coverage": coverage, "boot_c0": boot_c0, "boot_b1": boot_b1, "overall": overall}, indent=2))


if __name__ == "__main__":
    main()
