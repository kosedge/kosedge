# Edge Board assemble quarantine scrub — #8 Phase C / NFL-V3

**Date:** 2026-09-04  
**Cite:** Phase B candidate **4** · NFL-V3 · OD-1 / KOS-15 · #2 S2 · #4 E5  
**Base:** `deploy-vercel` @ `5e5c410f` (includes 13b)

## Symptom (Phase A/B receipt)

`/api/edge-board/nfl/assemble` shipped quarantine vocabulary that can leak if UI binds:

| Field | Observed |
| --- | --- |
| `isBestBet` key on rows | 32/32 (all false) |
| matchupOverview **Watch** section | 32/32 |
| reason `mild_edge_watch_list*` | 7 |

Customer chrome must stay **PLAY / LEAN / PASS** only. OD-1 CLOSED: research WATCH → suppress to PASS; no fourth tag; no Best Bet productization.

## Fix (honesty only)

1. **Assemble choke point** — `scrubEdgeBoardAssembleCustomerRows` on every sport’s assemble JSON before response.
2. **Decision quarantine** — `quarantineDecisionForCustomer` **deletes** `isBestBet` / `is_best_bet` (false still leaks) and maps `mild_edge_watch_list*` → `mild_edge_pass*`.
3. **Matchup overview** — section heading **Watch** → **What flips** (source + residual scrub).
4. **Row builders** — stop emitting `isBestBet` on NFL edge-board rows / legacy game rows.

## Locks held

- No remat · no PLAY invent · no Conf invent · no props philosophy UI
- Desk fork stays HOLD (out of this PR)
- Do not reverse OD-1 (no WATCH→LEAN; no fourth customer tag)
- Engine may still emit watch-list reasons offline; customer assemble must not

## Verify

```bash
# Unit / source-lock
pnpm --filter @kosedge/web exec vitest run \
  __tests__/lib/edge-board-assemble-honesty.test.ts \
  __tests__/lib/nfl-dead-tiers.test.ts \
  __tests__/lib/edge-board-matchup-overview.test.ts \
  __tests__/lib/edge-board-product-center.test.ts

# Live assemble (may 504 under load — use when API responds)
curl -sS 'https://www.kosedge.com/api/edge-board/nfl/assemble?slate=week1' \
  -o /tmp/eb-assemble.json
node -e '
const j=require("/tmp/eb-assemble.json");
const rows=j.rows||[];
const hasBest=rows.filter(r=>"isBestBet" in r || "is_best_bet" in r).length;
const watch=rows.filter(r=>/(^|\\n)Watch(\\n|$)/.test(String(r.matchupOverview||""))).length;
const mild=rows.filter(r=>JSON.stringify(r).includes("mild_edge_watch_list")).length;
console.log({n:rows.length,hasBest,watch,mild});
'
# Expect after: hasBest=0, watch=0, mild=0
```

Do **not** merge — CoS owns merge.
