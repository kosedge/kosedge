# NBA Chapter 1 — team prior shell brief

**Phase:** Pack a temporary team prior. **No** Edge tags, **no** props, **no** fantasy scorer.  
**Depends on:** [#363](https://github.com/kosedge/kosedge/pull/363) merged  
**Stamp:** `nba-season-engine-v0.1`  
**Chosen:** `TEAM_CARRY_SHRINK = 0.85`  
**Scorecard:** [`docs/NBA_CH1_TEAM_PRIOR_SCORECARD.md`](./NBA_CH1_TEAM_PRIOR_SCORECARD.md)  
**Plan:** [`artifacts/NBA_ENTERPRISE_PLAN.md`](../artifacts/NBA_ENTERPRISE_PLAN.md)

---

## Formula

```text
team' = league_mean + s * (team_2025_26 − league_mean)
```

One `s` for the league. Paper-sim set `{0.70, 0.80, 0.85, 0.90}` — **picked 0.85** (order-preserving, modest compression; same spirit as CFB carry without reusing `EFF_CARRY_SHRINK`).

This is a **shell**. Chapter 2 player×minutes rebases it. Not the finished model.

---

## Allowlist (this PR)

| Item                         | Path                                                                                |
| ---------------------------- | ----------------------------------------------------------------------------------- |
| `TEAM_CARRY_SHRINK` + reader | `services/model-service/src/services/nba_season_engine/priors.py` · `team_prior.py` |
| 2025–26 snapshot pack        | `…/nba_season_engine/data/nba_team_prior_2025_26_carry_2026_27.json`                |
| Rebuild script               | `scripts/nba/build_team_prior_ch1.py`                                               |
| Tests                        | `services/model-service/tests/test_nba_team_prior_ch1.py`                           |
| Docs                         | this brief + scorecard                                                              |

---

## Source note

Intended SoT path from Ch0 audit: NBA Stats Advanced via `nba_data.py`. In this build env `stats.nba.com` timed out and `data.nba.com` 2025–26 RS scores were unpublished on CDN. Pack stamped from Basketball-Reference 2025–26 Team Ratings (unadjusted ORtg/DRtg/NRtg) + advanced-team **Pace** — same concepts as NBA Stats Advanced. Rebuild script documents the failover.

---

## Forbidden (honored)

- Player RAPM / minute grid (Ch2)
- Situation / B2B (Ch3)
- KEI emit, Edge PLAY/LEAN, props tab
- DARKO / EPM / CTG blend
- Team `if` / Finals bump
- CFB / NFL / CBB file edits
- Launching `/edge-board/nba` tags off this pack

---

## Gates

- 30 teams (minute-unaware OK)
- League mean net ≈ 0 after shrink (micro-offset from BR rounding documented on scorecard)
- Top/bottom of 2025–26 do not invert into lottery favorites
- No futures rewrite
- Published CFB BALL@OSU still **−40.5** (`kei_spread_home = -40.51`)

---

## Done

One `s` chosen, pack on disk, scorecard merged. Board still PASS/empty.  
**Stop.** Chapter 2 is next — 3y player × 2026–27 minutes — not a props desk.
