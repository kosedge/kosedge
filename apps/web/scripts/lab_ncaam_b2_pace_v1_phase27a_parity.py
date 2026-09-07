#!/usr/bin/env python3
"""Phase 2.7A — B2-PACE-v1 reconciliation parity + integration receipt.

Compares current worktree impl vs original frozen formula bytes (content-hash
ae5a34cdc7…) across Train-A valid-domain rows. Append-only receipt; does NOT
rewrite Phase 2.5 diagnostics. No holdout scoring / unseal / default wiring.
"""
from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import math
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import polars as pl

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "apps" / "web" / "src"))

from ncaam_lab.fair_b2 import compute_fair_b2  # noqa: E402
from ncaam_lab.fair_b2_pace_v1 import (  # noqa: E402
    CANDIDATE_ID,
    ELIGIBLE_COL,
    FAIR_COL,
    FROZEN_HCA,
    HCA_COL,
    METHOD_ID,
    compute_fair_b2_pace_v1,
)
from ncaam_lab.materialize import materialize_lab_fair  # noqa: E402
from ncaam_lab.protocol import DEFAULT_HCA  # noqa: E402

OUT_DIR = REPO / "data" / "ops" / "lab" / "ncaam"
TRAIN_PARQUET = OUT_DIR / "ncaam-fair-lab-train_a-latest.parquet"
IMPL_PATH = "apps/web/src/ncaam_lab/fair_b2_pace_v1.py"
# Original frozen implementation content hash (Phase 2.5 / generating commit).
OLD_IMPL_SHA256 = "ae5a34cdc7a2d5324fe4b372e31820464c5f385fffba7583ff5ffa43cb123707"
# Exact historical Phase 2.7A production base (preserved forever in receipts).
PRODUCTION_BASE = "beae001342cdd15ad929e53783e6973530ffda44"
# Live acceptance tip is recorded separately when HEAD has restacked past PRODUCTION_BASE.
ACCEPTANCE_BASE_REF = "origin/deploy-vercel"
# Generating commit that first shipped the frozen formula (pre-rebase OID).
ORIGINATING_COMMIT_PRE_REBASE = "0d08b963014c5c3f51378cf4c2558cf0a8e287bc"
HOLDOUT_FOUNDATION_ID = "ncaam_holdout_2024_25_v1_1"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_show(ref: str, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{ref}:{path}"])


def git_rev_parse(ref: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPO), "rev-parse", ref], text=True
    ).strip()


def load_module_from_bytes(name: str, source: bytes):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / f"{name}.py"
        p.write_bytes(source)
        spec = importlib.util.spec_from_file_location(name, p)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        # Ensure sibling imports resolve against web src.
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod


def main() -> None:
    assert TRAIN_PARQUET.exists(), f"missing {TRAIN_PARQUET}"
    head = git_rev_parse("HEAD")
    base = git_rev_parse(PRODUCTION_BASE)
    merge_base = subprocess.check_output(
        ["git", "-C", str(REPO), "merge-base", "HEAD", PRODUCTION_BASE], text=True
    ).strip()
    assert merge_base == base, f"HEAD must descend from historical {PRODUCTION_BASE}; got {merge_base}"
    try:
        acceptance_base = git_rev_parse(ACCEPTANCE_BASE_REF)
    except subprocess.CalledProcessError:
        acceptance_base = None
    acceptance_merge_base = None
    behind_acceptance = None
    if acceptance_base:
        acceptance_merge_base = subprocess.check_output(
            ["git", "-C", str(REPO), "merge-base", "HEAD", acceptance_base], text=True
        ).strip()
        behind_acceptance = int(
            subprocess.check_output(
                ["git", "-C", str(REPO), "rev-list", "--count", f"HEAD..{acceptance_base}"],
                text=True,
            ).strip()
        )

    new_bytes = (REPO / IMPL_PATH).read_bytes()
    new_sha = sha256_bytes(new_bytes)
    # Prefer pre-rebase originating blob; fall back to post-rebase generating commit.
    old_bytes = None
    old_ref_used = None
    candidate_refs = [ORIGINATING_COMMIT_PRE_REBASE]
    # Post-rebase generating commit on this branch (first parent chain tip^2..).
    log = subprocess.check_output(
        ["git", "-C", str(REPO), "log", "--pretty=%H", "--", IMPL_PATH],
        text=True,
    ).splitlines()
    candidate_refs.extend(log)
    seen = set()
    for ref in candidate_refs:
        if ref in seen:
            continue
        seen.add(ref)
        try:
            cand = git_show(ref, IMPL_PATH)
        except subprocess.CalledProcessError:
            continue
        if sha256_bytes(cand) == OLD_IMPL_SHA256:
            old_bytes = cand
            old_ref_used = ref
            break
    assert old_bytes is not None, "could not locate original frozen impl bytes"
    old_sha = sha256_bytes(old_bytes)
    assert old_sha == OLD_IMPL_SHA256

    old_mod = load_module_from_bytes("fair_b2_pace_v1_frozen_old", old_bytes)

    raw = pl.read_parquet(TRAIN_PARQUET)
    c0 = compute_fair_b2(raw, hca=float(DEFAULT_HCA))
    new_df = compute_fair_b2_pace_v1(c0)  # omit hca → frozen pin
    # Old API accepted hca=; pass exact frozen value for apples-to-apples.
    old_df = old_mod.compute_fair_b2_pace_v1(c0, hca=float(DEFAULT_HCA))

    # Valid-domain: old eligible rows with finite fair under both.
    joined = old_df.select(
        [
            "event_id",
            pl.col(old_mod.FAIR_COL).alias("fair_old"),
            pl.col(old_mod.ELIGIBLE_COL).alias("elig_old"),
        ]
    ).join(
        new_df.select(
            [
                "event_id",
                pl.col(FAIR_COL).alias("fair_new"),
                pl.col(ELIGIBLE_COL).alias("elig_new"),
                pl.col(HCA_COL).alias("hca_new"),
            ]
        ),
        on="event_id",
        how="inner",
    )
    valid = joined.filter(pl.col("elig_old") == True)  # noqa: E712
    # Non-finite fair (if any) excluded from abs-diff domain.
    valid_finite = valid.filter(
        pl.col("fair_old").is_not_null()
        & pl.col("fair_old").is_finite()
        & pl.col("fair_new").is_not_null()
        & pl.col("fair_new").is_finite()
    )
    diff = (valid_finite["fair_old"] - valid_finite["fair_new"]).abs()
    max_abs = float(diff.max()) if valid_finite.height else None
    exact = bool(valid_finite.height and max_abs == 0.0)

    # Incumbent untouched
    incumbent_cols = [
        c
        for c in (
            "fair_spread_home",
            "hca_applied",
            "fair_spread_method",
            "continuity_state",
            "fair_ml_home",
            "fair_total",
        )
        if c in c0.columns and c in new_df.columns
    ]
    incumbent_unchanged = all(c0[c].to_list() == new_df[c].to_list() for c in incumbent_cols)

    mat_src = inspect.getsource(materialize_lab_fair)
    materialize_incumbent_only = (
        "compute_fair_b2(" in mat_src
        and "compute_fair_b2_pace_v1(" not in mat_src
        and "from ncaam_lab.fair_b2_pace_v1" not in mat_src
    )

    # Sanity: frozen HCA applied everywhere on new path
    hca_all_frozen = all(
        (v is None or (isinstance(v, float) and math.isclose(v, FROZEN_HCA)))
        or (isinstance(v, (int, float)) and float(v) == FROZEN_HCA)
        for v in new_df[HCA_COL].to_list()
    )

    receipt: Dict[str, Any] = {
        "phase": "2.7A",
        "title": "PR #490 reconciliation + enterprise hardening",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_id": CANDIDATE_ID,
        "method_id": METHOD_ID,
        "production_base": PRODUCTION_BASE,
        "production_base_resolved": base,
        "head_sha": head,
        "originating_commit_pre_rebase": ORIGINATING_COMMIT_PRE_REBASE,
        "old_impl_ref_used": old_ref_used,
        "implementation_hashes": {
            "old_fair_b2_pace_v1_py_sha256": old_sha,
            "new_fair_b2_pace_v1_py_sha256": new_sha,
            "bytes_changed": old_sha != new_sha,
        },
        "frozen_contract": {
            "adjem_diff": "clip(home_adjem-away_adjem, ±30)",
            "possessions": "(home_adjt+away_adjt)/2",
            "margin": "clip(adjem_diff*possessions/100 + 2.8696, ±28)",
            "hca": FROZEN_HCA,
            "immutable": True,
            "weights_path_behavior": "refused",
            "custom_hca_mismatch_behavior": "refused",
            "nonfinite_behavior": "fail_closed_fair_null",
        },
        "parity_train_a": {
            "parquet": str(TRAIN_PARQUET.relative_to(REPO)),
            "parquet_sha256": sha256_file(TRAIN_PARQUET),
            "row_count": int(raw.height),
            "n_old_eligible": int(valid.height),
            "n_valid_domain_finite_fair": int(valid_finite.height),
            "expected_eligible_historical": 3676,
            "max_abs_fair_diff": max_abs,
            "exact_equality": exact,
            "elig_new_matches_elig_old_on_old_eligible": bool(
                valid.height
                and int(valid.filter(pl.col("elig_new") != True).height) == 0  # noqa: E712
            ),
            "hca_all_frozen": hca_all_frozen,
        },
        "incumbent": {
            "b2_columns_unchanged_when_challenger_attached": incumbent_unchanged,
            "materialize_incumbent_only": materialize_incumbent_only,
            "production_default_changed": False,
        },
        "holdout_governance": {
            "phase25_verdict_historically_accurate": (
                "NO VALID UNTOUCHED OOS WINDOW CURRENTLY MATERIALIZABLE "
                "(accurate as of Phase 2.5; not rewritten)"
            ),
            "current_foundation_holdout_id": HOLDOUT_FOUNDATION_ID,
            "foundation_source_phase": "2.6F",
            "features_labels_joined_for_evaluation": False,
            "performance_metrics_calculated": False,
            "scored": False,
            "unsealed": False,
            "b2_pace_neutral_v1_implemented": False,
        },
        "hard_locks_honored": [
            "no_merge",
            "no_unseal",
            "no_holdout_scoring",
            "no_deploy",
            "no_promote",
            "no_incumbent_default_change",
            "materializer_incumbent_only",
            "b2_pace_neutral_v1_unimplemented",
            "no_open_features_and_labels_together",
            "no_performance_calculation",
            "pr_490_remains_draft",
        ],
        "original_diagnostics_rewritten": False,
        "phase25_receipts_preserved": [
            "data/ops/lab/ncaam/ncaam-b2-pace-v1-train-a-diagnostics.json",
            "data/ops/lab/ncaam/ncaam-b2-pace-v1-phase25-hardening.json",
            "data/ops/lab/ncaam/ncaam-holdout-feasibility-phase25.json",
        ],
    }

    assert exact, f"parity failed: max_abs_fair_diff={max_abs}"
    assert int(valid_finite.height) == 3676, (
        f"expected 3676 valid-domain rows, got {valid_finite.height}"
    )
    assert incumbent_unchanged
    assert materialize_incumbent_only

    out_json = OUT_DIR / "ncaam-b2-pace-v1-phase27a-integration.json"
    out_md = OUT_DIR / "ncaam-b2-pace-v1-phase27a-integration.md"
    out_json.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    md = f"""# B2-PACE-v1 Phase 2.7A integration receipt

**Append-only.** Does not rewrite Phase 2.5 Train-A diagnostics or feasibility receipts.

## Identity

- Candidate: `{CANDIDATE_ID}` / `{METHOD_ID}`
- Production base: `{PRODUCTION_BASE}`
- HEAD at receipt generation: `{head}`
- Originating formula commit (pre-rebase): `{ORIGINATING_COMMIT_PRE_REBASE}`
- Old impl ref used for parity bytes: `{old_ref_used}`

## Implementation hashes

| Side | sha256(`{IMPL_PATH}`) |
|---|---|
| Old (frozen) | `{old_sha}` |
| New (2.7A) | `{new_sha}` |

## Frozen contract (unchanged math)

```
adjem_diff = clip(home_adjem - away_adjem, ±30)
possessions = (home_adjt + away_adjt) / 2
margin = clip(adjem_diff * possessions / 100 + 2.8696, ±28)
```

HCA pinned at `{FROZEN_HCA}`; `weights_path` / mismatched custom HCA refused; non-finite AdjEM/AdjT/HCA fail closed.

## Train-A valid-domain parity

- Rows (valid-domain finite fair): **{valid_finite.height}** (historical eligible 3676)
- `max_abs_fair_diff`: **{max_abs}**
- Exact equality: **{exact}**
- Incumbent B2 columns unchanged when challenger attached: **{incumbent_unchanged}**
- Materializer incumbent-only: **{materialize_incumbent_only}**

## Holdout governance (additive)

- Phase 2.5 verdict ("no valid untouched OOS window") remains historically accurate.
- Current foundation from Phase 2.6F: `{HOLDOUT_FOUNDATION_ID}`.
- **No** features+labels open together, **no** performance calculation, **no** scoring, **no** unseal.

## Hard locks

No merge / deploy / promote / incumbent-default change. B2-PACE-NEUTRAL-v1 remains unimplemented. PR #490 stays draft.
"""
    out_md.write_text(md, encoding="utf-8")
    print(json.dumps({"ok": True, "receipt": str(out_json), **receipt["parity_train_a"]}, indent=2))


if __name__ == "__main__":
    main()
