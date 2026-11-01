# PROPOSAL (NOT APPROVED) — t5021u Lane A Q2→IF diagnostic join

**Status:** PROPOSAL paper only. **Not approved. Not CLEARED. Not an EXEC. Not a formula.**  
**Label:** DEV_RESEARCH · CERT=0 · NFL NO-GO · pub/bet HOLD  
**Mode:** research paper. **Do not merge · do not deploy · do not consume · do not change model math or prices · no EVAL · no retune · no new experiment · no new source.**

**Writing this file does not approve Lane A, Lane B, any formula, any weight, any replacement policy, or any join EXEC.**

**Paper preparation ≠ authorization to consume or change the model.**

---

## Authority

| Item                                | Tip / object                                                            | Role                                                                                    |
| ----------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| OWNER                               | t5021u                                                                  | Chief of Staff ORDER — paper prep only                                                  |
| Cursor ORDER box                    | `COS_ORDER_CURSOR_t5021u_Q2_LANE_A_JOIN_PAPER.md` tip **`ef7d737e`**    | Sealed ORDER for this paper                                                             |
| DIRECTION                           | **`849ccfd6`**                                                          | Direction tip cited with the ORDER                                                      |
| Missing-math card                   | **`88959dd2`**                                                          | Identified missing math; consumption + operational-price changes stay HELD              |
| Standing RO / paper-prep delegation | **`97925eb5`** + clarify **`d7e2a0e2`**                                 | Paper prep needs no further OWNER ack. Formula selection and EXEC remain **Needs Ryan** |
| Q2 keep ACCEPT                      | **`03a4dd90`**                                                          | Keep packet remains research-consumed; do not merge #679                                |
| #680 map                            | Alex PASS_RO_MAP **`4a1bc064`**                                         | Map only; no re-review                                                                  |
| #681 paper / ACCEPT                 | head **`e30e6f9c`** / CoS ACCEPT **`fc03a463`**                         | Field contract; not wiring                                                              |
| Wiring card                         | **`013ec7f8`**                                                          | Supersedes prior card tip `1e71808d` after CLEAR status update (see N2)                 |
| #682 writer                         | ACCEPT **`d17b30fa`** · Alex **`f55e9ffc`** · DRAFT head **`7d89a974`** | Offline artifact writer; **no forecast join**                                           |
| Layer-2 IF caller                   | `score_t4910u.py` @ **`6ca03716`**                                      | Offline diagnostic IF invoke (#672); not Layer 3                                        |
| CLEAR-A lineage                     | **`1b39f4e9`**                                                          | IF/ledger symbols on `deploy-vercel`; not wired to prod callers                         |

**IF in this paper = Independent Fair (CLEAR-A), not injury-factor.** Injury overlays stay out of Q2 keep / sidecar / Lane A scope.

**no prior grades** — research filing, not a recurring desk product. Knowledge ledger folders have no graded cards.

---

## 0. Identity

| Item                          | Value                                                                                      |
| ----------------------------- | ------------------------------------------------------------------------------------------ |
| This paper                    | t5021u · `research/q2_phase_b_t5009u/PROPOSAL_Q2_LANE_A_DIAGNOSTIC_JOIN_t5021u.md`         |
| Inspected live tip            | `origin/deploy-vercel` @ `f5e3bb58ccbe5a8892fed2a01f347c2308394a2f`                        |
| Q2 keep packet (do not merge) | draft [#679](https://github.com/kosedge/kosedge/pull/679) @ `af6be4f5`                     |
| RO map (do not re-do)         | draft [#680](https://github.com/kosedge/kosedge/pull/680) @ `be8c27a6`                     |
| Field contract                | draft [#681](https://github.com/kosedge/kosedge/pull/681) @ `e30e6f9c`                     |
| Offline sidecar writer        | draft [#682](https://github.com/kosedge/kosedge/pull/682) @ `7d89a974`                     |
| Offline IF diagnostic score   | draft [#672](https://github.com/kosedge/kosedge/pull/672) · `score_t4910u.py` @ `6ca03716` |

This PR carries **this markdown file only**. It does not copy #679 keep modules, #682 writer code, or any Python.

---

## 1. Three-layer reminder (do not collapse)

These three layers are **not interchangeable**. A sentence that says “IF is tests-only” or “IF is prod blended” without naming the layer is a defect.

### Layer 1 — Repository code on `deploy-vercel`

Symbols **present** at inspected tip `f5e3bb58` via CLEAR-A merge `1b39f4e9` (#657). Presence ≠ production invoke.

| Symbol / path                                          | Live location                                                                                                             | What it is                                                                                                |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `simulate_nfl_game(..., independent_fair=False\|True)` | `services/model-service/src/services/nfl_simulator.py:519`                                                                | Default path is the flag-OFF blended entry. Opt-in flag attaches labeled IF mus with `market_blend=0`.    |
| `simulate_nfl_game_independent_fair`                   | `nfl_simulator.py:877`                                                                                                    | Explicit labeled IF entry. Docstring: never the live default.                                             |
| `independent_fair_mus`                                 | `nfl_simulator.py:914`                                                                                                    | Reads labeled IF mus; fail-closed if unlabeled or blend ≠ 0.                                              |
| EPA / packaged strength                                | `tasks.py` `_load_team_strength_priors` / `_resolve_team_strength_indices`; HTTP uses `resolve_adhoc_simulation_strength` | Live strength SoT → `NflGameInputs.offense_index_*` / `defense_index_*`. Not Massey. Not Q2.              |
| Ledger helpers                                         | `nfl_handicap_ledger/schema.py` `L0_REQUIRED_FIELDS`                                                                      | DEVELOPMENT_ONLY — no production capture.                                                                 |
| Layer-1 test imports of the labeled IF entry           | `test_nfl_handicap_clear_a_d3.py`                                                                                         | **Layer 1 only.** Does not describe Layer 2 and does not overwrite OWNER-accepted offline IF caller work. |

### Layer 2 — Accepted offline Independent Fair caller

OWNER/CoS-accepted **offline** invoke of the labeled IF entry. **Not** tests-only. **Not** Railway/Vercel subscriber.

| Artifact                     | Pin                                           | What it is                                                                                                                                                                              |
| ---------------------------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `score_t4910u.py` (#672)     | tip **`6ca03716`** · simulator sha `52d9e909` | Offline IF diagnostic score of 70 complete 2017 REG games. Original score tip `19c6a460` invoked `simulate_nfl_game_independent_fair` × 70. Close tip `02197f58` did **not** re-invoke. |
| `CALL_AUDIT.md`              | same packet                                   | `MARKET_BLEND = 0`, `SIMULATIONS = 4000`. Distinct from the W8 offline eval caller.                                                                                                     |
| CLEAR-P1 shadow orchestrator | draft #662                                    | Local fixture only. Not a production writer.                                                                                                                                            |

`6ca03716` is the sealed **offline diagnostic** IF tip. Live Layer-1 code SoT is CLEAR-A `1b39f4e9`. Those are different claims. `6ca03716` is **not** Layer 3.

### Layer 3 — Deployed blended routes (`routes/nfl.py`)

What the model-service HTTP path **invokes** on inspected live tip `f5e3bb58`.

| Entrypoint                                         | File:lines                                                                                                       | Invoke                                                                                                                                   |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| HTTP blended caller **of record at this tip** (N3) | `services/model-service/src/routes/nfl.py:4739` `POST /simulations/{game_id}` → `:4893` `simulate_nfl_game(...)` | `independent_fair` omitted → `False`. Flag-OFF default path. Audit stamp includes `production_promote=False` (`:4908`).                  |
| Celery task (present; **not** N3 SoT)              | `tasks.py:4967` `run_nfl_market_simulations` → `simulate_nfl_game(...)`                                          | Still on the tree. N3 binds that future-consumption discussion treat `routes/nfl.py`, not `tasks.py`, as the blended caller at this tip. |

**Layer 3 does not run subscriber Independent Fair forecasts.** CERT=0 · pub/bet HOLD. Presence of `simulate_nfl_game` on HTTP/task paths is **not** CERT>0, **not** a PLAY tag, and **not** a claim that subscribers consume IF.

`NflGameInputs.offense_index_*` / `defense_index_*` still drive `compute_nfl_projection_decomposition` → MC means. Q2 Massey fields are not on this path.

### Layer-collapse defects (do not write)

| Defect                                                    | Why                                                                                                            |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| “IF is tests-only”                                        | True only for Layer 1 non-definition imports on live HEAD. False for Layer 2 (`score_t4910u.py` @ `6ca03716`). |
| “IF is in production”                                     | Layer 1 code is merged; Layer 3 callers still use flag-OFF `simulate_nfl_game`.                                |
| “`6ca03716` is the live IF caller”                        | That tip is the sealed offline diagnostic IF tree (#672).                                                      |
| “Week-cap is `cf514078`”                                  | Layer 3 week-cap ≠ kickoff-instant as-of.                                                                      |
| Treating this paper as Layer-3 / operational-price design | Consumption HELD. Layer-3 path design is **not** cleared.                                                      |

---

## 2. Two join classes — keep them sharp

Card tip **`88959dd2`** identified **missing math**. No formula, weight, or replacement policy is approved. This section records the gap. It does **not** fill it.

### 2a. Diagnostic annotation / read join (Lane A class)

A join that **never mutates**:

- `offense_index_home` / `offense_index_away`
- `defense_index_home` / `defense_index_away`
- `independent_fair.margin_mu` / `total_mu` / `sigma`
- `L0.margin_mu` / `total_mu` / `sigma`
- `L0.market_blend`
- L0 `off_eff_*` / `def_eff_*`

Properties if a later OWNER CLEAR ever authorized this class (this paper does **not**):

- Research labels only (`q2_*` sidecar fields from the accepted #681 contract).
- Identity join only: `game_id` if both sides have it; else `Game.key` = `(season, week, home, away)`.
- **No forecast margin change.** Attaching a label does not shift MC draws, blend weights, or EPA indices.
- Fail-closed on missing / NaN / bad pin / leakage. No impute.
- May **read** already-emitted #682 artifacts (`7d89a974`) or the sealed keep symbols they reuse. May not write a new transform.

This class is still **not approved** by being described.

### 2b. Strength / forecast-margin-affecting join (Lane B class) — HELD

Any join that would change `offense_index_*`, `defense_index_*`, `margin_mu`, `market_blend`, L0 efficiency fields, or MC draws.

**HELD. Needs Ryan formula.** Card `88959dd2` is the missing-math finding. This paper lists what would be required and **does not approve** any of it.

Required before anyone could even _ask_ to EXEC this class (inventory only — **not a CLEAR**):

1. An OWNER-selected **formula** mapping one or more of `q2_home_s` / `q2_away_s` / `q2_rating_diff` / `q2_pm_new` / `q2_asof_wl_diff` into a live strength or margin object. None exists. Sealed DEV OLS `q2_pm_new = 2.56374413 + 1.66062406 · rating_diff` is a **sidecar annotation**, not an IF `margin_mu` replacement.
2. An OWNER-selected **weight** (or an explicit “weight = 1 / replace” decision). None exists. Do not borrow `NFL_MARKET_BLEND_*` (0.30) or early-season boosts.
3. An OWNER **replace-vs-annotate** policy for EPA indices vs Q2 ratings.
4. An OWNER **entry point**: `NflGameInputs.offense_index_*` / `defense_index_*` vs L0 `off_eff_*` vs `independent_fair.margin_mu` vs L0 `margin_mu` vs a pre-MC intercept shift. Each is a different math change.
5. An OWNER rule for **when diagnostic may become strength** (promotion gate). Default while unset: **never**.
6. A separate OWNER CLEAR that names Layer 3 (`routes/nfl.py` per N3) or Layer 2 (`score_t4910u` @ `6ca03716`) as an allowed consumer. Default: **neither**.
7. Leakage (`cf514078` + `assert_asof_leakage` refuse-on-fail), pin match, and fail-closed missing would still bind. They do **not** substitute for (1)–(6).
8. Diff-proof in §7 would **fail** this class by construction (it forbids edits to `nfl_simulator.py` / sim call sites / ledger / `NflGameInputs`). That is why this class is a different paper, a different CLEAR, and **Needs Ryan**.

**Do not treat §2b as a design.** It is a hold list.

**Do not design Layer-3 / operational price paths as if cleared.** Consumption remains HELD.

---

## 3. Every missing OWNER decision

Formula selection and EXEC remain consequential (**Needs Ryan**). Standing RO authority covers **paper prep only**.

| #   | Decision                                   | Why it is missing                                                                                                          | Default while unset                                                                 |
| --- | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| D1  | **Formula**                                | `88959dd2`: no approved map from Q2 sidecar numbers into indices or `margin_mu`. Sealed `a_q2`/`b_q2` are annotation-only. | No formula. Do not invent one.                                                      |
| D2  | **Weight**                                 | No blend coefficient between Q2 and EPA / IF mu is approved.                                                               | No weight. Do not reuse market-blend 0.30.                                          |
| D3  | **Replace vs annotate**                    | #681/#682 isolate sidecar as non-authoritative payload beside L0/IF. Replacement was never asked.                          | Annotate-only is the Lane A _shape_; it is still **not approved**. Replace is HELD. |
| D4  | **Entry point** into indices / `margin_mu` | Four (or more) distinct write targets, each a model change.                                                                | No entry. No writes.                                                                |
| D5  | **When diagnostic may become strength**    | No promotion gate. Writing Lane A first must not be read as a scheduled flip.                                              | Never, until a later OWNER CLEAR names a gate.                                      |
| D6  | **Which caller may read a join**           | Layer 2 (`6ca03716`) vs Layer 3 (`routes/nfl.py` per N3) vs research files only.                                           | Research files only. No caller wiring.                                              |
| D7  | **Writer vs reader**                       | Whether a join EXEC may re-run `emit_q2_asof_sidecar.py` or only read `7d89a974` artifacts.                                | Neither authorized by this paper.                                                   |
| D8  | **Sample / window**                        | No new game set is commissioned. #682 demo = 2013 REG W2 (16 rows). #672 = 70 games offline IF.                            | No new sample. No second EVAL.                                                      |
| D9  | **FQ / CERT / scored `1ee90fac` reuse**    | Explicitly forbidden to claim.                                                                                             | CERT=0. Scored `1ee90fac` BLOCKED. No FQ PASS.                                      |
| D10 | **Merge / deploy / Layer-3 price path**    | Production contract is `deploy-vercel`. This tree is draft research.                                                       | No merge. No deploy. Operational prices HELD.                                       |

Until D1–D5 exist as OWNER writes, **any strength/margin join is out of scope**. Until D6–D8 exist, even a diagnostic reader is out of EXEC scope. This paper does not supply those writes.

---

## 4. ONE bounded diagnostic-first Lane A design (for Ryan review — NOT APPROVED)

**Recommended shape for review only.** Describing it does **not** approve it, CLEAR it, or authorize implementation.

**Name:** Lane A — diagnostic annotation/read join (identity only).

**Bound:**

1. **Read** existing `Q2AsOfSidecar` rows as specified by #681 (`e30e6f9c` / ACCEPT `fc03a463`) and emitted by #682 writer head `7d89a974` (ACCEPT `d17b30fa`, Alex `f55e9ffc`). Fields stay the contract set: identity + `q2_home_s` / `q2_away_s` / `q2_rating_diff` / `q2_hfa` / `q2_n_asof_games` + `q2_asof_wl_diff` + `q2_pm_new` + pin shas.
2. **Join** to a research/IF-diagnostic row by `game_id` or `Game.key` only. No fuzzy name/market/week join.
3. **Emit** a research-only annotation document (DEV_RESEARCH labels) that sits **beside** the other row. Copy sidecar fields; do not recompute ratings; do not apply a new map.
4. **Never write** `offense_index_*` / `defense_index_*` / `margin_mu` / `market_blend` / L0 `off_eff_*`. No forecast margin change.
5. **Reuse only** already-accepted symbols: `asof_for_targets`, `asof_wl_diff`, `assert_asof_leakage`, sealed `a_q2`/`b_q2`. No new ridge, OLS, source, or EVAL.
6. **Refuse** the row if leakage assert would fire, if any required field is missing/NaN, if pins mismatch, if 2024–25 would be opened, or if scored `1ee90fac` columns would be required.
7. **Do not** call `simulate_nfl_game` or `simulate_nfl_game_independent_fair` from a new Q2 runner. Do not edit `score_t4910u.py`. Do not touch `routes/nfl.py`.
8. **Stop.** No Stage C. No Layer-3 design. No promotion clause. No “and then feed margin_mu.”

**Out of this bound (still HELD):** §2b strength/margin join; any formula/weight/replace; any entry into indices/`margin_mu`; any claim that diagnostic has become strength.

**Ryan review question this paper is allowed to pose:** whether Lane A as specified is the correct _next paper-to-CLEAR candidate_ — not whether to EXEC it, and not whether to fill `88959dd2`.

**CoS may** ACCEPT this **paper** under standing RO authority (`97925eb5` + `d7e2a0e2`). **CoS may not** EXEC Lane A from this file. **Ryan** owns formula / EXEC if anyone later asks.

---

## 5. Leakage

Sidecar / Lane A as-of remains **`cf514078` (kickoff-instant)**, not week-cap.

| Rule                      | Binding                                                                                                                        |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Prior-game-only           | History filter `h.kickoff_utc < target.kickoff_utc` (strict).                                                                  |
| Current game excluded     | Target cannot appear in its own window (`self-inclusion` on `game_id`).                                                        |
| Same kickoff excluded     | Same-kickoff games do not see each other.                                                                                      |
| Later kickoff excluded    | Not countable in `q2_n_asof_games`.                                                                                            |
| Assert                    | Reuse existing `assert_asof_leakage` (`q2pb/strength.py` on the keep/#682 tree). **Refuse-on-fail.** Do not write a new guard. |
| Week-cap is not this rule | Layer 3 `_fetch_rolling_feature_latest_rows(..., week_cap=)` is `week <= week_cap`. Do not claim week-cap = `cf514078`.        |

If the leakage assert would fire: **do not emit / do not join the row**. No partial fill, no “last good week,” no impute from season-end or from Layer 3 EPA.

---

## 6. Reproducibility pins

Every future Lane A row (if ever CLEARED — **not** by this paper) must carry and match:

| Pin       | Prefix         | What                                                       |
| --------- | -------------- | ---------------------------------------------------------- |
| games     | **`4fe1cdd7`** | primary games.csv (`games_4fe1cdd7.csv` on #679/#682)      |
| fit       | **`70db070d`** | sealed fit object                                          |
| config    | **`aa2b47b3`** | sealed config                                              |
| as-of     | **`cf514078`** | kickoff-instant rule                                       |
| FROZEN md | **`28c582a1`** | sha256 prefix of `FROZEN_CONFIG_Q2PB_t5009u.md`            |
| outcomes  | **`50bda875`** | score-only 2013–2022 extract — **not** an experiment frame |

Keep ACCEPT `03a4dd90` · keep commit `af6be4f5` · writer head `7d89a974` are provenance, not substitutes for the six pins.

Do not retune λ=20, r=0.5, `a_q2`, or `b_q2`. Do not open a second EVAL look (`fe90f5f0` already k: 0→1; research-consumed).

---

## 7. Validation requirements (wiring card `013ec7f8`)

Wiring card tip **`013ec7f8`** supersedes prior card tip `1e71808d` after the CLEAR status update (N2). Any later EXEC that claimed to implement Lane A would have to prove **all** of the following. This paper runs **none** of them (no code, no EVAL).

| Gate                    | Requirement                                                                                                                      |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Pin sha match           | games `4fe1cdd7` · fit `70db070d` · config `aa2b47b3` · as-of `cf514078` (FROZEN `28c582a1` / outcomes `50bda875` as provenance) |
| Leakage green           | `assert_asof_leakage` green on the joined/emitted set; refuse-on-fail                                                            |
| Fail-closed missing     | Missing / NaN / bad pin / 2024–25 / scored `1ee90fac` columns → refuse the row; no silent defaults                               |
| Diff-proof              | **No edits** to `nfl_simulator.py` / sim call sites / ledger / `NflGameInputs`                                                   |
| Layer 3 still blended   | `routes/nfl.py` `POST /simulations/{game_id}` still calls flag-OFF `simulate_nfl_game` (N3). No Layer-3 IF flip                  |
| No second EVAL / retune | Do not re-open `fe90f5f0`. Do not refit `a_q2`/`b_q2` / λ / r                                                                    |
| Labels                  | **DEV_RESEARCH** on the PR, paper, and any artifact                                                                              |
| Review path             | Alex RO → CoS ACCEPT. No self-ACCEPT. No FQ claim                                                                                |
| No FQ claim             | Do not claim FQ PASS. Do not claim scored reuse of `1ee90fac`                                                                    |

A strength/margin join cannot satisfy the diff-proof row. That is intended.

---

## 8. Soft N1–N4 — future-consumption conditions (verbatim)

These are **consumption conditions**, not findings that consumption is authorized. Consumption remains HELD. Cite verbatim:

- **N1:** Cursor ORDER box tip is `09f70480` (chat once cited `8a4bd0ab`) — prefer `09f70480` as sealed tip
- **N2:** wiring card tip `013ec7f8` supersedes prior card tip `1e71808d` after CLEAR status update
- **N3:** blended caller at `routes/nfl.py` (not `tasks.py`) at this tip
- **N4:** games csv provenance column names mention `1ee90fac` (keep-identical; not scored reuse)

N1 names a sealed Cursor ORDER-box tip (`09f70480`) distinct from this paper’s ORDER tip `ef7d737e`. Prefer `09f70480` when consuming that box; do not “fix” chat citations of `8a4bd0ab` by rewriting history. This paper cites **`ef7d737e`** as the t5021u Lane A join-paper ORDER.

N3 does not delete `tasks.py:4967`. It binds the Layer-3 caller-of-record for future consumption talk at this tip.

N4 is **keep-identical provenance naming**, not a license to reload scored hist-index columns. Gate `83646d78` still blocks scored reuse of `1ee90fac`.

---

## 9. Explicit holds (do not propose lifting)

- **Consumption HELD** — including model consumption of Q2 sidecar fields and any operational-price change
- **Stage C AMEND** — not cleared
- **Scored `1ee90fac` BLOCKED** (gate `83646d78`) — N4 keep-identical mention is not scored reuse
- **CERT=0**
- **pub/bet HOLD**
- **No merge / no deploy** of this PR, #679, #680, #681, or #682
- **No Layer-3 / operational price path** designed as if cleared
- **No FQ PASS** claim
- **No S1 revive** (kill `50f57195`)
- **No 2024–25** access
- **No second EVAL / retune**
- **No Python / code** in this PR that changes model behavior or prices (this PR has no Python)

---

## 10. What this paper is not

- Not authorization to consume Q2 or change the model.
- Not a formula, weight, or replace-vs-annotate policy.
- Not an EXEC of Lane A or Lane B.
- Not a Layer-3 IF flip.
- Not a new experiment, EVAL, retune, merge, or data source.
- Not a claim that #682 already joined forecasts (it did not).
- Not a claim that `6ca03716` is live production IF.
- Not FQ PASS. Not scored reuse of `1ee90fac`.

---

## 11. Single recommended next action

**Ryan (or CoS under standing RO) may ACCEPT this paper as a proposal record.** That ACCEPT is **docs-only**.

Do **not** EXEC Lane A. Do **not** fill `88959dd2`. Do **not** commission a strength/margin formula. Do **not** merge this PR.

If a follow-on is wanted later, the next OWNER ask is **CLEAR or refuse a diagnostic-only reader** that implements §4 and proves §7 — still paper-to-CLEAR, still Needs Ryan for EXEC, still no formula.

Until then: Q2 keep stays research-consumed on draft #679; sidecar writer stays draft #682; IF diagnostic caller stays #672 @ `6ca03716`; Layer 3 stays blended `routes/nfl.py` `simulate_nfl_game`.

---

## 12. Citations

OWNER t5021u · ORDER **`ef7d737e`** · DIRECTION **`849ccfd6`** · missing-math **`88959dd2`** · delegation **`97925eb5`** · clarify **`d7e2a0e2`** · keep **`03a4dd90`** · Alex PASS_RO_MAP **`4a1bc064`** · #681 paper **`e30e6f9c`** / ACCEPT **`fc03a463`** · wiring **`013ec7f8`** (supersedes `1e71808d`) · #682 ACCEPT **`d17b30fa`** · Alex **`f55e9ffc`** · writer head **`7d89a974`** · IF caller **`6ca03716`** · CLEAR-A **`1b39f4e9`** · games **`4fe1cdd7`** · fit **`70db070d`** · config **`aa2b47b3`** · as-of **`cf514078`** · FROZEN **`28c582a1`** · outcomes **`50bda875`** · gate `83646d78` · S1 kill `50f57195` · N1 sealed box `09f70480` · live tip `f5e3bb58` · EXEC keep `af6be4f5` · map `be8c27a6`.
