# W8 #640 IMV RETURN — B3 credit ledger (t4468u)

**Authority:** IMV RETURN B3 `03a4caca`. Prior sealing RETURN pin `e5c84d60` (do not cite `d831`).  
**ENG PASS `86c6dbce` stands (eng-package only).** H-1b paper CLEAR `b9a24b8a`.  
**PR:** https://github.com/kosedge/kosedge/pull/640 (**DRAFT**). Successor to `6be2a85a`.  
**NFL NO-GO / Coming Soon ON.** Not a seal-ack. Not live Odds. Not H-1a.

## Fix

Hypothesis verified: `record_credit_use` raised before save; `fetch.py` estimated `next_credits=1`.

- Actual spend is always appended (overrun-marked) **before** raise+alert.
- After overrun / ceiling / used-header mismatch, every subsequent pre-call refuses.
- Pre-call estimate = bookmakers × markets × regions (PART B five-book = 30). Estimate < 1 rejected. Never default 1.
- Ledger delta reconciled to `x-requests-used`; mismatch fail-closed (still recorded).

## Proof

- Pytest: `bash scripts/ci/run-nfl-w8-capture-tests.sh`
- Required case: ledger 2990 + real cost 30 → cumulative 3020 recorded, next call refused.
- Tip SHA: `a23e5db3dd3f990c5212a84ae4b83f5e564d2c1f` (B3 code+docs). A docs-only receipt after this line may move HEAD; greens for the B3 fix belong to this SHA unless CI is reported on a later receipt.

## Remains for IMV re-grade

- Sealing ACCEPT on this successor tip (B3 was the last blocker).
- Cond 2 rotate/verify without key disclosure.
- Cond 5 first sealed capture independent verify.
- Live Odds still STOP.
