# CoS handoff — Phase 0 inventory + Phase 1 spec

Ryan t4344u OPTION B (`47afd7f6`). Opening path STOPPED.

## Route to IMV

1. `artifacts/injury-roster-leakage-inventory-v1/` (Phase 0)
2. `artifacts/injury-week-aware-roster-spec-v1/` (Phase 1)

Ask IMV to accept the spec or return the exact gaps. Do not authorize
a holdout open. Do not treat this as a PASS.

## Verified vs claimed

See `VERIFIED-VS-CLAIMED.md`. Short version: week column ignored in
`load_rosters` / `load_rosters_dir` (opened). Source files are one row
per player-season, usually last-week / playoff (counted on ≤2023
pins). PIT 2023 QBs are week 19 WC (opened). le2023 Spec C / export
`a38a55bb` / fit `6a5490db` are leakage-invalidated as a consequence
of that wiring, not because those bytes were re-read in this pass.

## Pins (sha8)

- decision `47afd7f6`
- frozen script `8d188da2`
- builder `247744d2`
- writer `9947b880`
- producer `ae8f9585`
- null contract `ff8e6527`
- roster 2023 `f98283e6`
- roster 2019 `b00259cf`

## PR

Unmerged only. Do not merge, deploy, or publish.

## Not written

- `holdout-once.lock`
- 2024 / 2025 / 2026 reads
- production refit
