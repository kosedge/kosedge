# NBA Chapter 0 — discovery brief

**Phase:** Audit. **No** pack, **no** KEI, **no** tags, **no** props.  
**Plan:** [`artifacts/NBA_ENTERPRISE_PLAN.md`](../artifacts/NBA_ENTERPRISE_PLAN.md)  
**Companion:** [`docs/NBA_CH0_AUDIT.md`](./NBA_CH0_AUDIT.md)  
**Leave alone:** CFB · NFL · CBB

---

## Purpose

Lock the enterprise spine and answer, with paths, what already exists on `/pro/nba` and `basketball_nba` before anyone types a coefficient.

**One rule (repeated):** team line, props, and fantasy must read the same `PlayerProjection`. That is the NFL miss. If that object isn’t real, you don’t get a props tab.

---

## Allowlist (this PR)

- `artifacts/NBA_ENTERPRISE_PLAN.md`
- `docs/NBA_CH0_DISCOVERY_BRIEF.md`
- `docs/NBA_CH0_AUDIT.md`

No wrapper. No scraper. No ratings JSON.

---

## Register only (do not code)

| Name                      | Value                |
| ------------------------- | -------------------- |
| `PLAYER_YEAR_WEIGHTS`     | `0.20 / 0.30 / 0.50` |
| `MINUTE_GRID_SUM`         | `240`                |
| `PROP_PLAY`               | `≥ 4.0 AND ≥ 0.6σ`   |
| `PROP_PLAY_CAP_PER_SLATE` | `8`                  |
| `ODDS_SPORT_KEY`          | `basketball_nba`     |

---

## Forbidden

- Pack / emit / tags
- Team `if`
- DARKO / EPM / CTG as SoT
- CFB / NFL edits
- Props tab treated as Ch6 without `PlayerProjection`
- Sneaky NFL prop rewrite

---

## Next PR (from audit)

| Pick  | Meaning                                                        |
| ----- | -------------------------------------------------------------- |
| **A** | Market exists → Chapter 1 team prior                           |
| **B** | No NBA Stats path → fetcher, then Ch1                          |
| **C** | Market missing → wire `basketball_nba` first, still no ratings |

**Written pick:** **A** — see audit § Decision.

Do **not** start Chapter 1 until this brief + audit merge with A/B/C written down.
