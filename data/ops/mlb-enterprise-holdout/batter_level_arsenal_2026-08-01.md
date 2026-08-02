# MLB batter-level lineup-ID arsenal (2026-08-01)

**Window:** densify target `2026-05-20 → 2026-07-17` (no Odds densify)  
**Stack held:** S0  
**Unused holdout:** frozen `2026-07-18 → 2026-08-10`  
**Flags (defaults):** `MLB_PITCH_MATCHUP_ENABLED=false`, `MLB_PITCH_MATCHUP_BATTER_LEVEL=false`

## What was built

1. Per-batter as-of contact-by-pitch-family index: `batter_contact_asof_index.json` (MLBAM batter id)
2. `get_batter_contact_as_of` with same-day leakage cutoff (as-of exclusive of game day)
3. `blend_lineup_batter_contact` — slot-weighted blend; requires enough batters/pitches
4. `resolve_batter_family_for_matchup` — batter-level when flag on + lineup IDs; else team-family
5. Lineup features include `person.id` for densify/live cards
6. Ablation arm **M1b** in `run_mlb_pitch_matchup_ablation` (M0 / M1 / M1b)
7. Unit tests: `tests/test_mlb_batter_level_arsenal.py` — **12** arsenal+batter tests passed locally

## Densify grade

| Config | Inter ML CLV | Inter RL CLV | Inter Tot CLV | WF Brier | Leak | Status |
|--------|-------------:|-------------:|--------------:|---------:|-----:|--------|
| M0 | — | — | — | — | — | **Not run yet** (needs Railway image with M1b wiring) |
| M1 / M1t | +0.00392 | 0.000 | +0.002 | 0.250 | 0 | Prior true-arsenal (team-family) — **no-ship** |
| M1b | — | — | — | — | — | **Pending densify** |

## Decision (current)

**Do not flip defaults.** Wiring ships OFF until M1b clears:

| Gate | Target | Result |
|------|--------|--------|
| Leakage | 0 | pending |
| Inter ML CLV | ≥ +0.010 | pending |
| RL/total not torched | hold | pending |

If M1b fails after densify: stop PA-mul research; architecture change (market-aware ML head) is the honest next path.

## How to grade

```bash
# After Railway deploy of this branch:
curl -sS -X POST "$MODEL_SERVICE_URL/api/jobs/mlb-pitch-matchup-ablation" \
  -H "x-internal-api-secret: $INTERNAL_API_SECRET" \
  -H "content-type: application/json" \
  -d '{"configs":["M0","M1","M1b"],"start":"2026-05-20","end":"2026-07-17"}'
```

Write metrics into `batter_level_arsenal_2026-08-01.json` and update this table. Ship only if M1b Inter ML CLV ≥ +0.010 with leak 0 and RL/total intact.
