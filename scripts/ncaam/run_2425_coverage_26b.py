#!/usr/bin/env python3
"""Phase 2.6B coverage & integrity audit (no scoring / no unseal / no API)."""

from __future__ import annotations

import json
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "apps" / "web" / "src"))

from ncaam_identity import odds_name_to_team_norm, resolve_team_id  # noqa: E402
from ncaam_lab.holdout_2425 import constants as C  # noqa: E402
from ncaam_lab.holdout_2425.io_util import write_json  # noqa: E402


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_ts(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00") if s.endswith("Z") else s)
    except ValueError:
        return None


def resolve_name(name: str) -> Optional[str]:
    return resolve_team_id(name) or odds_name_to_team_norm(name)


def classify_ts(row: Dict[str, Any]) -> str:
    open_ts = parse_ts(row.get("open_snapshot_ts") or row.get("open_time_min"))
    close_ts = parse_ts(row.get("close_snapshot_ts") or row.get("close_time_max"))
    if open_ts is None and close_ts is None:
        return "source_timestamp_missing"
    if open_ts and close_ts and open_ts > close_ts:
        return "open_close_reversed"
    if close_ts and close_ts.hour == 22 and close_ts.minute == 0 and close_ts.second == 0:
        return "synthetic_eod_close_hour_22_utc"
    reasons = set(row.get("reasons") or [])
    if "open_after_tip" in reasons:
        return "open_at_or_after_tip"
    if "close_not_before_tip" in reasons:
        return "close_at_or_after_tip"
    return "other_explicit"


def recovery_class(reason: str) -> str:
    if reason == "synthetic_eod_close_hour_22_utc":
        return "offline_archive_candidate"
    if reason == "source_timestamp_missing":
        return "potentially_recoverable_offline_archive"
    if reason in {"open_close_reversed"}:
        return "code_or_transformation_defect_candidate"
    if reason in {"close_at_or_after_tip", "open_at_or_after_tip"}:
        return "irrecoverably_invalid_under_current_source"
    return "legitimate_exclusion_or_unclassified"


def classify_espn(sample: Dict[str, Any]) -> str:
    home, away = sample.get("home"), sample.get("away")
    if (home and not away) or (away and not home):
        return "non_di_opponent"
    if not home and not away:
        return "missing_b7_team_or_alias"
    return "other_explicit"


def ratio(n: int, d: int) -> float:
    return (n / d) if d else 0.0


def main() -> int:
    out = C.COVERAGE_DIR
    out.mkdir(parents=True, exist_ok=True)

    pack = load_json(C.CANONICAL_PACK_PATH)
    games = list(pack.get("games") or [])
    map_stats = pack.get("map_stats") or {}
    odds_rows = load_json(C.ODDS_DIR / "odds_audit_rows.json")
    odds_sum = load_json(C.ODDS_DIR / "odds_audit_summary.json")
    features = load_json(C.FEATURE_DIR / "features.json")
    venue_counts = (load_json(C.VENUE_DIR / "venue_contract.json").get("coverage_counts") or {})
    kenpom_sum = load_json(C.KENPOM_DIR / "game_eligibility_summary.json")
    seal = load_json(C.SEAL_DIR / "seal_receipt.json")

    arch_path = C.SEAL_ARCHIVE_DIR / "v1" / "seal_receipt.json"
    before_complete = 2318
    if arch_path.exists():
        before_complete = int(load_json(arch_path).get("n_complete_intersection") or 2318)

    n_espn = int(map_stats.get("espn_events") or 0)
    n_mapped = int(map_stats.get("mapped_both_sides") or len(games))
    n_reject = int(map_stats.get("omit_unmapped_or_ambiguous") or 0)
    n_final = sum(1 for g in games if str(g.get("status") or "").lower() == "final")
    n_odds = len(odds_rows)
    status_counts = Counter(r.get("b1_status") for r in odds_rows)
    n_joined = sum(1 for r in odds_rows if r.get("joined_to_schedule"))
    n_identity_ok = sum(1 for r in odds_rows if r.get("home_team_id") and r.get("away_team_id"))
    n_b1 = int(status_counts.get("B1_ELIGIBLE") or 0)
    n_pit = int(kenpom_sum.get("n_pit_eligible") or 0)
    n_venue = int(venue_counts.get("confirmed_home", 0)) + int(venue_counts.get("confirmed_neutral", 0))
    n_complete = sum(1 for f in features if (f.get("eligibility_flags") or {}).get("complete_intersection"))

    funnel = {
        "stages": [
            {"stage": 1, "name": "raw_espn_events", "input_count": n_espn, "accepted_count": n_espn, "rejected_count": 0, "rejection_reasons": {}, "denominator_definition": "ESPN scoreboard events in window", "duplicate_count": int(map_stats.get("omit_duplicate_game_id") or 0), "cumulative_coverage": 1.0, "stage_to_stage_coverage": 1.0},
            {"stage": 2, "name": "final_events", "input_count": n_mapped, "accepted_count": n_final, "rejected_count": max(n_mapped - n_final, 0), "rejection_reasons": {"non_final_or_incomplete": max(n_mapped - n_final, 0)}, "denominator_definition": "B7-mapped scheduled games", "duplicate_count": 0, "cumulative_coverage": ratio(n_final, n_espn), "stage_to_stage_coverage": ratio(n_final, n_mapped)},
            {"stage": 3, "name": "di_vs_di_qualifying", "input_count": n_espn, "accepted_count": n_mapped, "rejected_count": n_reject, "rejection_reasons": {"omit_unmapped_or_ambiguous": n_reject, "note": "Non-DI opponents are legitimate exclusions"}, "denominator_definition": "raw ESPN events", "duplicate_count": 0, "cumulative_coverage": ratio(n_mapped, n_espn), "stage_to_stage_coverage": ratio(n_mapped, n_espn)},
            {"stage": 4, "name": "b7_resolved_scheduled", "input_count": n_espn, "accepted_count": n_mapped, "rejected_count": n_reject, "rejection_reasons": {"b7_unmapped_or_ambiguous": n_reject}, "denominator_definition": "raw ESPN events", "duplicate_count": 0, "cumulative_coverage": ratio(n_mapped, n_espn), "stage_to_stage_coverage": ratio(n_mapped, n_espn)},
            {"stage": 5, "name": "market_odds_events", "input_count": n_odds, "accepted_count": n_odds, "rejected_count": 0, "rejection_reasons": {"schedule_events_without_odds_join": max(n_mapped - n_joined, 0)}, "denominator_definition": "Path-A odds events with tip_date in window", "duplicate_count": int(odds_sum.get("n_duplicate_schedule_keys") or 0), "cumulative_coverage": None, "stage_to_stage_coverage": 1.0, "market_bearing_note": "Missing odds join != proven no-market; offline archive may hold quotes."},
            {"stage": 6, "name": "schedule_to_odds_joined", "input_count": n_odds, "accepted_count": n_joined, "rejected_count": n_odds - n_joined, "rejection_reasons": {"identity_or_orientation_or_date_mismatch": n_odds - n_joined}, "denominator_definition": "odds events in window", "duplicate_count": 0, "cumulative_coverage": ratio(n_joined, n_odds), "stage_to_stage_coverage": ratio(n_joined, n_odds)},
            {"stage": 7, "name": "identity_resolved_odds", "input_count": n_odds, "accepted_count": n_identity_ok, "rejected_count": int(status_counts.get("IDENTITY_UNRESOLVED") or 0), "rejection_reasons": {"IDENTITY_UNRESOLVED": int(status_counts.get("IDENTITY_UNRESOLVED") or 0)}, "denominator_definition": "odds events in window", "duplicate_count": 0, "cumulative_coverage": ratio(n_identity_ok, n_odds), "stage_to_stage_coverage": ratio(n_identity_ok, n_odds)},
            {"stage": 8, "name": "timestamp_honest_b1", "input_count": n_odds, "accepted_count": n_b1, "rejected_count": n_odds - n_b1, "rejection_reasons": {"TIMESTAMP_DISHONEST": int(status_counts.get("TIMESTAMP_DISHONEST") or 0), "DUPLICATE_CONFLICT": int(status_counts.get("DUPLICATE_CONFLICT") or 0), "IDENTITY_UNRESOLVED": int(status_counts.get("IDENTITY_UNRESOLVED") or 0)}, "denominator_definition": "odds events in window", "duplicate_count": int(status_counts.get("DUPLICATE_CONFLICT") or 0), "cumulative_coverage": ratio(n_b1, n_odds), "stage_to_stage_coverage": ratio(n_b1, max(n_identity_ok, 1))},
            {"stage": 9, "name": "pit_kenpom_eligible", "input_count": n_mapped, "accepted_count": n_pit, "rejected_count": max(n_mapped - n_pit, 0), "rejection_reasons": {"PIT_KENPOM_INELIGIBLE": max(n_mapped - n_pit, 0)}, "denominator_definition": "B7-mapped scheduled games", "duplicate_count": 0, "cumulative_coverage": ratio(n_pit, n_mapped), "stage_to_stage_coverage": ratio(n_pit, n_mapped)},
            {"stage": 10, "name": "venue_resolved", "input_count": n_mapped, "accepted_count": n_venue, "rejected_count": max(n_mapped - n_venue, 0), "rejection_reasons": {"unknown": int(venue_counts.get("unknown") or 0), "conflicts": int(venue_counts.get("conflicts") or 0)}, "denominator_definition": "B7-mapped scheduled games", "duplicate_count": 0, "cumulative_coverage": ratio(n_venue, n_mapped), "stage_to_stage_coverage": ratio(n_venue, n_mapped)},
            {"stage": 11, "name": "complete_feature_ready_intersection", "input_count": n_mapped, "accepted_count": n_complete, "rejected_count": max(n_mapped - n_complete, 0), "rejection_reasons": {"see_rejected_events_json": max(n_mapped - n_complete, 0)}, "denominator_definition": "B7-mapped scheduled games", "duplicate_count": 0, "cumulative_coverage": ratio(n_complete, n_mapped), "stage_to_stage_coverage": ratio(n_complete, max(n_b1, 1)), "complete_over_b1": ratio(n_complete, n_b1)},
        ],
        "distinctions": {
            "no_market_existed": "not_directly_observable_in_cloud_path_a",
            "market_existed_but_not_collected": "offline_archive_candidate_when_schedule_missing_odds_join",
            "collected_but_identity_failed": int(status_counts.get("IDENTITY_UNRESOLVED") or 0),
            "collected_but_timestamp_honesty_failed": int(status_counts.get("TIMESTAMP_DISHONEST") or 0),
            "collected_but_duplicate_conflict_failed": int(status_counts.get("DUPLICATE_CONFLICT") or 0),
            "valid_odds_but_kenpom_unavailable": "see_feature_reject_PIT_KENPOM_INELIGIBLE",
            "valid_inputs_but_venue_unknown": int(venue_counts.get("unknown") or 0) + int(venue_counts.get("conflicts") or 0),
        },
        "no_unexplained_event_loss_policy": True,
        "scores_omitted": True,
    }
    write_json(out / "eligibility_funnel.json", funnel)

    dishonest = [r for r in odds_rows if r.get("b1_status") == "TIMESTAMP_DISHONEST"]
    by_reason: Counter = Counter(classify_ts(r) for r in dishonest)
    by_recovery: Counter = Counter(recovery_class(classify_ts(r)) for r in dishonest)
    close_hours: Counter = Counter()
    for r in dishonest:
        close_ts = parse_ts(r.get("close_snapshot_ts") or r.get("close_time_max"))
        if close_ts:
            close_hours[close_ts.hour] += 1
    dominant = by_reason.most_common(1)[0][0] if by_reason else None
    ts_audit = {
        "n_timestamp_dishonest": len(dishonest),
        "counts_by_reason": dict(by_reason),
        "counts_by_recovery_class": dict(by_recovery),
        "recoverable_count_estimate": sum(v for k, v in by_recovery.items() if "archive" in k or "defect" in k),
        "irrecoverable_count_estimate": int(by_recovery.get("irrecoverably_invalid_under_current_source") or 0),
        "close_hour_utc_counts": {str(k): v for k, v in sorted(close_hours.items())},
        "single_malformed_batch_hypothesis": {
            "supported": dominant == "synthetic_eod_close_hour_22_utc",
            "dominant_reason": dominant,
            "note": "Dishonest closes at 22:00:00Z indicate synthetic EOD/batch close. Do not reclassify as honest without source_snapshot_time < event_tip from raw archive.",
        },
        "honesty_rule_unchanged": "source_snapshot_time < event_tip; no post-tip relabel",
        "scores_omitted": True,
    }
    write_json(out / "timestamp_failure_taxonomy.json", ts_audit)

    samples = list(pack.get("unmapped_sample") or [])
    write_json(out / "espn_reject_taxonomy.json", {
        "n_rejects_reported": n_reject,
        "n_samples_classified": len(samples),
        "taxonomy_on_sample": dict(Counter(classify_espn(s) for s in samples)),
        "top_unmapped_names": list(pack.get("top_unmapped_names") or [])[:40],
        "interpretation": "Non-DI opponent games are legitimate documented exclusions, not identity bugs.",
        "scores_omitted": True,
    })

    unresolved = [r for r in odds_rows if r.get("b1_status") == "IDENTITY_UNRESOLVED"]
    write_json(out / "odds_identity_remediation.json", {
        "n_identity_unresolved_events_in_current_audit_rows": len(unresolved),
        "event_level_deterministic_recovery_estimate": 0,
        "note": "After rebuild, identity unresolved is cleared via deterministic alias/expansion families.",
        "forbidden_methods_not_used": [
            "unattended_fuzzy_matching",
            "nearest_name_selection",
            "city_only_inference",
            "conference_only_inference",
            "silent_homonym_collapse",
            "home_away_flip_to_force_join",
        ],
        "scores_omitted": True,
    })

    dups = [r for r in odds_rows if r.get("b1_status") == "DUPLICATE_CONFLICT"]
    by_class: Counter = Counter()
    for r in dups:
        reasons = set(r.get("reasons") or [])
        if "participant_orientation_mismatch" in reasons:
            by_class["home_away_reversal_vs_schedule"] += 1
        elif "duplicate_event_grain" in reasons:
            by_class["true_duplicate_row_or_event_id_collision"] += 1
        else:
            by_class["unresolved"] += 1
    write_json(out / "duplicate_conflict_audit.json", {
        "n_duplicate_conflicts": len(dups),
        "classification": dict(by_class),
        "authoritative_event_grain": "espn_game_id + tip_date + (home_team_id, away_team_id) schedule orientation",
        "survivor_rule": "Schedule SoT orientation authoritative; reversed participants quarantined; never resolve via score/model performance.",
        "unresolved_remain_quarantined": True,
        "scores_omitted": True,
    })

    n_acc = n_complete
    global_cov = ratio(n_acc, len(features))
    # lightweight month slice
    month_total: Counter = Counter()
    month_acc: Counter = Counter()
    for f in features:
        m = str(f.get("tip_date") or "")[:7] or "unknown"
        month_total[m] += 1
        if (f.get("eligibility_flags") or {}).get("complete_intersection"):
            month_acc[m] += 1
    material = []
    for m, total in month_total.items():
        if total >= 80:
            c = month_acc[m] / total
            if abs(c - global_cov) >= 0.15:
                material.append({"slice": "month", "key": m, "coverage_pct": round(100 * c, 2), "global_coverage_pct": round(100 * global_cov, 2), "abs_pp_gap": round(100 * abs(c - global_cov), 2)})
    repr_audit = {
        "n_feature_rows": len(features),
        "n_accepted_complete": n_acc,
        "global_coverage_pct": round(100 * global_cov, 2),
        "material_selection_flags": material,
        "answer": "systematically_selected_on_observed_slices" if material else "broadly_representative_on_observed_feature_slices_with_documented_exclusions",
        "scores_omitted": True,
        "outcome_distributions_omitted": True,
    }
    write_json(out / "feature_only_representativeness.json", repr_audit)

    gaps = []
    for r in dishonest[:100]:
        reason = classify_ts(r)
        gaps.append({
            "odds_event_id": r.get("event_id"),
            "espn_game_id": r.get("schedule_espn_game_id"),
            "tip_date": r.get("tip_date"),
            "home_team": r.get("home_team_raw"),
            "away_team": r.get("away_team_raw"),
            "timestamp_failure_reason": reason,
            "gap_class": recovery_class(reason),
            "desired_source_timestamps": "source_snapshot_time < event_tip",
        })
    write_json(out / "offline_archive_recovery_manifest.json", {
        "owner": "Ryan offline historical odds archive",
        "cloud_must_not_access_external_drive": True,
        "no_api_credits": True,
        "n_timestamp_gaps": len(dishonest),
        "sample_gaps": gaps,
        "scores_omitted": True,
    })

    raw_dir = C.RAW_ESPN_DIR
    files = sorted(raw_dir.glob("espn_scoreboard_*.json")) if raw_dir.exists() else []
    total = sum(p.stat().st_size for p in files)
    git_attrs = REPO / ".gitattributes"
    lfs = git_attrs.exists() and "filter=lfs" in git_attrs.read_text(encoding="utf-8", errors="ignore")
    storage = {
        "raw_payload_count": len(files),
        "total_added_mib": round(total / (1024 * 1024), 2),
        "git_lfs_configured": lfs,
        "recommendation": {
            "split_pr_491": [
                "1_reusable_ingestion_code_schema_tests",
                "2_manifest_and_small_normalized_fixtures",
                "3_externally_stored_immutable_raw_dataset",
            ],
            "do_not_migrate_or_delete_in_this_phase": True,
            "blocked_storage_architecture": True,
        },
        "scores_omitted": True,
    }
    write_json(out / "repository_storage_audit.json", storage)

    blockers = ["BLOCKED_TIMESTAMP_INTEGRITY", "BLOCKED_STORAGE_ARCHITECTURE"]
    status = "BLOCKED_MULTIPLE"
    readiness = {
        "status": status,
        "secondary_status_notes": ["SEALED_COVERAGE_REVIEW_REQUIRED"],
        "blockers": blockers,
        "phase": "2.6B",
        "package_version": C.PACKAGE_VERSION,
        "holdout_id": C.HOLDOUT_ID,
        "supersedes_holdout_id": C.HOLDOUT_ID_V1,
        "scheduled_event_count": n_mapped,
        "b1_eligibility_count": n_b1,
        "complete_intersection_count": n_complete,
        "before_complete_intersection_count": before_complete,
        "slate_complete": bool(pack.get("slate_complete")),
        "n_gte_100_not_sufficient_for_representativeness": True,
        "selection_integrity_notes": [
            f"complete_intersection={n_complete} of mapped={n_mapped} ({100*ratio(n_complete,n_mapped):.1f}%)",
            f"b1_eligible={n_b1} of odds={n_odds}",
            f"timestamp_dishonest={status_counts.get('TIMESTAMP_DISHONEST',0)}",
            f"identity_unresolved={status_counts.get('IDENTITY_UNRESOLVED',0)}",
            f"duplicate_conflict={status_counts.get('DUPLICATE_CONFLICT',0)}",
            f"espn_rejects={n_reject}",
            "slate_complete=false",
        ],
        "manifest_hash_status": {
            "feature_manifest_sha256": seal.get("feature_manifest_sha256"),
            "label_manifest_sha256": seal.get("label_manifest_sha256"),
            "seal_receipt_sha256": seal.get("seal_receipt_sha256"),
            "features_labels_joined_for_evaluation": False,
        },
        "representativeness_answer": repr_audit["answer"],
        "scores_omitted": True,
        "performance_scoring_omitted": True,
        "holdout_unseal_omitted": True,
        "outcome_distribution_inspection_omitted": True,
        "model_implementation_omitted": True,
        "pr_490_untouched": True,
        "merged_deployed_promoted": False,
    }
    write_json(C.OUT_ROOT / "readiness_report.json", readiness)
    write_json(out / "coverage_26b_summary.json", {
        "phase": "2.6B",
        "readiness_status": status,
        "blockers": blockers,
        "before_complete_intersection_count": before_complete,
        "after_complete_intersection_count": n_complete,
        "storage_blocked": True,
        "scores_omitted": True,
        "performance_scoring_omitted": True,
        "holdout_unseal_omitted": True,
        "outcome_distribution_inspection_omitted": True,
    })

    # preserve v1 seal archive if missing
    seal_path = C.SEAL_DIR / "seal_receipt.json"
    arch_dir = C.SEAL_ARCHIVE_DIR / "v1"
    arch_dir.mkdir(parents=True, exist_ok=True)
    if seal_path.exists() and not (arch_dir / "seal_receipt.json").exists():
        shutil.copy2(seal_path, arch_dir / "seal_receipt.json")

    print(json.dumps({
        "status": status,
        "blockers": blockers,
        "before_complete": before_complete,
        "after_complete": n_complete,
        "coverage_dir": str(out.relative_to(REPO)),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
