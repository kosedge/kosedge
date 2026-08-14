# CFB Efficiency Backbone + SP+ Fill Reduction (research only)

**Date:** 2026-08-14  
**Branch:** `feat/cfb-p3c-efficiency-backbone` → `deploy-vercel` (stacked on #233–#237)  
**Engine:** `cfb-season-engine-v0.14-efficiency-backbone`  
**Backbone:** `cfb-efficiency-backbone-v0.14-20260814`  
**Calibration:** `cfb-margin-scale-v0.13-20260814` (tanh unchanged)  
**Doctrine:** Research fair only. `used_in_spread` stays **false**. No KEI. No lock. Merge criterion = honesty + real backbone wired, not 53% ATS.

---

## A. Method (leakage-safe)

Owned warehouse PBP → `efficiency_adj.py` (already shipped in P1):

| Rule | Value |
| --- | --- |
| Opponent adjustment | 4-iter expected-vs-observed vs opponent mean |
| Week W snapshot | same-season plays with `week < W` only |
| Season-final | last `as_of_week` (feature_week < next season) |
| Shrink | 80 plays toward league mean |
| Explosive proxy | EPA ≥ 1.0 or 15+ yards (PBP); packaged success/explosive are **EPA-z proxies**, not play rates |
| Garbage | `garbage.py`: competitive \|margin\| < 16 = 1.0; 2nd-half late blowout floor 0.10; first-half blowouts 0.85 |
| FCS | flagged, not deleted; do not let FCS blowouts dominate FBS z-norms |
| 2026 roster | **not** applied to 2020–25 walk-forward |

2026 overlay (`scripts/cfb/package_efficiency_backbone_2026.py`):

1. Keep packaged SP+ rows for official FBS when `source` starts with `packaged_sp_plus` and `off_eff ≠ 50`.
2. Else, if warehouse season-final ≤2025 has `n_games ≥ 8`: map `off_epa_adj` / inverted `def_epa_adj` to 0–100 via z vs 2025 official FBS (`50 + 18z`, clamp 5–95). `source=warehouse_pbp_epa_adj_2025`.
3. Else: `thin_sample_labeled` + placeholder fidelity (wider σ). **Not** a silent league average.
4. Drop FCS/alias extras from the snapshot (`ACU, CHAT, FAU2, FAY, IDHO, OLE, OREST, SOUTH, TA&M, TXAM, ULL`).
5. Do **not** blend warehouse into teams that already have SP+ (avoids double-count / −35 return).

Carry into 2026 project-game: prior-year OFF/DEF + P2 roster/QB/coaching. Decay = prior-year carry labeled stale (`eff_noise=0.04`). tanh constants unchanged.

Warehouse coverage (not fill failures): official 2025 EPA hits **134/136**. `APP` has warehouse through 2023 only (already has SP+). `HAW` has no warehouse rows any year (PBP identity gap; already has SP+).

---

## B. Fill report

Runtime official fills **before** (silent `league_average_fill` / missing SP+):

`ARST, CSU, ECU, JVST, M-OH, MIZZ, NEV, ODU, TOL, UAB, UNM, UNT` — **12**

Root cause: SP+ snapshot kept 11 FCS/alias extras instead of those official codes. `M-OH` was present as `league_average_fill`.

| | Before (v0.13) | After (v0.14) |
| --- | ---: | ---: |
| Official FBS in snapshot | 136 + 11 extras | **136** |
| Packaged SP+ | 124 | **124** |
| Silent `league_average_fill` | **12** | **0** |
| Warehouse EPA overlay | 0 | **12** |
| Thin-sample labeled (official) | — | **0** |

Warehouse 2025 season-finals for the 12: 12–14 games each.

| Team | n_games | off_eff | def_eff | Read |
| --- | ---: | ---: | ---: | --- |
| ARST | 13 | 34.6 | 40.8 | below-avg G5 |
| CSU | 12 | 41.9 | 35.5 | below-avg |
| ECU | 13 | 53.8 | 59.6 | mid |
| JVST | 14 | 34.1 | 41.9 | below-avg |
| M-OH | 14 | 34.1 | 47.8 | below-avg |
| MIZZ | 13 | 55.4 | 71.6 | SEC-quality DEF |
| NEV | 12 | 23.1 | 46.6 | thin offense |
| ODU | 13 | 48.4 | 74.9 | strong DEF |
| TOL | 13 | 47.3 | 73.5 | strong DEF |
| UAB | 12 | 50.6 | 27.4 | weak DEF |
| UNM | 12 | 50.6 | 47.7 | mid |
| UNT | 14 | 80.5 | 37.9 | high-powered OFF |

Remaining thin official: **none**. Codes outside the official 136 hit `thin_sample_labeled` at runtime (FCS / unknown), not silent league-avg.

`LEAGUE_REG_PLACEHOLDER=0.28` still shrinks leftover fill / thin-sample toward index 1.0. Official 136 no longer hit that path.

---

## C. Walk-forward (hostile, strictly before kickoff)

Program-prior harness (`points = net_epa_adj × 28`, seasons `< Y`, no 2026 roster). W0–1 is **100% program prior**. That prior **already was** the warehouse EPA backbone. Filling 2026 SP+ holes does not (and must not) move hist W0–1.

| Window | Before (v0.13) | After (v0.14) | Read |
| --- | ---: | ---: | --- |
| W0–1 ATS | 47.7% (n=415) | **47.7%** (n=415) | flat |
| W0–1 MAE | 8.36 | **8.36** | flat |
| W0–1 median \|err\| | 6.53 | **6.53** | flat |
| W0–1 mean error | +4.13 | **+4.13** | still too *cold* vs close |
| Overall ATS / MAE | 50.3% / 7.48 | 50.3% / 7.48 | unchanged |

ATS CI W0–1 still 43.0–52.5%. Coin-flip. Did **not** shrink σ to fake skill.

**Why ATS is flat:** feature quality on the hist path was not the 12 missing 2026 SP+ rows. The hist prior already uses opponent-adj EPA. Era + missing market layer remain the blockers if you want ATS > 50%. Next diagnostic is an **explicit open-line blend**, not more kitchen-sink features.

---

## D. Week 0 / scale (N=400, research only)

v0.13 published vs v0.14 live. None of these eight are warehouse-fill teams. tanh unchanged. A few rows moved ≤1.5 pts (sim / extras dropped from snapshot). **No −35 return.**

| Matchup | Week | Old (v0.13) | New (v0.14) | Total | WP home |
| --- | ---: | ---: | ---: | ---: | ---: |
| UNC @ TCU (Dublin) | 0 | −13.2 | **−14.4** | 52.5 | 78% |
| SJSU @ USC | 0 | −20.2 | **−21.7** | 60.6 | 88% |
| NCSU @ UVA | 0 | −5.1 | −5.0 | 56.6 | 61% |
| HAW @ STAN | 0 | +4.7 | **+6.1** | 50.2 | 37% |
| NMSU @ FSU (open camp) | 0 | −11.5 | **−12.6** | 53.0 | 75% |
| MEM @ UNLV | 0 | −4.6 | −4.6 | 61.7 | 59% |
| BALL @ OSU | 1 | −24.5 | **−24.5** | 58.0 | 84% |
| UTEP @ OU | 1 | −21.8 | **−21.8** | 57.9 | 80% |

2026 Week 0–2 FBS–FBS (96 games, N=200): mean \|spread\| **10.01** (was 10.50); p50 **9.7**; max **23.6** (was 24.5); \|spread\| > 28 = **0.0%**; > 35 = **0.0%**.

Fill-team games (counterfactual silent-50 vs warehouse overlay) — this is the input change:

| Matchup | Week | Old (league-avg) | New (warehouse) | Total |
| --- | ---: | ---: | ---: | ---: |
| UAB @ ILL | 1 | −14.7 | **−16.8** | 62.3 |
| TOL @ MSU | 1 | −9.0 | **−4.0** | 52.2 |
| ECU @ ALA | 1 | −15.6 | **−12.9** | 53.6 |
| UNT @ IU | 1 | −17.8 | **−15.1** | 68.5 |
| M-OH @ PITT | 1 | −15.2 | **−16.5** | 55.7 |

Toledo / ECU / UNT stop being fake cupcakes. Illinois–UAB widens because UAB’s warehouse DEF is actually poor. Still compressed. `used_in_spread=false` on every row.

Smell: OSU power 1.62 > BALL 0.82; MIZZ 1.19 > NEV 0.98. Open-QB (UGA/MICH/FSU/LSU/ALA) σ still wider than incumbent vs incumbent.

---

## E. Go / no-go

| # | Pass? |
| --- | --- |
| 1 Backbone leakage-safe from warehouse | **Yes** |
| 2 Placeholder fills materially reduced; remainder listed | **Yes** (12 → 0 silent; thin official = []) |
| 3 Wired into project-game strength | **Yes** |
| 4 W0–1 metrics reported honestly | **Yes** (flat 47.7 / 8.36) |
| 5 Scale still non-theater | **Yes** (max 23.6; 0% > 28) |
| 6 `used_in_spread` false; no KEI | **Yes** |
| 7 Status 200 + v0.14 + `n_filled` / `n_thin` | **Yes** |

**Recommendation: market-diagnostic pass (B) next.**  
Pure-model inputs are no longer silently average for playable history. Hist ATS will stay coin-flip until an explicit open-line layer exists. Do **not** do more feature theater, P4 win totals, CFP claims, or `used_in_spread` flip.

**Go for B (market diagnostic).** No-go for release / KEI / Edge population.

---

## Safety

- Status 200: `engine_version=cfb-season-engine-v0.14-efficiency-backbone`, `backbone_version`, `n_filled=12`, `n_thin=0`
- `used_in_spread=false` on snapshot, backbone table, predictions, project-game
- No Edge KEI
- No CFP/natty product numbers
- Densified seed still not official
