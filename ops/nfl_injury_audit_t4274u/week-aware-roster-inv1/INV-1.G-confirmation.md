# INV-1.G — confirmation

## 2024–25 holdout unread

- No `roster_2024.csv` / `roster_2025.csv` / `listings_2024.csv` /
  `listings_2025.csv` holdout files were opened.
- Historical W1 pack **contents** for 2024 and 2025 were not read
  (files exist; classified EXISTING BUT UNVERIFIED by name/size only).
- Owned-DB NDJSON is a 2025-W1 ingest dump. Season/week **counts and
  column names** were taken; those rows were not used as holdout
  reconstruction or fit inputs.

## holdout-once.lock absent

Checked: `/workspace/ops/nfl_injury_audit_t4274u/holdout-once.lock`
is **absent**. This package did not write it.

## Also true

- No opening runner started
- No refit
- No source pinned as SoT
- No leakage PASS claimed
- Leftover untracked `ops/` evaluator / opening trees were not staged
  and not executed
