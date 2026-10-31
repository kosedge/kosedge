# ALEX PROTOCOL t4921u — #4 R1 Bounded Confirmation (v1)
Date: 2026-10-31 · Author: Alex Rourke (RO) · Status: FROZEN ON SEAL · NFL NO-GO · CERT=0 · pub/bet HOLD

## 1. Purpose
Predeclare, before any run, a single evidence-only confirmatory high-N addendum to settle the remaining #4 R1 sampling condition (memo 9b064689, option 2). It does NOT replace, reseed, or re-grade the sealed N=4000 Card A claim packet.

## 2. Authority / lineage (verified on box 2026-10-31)
- CoS ORDER: COS_ORDER_ALEX_t4921u_HASH4_R1_PROTOCOL.md
- OWNER: OWNER_DIRECTION_t4921u_PROCEED_STAGE_B_AND_R1.md — pursue predeclared bounded confirmation; no waiver / tolerance shopping / reseed-to-PASS
- Memo OWNER_RESULT_t4899u_HASH4_REMAINING_CONDITIONS.md sha256 9b064689ce45fd7fc5733e40a978fe3dfe1cb001ef4f22a58a0eb4cf7690df2e (verified)
- SPEC ALEX_IF_COHERENCE_SPEC_CLARIFICATION_t4871u_v1.md sha256 fe4dc220d208fe6312cb32c7e441c49448d6e3b11c40639d919f47b5aedbea95 (verified; bands govern; §3 permits optional pre-declared confirmatory high-N as COND evidence)
- Parent Card A sealed: tip aa9605dc · packet-seal 1f4ffde3 · Alex RO b5de5df1 · N=4000 · seeds 48500–48512 · J9 MC n=1e6 seed 48711001 · no_rerun_until_pass=true — UNCHANGED
- Soft C2/C3 CLOSED: tip 9e370050 / Alex b0b0c04c — out of scope
- Baseline IF tip 6ca03716 · SOURCE pin 52d9e909 unedited · market_blend=0
- Parent mirror eval_w8_t4871u_coherence/: GAMES.json c73a9c0c2901070cf6dca8ea24bd2285aa243b3419757939996bf78a5c0b97ca · RESULTS.json e1c40da2bf7dbc50156ad78f577108a54779d315b3ac923ab5f6a7479dcbc0e1 · FROZEN_CONFIG.json 7efc08ef2df860180054d4252ec9d91f3572c955d04912dd7fc38c26b8c52ea7

Register preflight: EXISTING AND VERIFIED — SPEC fe4dc220; Card A aa9605dc / RO b5de5df1; memo 9b064689; soft 9e370050 CLOSED; SOURCE 52d9e909. MISSING before this filing — confirmatory protocol (this file). SUPERSEDED — none for bands.

## 3. R1 open checks (only these gate #4)
| Check | Game | Sealed (N=4000) |
|---|---|---|
| J7_S | 2026-W08-CLE@PIT | z=3.708 COND |
| J7_S | 2026-W08-MIN@DET | z=2.114 COND |
| J7 | 2026-W08-LAC@LAR | z=2.423 COND |
| J9 | 2026-W08-LAC@LAR | Δp=0.0170 · z=2.24 SE_p COND |

## 4. Frozen confirmatory config (no change after seeing results)
- Games: same 13 SUPPORTED games, sealed GAMES.json order; TNF CAR@GB excluded. Same A/B class split.
- N_confirm = 200_000 draws per game (chosen once).
- Seeds: game i uses 49210000 + i (disjoint from claim 48500–48512). Binding read from GAMES.json:

| i | game_id | parent seed | confirm seed | μ_h | μ_a | σ | sealed P_model |
|---|---|---|---|---|---|---|---|
| 0 | 2026-W08-ARI@DAL | 48500 | 49210000 | 24.4164 | 22.1823 | 10.0068 | 0.562779 |
| 1 | 2026-W08-ATL@TB | 48501 | 49210001 | 22.0501 | 22.1316 | 10.0068 | 0.497723 |
| 2 | 2026-W08-BAL@BUF | 48502 | 49210002 | 24.4012 | 21.7338 | 10.0068 | 0.574893 |
| 3 | 2026-W08-CLE@PIT | 48503 | 49210003 | 23.2178 | 22.1531 | 10.0068 | 0.530091 |
| 4 | 2026-W08-IND@JAX | 48504 | 49210004 | 24.2718 | 20.4837 | 10.0068 | 0.605912 |
| 5 | 2026-W08-LV@NYJ | 48505 | 49210005 | 23.4802 | 23.2237 | 10.0068 | 0.507405 |
| 6 | 2026-W08-MIN@DET | 48506 | 49210006 | 21.9439 | 23.1782 | 10.0068 | 0.465181 |
| 7 | 2026-W08-TEN@CIN | 48507 | 49210007 | 24.912 | 20.6344 | 10.0068 | 0.619327 |
| 8 | 2026-W08-LAC@LAR | 48508 | 49210008 | 24.4288 | 19.72 | 10.0068 | 0.630801 |
| 9 | 2026-W08-KC@DEN | 48509 | 49210009 | 22.6093 | 22.3016 | 10.0068 | 0.508796 |
| 10 | 2026-W08-NE@MIA | 48510 | 49210010 | 22.0768 | 24.2344 | 10.0068 | 0.439328 |
| 11 | 2026-W08-PHI@WAS | 48511 | 49210011 | 23.2701 | 22.223 | 10.0068 | 0.529626 |
| 12 | 2026-W08-CHI@SEA | 48512 | 49210012 | 21.7865 | 21.9481 | 10.0068 | 0.495447 |

- Generating params: sealed captured PRE-clamp μ_h, μ_a, σ (capture.mu_h/mu_a/sigma above). Reconstructed post-clamp means are FORBIDDEN as inputs.
- Draws: rng = random.Random(seed); per sim: raw_h = rng.gauss(μ_h, σ) then raw_a = rng.gauss(μ_a, σ); H=max(0,raw_h), A=max(0,raw_a). Same draw order/layout as parent (interleaved float64 LE [H0,A0,...]); emit draw_array_sha256 per game.
- RNG: CPython 3.x random.Random; record exact sys.version in packet. Parent used CPython 3.12.3; box default is 3.13.5 — either is acceptable (gauss algorithm unchanged) but the version used MUST be recorded and, preferably, 3.12.3 used for lineage parity.
- J9 model probability: REUSE sealed P_model_home_win from parent GAMES/RESULTS (same captured μ/σ ⇒ same target); no regen of P_model. If eng nonetheless regenerates, it must use exact truncated convolution or MC N≥1e6 seed 49211999 (never 48711001), report both, and the sealed value governs the band.
- Bands (verbatim SPEC fe4dc220; not loosened):
  - J7 / J7_S: z = |mean(D*) − E[D]| / SE_D, SE_D = sd(D*)/√N_confirm. PASS z≤2 · COND 2<z≤4 · FAIL z>4.
  - J9: Δ = |p̂_home − P_model|, SE_p at N_confirm. PASS Δ≤2·SE_p · COND 2·SE_p<Δ≤0.03 · FAIL Δ>0.03. (At N=200k, 2·SE_p≈0.0022 for p≈0.63.)
- no_rerun_until_pass = true: ONE shot. Result stands. No second N, seed, or partial re-run.
- Forbidden: changing N/seeds/bands/params post-hoc; reseeding/editing the sealed claim; tolerance shopping; Odds API; 2024–25 data; math/blend/SOURCE changes; any calibration/market/enterprise/betting claim.

## 5. Rubric (R1 → #4). Full Table B emitted for audit; only the four R1 checks gate.
- R1_PASS: all four in PASS band; zero A-class FAIL on any re-emitted identity checks; parent packet digests unchanged; scope label "ATS/OU NOT EMITTED" preserved. → Alex RO → CoS may ACCEPT #4 PASS as IF-only internal consistency.
- R1_CONDITIONAL: ≥1 of four in COND; zero FAIL. #4 stays CONDITIONAL. No second try.
- R1_FAIL: any of four in FAIL band, OR any A-class FAIL, OR param/tip/SOURCE mutation, OR reconstructed means used. #4 cannot PASS on this route; diagnosis required; not fixable by retune/reseed.
- BLOCKED: eng incomplete (missing capture, wrong tip, contract incomplete). Not a sampling grade.
- J11 (R2, NOT_DECISIVE): not required for R1. If decisive at N_confirm and disagreeing → A/B FAIL under J11, blocks. If still NOT_DECISIVE → allowed for #4 PASS per SPEC.
- Soft C2/C3: CLOSED, out of scope.

## 6. What #4 PASS would / would not mean
Would: IF-only engine internal sampling consistency at W8 for these 13 games. Would NOT: calibration, forecast skill, market edge, ATS/OU validity, enterprise readiness, CERT, merge, publication, or betting. (Diagnostic closure already graded forecast quality UNFAVORABLE.)

## 7. Authority statement
(b) Needs CLEAR / CoS dispatch of EXEC card. OWNER t4921u authorized pursuing the route and finalizing this protocol; Cursor EXEC of the confirmatory is NOT within Alex standing authority to self-run. EXEC_CARD_t4921u goes to CoS. After eng seals the addendum, Alex RO under standing RO authority. CoS ACCEPT of #4 PASS (if R1_PASS) is the gate; ≠merge ≠pub ≠bet ≠CERT.

## 8. Non-claims / soft notes
No run executed for this filing. No sealed artifact touched. Seed range 49210000–49210012 and 49211999 checked disjoint from 48500–48512 / 48711001. Python-version note in §4 is a lineage caveat, not a band change.
