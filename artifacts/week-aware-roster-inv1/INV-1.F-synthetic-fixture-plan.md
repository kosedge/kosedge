# INV-1.F — synthetic fixture plan (T-PIT-1..10)

Plan only. No runner. No holdout data. Expected answers will be
committed **before** any future runner sha (Step 2). Years: 2098 / 2099.

Each case: input CSV/JSON + `expected.json` + fail-closed assertion.

## T-PIT-1 Future membership blocked

Player `00-SYN-JOIN` first eligible on AAA in week 10.
Game AAA week 3: not a member; no silent include; component
NULL/ineligible if the listing would have applied.

Season-snapshot control: a week-19 WC row for the same player must
not make them a week-3 member (B-4b(n)-PIT shape).

## T-PIT-2 Future starter blocked

Week 1–5: QBA depth_order=1, QBB=2.
Week 6: QBA injured (listing as_of < kickoff).
Week 7+: QBB depth_order=1.
Week 6 game must **not** see QBB as depth=1 from the later state.

## T-PIT-3 Trade as-of

`00-SYN-TRD` AAA weeks 1–7, BBB weeks 8–18.
`availability_ts` from the transaction row.
Pre-trade games: old team only. Post-trade: new team only.
If txn `availability_ts` is after week-8 kickoff, week 8 BBB is not yet
a member.

## T-PIT-4 Practice-squad promotion

DEV weeks 1–8. Promote ACT Tuesday 12:00 UTC before week-9 Sunday
kickoff → week 9 member. A fixture kickoff *before* that Tuesday →
week 9 still not promoted.

## T-PIT-5 Injury status separation

Season-level roster status `RES` on a week-17 snapshot must not mark
the player out at week 1. Injury out/in remains listing
`report_time < kickoff` only. Fixture: Ben-class end-of-year `RES`
vs week-1 listing `active`.

## T-PIT-6 Missing evidence

Delete `availability_ts` or the weekly row. Result = missing/ineligible.
Imputing from season aggregate or next week = FAIL. Default depth=2 =
FAIL. `x_continuity=0` on missing prior book = FAIL (E-1).

## T-PIT-7 Cutoff inequality

Three rows: ts < cutoff (eligible), ts == cutoff (ineligible under this
draft until a closed-at-cutoff freeze), ts > cutoff (always FAIL).

## T-PIT-8 Cross-feature scan

A committed manifest lists: injuries, rosters, depth, transactions,
QB changes, odds, weather. Each has `availability_ts` or
`EXEMPT-WITH-RYAN-REASON`. Omit one class → FAIL.

## T-PIT-9 Determinism

Re-run the same pinned synthetic inputs twice → bit-identical
membership/depth outputs.

## T-PIT-10 Regression / season-level STOP

With G-PIT mode on, `load_rosters` / `load_rosters_dir` season-union
path hard-STOPs (or is removed). A season snapshot file must not
produce week-1 membership.

## Shared PIT control (current collapse must fail)

Reuse the 2023-PIT shape in synthetic 2098: only roster file is week-19
WC with two ACT QBs. Current `load_rosters` fails T-PIT-1/2/5/10.
Week-aware rebuild (later step) must pass.

## What is not in this plan

- 2024/2025 bytes
- Refit
- Claiming T-PIT-* PASS (nothing has been run)
