# NBA Enterprise Plan

**Status:** Chapter 0–1 merged. Chapter 2 roster×minutes rebased (`TEAM_REBASE_RESIDUAL_CAP=3.0`). No KEI / tags / props until Ch5 `PlayerProjection`. `TEAM_CARRY_SHRINK=0.85` unchanged.  
**Prod branch:** `deploy-vercel`  
**Leave alone:** CFB · NFL · CBB  
**One rule:** team line, props, and fantasy read the **same** `PlayerProjection`. That is the NFL miss. If that object isn’t real, you don’t get a props tab.

---

## Spine (don’t skip)

| Ch    | What                               | Why it exists                                                    |
| ----- | ---------------------------------- | ---------------------------------------------------------------- |
| **0** | Discovery                          | What’s already on `/pro/nba` and `basketball_nba`                |
| **1** | One-year team prior + shrink       | Temporary shell, like CFB carry                                  |
| **2** | 3y player talent × 2026–27 minutes | The actual model. Team prior becomes a residual                  |
| **3** | B2B / travel / rest / home         | Classes, capped                                                  |
| **4** | Team KEI + Edge Board              | Sides/totals only                                                |
| **5** | `PlayerProjection`                 | Only scorer                                                      |
| **6** | Props                              | That object vs trusted Best. Hard minutes gate. Cap 8 PLAY/slate |
| **7** | Fantasy                            | Same object. No third math                                       |
| **8** | Previews / camp / futures          | Utah rule on futures                                             |
| **9** | Grades                             | Team + each tagged prop before opening night                     |

**Multi-year stats live on players** (weights `0.20 / 0.30 / 0.50`). Not on three seasons of team net rating.

**Props do not launch off spread residue.** If Ch2 slips, Ch6 waits. Dark week with no tags beats a fake desk.

---

## Register (constants — code only when a chapter authorizes)

| Name                      | Value                | Chapter   |
| ------------------------- | -------------------- | --------- |
| `PLAYER_YEAR_WEIGHTS`     | `0.20 / 0.30 / 0.50` | 2         |
| `MINUTE_GRID_SUM`         | `240`                | 2 / 5     |
| `PROP_PLAY`               | `≥ 4.0 AND ≥ 0.6σ`   | 6         |
| `PROP_PLAY_CAP_PER_SLATE` | `8`                  | 6         |
| `ODDS_SPORT_KEY`          | `basketball_nba`     | 0 / 4 / 6 |

---

## Object contract (Ch5+)

```text
TeamGamePrior ──┐
PlayerTalent    ├──► PlayerProjection ──► team line (sum/constraint)
MinutesGrid ────┤                      ├─► props (vs trusted Best)
Situation (Ch3)─┘                      └─► fantasy (same means; scoring only)
```

- No props means that fantasy cannot see.
- No fantasy sheet with its own PTS/REB/AST.
- No team-if patches.
- No DARKO / EPM / CTG as SoT.

---

## Chapter gates (short)

| Ch  | Enter when                    | Exit when                                    |
| --- | ----------------------------- | -------------------------------------------- |
| 0   | Plan locked                   | Audit picks A / B / C; brief+audit merged    |
| 1   | A (or B after fetcher)        | One-year team prior pack + shrink; no props  |
| 2   | Ch1 live                      | Player talent × minutes; team prior residual |
| 3   | Ch2 live                      | Situation classes named + capped             |
| 4   | Ch2+3 honest enough for sides | Team KEI + Edge Board sides/totals only      |
| 5   | Ch2 minutes real              | Single `PlayerProjection` type on spine      |
| 6   | **Ch5 exists**                | Props vs Best; minutes gate; cap 8 PLAY      |
| 7   | Ch5 exists                    | Fantasy scores Ch5 only                      |
| 8   | Ch4+5                         | Previews / camp / futures (Utah rule)        |
| 9   | Before opening night          | Grade store team + tagged props              |

---

## Explicit anti-patterns

1. **NFL sidecar** — props board and fantasy reading different means for one player-game.
2. **Stub props forever** — today’s `NbaPlayerPropProjection` (minutes×default rates) is research scaffolding, **not** Ch6.
3. **Props from spread residue** — forbidden.
4. **Launching PLAY tags** before Ch9 harness can grade them.

---

## Chapter 0 deliverable

- `docs/NBA_CH0_DISCOVERY_BRIEF.md`
- `docs/NBA_CH0_AUDIT.md`

No wrapper, scraper, or ratings JSON in Ch0. Next PR is whatever the audit writes: **A / B / C**.
