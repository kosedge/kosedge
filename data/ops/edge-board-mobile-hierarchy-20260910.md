# Edge Board mobile hierarchy — presentation lock (2026-09-10)

Draft only. Desktop table frozen. Zero model / KEI / fair / edge / confidence / threshold / odds / open / bookmaker / game-ID / API / schema calculation changes.

## Components touched

| File | Role |
|------|------|
| `apps/web/components/EdgeBoardMobileCard.tsx` | New dedicated L1–L5 mobile composition (`lg:hidden` parent) |
| `apps/web/lib/edge-board-mobile-presentation.ts` | Presentation mapping + #508 fail-closed gates |
| `apps/web/components/EdgeBoard.tsx` | Mobile wrapper wires new card; desktop `<table>` path unchanged |
| `apps/web/lib/flat-rows-to-legacy.ts` | Pass-through `awayAbbr` / `homeAbbr` already computed by matchup context |

## Canonical value map (one source each)

| Customer slot | Row field(s) | Notes |
|---------------|--------------|--------|
| Current spread | `marketLineCurrent` else parsed `bestLine.bottom` | Home-signed decision/calc market |
| Current total | `marketOUCurrent` else parsed `bestOU` | |
| Kosedge Fair spread | `fairLineKei` else `keiLine.bottom` | Omit on pair mismatch |
| Kosedge Fair total | `fairOUKei` else `keiOU` | |
| Spread edge + side | `reconcileHandicapCustomerEdge` (#508) vs `fairLineKei` + decision market + `edgeMagnitudeLine` | Fail closed on disagreement |
| Total edge + direction | `reconcileTotalCustomerEdge` (#508) | Fail closed on disagreement |
| Recommendation | `toPublishActionLabel(actionLabel* ?? tag*)` → existing `displayActionLabel` | PLAY / LEAN / PASS only |
| Confidence | `modelConfidenceBand` if already on the row **and** in `reachableConfidenceBands()` | Omit if absent or unreachable HIGH |
| Open spread / total | `openLine.bottom` / `openOU` | Omit when blank |
| Line timestamp | `linesAsOf` → readable “Updated …” | NFL missing → “Market as-of unavailable” |
| Decision book | `bestLineBook` / `bestOUBook` **only when** that book’s painted price equals the decision number | Else omit badge (no decorative consensus book) |

Team labels: `presentationAbbr` → NFL `canonicalizeNflTeam` (truth layer). No UI nickname table. Favorite-labeled `SEA −2.5` (Unicode minus). Totals `O 44.5 / U 44.5`.

## #508 helper usage

- `reconcileHandicapCustomerEdge` / `reconcileTotalCustomerEdge` — magnitude + side; `DATA_GAP` → no painted edge
- `formatSelectedSideLineEdge` — `+1.4 pts` in L3 only
- `isFiniteNumber` / `EDGE_ARITH_TOLERANCE` — juice/open/fair collapse; decision-vs-best book identity
- JSX does not re-derive signs or sides

## Fail-closed (do not mask)

If decision market ≠ best-cell number: paint the **decision** line, drop book/juice (flag `spread_decision_vs_best_mismatch`). If Fair/Market/Edge disagree: keep status, omit side + magnitude. Do not invent a matching book.

## Desktop

`hidden lg:block` table, columns, KEI header, ActionDecisionCell (including desktop “Lean to”) unchanged. Breakpoint stays `lg`.

## Tests

- `apps/web/__tests__/lib/edge-board-mobile-presentation.test.ts`
- `apps/web/__tests__/components/EdgeBoardMobileCard.test.tsx`

## QA screenshots

Fixture gallery `/dev/edge-board-mobile-qa` (no Odds API). Production www first-paint at 393 was assemble-loading skeletons (client fetch) — not a usable before of the old 2×2 card; the removed `EdgeBoard.tsx` mobile block is the before.

| File | What |
|------|------|
| `data/ops/qa/edge-board-mobile-hierarchy/after-393-nfl-lean-card.png` | NFL LEAN @ 393 |
| `data/ops/qa/edge-board-mobile-hierarchy/after-393-nfl-lean-overview.png` | same + Overview open |
| `data/ops/qa/edge-board-mobile-hierarchy/after-393-cfb-empty-card.png` | CFB null/empty collapse |
| `data/ops/qa/edge-board-mobile-hierarchy/after-393x852.png` | full gallery 393×852 |
| `data/ops/qa/edge-board-mobile-hierarchy/after-375x812.png` | 375 |
| `data/ops/qa/edge-board-mobile-hierarchy/after-390x844.png` | 390 |
| `data/ops/qa/edge-board-mobile-hierarchy/after-402x874.png` | 402 |
| `data/ops/qa/edge-board-mobile-hierarchy/after-430x932.png` | 430 |
| `data/ops/qa/edge-board-mobile-hierarchy/after-tablet-820x1180.png` | tablet below lg (still cards) |
| `data/ops/qa/edge-board-mobile-hierarchy/after-desktop-1440x900.png` | desktop ≥lg |
| `data/ops/qa/edge-board-mobile-hierarchy/after-desktop-1440-table.png` | desktop table crop |

## L5 polish follow-on (draft)

Open Overview/Stats is shrink-wrap `min-h-11` disclosure (`text-kos-gold`), not `flex-1` / `rounded-lg` / filled CTA. Collapsed stays muted (`text-kos-gold/65`). Desktop ActionDecisionCell / “Lean to” untouched.

| File | What |
|------|------|
| `data/ops/qa/edge-board-mobile-l5-polish/after-393-overview-open.png` | NFL LEAN Overview open @ 393 |
