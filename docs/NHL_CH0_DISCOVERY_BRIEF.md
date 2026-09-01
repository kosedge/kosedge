# NHL Chapter 0 — discovery brief

**Phase:** Audit. **No** pack, **no** filling the blank KEI, **no** tags, **no** props.  
**As of:** `2026-09-01`  
**Plan:** [`artifacts/NHL_ENTERPRISE_PLAN.md`](../artifacts/NHL_ENTERPRISE_PLAN.md)  
**Companion:** [`docs/NHL_CH0_AUDIT.md`](./NHL_CH0_AUDIT.md)  
**Leave alone:** NBA · WNBA · CFB · NFL

Hockey is not NBA with skates. Same desk contract. Different physics.

---

## Purpose

Lock the enterprise spine and answer, with paths, what already exists on `/edge-board/nhl`, `/pro/nhl/*`, and `icehockey_nhl` before anyone types a coefficient or invents a KEINHL print.

**One rule (repeated):** team line, props, and fantasy must read the same `PlayerProjection`. That is the NFL miss. If that object isn’t real, you don’t get a props tab.

Prod already says it: `/edge-board/nhl` is **markets only**. KEI is blank on purpose.

---

## Allowlist (this PR)

- `artifacts/NHL_ENTERPRISE_PLAN.md`
- `docs/NHL_CH0_DISCOVERY_BRIEF.md`
- `docs/NHL_CH0_AUDIT.md`

No wrapper. No scraper. No ratings / prior JSON. No code edits to NBA / WNBA / CFB / NFL.

---

## Register only (do not code)

| Name                      | Value                                                  |
| ------------------------- | ------------------------------------------------------ |
| `ODDS_SPORT_KEY`          | `icehockey_nhl`                                        |
| `PLAYER_YEAR_WEIGHTS`     | `0.20 / 0.30 / 0.50`                                   |
| `PROP_PLAY_CAP_PER_SLATE` | `6`                                                    |
| `STARTER_GATE`            | unknown starter → **no goalie PLAY**; total sized down |

---

## Forbidden

- Pack / emit / tags / inventing KEINHL
- Blending MoneyPuck + NST + Evolving Hockey as SoT
- Mapping puck-line residue to “player to score”
- Porting NBA home `+2.0` or WNBA `+1.5`
- Team `if`
- NBA / WNBA / CFB / NFL edits
- Props tab treated as Ch6 without `PlayerProjection`

---

## Next PR (from audit)

| Pick  | Meaning                                                               |
| ----- | --------------------------------------------------------------------- |
| **A** | Market + stats exist → Chapter 1 NHL prior (own shrink, own filename) |
| **B** | No stats path → fetcher, then Ch1                                     |
| **C** | A hidden KEINHL leftover exists → document, don’t blend               |

**Written pick:** **B** — see audit § Decision.

Do **not** start Chapter 1 until this brief + audit merge with A/B/C written down. NBA / WNBA stay parked.
