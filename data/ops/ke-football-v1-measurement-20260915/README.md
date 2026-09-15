# KE Football v1 Phase 1 measurement evidence

Research only. `production_promote=false`.

| File | What |
| ---- | ---- |
| `nfl_measurement.json` | NFL 2025 as_of week 18 examples + validation (no full snapshot dump) |
| `cfb_measurement.json` | CFB 2025 as_of week 13 examples + validation |
| `validation.json` | Next-game EPA, stability, missingness, provenance, leakage probes |
| `disruption_inventory.json` | Per-event column audit; `weights_assigned=false` |
| `provenance.json` | RAW → DERIVED → ADJUSTED → MODELED |

Narrative: `docs/ratings/KE_FOOTBALL_V1_MEASUREMENT_PHASE1_2026-09-15.md`.

PBP cache (gitignored): `data/cfb/research/ke_football_pbp/`. Do not write 2026 into the Aug 13 historical lake.
