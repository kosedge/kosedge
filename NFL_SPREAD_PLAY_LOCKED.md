# LOCKED — NFL spread / totals / prop PLAY doctrine (Ryan Kos, 2026-09-03)

**Owner lock.** Not a suggestion. Do not retune, widen, or “busy up” the board without a new unused holdout **and** an explicit Ryan flip.

Holdout citation: `data/ops/nfl-play-only-holdout.md` · policy `spread_play_v2_cap7`.
Technical gates: `docs/NFL_ENTERPRISE_GATES.md` (same band — do not fork a second doctrine).

## Rules

1. **Spread PLAY** may fire only in the unused-holdout band that cleared:
   `2.5 ≤ |spread edge in points| < 7.0` (`spread_play_v2_cap7`).
   Below 2.5 → LEAN or PASS, **never PLAY**.
   At/above 7.0 → **not PLAY** in this band (cap7).

2. **One source of truth.** `publishTagSpread` and subscriber-facing `actionLabelSpread`
   (Edge Board badge via `displayActionLabel`, fair-lines, desk) must be the **same
   action** after any dead-tier display remap. No publish=PASS while the badge says PLAY.

3. **Totals PLAY stays sat.** Totals PLAY failed holdout (RED). Totals may be
   LEAN / PASS / STAY AWAY, **never PLAY**, until a new unused holdout greens and Ryan flips it.
   Do not retune totals to mint PLAY.

4. **Prop PLAY stays sat.** `PLAY_STAKE_ELIGIBLE` / `NFL_PROPS_PLAY_STAKE_ELIGIBLE` stays **False**.
   Do not enable prop PLAY tags or filters.

5. **Do not hunt PLAY.** A thin Week 1 slate is correct. Do not lower floors, raise
   confidence, or remap LEAN→PLAY to make the board look busier.

6. **HIGH / BEST VALUE unchanged.** Dead-tier honesty from PR #432 stays
   (HIGH / BEST VALUE chrome hidden while 0.72 base < 0.75). Do not retune confidence
   floors or HIGH cuts in the same change set as this lock.

## Out of scope for lock enforcement PRs

No remat, no KEI mint, no paywall, no Compare Odds book list, no calibration retune.

## Regression shape (Week 1 2026)

ARI@LAC `spreadEdge` 2.19 with confidence MEDIUM must **not** be PLAY (under 2.5 floor).
Publish and badge must agree after remap.
