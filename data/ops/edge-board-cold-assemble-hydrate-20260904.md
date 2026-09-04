# #12 GO-1 — Edge Board COLD assemble→hydrate (2026-09-04)

## Phase A receipts (cite labels — never average)

| Label | TTUEB |
| --- | --- |
| `01 VP-390 × NET-F4G × COLD` | **24980 ms** |
| `04 VP-430 × NET-F4G × COLD` | **767 ms** |

Budget **B-COLD-F4G-390**: provisional ≤8000 ms; any run >15000 = P0 open.
SoT cited in PR: Phase B budgets LOCKED 2026-09-04 (file may live outside repo).

## Root cause

1. `/edge-board/nfl` SSR shell is fast + honest (`Loading board…` + `data-missing` as-of) — correct; do not invent useful.
2. Assemble only started in client `useEffect` **after** JS hydrate → extra waterfall (U-A).
3. Client used `cache: "no-store"`, fighting page-data CDN reuse on IR/WARM.
4. NFL assemble always loaded `slate: "full"` then filtered to week1 → full-slate matchup enrich on the default tab.
5. Prod probe (2026-09-04): assemble cold origin ~20–25s (or 504 at pageData 25s); CDN HIT ~75ms. Variance matches Phase A 01 vs 04.

## Smallest fix

- Early assemble bootstrap in SSR HTML (`preload` + inline fetch bag) — start with parse, not post-hydrate.
- Client takes bootstrap promise; drop `cache: "no-store"`.
- NFL assemble honors requested `slate` (week1 enriches week1 only; fullCount badge omitted until Full tab).

Locks held: no redesign · no fake early TTUEB · no invent LCP · no #9 · honesty until assemble returns.
Alex remeasures 3× VP-390 F4G COLD + WARM + IR after promo. CoS owns merge.
