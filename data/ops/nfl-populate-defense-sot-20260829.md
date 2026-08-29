# Defense SoT populate — durable IR/out + named starters (2026-08-29)

**Branch:** `cursor/populate-defense-sot-7d1e` → `deploy-vercel`  
**Prerequisite:** #305 on e253 (`git_sha=3af0ab115626`)  
**Doctrine:** source → DepthSotWorkItem → human accept → pack. **Zero accepts in this PR.**

## What

| Piece | Change |
|-------|--------|
| Scanner | `nfl_defense_sot_populate.py` — camp-desk durable IR/out + named EDGE vs live `defense_roles` |
| Accept path | `create_if_missing` on `defense_roles` when pack blank (explicit seed only) |
| CLI | `queue_camp_sot_flags.py --scan-defense` / `--queue-defense` |
| Queue | Same `queue/runtime/` DepthSotWorkItem path — no second SoT |

## Out of scope

- Weather feed / ID-map / CFB
- Invented 32-team defense charts
- Unit-shock rewrites
- Any Accept / remat

## Queue table (STOP for human accept list)

| team | player | pos | already-in-SoT | proposed T1 | pack_injury | kind |
|------|--------|-----|----------------|-------------|-------------|------|
| CAR | Jaelan Phillips | EDGE | no | T1 | (blank) | named_starter |
| CAR | Nic Scourton | EDGE | no | T1 | (blank) | durable_out |
| GB | Micah Parsons | EDGE | no | T1 | (blank) | durable_out |
| MIN | Jamal Adams | S | no | T1 | (blank) | durable_out |
| NO | Bryan Bresee | DL | no | T1 | (blank) | durable_out |
| SEA | Bud Clark | S | no | T1 | (blank) | durable_out |
| SF | Charvarius Ward | CB | yes | — | active | pack_seed |
| SF | Deommodore Lenoir | NB | yes | — | active | pack_seed |
| SF | Fred Warner | LB | yes | — | active | pack_seed |
| SF | Javon Hargrave | DL | yes | — | active | pack_seed |
| SF | Nick Bosa | EDGE | yes | — | active | pack_seed |
| SF | Talanoa Hufanga | S | yes | — | active | pack_seed |

**proposed_t1=6 · accepts_performed=0**

Notes:

- Adams / Scourton / Bresee / Parsons / Clark = durable IR/PUP from Camp Desk 2026-08-26 (+ Athletic/team IR).
- Phillips = named EDGE opposite Scourton (desk) — not invented depth behind him.
- Clark seeded as **depth** (not starter) — desk said “pushing for a role,” not crowned S1.
- SF pack seed left alone (already-in-SoT).
- Unknown teams stay empty (no shock).

## Human accept commands (after approval)

```bash
python scripts/nfl/queue_camp_sot_flags.py --scan-defense
# then per approved id:
python scripts/nfl/queue_camp_sot_flags.py --accept \
  data/ops/nfl-daily-intel/queue/runtime/work-item-….json --dry-run
# only after human OK:
python scripts/nfl/queue_camp_sot_flags.py --accept \
  data/ops/nfl-daily-intel/queue/runtime/work-item-….json --write --rematerialize --actor desk
```

## Tests

`tests/test_nfl_defense_sot_populate.py` (+ existing `test_nfl_defense_depth_sot.py`)
