# NFL preseason release gate

- **Bundle:** `data/ops/nfl-preseason-sim-2026-20260813T214500Z`
- **Generated:** 2026-08-13T21:35Z
- **Lock tag:** `nfl-season-engine-2026-preseason-lock`
- **Result:** **PASS**
- **Identity:** nfl-season-engine-2026-preseason-lock · N_team=100000 · 2026-08-13

| Check | Result | Detail |
|-------|--------|--------|
| `walker_kc` | **PASS** | Walker team=KC (need KC) |
| `charbonnet_sea` | **PASS** | Charbonnet team=SEA (need SEA) |
| `evans_sf` | **PASS** | Evans team=SF (need SF) |
| `egbuka_tb` | **PASS** | Egbuka team=TB (need TB) |
| `walker_feature_volume` | **PASS** | Walker rush=1172 (need 1050–1650 and > Johnson 426; not 1,800 invented) |
| `checksum_qbs` | **PASS** | Tua ATL / Willis MIA / Kyler MIN / ARI ≠ Kyler |
| `qb_pass_shape` | **PASS** | 8/96 QBs ≥4000; min=85 (need not 32/32 ≥4000 and min<3200) |
| `top5_rb_spread` | **PASS** | top-5 Half-PPR spread=52.8 (need ≥50) |
| `season_wl_conservation` | **PASS** | Σ wins=271.9999 target=272.0±0.51 (ties not modeled — wins only) |
| `invariants_all` | **PASS** | I1–week1 suite |
| `bundle_identity` | **PASS** | nfl-season-engine-2026-preseason-lock · N_team=100000 · 2026-08-13 |
| `pack_vs_fp_clear_error` | **PASS** | CLEAR_ERROR=0 (need 0) |

## Named

- Walker: KC rush=1172.2 RB5 ov22 234.0 Half-PPR
- Charbonnet: SEA rush=960.8 RB12
- Top-5 RB spread: 52.8
- QBs ≥4000: 8

