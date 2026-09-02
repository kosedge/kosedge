# NHL Chapter 2 — TOI grid + goalie tandem brief

**Phase:** Usage geometry. **No** board emit.  
**Depends on:** Ch1 pack on disk (`NHL_TEAM_CARRY_SHRINK = 0.85` frozen)  
**Stamp:** `nhl-season-engine-v0.1`  
**Packs:** `nhl_toi_grid_2026.json` · `nhl_goalie_tandem_2026.json`  
**Scorecard:** [`docs/NHL_CH2_TOI_GRID_SCORECARD.md`](./NHL_CH2_TOI_GRID_SCORECARD.md)  
**Leave alone:** blank KEINHL · NBA · WNBA · CFB · NFL · Ch1 shrink

---

## Formula

```text
toi_sec_w = Σ_y w_y · toi_per_game_y     # w = 0.20 / 0.30 / 0.50 (23–24 / 24–25 / 25–26)
keep top 18 skaters / team by toi_sec_w
toi_share = toi_sec_w / Σ_18
toi_min   = toi_share × 300               # 5 on-ice × 60

gs_w      = Σ_y w_y · gs_y
gs_share  = gs_w / Σ_team                 # starter / backup / residual
```

Identity: `Σ toi_share = 1` · `Σ toi_min = 300` · `Σ gs_share = 1` per team.

Multi-team box rows (`MIN,VAN`) assign to the **last** abbrev.  
Does **not** rebase `nhl_team_prior_2026.json`. Does **not** retune `NHL_TEAM_CARRY_SHRINK`.

---

## Allowlist

| Item       | Path                                                          |
| ---------- | ------------------------------------------------------------- |
| Constants  | `nhl_season_engine/priors.py` (`NHL_TOI_GRID_SKATER_MINUTES`) |
| Reader     | `nhl_season_engine/toi_grid.py`                               |
| Packs      | `nhl_toi_grid_2026.json` · `nhl_goalie_tandem_2026.json`      |
| Rebuild    | `scripts/nhl/build_toi_grid_ch2.py`                           |
| Tests + CI | `tests/test_nhl_toi_grid_ch2.py` · NHL-only CI                |
| Docs       | this brief + scorecard                                        |

---

## Forbidden

- Filling `/edge-board/nhl` / KEINHL
- Retuning Ch1 shrink / rewriting team prior
- xG vendor · situation · player means (later chapters)
- NBA / WNBA minute-grid copy · CFB / NFL

---

## Gates

- 32 teams · 18 skaters · Σ share = 1 · Σ min = 300
- Goalie tandem Σ GS share = 1
- Ch1 shrink still 0.85 · KEINHL blank · cross-sport untouched

---

## Done

TOI grid + goalie tandem on disk.  
**Stop.** Not emit. Situation / KEI / props are later chapters.
