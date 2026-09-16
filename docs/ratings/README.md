# KE Football Ratings research track

**Lock:** Ryan / CoS 2026-09-15. Research only. No production promote. Boards stay dark (`NFL_EDGE_BOARD_PUBLIC_ENABLED` / `CFB_EDGE_BOARD_PUBLIC_ENABLED` both false). No PFF. No vendor shopping. Do not invent another scoring equation. Do not treat #562 REVISE as permission to retune coefficients.

This folder is the ratings-research home. It is **not** a live ratings engine.

**Phase 1 GO (2026-09-15):** measurement layer only. See [`KE_FOOTBALL_V1_PROVENANCE_AMEND_2026-09-15.md`](./KE_FOOTBALL_V1_PROVENANCE_AMEND_2026-09-15.md) and [`KE_FOOTBALL_V1_MEASUREMENT_PHASE1_2026-09-15.md`](./KE_FOOTBALL_V1_MEASUREMENT_PHASE1_2026-09-15.md). Team Strength / scoring / matchup / market / UI remain unauthorized.

**Phase 1B GO (2026-09-15):** measurement validation and repair only. See [`KE_FOOTBALL_V1_MEASUREMENT_PHASE1B_2026-09-15.md`](./KE_FOOTBALL_V1_MEASUREMENT_PHASE1B_2026-09-15.md). Team Strength still **HOLD**.

**Phase 2A GO (2026-09-16):** KE Off/Def Efficiency unit ratings only. See [`KE_FOOTBALL_V1_UNIT_RATINGS_PHASE2A_2026-09-16.md`](./KE_FOOTBALL_V1_UNIT_RATINGS_PHASE2A_2026-09-16.md). Team Strength still **HOLD**. Opponent adjustment not reopened (`NO_ADJUSTMENT_WINNER`).

## How to read

| Artifact                                                                                                           | Role                                                                      |
| ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| [`KE_FOOTBALL_RATINGS_ENGINE_INVENTORY_2026-09-15.md`](./KE_FOOTBALL_RATINGS_ENGINE_INVENTORY_2026-09-15.md)       | What already exists (NFL live + CFB live + CFB research). Inventory only. |
| [`KE_FOOTBALL_GAP_MATRIX_AND_ARCHITECTURE_2026-09-15.md`](./KE_FOOTBALL_GAP_MATRIX_AND_ARCHITECTURE_2026-09-15.md) | NFL vs CFB gap matrix and proposed layer. Still inventory.                |
| [`KE_FOOTBALL_V1_SPEC.md`](./KE_FOOTBALL_V1_SPEC.md)                                                               | Canonical metric specs (#569). Taxonomy amended by the provenance note.   |
| [`KE_FOOTBALL_V1_PROVENANCE_AMEND_2026-09-15.md`](./KE_FOOTBALL_V1_PROVENANCE_AMEND_2026-09-15.md)                 | **RAW → DERIVED → ADJUSTED → MODELED.** Supersedes the three-layer list.  |
| [`KE_FOOTBALL_V1_MEASUREMENT_PHASE1_2026-09-15.md`](./KE_FOOTBALL_V1_MEASUREMENT_PHASE1_2026-09-15.md)             | Phase 1 implementation note + Ryan examples.                              |
| [`KE_FOOTBALL_V1_MEASUREMENT_PHASE1B_2026-09-15.md`](./KE_FOOTBALL_V1_MEASUREMENT_PHASE1B_2026-09-15.md)           | Phase 1B finishing repair, per-component validation, bakeoff, scorecard.  |
| [`KE_FOOTBALL_V1_UNIT_RATINGS_PHASE2A_2026-09-16.md`](./KE_FOOTBALL_V1_UNIT_RATINGS_PHASE2A_2026-09-16.md)         | Phase 2A KE Off/Def Efficiency unit ratings (no Team Strength).           |
| [`KE_FOOTBALL_V1_METRIC_MATRIX.md`](./KE_FOOTBALL_V1_METRIC_MATRIX.md)                                             | Metric × data × validation × buildability matrix (human).                 |
| [`KE_FOOTBALL_V1_METRIC_MATRIX.json`](./KE_FOOTBALL_V1_METRIC_MATRIX.json)                                         | Same matrix (machine companion).                                          |

Prior cross-sport inventories (#556 / #558) remain historical context. Football cells were superseded by the 2026-09-15 football inventory, then designed here. ~**28%** proprietary KE estimate from #556 is **unchanged** by this design.

## Hard stops

- Measurement Phase 1 only. No Team Strength composite. No scoring, matchup, market, UI, or board reopen.
- NFL is the reference implementation. CFB shares names and infrastructure concepts, not fake values.
- #559 / #560 are reconciled into measurement where they fit and **not promoted**.
- #562 scoring REVISE is not a ratings component and is not a tuning justification.
- NFL remat / #564 / #567 is a **separate** track.
- Opponent adjustment in this phase is **ADJUSTED** (PIT SOS). #560 ridge stays **MODELED** research.

**STOP** after Phase 2A unit-rating scorecard is reviewable. Team Strength / overall weights remain unauthorized.
