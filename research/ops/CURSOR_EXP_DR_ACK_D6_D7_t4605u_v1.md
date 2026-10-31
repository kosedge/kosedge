# CURSOR ACK — Exp D-R D6 / D7 t4605u v1

**PAPER-ONLY · CERT=0 · NFL NO-GO · F2 FROZEN · #648 DRAFT**

Filed 2026-10-28. Cursor (cloud eng). **No Exp D-R run.** No Odds. No merge. Not CLEAR to execute.

Closes IMV RETURN v2 `45d0aed5` residuals **D6** (column count) and **D7** (stop precedence). Same pattern as t4586u ACK / v1.1 precedence: this file adopts; feasibility v1 `9906430e` is **frozen** (not rewritten).

| bind | sha8 |
|---|---|
| IMV_GRADE Exp D-R PRE-REG v2 (RETURN) | **45d0aed5** |
| COS_ORDER this ACK | **01b41b79** |
| COS_FREEZE D6 option (B) four-col | **81998210** |
| ALEX_EXP_DR_STOP_ERRATUM §5 STOP BOX | **6bd07cc8** |
| Cursor FEASIBILITY v1 (frozen) | **9906430e** |
| Alex diagnosis (unedited) | **81a6727d** |
| H2 FROZEN | **db2cf4b2** |
| G34 predictions comparator | **c3248302** |
| Ryan DECISION | **e65b9c77** |
| CoS ACCEPT of 6bd07cc8 (cited by IMV) | **6751ec52** |

**VERDICT: ACK — adopted.** D6 = CoS FREEZE (B). D7 = Alex `6bd07cc8` §5 governs. Floor not re-opened.

**Institutional memory:** `no prior grades` for this ACK product. Forward-only from IMV `45d0aed5` · Alex `6bd07cc8` · CoS freeze `81998210`.

---

## D6 — ADOPT CoS FREEZE (B): `X_rest` = exactly 4 columns

Supersedes Cursor feasibility `9906430e` **§3.3** “exactly 3 columns” LOOK. CoS picked (B). IMV did not invent.

**Frozen `X_rest` (four fit columns, four β_rest):**

| # | column | definition |
|---|---|---|
| 1 | `drest_clip` | `clip(r_h' − r_a', −7, +7)` with `r' = 0` if NaN else rest |
| 2 | `short_h` | `1` if `rest_home ≤ 5` **and** not NaN; else `0` |
| 3 | `short_a` | `1` if `rest_away ≤ 5` **and** not NaN; else `0` |
| 4 | `rest_missing` | `1{home NaN or away NaN}` |

Still frozen from `9906430e` §3.2 (unchanged): `nflverse_gameday` on emit `02f6b2e2` / `games.csv` `4fe1cdd7`; `>21d` → NaN; no new Odds; no new PBP; no DOW heuristic; no `simulate_nfl_game`.

**Equation (pinned):**

```text
pm_DR = pm_G34 + X_rest · β_rest
β_rest = (β_drest, β_short_h, β_short_a, β_missing)   # 4 coefficients
```

- G34 cell + H2 folds **frozen**. Comparator `c3248302`.
- Fit: intercept-free OLS `(m − pm_G34) ~ X_rest` on seasons `< S` only. HC1 diagnostic; point β used.
- Alex erratum §6 table schema (`beta_missing_ind`) is now aligned.
- Adding or dropping a column after the first scored run = **VOID**.
- Cost remains **S** (ratings not re-walked).

---

## D7 — STOP PRECEDENCE: Alex `6bd07cc8` §5 STOP BOX GOVERNS

Cursor feasibility `9906430e` **§8 DRAFT** (diagnosis copy: OR-path (b), point Δ ≥ 0.10, “IMV decides”, dual-floor language) is **WITHDRAWN for Exp D-R**.

Do **not** re-open the floor choice. `RESEARCH_FLOOR_vs_G34 = 0.05`. Exp A `ddffb72e` §4 0.10 **does not apply** to D-R.

**Frozen STOP BOX (verbatim meaning of Alex §5; binding = pooled ≤2022 OOF, F1–F9, H2 `db2cf4b2`). RESEARCH PASS iff ALL of:**

1. **Path M (mandatory encompassing):** `m ~ a + b·mm + c·pm_DR` (OLS HC1); **c > 0** and the 95% CI excludes 0.
2. **Vs G34:** paired game bootstrap **B=10000**, seed **4141**; percentile 95% CI on Δ_DR excludes 0 **AND** point Δ_DR ≥ **`RESEARCH_FLOOR_vs_G34 = 0.05`**.
3. **D4 artifacts** per Alex §6 (β_rest HC1 table including `beta_missing_ind`; short-rest subset supportive; missingness rates from hashed emit).

`Δ_DR = mean(gap_G34) − mean(gap_DR) = mae_G34 − mae_DR` (market terms cancel; Δ is **not** market-relative — path M is that gate).

Also frozen from Alex §3–§5:

- 2023 supportive only / cannot-alone-PASS. 2024+ forbidden.
- FAIL if any conjunct fails → G34 stays the benchmark.
- VOID if stop, floor, comparator, folds, features, or coding change after first scored run.
- Primary comparator `c3248302`. EPA secondary (report only).
- **Research PASS ≠ market bar ≠ CERT.** Ryan-visible: CERT/product still needs mae ≤ mae_market with uncertainty and/or `seasons_beating_market > 0`, plus IMV/Ryan CLEAR. Hard FAIL note for future CERT if `seasons_beating_market == 0` or `mae_DR ≥ mae_market` unless a separate Ryan CLEAR waives it.
- Old OR-(b)-alone **removed**. No 0.10 on D-R.

---

## What this ACK does not do

- Does not run Exp D-R. Does not write `rest_emit.csv`. Does not fit β_rest.
- Does not rewrite feasibility `9906430e` (frozen) or diagnosis `81a6727d` (unedited).
- Does not merge #646/#647/#648. Does not touch LOCKED_SCORING / F2 / Odds.
- Does not claim PASS_PROTOCOL, CLEAR, or CERT. IMV v3 re-grade is next. Execution still needs a **new Ryan CLEAR**.

NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · G34 not promoted
