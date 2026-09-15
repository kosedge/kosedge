# KE Football Ratings research track

**Lock:** Ryan / CoS 2026-09-15. Research and design only. No production promote. Boards stay dark (`NFL_EDGE_BOARD_PUBLIC_ENABLED` / `CFB_EDGE_BOARD_PUBLIC_ENABLED` both false). No PFF. No vendor shopping. Do not invent another scoring equation. Do not treat #562 REVISE as permission to retune coefficients.

This folder is the ratings-research home. It is **not** a live ratings engine.

## How to read

| Artifact                                                                                                           | Role                                                                                 |
| ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| [`KE_FOOTBALL_RATINGS_ENGINE_INVENTORY_2026-09-15.md`](./KE_FOOTBALL_RATINGS_ENGINE_INVENTORY_2026-09-15.md)       | What already exists (NFL live + CFB live + CFB research). Inventory only.            |
| [`KE_FOOTBALL_GAP_MATRIX_AND_ARCHITECTURE_2026-09-15.md`](./KE_FOOTBALL_GAP_MATRIX_AND_ARCHITECTURE_2026-09-15.md) | NFL vs CFB gap matrix and proposed layer. Still inventory.                           |
| [`KE_FOOTBALL_V1_SPEC.md`](./KE_FOOTBALL_V1_SPEC.md)                                                               | **KE Football Ratings Engine v1 design.** Canonical metric specs. **STOP for Ryan.** |
| [`KE_FOOTBALL_V1_METRIC_MATRIX.md`](./KE_FOOTBALL_V1_METRIC_MATRIX.md)                                             | Metric × data × validation × buildability matrix (human).                            |
| [`KE_FOOTBALL_V1_METRIC_MATRIX.json`](./KE_FOOTBALL_V1_METRIC_MATRIX.json)                                         | Same matrix (machine companion).                                                     |

Prior cross-sport inventories (#556 / #558) remain historical context. Football cells were superseded by the 2026-09-15 football inventory, then designed here. ~**28%** proprietary KE estimate from #556 is **unchanged** by this design.

## Hard stops

- DESIGN ONLY. No implementation, fitting, production writes, UI, scoring changes, or board reopen.
- NFL is the reference implementation. CFB shares names and infrastructure concepts, not fake values.
- #559 / #560 are reconciled into the design and **not promoted**.
- #562 scoring REVISE is not a ratings component and is not a tuning justification.
- NFL remat / #564 / #567 is a **separate** track.

**STOP.** Next action, if any, is Ryan after reviewing the v1 spec.
