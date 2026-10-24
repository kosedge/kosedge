# B-1 / B-4 / B-6 / B-8a / B-13 contract (`4fd6cfbe`) — expected before the runner

Quoted remaining defects. Accepted items (B-2, B-3 code, B-5, B-7, B-9,
B-10) stay as in v3. B-12 is a scope change: scorer v6.2 is DRAFT
PENDING_RYAN; the runner stays on `ca98ae0e` until the Ryan decision file
exists.

## B-1

Production `main()` must run `run_holdout_workspace`: pins → B-13 inputs
→ lock → chain → week-1 → consumed → receipt. Post-lock handler catches
`BaseException`. Week-1 identity before receipt 0444. Does not rewrite
0444.

## B-4

Deltas from `holdout_delta_producer.py` (`43d80936`): `apply_params` +
`6a5490db` selected_params + `ff8e6527`. `QB1_INDEX_UNITS = 0.12` from
fit floor/ppu (equals HEAD `8e2a15ac` injury_paths). Extra player keys
refused. `as_of <= kickoff` on ok rows. `games.json` raw deltas forbidden.

## B-6

Receipt: computed `opening_permitted` / `holdout_years_opened`; I-1;
scorer holm list only (no runner `p*(9-rank+1)`); K-2; 0444; top-level
runner/scorer sha. RECEIPT_MANIFEST after receipt 0444 and not rewritten
into the receipt. SUMS = MANIFEST lines + MANIFEST hash. Both 0444.

## B-8a

Exactly one anchored `^VERDICT: (PASS|RETURN|PASS WITH CONDITIONS|FAIL)$`
equal to `VERDICT: PASS`, plus `RUNNER_SHA: <64hex>` equal to
`runner_sha()`. Sidecar `.abs.sha256` + 0444. Exact IMV dir. Not a
substring test. No `REQUIRED_OPENING_PASS`. Do not read `seeded/`.

## B-13

Production paths (audit dir):
`/workspace/ops/nfl_injury_audit_t4274u/{games.json,close.csv,schedule.csv,listings/}`.
Pre-lock existence, headers, no-open size. Missing file STOPs before lock.

## B-12 (not switched)

v6.2 draft `1129354a` for IMV diff review only. Active pin `ca98ae0e`
until `/workspace/fg-repair/imv-gate1-review-2026-10-02/DECISION_RYAN_SCORER_V6_2.txt`.
