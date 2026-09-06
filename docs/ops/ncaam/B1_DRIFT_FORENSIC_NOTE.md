# B1 drift forensic investigation note — Phase 2.6F CR4

**Status:** OPEN — ownership: Alex  
**Do not change B1 code or scoring.** This note is for event-level receipt fill-in only.  
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
    "n_drift": null,
    "root_cause_hypothesis": "TODO — Alex"
  }
}
```

## Hard stops

- No B1 code changes in this CR4 track
- No unseal / scoring / Odds API live pulls for “fix”
- No promotion of forensic rebuild into live sealed package
- #490 / #491 / #496 / #497 untouched
