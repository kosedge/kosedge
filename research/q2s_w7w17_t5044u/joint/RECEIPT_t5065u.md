# t5065u / t5064u — research.q2s.joint EXEC receipt

**RETRO_FIT / DEV_RESEARCH · CERT=0 · NFL NO-GO · DRAFT #686 — do not merge.**

Authority: OWNER CLEAR **dad9eb89** + J10 resolve **a091ce1a** (lifts REFUSE_EXEC) under **d7e0a6bc**.
Spec baseline: CoS **22f2c33f** · Alex **5d07dc49** · iface **475b84a1**.
Standing **2db90f76** · guardrails **52c79ee6**.

## Head

Branch `cursor/q2s-w7w17-t5044u-86b2`. Head SHA is the commit that adds this receipt.

## Construction (frozen)

Verbatim IF joint-score branch @ **6ca03716** / sim **52d9e909** / framework **a0051cc4**, plus one pre-floor symmetric shift after framework floors:

`d = frozen_q2s_margin − frozen_IF_margin`; `μh' = μh + d/2`; `μa' = μa − d/2`; `H',A' = max(0, N(μ',σ))`.

Same per-team σ (not margin σ), `seed_for(game_id)`, gauss order, N=4000, 141 identities, blend=0, `apply_linear_totals_calibration=False`. No extra HFA, no weight change (w=0.5), no iterative d, no new σ.

## Artifacts (`research.q2s.joint.*`)

| File | sha256 | sha8 |
|---|---|---|
| `joint/artifacts/Q2S_JOINT_W7W17.json` | `5076421ef1fba943df9c1e8eeaefede4f7a7e30a36ae2ed792a7f2bc295c4e27` | **5076421e** |
| `joint/artifacts/Q2S_JOINT_DRAWS_W7W17.npz` | `ce6b1244895df065ea8428851261becbb8012c7379d6184770116a7dfbcb0fc5` | **ce6b1244** |
| draws catalog (game_id + H + A bytes) | `a75f8a9b29caaf03…` | **a75f8a9b** |

Paired float64 H',A' shape `(141, 4000)`. Order: rows sorted by `(week, game_id)`; draw index `i=0..3999` ≡ `i=1..4000`; pair `(H_i, A_i)`. Every research spread / total / WP / ML is derived from that one array.

## Input pins (re-hashed pre & post; originals byte-identical)

| Artifact | sha8 |
|---|---|
| `q2s_rows_w7w17.json` | **55d8c8bc** |
| `IF_MUS_W7W17.json` | **32e97434** |
| `RECON_MATRIX_W7W17.csv` | **b56be146** |
| `PROTOCOL_FREEZE.json` | **90774bd4** |
| `FINAL_PRELOOK_FREEZE_t5055u.json` | **60b5f4b0** |
| history freeze (bytes only) | **a4652323** |

141 identities. 24 T2 sealed / examined 70 refused. Frozen 141 predictions **not overwritten**.

## Q1 / J13 d=0

**PASS on all 141.** `simulate_q2s_joint(d=0)` reproduces official IF replay raw means (≤1e-12), frozen `if_margin_mu` / `if_total_mu`, win-count-derived legacy WP at 4dp, and official fair ML integers. Original prediction artifacts remain byte-identical.

## Q6 / 50bda875

**Not opened.** Pin verify hashes allowed input files only. Freeze JSON `files` maps that list outcomes are not traversed into `50bda875`. LOOK_CONSUMED / LOOK_RESULT not opened. No second look. No outcome join.

## Tests

`python3 -m unittest research.q2s_w7w17_t5044u.joint.tests.test_q2s_joint -v` → **28/28 OK**.

Q1–Q6 + J1–J14 + J12F + Q5-diag implemented. Bands from dad9eb89 §4 as amended by a091ce1a **only** for J10. J14 = **NOT EMITTED**, never PASS.

### Cellwise gate counts (141 games × gates)

| Status | Count |
|---|---|
| PASS | 2222 |
| COND | 34 |
| FAIL | 0 |
| REFUSE | 0 |
| NOT_EMITTED (J14) | 141 |

### Per-gate status counts

| Gate | PASS | COND | FAIL | REFUSE | NOT_EMITTED / reported |
|---|---|---|---|---|---|
| J1 | 141 | 0 | 0 | 0 | — |
| J2 | 141 | 0 | 0 | 0 | — |
| J3 | 141 | 0 | 0 | 0 | — |
| J4 | 141 | 0 | 0 | 0 | — |
| J5 | 141 | 0 | 0 | 0 | — |
| J6 | 141 | 0 | 0 | 0 | — |
| J7a | 124 | **17** | 0 | 0 | — |
| J7b | 141 | 0 | 0 | 0 | — |
| J8 | 138 | **3** | 0 | 0 | — |
| J9 | 133 | **8** | 0 | 0 | — |
| J10 | 141 | 0 | 0 | 0 | — |
| J11 | 135 | **6** | 0 | 0 | — |
| J12 | diagnostic only (τ=0.997568; 12 inversions) | | | | |
| J12F | monotone exact (controlled same-total/same-σ fixtures) | | | | |
| J13 / Q1 | 141 | 0 | 0 | 0 | — |
| J14 | — | — | — | — | **141 NOT_EMITTED** |
| Tie | 141 | 0 | 0 | 0 | — |
| Q3 | 141 | 0 | 0 | 0 | — |
| Q5 | 141 | 0 | 0 | 0 | — |
| Q5_diag | — | — | — | — | 141 reported |

Worst-gate per game: PASS 114 · COND 27 · FAIL 0 · REFUSE 0.

### COND (kept visible; not retuned / not band-widened)

- **J7a** (2<z≤4): 2017_07_ARI_LA, 2017_07_ATL_NE, 2017_09_IND_HOU, 2017_09_KC_DAL, 2017_10_NO_BUF, 2017_11_LA_MIN, 2017_11_TB_MIA, 2017_11_TEN_PIT, 2017_13_CAR_NO, 2017_13_DEN_MIA, 2017_13_IND_JAX, 2017_13_LA_ARI, 2017_14_GB_CLE, 2017_14_PHI_LA, 2017_15_LAC_KC, 2017_17_DAL_PHI, 2017_17_NYJ_NE
- **J8** (3%<rel≤8%): 2017_09_ATL_CAR, 2017_12_DEN_OAK, 2017_14_DET_TB
- **J9** (2√(p(1-p)/N) < err ≤0.03): 2017_07_ATL_NE, 2017_11_TEN_PIT, 2017_13_IND_JAX, 2017_13_WAS_DAL, 2017_14_GB_CLE, 2017_14_PHI_LA, 2017_16_SEA_DAL, 2017_17_CIN_BAL
- **J11** (\|spread\|<0.25): 2017_10_DAL_ATL, 2017_10_NO_BUF, 2017_14_DET_TB, 2017_14_MIN_CAR, 2017_14_NO_ATL, 2017_15_NE_PIT

No FAIL. No J10 REFUSE on the 141 (analytic independence 0.0 reported separately). d range on 141: min −5.13, max +6.61, mean +0.92; 121 with \|d\|≥0.5.

## Holds

No reseed · no N increase · no band widen · no outcomes join · no cal/FQ claim · no second look · no overwrite of 141 frozen predictions · no Layer-3 / `nfl_simulator.py` / `score_t4910u` / `routes/nfl.py` / `tasks.py` / sealed emitter edits · no merge · CERT=0.
