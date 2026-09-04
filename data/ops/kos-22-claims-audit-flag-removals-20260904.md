# #10 Trust/Claims Audit — bounded FLAG removals (KOS-22)

**Date:** 2026-09-04  
**Owners:** CoS (execution) · Riley CLEAR (editorial gate)  
**Status:** Removals shipped on draft PR — CoS merges to `deploy-vercel`.

## Hard locks honored

- NOT a methodology/copy rewrite
- No new explanatory paragraphs / educational clutter on product pages
- Model Transparency held-out backtest left alone (C12 PASS)
- No PLAY invent · no Conf invent · no remat
- Remove/replace listed FLAG strings only

## Removals

| ID | Surface | Action |
| --- | --- | --- |
| C03 | Homepage | Removed `Sharper Data. Smarter Bets.` |
| C07 | `/methodology` | Removed real-framework promise clause |
| C09 | `/about` | Removed duplicate real-process promise |
| C20 | NFL props | `no mkt` → `N/A—DATA GAP` (#5 fail-visible) |
| C21 | `/pricing` | Removed `Built for long-term edge` |
| C23 | `/pro/nfl/overview` | Edges hint/desc: side only (dropped “and confidence”) |
| C24 | `/pro/nfl/overview` | Dropped ROI/EV live-performance promise; kept Performance→Model Transparency + TBD one-liner |
| C25 | `/pro/nfl/edges` | Removed `Min confidence:` chrome/filter (Conf% dark until Lab) |
| C26 | `/pro/clv-tracker` | Darked public beat-% / avg CLV; honest unavailable until Signal Ledger (page title unchanged; Riley U02) |

## Guard

`apps/web/__tests__/lib/claims-audit-source-lock.test.ts` greps key customer files so these strings cannot return silently.
