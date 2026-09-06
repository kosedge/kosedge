"""Feature/label separation + seal receipt for 2024–25 holdout."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ncaam_lab.holdout_2425.constants import (
    FEATURE_DIR,
    FEATURE_SCHEMA_VERSION,
    HOLDOUT_ID,
    LABEL_DIR,
    LABEL_SCHEMA_VERSION,
    PACKAGE_SCHEMA_VERSION,
    REJECTED_DIR,
    REPO,
    SEAL_DIR,
    WINDOW_END,
    WINDOW_START,
)
from ncaam_lab.holdout_2425.io_util import write_json
from ncaam_lab.holdout_2425.locked_identity import (
    V1_1_FEATURE_SEALED_AT,
    V1_1_LABEL_SEALED_AT,
    V1_1_SEAL_SEALED_AT,
)
from ncaam_lab.holdout_2425.schedule_normalize import outcome_label_ok


def build_feature_and_label_packages(
    *,
    schedule_rows: list[dict[str, Any]],
    venue_rows: list[dict[str, Any]],
    kenpom_eligibility: list[dict[str, Any]],
    odds_by_espn_id: dict[str, dict[str, Any]],
    out_root: Path | None = None,
) -> dict[str, Any]:
    """Build physically separated feature + label packages.

    Never joins labels to candidate predictions. Scores appear only in the label package.

    Hashed identity uses frozen v1.1 sealed_at timestamps (not datetime.now).
    When out_root is set, packages write under that staging/live root.
    """
    if out_root is None:
        feature_dir = FEATURE_DIR
        label_dir = LABEL_DIR
        rejected_dir = REJECTED_DIR
        seal_dir = SEAL_DIR
    else:
        feature_dir = out_root / "feature_package"
        label_dir = out_root / "label_package"
        rejected_dir = out_root / "rejected"
        seal_dir = out_root / "seal"

    feature_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)
    rejected_dir.mkdir(parents=True, exist_ok=True)
    seal_dir.mkdir(parents=True, exist_ok=True)

    venue_by_eid = {str(r.get("source_event_id") or ""): r for r in venue_rows}
    kp_by_eid = {
        str(r.get("source_event_id") or r.get("event_id") or ""): r
        for r in kenpom_eligibility
    }

    features: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for g in schedule_rows:
        eid = str(g.get("espn_game_id") or g.get("game_id") or "")
        tip = str(g.get("tipoff") or g.get("kickoff") or "")
        tip_date = str(g.get("date") or "")[:10]
        venue = venue_by_eid.get(eid) or {}
        kp = kp_by_eid.get(eid) or {}
        od = odds_by_espn_id.get(eid) or {}

        label_ok = outcome_label_ok(g)
        hs = g.get("home_score", g.get("home_score"))
        aws = g.get("away_score", g.get("away_score"))
        b7_ok = bool(g.get("home")) and bool(g.get("away"))
        venue_status = str(venue.get("venue_status") or "unknown")
        venue_ok = venue_status in {"confirmed_home", "confirmed_neutral"}
        kp_ok = str(kp.get("eligibility_status") or "") == "PIT_ELIGIBLE"
        b1_status = str(od.get("b1_status") or od.get("status") or "NONQUALIFYING_EVENT")
        b1_ok = b1_status == "B1_ELIGIBLE"

        reasons: list[str] = []
        if not b7_ok:
            reasons.append("IDENTITY_UNRESOLVED")
        if not label_ok:
            reasons.append("OUTCOME_INCOMPLETE")
        if not venue_ok:
            reasons.append("VENUE_UNKNOWN_OR_CONFLICT")
        if not kp_ok:
            reasons.append("PIT_KENPOM_INELIGIBLE")
        if not b1_ok:
            reasons.append(b1_status if b1_status != "B1_ELIGIBLE" else "MISSING_ODDS")

        complete = not reasons
        features.append(
            {
                "event_id": eid,
                "tip": tip,
                "tip_date": tip_date,
                "home_team_norm": g.get("home"),
                "away_team_norm": g.get("away"),
                "home_team_id": g.get("home"),
                "away_team_id": g.get("away"),
                "venue_status": venue_status,
                "venue_lineage_ref": {
                    "source_event_id": venue.get("source_event_id"),
                    "validation_status": venue.get("validation_status"),
                    "historical_reconstruction": venue.get("historical_reconstruction"),
                    "b7_join_key": venue.get("b7_join_key"),
                    "conflict_reason": venue.get("conflict_reason"),
                },
                "kenpom_snapshot_id": kp.get("selected_snapshot_id"),
                "kenpom_snapshot_sha256": kp.get("selected_snapshot_sha256"),
                "kenpom_eligibility": kp.get("eligibility_status"),
                "b1_status": b1_status,
                "b1_odds_event_id": od.get("event_id"),
                "b1_open_ts": od.get("open_snapshot_ts") or od.get("open_time_min"),
                "b1_close_ts": od.get("close_snapshot_ts") or od.get("close_time_max"),
                "books_present": od.get("n_books") or od.get("books_present"),
                "eligibility_flags": {
                    "b7_ok": b7_ok,
                    "venue_ok": venue_ok,
                    "kenpom_ok": kp_ok,
                    "b1_ok": b1_ok,
                    "label_ok": label_ok,
                    "complete_intersection": complete,
                },
                "schema_version": FEATURE_SCHEMA_VERSION,
            }
        )

        labels.append(
            {
                "event_id": eid,
                "home_score": hs if label_ok else None,
                "away_score": aws if label_ok else None,
                "actual_home_margin": (float(hs) - float(aws)) if label_ok else None,
                "final_outcome_status": "final"
                if label_ok
                else str(g.get("status") or "incomplete"),
                "label_present": label_ok,
                "schema_version": LABEL_SCHEMA_VERSION,
            }
        )

        if reasons:
            rejected.append({"event_id": eid, "reasons": sorted(set(reasons))})

    feat_path = feature_dir / "features.json"
    lab_path = label_dir / "labels.json"
    rej_path = rejected_dir / "rejected_events.json"
    feat_sha = write_json(feat_path, features)
    lab_sha = write_json(lab_path, labels)
    rej_sha = write_json(rej_path, rejected)

    def _rel(p: Path) -> str:
        # Identity path is always the live package path (not staging), so manifest
        # hashes remain stable across staging rebuilds.
        live_map = {
            "features.json": "data/ops/lab/ncaam/holdout_2024_25/feature_package/features.json",
            "labels.json": "data/ops/lab/ncaam/holdout_2024_25/label_package/labels.json",
        }
        if p.name in live_map:
            return live_map[p.name]
        try:
            return str(p.relative_to(REPO))
        except ValueError:
            return p.as_posix()

    feature_manifest = {
        "holdout_id": HOLDOUT_ID,
        "package": "feature",
        "schema_version": FEATURE_SCHEMA_VERSION,
        "window": {"start": WINDOW_START.isoformat(), "end": WINDOW_END.isoformat()},
        "n_rows": len(features),
        "n_complete_intersection": sum(
            1 for f in features if f["eligibility_flags"]["complete_intersection"]
        ),
        "content_sha256": feat_sha,
        "path": _rel(feat_path),
        "sealed_at": V1_1_FEATURE_SEALED_AT,
        "note": "PIT inputs + static metadata only; no final scores",
    }
    label_manifest = {
        "holdout_id": HOLDOUT_ID,
        "package": "label",
        "schema_version": LABEL_SCHEMA_VERSION,
        "window": {"start": WINDOW_START.isoformat(), "end": WINDOW_END.isoformat()},
        "n_rows": len(labels),
        "n_label_present": sum(1 for L in labels if L.get("label_present")),
        "content_sha256": lab_sha,
        "path": _rel(lab_path),
        "sealed_at": V1_1_LABEL_SEALED_AT,
        "note": "Evaluation labels only; must not be joined to predictions in Phase 2.6A",
    }
    fm_sha = write_json(feature_dir / "feature_manifest.json", feature_manifest)
    lm_sha = write_json(label_dir / "label_manifest.json", label_manifest)

    # Seal membership payload — hash this body BEFORE inserting any self-hash field.
    seal = {
        "holdout_id": HOLDOUT_ID,
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "feature_manifest_sha256": fm_sha,
        "label_manifest_sha256": lm_sha,
        "feature_content_sha256": feat_sha,
        "label_content_sha256": lab_sha,
        "rejected_sha256": rej_sha,
        "n_features": len(features),
        "n_labels": len(labels),
        "n_rejected": len(rejected),
        "n_complete_intersection": feature_manifest["n_complete_intersection"],
        "features_labels_joined_for_evaluation": False,
        "sealed_at": V1_1_SEAL_SEALED_AT,
    }
    seal_path = seal_dir / "seal_receipt.json"
    # seal_payload_sha256 = SHA-256 of canonical JSON without the hash field itself.
    # The on-disk file hash differs once the field is inserted; that file digest is
    # recorded externally (sidecar / build_summary), never claimed as the payload hash.
    seal_payload_sha = write_json(seal_path, seal)
    seal["seal_payload_sha256"] = seal_payload_sha
    seal_file_sha = write_json(seal_path, seal)
    seal_file_sidecar = seal_dir / "seal_receipt.file_sha256"
    seal_file_sidecar.write_text(seal_file_sha + "\n", encoding="utf-8")
    return {
        **seal,
        "seal_file_sha256": seal_file_sha,
    }
