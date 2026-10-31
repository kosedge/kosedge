# CODEX_CHALLENGE_t4740u_HANDICAP_CLEAR_A_DELTAS_v1

**Verdict:** `CHALLENGE_FILED` (deltas)  
**Not a grade:** this paper is **not** `PASS_CLEAR_A` and **not** `FAIL_CLEAR_A`. IMV re-grades D1–D4 after.  
**Role:** Codex — independent adversarial re-challenge. Paper only. No repairs. No product commits. No merge. No deploy. No capture. No self-grade.

Prior challenge **3aa21f63** on tip `c5252101` stands as history. This paper is **D1–D4 remotion only** vs sealed tip `10fe9175`. Closed prior scope is not reopened.

| Field | Value |
|---|---|
| Authority | COS_ORDER_CODEX deltas · DECISION d744fa87 · IMV RETURN 5c616db5 · Cursor v2 remotion |
| New sealed tip | `10fe917534254b94307dcbb1b47ffa250cde5c9e` |
| Remotion | `e1bf070c96e53c08d045f06740a1e636b43dc0d4` |
| Prior tip | `c525210170fd09864b7232974b37dfc56f2ef4ab` |
| Base | `deploy-vercel` @ `209e90aa4a3f7edca15592af4cdd2f3c44f8b4c4` |
| DRAFT PR | https://github.com/kosedge/kosedge/pull/657 (`isDraft: true`, `headRefOid=10fe9175`) |
| Evidence | CURSOR_EVIDENCE v2 · RECEIPT tip 10fe9175 |
| Prior Codex | 3aa21f63 on c5252101 |
| Locks | NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD · overlays OFF |

---

## 0. Method

Diff `c5252101..10fe9175`: 10 files, +770/−192 (ledger + simulator IF mu gate + D3 test label fix + new remotion test module + evidence restamp). Diff `209e90aa..10fe9175` still excludes `tasks.py`, `routes/nfl.py`, `infra/db`, `apps/web`.

Re-ran on tip tree:

```
python3 -m pytest tests/test_nfl_handicap_clear_a_d3.py tests/test_nfl_handicap_clear_a_d1_d4_remotion.py -q
```

**15 passed in 0.09s** (5 D3 + 10 remotion). Independently re-measured each filed probe under `/tmp` (not by trusting the remotion tests alone). D3(ii) sha256 recomputed on tip default path.

---

## 1. Disposition (D1–D4 only)

| Finding | IMV RETURN | Remotion claim | Codex deltas |
|---|---|---|---|
| F1 L0 blend `int()` | OPEN blocker | CLOSED | **CLOSED** (measured) |
| F2 caller-chosen id | OPEN blocker | CLOSED | **CLOSED** (measured) |
| F3 JSONL last-wins | OPEN blocker | CLOSED | **CLOSED** (measured) |
| F4 payload-hash overwrite | OPEN blocker | CLOSED | **CLOSED** (measured) |
| F5 naive TZ | OPEN blocker | CLOSED | **CLOSED** (measured) |
| F6 imputes (listed) | OPEN blocker | CLOSED | **CLOSED** (measured) |
| F7 L1/L0 required sets | OPEN blocker | CLOSED | **CLOSED** (measured) |
| F9 HF/MIF smear | OPEN minor | CLOSED | **CLOSED** (measured) |
| F11 ValueError | OPEN minor | CLOSED | **CLOSED** (measured) |
| F13 non-atomic stage | OPEN blocker | CLOSED | **CLOSED** (measured) |
| F12 packet SHA | OPEN minor | restamped | **CLOSED** (no stale HEAD SHA) |
| F8 D3(i) oracle | NON_BLOCKING | residual | **NON_BLOCKING** (not broken) |
| F10 DDL REVOKE | NON_BLOCKING | residual | **NON_BLOCKING** (not broken; not in `infra/db`) |

No D1–D4 blocker reopened. No new live-path flip. #657 remains draft.

---

## 2. Measured proof — CLOSED

### F1 — exact `market_blend == 0`

`is_exact_zero` rejects `bool` before numeric compare; `int(blend)` is gone (`validate.py`).

| Input | Result |
|---|---|
| `0` / `0.0` | ACCEPTED |
| `0.3` | `HandicapLedgerReject` market_blend MUST = 0 |
| `False` / `True` | REJECT |
| `"0"` / `None` | REJECT |

Prior fail-open (`int(0.3)==0`, `int(False)==0`) does not reproduce.

### F2 — validated-only append; id re-derived

| Probe | Result | store len |
|---|---|---|
| `append({prediction_id: hl_attacker_chosen, junk})` | REJECT unvalidated (need layer, forecast_label, decision_ts) | 0 |
| `HandicapLedgerEnvelope(prediction_id=hl_attacker_chosen, …)` | REJECT caller-chosen does not match re-derived | 0 |
| Valid L1 fields + `prediction_id=hl_attacker_chosen` via `append_layer` | REJECT caller-chosen mismatch | 0 |

`make_prediction_id` ignores `payload`. Envelope always stores the derived id.

### F3 — JSONL load rejects duplicates (no last-wins)

| Disk | Result |
|---|---|
| two lines, same `prediction_id` | REJECT `duplicate prediction_id same (no last-wins)` |
| two lines, different pids, same business key | REJECT `duplicate business identity (no last-wins)` |

Constructor raises; no in-memory last-wins index.

### F4 — business identity = DDL unique key

`make_prediction_id(..., payload={delta:0.0})` == `make_prediction_id(..., payload={delta:1.5})` → **True** (`hl_896e11e0…` on this fixture).

First `commit_l1_stage(delta=0.0)` ACCEPTED (len 1). Second `delta=1.5` → REJECT `duplicate prediction_id …; no writes` (len stays 1).

Python identity columns match `ddl_clear_a.sql` unique index: `layer, forecast_label, game_id, as_of_ts, capture_id, schema_version`.

### F5 — naive REJECT; mixed-offset aware compare

| as_of / decision | Result |
|---|---|
| naive `17:00:00` / `16:00:00-04:00` | REJECT naive (no UTC impute) |
| `15:00:00-04:00` / naive `16:00:00` | REJECT naive |
| `15:00:00-04:00` (19:00Z) / `16:00:00Z` | REJECT as_of > decision |
| `15:00:00-04:00` / `20:00:00Z` | ACCEPTED |
| `15:00:00Z` / `16:00:00+00:00` | ACCEPTED |

Prior false-accept (naive-as-UTC) and false-reject (ET vs naive) do not reproduce.

### F6 — listed imputes gone

| Probe | Result |
|---|---|
| L4 omit `as_of_ts` (has `captured_at`) | REJECT missing `as_of_ts` (no captured_at fallback) |
| L1 omit `baseline_ref`, supply `baseline_personnel_ref` | REJECT missing `baseline_ref` |
| L1 `registry_id=""` | REJECT missing `registry_id` |
| `independent_fair_mus` without mus | `ValueError` mus missing (no impute to 0.0) |

Documented NON_BLOCKING leftovers (not as-of identity): `created_at` write stamp; `schema_version` default to `handicap-ledger-v0-clear-a`. Dead-path `if margins else 0.0` remains in the IF branch; `sims = max(300, …)` makes empty draws unreachable. Not an F6 reopen.

### F7 — blueprint L1 + L0 required sets

L1 now requires `factor, entry_point, delta, uncertainty` plus the original five. Measured REJECT on each omission. `delta=False` → REJECT must be numeric.

L0 now requires `off_eff_*`, `def_eff_*`, `pace_*`, `sigma`, `market_blend` (243a384e). Measured REJECT on omitted `off_eff_h`, `sigma`, `market_blend`.

### F9 — L1 is delta, L4 is MIF

| Probe | Result |
|---|---|
| `validate_l1_row(forecast_label=handicapped_fair)` | REJECT must be `handicap_delta` |
| `append_layer(L1, handicapped_fair)` | REJECT HF/MIF smear forbidden |
| L4 `forecast_label=""` | REJECT missing `forecast_label` |
| L4 labeled `independent_fair` | REJECT must be `market_informed_fair` |

D3 coexist test now stores L1 as `handicap_delta`. `handicapped_fair` remains in `FORECAST_LABELS` / DDL CHECK but cannot attach to L0/L1/L4. Unused HF-forecast layer is out of CLEAR-A scope (L2/L3 not implemented).

### F11 — identity errors are `HandicapLedgerReject`

`make_prediction_id(game_id="")` → `HandicapLedgerReject: all prediction_id components required (no impute)` (not bare `ValueError`).

L4 `append_layer` missing `capture_id` → `HandicapLedgerReject` missing required `capture_id`.

### F13 — stage is validate + dup-check all, then write

| Stage | Result | store len |
|---|---|---|
| `[ok, same-biz weather]` | REJECT duplicate prediction_id; no writes | 0 |
| then `[ok]` | ACCEPTED | 1 |
| then `[ok, delta=1.5]` | REJECT no writes | 1 |
| `[ok game A, missing factor game B]` on empty store | REJECT missing factor | 0 |

`append_many` snapshots rows/ids/biz/JSONL bytes and restores on exception.

### F12 — packet no longer names a stale HEAD

In-repo evidence at `10fe9175` names remotion parent `e1bf070c` and says sealed tip is “this stamp commit” (confirm via `HEAD` / `headRefOid`). It does **not** reprint a previous SHA as HEAD (the c5252101/3e29a0a7 lag). CoS RECEIPT names `10fe9175`. Hygiene CLOSED. Self-hash chicken-egg remains (a commit cannot contain its own SHA without a further stamp).

---

## 3. NON_BLOCKING residuals (not broken by remotion)

### F8 / R1 — D3(i) oracle unchanged

Tip default-path sha256 still `75ee2ee90dfb423c21cd66c8caab999cea20fda7277676e4944416596fac6224` (D3(ii) pin holds). IF payload `margin_mu=0.157…` vs helper `0.16` (abs 0.00285 ≤ 0.01). Published IF `markets.spread_home=-0.16` vs blended `+0.94` (gap 1.10). Test still does not lock `if_out["markets"]` or weeks 1–4. Remotion left an explicit residual comment. **Not broken. Not closed. Not reopened as a D1–D4 blocker.**

### F10 / R2 — DDL owner lock

`REVOKE UPDATE, DELETE … FROM PUBLIC` remains. File is still not under `infra/db`. Migrate discovery still requires `NNN_name.sql`. Do not apply. **Not broken. Must close before any apply CLEAR.**

---

## 4. Hard stops / scope (unchanged)

#657 `isDraft: true`, base still `209e90aa`. Live callers unwired. `NFL_INDEPENDENT_FAIR_PATH is False`. No capture, overlays OFF, no CERT/F2/Coming Soon/#655. Remotion did not expand into tasks/routes/infra/db/web.

---

## 5. Close

**`CHALLENGE_FILED` (deltas).** D1–D4 blockers F1 F2 F3 F4 F5 F6 F7 F13 and minors F9 F11 F12 are **CLOSED with measured proof** on tip `10fe9175`. F8 and F10 remain **NON_BLOCKING** residuals (not broken). Prior paper 3aa21f63 on `c5252101` is history.

IMV re-grades D1–D4. Codex does not grade PASS/FAIL.

Paper only · no repairs · no merge · no deploy · no capture  
NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD · overlays OFF
