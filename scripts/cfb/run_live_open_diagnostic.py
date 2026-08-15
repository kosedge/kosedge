#!/usr/bin/env python3
"""2026 live open diagnostic — v0.15 fair vs owned opens. Report only.

Usage:
  python scripts/cfb/run_live_open_diagnostic.py --repo-fallback
  python scripts/cfb/cfb live-open --repo-fallback

Does not write KEI. used_in_spread stays false. Not a release gate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

OPS_MD = ROOT / "data" / "ops" / "cfb-live-open-diagnostic-20260815.md"
OPS_JSON = ROOT / "data" / "ops" / "cfb-live-open-diagnostic-20260815.json"


def _attach_fairs(reduced: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    from src.services.cfb_season_engine import (
        build_packaged_universe,
        project_game_preview,
        project_game_to_dict,
    )

    universe = build_packaged_universe(2026)
    out: List[Dict[str, Any]] = []
    for row in reduced:
        home = str(row.get("home_team_id") or "")
        away = str(row.get("away_team_id") or "")
        week = int(row.get("week") or 0)
        if not home or not away:
            continue
        proj = project_game_preview(
            universe,
            home_team=home,
            away_team=away,
            week=week,
            n_sims=80,
            seed=7,
        )
        payload = project_game_to_dict(proj)
        assert payload["used_in_spread"] is False
        joined = dict(row)
        joined["model_spread_home"] = round(float(proj.spread_home), 2)
        joined["model_total"] = round(float(proj.expected_total), 2)
        joined["model_fair_present"] = True
        joined["used_in_spread"] = False
        joined["kei"] = False
        out.append(joined)
    return out


def run(*, prefer_hd: bool) -> Dict[str, Any]:
    from src.services.cfb_warehouse.live_open_diagnostic import diagnose_opens
    from src.services.cfb_warehouse.open_ingest import load_mapped, reduce_mapped_games

    mapped = load_mapped(prefer_hd=prefer_hd)
    reduced = reduce_mapped_games(mapped, weeks=(0, 1, 2))
    n_opens = sum(1 for r in reduced if r.get("open_spread_home") is not None)
    n_closes = sum(1 for r in reduced if r.get("close_spread_home") is not None)
    extra = {
        "n_lake_mapped_rows": len(mapped),
        "n_slate_games_with_snaps": len(reduced),
        "weeks": [0, 1, 2],
    }
    if n_opens == 0:
        return diagnose_opens([], n_opens=0, n_closes=n_closes, extra=extra)
    joined = _attach_fairs([r for r in reduced if r.get("open_spread_home") is not None])
    return diagnose_opens(joined, n_opens=n_opens, n_closes=n_closes, extra=extra)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-fallback", action="store_true")
    args = parser.parse_args(argv)
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    payload = run(prefer_hd=not args.repo_fallback)
    OPS_JSON.parent.mkdir(parents=True, exist_ok=True)
    OPS_JSON.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    summary = {
        "wrote": str(OPS_JSON),
        "status": payload.get("status"),
        "n_opens": payload.get("n_opens"),
        "n_matched": payload.get("n_matched"),
        "match_rate": payload.get("match_rate"),
        "bias": payload.get("bias"),
        "bias_one_liner": payload.get("bias_one_liner"),
        "overall": payload.get("overall"),
        "by_week": payload.get("by_week"),
        "by_open_abs_bucket": payload.get("by_open_abs_bucket"),
        "by_favorite_home": payload.get("by_favorite_home"),
        "gate": payload.get("gate"),
        "used_in_spread": payload.get("used_in_spread"),
        "kei": payload.get("kei"),
        "not_a_release_gate": True,
    }
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
