# B-1..B-10 contract (`77d9c00a`) — expected before the runner

Quoted defects. Implemented in the v3 runner after this filing.

## B-1

Production `main()` must run `run_holdout_workspace`: pins → lock → chain →
consumed → receipt. Never `write_lock` before `assert_pins_before_lock`.

## B-2

2024/25 allowance = `lock_is_production` AND verified PASS. Fixture marker
cannot admit 2024/25. Fixtures use 2098/2099.

## B-3

Fold years from request v3.1 parse `season ∈ {2024, 2025}`. Not 2022/2023
literals. `dry_run_label` True for fixtures; False only production+PASS.

## B-4

Deltas from `holdout_delta_producer.py` (`57df9a50`): `apply_params` +
`6a5490db` selected_params + `ff8e6527`. Pin in expected answers and lock.
`games.json` raw deltas forbidden.

## B-5

`record_hfa_baseline_method.py` sha `76aac887` asserted vs expected answers
**before import**.

## B-6

Receipt: computed `opening_permitted` / `holdout_years_opened`; I-1; 9 Holm
p-values; K-2; 0444; top-level runner/scorer sha; receipt MANIFEST/SUMS.

## B-7

Synthetic holdout-season post-lock E2E on 2098/2099.

## B-8

Read `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_vN.txt`.
Sidecar `.abs.sha256` + 0444 + `VERDICT: PASS` + `runner_sha()`. No
`REQUIRED_OPENING_PASS`. Do not read PASS from `seeded/`.

## B-9

Decimal `ROUND_HALF_UP`. Method-vs-CSV on le2023. 2015 wk12 DAL-CAR
45.3563. Tolerance 1e-4 vs `502110cf`.

## B-10

Path 1 holdout export = producer + `timestamps_for_game` +
`write_sidecar_chain`. `writer.main()` not invoked on holdout.
