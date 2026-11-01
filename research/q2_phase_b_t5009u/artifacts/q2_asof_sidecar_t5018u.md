# t5018u — Q2AsOfSidecar offline artifacts (DEV_RESEARCH)

**CERT=0 · NFL NO-GO · research-consumed only · do not merge/deploy/pub/bet.**

Passive annotation beside Independent Fair. Not a forecast join.
Contract: `Q2_ASOF_SIDECAR_FIELD_CONTRACT_t5015u.md` (§3–§7, §9, A1–A2).

## Pins

- games `4fe1cdd7` (require `4fe1cdd7`)
- outcomes `50bda875` (require `50bda875`)
- fit `70db070d` (require `70db070d`)
- config `aa2b47b3` (require `aa2b47b3`)
- as-of `cf514078` (require `cf514078`)
- frozen md `28c582a1` (require `28c582a1`)
- λ=20.0 r=0.5 a_q2=2.5637441292077354 b_q2=1.660624056183471

## Isolation

No writes to `offense_index_*` / `defense_index_*` / L0 `off_eff_*` /
`independent_fair.margin_mu` / `L0.market_blend`. No `simulate_nfl_game*`.

## Counts

- history games: 267
- window targets: 16
- emitted rows: 16
- refused rows: 0

## Emitted (identity + q2_pm_new)

- `2013_02_NYJ_NE` NYJ@NE W2 2013 pm_new=2.6204 n_asof=16
- `2013_02_CAR_BUF` CAR@BUF W2 2013 pm_new=2.8001 n_asof=17
- `2013_02_CLE_BAL` CLE@BAL W2 2013 pm_new=1.8953 n_asof=17
- `2013_02_DAL_KC` DAL@KC W2 2013 pm_new=4.1597 n_asof=17
- `2013_02_MIA_IND` MIA@IND W2 2013 pm_new=1.8735 n_asof=17
- `2013_02_MIN_CHI` MIN@CHI W2 2013 pm_new=3.5342 n_asof=17
- `2013_02_SD_PHI` SD@PHI W2 2013 pm_new=3.2539 n_asof=17
- `2013_02_STL_ATL` STL@ATL W2 2013 pm_new=1.8953 n_asof=17
- `2013_02_TEN_HOU` TEN@HOU W2 2013 pm_new=2.2618 n_asof=17
- `2013_02_WAS_GB` WSH@GB W2 2013 pm_new=2.5746 n_asof=17
- `2013_02_DET_ARI` DET@ARI W2 2013 pm_new=1.7775 n_asof=26
- `2013_02_NO_TB` NO@TB W2 2013 pm_new=2.2287 n_asof=26
- `2013_02_DEN_NYG` DEN@NYG W2 2013 pm_new=0.7243 n_asof=28
- `2013_02_JAX_OAK` JAX@OAK W2 2013 pm_new=4.4296 n_asof=28
- `2013_02_SF_SEA` SF@SEA W2 2013 pm_new=2.5905 n_asof=30
- `2013_02_PIT_CIN` PIT@CIN W2 2013 pm_new=3.1615 n_asof=31

## Holds

No second EVAL · no Stage C · no 2024–25 · no `1ee90fac` scored columns · CERT=0.
