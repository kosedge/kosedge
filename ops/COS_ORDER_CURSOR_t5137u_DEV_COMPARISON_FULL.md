# Cos ORDER — Cursor B worker: full DEV matched72 comparison record

Authority: OWNER_CLEAR_t5137u **574dde7f** · parent #693 HEAD **0e8aa7f8** / market E2E impl **4c84cb55** · Cos ACCEPT market **6dca4edd** · Alex market PASS_RO **6ad6b652**
CERT=0 · DRAFT≠merge · NO EVAL · NO claim · NO retune · HARD END 19:35 ET

## Goal
Complete the already-approved R2-B DEV matched-market diagnostic by persisting the omitted model-vs-market fields for the **immutable matched72** cohort.

## Do
1. Preserve old MARKET_E2E / DEV receipts byte-immutable (do not rewrite history).
2. Append full matched72 **DEV_RESEARCH** record including:
   - exact game IDs + input hashes
   - candidate MAE/RMSE/bias, IF MAE/RMSE/bias, market MAE/RMSE/bias
   - paired mean signed absolute-loss differences vs IF and vs market
   - both frozen game-cluster and week-cluster intervals
   - per-season tables
3. Explicitly pass/label **DEV** (fix any inherited `split="eval"` on the matched DEV call).
4. If recompute needed to persist omitted output: same fixed DEV calculation only; label **reporting reproduction** (not independent confirmation). Disclose in addendum.
5. Do **not** substitute #694 normalized 94-DEV cohort. This tip is matched72 only.
6. Stop: DRAFT update on #693, addendum + receipt hashes. No EVAL invoke.

## Out
EVAL · NEW bind · fitting · retune · new candidate · G5 loosen · merge · #694 rewrite · silent 94 swap.
