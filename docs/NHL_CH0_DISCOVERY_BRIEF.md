# NHL Chapter 0 — discovery brief

**Phase:** Audit. **No** pack, **no** tags, **no** filling blank KEINHL.  
**As of:** `2026-09-01`  
**Clock:** camps ~**Sep 16** · preseason **Sep 19–26** · open **Sep 29** (~**84** games)  
**Companion:** [`docs/NHL_CH0_AUDIT.md`](./NHL_CH0_AUDIT.md)  
**Leave alone:** NBA · WNBA · CFB · NFL

Own constants and packs when chapters start — same playbook as NBA/WNBA, not a shared religion. Do **not** copy NBA/WNBA shrink or filenames.

---

## Purpose

Audit what already prints on `/edge-board/nhl` and `/pro/nhl/*` before anyone types an NHL enterprise prior or invents KEINHL numbers.

**Prod honesty:** `/edge-board/nhl` is **markets only**. Banner already says KEINHL is not shipped. Do not fill the blank.

---

## Allowlist (this PR)

- `docs/NHL_CH0_DISCOVERY_BRIEF.md`
- `docs/NHL_CH0_AUDIT.md`

No wrapper. No scraper. No ratings / prior JSON. No code edits to NBA / WNBA / CFB / NFL. No model-service `nhl_*` pack.

---

## Register only (do not code)

| Name                      | Value                                                    |
| ------------------------- | -------------------------------------------------------- |
| `ODDS_SPORT_KEY`          | `icehockey_nhl`                                          |
| `PLAYER_YEAR_WEIGHTS`     | `0.20 / 0.30 / 0.50`                                     |
| `PROP_PLAY_CAP_PER_SLATE` | `6`                                                      |
| `STARTER_GATE`            | `unknown` → **no goalie PLAY**                           |

Ch1 names (next chapter, not this PR): `NHL_TEAM_CARRY_SHRINK`, `nhl_team_prior_2026.json` — own constants, own file.

---

## Forbidden

- Pack / emit / tags
- Filling blank KEINHL on the Edge Board
- Copying NBA / WNBA Ch1 shrink or filenames
- Team `if`
- NBA / WNBA / CFB / NFL edits
- Treating Limited Props shell as enterprise Ch6
- Blending any leftover board number into a prior (none found — keep it that way)

---

## Next PR (from audit)

| Pick  | Meaning                                                                                      |
| ----- | -------------------------------------------------------------------------------------------- |
| A     | Market + stats exist → Chapter 1 prior (`NHL_TEAM_CARRY_SHRINK`, `nhl_team_prior_2026.json`) |
| **B** | No stats path → **fetcher**, then Ch1                                                        |
| C     | Hidden KEINHL leftover → document, don’t blend                                               |

**Written pick:** **B** — see audit § Decision.

Do **not** start Chapter 1 until this brief + audit merge with A/B/C written down. NBA / WNBA / CFB / NFL stay parked.
