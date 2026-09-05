"""Metadata-only readiness report for 2024–25 sealed holdout."""

from __future__ import annotations

from typing import Any, Dict, List

from ncaam_lab.holdout_2425.constants import READINESS_STATUSES


def compute_readiness(
    *,
    schedule_pack: Dict[str, Any],
    venue_pack: Dict[str, Any],
    kenpom_game: Dict[str, Any],
    odds_audit: Dict[str, Any],
    seal: Dict[str, Any],
    b7_reject_count: int,
    quarantine_count: int,
) -> Dict[str, Any]:
    games = schedule_pack.get("games") or []
    n_scheduled = len(games)
    n_final_labels = sum(
        1
        for g in games
        if str(g.get("status") or "").lower() == "final"
        and (g.get("home_score") is not None or g.get("home_score") is not None)
        and (g.get("away_score") is not None or g.get("away_score") is not None)
    )
    n_b7 = sum(1 for g in games if g.get("home") and g.get("away"))
    venue_counts = venue_pack.get("coverage_counts") or venue_pack.get("coverage_counts") or {}
    n_venue_known = int(venue_counts.get("confirmed_home", 0)) + int(
        venue_counts.get("confirmed_neutral", 0)
    )
    n_venue_unknown = int(venue_counts.get("unknown", 0))
    n_venue_conflicts = int(venue_counts.get("conflicts", 0))
    n_pit = int(kenpom_game.get("n_pit_eligible") or 0)
    n_b1 = int(odds_audit.get("n_b1_eligible") or 0)
    n_complete = int(seal.get("n_complete_intersection") or 0)

    blockers: List[str] = []
    if n_scheduled <= 0 or n_b7 <= 0 or b7_reject_count > max(n_scheduled, 1) * 0.25:
        blockers.append("BLOCKED_IDENTITY")
    if n_final_labels <= 0 or n_final_labels < max(n_scheduled, 1) * 0.9:
        blockers.append("BLOCKED_OUTCOMES")
    if n_pit <= 0 or n_pit < max(n_scheduled, 1) * 0.85:
        blockers.append("BLOCKED_PIT_KENPOM")
    if n_b1 <= 0:
        blockers.append("BLOCKED_B1_ODDS")
    if n_venue_known <= 0 or (n_venue_unknown + n_venue_conflicts) > max(n_scheduled, 1) * 0.5:
        blockers.append("BLOCKED_VENUE_CONTRACT")
    if not seal.get("feature_manifest_sha256") or not seal.get("label_manifest_sha256"):
        blockers.append("BLOCKED_MULTIPLE")
    if seal.get("features_labels_joined_for_evaluation"):
        blockers.append("BLOCKED_MULTIPLE")
    if n_complete <= 0 and "BLOCKED_MULTIPLE" not in blockers:
        # incomplete intersection is a multi-layer readiness failure when no other single blocker
        if not blockers:
            blockers.append("BLOCKED_MULTIPLE")

    if not blockers and n_complete > 0:
        status = "SEALED_AND_READY"
    elif len(blockers) == 1:
        status = blockers[0]
    else:
        status = "BLOCKED_MULTIPLE"

    assert status in READINESS_STATUSES

    return {
        "status": status,
        "blockers": blockers,
        "scheduled_event_count": n_scheduled,
        "final_label_presence_count": n_final_labels,
        "b7_coverage_count": n_b7,
        "b7_reject_count": b7_reject_count,
        "quarantine_count": quarantine_count,
        "venue_status_coverage": {
            "confirmed_home": int(venue_counts.get("confirmed_home", 0)),
            "confirmed_neutral": int(venue_counts.get("confirmed_neutral", 0)),
            "unknown": n_venue_unknown,
            "conflicts": n_venue_conflicts,
            "known_total": n_venue_known,
        },
        "pit_kenpom_eligibility_count": n_pit,
        "b1_eligibility_count": n_b1,
        "complete_intersection_count": n_complete,
        "rejection_counts_note": "see rejected/rejected_events.json reasons (no scores)",
        "manifest_hash_status": {
            "feature_manifest_sha256": seal.get("feature_manifest_sha256"),
            "label_manifest_sha256": seal.get("label_manifest_sha256"),
            "seal_receipt_sha256": seal.get("seal_receipt_sha256"),
            "features_labels_joined_for_evaluation": False,
        },
        "forbidden_outputs_omitted": [
            "score_values",
            "actual_margin_distribution",
            "candidate_predictions_joined_to_outcomes",
            "mae",
            "rmse",
            "ats",
            "roi",
            "clv",
            "calibration",
            "b1_vs_candidate_performance",
            "result_conditioned_slices",
        ],
        "slate_complete": bool(schedule_pack.get("slate_complete")),
    }
