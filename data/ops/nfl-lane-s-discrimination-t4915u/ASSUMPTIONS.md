# ASSUMPTIONS — t4915u Lane S EXEC

Label: **DEV_RESEARCH / RETRO_FIT exploratory**. CERT=0. NFL NO-GO.
These 70 games were already examined. Findings are not fresh validation.
No weight, cutoff, or feature was selected to maximize performance on this sample.

## Pins (verified this EXEC)

| Item | Value |
|---|---|
| Control tip | `02197f58` (untouched) |
| SCORE_RESULTS sha256 | `2b9f302e097183ef…` (sha8 **2b9f302e**) |
| SAMPLE_MANIFEST_70 sha8 | `861a6264` |
| EXEC_FREEZE Amend-1 sha256 | `29dc400571da4f7bfdd7f99b195324d8e71042a7c133ce831cd929f6e3ac53fc` |
| OWNER_ACCEPT sha256 | `dd4a2390a96568ab223fbc24031e4630d3f1607cccdc7bc38c0f5ec5481518c8` |
| Proposal | `44e3451f` |
| IF tip (from SCORE_RESULTS) | `6ca03716fe52930332d5ffba302c312a651980cc` |
| W2 RECON attached | sha256 `708513db…` (tip `440314e4`) |
| W3–W6 RECON attached | sha256 `cdff0115…` (tip `f92aaea3`) |
| Contract (cited, not re-opened) | `b41f4b43` |

## Sample

Exactly the 70 `game_id`s in SCORE_RESULTS (W2=14, W3=16, W4=16, W5=14, W6=10).
Manifest `selection_hash` recomputed and matched.
W3–W6 RECON matrix also contains four bye-partial games (`2017_06_DET_NO`, `2017_06_MIA_ATL`, `2017_06_NYG_DEN`, `2017_06_SF_WAS`). Those are **not** in the 70 and were **not** added.

## Outcome orientation (home-positive)

- `realized_margin = home_score - away_score` (SCORE_RESULTS; verified equal on all 70).
- `realized_su = 1` if margin>0, `0` if margin<0, `TIE` if margin==0.
- Ties excluded from SU rates; `n_ties` reported. This EXEC: **n_ties = 0**.
- `forecast_margin` is the sealed IF home-positive mean (association-to-IF only).

## MISSING rules (no impute)

A component is MISSING if any of:

1. Field absent from the joined wide RECON row.
2. RECON `status` ≠ `DERIVED_PREGAME`.
3. `reconstructed_value` empty or non-finite.
4. W-L denom `wins+losses == 0` (ties ignored in denom).

A derived signal is MISSING if any operand is MISSING.
Games with any signal MISSING are listed; they are dropped from that signal’s comparisons only.
This EXEC: **no game had any signal MISSING**. `n_complete = 70` for every frozen signal.

## Signal formulas (frozen; home-positive)

W-L from SCORE_RESULTS `record_asof_*` parsed as `W-L` or `W-L-T`:

- `wl_home_wpct = wins / (wins+losses)` (ties ignored).
- `wl_away_wpct` same for away.
- `wl_diff = wl_home_wpct - wl_away_wpct`.

Index diffs from sealed RECON `offense_index_*` / `defense_index_*`:

- `wl_index_off_diff = offense_index_home - offense_index_away`.
- `wl_index_def_diff = defense_index_away - defense_index_home` (freeze literal; labeled home-favorable).
- `wl_index_net = wl_index_off_diff + wl_index_def_diff`.

EPA / success (A1 **RETRO_FIT / DEV_RESEARCH only**):

- `epa_off_diff = home_off_epa_5g - away_off_epa_5g`.
- `epa_def_diff = away_def_epa_allowed_5g - home_def_epa_allowed_5g`.
- `epa_net_diff = epa_off_diff + epa_def_diff`.
- `success_off_diff = home_success_offense_5g - away_success_offense_5g`.
- `success_def_diff = away_success_defense_allowed_5g - home_success_defense_allowed_5g`.
- `success_net_diff = success_off_diff + success_def_diff`.
- `matchup_diff_off_epa_5g` and `matchup_diff_success_rate_5g` taken **as sealed** in RECON (not recomputed). On this sample they match `epa_off_diff` and `success_net_diff / 2` to float noise (ranks identical).

Forbidden: new composites, opponent-adjust, or weight search on this sample.

## Comparisons (all reported)

Seeds / constants:

- Bootstrap: paired index resample, **B = 2000**, `numpy.random.RandomState(4915)` (MT19937).
- CI: percentile 2.5 / 97.5 of defined resamples (`numpy.percentile`, `method="linear"`).
- Spearman: Pearson of 1-based **average** ranks (ties share mid-rank).
- Pearson: mean-centered cosine.
- Undefined if `n<2` or a side has zero variance (resample skipped; count reported).
- Wilson 95%: \(z = \Phi^{-1}(0.975) = 1.959963984540054\).
- SU split: home-win rate when `signal>0` vs `signal<0`; exclude `signal==0` and margin ties.
- Tertiles: average rank; T1 if `rank <= n/3`; T2 if `rank <= 2n/3`; else T3. **No optimized cutoffs.** Ties can make tertile counts uneven (W-L is discrete).
- OLS: `realized_margin ~ 1 + signal`. Slope/intercept SE from residual \(\hat\sigma^2/(n-2)\). 95% CI uses \(t_{n-2,0.975}\).
- \(t\) quantile: Acklam inverse-normal + Cornish–Fisher in `df` (documented; not a scipy install). For `n=70`, `df=68`, \(t_{0.975}\approx 1.99547\).
- Week-stratified: Spearman + SU sign split on weeks 2,3,4,5,6 separately.
- Leave-one-week-out: Spearman on the 70 minus that week; report min/max/range.
- Association-to-IF: Spearman(signal, `forecast_margin`) only — **not a retune**.

Control IF (`forecast_margin` vs `realized_margin`) is reported as a known comparator, not as a searched signal.

## Software

- Python 3 + numpy 1.26.4. No pandas/scipy/statsmodels. No model-service import.
- Runner: `run_lane_s_exec.py` (one EXEC).

## Labels

Every EPA/success claim in this packet is **RETRO_FIT / DEV_RESEARCH only (A1)**.
No predictive PASS, no betting PASS, no CERT, no publish.
