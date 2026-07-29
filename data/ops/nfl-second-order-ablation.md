# NFL Second-Order Ablation Holdout

Generated: 2026-07-29T07:13:57.832710+00:00
Policy: `spread_play_v2_cap7`
Method: additive deltas on stored v3 projections (week−1 lag)

## Warehouse
- board rows 2023–25: 855
- coach weekly rows: 1710
- personnel weekly rows: 0
- PBP offense_personnel filled: 0
- VC key present: False

## Confirmatory PLAY (2024–25)

| Variant | n | ATS | CLV+ (move) | n_clv | Gate | Promote? | ΔATS | ΔCLV |
|---|---:|---:|---:|---:|---|---|---:|---:|
| baseline | 229 | 0.7293 | 0.6039 | 207 | GREEN | None | None | None |
| A_coach | 223 | 0.7265 | 0.602 | 201 | GREEN | True | -0.0028 | -0.0019 |
| B_personnel | 229 | 0.7293 | 0.6039 | 207 | GREEN | False | 0.0 | 0.0 |
| E_info_velocity | 232 | 0.694 | 0.5972 | 211 | GREEN | False | -0.0353 | -0.0067 |
| H_travel_weather | 220 | 0.7364 | 0.6041 | 197 | YELLOW | True | 0.0071 | 0.0002 |
| D_error_regime | 229 | 0.7293 | 0.6039 | 207 | GREEN | True | 0.0 | 0.0 |
| all_enabled | 227 | 0.7004 | 0.6029 | 204 | GREEN | False | -0.0289 | -0.001 |
| recommended | 218 | 0.7431 | 0.6051 | 195 | YELLOW | True | 0.0138 | 0.0012 |

## Primary 2025 PLAY

| Variant | n | ATS | CLV+ | n_clv | Gate |
|---|---:|---:|---:|---:|---|
| baseline | 112 | 0.6964 | 0.58 | 100 | YELLOW |
| recommended | 107 | 0.7196 | 0.5895 | 95 | YELLOW |
| all_enabled | 117 | 0.6923 | 0.5673 | 104 | YELLOW |

## Promoted vs killed (final — strict ST/QB: any ATS regress kills)
- Promoted: **H_travel_weather**, **D_error_regime**
- Killed: **E_info_velocity** (ATS −3.5pp), **B_personnel** (no signal), **A_coach** (ATS −0.28pp regress)
- Shipped defaults: `travel_weather_interaction=true`, `error_regime=true`; personnel/coach/info_velocity=false
- Note: script's noise bar initially kept A; final product defaults apply strict zero-ATS-regress kill.

