# Verified vs claimed

Expected answers `52879746` before harness `3f226966`.

## Verified

| item | evidence |
| --- | --- |
| T-PIT-1..10 PASS on synthetic 2098 | `leakage/receipts/SYNTHETIC.json` (`all_pass` true, 10/10) |
| DEV-COVERAGE PASS | `leakage/receipts/DEV-COVERAGE.json` |
| n_dev_games | 2863 REG keys 2013–2023 |
| n_reconstructible | **0** |
| n_ineligible | **2863** |
| W1 2019–23 week-label | ineligible (`INELIGIBLE_WEEK_LABEL`); packs not used as PIT |
| B2b 2024/25 W1 | **not opened** |
| holdout years read | `[]` |
| refit | **false** |
| lock written | **no** |
| scoring-rule delta | **none**; K-*/I-* unread and unchanged |
| season-level loader | HARD_STOP under `GPIT_MODE=1` (T-PIT-10 exit 2) |
| agent store path exists | `/cursor/stores/self/artifacts/week-aware-roster-step2-v1/` |

## Claimed (not production truth; not Step 3/4)

| item | status |
| --- | --- |
| Week-aware roster SoT pin | **not claimed** — no source selected |
| Reconstructible=0 | coverage fact (NR-1 / missing capture-time weekly archive), not a model score |
| C-1 fit/export (`6a5490db`, `a38a55bb`) | SUPERSEDED; not re-certified |
| Closed-at-cutoff | **false**; `==` remains ineligible until Ryan/IMV freeze otherwise |
| Opening / lock / holdout | **not claimed**; sealed |
| Step 4 refit | **not started** |
| Odds API / spend | ON HOLD; NR-1 still Needs-Ryan |
