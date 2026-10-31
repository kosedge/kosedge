# W8 t4520u / t4523u Option A — T-0 reserve + reconcile (draft)

**Status:** paper/code draft only. NFL NO-GO stays. Coming Soon ON. sealed=0.  
**PR:** draft `#640`. Tip after this commit (see git). No merge. No deploy. No live Odds.  
**Authority:** `DECISION_RYAN_t4520u` sha8 `c189be63`; COS_ORDER sha8 `3d2e3eef`; Ryan t4523u Option A LOCKED (leave beat/worker running).  
**PR evidence:** `PR_T4520U_RO_CREDIT_RECONCILE_EVIDENCE` sha8 `75aa28b4`.  
**Immutable FAIL CLOSED:** `PR_W8_FIRST_SEALED_CAPTURE_RECEIPT_t4516u` sha8 `072005fe` — do not rewrite.

**no prior grades** for this credit-accounting correction (`data/knowledge/` has no W8 capture cards covering T-0 reconcile).

## Defect (localized, confirmed)

`credits.seed_account_baseline_note` on tip `3e2f643b` wrote ledger prev `used=11622 last=0` (VERIFY cite).  
`_reconcile_account_used` required `prev+last==used` exactly.

PATH A first live response: `used=11707 last=3` → `11622+3 != 11707` → EXIT 2.  
Fail-closed was **correct** under that code. Gap 82 is concurrent beat/worker since VERIFY (Option A: leave running).  
T-0 probe `11704 last=0` + capture `11707 last=3` is arithmetically consistent (`11704+3=11707`).

H-1c constants **11622 / 14622 stay immutable**. Do not reset or enlarge. Do not treat 11622 as a live prior.

## Fix (this tip)

1. Baseline note is note-only. It does **not** write `used=11622` as ledger prev.
2. Reconcile prior is a **T-0** snapshot (`role=t0`, `last` must be 0) immediately before each request.
3. **Reserve worst-case** (`T-0 used + estimate`) before execute. Reservation must not ignore counter differences (refusing `used_for_reserve=11622` when T-0 is `11704`).
4. After: this-request charge = `x-requests-last`. Concurrent = `used_after − T-0 − last`.
5. Concurrent >0 is attributed `beat_worker` (Option A). Never zeroed, never folded into oneshot cumulative.
6. Unexplained discrepancy (negative concurrent, this-request charge > reserved, missing T-0, missing headers, missing attribution) → fail closed.
7. Insufficient headroom vs 14622 / `(used−11622)+estimate≤3000` → fail closed **before** transport.
8. Abort recovery = **new bundle + new T-0**. Dirty dest (`072005fe`) stays closed.

KEEP / rotate-confirm FAIL CLOSED is unchanged (R1–R7).

## Synthetic proof (no live Odds)

```
cd services/model-service && PYTHONPATH=. NFL_W8_H1_AUTH_CITE=89fdd45f CREDENTIAL_POLICY=KEEP_EXISTING KEEP_AUTH_SHA8=a9ae5ae6 VERIFY_PASS_SHA8=e64e73ac H1C_AUTH_SHA8=89fdd45f T4500U_SHA8=20325274 ROTATION_ASSERTED=false python3 -m src.services.nfl_w8_capture --synthetic --bundle-dir /tmp/nfl-w8-synthetic-demo
```

`--synthetic` auto-seeds T-0 `11622/8378/last=0` to match fixture `11652/30`. Live path requires `--t0-used` / `--t0-remaining` or `NFL_W8_T0_*`.

```
bash scripts/ci/run-nfl-w8-capture-tests.sh
```

Required cases: normal T-0; stale VERIFY seed; concurrent beat/worker; reservation ignore-delta; missing headers; T-0 last≠0; this-request > reserved; account ceiling; repeated exec; abort recovery; insufficient headroom (no transport); oneshot missing T-0; oneshot concurrent synthetic.

## Out of scope

Live Odds. Merge. Deploy. Railway env. Pause/change beat or worker (Option A: leave running). Retry under t4516u/t4517u. Rewrite `072005fe`.
