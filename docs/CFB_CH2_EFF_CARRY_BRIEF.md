# Chapter 2 Phase 2B — 2025 SP+ carry shrink (fit)

**Repo:** `kosedge/kosedge`  
**Base:** after Phase 2A + canary rewrite (near-ties)  
**Authorized s:** **0.85 only**

```text
eff' = 50 + 0.85 * (eff_2025 - 50)   # league target 50; no roster blend
```

## Write

- `EFF_CARRY_SHRINK = 0.85` in `priors.py` (compose reads via `efficiency.py`)
- Regenerated `cfb_efficiency_snapshot_2025_carry_2026.json` (post-shrink + `off_eff_pre_shrink`)
- Live `build_power_sot` + KEI re-emit (`--kei-only`; futures / Utah untouched)
- Scorecard

## Canaries (rewritten)

Keep: OSU #1 · BALL@OSU WP ≥ 0.90 · polarity · s=0.85 only · no team-if / RESPONSE / 1C–1E revert / PBP SoT  
Drop: exact top-7 order  
Replace: membership may change only ORE↔MISS and ND↔TEX

## Forbidden

`STRENGTH_NOISE` change · `WEIGHT_OFF_EFF` · roster blend · `MATCHUP_RESPONSE` · team if · invented s · Utah / NFL/CBB/MLB
