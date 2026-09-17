# NFL Fair Lines PRODUCTION-CERT — Product track (2026-09-17)

**Track:** Product  
**Authority:** Ryan OS 2026-09-17  
**Repo / base:** `kosedge/kosedge` · `deploy-vercel`  
**Public numbers:** **OFF** (Coming soon ON)  
**Recommendation:** **NO CLEAR** — cert-binding + smoke harness only

Machine twin: [`data/ops/nfl-fair-lines-production-cert-product-20260917/packet.json`](../../data/ops/nfl-fair-lines-production-cert-product-20260917/packet.json)  
Ops receipt: [`data/ops/nfl-fair-lines-production-cert-product-20260917.md`](../../data/ops/nfl-fair-lines-production-cert-product-20260917.md)

This packet does **not** reopen Fair Lines, Overview, or Edge Board. It does **not** remat, invent numbers, CLEAR a market, or authorize PLAY / Kelly.

CoS:
Ryan:

---

## Hard locks held

| Lock | Value | Notes |
| ---- | ----- | ----- |
| `NFL_EDGE_BOARD_PUBLIC_ENABLED` | `false` | Coming soon ON |
| `CFB_EDGE_BOARD_PUBLIC_ENABLED` | `false` | Independent; untouched |
| Spread / ML / total public gates | `false` | Independent; not bundled |
| PLAY / Kelly | `false` | Separate authorization required |
| Certified `run_id` + `sha256` | unbound (`null`) | Do not invent a hash |
| Remat / invented numbers | none | Product harness only |
| DFS / Line Curve / CFB | out of scope | Not this PR |

---

## What shipped (Product)

1. **Cert-binding** in `apps/web/lib/cfb-edge-board-public.ts` — `bindNflFairLinesCertifiedRun` fail-closes on:
   - unbound certified slot
   - missing `run_id`
   - missing / invalid sha256
   - `run_id` mismatch
   - sha256 mismatch
   - missing `certifiedAt`
   - stale (default max age 168h)
2. **Independent market gates** (default false): `NFL_FAIR_LINES_PUBLIC_SPREAD_ENABLED`, `NFL_FAIR_LINES_PUBLIC_ML_ENABLED`, `NFL_FAIR_LINES_PUBLIC_TOTAL_ENABLED`.
3. **Fair Lines paths** — `/api/nfl/fair-lines` and `/pro/nfl/fair-lines` use `isNflFairLinesCustomerSurfaceClosed()`. Customer chrome stays Coming soon. INTERNAL QA is not a CLEAR.
4. **Smoke harness** — `scripts/nfl/nfl-fair-lines-production-cert-smoke.sh` + `apps/web/__tests__/lib/nfl-fair-lines-production-cert.test.ts`.

Public certified paint still requires **all** of: master NFL public flag + at least one market gate + a valid cert bind. None of those are on.

---

## Product release packet slots

Approver slots stay empty. Filling a name here is not a CLEAR.

| Slot | Status | CoS | Ryan |
| ---- | ------ | --- | ---- |
| Public numbers (master `NFL_EDGE_BOARD_PUBLIC_ENABLED`) | HOLD |  |  |
| Fair Lines spread | HOLD |  |  |
| Fair Lines moneyline | HOLD |  |  |
| Fair Lines total | HOLD |  |  |
| PLAY chrome | HOLD |  |  |
| Kelly / stake | HOLD |  |  |
| Certified run bind (`run_id` + sha256) | UNBOUND |  |  |

Do not piggyback ML or total on a later spread CLEAR. Do not treat INTERNAL=`1` as a public CLEAR.

---

## Rollback

No remat. No production means rewrite. Revert the Product harness or pin the constants:

1. Keep / set `NFL_EDGE_BOARD_PUBLIC_ENABLED = false`.
2. Keep / set `CFB_EDGE_BOARD_PUBLIC_ENABLED = false`.
3. Keep / set `NFL_FAIR_LINES_PUBLIC_SPREAD_ENABLED`, `_ML_`, `_TOTAL_` all `false`.
4. Keep / set `NFL_FAIR_LINES_PLAY_ENABLED = false` and `NFL_FAIR_LINES_KELLY_ENABLED = false`.
5. Clear certified slots to unbound: `NFL_FAIR_LINES_CERTIFIED_RUN_ID`, `_SHA256`, `_AT` = `null`.
6. Redeploy `deploy-vercel` (web). Railway remat is **not** required.
7. Verify `/pro/nfl/fair-lines` shows **Coming soon** (no ghost table).
8. Verify `/api/nfl/fair-lines` returns **503** empty (`nfl_edge_board_unavailable`).
9. Optional: `bash scripts/nfl/nfl-fair-lines-production-cert-smoke.sh`.

If this PR is the only change, `git revert` of the merge commit is sufficient.

---

## Out of scope

- Public market CLEAR
- Rematerialize / invented KEI or fair
- PLAY / Kelly / Best Bet chrome
- DFS
- Line Curve
- CFB
- Edge Board / Overview reopen
