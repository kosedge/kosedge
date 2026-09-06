# B1 drift forensic investigation note — Phase 2.6F CR4

**Status:** OPEN — ownership: Alex (platform note folded for CR4 support)  
**Do not change B1 code, thresholds, or membership.** This note is for event-level receipt fill-in only.  
**Authoritative holdout recovery:** private R2 exact frozen v1.1 packages (not this path).

## Purpose

Separate forensic track for B1 (odds open/close timestamp integrity) drift investigation.
Raw + KenPom + odds reconstruction is explicitly **not** allowed to redefine the frozen
holdout. Use:

```bash
python scripts/ncaam/forensic_rebuild_2425_from_raw_kenpom_odds.py --dry-run
python scripts/ncaam/forensic_rebuild_2425_from_raw_kenpom_odds.py \
  --out-root /tmp/ncaam-forensic-2425-b1
```

## Platform forensic note (supports CR4 — no B1 code changes)

Observed tip drift: **65** events `B1_ELIGIBLE → IDENTITY_UNRESOLVED`.

Illustrative schools in the unresolved set:

- Loyola MD
- New Orleans
- Sam Houston St
- LIU

Root-cause hypothesis (platform): the tip used a **generic strip-final-token** path for odds name normalization. Current **governed-mascot strip** fail-closes correctly (does not invent campus-school / trailing-token matches).

**CR4 implication:** a raw+KenPom+odds rebuild cannot redefine frozen v1.1 membership or B1 eligibility. Disaster recovery remains exact R2 bytes only. No B1 / threshold / membership changes in this track.

## Ownership

| Role                      | Owner          | Responsibility                                                                              |
| ------------------------- | -------------- | ------------------------------------------------------------------------------------------- |
| Event-level receipt       | **Alex**       | Fill per-event B1 drift receipts (open/close/tip parseability, orientation, source row ids) |
| Forensic script isolation | Platform / CR4 | Ensure forensic path cannot promote live seal                                               |
| Frozen holdout authority  | CoS + R2 CR4   | Exact bytes in private retention-locked buckets                                             |

## Alex fill-in (event-level receipt)

Copy/extend as needed. Do not paste secrets or live Odds API payloads into git.

```json
{
  "schema_version": "ncaam-b1-drift-forensic-receipt-v1",
  "investigator": "Alex",
  "holdout_id": "ncaam_holdout_2024_25_v1_1",
  "forensic_only": true,
  "redefines_frozen_holdout": false,
  "platform_note": {
    "n_b1_eligible_to_identity_unresolved": 65,
    "example_schools": ["Loyola MD", "New Orleans", "Sam Houston St", "LIU"],
    "tip_behavior": "generic_strip_final_token",
    "current_behavior": "governed_mascot_strip_fail_closed",
    "supports_cr4": "raw_rebuild_cannot_redefine_frozen_v1_1"
  },
  "events": [
    {
      "espn_game_id": "TODO",
      "b7_join_key": "TODO",
      "tipoff": "TODO",
      "open_snapshot_ts": "TODO",
      "close_snapshot_ts": "TODO",
      "b1_status_observed": "TODO",
      "drift_class": "TODO",
      "notes": "TODO"
    }
  ],
  "summary": {
    "n_events_reviewed": null,
    "n_drift": 65,
    "root_cause_hypothesis": "tip generic strip-final-token vs current governed-mascot strip fail-closed — Alex to confirm event-level"
  }
}
```

## Hard stops

- No B1 code changes in this CR4 track
- No unseal / scoring / Odds API live pulls for “fix”
- No promotion of forensic rebuild into live sealed package
- #490 / #491 / #496 / #497 untouched
