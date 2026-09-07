#!/usr/bin/env python3
"""Build 2024–25 sealed holdout packages (metadata + separated features/labels).

Season-parameterized orchestration. Does NOT score models, join predictions to
labels, or unseal the holdout. No odds API calls.
"""

from __future__ import annotations

import argparse
import json
import sys
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
from ncaam_lab.holdout_2425.active_release import (  # noqa: E402
    ActiveReleaseError,
    canonical_pack_path_for_active,
    current_is_set,
    load_canonical_pack,
)
from ncaam_lab.holdout_2425.locked_identity import (  # noqa: E402
    V1_1_BUILD_SUMMARY_BUILT_AT,
    V1_1_SCHEDULE_INDEX_BUILT_AT,
)


def _raw_ingestion_receipt(raw_dir: Path) -> Dict[str, Any]:
    """Fail-closed raw integrity: every JSON must have a matching sha256 sidecar.

    Sidecar contents are verified against the file digest. Missing sidecars or
    digest mismatches refuse the receipt (immutable_raw_preserved=False).
    """
    files = sorted(raw_dir.glob("espn_scoreboard_*.json")) if raw_dir.exists() else []
    sha_sidecars = (
        sorted(raw_dir.glob("espn_scoreboard_*.sha256")) if raw_dir.exists() else []
    )
    n_indexed = 0
    missing_sidecars: List[str] = []
    digest_mismatches: List[Dict[str, str]] = []
    for fp in files:
        side = raw_dir / fp.name.replace(".json", ".sha256")
        if not side.exists():
            missing_sidecars.append(fp.name)
            continue
        claimed = side.read_text(encoding="utf-8").strip().split()[0]
        actual = io.sha256_file(fp)
        if claimed.lower() != actual.lower():
            digest_mismatches.append(
                {
                    "file": fp.name,
                    "sidecar": side.name,
                    "claimed_sha256": claimed,
                    "actual_sha256": actual,
                }
            )
            continue
        n_indexed += 1
    integrity_ok = (
        len(files) > 0
        and len(missing_sidecars) == 0
        and len(digest_mismatches) == 0
        and n_indexed == len(files)
    )
    try:
        raw_dir_s = str(raw_dir.relative_to(REPO)) if raw_dir.exists() else str(raw_dir)
    except ValueError:
        raw_dir_s = str(raw_dir)
    return {
        "source": "espn_scoreboard_public",
        "raw_dir": raw_dir_s,
        "n_day_payloads": len(files),
        "n_sha256_sidecars": len(sha_sidecars),
        "immutable_raw_preserved": integrity_ok,
        "n_day_receipts_indexed": n_indexed,
        "n_missing_sidecars": len(missing_sidecars),
        "n_digest_mismatches": len(digest_mismatches),
        "missing_sidecars": missing_sidecars,
        "digest_mismatches": digest_mismatches,
        "checksum_policy": "every_json_requires_verified_sha256_sidecar",
        "captured_note": "HISTORICAL_STATIC_RECONSTRUCTION for static/venue fields",
    }


def _refuse_if_raw_not_preserved(raw_receipt: Dict[str, Any]) -> None:
    """Hard stop before any derived artifacts / package sealing."""
    if raw_receipt.get("immutable_raw_preserved"):
        return
    raise SystemExit(
        "FAIL-CLOSED: immutable ESPN raw not preserved "
        f"(n_day_payloads={raw_receipt.get('n_day_payloads')}, "
        f"n_missing_sidecars={raw_receipt.get('n_missing_sidecars')}, "
        f"n_digest_mismatches={raw_receipt.get('n_digest_mismatches')}). "
        "Refusing derived artifacts and seal."
    )


def build(*, season: str = C.SEASON_KEY) -> Dict[str, Any]:
    if season != C.SEASON_KEY:
        raise SystemExit(
            f"This Phase 2.6A builder seals {C.SEASON_KEY} only; got {season}."
        )

    if current_is_set():
        raise SystemExit(
            "FAIL-CLOSED: CURRENT active release is set. Refusing default flat "
            "live build (would create dual-reality vs CURRENT). Use Path B "
            "recovery / explicit staging out_root — do not write via legacy "
            f"FEATURE_DIR under {C.OUT_ROOT}."
        )

    # Fail closed on raw integrity BEFORE any derived artifacts or sealing.
    raw_receipt = _raw_ingestion_receipt(C.RAW_ESPN_DIR)
    _refuse_if_raw_not_preserved(raw_receipt)

    # CR7: authoritative pack is the active release (CURRENT when set).
    try:
        pack_path = canonical_pack_path_for_active()
        pack = load_canonical_pack()
    except ActiveReleaseError as exc:
        raise SystemExit(
            "FAIL-CLOSED: authoritative canonical schedule pack unavailable "
            f"({exc}). Rebuild/recover via Path B "
            "(scripts/ncaam/recover_2425_sealed_holdout_from_r2.py) — do not "
            "manually place hash-only seal artifacts. Declared flat "
            f"CANONICAL_PACK_PATH={C.CANONICAL_PACK_PATH} is non-authoritative "
            f"once CURRENT exists (current_set={current_is_set()})."
        ) from exc

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
    io.write_json(C.SCHEDULE_DIR / "raw_ingestion_receipt.json", raw_receipt)

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

    try:
        pack_rel = str(pack_path.relative_to(REPO))
    except ValueError:
        pack_rel = str(pack_path)
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
        "canonical_pack_path": pack_rel,
        "canonical_pack_sha256": io.sha256_file(pack_path),
        "active_release_current_set": current_is_set(),
        "game_ids": [
            str(g.get("espn_game_id") or g.get("game_id") or "") for g in games
        ],
        "built_at": V1_1_SCHEDULE_INDEX_BUILT_AT,
    }
    io.write_json(C.SCHEDULE_DIR / "schedule_sot_index.json", schedule_index)

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
        "seal_payload_sha256": seal.get("seal_payload_sha256"),
        "seal_file_sha256": seal.get("seal_file_sha256"),
        # Compatibility alias for external readers only; equals seal_payload_sha256.
        # Internal build/readiness consumers must use seal_payload_sha256 / seal_file_sha256.
        "seal_receipt_sha256": seal.get("seal_payload_sha256"),
        "seal_receipt_sha256_alias_of": "seal_payload_sha256",
        "features_labels_joined_for_evaluation": False,
        "performance_metrics_calculated": False,
        "api_calls_made": False,
        "raw_day_payloads": raw_receipt.get("n_day_payloads"),
        "built_at": V1_1_BUILD_SUMMARY_BUILT_AT,
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
