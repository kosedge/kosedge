#!/usr/bin/env python3
"""Research-only owned PBP validation + raw metrics (no model, no KEI, no adj).

Prefers /Volumes/KosEdgeData. Optional --allow-fetch restores the same
SportsDataverse espn_cfb_pbp releases already documented as owned.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_warehouse.cfbd_auth import probe_cfbd  # noqa: E402
from src.services.cfb_warehouse.owned_metrics import (  # noqa: E402
    DEFINITIONS,
    METRIC_VERSION,
    audit_epa_success,
    drive_metrics,
    league_rollups,
    opportunity_summary,
    pace_summary,
    rolling_form,
    team_game_raw_metrics,
)
from src.services.cfb_warehouse.owned_pbp import (  # noqa: E402
    INVENTORY_HIST_GAMES,
    INVENTORY_HIST_PLAYS,
    OWNED_HIST_SEASONS,
    VALIDATE_UNLOCK_SEASON,
    ensure_season,
    inspect_files,
    load_core_records,
    provenance_block,
    reconcile_to_inventory,
)
from src.services.cfb_warehouse.paths import hd_mounted  # noqa: E402
from src.services.cfb_warehouse.season_2026_w1 import features_for_week, w1_status  # noqa: E402


def _round_metrics(obj):
    if isinstance(obj, float):
        return round(obj, 6)
    if isinstance(obj, dict):
        return {k: _round_metrics(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_metrics(v) for v in obj]
    return obj


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-fetch",
        action="store_true",
        help="Restore missing seasons from the owned SportsDataverse release (not a new vendor).",
    )
    parser.add_argument("--skip-2025", action="store_true")
    parser.add_argument("--skip-metrics", action="store_true")
    parser.add_argument("--as-of-week", type=int, default=3, help="2026 W−1 as_of_week")
    parser.add_argument(
        "--out",
        default=str(ROOT / "data" / "ops" / "cfb-owned-pbp-research-20260915" / "evidence.json"),
    )
    args = parser.parse_args(argv)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    evidence: dict = {
        "research_only": True,
        "opponent_adjusted": False,
        "metric_version": METRIC_VERSION,
        "hd_mounted": hd_mounted(),
        "provenance": provenance_block(),
        "inventory_target_2021_2024": {
            "plays": INVENTORY_HIST_PLAYS,
            "games": INVENTORY_HIST_GAMES,
        },
        "validate_2025": None,
        "hist_2021_2024": None,
        "epa_success_audit": None,
        "raw_metrics": None,
        "cfbd_auth": None,
        "ingest_2026_w1": None,
        "definitions": DEFINITIONS,
    }

    if not args.skip_2025:
        files_25 = ensure_season(
            VALIDATE_UNLOCK_SEASON, prefer_hd=True, allow_fetch=args.allow_fetch
        )
        if files_25.source == "missing":
            evidence["validate_2025"] = {
                "status": "missing",
                "hd_mounted": hd_mounted(),
                "note": "Documented HD path not visible here. Re-run on Ryan's Mac or pass --allow-fetch.",
            }
        else:
            inspected = inspect_files(files_25)
            evidence["validate_2025"] = {
                "status": "ok",
                **inspected,
                "reconcile": reconcile_to_inventory(inspected),
                "note": "2025 unlocked for validation only. Not used to fill 2021–2024 gaps.",
            }

    hist_rows = []
    plays_all = []
    hist_plays = hist_games = 0
    for season in OWNED_HIST_SEASONS:
        files = ensure_season(season, prefer_hd=True, allow_fetch=args.allow_fetch)
        if files.source == "missing":
            hist_rows.append({"season": season, "status": "missing"})
            continue
        inspected = inspect_files(files)
        rec = reconcile_to_inventory(inspected)
        hist_rows.append({"status": "ok", "reconcile": rec, **inspected})
        raw = inspected.get("raw") or inspected.get("core") or {}
        hist_plays += int(raw.get("plays") or 0)
        hist_games += int(raw.get("games") or 0)
        if not args.skip_metrics:
            plays_all.extend(load_core_records(season, prefer_hd=files.source == "hd"))

    evidence["hist_2021_2024"] = {
        "seasons": hist_rows,
        "observed_plays": hist_plays,
        "observed_games": hist_games,
        "expected_plays": INVENTORY_HIST_PLAYS,
        "expected_games": INVENTORY_HIST_GAMES,
        "play_delta": hist_plays - INVENTORY_HIST_PLAYS if hist_plays else None,
        "game_delta": hist_games - INVENTORY_HIST_GAMES if hist_games else None,
        "exact_match": hist_plays == INVENTORY_HIST_PLAYS and hist_games == INVENTORY_HIST_GAMES,
    }

    if plays_all and not args.skip_metrics:
        audit = audit_epa_success(plays_all)
        games = team_game_raw_metrics(plays_all)
        drives = drive_metrics(plays_all)
        # W−1 smoke on 2024 week 8 using only week < 8 (historical, not 2025).
        form_2024_w8 = rolling_form(plays_all, season=2024, as_of_week=8)
        evidence["epa_success_audit"] = audit
        evidence["raw_metrics"] = _round_metrics(
            {
                "scope": "2021-2024 core/raw owned files actually loaded",
                "plays_scored": len(plays_all),
                "team_games": len(games),
                "pace": pace_summary(games),
                "league": league_rollups(games),
                "opportunity": opportunity_summary(drives),
                "rolling_form_2024_as_of_week_8_teams": len(form_2024_w8),
                "rolling_form_2024_w8_max_feature_week": max(
                    (r["feature_week"] for r in form_2024_w8), default=None
                ),
            }
        )

    evidence["cfbd_auth"] = probe_cfbd()
    evidence["ingest_2026_w1"] = {
        **w1_status(as_of_week=args.as_of_week),
        "scaffold": features_for_week([], as_of_week=args.as_of_week),
    }

    out_path.write_text(json.dumps(evidence, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: evidence[k] for k in (
        "hd_mounted",
        "validate_2025",
        "hist_2021_2024",
        "epa_success_audit",
        "raw_metrics",
        "cfbd_auth",
        "ingest_2026_w1",
    )}, indent=2, default=str)[:8000])
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
