# ALEX + CURSOR — EXP A ESTIMATOR / β ADDENDUM — t4586u v1

- Filed: 2026-10-27 ~21:15 ET (America/New_York) · AUTHOR: Alex Rourke (statistical pin) · Cursor: eng-mapping ACK pending
- **PAPER-ONLY.** No Exp E / Exp A run. No merge/deploy/Odds/redesign. NFL NO-GO, **CERT=0**, **F2 frozen**.
- Binds: COS_ORDER 8a82be85 · IMV RETURN ca066197 (closes **D2**) · Alex SPEC ddffb72e (no pin change) · Cursor FEASIBILITY e20d8ec3 · Ryan 29eb0f92 · CoS ACCEPT SPEC 5fcdb37e
- **VERDICT: D2 CLOSE candidate — pending Cursor eng ACK + IMV re-grade.**

## 1) Purpose / authority / hashes

Closes IMV D2: generator/β not single-defined across ddffb72e §3 and e20d8ec3 §2.4–2.5. Pins ONE estimator, ONE β, ONE output path, and the grid→knob map **before any run**.

| Artifact | expected | sha256 recomputed this filing | status |
|---|---|---|---|
| COS_ORDER_ALEX_t4586u_EXP_E_A_ESTIMATOR_ADDENDUM_v1.txt | 8a82be85 | 8a82be85d3fc62b3afb5965ceeedcf252f61f4c6b8d987c055ab93b5db3ea9ce | MATCH |
| IMV_GRADE_t4586u_EXP_E_A_PROTOCOL_PAIR_v1.txt | ca066197 | ca06619743be1396797e68673465947378c4b09f2f353dccfa939b9f2e2cd7aa | MATCH |
| ALEX_EXP_E_A_PRE_REG_SPEC_t4586u_v1.md | ddffb72e | ddffb72e78bc2f0b503cb768981d1259b24b79b00e706ed6b29ad2000a9a3aee | MATCH |
| CURSOR_EXP_E_A_FEASIBILITY_DESIGN_t4586u_v1.md | e20d8ec3 | e20d8ec3e6de3193b70daae77aab8ea554432816ebc79844b5c8ae854dd9b259 | MATCH |
| Ryan decision / CoS ACCEPT SPEC | 29eb0f92 / 5fcdb37e | per IMV ca066197 §B (MATCH) | carried by reference |

**Register preflight:** `/workspace/kosedge-registers/` searched for `ESTIMATOR_ID` / `opp-adj-epa` / `ridge-joint` → **MISSING** (no existing Exp A estimator pin). No register write made; any append goes via CoS.

## 2) ESTIMATOR_ID (pinned)

**`ESTIMATOR_ID = nfl-research-opp-adj-epa-v0-ridge-joint`**

Model (e20d8ec3 §2.3, CFB `research_opp_adj.py` fork): `y_{g,i} = μ + h·home_{g,i} + off_i + def_j + ε`, ridge with prior `n0` + prior decay, league off/def centered; eligible plays = emit-identical (pass/run, finite epa), OT excluded, neutral → home=0 inside rating model, kickoff-honest cutoff (requires Exp E PASS).

Why ridge, not Kalman:
- Cursor e20d8ec3 implements/ports CFB-style joint ridge (`fit_joint`/`pregame_fit`/`predict_game` exist); Kalman (ρ, σ_ε) has **no** mapped eng knobs and would leave a second open family (forking path).
- **Kalman CLOSED / out of scope** for this pre-reg; may be a later experiment only under a new Ryan CLEAR + new pre-reg.
- KAV (`iterative_opponent_adjust`), `ke_football/opp_adj.py`, `efficiency_backbone.opponent_adjust_epa`, warehouse CURRENT ROW are **NOT** this estimator; results may not be reported as "KAV worked".

## 3) β definition (pinned)

**Fold-fit from prior seasons only.** For each expanding outer fold, target S ∈ {2014,…,2022}:
- Design set = completed games in seasons **< S** (2013 burn-in onward), each with **pregame** `rating_diff_home` computed as-of that game's kickoff (no same-season residuals of S; no post-game ratings).
- Fit OLS: `actual_margin_home ~ β·rating_diff_home` (+ HFA term iff HFA mode = fold-fit; intercept-free when HFA = off). Neutral-site rows: HFA indicator = 0.
- HC1 SEs reported for diagnostics only; β **point** used for prediction; frozen for all of season S.
- Inner-CV (grid selection) refits β the same way within each inner training set.
- 2023 supportive look: β + grid winner **frozen from ≤2022 selection** (fit on 2013–2022); no refit.

FORBIDDEN: fiat β≈20.9 (or any fixed constant); eval-pred stretch (`pred*k`, `a+b·pred` on eval fold, SD-ratio scaling); market spread as target or design column; fitting β on 2023 or any 2024+ data.

## 4) Output path (pinned)

**Linear:** `margin_A = β · rating_diff_home + HFA` (HFA = fold-fit scalar or 0 per grid; 0 at neutral sites). `pm_A = margin_A`.

- `simulate_nfl_game` / LOCKED_SCORING is **NOT** used for Exp A scored predictions.
- Rationale: SPEC §3 baseline is the unblended emit margin `pm_epa = −epa_trailing_spread_home`; §4 stop rule compares MAE-gap/encompassing on that margin surface. Routing through LOCKED sim reintroduces rest placeholders, HFA +1.05, caps/clamps and the emergent ~12 slope, confounding the opp-adj hypothesis with locked-spine mechanics.
- Research code may **read** emit features (baseline pm_epa); it must not call `simulate_nfl_game`, pass `config_overrides`, or touch LOCKED keys for A's `pm`.

**Cursor eng ACK requested (verbatim ask):** "Cursor confirms it can emit fold-honest pregame `rating_diff_home` per game from `nfl-research-opp-adj-epa-v0-ridge-joint` (kickoff-cutoff, ratings on seasons < S + in-season games before kickoff) and the β/HFA fold fit above, without calling `simulate_nfl_game`, without `config_overrides`, and without any change to LOCKED_SCORING production; and confirms the knob synonyms in §5."

## 5) Grid (SPEC §4, unchanged values) → Cursor knobs

Middle row interpreted as **ridge λ** (not Kalman σ_ε) because ESTIMATOR_ID is ridge-joint.

| Alex param (ddffb72e §4) | values | Cursor knob (e20d8ec3 §2.3) | ACK needed |
|---|---|---|---|
| ρ weekly persistence | {0.90, 0.95, 0.98} | `CURSOR_KNOB:prior_decay` (per-week observation weight decay; weight of a game k weeks old = ρ^k) | confirm synonym/parameterization |
| ridge λ (relative) | {0.5, 1, 2} | `CURSOR_KNOB:n0` (ridge prior strength); λ multiplies the manifest base n0: n0 = λ·n0_base, n0_base fixed in fold manifest before run | confirm n0_base value + synonym |
| ρ_s offseason regression | {0.50, 0.67, 0.80} | `CURSOR_KNOB:offseason_shrink` (week-1 prior = ρ_s·prior-season posterior, league-centered); e20d8ec3 says "no offseason shrink unless in frozen grid" → it **is** in the frozen grid | confirm knob name (not named in e20d8ec3) |
| HFA mode | {fold-fit scalar, off}; neutral=0 | output-layer HFA in §4 (OLS term) ; rating-model `h` fit per ridge as e20d8ec3 (neutral home=0) | confirm `h` stays internal and is not the output HFA |

- 3×3×3×2 = **54 configs max**. β not on grid (fitted §3).
- Selection = inner-CV MAE of margin (vs actual margin, **not** vs market), ≤2022 only; tie → simpler: HFA off preferred, then mid grid values (ρ=0.95, λ=1, ρ_s=0.67).
- Grid file + fold manifest hashed at freeze (H2 TO-HASH).

## 6) Rejected alternatives

- **Cursor FEASIBILITY §2.4 option 1 (no β / leave epa_to_strength_indices unscaled / emergent locked slope ~12) is REJECTED for this pre-reg because it fails H2 (β must be fit from data, not absent/emergent).**
- Cursor §2.4 option 2 (β_epa into simulate) — **SUPERSEDED** by the §4 linear path; not left open.
- Kalman (ρ, σ_ε) estimator — closed (§2).
- LOCKED `simulate_nfl_game` output path — rejected (§4).
- Fiat β≈20.9 / eval stretch / market-fit β — forbidden (§3).

## 7) Relationship to SPEC ddffb72e

ddffb72e **§1–§6 unchanged**. Stop rule **§4 binding** (c>0 HC1 OR boot B=10000 seed 4141 CI excl 0 AND Δ ≥ 0.10; ≤2022 pooled OOF binding; 2023 cannot alone PASS; VOID if changed post-run). This addendum only resolves D2 generator ambiguity (ddffb72e §3 "Kalman or ridge" → ridge; §4 grid row "σ_ε or λ" → λ).

## 8) Authorization

Paper-only. No Exp E/A run. Cursor must ACK adoption (§4 ask, §5 synonyms) and file D1/D3/D4 erratum; IMV re-grades the pair. Any run requires: PASS_PROTOCOL + Exp E PASS + H1–H3 closed + **new Ryan CLEAR**.

## 9) Confirmations

No run executed · no pin change to stop rule / 0.10 floor / seed 4141 · no messages sent · no edits to ddffb72e / e20d8ec3 · no LOCKED_SCORING touch · CERT=0 · F2 frozen · NFL NO-GO.
