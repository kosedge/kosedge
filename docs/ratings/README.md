# KE Ratings research track

**Lock:** Ryan / CoS 2026-09-15. Inventory and research only. No production promote. Boards stay dark (`NFL_EDGE_BOARD_PUBLIC_ENABLED` / `CFB_EDGE_BOARD_PUBLIC_ENABLED` both false). No PFF. No vendor shopping. Do not invent another scoring equation.

This folder is the ratings-research home. It is **not** a live ratings engine.

## How to read (do not treat later docs as a blank slate)

| Artifact | PR | Role |
| --- | --- | --- |
| [`KE_RATINGS_ENGINE_EXISTING_INVENTORY_2026-09-15.md`](https://github.com/kosedge/kosedge/blob/cursor/ke-ratings-engine-inventory-fa52/docs/ratings/KE_RATINGS_ENGINE_EXISTING_INVENTORY_2026-09-15.md) | [#556](https://github.com/kosedge/kosedge/pull/556) (open) | Cross-sport existing-system inventory. Headline: ~**28%** of a proprietary KE Ratings Engine is present. Football cells in that matrix are the prior SoT. |
| [`KE_RATINGS_CFB_2026_PBP_PATH_AMENDMENT_2026-09-15.md`](https://github.com/kosedge/kosedge/blob/cursor/cfb-2026-sdv-current-proof-56c3/docs/ratings/KE_RATINGS_CFB_2026_PBP_PATH_AMENDMENT_2026-09-15.md) | [#558](https://github.com/kosedge/kosedge/pull/558) (open) | Amends #556 classification: data vs metric axes. CFB 2026 PBP is SDV, not CFBD-blocked. ~28% **unchanged**. |
| [`KE_RATINGS_NFL_CFB_GAP_MATRIX_2026-09-15.md`](https://github.com/kosedge/kosedge/blob/cursor/cfb-2026-sdv-current-proof-56c3/docs/ratings/KE_RATINGS_NFL_CFB_GAP_MATRIX_2026-09-15.md) | [#558](https://github.com/kosedge/kosedge/pull/558) (open) | First NFL+CFB gap matrix. Recommended first build was 2026 W−1 raw team-game metrics (**later built in #559**). |
| [`KE_FOOTBALL_RATINGS_ENGINE_INVENTORY_2026-09-15.md`](./KE_FOOTBALL_RATINGS_ENGINE_INVENTORY_2026-09-15.md) | this PR | Football-only inventory (NFL + CFB + shared). Extends #556 §4.1–4.2 / §5 after #555–#562. |
| [`KE_FOOTBALL_GAP_MATRIX_AND_ARCHITECTURE_2026-09-15.md`](./KE_FOOTBALL_GAP_MATRIX_AND_ARCHITECTURE_2026-09-15.md) | this PR | Reconciled NFL vs CFB gap matrix, data requirements, proposed canonical layer. **STOP for Ryan.** |

## CFB research chain this inventory reconciles

| PR | State | What it is | What it is not |
| --- | --- | --- | --- |
| [#555](https://github.com/kosedge/kosedge/pull/555) | open | Owned PBP inventory, loader, raw metric **definitions** | Ratings, opponent adj, live compose |
| [#558](https://github.com/kosedge/kosedge/pull/558) | open | 2026 SDV current-season proof + #556 amendment | Ratings implementation |
| [#559](https://github.com/kosedge/kosedge/pull/559) | open | 2026 W−1 **raw** unadjusted team-game metrics | KE Ratings (`opponent_adjusted=false`) |
| [#560](https://github.com/kosedge/kosedge/pull/560) | **merged** | Research opp-adj O/D EPA — **ADVANCE** (2025 sealed) | Spreads, totals, KEI, production promote |
| [#562](https://github.com/kosedge/kosedge/pull/562) | open | Efficiency → scoring — **REVISE** (margin helped, **totals missed**) | New scoring equation, board reopen |
| [#561](https://github.com/kosedge/kosedge/pull/561) | merged | Coming soon / public numbers parked | A ratings decision |

## Hard stops (this track)

- No production changes.
- No model fitting.
- No new scoring equation (#562 totals gate stands; do not loosen).
- No board reopen.
- No PFF / vendor shopping.
- NFL remediation is a **separate** track from this inventory.
- Returning-production / unit / coaching constants are **not** football efficiency.

**STOP.** Next action, if any, is Ryan / CoS after this review.
