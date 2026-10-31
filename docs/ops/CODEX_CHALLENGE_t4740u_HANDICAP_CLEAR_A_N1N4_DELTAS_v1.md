# CODEX_CHALLENGE_t4740u_HANDICAP_CLEAR_A_N1N4_DELTAS_v1

**Verdict:** `CHALLENGE_FILED` (N1–N4 deltas)  
**Not a grade:** this paper is **not** `PASS_CLEAR_A` and **not** `FAIL_CLEAR_A`. IMV re-grades N1–N4 after.  
**Role:** Codex — independent adversarial re-challenge. Paper only. No repairs. No product commits. No merge. No deploy. No capture. No self-grade.

Prior deltas **5cc4fcc1** on tip `10fe9175` stand as history. Closed D1/D3/D4 validator-path scope is **not** reopened. This paper is **N1–N4 only** vs sealed tip `1443d567`.

| Field | Value |
|---|---|
| Authority | COS_ORDER_CODEX N1–N4 · DECISION d744fa87 · IMV RETURN dafa4f94 · RECEIPT d4c0b7c2 |
| New sealed tip | `1443d567277b7e97271536dbe63871dbf194b00c` |
| Remotion v3 | `39a640aedeadb5e79eb1bd11d17e028a77959461` |
| Parent tip | `10fe917534254b94307dcbb1b47ffa250cde5c9e` |
| Base | `deploy-vercel` @ `209e90aa4a3f7edca15592af4cdd2f3c44f8b4c4` |
| DRAFT PR | https://github.com/kosedge/kosedge/pull/657 (`isDraft: true`, `headRefOid=1443d567`) |
| Prior Codex deltas | 5cc4fcc1 on 10fe9175 |
| Locks | NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD · overlays OFF |

---

## 0. Method

Diff `10fe9175..1443d567`: 7 files, +345/−125 (`identity.py` canonicalize, `validate_envelope`, `append_many` intra-batch, JSONL re-validate/re-derive, N1–N4 test module, D1–D4 match-string widen, evidence restamp). No `tasks.py` / `routes/nfl.py` / `infra/db` / `apps/web` in remotion. `nfl_simulator.py` unchanged vs `10fe9175`.

Re-ran on tip tree:

```
python3 -m pytest tests/test_nfl_handicap_clear_a_d3.py \
  tests/test_nfl_handicap_clear_a_d1_d4_remotion.py \
  tests/test_nfl_handicap_clear_a_n1_n4_remotion.py -q
```

**20 passed in 0.12s.** Independently re-measured N1–N4 and D1/D3/D4 probes under `/tmp`.

---

## 1. Disposition

| Item | Remotion claim | Codex N1–N4 |
|---|---|---|
| N1 Envelope takes layer gates | CLOSED | **CLOSED** (measured) |
| N2 `append_many` intra-batch dups | CLOSED | **CLOSED** (measured) |
| N3 UTC-canonical `as_of_ts` identity | CLOSED | **CLOSED** (measured) |
| N4 JSONL re-validate + re-derive | CLOSED | **CLOSED** (forged id / stub measured) |
| D1 / F1 exact blend=0 | no regress | **no regress** |
| D3 / F5 F6 F7 | no regress | **no regress** |
| D4 / F9 F11 F12 | no regress | **no regress** |
| F8 D3(i) oracle | NON_BLOCKING | **NON_BLOCKING** (not broken) |
| F10 DDL owner lock | NON_BLOCKING | **NON_BLOCKING** (not broken; not in `infra/db`) |

No N1–N4 blocker reopened. #657 remains draft.

---

## 2. Measured proof — N1–N4 CLOSED

### N1 — public Envelope runs `validate_envelope`

`append` / `append_many` call `validate_envelope` (layer/label + aware ts + `validate_l0/l1/l4` + re-derive).

| Probe | Result | store len |
|---|---|---|
| L1 Envelope labeled `handicapped_fair`, naive `as_of`, empty payload | REJECT `forecast_label must be handicap_delta (HF/MIF smear forbidden)` | 0 |
| Valid L0 Envelope with `payload.market_blend=0.3` via `append` | REJECT `market_blend MUST = 0` | 0 |
| Same dirty Envelope via `append_many` | REJECT `market_blend MUST = 0` | 0 |

Prior envelope bypass (HF/naive/empty or dirty L0 payload written without layer gates) does not reproduce.

### N2 — intra-batch duplicate rejected before write

`append_many([env, env])` on an empty store → REJECT `duplicate prediction_id (hl_fbe27c6e…); never overwrite`. `len==0`, `rows()==[]`.

`seen_ids` / `seen_biz` are checked against both the store and the in-batch sets **before** `_write`. Snapshot rollback path unchanged.

### N3 — same instant, one identity

`canonicalize_as_of_ts` maps:

| Input | Canonical |
|---|---|
| `2026-10-25T15:00:00Z` | `2026-10-25T15:00:00Z` |
| `2026-10-25T15:00:00+00:00` | `2026-10-25T15:00:00Z` |
| `2026-10-25T11:00:00-04:00` | `2026-10-25T15:00:00Z` |

`make_prediction_id` equal across all three. First `commit_l1_stage` ACCEPTED (len 1). Second (`+00:00`, delta 1.5) REJECT duplicate. Third (`-04:00`, delta 9.0) REJECT duplicate. Len stays 1.

Grain note (not an N3 reopen): `canonicalize_as_of_ts` strips microseconds, so `15:00:00.999Z` and `15:00:00Z` share an id (`us_collapse=true`). Second-grain timestamptz identity; distinct sub-second instants collapse.

### N4 — JSONL load re-validates and re-derives

| Disk | Result |
|---|---|
| Valid L1 row with `prediction_id` replaced by `hl_forged` | REJECT caller-chosen / forged mismatch |
| Stub `{prediction_id: hl_forged, layer: L1}` | REJECT missing layer/forecast_label/decision_ts |

Prior last-wins / silent accept of forged ids does not reproduce.

**Residual (not N4 reopen):** JSONL load **ACCEPTED** a row with top-level `market_blend=0` and `payload.market_blend=0.3` because `_field_from` prefers the top-level field. The same dirty Envelope on `append` still REJECTS (N1). D1 validator-path `validate_l0_row(market_blend=0.3)` still REJECTS. Load-path field precedence is a residual, not a forged-id miss and not a D1 regress.

---

## 3. No-regress — D1 / D3 / D4 validator path

| Probe | Result |
|---|---|
| F1 `0`/`0.0` exact zero | True |
| F1 `market_blend=0.3` / `False` | REJECT MUST = 0 |
| F5 naive as_of | REJECT naive (no UTC impute) |
| F5 ET `15:00-04:00` vs `20:00Z` | ACCEPTED |
| F6 L1 `baseline_personnel_ref` smear | REJECT missing `baseline_ref` |
| F7 missing `factor` / L0 missing `sigma` | REJECT missing required |
| F9 L1 labeled `handicapped_fair` | REJECT must be `handicap_delta` |
| F11 empty `game_id` | `HandicapLedgerReject` (not bare `ValueError`) |
| F12 packet | names remotion parent `39a640ae`; no stale HEAD SHA printed |

D1–D4 remotion tests still pass (match strings widened to `REJECT` because N1/N4 reject earlier with different text). Reject behavior holds.

---

## 4. NON_BLOCKING residuals (not broken)

**F8 / R1** — D3(ii) pin still `75ee2ee90dfb423c21cd66c8caab999cea20fda7277676e4944416596fac6224`. Default path has no `independent_fair` key. IF `margin_mu` still `0.157…`. Oracle still payload-vs-helper, week 8. Not broken.

**F10 / R2** — DDL still not under `infra/db`. `REVOKE FROM PUBLIC` unchanged. Do not apply.

---

## 5. Hard stops / scope

#657 `isDraft: true`, base still `209e90aa`. Live callers unwired. No capture, overlays OFF, no CERT/F2/Coming Soon/#655. Remotion v3 did not touch `nfl_simulator.py` vs parent `10fe9175`.

---

## 6. Close

**`CHALLENGE_FILED` (N1–N4 deltas).** N1 N2 N3 N4 are **CLOSED with measured proof** on tip `1443d567`. D1/F1, D3/F5–F7, D4/F9/F11/F12 did **not** regress. F8 and F10 remain **NON_BLOCKING**. Load-path top-level vs payload precedence is a residual beside N4, not a reopen. Prior papers 3aa21f63 / 5cc4fcc1 are history.

IMV re-grades N1–N4. Codex does not grade PASS/FAIL.

Paper only · no repairs · no merge · no deploy · no capture  
NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD · overlays OFF
