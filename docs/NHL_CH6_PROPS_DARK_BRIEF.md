# NHL Chapter 6 — props dark brief

**Phase:** Proj vs line. **Zero PLAY. Zero LEAN.**  
**Reads:** Ch5 `PlayerProjection` only. Do **not** re-score.  
**Stamp frozen:** shrink `0.85` · Ch2 TOI + tandem · Ch3 coeffs · Ch4 team KEI · Ch5 scorer  
**Scorecard:** [`docs/NHL_CH6_PROPS_DARK_SCORECARD.md`](./NHL_CH6_PROPS_DARK_SCORECARD.md)

---

## Formula

```text
edge = PlayerProjection[market] − trusted_Best
```

Odds-backed skater markets (`icehockey_nhl`), **only if** the Odds client returns them:  
`goals assists pts sog`.  
`SAVES` exists on Ch5 but Odds has **no** coded key → goalie rows stay **—** while `STARTER_GATE = unknown`.

Untrusted / missing Best / starter-unknown → **—**. Tag always **PASS**.

---

## Register (still dark — not emitted)

| Name                      | Value                        |
| ------------------------- | ---------------------------- |
| `PROP_PLAY`               | `≥ 4.0` abs **and** `≥ 0.6σ` |
| `PROP_PLAY_CAP_PER_SLATE` | `6`                          |
| `PROP_TOI_GATE`           | `8.0`                        |
| `STARTER_GATE`            | `unknown` → no goalie PLAY   |

---

## Allowlist

- Join Ch5 ↔ `icehockey_nhl` player props (goals/assists/pts/sog)
- Existing props surface: **proj, Best, edge, σ**
- Untrusted Best / starter-unknown → —
- Star scorecard + goalie dash rows
- Register only (still dark)
- NHL-only CI

---

## Forbidden

Tags on props · new player means · new TOI · team if · retune Ch3/Ch4 · fantasy · inventing Odds saves · NBA/WNBA/CFB/NFL

---

## Gates

- Displayed mean == Ch5 field
- No fake book
- No PLAY/LEAN string on a prop
- Goalie starter-unknown rows stay —
- Team board (Ch4) unchanged · FLA@CAR puck −0.94
- NBA/WNBA/CFB untouched

---

## Done

Stop after dark + screenshot. Tags are a later PR. Chapter 7 fantasy is queued and must read this same object.
