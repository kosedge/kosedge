# Playing-time role caps — Phase 1 (2026-08-20)

**LIVE stays true.** Expert gate ships on Vercel immediately. Spine caps apply after Railway worker remat (`POST /nfl/ops/rebuild-props-layers?season=2026` weeks 1–18, then SUM draft rankings).

Diagnose: `data/ops/nfl-playing-time-diagnose-20260820.md`.

---

## What shipped

1. **`nfl_playing_time.py`** — role from SoT depth, hard share ceilings, conservation up the chart.
2. **`compute_qb_starter_shares`** — depth SoT ranks the room. Priors no longer crown QB3. Shares **QB1 0.94 / QB2 0.06 / QB3+ ≈ 0**.
3. **RB/WR/TE** — RB3+ cap 0.04 (committee keeps RB2 alive); WR4+ target prior 0.015 and blended cap 0.02.
4. **Expert / sleepers** — no “value” unless material volume **and** ADP ≤ 250 (high-confidence). Kills O’Connell ADP 438 / Cook 297 / Dorsett 410 on www **before remat**.

Injury / starter_out still uses `redistribute_team_usage_for_injuries` (QB1 residual → healthy QB2).

---

## Defaults (document before retune)

| Role | Ceiling |
|------|---------|
| QB1 | 0.94 (cap 0.98) |
| QB2 | 0.06 (cap 0.08) |
| QB3+ | **0** (cap 0.005) |
| RB3+ | 0.04 unless committee (RB2 stays ≥ ~0.28) |
| WR4+ | target prior 0.015, blend cap 0.02 |
| TE3+ | 0.04 |

Team budgets conserved: clipped share is reassigned to shallower depth, then renormalized.

---

## Before / after (unit + prod before)

| Player | Before (prod SUM) | After (role cap contract) |
|--------|-------------------|---------------------------|
| A.O'Connell LV QB3 | 3065 pass · #54 | share ≈ 0 → **&lt; ~80 pass yards** at 35 att × 17 × 7.2 |
| K.Cousins LV QB1 | 183 pass · #832 | **QB1 0.94** → starter-class (~3k+ at same YPA) |
| B.Cook NYJ QB3 | 3302 pass · Expert #1 | share ≈ 0; expert **hidden** (ADP 297) |
| G.Smith NYJ QB1 | 215 pass | **QB1** |
| J.Burrow / J.Allen | 4297 / 3533 | unchanged class (already SoT QB1) |
| C.McCaffrey | 1304/688 · #1 | RB1 not capped down |
| P.Dorsett | 478 rec | WR4 target ≤ 0.02; expert hidden |

2025 pool shape (`n≥4000` / pass–rec gap): **report after remat**, not in this PR. Caps reallocate within the team; they should not reopen a pass/rec war. If 2025 n≥4000 collapses, stop and retune QB1 share (0.94→0.92) before another cal pass.

Props mean == fantasy mean: same `qb_starter_share` / target_proxy on weekly baselines. No props-only patch.

---

## Smell tests (pytest)

- O’Connell-class room: QB3 share ≤ 0.01; implied season pass yards &lt; 80
- QB1 ≥ 0.90 of room
- Conservation: shares sum to 1.0
- Expert notes: ADP 438 / 297 / 410 → `[]`

---

## Remat (after Railway image)

```text
POST /nfl/ops/rebuild-props-layers?season=2026
POST /nfl/ops/materialize-fantasy-draft-rankings?season=2026
```

Do not bounce the worker while a remat is STARTED. Then re-check LV QBs + www Expert strip.

---

## Confident?

**Yes** on diagnose and on the contract (SoT role → caps → expert gate).

**Remaining gaps (not this PR):**

- Prod numbers until remat (engine code is inert on www until worker runs)
- Mendoza missing from the 940-row board (id/grain, not share math)
- Phase 2: camp/job-battle flags, coaching RBBC priors
- Stale SoT: if depth lists the wrong QB1, we now **trust it** — pack depth, don’t override with priors
- 2025 control pool after remat
