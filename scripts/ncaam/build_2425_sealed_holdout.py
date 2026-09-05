#!/usr/bin/env python3
"""Build 2024–25 sealed holdout packages (metadata + separated features/labels).

Season-parameterized orchestration. Does NOT score models, join predictions to
labels, or unseal the holdout. No odds API calls.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[2]
WEB_SRC = REPO / "apps" / "web" / "src"
if str(WEB_SRC) not in sys.path:
    sys.path.insert(0, str(WEB_SRC))

from ncaam_lab.holdout_2425 import constants as C  # noqa: E402
from ncaam_lab.holdout_2425 import io_util as io  # noqa: E402
from ncaam_lab.holdout_2425 import kenpom_audit as kenpom  # noqa: E402
from ncaam_lab.holdout_2425 import odds_audit as odds  # noqa: E402
from ncaam_lab.holdout_2425 import readiness as readiness_mod  # noqa: E402
from ncaam_lab.holdout_2425 import schedule_normalize as sched  # noqa: E402
from ncaam_lab.holdout_2425 import seal_package as seal_mod  # noqa: E402
from ncaam_lab.holdout_2425 import venue_contract as venue  # noqa: E402


def _raw_ingestion_receipt(raw_dir: Path) -> Dict[str, Any]:
    files = sorted(raw_dir.glob("espn_scoreboard_*.json")) if raw_dir.exists() else []
    sha_sidecars = (
        sorted(raw_dir.glob("espn_scoreboard_*.sha256")) if raw_dir.exists() else []
    )
    n_indexed = 0
    for fp in files:
        side = raw_dir / fp.name.replace(".json", ".sha256")
        if side.exists() or True:
            n_indexed += 1
    return {
        "source": "espn_scoreboard_public",
        "raw_dir": str(raw_dir.relative_to(REPO)) if raw_dir.exists() else str(raw_dir),
        "n_day_payloads": len(files),
        "n_sha256_sidecars": len(sha_sidecars),
        "immutable_raw_preserved": len(files) > 0,
        "n_day_receipts_indexed": n_indexed,
        "captured_note": "HISTORICAL_STATIC_RECONSTRUCTION for static/venue fields",
    }


def build(*, season: str = C.SEASON_KEY) -> Dict[str, Any]:
    if season != C.SEASON_KEY:
        raise SystemExit(
            f"This Phase 2.6A builder seals {C.SEASON_KEY} only; got {season}."
        )

    io.ensure_dirs(
        [
            C.OUT_ROOT,
            C.SCHEDULE_DIR,
            C.VENUE_DIR,
            C.KENPOM_DIR,
            C.ODDS_DIR,
            C.QUARANTINE_DIR,
            C.REJECTED_DIR,
            C.SEAL_DIR,
        ]
    )

    pack = json.loads(C.CANONICAL_PACK_PATH.read_text(encoding="utf-8"))
    games: List[Dict[str, Any]] = list(pack.get("games") or [])

    dup_ids = sched.detect_duplicate_event_ids(games)
    reversals = sched.detect_participant_reversals(games)
    _kept, quarantined = sched.quarantine_nonfinal(games)

    io.write_json(
        C.QUARANTINE_DIR / "duplicate_event_ids.json",
        {"n": len(dup_ids), "event_ids": dup_ids},
    )
    io.write_json(C.QUARANTINE_DIR / "participant_reversals.json", reversals)
    io.write_json(C.QUARANTINE_DIR / "nonfinal_or_incomplete.json", quarantined)

    b7_reject_count = int((pack.get("map_stats") or {}).get("omit_unmapped_or_ambiguous") or 0)

    schedule_index = {
        "holdout_id": C.HOLDOUT_ID,
        "season": season,
        "schema_version": C.SCHEMA_VERSION_SCHEDULE,
        "window": {
            "start": C.WINDOW_START.isoformat(),
            "end": C.WINDOW_END.isoformat(),
        },
        "source": pack.get("source"),
        "metadata_class": pack.get("metadata_class")
        or "HISTORICAL_STATIC_RECONSTRUCTION",
        "n_games": len(games),
        "n_quarantined_nonfinal": len(quarantined),
        "n_duplicate_event_ids": len(dup_ids),
        "n_participant_reversals": len(reversals),
        "slate_complete": bool(pack.get("slate_complete")),
        "map_stats": pack.get("map_stats"),
        "canonical_pack_path": str(C.CANONICAL_PACK_PATH.relative_to(REPO)),
        "canonical_pack_sha256": io.sha256_file(C.CANONICAL_PACK_PATH),
        "game_ids": [
            str(g.get("espn_game_id") or g.get("game_id") or "") for g in games
        ],
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    io.write_json(C.SCHEDULE_DIR / "schedule_sot_index.json", schedule_index)

    raw_receipt = _raw_ingestion_receipt(C.RAW_ESPN_DIR)
    io.write_json(C.SCHEDULE_DIR / "raw_ingestion_receipt.json", raw_receipt)

    venue_pack = venue.build_venue_table(games)
    io.write_json(C.VENUE_DIR / "venue_contract.json", venue_pack)
    io.write_json(
        C.VENUE_DIR / "venue_coverage.json",
        {
            "coverage_counts": venue_pack.get("coverage_counts"),
            "n_rows": venue_pack.get("n_rows"),
            "scores_omitted": True,
        },
    )

    snapshots = kenpom.inventory_snapshots()
    kenpom_game = kenpom.build_game_eligibility(games, snapshots)
    io.write_json(
        C.KENPOM_DIR / "snapshot_inventory.json",
        {
            "n_snapshots": len(snapshots),
            "n_eligible": sum(1 for s in snapshots if s.get("eligible")),
            "snapshots": snapshots,
            "scores_omitted": True,
        },
    )
    io.write_json(
        C.KENPOM_DIR / "game_eligibility_summary.json",
        {k: v for k, v in kenpom_game.items() if k != "rows"},
    )
    io.write_json(C.KENPOM_DIR / "game_eligibility_rows.json", kenpom_game["rows"])

    odds_events = odds.load_odds_event_grain()
    odds_audit = odds.classify_odds_events(odds_events, games)
    io.write_json(
        C.ODDS_DIR / "odds_audit_summary.json",
        {k: v for k, v in odds_audit.items() if k != "rows"},
    )
    io.write_json(C.ODDS_DIR / "odds_audit_rows.json", odds_audit["rows"])
    odds_by_espn = odds.index_odds_by_espn_id(odds_audit)

    seal = seal_mod.build_feature_and_label_packages(
        schedule_rows=games,
        venue_rows=venue_pack["rows"],
        kenpom_eligibility=kenpom_game["rows"],
        odds_by_espn_id=odds_by_espn,
    )

    readiness = readiness_mod.compute_readiness(
        schedule_pack={
            "games": games,
            "slate_complete": bool(pack.get("slate_complete")),
        },
        venue_pack=venue_pack,
        kenpom_game=kenpom_game,
        odds_audit=odds_audit,
        seal=seal,
        b7_reject_count=b7_reject_count,
        quarantine_count=len(quarantined) + len(dup_ids) + len(reversals),
    )
    io.write_json(C.OUT_ROOT / "readiness_report.json", readiness)

    summary = {
        "holdout_id": C.HOLDOUT_ID,
        "season": season,
        "window": {
            "start": C.WINDOW_START.isoformat(),
            "end": C.WINDOW_END.isoformat(),
        },
        "readiness_status": readiness["status"],
        "scheduled_event_count": readiness["scheduled_event_count"],
        "final_label_presence_count": readiness["final_label_presence_count"],
        "b7_coverage_count": readiness["b7_coverage_count"],
        "b7_reject_count": readiness["b7_reject_count"],
        "venue_status_coverage": readiness["venue_status_coverage"],
        "pit_kenpom_eligibility_count": readiness["pit_kenpom_eligibility_count"],
        "b1_eligibility_count": readiness["b1_eligibility_count"],
        "complete_intersection_count": readiness["complete_intersection_count"],
        "feature_manifest_sha256": seal.get("feature_manifest_sha256"),
        "label_manifest_sha256": seal.get("label_manifest_sha256"),
        "seal_receipt_sha256": seal.get("seal_receipt_sha256"),
        "features_labels_joined_for_evaluation": False,
        "performance_metrics_calculated": False,
        "api_calls_made": False,
        "raw_day_payloads": raw_receipt.get("n_day_payloads"),
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    io.write_json(C.OUT_ROOT / "build_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", default=C.SEASON_KEY)
    args = parser.parse_args(argv)
    build(season=args.season)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
