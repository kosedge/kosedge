# CURSOR ACK — ALEX EXP A ESTIMATOR ADDENDUM t4586u `84a28a05`

**PAPER-ONLY · CERT=0 · NFL NO-GO · F2 FROZEN · #648 DRAFT**

Filed 2026-10-28. Cursor (cloud eng). No Exp E / Exp A run. No `LOCKED_SCORING` change. No Odds.

| bind | sha8 |
|---|---|
| ALEX_CURSOR_EXP_A_ESTIMATOR_ADDENDUM_t4586u_v1.md | **84a28a05** |
| sha256 | `84a28a057d9fb2980fb21e95bfd6764ee7219365756da096a3103ffbcd5390cb` |
| IMV RETURN | ca066197 |
| Cos erratum order | 4b8a52ec |
| Cursor v1 (frozen) | e20d8ec3 |
| Cursor v1.1 (this delivery) | see sidecar after seal |
| Alex SPEC §4 (governs stop) | ddffb72e |
| Ryan | 29eb0f92 |

**VERDICT: ACK — adopted.** D2 pin accepted as implementable. Completes Cos ACCEPT pending item (1).

---

## §4 ask (verbatim confirmation)

Cursor confirms it can emit fold-honest pregame `rating_diff_home` per game from **`nfl-research-opp-adj-epa-v0-ridge-joint`** (kickoff-cutoff, ratings on seasons `< S` + in-season games before kickoff) and the β/HFA fold fit in addendum §3, **without** calling `simulate_nfl_game`, **without** `config_overrides`, and **without** any change to `LOCKED_SCORING` production.

Implementation surface: new research module under `research/nfl/` (CFB `research_opp_adj.fit_joint` / `games_before_cutoff` / `predict_game` fork). `pm_A = margin_A = β · rating_diff_home + HFA`. Emit CSV `02f6b2e2` is **read** for baseline `pm_epa` only.

---

## §5 knob synonyms (confirmed)

| Alex param | values | Cursor knob | ACK |
|---|---|---|---|
| ρ weekly persistence | {0.90, 0.95, 0.98} | `prior_decay` | **CONFIRMED synonym.** Weight of a game *k* weeks old = `ρ^k`. |
| ridge λ (relative) | {0.5, 1, 2} | `n0 = λ · n0_base` | **CONFIRMED.** **`n0_base = 4.0`** (CFB `DEFAULT_PRIOR_N0` analogue; game-equivalents). Then `n0 ∈ {2.0, 4.0, 8.0}`. Manifest must hash `n0_base` before any run (H2). |
| ρ_s offseason regression | {0.50, 0.67, 0.80} | `offseason_shrink` | **CONFIRMED knob name.** Week-1 prior = `ρ_s ·` prior-season posterior, league-centered. In the frozen grid (not optional). |
| HFA mode | {fold-fit scalar, off}; neutral=0 | output-layer HFA | **CONFIRMED.** Rating-model **`h` stays internal** (ridge HFA on EPA/play `y`; neutral `home=0`). **`h` is NOT the output HFA.** Output HFA = OLS fold term **or 0**. Do not add `h` into `margin_A`. β OLS is intercept-free when HFA = off. |

3×3×3×2 = 54 configs max. β not on grid (fitted). Selection = inner-CV MAE vs **actual** margin, ≤2022 only. Tie-break as addendum §5 (HFA off preferred, then mid values ρ=0.95, λ=1, ρ_s=0.67). Cursor does not reopen the CoS LOOK on tie-break vs SPEC §4; that is IMV’s re-grade note, not an eng pin change.

---

## Rejected / superseded (echo)

- v1 §2.4 **option 1** (no β / emergent locked slope ~12): **REJECTED** (fails H2).
- v1 §2.4 **option 2** (β_epa into `simulate_nfl_game`): **SUPERSEDED** by linear `margin_A`.
- Kalman: **CLOSED** this pre-reg.
- `simulate_nfl_game` scored path: **rejected** (addendum §4).

---

## What this ACK does not do

- Does not run Exp E or Exp A.
- Does not claim H1/H3 closed.
- Does not change ddffb72e §4 stop (c>0, OLS HC1, B=10000 seed 4141, Δ ≥ 0.10, binding ≤2022 OOF, 2023 cannot alone PASS, VOID).
- Does not merge #648/#647/#646. F2 frozen. CERT=0.

NFL NO-GO · CERT=0 · F2 frozen
