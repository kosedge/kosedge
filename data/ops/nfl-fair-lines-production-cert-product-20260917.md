# NFL Fair Lines PRODUCTION-CERT Product receipt — 2026-09-17

**Track:** Product (Ryan 2026-09-17)  
**Boards:** Coming soon stays ON.  
**Public flags:** `NFL_EDGE_BOARD_PUBLIC_ENABLED = false`, `CFB_EDGE_BOARD_PUBLIC_ENABLED = false`.  
**Certified run:** unbound (`run_id` + sha256 both `null`).  
**War-room practice SHA:** `pe_drive_poss_v1` / `b5ee9d80494bbc13b989174af0676afb1831a4cb11e678f2f243ac469b92d36b` — **rejected**. Alex NO CLEAR (all five gates FAIL). Not a production bind.  
**v2:** `pe_drive_poss_v2` diagnostic STOP — do not bind.  
**Production target:** unbound; waits a new clock/play freeze + checksum. Richer clock/play engine authorized as research only.  
**Recommendation:** **NO CLEAR**.

Packet: [`docs/ops/NFL_FAIR_LINES_PRODUCTION_CERT_PRODUCT_2026-09-17.md`](../../docs/ops/NFL_FAIR_LINES_PRODUCTION_CERT_PRODUCT_2026-09-17.md)  
Machine: [`packet.json`](./nfl-fair-lines-production-cert-product-20260917/packet.json)

## Shipped

- Cert-binding helper fail-closes missing / mismatched / stale `run_id` + sha256.
- Independent spread / ML / total gates default false.
- PLAY / Kelly stay suppressed.
- `/api/nfl/fair-lines` + `/pro/nfl/fair-lines` use `isNflFairLinesCustomerSurfaceClosed()`.
- Smoke: `scripts/nfl/nfl-fair-lines-production-cert-smoke.sh`.
- Tests: `apps/web/__tests__/lib/nfl-fair-lines-production-cert.test.ts`.

## Not shipped

- Public numbers
- Any market CLEAR
- Remat / invented numbers
- PLAY / Kelly chrome
- DFS / Line Curve / CFB

## Approvers

CoS: (empty)  
Ryan: (empty)

## Rollback

See the packet. Pin public + market + stake flags false, unbind the cert slot, redeploy `deploy-vercel`. No remat.
