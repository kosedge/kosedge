# FEASIBILITY — 2017 REG W7–W17 Q2s follow-up (t5039u)

**READ-ONLY · CERT=0 · NFL NO-GO · DRAFT · no rebuild · no score · no Appendix O · no outcome look.**

Cite **t5039u · d7e0a6bc · 404a4ab2 · 2b9f302e**.

ChatGPT labeled [#685](https://github.com/kosedge/kosedge/pull/685) **PROTOCOL_DEVIATION** (research-consumed **INCONCLUSIVE**; Gate 5 **NOT MET**). Guard work on head `2805f42e` is left untouched — Alex is RO-ing that guard (t5035u / `404a4ab2`). This note is a **distinct** preregistered-follow-up inventory only.

Frozen candidate if a later experiment is cleared: `margin_mu_q2s = 0.5*IF.margin_mu + 0.5*q2_pm_new`. Same control lineage. **No alternate weight. No outcome analysis here.**

---

## Verdict

**W7–W17 is not available for the same IF+Q2s comparison.**

Genuine sealed Independent Fair (IF) forecasts live only on the already-examined 70 (2017 REG W2–W6 / `SCORE_RESULTS.json` sha256 `2b9f302e097183ef275185a4edb100ab206565a087ca1ce78dbe8062524e877a`). No sealed IF `forecast_margin` exists for any 2017 REG W7–W17 game. Q2 as-of and score-only finals **do** exist for the window; that is not an IF baseline.

---

## Scope (owned inventory, this checkout)

| Slice | Source | N |
|---|---|---:|
| 2017 REG W7–W17 scheduled | `games.csv` **4fe1cdd7** | **165** |
| 2017 REG W2–W6 scheduled (already examined 70 + 6 excluded) | same | 76 |
| Already-examined scored 70 | `SAMPLE_MANIFEST_70` + `SCORE_RESULTS` **2b9f302e** | 70 |
| W7–W17 ∩ score-only extract **50bda875** | identity join | **165 / 165** (0 missing) |
| W7–W17 ∩ sealed IF `SCORE_RESULTS` **2b9f302e** | `forecast_margin` | **0 / 165** |

Per-week scheduled (4fe1cdd7): W7=15, W8=13, W9=13, W10=14, W11=14, W12–W17=16 each.

Sample W7 ids (not a selection seal): `2017_07_KC_OAK`, `2017_07_ARI_LA`, `2017_07_ATL_NE`, `2017_07_BAL_MIN`, `2017_07_CAR_CHI`.

---

## 1) Genuine IF-baseline availability

**Where sealed IF forecasts live today**

- Repo copy: `research/q2s_adapter_t5033u/pins/t4910u/SCORE_RESULTS.json` (from draft [#672](https://github.com/kosedge/kosedge/pull/672)).
- Ops-box path: `ops/nfl_enterprise_green_t4359u/nfl-hist-diag-score-70-t4910u/`.
- Tip: file sha **2b9f302e…** (not a git commit). IF caller tip **6ca03716**, blend=0, sims=4000, rest `BIND_PACKET_ONLY`.
- Weeks present: **W2–W6 only**. `n=70`. Field `forecast_margin` = IF `f_margin`.

**Gaps for W7–W17**

| Need | Status |
|---|---|
| Sealed `SCORE_RESULTS` / `forecast_margin` | **Absent** |
| Stage-1b complete 27/27 IF-input packet | **Absent** for W9–W17. W7–W8 inputs only on draft [#674](https://github.com/kosedge/kosedge/pull/674) (not IF mus) |
| Stage C / IF invoke @ 6ca03716 | **Not authorized** |
| PBP 2017 **84eacd96** on this VM | **Absent** (Stage B remounted it; hash-before-parse required if recon is later cleared) |
| #684 2013 W2 demo IF | Placeholder — **forbidden substitute** (`9982d42f`) |
| games.csv `market_*` / `epa_*` / `*_prob` | Present on 4fe1cdd7 — **not** IF forecasts |

Stage B t4923u (#674, Alex RO **ba1c89f5**): 2017 W7–W8 **28/28 produced**, **22 complete 27/27**, **6 bye `MISSING_RECORD`**. Verdict `PASS_STAGE_B_PARITY_COVERAGE` is reconstruction / as-of / season-handling only. Explicitly: no outcomes, no scores, no Stage C, no touch of `SCORE_RESULTS` 2b9f302e.

---

## 2) Exact owned-data reconstruction required

To build the **same** IF+Q2s comparison on this window (not authorized by t5039u) the later ticket must own **all** of:

**Identity / as-of / Q2 (already on #685 tree)**

| Pin | sha8 / object | Path / PR |
|---|---|---|
| games | **4fe1cdd7** | this tree `data/games_4fe1cdd7.csv`; SoT `data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv` (#638) |
| score-only finals | **50bda875** | this tree `data/outcomes_2013_2022_score_only.csv` |
| Q2 frozen config | **aa2b47b3** / md **28c582a1** | `frozen/FROZEN_CONFIG_Q2PB_t5009u.{json,md}` |
| fit object | **70db070d** | inside frozen JSON; `a_q2=2.5637441292077354`, `b_q2=1.660624056183471`, λ=20, r=0.5 |
| as-of | **cf514078** / module **7dc6afea** | kickoff-strict; keep `asof_for_targets` |
| adapter | w=0.5 predeclared | `q2s/blend.py` — do not retune |

**IF inputs (not on this tree; copy/pin, do not invent transforms)**

| Pin | sha8 | Lives on |
|---|---|---|
| Contract (27 fields = 20 efficiency + 7 context) | **b41f4b43** | `ALEX_E1_EFFICIENCY_CONTRACT_t4770u_v2.md` |
| T1–T4 builder | **7e77c57f** | W2 Stage-1b; Stage B parameterized wrapper |
| W2 RECON (lineage only; not this window) | tip **440314e4** / matrix **708513db** | #669 `data/ops/nfl-hist-bt-stage1b-w2-t4893u/` |
| W3–W6 RECON (lineage only) | tip **f92aaea3** / matrix **cdff0115** | #671 `data/ops/nfl-hist-bt-stage1b-w3w6-t4893u/` |
| W7–W8 input matrix (coverage, not IF) | matrix **cd9af285** | #674 `data/ops/nfl-hist-stage-b-t4923u/RECON_MATRIX.csv` |
| PBP 2017 | **84eacd96** (receipt family **6ee24b44**) | remount + hash-before-parse; W9–W17 T1 needs W8–W16 plays |
| rest | `BIND_PACKET_ONLY` | sealed ET DOW; W8 eval caller re-derive **FORBIDDEN** (OWNER_ACCEPT t4910u) |
| IF tip | **6ca03716** | `score_t4910u` sealed; blend=0; seed `201710 + (int(sha256(game_id)[:12],16) % 1000003)` |

**Pipelines (order; each a separate CLEAR)**

1. Seal selection hash **before** PBP (t4893u / Stage B Step 0 pattern).
2. Remount PBP · hash-before-parse **84eacd96**.
3. Rebuild T1–T4 / 27-field matrix with **7e77c57f** functions (no new transforms; no T2 last-played).
4. Alex RO of recon (complete vs `MISSING_RECORD` visible).
5. **New** Stage C / IF invoke @ **6ca03716** — Owner CLEAR required; #674 does not authorize this.
6. Emit `research.q2s.*` only (same `emit_q2s_adapter` contract).
7. **Then** freeze with a real receipt (see last section) · **one** look.

This checkout has **no** `data/ops/nfl-hist-*` packets and **no** 2017 PBP.

---

## 3) Eligibility / missing rules

Copy t4893u / Stage B (not a new rule). Fail-closed. No silent subset. No replacement.

1. Universe = every 4fe1cdd7 row with `season=2017` and `week∈[7,17]`. Week ≤ 17. Season ≥ 2024 abort.
2. Completed as-of = same-season rows that join **50bda875** (or OOS **1ee90fac** PILOT for T5 W-L only) with both scores present and kickoff **strictly before** the candidate (`cf514078`).
3. **Ineligible / MISSING** if either side has **0** completed same-season games as-of kickoff. Expected **0** in W7–W17 (Irma pair is W2-only: `2017_02_CHI_TB`, `2017_02_MIA_LAC`).
4. Cell-level T2 `MISSING_RECORD` (exact `rating_week`; bye return) is **not** a selection exclusion. Game stays listed; cells stay missing; **not** complete 27/27; **not** IF-scorable under the 70-game rule.
5. IF-score sample = **complete 27/27 only**. Failed / bye / Irma stay visible. Replacement forbidden.
6. **Exclude** the already-examined 70 and the six W2–W6 excluded ids. They are not in W7–W17.
7. Do **not** add W1 (Stage-1 #668: 0/31 fully reconstructable), postseason W18–W21, 2016 W8, EVAL 2018–22, reserve 2023, or sealed 2024–25.

**T2-risk (bye-return) W7–W17 = 24 games.** Same six W7–W8 ids as Stage B:

| wk | game_id | bye side |
|---:|---|---|
| 7 | `2017_07_TB_BUF` | BUF home (W6) |
| 7 | `2017_07_DAL_SF` | DAL away (W6) |
| 7 | `2017_07_CIN_PIT` | CIN away (W6) |
| 7 | `2017_07_SEA_NYG` | SEA away (W6) |
| 8 | `2017_08_HOU_SEA` | HOU away (W7) |
| 8 | `2017_08_PIT_DET` | DET home (W7) |
| 9 | `2017_09_ARI_SF` | ARI |
| 9 | `2017_09_BAL_TEN` | TEN |
| 9 | `2017_09_CIN_JAX` | JAX |
| 9 | `2017_09_LA_NYG` | NYG + LAR |
| 9 | `2017_09_DET_GB` | GB |
| 10 | `2017_10_CLE_DET` | CLE |
| 10 | `2017_10_GB_CHI` | CHI |
| 10 | `2017_10_LAC_JAX` | LAC |
| 10 | `2017_10_MIN_WAS` | MIN |
| 10 | `2017_10_NE_DEN` | NE |
| 10 | `2017_10_PIT_IND` | PIT |
| 11 | `2017_11_BAL_GB` | BAL |
| 11 | `2017_11_KC_NYG` | KC |
| 11 | `2017_11_NE_OAK` | OAK |
| 11 | `2017_11_PHI_DAL` | PHI |
| 12 | `2017_12_CAR_NYJ` | NYJ + CAR |
| 12 | `2017_12_SEA_SF` | SF |
| 12 | `2017_12_TEN_IND` | IND |

If T2 is the only completeness fail: **141 / 165** complete (W7–W8 = 22 already observed; W9–W17 expected 119). Not a selection seal — inventory only.

---

## 4) Fit-exclusion proof path (`a_q2` / `b_q2` vs this window)

Reuse `q2s/coverage.py::prove_fit_exclusion` on the **new** target list. Do not refit.

Required evidence (already true for all of 2017):

- Frozen `fit_object_sha256` == `70db070dad3fcdb4d4ff165ba09b7840c173c232a71c8fcd670ba9c3c0bc5571` and `n_fit == 960`.
- `season_end_ratings` keys = DEV 2013–16 only (≤ 2016).
- Keep constants: `DEV_SEASONS=(2013,2014,2015,2016)`, `HISTORY_ONLY_SEASONS=(2017,)`, `DEV_WEEKS=W2–17`.
- Every target `season == 2017`.
- Optional: no target `game_id` in the DEV window id set.

2017 is HISTORY_ONLY: as-of carry into 2018; never fit; never EVAL-scored. `a_q2`/`b_q2` are DEV 2013–16 REG W2–17 OLS. W7–W17 is the same exclusion class as the 70. Path does **not** reopen Q2 EVAL **03a4dd90**.

---

## 5) Field-level provenance restrictions

| Source | May use | Must not use |
|---|---|---|
| games **4fe1cdd7** | `season,week,game_id,home,away,kickoff_utc,record_entering_*` | `market_*`, `epa_*`, `*_prob`, `trailing_*`, `packaged_*`, `cover_prob`, `apply_market_blend`, live `rest_days_*` as IF rest |
| extract **50bda875** | six columns `season,week,home,away,home_score,away_score` for 2013–2022 | any other hist column |
| hist index **1ee90fac** | T5 W-L **PILOT-ONLY** (Stage B); score-only extract already taken | trailing / packaged / EPA / `*_err` / 2023–25 / model margins. Gate **83646d78** stays |
| `SCORE_RESULTS` **2b9f302e** | cite as the consumed 70-game IF SoT | W7–W17 baseline; second look; `f_margin` copy |
| PBP **84eacd96** | T1–T4 cells after hash-before-parse, if recon is cleared | new acquisition; 2023+; silent remount |
| #684 demo | mechanical fixtures | outcome scoring / IF substitute |
| adapter emit | `research.q2s.*` only | Layer 3, `NflGameInputs`, `independent_fair.*`, candidate WP/ATS/OU, MC draws, `score_t4910u.py`, `emit_q2_asof_sidecar.py` |

`market_spread_home` is parsed onto the keep `Game` dataclass but is **not** an IF `margin_mu` and is not a Q2 input.

---

## 6) Reuse of existing reconstruction + Stage C material

**Reuse without lifting scored-index holds or reopening 03a4dd90**

| Material | Reuse? |
|---|---|
| games 4fe1cdd7, outcomes 50bda875, frozen Q2, as-of cf514078, keep `asof_for_targets` | **Yes** — Q2 as-of for 2017 W7–W17 is generable from these pins |
| `q2s/blend.py` w=0.5, `coverage.py`, emit contract (`research.q2s.*` only) | **Yes** — mechanical, no look |
| T1–T4 functions **7e77c57f** / Stage B wrapper | **Yes as method** after a new selection seal |
| Stage B W7–W8 `RECON_MATRIX` **cd9af285** | **Yes as input evidence** after Alex RO **ba1c89f5** — **not** IF mus |
| W2 / W3–W6 RECON **708513db** / **cdff0115** | lineage / method only — wrong weeks |
| `SCORE_RESULTS` 2b9f302e / #685 rows `0d6a5e14` / Appendix O `be701325` | **No** — research-consumed; do not re-look |
| Gate **83646d78** / S1 kill **50f57195** / 2024–25 | **Do not lift** |
| Q2 EVAL **03a4dd90** | **Stay CLOSED** |
| Stage C / IF invoke / #674 “next” | **Not authorized** by t5039u or by Stage B PASS |
| PROTOCOL_FREEZE / FREEZE_ADDENDUM / t5035u guard @ `2805f42e` | **Leave** — Alex RO |

Q2-only `q2_pm_new` vs realized on W7–W17 is **generable** from owned pins. That is a **different experiment**, not the IF+Q2s adapter comparison.

---

## 7) Blocker + best justified alternative

**Exact blocker.** Same-game IF+Q2s comparison on W7–W17 requires a genuine sealed IF `forecast_margin` per game. None exists. Getting one requires a new complete 27/27 recon **and** a new IF invoke at **6ca03716**. t5039u forbids rebuild/score. Stage B W7–W8 is input parity, not forecasts. PBP **84eacd96** is not on this VM. Stage C is not cleared.

**Do not use as substitutes:** #684 2013 demo placeholders; Q2 EVAL 2018–22 (`03a4dd90`); 2023 reserve; 2024–25 sealed; Irma / W6 bye / W7–W17 T2-partial games; games.csv market/EPA columns; a second look of the 70; an alternate weight.

**Best justified alternative inside owned / approved data**

Preregister a **new** Layer-2 ticket (not a continuation look of #685) with three separately sealed steps:

1. **Recon.** Extend Stage-1b / Stage B method through 2017 REG W7–W17 (or **W9–W17** if W7–W8 matrix **cd9af285** is accepted after Alex RO). Same eligibility; T2 misses retained; expected complete ~141 (or ~119 if W9–W17 only).
2. **IF score.** Owner CLEAR for Stage C: one invoke @ **6ca03716**, blend=0, `BIND_PACKET_ONLY` rest, complete 27/27 only. New `SCORE_RESULTS` sha — do not write over **2b9f302e**.
3. **Q2s emit + one look.** Same frozen `0.5*IF+0.5*q2_pm_new`. Fit-exclusion proof on the new manifest. Receipt **before** the look (below).

Until those CLEARs exist: **stop**. Q2-only mechanical emit may be inventoried but must not be labeled the IF+Q2s comparison and must not run Appendix O under this ticket.

---

## Protocol — any NEXT scored experiment

t5035u M1 (`404a4ab2`): `PROTOCOL_FREEZE` omitted scored rows; compare tested `FREEZE.exists()` only. That is **not** a receipt.

A later scored experiment requires a **real pre-look independent receipt**, bound **before any outcome look**, to the **exact** bytes of:

| Bound | Example of what “exact” means |
|---|---|
| code | adapter + blend + IF tip **6ca03716** object hashes (not “file present”) |
| config | frozen **aa2b47b3** / fit **70db070d** / w=0.5 / as-of **cf514078** |
| manifest | sha256 of the sealed game_id list (selection-hash recipe) |
| rows | sha256 of the emitted `research.q2s` JSON (the t5033u hole: rows `0d6a5e14` were unbound) |

Re-hash every pin at compare time (t5035u guard pattern). Refuse on mismatch. One look. Stop. File-exists is insufficient.

---

## Locks (this note)

≠rebuild ≠score ≠Appendix O ≠outcome look ≠alternate weight ≠merge ≠deploy ≠pub ≠bet ≠CERT ≠E1 ≠Stage C ≠lift 83646d78 ≠reopen 03a4dd90 ≠edit `2805f42e` guard.

Label: **RETRO_FIT / DEV_RESEARCH**. Inventory only. Not a forecast-quality claim.
