# t5061u — IFACE CONSTRAINTS: offline research joint from frozen Q2s margin

**INSPECT ONLY.** No EXEC build. No weight. No retune. No forecast regen.
CERT=0 · NFL NO-GO · DRAFT #686 · research-only.

Cite **46789d12 · 12763c08 · bd51eb3e · 8bea4ca3 · 55d8c8bc · 32e97434 · 60b5f4b0 · 90db4976 · d7e0a6bc**.

Look package is COMPLETE (`LOOK_CONSUMED` present). Fixed candidate
`research.q2s.margin_mu_q2s` is **retained research-only**. This note maps
how a later package could consume those **unchanged** 141 margins into a
joint score / ST / ML distribution. It does **not** authorize that package.

## 1. Exact entry points (today)

| Role | Module | Function |
|---|---|---|
| Joint score generator (Layer 1, frozen IF) | `services/model-service/src/services/nfl_simulator.py` @ tip **6ca03716** / sha **52d9e909** | `simulate_nfl_game` → independent `rng.gauss(mean_home, stdev)` + `rng.gauss(mean_away, stdev)` (same stdev; scores floored at 0). Draws are **not returned**. |
| IF-labeled wrapper | same | `simulate_nfl_game_independent_fair(...)` → `simulate_nfl_game(..., independent_fair=True)` |
| IF mus extractor | same | `independent_fair_mus(projection) → (margin_mu, total_mu)` |
| Inputs dataclass | same | `NflGameInputs` (27 recon fields + rest; production has extra optional nowcast/KAV fields unused by Phase 4) |
| Mean decomposition | `nfl_handicapping_framework.py` sha **a0051cc4** | `compute_nfl_projection_decomposition` → `expected_home_points` / `expected_away_points` |
| ST/ML from draws | `nfl_simulator.py` | `markets.home_win_prob` = P(margin>0); `spread_home` = −mean(margins); `fair_*_ml` = `_fair_moneyline_from_prob`; totals quantiles + optional linear calibration **after** IF mus are taken |
| Offline IF caller (research copy) | `research/q2s_w7w17_t5044u/phase4/score_if_w7w17.py` | `assemble_sample` → `build_inputs` → `score_game` → `write_if_mus`. **Does not persist draws.** |
| Q2s margin consumer (today) | `phase4/emit_q2s_w7w17.py` + `phase4/q2s/blend.py` | `margin_mu_q2s(if_margin_mu, q2_pm_new)` only. Copies IF baseline. Sets `mc_draws_unchanged=true`, `no_candidate_probabilities=true`. |
| Look (consumed) | `evaluator/compare.py` | `look_real` / `evaluate` — margin MAE only. Not a joint path. |

Layer-3 production callers (**do not use / do not edit**):
`src/routes/nfl.py` ~4893 `simulate_nfl_game(...)` (default, not IF);
`src/tasks.py` ~4967 `simulate_nfl_game(..., market_spread_home, market_total)` (blend-on path).

There is **no** existing function that takes `margin_mu_q2s` and emits joint
scores / ST / ML. Blend is a scalar. IF Monte Carlo is discarded after mus.

## 2. Input contract a future consumer would read

Read-only. Re-hash before any new write. Do **not** regenerate 141 forecasts.

| Artifact | sha8 | Consumer use |
|---|---|---|
| `phase4/artifacts/q2s_rows_w7w17.json` | **55d8c8bc** | `research.q2s.margin_mu_q2s` (candidate mean). Identity `(season,week,home,away)` / `game_id`. |
| `phase4/artifacts/IF_MUS_W7W17.json` | **32e97434** | `if_margin_mu`, `if_total_mu`, `if_sigma` (per-score stdev, not margin σ), `seed`, `simulations=4000`, `market_blend=0`. **No draw arrays. No mean_home/mean_away.** |
| `gate2/RECON_MATRIX_W7W17.csv` | **b56be146** | Identity + 27/27 fields **only if** re-simulating IF. Not required for a mus-only joint. |
| `phase4/artifacts/PROTOCOL_FREEZE.json` | **90774bd4** | Parent files map + row hashes. |
| `evaluator/FINAL_PRELOOK_FREEZE_t5055u.json` | **60b5f4b0** | Live complete-set gate. History `a4652323` object-sha only. |
| Pins | `4fe1cdd7` games / `50bda875` score-only | Identity / as-of history already used at emit. **Not** a second look. |
| IF tree | tip **6ca03716** | Required **only** if re-running `simulate_nfl_game_independent_fair`. Live checkout currently matches **52d9e909** / **a0051cc4**; still pin the worktree, do not call Layer 3. |

Recoverable from frozen mus (MC means, not pre-draw gauss means):
`E[home] ≈ (if_total_mu + margin)/2`, `E[away] ≈ (if_total_mu − margin)/2`.
`if_sigma` ≈ 10.0068 is the **per-score** gauss stdev used in the loop.

24 T2 sealed IDs stay **out**. Examined 70 stay **out**. n=141 only.

## 3. Stay frozen vs must change (coherent joint)

**Stay frozen (do not rewrite):**
- 141 `margin_mu_q2s` and the 0.5 blend (`q2s/blend.py` `Q2S_WEIGHT=0.5`)
- IF mus / sigma / seeds / blend=0 / sims=4000
- matrix, identities, rest BIND_PACKET_ONLY / **155d3ca0**
- look artifacts (`LOOK_CONSUMED` once)
- `score_t4910u` / `#682 emit_q2_asof_sidecar` / Layer 3

**Must be new (research copy only) — not a post-shift on IF probabilities:**
Today `baseline.if_forecast_wp_*` are IF-draw WP. `mc_draws_unchanged=true`
means those draws were **not** moved when the margin was blended. Mapping
`margin_mu_q2s` → ST/ML by logistic / constant-σ WP while leaving IF draws
and IF WP in place is **incoherent** and is already forbidden
(`FORBIDDEN_OUTPUT_KEYS` includes `win_prob` / `ats_prob` / `ou_prob` /
`home_score` / `away_score` on the emit).

A coherent joint must generate **new** paired `(home_score, away_score)`
whose sample margin mean equals frozen `margin_mu_q2s`, and derive ST/ML
from **those** draws. Two inspect-legal shapes (choose later, not now):

1. **Mus-only joint** — new offline sampler from
   `(margin_mu_q2s, if_total_mu, if_sigma)` with a declared seed. Does not
   re-open the framework. Does not need matrix values.
2. **Re-sim then margin-shift** — re-run pinned IF @ 6ca03716 (same 27
   fields, same seed) to recover draws, then shift each pair on the margin
   axis (`home += d/2`, `away -= d/2`, `d = q2s − if_margin`) so totals
   and IF decomposition stay, ST/ML come from shifted draws.

Either way: new artifact namespace (`research.q2s.joint.*`). Do **not**
overwrite `55d8c8bc`. Persist draws or a draw-hash if ST/ML will be claimed.

`if_total_mu` is the **pre-calibration** MC total. Production
`markets.total_mean` may apply linear totals calibration **after** IF mus.
A research joint must say which total it keeps (inspect default: keep
frozen `if_total_mu`; do not apply production totals cal).

## 4. Test hooks without outcome scoring

Available now (no realized join):

- `assemble_sample()` — 141 / 24 T2 / disjoint from 70 / rest bind
- `seed_for(game_id)` — `201710 + (int(sha256(game_id)[:12],16) % 1000003)`
- `margin_mu_q2s` unit identity vs stored rows (already in
  `tests/test_phase4_if_emit_freeze.py`)
- Re-hash `32e97434` / `55d8c8bc` / `b56be146` / `90774bd4` / `60b5f4b0`
- `simulate_nfl_game_independent_fair` + `independent_fair_mus` in
  `services/model-service/tests/test_nfl_handicap_clear_a_d3.py` (synthetic
  `NflGameInputs`; blend=0; no OOS)
- In-memory `evaluate()` / week-cluster fixtures (margin-only; already looked)

Future joint tests (not written): d=0 identity (joint mus match IF);
nonzero d moves sample margin to `margin_mu_q2s` and **changes** WP vs
frozen IF WP; draw-hash stability; refuse T2 / 70 / n≠141; refuse if
q2s/IF sha drift. **Do not** join `50bda875` for a second look.

Caveat: `test_phase4_if_emit_freeze.Phase4Artifacts.test_no_look_consumed`
still asserts `LOOK_CONSUMED` absent (Phase 4 era). Look is now consumed.
Do not “repair” that in this inspect; a later package should not reuse
that assertion as a gate.

## 5. Hard blockers / leakage / Layer-3 / runtime

| Blocker | Why |
|---|---|
| **No archived IF draws** | Phase 4 stored mus only. Cannot shift “unchanged draws.” |
| **Emit forbids candidate ST/ML** | `no_candidate_probabilities` + forbidden keys. New joint file only. |
| **LOOK_CONSUMED** | One look done. No second realized comparison. No new weight. |
| **Layer 3** | Do not edit `routes/nfl.py`, `tasks.py`, or production `NflGameInputs` usage. Do not call default `simulate_nfl_game` (market blend). |
| **Sealed IF caller** | Do not edit `score_t4910u.py`. Research copy only if re-sim. |
| **`1ee90fac`** | Still blocked. Score-only pin is look-consumed, not a joint input. |
| **Q2 EVAL `03a4dd90`** | CLOSED. No re-look of the 70. |
| **24 T2 / examined 70** | Out of sample. No silent subset. |
| **Rest / tip `90bf65ab`** | BIND_PACKET_ONLY only. |
| **Runtime / merge / Stage C / CERT** | Held. No promote of Q2s joint to live markets. |
| **w** | Frozen 0.5. Do not choose another weight here. |

## Status

Constraints + interface map only. Alex recommendation tip **90db4976**
is parallel. CoS folds both into one executable spec later.
No joint package implemented. Predictions unchanged.
