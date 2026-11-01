# FROZEN_CONFIG_Q2PB_t5009u — DEV_RESEARCH

**CERT=0 · NFL NO-GO · DEV_RESEARCH · no merge/deploy/pub/bet**

Sealed **before** any EVAL 2018–22 row was read.

## Identity

- ORDER tip `dc78aa4e` · design `2702b295` · eval spec `349e081e`
- games.csv sha256 `4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8` (prefix `4fe1cdd7`)
- outcomes extract sha256 `50bda875daa8bf1aadd56dd0a3bc19f1bb52dafe42b6a9c921a5816c7d7dc081`
- as-of rule `cf514078` (kickoff < target)
- freeze timestamp (America/New_York): `2026-10-31T18:08:23.133346-04:00`
- fit object sha256: `70db070dad3fcdb4d4ff165ba09b7840c173c232a71c8fcd670ba9c3c0bc5571`
- config sha256: `aa2b47b3f0b504f39b785d0cb6fc2918bb7a36fb5a22242e80fb37707b790d49`

## Hyperparameters (DEV 2013–16 REG W2–17 only)

- λ = `20.0`
- regression fraction r = `0.5`
- selection: max DEV Spearman rho(rating_diff, m); tie-break min DEV MAE(pm_new,m)

## Comparator / Q2 maps (DEV OLS / logistic)

- WL_MARGIN: pm_WL = 2.77041980 + 10.71786351 · wl_diff
- WL_WP: σ(0.33704197 + 1.35467327 · wl_diff)
- Q2: pm_new = 2.56374413 + 1.66062406 · rating_diff
- Q2 WP: P_new = σ(-0.02025957 + 0.13753239 · pm_new)
- CONST_MARGIN = 2.53645833
- CONST_WP = 0.57217573

## Fit counts

- n_fit = 960
- n_ties_excluded = 4

## DEV screens (invention; not EVAL)

- Spearman ρ(rating_diff, m) = 0.375804
- MAE(pm_new, m) = 10.428761
- MAE(WL_MARGIN, m) = 10.771745
- MAE(CONST, m) = 11.188346
- residual ICC (home team-season) = 0.019518604602415775 (k=128.0, N=960.0, n0=7.499737532808399)

## wl_diff

- column in games.csv: `None` (absent; mapping not definition)
- definition: home current-season as-of win% minus away current-season as-of win%; win%=(W+0.5T)/(W+L+T); 0-0 → 0.5; as-of games have kickoff < target (cf514078). games.csv has no wl_diff column; record_entering_home/away is a W-L mapping cross-check only.
- Pearson(recomputed, record_entering mapping) = 0.9999326639435053

## EPA / PBP

- SKIPPED/UNAVAILABLE — no PBP 6ee24b44 on this VM; primary is margin strength
- S1/EPA-trail revive: not attempted (kill not loaded as experiment frame; score-only 2013-2022 extract only)

## Outcome join

OUTCOME_JOIN_ONLY: games.csv tip 4fe1cdd7 has identity/kickoff/records but no home_score/away_score. Public finals for 2013–2022 were copied from the six identity+score columns of the gated hist file (tip 1ee90fac) after dropping every model/trailing/EPA/error column and every 2023–2026 row. This is not scored reuse of the hist index (gate 83646d78); Alex RO must confirm. 2023 reserve and 2024–25 sealed rows were never copied.

## Early-stop flags (DEV)

- early_stop = False
- rho < 0.10 = False
- MAE_new ≥ MAE_WL = False
- eval_rows_read at seal = False

No self-ACCEPT of keep. Result returns via Alex RO → CoS.
