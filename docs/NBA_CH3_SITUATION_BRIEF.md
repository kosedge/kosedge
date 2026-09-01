# NBA Chapter 3 — situation brief

**Phase:** Global modifiers on the frozen prior. **No** tags, **no** props scorer.  
**Depends on:** [#366](https://github.com/kosedge/kosedge/pull/366) merged (Ch5 scorer) · Ch2 rebased teams live  
**Stamp:** `nba-season-engine-v0.1`  
**Ch1 shrink:** `TEAM_CARRY_SHRINK = 0.85` (**unchanged**)  
**Residual cap:** `TEAM_REBASE_RESIDUAL_CAP = 3.0` (**unchanged**)  
**Scorecard:** [`docs/NBA_CH3_SITUATION_SCORECARD.md`](./NBA_CH3_SITUATION_SCORECARD.md)

---

## What this PR does

Four **classes** (not teams), one coefficient each, applied **on read** to the Ch2 team line:

1. **Home**
2. **B2B** (3-in-4 uses the same rest class when the schedule SoT flags it)
3. **Travel** (timezone-band threshold from venue SoT)
4. **Altitude** (venue class flag on DEN / UTA arenas — never `if team ==`)

Situation is capped so it cannot become a second prior. Paper-sim before pack write.  
PlayerProjection means stay talent×minutes; on-read copy-through scales PTS/USG only if Σ PTS would break the residual cap after the team-line adjust.

---

## Allowlist

| Item | Path |
| --- | --- |
| Constants | `priors.py` (`SITUATION_*`) |
| Reader / apply-on-read | `situation.py` |
| Venue class pack | `…/data/nba_venues_2026.json` |
| Schedule SoT + paper-sim | `…/data/nba_situation_2026.json` |
| Builder | `scripts/nba/build_situation_ch3.py` |
| Tests | `tests/test_nba_situation_ch3.py` (NBA-only CI) |
| Docs | this brief + scorecard |

---

## Forbidden (honored)

- Team `if` / Finals bump
- New player means / rewriting Ch2 minutes grid
- Changing `TEAM_CARRY_SHRINK` or residual cap
- Edge PLAY / props tab / launching `/edge-board/nba` tags
- CFB / NFL edits · Chapter 6

---

## Gates

- ORtg/DRtg stay league-sane after apply
- Σ PTS within residual cap (copy-through if needed)
- CFB BALL@OSU still **−40.5**
- No name-in-an-if
- Board still untagged

---

## Done

Coefficients registered + applied on read. Board still untagged.  
**Stop.** Chapter 4 (team KEI + Edge Board, PASS until trusted Best) is next. Chapter 6 still waits.
