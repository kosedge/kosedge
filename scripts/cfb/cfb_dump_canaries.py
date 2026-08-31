#!/usr/bin/env python3
"""Dump CFB canaries from the same artifacts / functions the site uses.

Prints power, E[wins], win-total width, playoff%, title%, KEI sample, as_of,
and git sha for OSU / USF / Utah / top-7.

Usage:
  python scripts/cfb/cfb_dump_canaries.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS_DATA = ROOT / "services/model-service/src/services/cfb_season_engine/data"
WEB_DATA = ROOT / "apps/web/lib/data"

CANARIES = ("OSU", "USF", "UTAH")


def _load(name: str) -> dict:
    for base in (MS_DATA, WEB_DATA):
        # model-service uses underscores; web uses hyphens for some packs
        candidates = [
            base / name,
            base / name.replace("_", "-"),
            base / name.replace("cfb_", "cfb-").replace("_", "-"),
        ]
        for p in candidates:
            if p.is_file():
                return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError(name)


def _git_sha() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT)
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


def _by_team(rows: list) -> dict:
    return {str(r.get("team")): r for r in rows}


def main() -> None:
    power = _load("cfb_power_sot_2026.json")
    proj = _load("cfb_season_projections_2026.json")
    futures = _load("cfb_futures_2026.json")
    kei = _load("cfb_kei_w0_w1_2026.json")

    tp = _by_team(power.get("teams") or [])
    tr = _by_team(proj.get("teams") or [])
    tf = _by_team(futures.get("teams") or [])

    print("=== CFB canary dump ===")
    print(f"git_sha={_git_sha()}")
    try:
        from src.services.cfb_season_engine.priors import ENGINE_VERSION as _EV
    except Exception:
        _EV = power.get("engine_version") or proj.get("engine_version")
    print(f"ENGINE_VERSION={_EV}")
    print(
        "artifact engine stamps:",
        {
            "power": power.get("engine_version"),
            "proj": proj.get("engine_version"),
            "futures": futures.get("engine_version"),
            "kei": kei.get("engine_version"),
        },
    )
    print(
        "as_of inventory:",
        {
            "power": power.get("power_as_of"),
            "proj": proj.get("as_of"),
            "futures": futures.get("as_of"),
            "kei": kei.get("as_of"),
        },
    )
    print(
        "lineage:",
        proj.get("lineage")
        or {
            "engine": "cfb",
            "wp_mapper": "power_sot.frozen_home_wp",
            "shock": "priors.SCORE_NOISE_SD+STRENGTH_NOISE",
            "kei_def": "cfb_kei.apply_cfb_kei",
            "sim_n": proj.get("n_sims"),
            "sim_seed": proj.get("sim_seed"),
        },
    )
    print()
    print("TOP-7 power (power_sot.build_power_sot / artifact):")
    for row in sorted(power.get("teams") or [], key=lambda r: -(r.get("power_index") or 0))[:7]:
        print(f"  {row.get('rank')}. {row.get('team')} {row.get('power_index')}")
    print()
    print("CANARIES (artifact functions = site loaders):")
    for code in CANARIES:
        p, pr, f = tp[code], tr[code], tf[code]
        width = float(pr["p90"]) - float(pr["p10"])
        print(
            f"  {code}: power={p.get('power_index')} E[wins]={pr.get('mean')} "
            f"width={width} std={pr.get('std')} "
            f"cfp={f.get('cfp_make_pct')} natty={f.get('natty_pct')}"
        )
    print()
    print("KEI is game-line only (apply_cfb_kei). Sample W0/W1 cupcakes:")
    games = [
        g
        for g in (kei.get("games") or [])
        if g.get("fbs_vs_fbs") and g.get("model_home_win_prob") is not None
    ]
    games.sort(key=lambda g: abs(float(g.get("model_spread_home") or 0)), reverse=True)
    for g in games[:8]:
        k = g.get("kei") or {}
        print(
            f"  W{g.get('week')} {g.get('away')}@{g.get('home')} "
            f"spread={g.get('model_spread_home')} model_wp={g.get('model_home_win_prob')} "
            f"kei_wp={k.get('kei_home_win_prob')}"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"dump failed: {exc}", file=sys.stderr)
        sys.exit(1)
