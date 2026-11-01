# t5018u — Q2AsOfSidecar offline artifact writer

**Label:** DEV_RESEARCH · CERT=0 · NFL NO-GO · research-consumed only · DRAFT  
**Mode:** offline annotation writer. **Do not merge · do not deploy · do not join forecasts · no EVAL · no retune.**

## Authority

- OWNER CLEAR tip `1e71808d` — `OWNER_WIRING_CARD_t5015u_Q2_SIDECAR` offline artifact writer only.
- Contract: accepted #681 paper `Q2_ASOF_SIDECAR_FIELD_CONTRACT_t5015u.md` (head `e30e6f9c`; CoS ACCEPT tip `fc03a463`).
- Frozen inputs: #679 / FROZEN `28c582a1` · fit `70db070d` · config `aa2b47b3` · games `4fe1cdd7` · outcomes `50bda875` · as-of `cf514078` · keep commit `af6be4f5`.

This writer implements contract **§3–§7, §9, appendix A1–A2** as a **passive file emitter**. It does **not** EXEC Layer-3 wiring, IF caller wiring, or ledger capture.

## What it writes

`emit_q2_asof_sidecar.py` → `artifacts/q2_asof_sidecar_t5018u.{json,csv,md}`

Fields: game identity (`game_id` + `Game.key`) + `q2_home_s` / `q2_away_s` / `q2_rating_diff` / `q2_hfa` / `q2_n_asof_games` + `q2_asof_wl_diff` + `q2_pm_new` (sealed `2.56374413 + 1.66062406 · rating_diff`) + pin shas.

Default window: **2013 REG W2** (bounded DEV demo). `--seasons` / `--weeks` may expand inside 2013–2022 REG W2–17. 2023+ and 2024–25 are refused.

## Reuse only

`asof_for_targets` · `asof_wl_diff` · `assert_asof_leakage` · `load_games` / `verify_games_pin` / `load_outcomes_score_only` · sealed λ=20, r=0.5, `a_q2`/`b_q2`. Incoming priors = FROZEN `season_end_ratings` (no hyperparameter re-grid).

## Isolation

Does not write `offense_index_*` / `defense_index_*` / L0 `off_eff_*` / `independent_fair.margin_mu` / `L0.market_blend`. Does not import or call `simulate_nfl_game` / `simulate_nfl_game_independent_fair` / `run_nfl_market_simulations`. Does not open hist index `1ee90fac`.

## Holds

No second EVAL · no Stage C · no S1 · no 2024–25 · no production promote · CERT=0 · pub/bet HOLD.

## Reproduce

```bash
python3 research/q2_phase_b_t5009u/tests/test_q2pb_guards.py -v
python3 research/q2_phase_b_t5009u/tests/test_q2_asof_sidecar_writer.py -v
python3 research/q2_phase_b_t5009u/emit_q2_asof_sidecar.py --seasons 2013 --weeks 2
```
