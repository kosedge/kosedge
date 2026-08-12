# NFL fantasy ADP-deviation QA flags

Date: 2026-08-12  
Branch: `feat/nfl-fantasy-adp-qa-flags`  
Doctrine: Extreme model-vs-ADP disagreement is allowed — flagged and explainable, not silent alpha. Players are not auto-hidden.

## Config

`apps/web/lib/fantasy/adp-qa-flags.ts`

| Position | \|modelRank − ADP\| |
|----------|---------------------|
| Default (RB / WR / QB1) | **≥ 40** |
| TE or QB2 (pos rank ≥ 13) | **≥ 60** |

Unmatched ADP (—) or cross-format (Value Δ blank) → **no flag**.

## Example flagged rows (Half-PPR, illustrative)

1. **Mike Gesicki** CIN TE8 — model #47 vs ADP ~251 (\|Δ\| ~204) → **High deviation · Model ≫ market**. Drivers: CIN TE8 role, ~620 rec yards, Value Δ, VOR, preseason sim. Expert copy still suppresses 7.7 rec TD headlines.
2. **WR3 value** — model #50 vs ADP ~90 (\|Δ\| 40) → **Model ≫ market** with volume + Value Δ. Normal \|Δ\| 6–8 stays uncluttered.
3. **Market ≫ model RB** — model #72 vs ADP ~22 (\|Δ\| 50) → **Market ≫ model** (board is ahead of the sim).

## Surfaces

Draft rankings + player card, full player page, sleepers. Chip is absent on in-threshold ranks.

## Smoke

Gesicki-class gap shows flag + drivers; a fair WR/RB rank has no chip.
