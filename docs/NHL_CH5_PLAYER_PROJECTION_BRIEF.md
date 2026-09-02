# NHL Chapter 5 — PlayerProjection brief

**Phase:** One pack, two types (skater + goalie). **No** board emit. **No** props.  
**Depends on:** Ch2 TOI grid + goalie tandem (#393) · Ch1 team prior (shrink **0.85** frozen)  
**Stamp:** `nhl-season-engine-v0.1`  
**Pack:** `nhl_player_projection_2026.json`  
**Scorecard:** [`docs/NHL_CH5_PLAYER_PROJECTION_SCORECARD.md`](./NHL_CH5_PLAYER_PROJECTION_SCORECARD.md)  
**Leave alone:** blank KEINHL · NBA · WNBA · CFB · NFL · Ch1 shrink · Ch2 packs

---

## Formula

```text
# Skater (per team, Ch2 top-18 TOI)
rate_stat = Σ_y w_y · ((stat/gp) / (toi_sec/60))   # w = 0.20 / 0.30 / 0.50
raw_G     = rate_g × toi_min
G         = raw_G × (Ch1_gf/gp / Σ raw_G)          # identity scale
A, SOG    = rate × toi_min                         # unscaled rate shape
P         = G + A
TOI_EV    = toi_min                                # raw box has no PP TOI
TOI_PP    = 0
σ         = pstdev(year rates) × minutes (± scale on G)

# Goalie (Ch2 tandem shares)
start_share = Ch2 gs_share                         # Σ ≈ 1.0
SV_pct, GAA = Σ w_y · season rates
SA          = sa_per_gs × start_share
SAVES       = SA × SV_pct
σ           = pstdev(year rates) · (volume on SA/SAVES)
```

Identity: `|Σ skater G − Ch1 GF/G| ≤ NHL_TEAM_REBASE_RESIDUAL_CAP (0.15)` · `Σ start_share ≈ 1.0`.

Does **not** rewrite Ch2 TOI/tandem. Does **not** retune `NHL_TEAM_CARRY_SHRINK`. Does **not** fill KEINHL.

---

## Allowlist

| Item       | Path                                                              |
| ---------- | ----------------------------------------------------------------- |
| Residual   | `nhl_season_engine/priors.py` (`NHL_TEAM_REBASE_RESIDUAL_CAP`)    |
| Reader     | `nhl_season_engine/player_projection.py`                          |
| Pack       | `nhl_player_projection_2026.json`                                 |
| Rebuild    | `scripts/nhl/build_player_projection_ch5.py`                      |
| Tests + CI | `tests/test_nhl_player_projection_ch5.py` · NHL-only CI           |
| Docs       | this brief + scorecard                                            |

---

## Forbidden

- Filling `/edge-board/nhl` / KEINHL
- Props PLAY / stake tags
- New TOI grid · MoneyPuck as the mean · team `if`
- Changing `0.85` · NBA / WNBA / CFB / NFL
- Situation (Ch3) · KEI emit (Ch4)

---

## Gates

- Every skater with TOI > 0 has full vector + σ
- Every team goalie shares sum ~1.0
- σ computed (not a hardcoded 4)
- KEINHL still blank · cross-sport untouched

---

## Done

PlayerProjection pack on disk. Board still markets-only.  
**Stop.** Chapter 3 situation next (NHL goal units, paper-sim). Chapter 4 is the first emit.
