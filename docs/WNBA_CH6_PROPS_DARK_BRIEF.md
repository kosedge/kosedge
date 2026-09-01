# WNBA Chapter 6 — props dark brief

**Phase:** Proj vs line. **Zero PLAY. Zero LEAN.**  
**Reads:** Ch5 `PlayerProjection` only. Do **not** re-score.  
**Stamp frozen:** shrink `0.85` · grid `200` · Ch3 coeffs · Ch4 team KEI  
**Scorecard:** [`docs/WNBA_CH6_PROPS_DARK_SCORECARD.md`](./WNBA_CH6_PROPS_DARK_SCORECARD.md)

---

## Formula

```text
edge = PlayerProjection[market] − trusted_Best
```

Markets, **only if** `basketball_wnba` already returns them:  
`PTS REB AST 3PM` (Odds keys → `pts reb ast threes`).  
`PRA` / `PR` / `RA` exist on Ch5 but Odds has **no** WNBA key → **missing** (do not guess).

Untrusted / missing Best → **—**. Tag always **PASS**.

---

## Register (still dark — not emitted)

| Name                      | Value                        |
| ------------------------- | ---------------------------- |
| `PROP_PLAY`               | `≥ 4.0` abs **and** `≥ 0.6σ` |
| `PROP_PLAY_CAP_PER_SLATE` | `4`                          |
| `PROP_MINUTES_GATE`       | `10.0`                       |

---

## Allowlist

- Join Ch5 ↔ `basketball_wnba` player props
- Existing props surface: **proj, Best, edge, σ**
- Untrusted Best → —
- 8-row star scorecard
- Register only (still dark)
- WNBA-only CI

---

## Forbidden (honored)

Tags on props · new player means · new grid · team if · retune Ch3/Ch4 · fantasy · alts · NBA/CFB/NFL

---

## Gates

- Displayed mean == Ch5 field
- No fake book
- No PLAY/LEAN string on a prop
- Team board unchanged (Ch4 CON@ATL KEI)
- NBA HOU@OKC ~−4.2 · CFB BALL@OSU **−40.5**

---

## Done

Stop after dark. Fantasy is Chapter 7 later and must read this same `PlayerProjection` object.
