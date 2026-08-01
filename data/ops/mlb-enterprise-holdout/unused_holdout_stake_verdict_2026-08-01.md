# Unused-holdout stake verdict (2026-08-01)

**Window:** 2026-07-18 → 2026-08-10 (frozen; train-excluded)  
**Resim (eval only):** 2026-07-18 → 2026-08-01 — task simulated **117** games (`903de81f-…`)  
**HFA:** 1.025 (restored winner)

## Gates

| Gate | Target | Observed | Pass? |
|------|--------|----------|:-----:|
| Unused eval n | ≥120 | **51** walkforward unused pts available | **NO** |
| ML Brier (densify / overall) | ≤0.24 | ~0.249–0.250 | **NO** |
| ML CLV vs prior bar | ≳ +0.02 | ~+0.004–0.007 | **NO** |
| Leakage | 0 | **0** | YES |
| ECE | ≤0.06 | ~0.017–0.023 | YES |
| Props PLAY stake | separate holdout | research_only | **NO** |

## Verdict

**Stake marketing OFF.** Do not flip `props_play_stake_eligible` or game-line stake flags.  
Props remain `research_only`. Unused holdout stays frozen for train/tune.
