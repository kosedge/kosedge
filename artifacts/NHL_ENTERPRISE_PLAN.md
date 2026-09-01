# NHL Enterprise Plan

**Status:** Chapter 0 audit only. Markets live; **no** KEI pack, **no** props tags, **no** invented KEINHL.  
**Prod branch:** `deploy-vercel`  
**Leave alone:** NBA · WNBA · CFB · NFL  
**One rule:** team line, props, and fantasy read the **same** `PlayerProjection`. That is the NFL miss. If that object isn’t real, you don’t get a props tab.

Hockey is not NBA with skates. Same desk contract. Different physics.

Prod already says it: `/edge-board/nhl` is **markets only**. KEI is blank on purpose. Do not invent a number to fill it.

---

## What you copy from NBA / WNBA

- Model → KEI → Edge vs trusted Best
- One projection object for team / props / fantasy
- PASS if Best is missing or untrusted
- Situation as classes, not team ifs
- Props dark before tags
- Grades before opening night (**Sep 29**)

---

## What is different

|           | Basketball      | NHL                                                                        |
| --------- | --------------- | -------------------------------------------------------------------------- |
| Time      | Minutes         | TOI + PP1 / PP2                                                            |
| Team GA   | Opponent + luck | Which goalie starts                                                        |
| Score     | ~110 pts        | ~3 goals. One bounce is the puck line                                      |
| Props     | PTS / REB / AST | Skater G / A / P / SOG. Goalie saves                                       |
| Late news | Lineup          | Starter often same-day. Unknown starter → no goalie PLAY, total sized down |
| Season    | 82 / 44         | **84** this year. Camps ~Sep 16. Preseason Sep 19–26                       |

**NFL props miss, hockey version:** do not map puck-line residue to “player to score.” Goals come from `TOI × shot rate × finishing`, shrunken. Saves come from `start_prob × shot volume × SV%`.

Do **not** blend MoneyPuck + NST + Evolving Hockey as the published line. **One SoT.**

Do **not** port NBA home `+2.0` or WNBA `+1.5`.

---

## Spine (don’t skip)

| Ch    | What                                                    | Why it exists                                                      |
| ----- | ------------------------------------------------------- | ------------------------------------------------------------------ |
| **0** | Discovery                                               | What’s already on `/edge-board/nhl`, `/pro/nhl/*`, `icehockey_nhl` |
| **1** | One-year team prior + **own** shrink + **own** filename | Temporary shell after stats path exists                            |
| **2** | 3y skater/goalie talent × 2026–27 TOI / role            | The actual model. Team prior becomes a residual                    |
| **3** | Situation classes (rest / B2B / travel / home)          | Classes, capped — not basketball coeffs                            |
| **4** | Team KEINHL + Edge Board                                | ML / puck line / totals only                                       |
| **5** | `PlayerProjection`                                      | Only scorer (skater + goalie means)                                |
| **6** | Props dark → tags later                                 | That object vs trusted Best. Cap 6 PLAY/slate. Starter gate        |
| **7** | Fantasy                                                 | Same object. No third math                                         |
| **8** | Previews / camp / futures                               | After Ch4+5                                                        |
| **9** | Grades                                                  | Team + each tagged prop before opening night (Sep 29)              |

**Multi-year stats live on players** (weights `0.20 / 0.30 / 0.50`). Not on three seasons of team goal differential alone.

**Props do not launch off puck-line residue.** If Ch2 / Ch5 slip, Ch6 waits. Dark week with no tags beats a fake desk.

---

## Register (constants — code only when a chapter authorizes)

| Name                      | Value                                                  | Chapter   |
| ------------------------- | ------------------------------------------------------ | --------- |
| `ODDS_SPORT_KEY`          | `icehockey_nhl`                                        | 0 / 4 / 6 |
| `PLAYER_YEAR_WEIGHTS`     | `0.20 / 0.30 / 0.50`                                   | 2         |
| `PROP_PLAY_CAP_PER_SLATE` | `6`                                                    | 6         |
| `STARTER_GATE`            | unknown starter → **no goalie PLAY**; total sized down | 6 / desk  |

---

## Object contract (Ch5+)

```text
TeamGamePrior ──┐
PlayerTalent    ├──► PlayerProjection ──► team line (sum/constraint)
TOI / role ─────┤                      ├─► props (vs trusted Best)
Situation (Ch3)─┘                      └─► fantasy (same means; scoring only)
Goalie start_prob ─────────────────────► saves / team GA
```

- No props means that fantasy cannot see.
- No fantasy sheet with its own G / A / P / SOG / SV.
- No team-if patches.
- No MoneyPuck / NST / Evolving Hockey blend as SoT.
- No inventing KEINHL to fill `/edge-board/nhl`.

---

## Chapter gates (short)

| Ch  | Enter when                    | Exit when                                            |
| --- | ----------------------------- | ---------------------------------------------------- |
| 0   | Plan locked                   | Audit picks A / B / C; brief+audit merged            |
| 1   | A — or **B after fetcher**    | One-year team prior pack + own shrink; no props      |
| 2   | Ch1 live                      | Skater/goalie talent × TOI/role; team prior residual |
| 3   | Ch2 live                      | Situation classes named + capped (hockey physics)    |
| 4   | Ch2+3 honest enough for sides | Team KEINHL + Edge Board ML/puck/totals              |
| 5   | Ch2 TOI/role real             | Single `PlayerProjection` type on spine              |
| 6   | **Ch5 exists**                | Props vs Best; starter gate; cap 6 PLAY              |
| 7   | Ch5 exists                    | Fantasy scores Ch5 only                              |
| 8   | Ch4+5                         | Previews / camp / futures                            |
| 9   | Before opening night (Sep 29) | Grade store team + tagged props                      |

---

## Explicit anti-patterns

1. **NFL sidecar** — props board and fantasy reading different means for one player-game.
2. **Puck-line → “player to score”** — forbidden residue map.
3. **Fill the blank KEI** — markets-only until Ch4 ships a real fair line.
4. **Blend public models** as the published SoT.
5. **Port basketball home coeffs**.
6. **Goalie PLAY** when starter is unknown.
7. **Touch NBA / WNBA / CFB / NFL** while building NHL.

---

## Chapter 0 deliverable

- `artifacts/NHL_ENTERPRISE_PLAN.md` (this file)
- `docs/NHL_CH0_DISCOVERY_BRIEF.md`
- `docs/NHL_CH0_AUDIT.md`

No wrapper, scraper, or ratings JSON in Ch0. Next PR is whatever the audit writes: **A / B / C**.
