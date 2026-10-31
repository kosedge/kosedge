# ALEX_IF_COHERENCE_SPEC_CLARIFICATION_t4871u_v1 — #4 acceptance-rubric FREEZE (overlay)
OWNER CLEAR Card A t4871u (OWNER_CLEAR_t4871u_CARD_A_COHERENCE_ENG.md) · Alex Rourke · filed 2026-10-30 EDT
**Parent (unedited):** ALEX_IF_ONLY_COHERENCE_PAPER_t4862u_v2.md sha256 05222939cc37086f0544063df3a6b66a1238cbc4bf92d7a0b88b2522718f0d3a (recomputed MATCH)
**Verdict: SPEC_CLARIFICATION_FILED · eng NOT started by Alex · #4 NOT CLAIMED PASS** · EVAL_ONLY

## 0. Precedence
This file overlays v2 §§3, 4, 6, 7 for eng acceptance. Where it conflicts with v2, **this file governs**. Everything not restated here stands as in v2. No forecast mathematics changed; no tolerance in v2 loosened except where v2 was internally contradictory (J7, J14 — resolved below, with reason). Tolerances are frozen by this seal; changing any after a run to obtain PASS is prohibited (any change = new paper + CoS ACCEPT before any rerun).

## 1. Garble / ambiguity fixes
**What was garbled:** in v2 §4 the J10 and J11 rows contained literal `|` (in `|ρ|` and `|spread|`) which broke the markdown table, splitting tolerance and class text into wrong columns. J7 had overlapping bands (PASS ≤3SE but COND >2SE; nothing defined 3–4SE). J9/J12 had no class. J14 ("omission ≠ PASS") conflicted with §6 CONDITIONAL-on-omission.

Notation: N = draws; D*=H*−A*, S*=H*+A* from the **one** captured draw array; SE_D = sd(D*)/√N (empirical, not hardcoded 0.224); SE_p = √(p̂(1−p̂)/N); z = |observed − expected| / SE.

**J10 (restored, complete):** Independence. Compute ρ̂ = corr(H*, A*). PASS if abs(ρ̂) ≤ 0.05. COND if 0.05 < abs(ρ̂) ≤ 0.10. FAIL if abs(ρ̂) > 0.10. The current IF draws H and A independently (ρ=0 by construction); if a future IF introduces a stated correlation ρ₀, J8/J9 expectations must use ρ₀ and J10 tests abs(ρ̂−ρ₀) on the same bands. Class: sampling-sensitive (§3B).

**J11 (restored, complete):** Sign coherence, same draws. Let m = mean(D*) (= −spread_home) and p̂ = home_wp. Decisive zone: abs(m) ≥ max(0.25, 2·SE_D) AND abs(p̂−0.5) ≥ 2·SE_p. In the decisive zone, sign(m) must equal sign(p̂−0.5): agreement → PASS; disagreement → FAIL (BLOCK). Outside the decisive zone (pick'em, e.g. ATL@TB) → recorded NOT_DECISIVE = COND-neutral (does not fail, does not by itself block PASS; listed per game). Class: sampling-sensitive.

**J7 (mutually exclusive bands):** expected E[D] = E[max(0,X_h)] − E[max(0,X_a)], X~N(μ,σ) using **captured pre-clamp** μ_h, μ_a, σ (§2). z = abs(mean(D*) − E[D]) / SE_D. **PASS z ≤ 2 · COND 2 < z ≤ 4 · FAIL z > 4.** Same exclusive scheme for J2-analogue on S (E[S] sum of truncated means). (v2 "≤3SE PASS" was tighter-and-looser simultaneously; the 2/4 split is the only reading consistent with v2's COND>2SE and FAIL>4SE clauses; no band moved outward beyond what v2 already stated.)

**J8:** rel = abs(sd(D*) − √(Var_h^tr+Var_a^tr)) / expected. PASS ≤3% · COND 3–8% (exclusive: 3% < rel ≤ 8%) · FAIL >8%.
**J9:** abs(p̂ − P_model(D>0)) where P_model computed from captured params (exact truncated convolution or MC with N≥10⁶ fixed seed; normal approx only if P(clamp)<2% per side). PASS ≤ 2·SE_p · COND 2·SE_p < Δ ≤ 0.03 · FAIL > 0.03. If 2·SE_p > 0.03 (not at N=4000), use 4·SE_p as FAIL bound.
**J12:** pairs (i,j) counted as inversions only if margin and wp order disagree AND abs(m_i − m_j) > max(0.5, 2·√(SE_Di²+SE_Dj²)) → any such inversion FAIL. Kendall τ over all games: PASS ≥0.95; COND <0.95 when every inversion is within noise; never FAIL on noise-level inversions.

## 1b. J14 — ONE rule for omitted ATS/OU
**Chosen rule: scope-limited PASS, never silent.** If the packet emits no ATS-cover / OU-over / push probability, J14 = `NOT_APPLICABLE_NOT_EMITTED` and does **not** by itself make #4 CONDITIONAL, **provided** (a) test_no_ats_ou_emitted asserts every ATS/OU/push field across RESULTS/outputs is absent or null (proof, not assumption), and (b) the verdict string carries the scope label: `PASS_RO(#4 IF-only; scope: spread/total/wp/ML; ATS/OU NOT EMITTED, NOT TESTED)`. If any ATS/OU value is emitted anywhere, J14 becomes BLOCK-class: P(D>−line), P(S>line), P(push at integer lines) recomputed from the same draws within 1e-4, else FAIL. Missing proof (a) → BLOCKED (omission ≠ PASS). This supersedes v2 §6 "CONDITIONAL … J14 untested by omission"; rationale: there is no emitted quantity whose coherence could fail, and the label prevents the PASS being read as covering ATS/OU.

## 2. Actual pre-clamp generating parameters (required capture)
Per game, the eng run must capture **from the IF call itself** (instrumented at the gauss() call site, no math change): μ_h, μ_a (pre-clamp), σ (per-team SD as passed), seed, N, RNG identity/version, draw-order note, n_clamped_h, n_clamped_a, and sha256 of the raw (H,A) draw array (float64, little-endian, documented layout). J7/J8/J9 expectations use only these captured values. **Alex v2 §5 reconstructed means (μ=(T±M)/2, post-clamp) are exploratory evidence only and are NOT acceptance inputs**; any run using them for J7–J9 is BLOCKED for that rule.

## 3. Deterministic vs sampling-sensitive split
**A. Deterministic identities (same draw array, exact/float tolerance, no SE): J1, J2, J3, J4, J5, J6, J13, J14(if emitted), tie-count identity (n_home+n_away_strict+n_tie = N).** Any miss = FAIL/BLOCK — a formula/plumbing defect, not noise.
**B. Sampling-sensitive (compare draws to a model expectation; SE-banded): J7, J8, J9, J10, J11, J12, tie-rate band.** Finite-N treatment frozen now: bands as §1 using empirical SE at the run's own N; N and seeds fixed in the run config before execution and recorded; **no reseeding, no N change, no rerun-until-pass**. A B-class COND is reported as sampling noise, never as formula defect; a B-class FAIL (z>4 or stated FAIL bound) requires a diagnosis note and may not be "fixed" by retuning. Optional confirmatory high-N run (e.g. N=200k, pre-declared seed) may be attached as evidence for a COND but does not replace the packet run.

## 4. Ties — engine conventions, not NFL truth
- Continuous scores ⇒ D==0 only at 0–0 clamp; P(tie) ≈ 1e-4. Ties→away is an **engine convention**. It is NOT a validated NFL tie probability (real NFL ties after OT are rare but nonzero and arise from integer scoring/OT rules not modeled) and NOT a universal market settlement rule (2-way ML books commonly void/push ties; 3-way markets price ties separately).
- Tests MUST emit separately per game: **p_home_win = #(D>0)/N, p_away_win_strict = #(D<0)/N, p_tie = #(D==0)/N**, plus engine-reported home_wp/away_wp, and assert home_wp = p_home_win and away_wp = p_away_win_strict + p_tie.
- Effect on fair ML: ML derived from home_wp; tie mass shifts away_wp by p_tie ⇒ ≤3e-4 on W8 ⇒ ≤1 integer ML step. Report the alternate tie-excluded p̃ = p_home/(p_home+p_away_strict) and resulting ML as **information only** (no rule change).
- Tie-rate bands (v2, unchanged, exclusive): PASS p_tie ≤ 1e-3 · COND 1e-3 < p_tie ≤ 5e-3 · FAIL > 5e-3 (signals integer rounding; requires new CLEAR for a push rule).
- Limitations: coherence PASS says nothing about tie realism or settlement; the fair ML is a 2-way engine price under this convention only.

## 5. Preserved (not weakened)
Same-draw requirement (all of wp/spread/total/ML/ties from one array, hash-bound) · independent Alex RO after Cursor seal · no model math change (any correction = separate proposal) · no tolerance tuning to obtain PASS · PASS = IF-only internal consistency only (≠calibration ≠accuracy ≠market ≠enterprise readiness).

## 6. Acceptance contract for Cursor eng (must emit / prove)
- [ ] Pins: execution tip == INVOKE HEAD; code sha of nfl_simulator.py at tip; config + input data sha256; run_id; command line; SHA256SUMS.
- [ ] Per game §2 capture: μ_h, μ_a, σ, seed, N, RNG id, n_clamped, draw-array sha256 (+ draw artifact or reproducible regen).
- [ ] Per game: mean_H, mean_A, sd_D, sd_S, corr_HA, p_home_win, p_away_win_strict, p_tie, home_wp, away_wp, spread, total, ML_h, ML_a, SE_D, SE_p.
- [ ] Table A (J1–J6, J13, tie identity, J14 if emitted): value, recompute, Δ, PASS/FAIL.
- [ ] Table B (J7–J12, tie band): observed, expected, SE, z, band — PASS/COND/FAIL per §1 exclusive bands; J11 NOT_DECISIVE listed.
- [ ] Tests v2 §7 #1–25 present and green, plus: test_emit_win_away_tie_separately, test_preclamp_params_captured (fail if absent or derived from post-clamp means), test_no_ats_ou_emitted (§1b), test_bands_exclusive (boundary fixtures at z=2, z=4).
- [ ] Negative fixtures: second-seed wp injection → FAIL; integer-rounded scores → tie FAIL; market field present → nonzero exit.
- [ ] Frozen-config attestation: N, seeds, tolerances = this file's sha; no rerun-to-pass log.
- [ ] Holds: blend=0, market fields null, public_delivery=false, zero Odds/C10 calls.
**Packet verdict mapping:** PASS_RO = all A PASS + all B PASS (J11 NOT_DECISIVE allowed) + contract complete, with scope label. CONDITIONAL = all A PASS, ≥1 B in COND, contract complete. BLOCKED = any A FAIL, any B FAIL, any contract item missing, reconstructed means used, or different draw sets.

## 7. Non-claims / bounds
#4 NOT CLAIMED PASS · eng NOT started by Alex · no Odds, no market prices · omission ≠ PASS · ≠FREE_PUBLIC ≠betting ≠Odds ≠merge ≠E1 ≠CERT · NFL NO-GO · CERT=0. v2 paper and OWNER CLEAR file untouched.
