# B2-PACE-v1 Train-A diagnostics

Candidate: `B2-PACE-v1` / `kenpom_adjem_pit_tempo_plus_game_hca_v1` (research alias C3)
HCA frozen: `2.8696`
n eligible with actual: `3583`

## Coverage

- Lab rows: 3676
- B2-PACE-v1 eligible: 3676 (1.0)
- Missing/invalid AdjT either side: 0

## Paired bootstrap (game grain)

- MAE(B2-PACE-v1)-MAE(C0): -0.4486 95% CI [-0.5619057427248882, -0.33578819208480143]
- MAE(B2-PACE-v1)-MAE(B1): 0.3143 95% CI [0.23206913119759198, 0.39386460552238434]

## Monthly MAE

| month | n | C0 | B2-PACE-v1 | B1 |
|---|---:|---:|---:|---:|
| 2022-11 | 578 | 10.0328 | 9.4899 | 8.8223 |
| 2022-12 | 740 | 9.7282 | 9.2656 | 9.0501 |
| 2023-01 | 976 | 9.2469 | 8.8252 | 8.5540 |
| 2023-02 | 943 | 9.2314 | 8.8186 | 8.6459 |
| 2023-03 | 346 | 9.6605 | 9.2261 | 8.7825 |

## Rolling-origin folds

| fold | n_test | C0 | B2-PACE-v1 | B1 |
|---|---:|---:|---:|---:|
| roll_2022-12 | 740 | 9.7282 | 9.2656 | 9.0501 |
| roll_2023-01 | 976 | 9.2469 | 8.8252 | 8.5540 |
| roll_2023-02 | 943 | 9.2314 | 8.8186 | 8.6459 |
| roll_2023-03 | 346 | 9.6605 | 9.2261 | 8.7825 |

Test-A is development-exposed for this unit-correction family and is not an untouched confirmation set.

No Test-A or 2025 pocket performance was scored in this run.

