# D-2 gate table

**Decision:** `fabf87320453c274b2b8ec8e443b8af4709d8d24ff8fb6baa449fe3d739d4bd0`  
  `/workspace/fg-repair/imv-gate1-review-2026-10-02/DECISION_RYAN_t4335s14919_HOLDOUT_CLEAR_v3_1_v1.txt`  
  Ryan `t4335s14919`: `CLEAR: build the runner, IMV reviews, then open once`  
**Ruling:** `8ca00bc49b412c1524b4a0d5a1ebacdd7bc4fe26f3e6354d52cb549812dbb012`  
  `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v6.txt`  
**Erratum:** `14ac18190c89d3620a6f27d0a0be64fc8147c321063ca4aeaa459faa31fcde41`  
**Request v3.1:** `35cbb56e10cfe0ec3730441a453f171bda917e7c58ad3e5eb2fe2c573de5ef7b`  
**Export pin (le2023 dry-run):** on-disk `a38a55bb` (`46d2a565` is blob only)

This package implements D-2 only. It does not retune I-1..I-5 or K-2..K-4.
Opening remains blocked until IMV passes **this runner**.

| Gate | Code | STOP fixture |
|---|---|---|
| Listings TZ census; naive → STOP | `census_listings_tz` | F-NAIVE |
| Incomplete-row + count before join | `apply_incomplete_row_rule` | F-INC-TS, F-INC-DELTA, F-COMP-NULL, F-JOIN-FIRST |
| Observed excluded IDs in provenance | `write_provenance` | F-OK / le2023 (record, not a STOP) |
| On-disk `.v2` export pin | `pin_export_v2` | F-V2-MISSING, F-V2-BLOB, F-V2-MISMATCH |
| No 2024/25 open | `assert_path_not_holdout`, `--mode holdout` | F-NAME, F-HOLDOUT |
