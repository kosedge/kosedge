# Independent validation checklist — MLB/NHL market contract (post–Grok reset)

Builder findings are **not** independent approval.

1. Re-read locked MLB/NHL decisions before code.
2. Confirm catalog ids and enums match `mlb-nhl-market-contract-v1`.
3. Re-run `apps/web/__tests__/lib/market-contract/market-contract.test.ts`.
4. Spot-check surface matrix rows against live files on `deploy-vercel`.
5. Verify this branch has **no** production UI diff beyond research modules/docs/tests.
6. Verify no threshold constants changed (`NHL_LEAN_EDGE_PTS=2.5`, `NHL_PLAY_EDGE_PTS=4.0`, MLB desk mins untouched).
7. Confirm `nhlDisplayMarketLabel` still maps Spread→Puck Line and Moneyline→Game ML OT/SO.
8. Confirm Regulation ML cannot pass the two-way ML helper.
9. Mark each contradiction OPEN/BLOCKED — no soft green.
10. Ryan-only: any PLAY/LEAN enablement or board promotion of Run Line / NHL ML.
