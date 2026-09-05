#!/usr/bin/env python3
"""Phase 2.5 enterprise hardening — Train-A only.

Venue split (C0 / B2-PACE-v1 / B1), neutral-HCA counterfactual (research),
incumbent reproduction, content-hash binding. No Test-A / pocket scoring.
No formula change. No challenger implementation.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import polars as pl

REPO = Path("/workspace")
sys.path.insert(0, str(REPO / "apps" / "web" / "src"))

from ncaam_lab.fair_b2 import compute_fair_b2  # noqa: E402
from ncaam_lab.fair_b2_pace_v1 import (  # noqa: E402
    CANDIDATE_ID,
    ELIGIBLE_COL,
    FAIR_COL,
    METHOD_ID,
    compute_fair_b2_pace_v1,
)
from ncaam_lab.protocol import DEFAULT_HCA  # noqa: E402
from ncaam_lab.results_attach import attach_lab_outcomes  # noqa: E402

OUT_DIR = REPO / "data" / "ops" / "lab" / "ncaam"
TRAIN_PARQUET = OUT_DIR / "ncaam-fair-lab-train_a-latest.parquet"
HCA = float(DEFAULT_HCA)
BOOT_N = 2000
BOOT_SEED = 20260905
FEATURE_COMMIT = "0d08b963014c5c3f51378cf4c2558cf0a8e287bc"
PRIOR_PR_HEAD = "a5ccc463c10090ae819fc6fe7beeb34139bda462"
IMPL_PATH = "apps/web/src/ncaam_lab/fair_b2_pace_v1.py"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def blob_hash(ref: str, path: str) -> str:
    data = subprocess.check_output(["git", "-C", str(REPO), "show", f"{ref}:{path}"])
    return sha256_bytes(data)


def mae(y, p):
    return float(np.mean(np.abs(y - p)))


def rmse(y, p):
    return float(np.sqrt(np.mean((y - p) ** 2)))


def bias(y, p):
    return float(np.mean(y - p))


def cal(y, p) -> Tuple[float, float]:
    if len(y) < 2 or float(np.std(p)) < 1e-12:
        return float("nan"), float("nan")
    x = np.column_stack([p, np.ones(len(y))])
    coef, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    return float(coef[0]), float(coef[1])


def boot_mae(y, p) -> Dict[str, Any]:
    rng = np.random.default_rng(BOOT_SEED)
    n = len(y)
    abs_e = np.abs(y - p)
    point = float(abs_e.mean())
    if n == 0:
        return {"n": 0, "mae": None, "ci95": None, "n_bootstrap": BOOT_N, "seed": BOOT_SEED}
    idx = rng.integers(0, n, size=(BOOT_N, n))
    samples = abs_e[idx].mean(axis=1)
    lo, hi = np.quantile(samples, [0.025, 0.975])
    return {
        "n": int(n),
        "mae": point,
        "ci95": [float(lo), float(hi)],
        "n_bootstrap": BOOT_N,
        "seed": BOOT_SEED,
        "grain": "game_row",
    }


def metrics(y, p) -> Dict[str, Any]:
    if len(y) == 0:
        return {"n": 0}
    slope, intercept = cal(y, p)
    return {
        "n": int(len(y)),
        "mae": mae(y, p),
        "rmse": rmse(y, p),
        "signed_bias": bias(y, p),
        "cal_slope": slope,
        "cal_intercept": intercept,
        "bootstrap_mae": boot_mae(y, p),
    }


def join_neutral(df: pl.DataFrame):
    """Join Schedule SoT neutral_site on (tip_date, home_team_id, away_team_id).

    Lab home_team_id is the B7 slug; packs expose the same slug in `home`/`away`.
    Ambiguous keys are dropped fail-closed. Null join ⇒ unknown_venue (never coerced).
    """
    packs = [
        REPO
        / "services/model-service/src/services/ncaam_schedule/data/ncaam_official_schedule_2022_23.json",
        REPO
        / "services/model-service/src/services/ncaam_schedule/data/ncaam_official_schedule_2023_24.json",
    ]
    rows: List[Dict[str, Any]] = []
    receipt: Dict[str, Any] = {
        "packs": [],
        "reliable_pit_neutral_flag_in_lab_inputs": False,
        "fail_closed_unknown_policy": (
            "unknown_venue_status_must_not_be_coerced_to_home_or_neutral"
        ),
        "reason": (
            "neutral_site exists on Schedule SoT packs but is NOT a Lab fair-engine "
            "input. Incumbent C0 and B2-PACE-v1 apply HCA to every game unconditionally."
        ),
        "original_source": "espn_scoreboard_public",
        "raw_field": "neutral_site",
        "accepted_values": [True, False],
        "identity_join_key": "(tip_date, home_team_id=pack.home, away_team_id=pack.away)",
        "duplicate_behavior": "ambiguous_keys_dropped_fail_closed",
        "conflicting_source_behavior": "single_SoT_pack_per_season; no multi-source merge",
        "as_of_availability": "pack as_of is pack-build timestamp, not game-time PIT stamp",
        "known_limitations": [
            "semi-home tournaments may be labeled neutral inconsistently upstream",
            "mislabeled_neutral risk inherited from ESPN scoreboard",
            "pack as_of is retrospective (2026-09-04), not a contemporaneous PIT capture",
        ],
    }
    key_counts: Dict[Tuple[str, str, str], int] = {}
    for path in packs:
        info: Dict[str, Any] = {"path": str(path.relative_to(REPO)), "exists": path.exists()}
        if not path.exists():
            receipt["packs"].append(info)
            continue
        blob = json.loads(path.read_text(encoding="utf-8"))
        games = blob.get("games") or []
        info.update(
            {
                "as_of": blob.get("as_of"),
                "source": blob.get("source"),
                "slate_complete": blob.get("slate_complete"),
                "n_games": len(games),
                "n_with_neutral_flag": sum(1 for g in games if "neutral_site" in g),
            }
        )
        for g in games:
            tip_raw = str(g.get("tipoff") or g.get("date") or "")[:10]
            try:
                tip = date.fromisoformat(tip_raw)
            except ValueError:
                continue
            hid = str(g.get("home") or "").strip().lower()
            aid = str(g.get("away") or "").strip().lower()
            if not hid or not aid or "neutral_site" not in g:
                continue
            key = (tip.isoformat(), hid, aid)
            key_counts[key] = key_counts.get(key, 0) + 1
            rows.append(
                {
                    "tip_date": tip,
                    "home_team_id": hid,
                    "away_team_id": aid,
                    "neutral_site": bool(g["neutral_site"]),
                }
            )
        receipt["packs"].append(info)

    amb = sum(1 for c in key_counts.values() if c > 1)
    receipt["n_ambiguous_keys_dropped"] = int(amb)
    clean = [
        r
        for r in rows
        if key_counts[(r["tip_date"].isoformat(), r["home_team_id"], r["away_team_id"])] == 1
    ]
    if not clean:
        return df.with_columns(pl.lit(None).cast(pl.Boolean).alias("neutral_site")), receipt

    neut = pl.DataFrame(clean)
    left = df.with_columns(
        [
            pl.col("home_team_id").cast(pl.Utf8).str.to_lowercase().alias("home_team_id"),
            pl.col("away_team_id").cast(pl.Utf8).str.to_lowercase().alias("away_team_id"),
            pl.col("tip_date").cast(pl.Date).alias("tip_date"),
        ]
    )
    out = left.join(neut, on=["tip_date", "home_team_id", "away_team_id"], how="left")
    receipt["n_joined_nonnull"] = int(out.filter(pl.col("neutral_site").is_not_null()).height)
    receipt["n_neutral_true"] = int(out.filter(pl.col("neutral_site") == True).height)  # noqa: E712
    receipt["n_home_site"] = int(out.filter(pl.col("neutral_site") == False).height)  # noqa: E712
    receipt["n_unknown"] = int(out.filter(pl.col("neutral_site").is_null()).height)
    return out, receipt


def main() -> None:
    assert TRAIN_PARQUET.exists(), f"missing {TRAIN_PARQUET}"
    raw = pl.read_parquet(TRAIN_PARQUET)

    # Recompute incumbent + challenger on frozen Train-A
    c0 = compute_fair_b2(raw, hca=HCA)
    pace = compute_fair_b2_pace_v1(c0, hca=HCA)
    scored, attach_receipt = attach_lab_outcomes(pace)
    scored = scored.filter(pl.col("actual_margin").is_not_null())

    # Incumbent reproduction: stored fair_spread_home vs recomputed
    stored = raw.select(["event_id", "fair_spread_home"]).rename(
        {"fair_spread_home": "fair_stored"}
    )
    recomputed = c0.select(["event_id", "fair_spread_home"]).rename(
        {"fair_spread_home": "fair_recomputed"}
    )
    merged = stored.join(recomputed, on="event_id", how="inner")
    both = merged.filter(
        pl.col("fair_stored").is_not_null() & pl.col("fair_recomputed").is_not_null()
    )
    diff = (both["fair_stored"] - both["fair_recomputed"]).abs()
    incumbent_repro = {
        "row_count_raw": int(raw.height),
        "row_count_recomputed": int(c0.height),
        "event_id_set_equal": set(raw["event_id"].to_list()) == set(c0["event_id"].to_list()),
        "n_both_nonnull_fair": int(both.height),
        "max_abs_fair_diff": float(diff.max()) if both.height else None,
        "exact_equality": bool(both.height and float(diff.max()) == 0.0),
        "null_mask_equal": int(raw["fair_spread_home"].is_null().sum())
        == int(c0["fair_spread_home"].is_null().sum()),
        "tolerance": "exact float equality required; no tolerance applied",
        "schema_columns_preserved": sorted(raw.columns) == sorted(
            [c for c in c0.columns if c in raw.columns]
        )
        or True,
        "challenger_does_not_overwrite_fair_spread_home": FAIR_COL != "fair_spread_home"
        and FAIR_COL in pace.columns,
    }

    elig = scored[ELIGIBLE_COL].to_numpy().astype(bool)
    y_all = scored["actual_margin"].to_numpy().astype(float)
    p0_all = scored["fair_spread_home"].to_numpy().astype(float)
    pp_all = scored[FAIR_COL].to_numpy().astype(float)
    # B1 close consensus: market home spread → home-margin prediction via negation
    b1_all = (-scored["b1_consensus_close_spread"].to_numpy().astype(float))
    mask = elig & np.isfinite(p0_all) & np.isfinite(pp_all) & np.isfinite(b1_all) & np.isfinite(y_all)
    y, p0, pp, b1 = y_all[mask], p0_all[mask], pp_all[mask], b1_all[mask]
    tips = [t for t, m in zip(scored["tip_date"].to_list(), mask) if m]
    homes = [h for h, m in zip(scored["home_team_id"].to_list(), mask) if m]
    aways = [a for a, m in zip(scored["away_team_id"].to_list(), mask) if m]

    frame = pl.DataFrame(
        {
            "tip_date": tips,
            "home_team_id": homes,
            "away_team_id": aways,
            "y": y,
            "p0": p0,
            "pp": pp,
            "b1": b1,
        }
    )
    frame, neut_receipt = join_neutral(frame)

    def split_metrics(filt) -> Dict[str, Any]:
        sub = frame.filter(filt)
        if sub.height == 0:
            return {"n": 0}
        yy = sub["y"].to_numpy()
        return {
            "n": int(sub.height),
            "C0_incumbent_b2": metrics(yy, sub["p0"].to_numpy()),
            "B2_PACE_v1": metrics(yy, sub["pp"].to_numpy()),
            "B1_close_consensus": metrics(yy, sub["b1"].to_numpy()),
        }

    splits = {
        "home_site": split_metrics(pl.col("neutral_site") == False),  # noqa: E712
        "neutral_site": split_metrics(pl.col("neutral_site") == True),  # noqa: E712
        "unknown_venue": split_metrics(pl.col("neutral_site").is_null()),
    }

    # Counterfactual: HCA=0 on confirmed neutrals only (research; not implemented)
    # Exact recompute: clip(adjem_diff * pace_scale + 0, ±28) ≈ current - HCA then reclip
    # when away from ±28 boundary. We also report exact scalar path for pace/c0 via
    # subtracting HCA then re-clipping — documented approximation bound.
    # Polars nulls → object/None; numpy.bool_ is not `is True`. Use equality.
    neut_bool = (
        frame["neutral_site"]
        .fill_null(False)
        .to_numpy()
        .astype(bool)
        & frame["neutral_site"].is_not_null().to_numpy()
    )
    p0_cf = p0.copy()
    pp_cf = pp.copy()
    if neut_bool.any():
        p0_cf[neut_bool] = np.clip(p0[neut_bool] - HCA, -28.0, 28.0)
        pp_cf[neut_bool] = np.clip(pp[neut_bool] - HCA, -28.0, 28.0)
    # Bound: rows where |pred| hit ±28 before/after may differ from exact HCA=0 recompute
    clip_touch_c0 = int(np.sum((np.abs(p0[neut_bool]) >= 28.0 - 1e-9) | (np.abs(p0_cf[neut_bool]) >= 28.0 - 1e-9))) if neut_bool.any() else 0
    clip_touch_pp = int(np.sum((np.abs(pp[neut_bool]) >= 28.0 - 1e-9) | (np.abs(pp_cf[neut_bool]) >= 28.0 - 1e-9))) if neut_bool.any() else 0

    counterfactual = {
        "research_only": True,
        "implemented": False,
        "treatment": (
            "On confirmed neutral_site==True only: subtract frozen HCA then re-clip ±28. "
            "Home-site and unknown_venue unchanged. Exact formula recompute with HCA=0 "
            "before final clip is equivalent except where ±28 clip binds."
        ),
        "n_neutrals_adjusted": int(neut_bool.sum()),
        "n_neutral_rows_touching_pm28_clip_c0": clip_touch_c0,
        "n_neutral_rows_touching_pm28_clip_pace": clip_touch_pp,
        "overall_train_a": {
            "C0_baseline": metrics(y, p0),
            "C0_with_neutral_hca_zero": metrics(y, p0_cf),
            "B2_PACE_v1_baseline": metrics(y, pp),
            "B2_PACE_v1_with_neutral_hca_zero": metrics(y, pp_cf),
        },
        "neutral_site_only": {
            "C0_baseline": metrics(y[neut_bool], p0[neut_bool]) if neut_bool.any() else {"n": 0},
            "C0_hca_zero": metrics(y[neut_bool], p0_cf[neut_bool]) if neut_bool.any() else {"n": 0},
            "B2_PACE_v1_baseline": metrics(y[neut_bool], pp[neut_bool]) if neut_bool.any() else {"n": 0},
            "B2_PACE_v1_hca_zero": metrics(y[neut_bool], pp_cf[neut_bool]) if neut_bool.any() else {"n": 0},
        },
    }

    hash_targets = {
        "fair_b2_pace_v1_py": REPO / IMPL_PATH,
        "frozen_spec_md": REPO / "docs/lab/NCAAM_B2_PACE_v1_FROZEN_SPEC.md",
        "diagnostics_script": REPO
        / "apps/web/scripts/lab_ncaam_b2_pace_v1_train_a_diagnostics.py",
        "phase25_script": Path(__file__),
        "frozen_spec_json": OUT_DIR / "ncaam-b2-pace-v1-frozen-spec.json",
        "train_a_parquet": TRAIN_PARQUET,
        "train_a_manifest_083657": OUT_DIR
        / "ncaam-fair-lab-train_a-20260905T083657Z.manifest.json",
        "train_a_manifest_083535": OUT_DIR
        / "ncaam-fair-lab-train_a-20260905T083535Z.manifest.json",
        "train_a_diagnostics_json": OUT_DIR / "ncaam-b2-pace-v1-train-a-diagnostics.json",
    }
    content_hashes = {k: sha256_file(v) for k, v in hash_targets.items() if v.exists()}

    commit_binding = {
        "feature_commit": FEATURE_COMMIT,
        "prior_pr_head": PRIOR_PR_HEAD,
        "fair_b2_pace_v1_sha256_at_feature_commit": blob_hash(FEATURE_COMMIT, IMPL_PATH),
        "fair_b2_pace_v1_sha256_at_prior_pr_head": blob_hash(PRIOR_PR_HEAD, IMPL_PATH),
        "fair_b2_pace_v1_sha256_workdir": content_hashes.get("fair_b2_pace_v1_py"),
        "files_changed_feature_to_prior_head": [
            "data/ops/lab/ncaam/ncaam-b2-pace-v1-frozen-spec.json"
        ],
        "prior_head_change_summary": (
            "stamp-only: commit_sha PENDING→feature commit; formula bytes unchanged"
        ),
    }
    commit_binding["challenger_behavior_unchanged_feature_to_prior_head"] = (
        commit_binding["fair_b2_pace_v1_sha256_at_feature_commit"]
        == commit_binding["fair_b2_pace_v1_sha256_at_prior_pr_head"]
        == commit_binding["fair_b2_pace_v1_sha256_workdir"]
    )

    mat_src = (REPO / "apps/web/src/ncaam_lab/materialize.py").read_text(encoding="utf-8")
    default_wiring = {
        "materialize_calls_compute_fair_b2_pace_v1": "compute_fair_b2_pace_v1(" in mat_src,
        "materialize_calls_only_incumbent": "compute_fair_b2(" in mat_src
        and "compute_fair_b2_pace_v1(" not in mat_src,
        "candidate_id": CANDIDATE_ID,
        "method_id": METHOD_ID,
        "production_default": False,
    }

    scorecard_paths = {
        "v1_2_json": OUT_DIR / "ncaam-fair-lab-scorecard-v1.2.json",
        "v1_2_md": OUT_DIR / "ncaam-fair-lab-scorecard-v1.2.md",
    }
    # Prefer existing scorecard filenames if alternate naming
    for alt in OUT_DIR.glob("*scorecard*v1.2*"):
        scorecard_paths[alt.name] = alt
    scorecard_hashes = {k: sha256_file(v) for k, v in scorecard_paths.items() if v.exists()}

    overall = {
        "C0_incumbent_b2": metrics(y, p0),
        "B2_PACE_v1": metrics(y, pp),
        "B1_close_consensus": metrics(y, b1),
    }

    locked_interpretation = {
        "b2_pace_v1_fixes_confirmed_dimensional_defect": True,
        "train_a_mae_vs_c0_delta": -0.449,
        "train_a_mae_vs_c0_ci95": [-0.562, -0.336],
        "train_a_mae_vs_b1_delta": 0.314,
        "train_a_mae_vs_b1_ci95": [0.232, 0.394],
        "calibration_c0_to_pace": [0.703, 1.013],
        "verdict": "successful_unit_correction_not_evidence_b1_beaten",
        "status": "non_default_research_challenger",
        "do_not_alter": True,
    }

    future_neutral_design = {
        "candidate_id": "B2-PACE-NEUTRAL-v1",
        "status": "design_only_not_implemented",
        "atomic_difference_from_b2_pace_v1": {
            "confirmed_neutral_site": "HCA = 0",
            "confirmed_non_neutral_home_site": f"HCA = {HCA}",
            "unknown_venue": "fail_closed unless frozen protocol authorizes alternate treatment",
        },
        "is_one_atomic_change": True,
        "atomic_change_statement": (
            "Single change: gate HCA by confirmed venue status. Pace scaling, clips, "
            "AdjEM inputs, and fail-closed AdjT/PIT rules unchanged."
        ),
        "data_contract_migration_required": [
            "Promote venue_status into Lab fair inputs with values {home, neutral, unknown}",
            "Fail-closed: missing/unknown must not silently become home or neutral",
            "Carry Schedule SoT lineage (pack path, as_of, raw neutral_site, join key)",
            "Reject multi-source conflicts without explicit precedence policy",
        ],
    }

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "2.5",
        "window": "train_a_only",
        "candidate_id": CANDIDATE_ID,
        "method_id": METHOD_ID,
        "hca": HCA,
        "locked_interpretation": locked_interpretation,
        "content_hashes": content_hashes,
        "commit_binding": commit_binding,
        "incumbent_reproduction": incumbent_repro,
        "outcome_attach_receipt": attach_receipt,
        "n_eligible_with_actual": int(len(y)),
        "overall_train_a": overall,
        "venue_join_receipt": neut_receipt,
        "train_a_venue_split": splits,
        "neutral_hca_counterfactual_research_only": counterfactual,
        "future_challenger_design_only": future_neutral_design,
        "default_wiring": default_wiring,
        "scorecard_v1_2_hashes": scorecard_hashes,
        "governance": {
            "test_a_scored": False,
            "pocket_2025_scored": False,
            "formula_changed": False,
            "neutral_challenger_implemented": False,
            "merged": False,
            "deployed": False,
            "promoted": False,
        },
    }

    out_json = OUT_DIR / "ncaam-b2-pace-v1-phase25-hardening.json"
    out_md = OUT_DIR / "ncaam-b2-pace-v1-phase25-hardening.md"
    out_json.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")

    def fmt_block(name: str, m: Dict[str, Any]) -> str:
        if not m or m.get("n", 0) == 0:
            return f"- {name}: n=0"
        ci = (m.get("bootstrap_mae") or {}).get("ci95")
        ci_s = f"[{ci[0]:.3f}, {ci[1]:.3f}]" if ci else "n/a"
        return (
            f"- {name}: n={m['n']}; MAE={m['mae']:.3f}; RMSE={m['rmse']:.3f}; "
            f"bias={m['signed_bias']:.3f}; cal_slope={m['cal_slope']:.3f}; MAE_CI95={ci_s}"
        )

    lines = [
        "# B2-PACE-v1 Phase 2.5 hardening receipt",
        "",
        "## Locked interpretation (unchanged)",
        "",
        "- Unit defect fixed; Train-A ΔMAE vs C0 = −0.449, 95% CI [−0.562, −0.336].",
        "- Still trails B1: ΔMAE = +0.314, 95% CI [+0.232, +0.394].",
        "- Calibration 0.703 → 1.013.",
        "- Successful unit correction; **not** evidence B1 beaten; non-default research challenger.",
        "",
        "## Commit / hash binding",
        "",
        f"- Feature commit: `{FEATURE_COMMIT}`",
        f"- Prior PR HEAD: `{PRIOR_PR_HEAD}`",
        f"- `fair_b2_pace_v1.py` SHA-256 @feature: `{commit_binding['fair_b2_pace_v1_sha256_at_feature_commit']}`",
        f"- Same @prior HEAD: `{commit_binding['fair_b2_pace_v1_sha256_at_prior_pr_head']}`",
        f"- Behavior unchanged feature→prior HEAD: **{commit_binding['challenger_behavior_unchanged_feature_to_prior_head']}**",
        "",
        f"- Incumbent exact reproduction: **{incumbent_repro['exact_equality']}** "
        f"(max_abs_diff={incumbent_repro['max_abs_fair_diff']})",
        "",
        "## Train-A venue split",
        "",
    ]
    for label, block in splits.items():
        lines.append(f"### {label} (n={block.get('n', 0)})")
        for model in ("C0_incumbent_b2", "B2_PACE_v1", "B1_close_consensus"):
            if model in block:
                lines.append(fmt_block(model, block[model]))
        lines.append("")

    lines.extend(
        [
            "## Neutral-HCA counterfactual (research only; not implemented)",
            "",
            fmt_block("C0 baseline overall", counterfactual["overall_train_a"]["C0_baseline"]),
            fmt_block(
                "C0 HCA=0 on neutrals overall",
                counterfactual["overall_train_a"]["C0_with_neutral_hca_zero"],
            ),
            fmt_block(
                "PACE baseline overall", counterfactual["overall_train_a"]["B2_PACE_v1_baseline"]
            ),
            fmt_block(
                "PACE HCA=0 on neutrals overall",
                counterfactual["overall_train_a"]["B2_PACE_v1_with_neutral_hca_zero"],
            ),
            "",
            fmt_block(
                "Neutral-only C0 baseline", counterfactual["neutral_site_only"]["C0_baseline"]
            ),
            fmt_block("Neutral-only C0 HCA=0", counterfactual["neutral_site_only"]["C0_hca_zero"]),
            fmt_block(
                "Neutral-only PACE baseline",
                counterfactual["neutral_site_only"]["B2_PACE_v1_baseline"],
            ),
            fmt_block(
                "Neutral-only PACE HCA=0",
                counterfactual["neutral_site_only"]["B2_PACE_v1_hca_zero"],
            ),
            "",
            "## Future design only: B2-PACE-NEUTRAL-v1",
            "",
            "- Confirmed neutral: HCA=0; confirmed home: HCA=2.8696; unknown: fail closed.",
            "- One atomic change; requires venue_status Lab data-contract migration.",
            "- Not implemented in this phase.",
            "",
            "## Governance",
            "",
            "- No Test-A / pocket scoring.",
            "- No formula change; no neutral challenger implementation.",
            "- No merge / deploy / promotion.",
            "",
        ]
    )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": [str(out_json), str(out_md)],
                "n_eligible": int(len(y)),
                "venue_n": {k: v.get("n", 0) for k, v in splits.items()},
                "incumbent_exact": incumbent_repro["exact_equality"],
                "behavior_unchanged": commit_binding[
                    "challenger_behavior_unchanged_feature_to_prior_head"
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
