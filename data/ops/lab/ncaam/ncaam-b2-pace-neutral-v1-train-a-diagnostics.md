# B2-PACE-NEUTRAL-v1 Train-A diagnostics (research only)

- Candidate: `B2-PACE-NEUTRAL-v1` / `kenpom_adjem_pit_tempo_gated_hca_v1`
- Generating commit: `1e1e969d350e5bfca11ace0478d548a7e59bb491`
- Scored eligible n: **3583**
- Status: **research evidence only — not promoted**

## Overall MAE

| Model | MAE | bias | cal slope |
| --- | ---: | ---: | ---: |
| C0 | 9.509 | -0.295 | 0.703 |
| B2-PACE-v1 | 9.060 | 0.370 | 1.013 |
| B2-PACE-NEUTRAL-v1 | 9.039 | 0.640 | 1.019 |
| B1 | 8.746 | 0.375 | 1.009 |

## Paired ΔMAE (NEUTRAL − comparator)

- vs PACE: {'n': 3583, 'mean': -0.021446928608791528, 'ci95': [-0.04833843197411459, 0.005715078000623768], 'n_bootstrap': 2000, 'seed': 20260909}
- vs B1: {'n': 3583, 'mean': 0.29290183218247284, 'ci95': [0.21163783707447867, 0.36707319455559645], 'n_bootstrap': 2000, 'seed': 20260909}
- vs C0: {'n': 3583, 'mean': -0.47002916536839245, 'ci95': [-0.5767775412701696, -0.3577233879604843], 'n_bootstrap': 2000, 'seed': 20260909}

## Hard stops

- Holdout / Test-A / pocket: **not scored**
- Parent B2-PACE-v1: **unchanged**
- No promotion / PLAY / LEAN
