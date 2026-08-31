# Chapter 2 Phase 1C — soft ceiling on qb_situation (power order frozen)

**Repo:** `kosedge/kosedge`  
**Base:** after qb_situation construction audit (#349)

Discovery locked: `score=80.4` is only the image of `index=1.38`; **43/125** at the cap including all top-7. Unclamped OSU **1.577** · HAW **1.502** · TCU **1.481**. Haircutting the clamp alone is forbidden.

## This PR

One global soft ceiling above ~1.25 so published index preserves **OSU > HAW > TCU**. Do not rewrite `talent_from_qb_stats`. Do not cut `WEIGHT_QB` / `MATCHUP_RESPONSE`. No team ifs. No week-0 power refit.

Success: Sayin ≠ Alejado as QB objects; top-7 flat; BALL still a cupcake. Hawaii polarity reported, not forced.

## Forbidden

Hard clamp haircut to flatten elites; `talent_from_qb_stats` in this PR; compose weights; team branches; Utah / NFL/CBB/MLB.
