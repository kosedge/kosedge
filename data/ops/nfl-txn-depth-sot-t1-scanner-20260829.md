# Free NFL txn → DepthSot T1 scanner (2026-08-29)

**Propose only.** Sleeper (+ optional PFR) diff vs live pack `injury_status` /
`depth_order` → `proposed_patch` queue items. No auto-accept. No means / props /
fantasy writes from the feed. Accept remat reuses `live_remat_fn` (rebuild-props
+ companion materialize-fantasy).

## Commands

```bash
python scripts/nfl/ingest_nfl_transactions.py --scan
python scripts/nfl/queue_camp_sot_flags.py --scan-txns
python scripts/nfl/queue_camp_sot_flags.py --scan-txns --queue   # upsert only
python scripts/nfl/queue_camp_sot_flags.py --scan-txns --alert-t1
```

Cache (gitignored): `data/ops/nfl-daily-intel/cache/`.

## Live prove (2026-08-29, print only — no accepts)

| Player | Disposition |
|--------|-------------|
| HOU Jayden Higgins | already in SoT (`out`) — **no new T1** |
| BAL Danny Pinter | already in SoT (`out`) — **no new T1** |
| LAC Tyler Biadasz | already in SoT (`out`) — **no new T1** |
| NYG Calvin Austin III | no pack row / #299 — **no new T1** |

Would-open T1 (not accepted): HOU Graham Mertz (IR), NYG Tyrone Tracy Jr. (Out).

ATL Penix stays open-race safe: feed may open T2 `injury_status` only — never
`competition_status` / depth crowns.
