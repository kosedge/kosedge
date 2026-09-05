"""Materialize NCAAM Lab fair research artifacts (no Edge Board side effects)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import polars as pl

from ncaam_lab.fair_b2 import compute_fair_b2
from ncaam_lab.kenpom_asof import (
    assert_no_kenpom_leakage,
    attach_kenpom_asof,
    load_kenpom_snapshot_archive,
)
from ncaam_lab.protocol import (
    CUT_WINDOWS,
    PROTOCOL_DOC,
    PROTOCOL_VERSION,
    protocol_manifest,
)
from ncaam_lab.schedule_sot_d import build_lab_game_set

# Forbidden product write targets — materialize must never touch these.
FORBIDDEN_PRODUCT_PATHS = (
    "kei_lines_ncaam.json",
    "edge_board_fallback_ncaam.json",
    "power_ratings_ncaam.json",
)


def _repo_root() -> Path:
    # apps/web/src/ncaam_lab/materialize.py → repo root
    return Path(__file__).resolve().parents[4]


def _web_root() -> Path:
    return Path(__file__).resolve().parents[2]


def materialize_lab_fair(
    *,
    cut: str = "train_a",
    odds_path: Optional[Path] = None,
    kenpom_snapshots_dir: Optional[Path] = None,
    open_dir: Optional[Path] = None,
    weights_path: Optional[Path] = None,
    out_dir: Optional[Path] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Build Lab fair parquet + manifest for a locked cut window.

    Writes under data/ops/lab/ncaam/ only. Never writes Edge Board / kei_lines.
    """
    web = _web_root()
    root = _repo_root()

    odds_path = odds_path or (web / "data" / "processed" / "ncaab_historical_odds_open_close.parquet")
    kenpom_snapshots_dir = kenpom_snapshots_dir or (
        web / "data" / "processed" / "kenpom_snapshots"
    )
    open_dir = open_dir or (web / "data" / "raw" / "odds" / "open")
    weights_path = weights_path or (web / "data" / "processed" / "ensemble_weights.json")
    out_dir = out_dir or (root / "data" / "ops" / "lab" / "ncaam")

    if cut not in CUT_WINDOWS:
        raise ValueError(f"cut must be one of {sorted(CUT_WINDOWS)}; got {cut!r}")

    # Guard: refuse if caller tries to point out_dir at product JSON dirs
    out_resolved = out_dir.resolve()
    for forbidden in FORBIDDEN_PRODUCT_PATHS:
        if (web / "data" / "processed" / forbidden).resolve() == out_resolved:
            raise RuntimeError(f"refusing to write Lab fair into product path {forbidden}")

    if not odds_path.exists():
        raise FileNotFoundError(f"Path A odds parquet missing: {odds_path}")

    odds = pl.read_parquet(odds_path)
    games = build_lab_game_set(odds, cut=cut, open_dir=open_dir)

    archive = load_kenpom_snapshot_archive(kenpom_snapshots_dir)
    if archive is None:
        raise FileNotFoundError(
            f"KenPom snapshots missing/empty under {kenpom_snapshots_dir} (feed required)"
        )

    games = attach_kenpom_asof(games, archive)
    ok_leak, n_viol = assert_no_kenpom_leakage(games)
    if not ok_leak:
        raise RuntimeError(f"KenPom leakage audit failed: {n_viol} as_of > tip violations")

    # Incumbent only. B2-PACE-v1 is a non-default challenger (fair_b2_pace_v1) and must never become the silent materialize path.
    games = compute_fair_b2(games, weights_path=weights_path)

    # Drop rows still without fair_spread (missing KenPom both sides)
    n_before = len(games)
    games_scored = games.filter(pl.col("fair_spread_home").is_not_null())
    n_no_ratings = n_before - len(games_scored)

    stamped = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parquet_name = f"ncaam-fair-lab-{cut}-{stamped}.parquet"
    latest_name = f"ncaam-fair-lab-{cut}-latest.parquet"
    manifest_name = f"ncaam-fair-lab-{cut}-{stamped}.manifest.json"

    summary = {
        "protocol_version": PROTOCOL_VERSION,
        "protocol_doc": PROTOCOL_DOC,
        "sport": "ncaam",
        "cut": cut,
        "cut_window": {
            "start": CUT_WINDOWS[cut].start.isoformat(),
            "end": CUT_WINDOWS[cut].end.isoformat(),
        },
        "schedule_sot": "D",
        "baselines": {"B1": "close_consensus_path_a", "B2": "kenpom_adjem_plus_hca"},
        "n_lab_games": len(games),
        "n_with_fair_spread": len(games_scored),
        "n_missing_kenpom": n_no_ratings,
        "n_continuity_prior": int(
            (games_scored["continuity_state"] == "PRIOR").sum()
        )
        if len(games_scored)
        else 0,
        "n_continuity_unknown": int(
            (games_scored["continuity_state"] == "UNKNOWN").sum()
        )
        if len(games_scored)
        else 0,
        "n_with_fair_total": int(games_scored["fair_total"].is_not_null().sum())
        if len(games_scored) and "fair_total" in games_scored.columns
        else 0,
        "n_open_snapshot_honest": int(games_scored["open_snapshot_honest"].sum())
        if len(games_scored) and "open_snapshot_honest" in games_scored.columns
        else 0,
        "kenpom_leakage_ok": ok_leak,
        "kenpom_leakage_violations": n_viol,
        "inputs": {
            "odds_path": str(odds_path),
            "kenpom_snapshots_dir": str(kenpom_snapshots_dir),
            "open_dir": str(open_dir),
            "weights_path": str(weights_path),
        },
        "outputs": {},
        "product_side_effects": "none",
        "forbidden_untouched": list(FORBIDDEN_PRODUCT_PATHS),
        "stamped_utc": stamped,
        "protocol": protocol_manifest(),
    }

    if dry_run:
        summary["dry_run"] = True
        return summary

    out_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = out_dir / parquet_name
    latest_path = out_dir / latest_name
    manifest_path = out_dir / manifest_name
    protocol_path = out_dir / "ncaam-fair-lab-protocol-v1.json"

    games_scored.write_parquet(parquet_path)
    games_scored.write_parquet(latest_path)
    protocol_path.write_text(json.dumps(protocol_manifest(), indent=2) + "\n", encoding="utf-8")

    summary["outputs"] = {
        "parquet": str(parquet_path.relative_to(root)) if parquet_path.is_relative_to(root) else str(parquet_path),
        "latest": str(latest_path.relative_to(root)) if latest_path.is_relative_to(root) else str(latest_path),
        "manifest": str(manifest_path.relative_to(root)) if manifest_path.is_relative_to(root) else str(manifest_path),
        "protocol_json": str(protocol_path.relative_to(root))
        if protocol_path.is_relative_to(root)
        else str(protocol_path),
    }
    manifest_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary
