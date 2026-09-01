# NBA Chapter 6 — props dark brief

**Phase:** Proj vs line. **Zero PLAY. Zero LEAN.**  
**Reads:** Ch5 `PlayerProjection` only. Do **not** re-score.  
**Stamp frozen:** shrink `0.85` · Ch2 grids · Ch3 coeffs · Ch4 team KEI  
**Scorecard:** [`docs/NBA_CH6_PROPS_DARK_SCORECARD.md`](./NBA_CH6_PROPS_DARK_SCORECARD.md)

---

## Formula

```text
edge = PlayerProjection[market] − trusted_Best
```

Markets, **only if** the Odds client already returns them:  
`PTS REB AST 3PM PRA` (Odds keys → `pts reb ast threes pra`).  
`PR` / `RA` exist on Ch5 but Odds has **no** key → **missing** (do not guess).

Untrusted / missing Best → **—**. Tag always **PASS**.

---

## Register (still dark — not emitted)

| Name                      | Value                        |
| ------------------------- | ---------------------------- |
| `PROP_PLAY`               | `≥ 4.0` abs **and** `≥ 0.6σ` |
| `PROP_PLAY_CAP_PER_SLATE` | `8`                          |
| `PROP_MINUTES_GATE`       | `12.0`                       |

---

## Allowlist

- Join Ch5 ↔ `basketball_nba` player props
- Existing props surface: **proj, Best, edge, σ**
- Untrusted Best → —
- 10-row star scorecard
- Register only (still dark)
- NBA-only CI

---

## Forbidden (honored)

Tags on props · new player means · new grid · team if · retune Ch3/Ch4 · fantasy · alts / first basket / quarters · CFB/NFL

---

## Gates

- Displayed mean == Ch5 field
- No fake book
- No PLAY/LEAN string on a prop
- Team board unchanged
- CFB BALL@OSU **−40.5**

---

## Done

Stop after dark. Tags are a later PR. Chapter 7 fantasy is later and must read this same object.
