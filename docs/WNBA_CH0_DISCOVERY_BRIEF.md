# WNBA Chapter 0 — discovery brief

**Phase:** Audit. **No** pack, **no** tags, **no** new KEI emit.  
**As of:** `2026-09-01` (midseason — RS ends Sep 24; playoffs Sep 27)  
**Companion:** [`docs/WNBA_CH0_AUDIT.md`](./WNBA_CH0_AUDIT.md)  
**Leave alone:** NBA v0.1 · CFB · NFL

Do **not** copy the NBA pack. Own shrink, own filename when Ch1 starts.

---

## Purpose

Audit what already prints on `/edge-board/wnba` and `/pro/wnba/*` before anyone types a WNBA enterprise prior. Chapter 0 (possession-sim research stack) already exists — do **not** build a second engine beside it.

**Context:** This is midseason, not a summer prior. 2026 games already final are **not** a fit sample.

---

## Allowlist (this PR)

- `docs/WNBA_CH0_DISCOVERY_BRIEF.md`
- `docs/WNBA_CH0_AUDIT.md`

No wrapper. No scraper. No ratings / prior JSON. No code edits to NBA / CFB / NFL.

---

## Register only (do not code)

| Name                      | Value                                                    |
| ------------------------- | -------------------------------------------------------- |
| `MINUTE_GRID_SUM`         | `200` (40-min × 5)                                       |
| `PLAYER_YEAR_WEIGHTS`     | `0.20 / 0.30 / 0.50` (2024 / 2025 / 2026)                |
| `SITUATION_COEFFS`        | paper-sim on **WNBA** points — **not** NBA `+2.0 / −1.5` |
| `PROP_PLAY_CAP_PER_SLATE` | `4`                                                      |
| `ODDS_SPORT_KEY`          | `basketball_wnba`                                        |

---

## Forbidden

- Pack / emit / tags
- Copying NBA Ch1–Ch6 filenames or shrink
- Blending leftover board KEI into a new prior
- Team `if`
- CFB / NFL / NBA v0.1 edits
- Treating research props (`wnba-player-props-v1`) as enterprise Ch6

---

## Next PR (from audit)

| Pick  | Meaning                                                                 |
| ----- | ----------------------------------------------------------------------- |
| **A** | Market + stats exist → Chapter 1 WNBA prior (own shrink, own file)      |
| **B** | No stats path → fetcher, then Ch1                                       |
| **C** | Board KEI is an unknown leftover → document, replace later, don’t blend |

**Written pick:** **A** — see audit § Decision.

Do **not** start Chapter 1 until this brief + audit merge with A/B/C written down. NBA stays parked.
