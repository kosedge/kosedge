# NHL Chapter 1 — team prior shell brief

**Phase:** Shrink the raw 2025–26 team box. **No** board emit.  
**Depends on:** [#391](https://github.com/kosedge/kosedge/pull/391) merged (fetcher)  
**Stamp:** `nhl-season-engine-v0.1`  
**Chosen:** `NHL_TEAM_CARRY_SHRINK = 0.85`  
**Reads:** `nhl_team_box_2025.json` only  
**Pack:** `nhl_team_prior_2026.json`  
**Scorecard:** [`docs/NHL_CH1_TEAM_PRIOR_SCORECARD.md`](./NHL_CH1_TEAM_PRIOR_SCORECARD.md)  
**Leave alone:** NBA · WNBA · CFB · NFL · blank KEINHL

---

## Formula

```text
team' = league_mean + s * (team_2025_26 − league_mean)
```

Applied to **GF**, **GA**, and **net** (`GF − GA`). One `s` for the league.  
Paper-sim set `{0.70, 0.80, 0.85, 0.90}` — **picked 0.85** (order-preserving, modest compression). Own constant **`NHL_TEAM_CARRY_SHRINK`** — do **not** reuse NBA/WNBA shrink.

This is a **shell**. Chapter 2 is TOI grid + goalie tandem. Not emit.

---

## Allowlist (this PR)

| Item                             | Path                                                                 |
| -------------------------------- | -------------------------------------------------------------------- |
| `NHL_TEAM_CARRY_SHRINK` + reader | `…/nhl_season_engine/priors.py` · `team_prior.py`                    |
| Prior pack                       | `…/nhl_season_engine/data/nhl_team_prior_2026.json`                  |
| Rebuild                          | `scripts/nhl/build_team_prior_ch1.py`                                |
| Tests + CI                       | `tests/test_nhl_team_prior_ch1.py` · NHL-only path in `pr-check.yml` |
| Docs                             | this brief + 32-team scorecard                                       |

---

## Forbidden (honored)

- Filling `/edge-board/nhl` / blank KEINHL
- xG vendor (MoneyPuck / NST)
- New player tables
- Situation layer
- NBA / WNBA coeffs
- CFB / NFL

---

## Gates

- 32 rows · mean net ≈ 0 (exact `0.0` here — closed league)
- 2025–26 top/bottom don’t invert
- KEINHL still blank
- NBA / WNBA / CFB untouched

---

## Done

One `s` chosen, pack on disk.  
**Stop.** Chapter 2 is TOI grid + goalie tandem (`docs/NHL_CH2_TOI_GRID_BRIEF.md`). Not emit.
