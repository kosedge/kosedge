# CURSOR EXP D-R FEASIBILITY — t4605u v1

**PAPER / READ-ONLY FEASIBILITY · CERT=0 · NFL NO-GO · F2 PHI@WSH FROZEN · sealed=1**  
**NOT CLEAR TO EXECUTE.** No rest emit written. No β_rest fit. No Odds. #648 stays **DRAFT**.

Filed 2026-10-28. Cursor (cloud eng) seat. Authority: CoS order `349b3250` · DECISION_RYAN `e65b9c77` · Alex diagnosis `81a6727d` (CoS ACCEPT `eb8c4501`).

This paper answers: can Exp D-R (honest schedule-rest on frozen G34) be run from **already-hashed** schedule/feature files **without** new Odds or new PBP? It pins the feature recipe, the design-matrix extension, scripts, hash-before-run, and FAIL modes so IMV can pre-register. It does **not** authorize a run.

**Institutional memory:** `no prior grades` for this D-R research-diagnostic product. Forward-only from Exp E PASS `3d79c41b` / Exp A packet tip `6f1fe16b` / Alex `81a6727d`. Do not invent grades.

```text
❌ BAD: re-run the 54-cell grid; feed rest into simulate_nfl_game; scrape Odds; use DOW heuristic rest; peek 2024+
✅ GOOD: date-diff rest from hashed gameday → fold-fit β_rest only on frozen G34 pm_A (c3248302) → score vs G34
```

---

## 0) Authority / hash table (recomputed this filing)

| item | sha8 | status |
|---|---|---|
| COS_ORDER_CURSOR_t4605u_EXP_DR_FEASIBILITY_v1 | **349b3250** | MATCH `349b3250fb597354141758ddb78302ca828d359466fa4569ec116b66ee748c0f` |
| DECISION_RYAN_t4605u | **e65b9c77** | cited (source file not mounted on this VM) |
| ALEX_MARKET_GAP_DIAGNOSIS_t4605u_v1.md | **81a6727d** | MATCH `81a6727dedebed6a481f76d297e11cdbb70f4754da019821dd1cd98f315aebf7` |
| ALEX numbers sidecar | **e4c4ee3f** | MATCH `e4c4ee3f683004f5f65afa6c4edaa07ca57b7dc8af38a1ce254d37d16f91456a` |
| CoS ACCEPT of 81a6727d | **eb8c4501** | MATCH `eb8c4501a74e45e67d1b52535a99555871367cfb104daa2addf4984f75c3fbda` |
| H2 FROZEN manifest | **db2cf4b2** | MATCH (this tree) |
| Exp A predictions.csv | **c3248302** | MATCH (this tree; G34 only) |
| Exp A counts.json | **b60deb6a** | MATCH |
| Exp A selected_cell.json | **3172b236** | MATCH |
| Exp A stop_rule.json | **e14e235d** | MATCH |
| games.csv | **4fe1cdd7** | MATCH |
| historical_oos_games.csv | **1ee90fac** | MATCH |
| EPA emit 02f6b2e2 | **02f6b2e2** | MATCH via `git show` #646 cite (not a merge); cache bytes MATCH |
| Exp E counts (rest placeholder) | **b0365365** | MATCH; `n_rest_placeholder=2992` |
| Exp E rest_catalog.csv | **82b956ec** | MATCH; **cite-only** (kickoff recipe; not the D-R emit) |
| Alex SPEC §4 | **ddffb72e** | cited; 0.10 floor unchanged |
| ESTIMATOR addendum | **84a28a05** | cited; not edited |
| Cursor ACK | **6fcc0af6** | cited |
| FEASIBILITY E/A v1.1 | **15ee3a1b** | cited |
| Exp A IMV_PASS (Alex bind) | **0d1f4f9b** | cited (grade file not mounted) |
| Packet tip | **6f1fe16b** | this branch HEAD at paper start |

`/workspace/ops/nfl_enterprise_green_t4359u/` is **absent** on this VM. Paper lands on the #648 DRAFT sibling path (`data/ops/` + `research/ops/` + `research/nfl/t4605u_exp_dr_feasibility/`). No directory invented under `ops/`.

---

## 1) Verdict

**FEASIBLE as a research script. Not authorized to run.**

| question | answer |
|---|---|
| Rest emit from hashed schedule/features without new Odds / new PBP? | **YES** |
| Primary date SoT | `nflverse_gameday` on emit `02f6b2e2` / twin `games.csv` `4fe1cdd7` (2992/2992 non-empty) |
| Cross-check date (not required to emit) | OOS `1ee90fac` `game_date` (2992/2992 non-empty on ≤2023) |
| New Odds? | **NO** |
| New PBP download? | **NO** (2012 PBP not required; openers are NaN by pin) |
| G34 cell + H2 folds frozen? | **YES** — do not re-walk ratings, do not re-grid |
| Comparator | Exp A `predictions.csv` **c3248302** (pm_A / m / mm / fold) |
| What is fitted? | **β_rest only** (3 columns), prior seasons `< S` |
| Cost | **S** under this pin (Alex said S–M; M only if ratings were re-fit — that path is **forbidden**) |
| Production / LOCKED_SCORING / `simulate_nfl_game` | **untouched** |
| CERT | **0**. D-R cannot close the market gap (Alex expected residual ≈0.29–0.34). |

---

## 2) What D-R is / is not

| D-R is | D-R is not |
|---|---|
| Honest **schedule-date** rest on the frozen G34 linear margin | A second 54-cell search |
| Fold-fit **β_rest** on prior seasons only | Refit of ridge-joint ratings, ρ/λ/ρ_s, or G34 β/HFA |
| `pm_DR = pm_G34 + X_rest · β_rest_S` | `simulate_nfl_game` rest_delta / short-rest ±0.30 |
| Comparator = sealed G34 predictions `c3248302` | Market as a design column |
| One look at 2023 after freeze | Fit, peek, or PASS on 2023; any 2024+ |

G34 stays the **research benchmark** (not promoted). EPA baseline `pm_epa` stays a **secondary** report-only comparator.

---

## 3) Rest emit — pin (no new Odds / no new PBP)

### 3.1 CODE FACT inventory (this seat; no D-R emit written)

| source | pin | rest / date fields | this seat |
|---|---|---|---|
| EPA emit `02f6b2e2` | #646 cite; sha MATCH | `nflverse_gameday`, `kickoff_utc`, `rest_days_home`, `rest_days_away` | header present; bytes MATCH in cache |
| `games.csv` `4fe1cdd7` | in-repo | same columns | `nflverse_gameday` empty **0**; `kickoff_utc` empty **0**; `rest_days_*` = **7.0 on 2992/2992** |
| OOS `1ee90fac` | in-repo | `game_date` | empty **0** on 2013–2023 n=2992; 2024+ n=586 **must drop** |
| Exp E rest_catalog `82b956ec` | in-repo | kickoff-to-kickoff `rest_true_*` | catalog only; used 2012 PBP meta — **not** the D-R recipe |
| Live nflverse schedules | — | mutable | **UNPINNABLE**; do not download |

Emit placeholder rest = 7.0 everywhere is RCA I-1 / Alex §5.5. Confirmed on `games.csv` (nunique=1). That column is **not** a D-R feature.

### 3.2 Date grain (pinned)

Alex §7: rest from **schedule dates** (`nflverse_gameday` on `02f6b2e2`, or `game_date` on `1ee90fac`).

**Cursor pin (one recipe):**

1. Join emit `02f6b2e2` ↔ `games.csv` `4fe1cdd7` on `game_id` (expect 2992/2992). FAIL if `nflverse_gameday` differs on any row.
2. `game_date` := date(`nflverse_gameday`) (calendar day, America/not-needed — the column is already a date).
3. Per franchise (`canonicalize_team`: STL→LAR, SD→LAC, OAK→LV, LA→LAR, WSH→WAS):
   - sort that team's 2013–2023 panel games by `(game_date, kickoff_utc, game_id)`
   - `rest_days` = `(date_G − date_prev).days` if a previous **panel** game exists, else **NaN**
4. If `rest_days > 21` (opener / long layoff / post-bye long gap) → **NaN** (Alex §5.5 / §7).
5. No 2012 PBP. Week-1 2013 prior games are off-panel → NaN. That is the opener rule, not a hole to fill.
6. Do **not** use `kickoff_utc` fractional days as the D-R feature (that is the Exp E catalog recipe). `kickoff_utc` is allowed only as a **tie-break** when two games share a gameday (should not happen for one team).
7. Do **not** use `rest_days_from_schedule` (DOW heuristic: Thu→4, Mon→6, else 7; both teams same). Forbidden.
8. Do **not** call `compute_rest_fields` / `simulate_nfl_game`. Cite-only.

OOS `game_date` is a **join audit** (expect date match after canonicalize). A mismatch is a FAIL/BLOCKED, not a silent fallback.

### 3.3 Feature columns (pinned; 3 columns)

CoS: `Δrest ±7` + `short-rest ≤5` + `opener/bye NaN→0+indicator`.  
Alex §7 hypothesis: rest-diff clipped ±7 **plus home/away short-rest ≤5 indicators**.  
Alex §7 controls: “3 columns, clip ±7, short ≤5, openers/post-bye >21d → rest=NaN→0 with indicator”.

**Pinned `X_rest` (exactly 3 columns; no fourth without IMV pre-reg):**

| col | definition |
|---|---|
| `drest_clip` | `clip(r_h' − r_a', −7, +7)` |
| `short_h` | `1` if `rest_days_home ≤ 5` **and** rest_home is not NaN; else `0` |
| `short_a` | `1` if `rest_days_away ≤ 5` **and** rest_away is not NaN; else `0` |

Transforms (not extra β columns):

- `r' = 0` if rest is NaN else rest. This **is** CoS `NaN→0`.
- Short indicators are `0` when rest is NaN. That is the implementable reading of “NaN→0+indicator” **without** adding a 4th column.

**LOOK (non-blocking; IMV decides in pre-reg):** an explicit `rest_missing = 1{home NaN or away NaN}` would be a **4th** column. Adding it after the run is **VOID**. If IMV wants it, freeze it **before** CLEAR.

Bye weeks with gap ≤21 stay numeric (~14 d typical). They are not forced to NaN.

### 3.4 Why this does not need new PBP or Odds

- Dates live on hashed emit / games / OOS.
- Market labels stay on OOS `1ee90fac` (`mm = −market_spread_home`) — already pinned; no Odds API.
- Ratings / `pm_G34` live on `c3248302`. No ridge re-walk, so no PBP.
- 2012 is not required because `>21d` / missing-prev → NaN.

Alex §5.5 coverage (cite `e4c4ee3f`, **not re-derived here**): derived rest non-null ≈77% of ≤2022 OOF; 758 games with nonzero rest-diff. D-R must **report** its own coverage after a hashed emit; it must not silently change the 21-day / clip / short thresholds to chase that 77%.

---

## 4) Design matrix / β_rest (G34 + H2 frozen)

### 4.1 Frozen objects (do not refit)

| object | pin | D-R may |
|---|---|---|
| Grid cell G34 | ρ=0.95, λ=2.0, ρ_s=0.67, HFA=`fold_fit`, n0=8.0 · `3172b236` | read |
| H2 folds F1–F9 | S=2014…2022 · `db2cf4b2` | reuse |
| `pm_A`, `rating_diff_home`, fold `beta`/`hfa` | `c3248302` | **freeze**; do not overwrite |
| Ridge-joint ratings | ESTIMATOR_ID `nfl-research-opp-adj-epa-v0-ridge-joint` | **do not re-walk** |
| Market `mm` | OOS `1ee90fac` | label / metric only |

### 4.2 Equation (pinned)

```text
pm_DR = pm_G34 + β_drest·drest_clip + β_sh·short_h + β_sa·short_a
```

- `β_rest_S = (β_drest, β_sh, β_sa)` is fold-fit on seasons **`< S`** only (2013 burn-in onward that appear on `c3248302` design rows).
- Fit: `(m − pm_G34) ~ drest_clip + short_h + short_a` — **intercept-free** (same style as Exp A β when HFA=off).
- HC1 SEs diagnostic only; **point** β_rest used.
- 2023: β_rest frozen from ≤2022 (fit on 2014–2022 OOF rows + 2013 design if present in rest emit; **no 2023 in X**). Grid / G34 unchanged. 2023 cannot alone PASS.
- Neutral rows: rest columns still apply (rest is not HFA). Do not zero them.
- **Do not** refit G34 `β` or `hfa`. **Do not** put `mm` in X. **Do not** stretch `pm_DR`.

This is the “3-column extension” of the Exp A linear path. It is **not** an edit of `fit_joint` and **not** a new HFA.

### 4.3 Folds (copy H2; D3 still holds)

| fold | S | fit β_rest | evaluate | status |
|---|---:|---|---|---|
| F1…F9 | 2014…2022 | seasons `< S` | S | **primary** (pooled ≤2022 OOF) |
| — | 2023 | frozen ≤2022 | 2023 one look | **supportive** · cannot alone PASS |
| — | 2024+ | — | — | **forbidden** |

Join D-R rest → `c3248302` on `game_id`. Binding n must = **2440**. 2023 n must = **285**. FAIL if drift.

---

## 5) Scripts to touch (exact)

**NEW (authorized only after Ryan CLEAR + IMV pre-reg):**

| path | role |
|---|---|
| `research/nfl/t4605u_exp_dr_rest_emit.py` | Hash-before-read; write `rest_emit.csv` + coverage counts; **no OLS** |
| `research/nfl/t4605u_exp_dr_fold_validate.py` | Join `c3248302`; fit β_rest only; emit Δ_DR, §4 (a)(b), SHA256SUMS, REPORT |

**READ-ONLY (import helpers / pins; do not modify):**

| path | role |
|---|---|
| `research/nfl/t4602u_exp_a_ridge_joint.py` | `ols_hc1` / HC1 CI only |
| `research/nfl/t4602u_exp_a/predictions.csv` | comparator `c3248302` |
| `research/nfl/t4586u_exp_a_h2_manifest_freeze/CURSOR_EXP_A_H2_GRID_FOLD_MANIFEST_t4598u_v1.json` | fold table |
| `research/nfl/t4586u_exp_e_inputs/games.csv` | `4fe1cdd7` |
| `research/nfl/t4586u_exp_e_inputs/historical_oos_games.csv` | `1ee90fac` |
| #646 emit (git show) | `02f6b2e2` cite, not merge |
| `src.services.nfl_canonical_teams.canonicalize_team` | franchise aliases |

**DO NOT TOUCH**

- `LOCKED_SCORING` / `config_overrides` / `simulate_nfl_game` / `NflGameInputs`
- H2 freeze bytes `db2cf4b2`
- Exp E seals (`b0365365` / `1d7f5c78` / `aa9d37e0`) / H1 addendum `5d426ae9`
- Exp A sealed outputs (except **read** `c3248302`)
- `apps/web` / F2 PHI@WSH
- Production `rest_days_from_schedule` / warehouse

Alex’s “extend `t4602u_exp_a_ridge_joint.py`” is satisfied by a **new** `fit_beta_rest_only` in the D-R script (or a new helper module). Do not rewrite sealed Exp A `fit_beta_fold`.

---

## 6) Hash-before-run plan

Same discipline as Exp E H1 / Exp A execute.

```text
BEFORE any rest date-diff or OLS:
  sha256(02f6b2e2 emit)
  sha256(4fe1cdd7 games.csv)
  sha256(1ee90fac oos)
  sha256(c3248302 predictions)
  sha256(db2cf4b2 H2)
  sha256(3172b236 selected_cell)
  sha256(t4605u_exp_dr_rest_emit.py)
  sha256(t4605u_exp_dr_fold_validate.py)
  write research/nfl/t4605u_exp_dr/SHA256SUMS.inputs
  FAIL/BLOCKED if any drift vs this paper’s pins

THEN rest emit → hash rest_emit.csv → then β_rest.
Refuse 2024+ in any parsed row (count then drop is not enough if drop is skipped).
```

No Odds calls. No live schedule download. `DATABASE_URL` unset is **fine**.

---

## 7) Outputs (when authorized; not this PR)

```text
research/nfl/t4605u_exp_dr/
  SHA256SUMS.inputs
  SHA256SUMS
  rest_emit.csv          # game_id, rest_h, rest_a, drest_clip, short_h, short_a, nan flags
  counts.json
  betas_rest_by_fold.csv
  fold_table.csv
  predictions_dr.csv     # game_id, pm_G34, pm_DR, m, mm, X_rest
  stop_rule.json         # (a) and (b) vs G34; secondary vs EPA
  metrics_binding.json
  metrics_2023.json
  REPORT.md
  artifact_sha8.json
```

`counts.json` required keys: `n_games`, `n_oof_le_2022` (=2440), `n_2023` (=285), `n_rows_season_ge_2024` (FAIL if >0), `n_join_miss_vs_c3248302` (FAIL if >0), `n_gameday_mismatch_emit_games` (FAIL if >0), `n_rest_nan_home`, `n_rest_nan_away`, `n_drest_nonzero`, `n_short_h`, `n_short_a`, `verdict`.

---

## 8) Stop rule (DRAFT for IMV — copy of Alex §7; floor unchanged)

Cursor does **not** re-anchor. Binding text is Alex `81a6727d` §7.4:

1. Binding = pooled ≤2022 OOF (F1–F9); 2023 supportive, cannot alone PASS; 2024+ forbidden.
2. Primary comparator = **G34 predictions c3248302**; secondary = EPA emit (report only).
3. `gap_X = |m − pm_X| − |m − mm|`; `Δ_DR = mean(gap_G34) − mean(gap_DR)`.
4. PASS requires **(a)** encompassing `m ~ a + b·mm + c·pm_DR` (OLS HC1) with c 95% CI excluding 0 and c>0 **AND** incremental `m ~ a + b·mm + c₁·pm_G34 + c₂·(pm_DR − pm_G34)` with c₂ CI excluding 0 and c₂>0; **OR (b)** paired game bootstrap Δ_DR, B=10000, seed 4141, percentile 95% CI excludes 0 **AND** point Δ_DR ≥ 0.10.
5. Also report: per-season Δ_DR, short-rest subset, T3 `|pm_G34−mm|` tercile gap, mae vs market.
6. FAIL → G34 stays the benchmark; rest stays a documented placeholder-fix candidate. **VOID** if features, fold scheme, stop, or comparator change after run. No CERT under any outcome.

**DRAFT note (Alex, echoed):** expected vs-G34 benefit ≈ **0.00–0.05** MAE; market gap expected to remain ≈ **0.29–0.34**. Path (b)’s 0.10 floor will very likely FAIL. IMV decides whether that is intended. Cursor will **not** lower 0.10.

---

## 9) FAIL / BLOCKED / VOID modes

| mode | trigger |
|---|---|
| **BLOCKED** | input sha mismatch vs pins in §0; emit/`games.csv` `nflverse_gameday` disagree; `c3248302` not G34-only; H2 ≠ `db2cf4b2` |
| **FAIL** | `n_rows_season_ge_2024>0`; `n_join_miss_vs_c3248302>0`; binding n ≠ 2440; 2023 used in β_rest; market column in X; ridge-joint re-walked; `simulate_nfl_game` imported; rest_days emit (7.0) used as the feature; DOW heuristic used |
| **VOID** | any post-run change to the 3 columns, 21-day rule, ±7 clip, ≤5 short, folds, stop, or comparator |
| **not FAIL** | rest NaN on openers (expected); 2023 Δ_DR sign; market gap remaining |

---

## 10) Cost (S–M confirmation)

| item | note |
|---|---|
| Alex | S–M; 1–2 days; 3-column extension + F1–F9 + 2023 |
| Cursor | **S** under §4 (ratings frozen; 9+1 intercept-free OLS; bootstrap B=10000 already written) |
| When it would become M | re-fitting 27 rating walks / 54 cells — **forbidden** |
| Deps | pandas already on the E/A path; numpy OLS; no statsmodels; no DB; no Odds |
| Production collision | none if D-R never writes `nfl_game_context` / packaged priors / web |

---

## 11) Explicit non-claims

- No Exp D-R run. No rest_emit.csv written this filing.
- Alex §5.5 derived-rest slopes (+0.146 / −0.046) are **association**, not a D-R effect. Not re-computed here.
- Exp E rest_catalog (kickoff + 2012 PBP) is **not** claimed as the D-R emit.
- D-R is not expected to close the 0.34 market gap. FAIL is an informative outcome.
- QB / injuries / travel / weather remain MISSING (Alex §5.5). Not in scope.
- G34 is not promoted. CERT=0. F2 frozen. Coming Soon ON.
- `ddffb72e` / `84a28a05` / H2 `db2cf4b2` / Exp A outputs **not edited**.

---

## 12) Authorization boundary

Ryan `e65b9c77` authorized recovery **diagnosis** and this feasibility. Execution of D-R requires: IMV pre-reg of §3–§8 **and** a **new** Ryan CLEAR. This paper is not that CLEAR.

Standing locks: NFL NO-GO · CERT=0 · Coming Soon ON · sealed=1 · F2 frozen · no merge #646/#647/#648 · no deploy · no Odds · no LOCKED_SCORING.

---

## 13) Deliverable seal

| file | role |
|---|---|
| `data/ops/CURSOR_EXP_DR_FEASIBILITY_t4605u_v1.md` | this paper |
| `data/ops/CURSOR_EXP_DR_FEASIBILITY_t4605u_v1.md.sha256` | sidecar |
| `research/ops/` copy | identical bytes |
| `research/nfl/t4605u_exp_dr_feasibility/` copy | #648 sibling |

**Owners:** Cursor (this feasibility) · Alex (diagnosis + DRAFT stop) · IMV (pre-reg) · Ryan (execution GO).

NFL NO-GO · CERT=0 · F2 frozen · no Exp D-R run · no #648 merge
