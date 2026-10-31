# CODEX_CHALLENGE_t4748u_HANDICAP_CLEAR_A_R7_v1

**Verdict:** `CHALLENGE_FILED` (R7 deltas)  
**Not a grade:** this paper is **not** `PASS_CLEAR_A` and **not** `FAIL_CLEAR_A`. IMV grades after.  
**Role:** Codex — independent adversarial challenge. Paper only. No repairs. No product commits. No merge. No deploy. No capture. No self-grade.

Prior N1–N4 paper **7e353b5b** on tip `1443d567` stands. D1–D4 / N1–N4 are **not** reopened (no measured regress). CLEAR-B not in scope.

| Field | Value |
|---|---|
| Authority | DECISION 39fe2d9d · CoS ORDER 292f5b50 · Cursor RECEIPT 163b053a |
| Challenged tip | `637c2894fe12ddbec67cc3fef412c8a66c94d3d0` |
| R7 remotion | `b2cc5d666b391559fa040e0b716cc1628cb6b383` |
| Parent tip | `1443d567277b7e97271536dbe63871dbf194b00c` |
| Base | `deploy-vercel` @ `209e90aa4a3f7edca15592af4cdd2f3c44f8b4c4` |
| DRAFT PR | https://github.com/kosedge/kosedge/pull/657 (`isDraft: true`, `headRefOid=637c2894`) |
| Locks | NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD · overlays OFF |

---

## 0. Method

Diff `1443d567..637c2894`: 4 files, +271/−22.

| Commit | What |
|---|---|
| `b2cc5d66` | `validate.py` conflict + contaminated-blend gates; `tests/test_nfl_handicap_clear_a_r7.py` (6 tests) |
| `072cb4d2` | evidence restamp + R7 receipt (docs) |
| `637c2894` | prettier table alignment on those two docs files only |

Not in remotion: `store.py`, `nfl_simulator.py`, `tasks.py`, `routes/nfl.py`, `infra/db`, `apps/web`. JSONL load still calls `validate_l0_row` / `validate_l1_row` / `validate_l4_row` (unchanged store); R7 gates run because those validators now invoke them.

Re-ran on tip:

```
python3 -m pytest tests/test_nfl_handicap_clear_a_d3.py \
  tests/test_nfl_handicap_clear_a_d1_d4_remotion.py \
  tests/test_nfl_handicap_clear_a_n1_n4_remotion.py \
  tests/test_nfl_handicap_clear_a_r7.py -q
```

**26 passed in 0.20s.** Independently re-measured R7 load/reload/append under `/tmp`.

---

## 1. Disposition (prove or refute)

| Claim | Result |
|---|---|
| 1. Contaminated JSONL `top market_blend=0` + `payload.market_blend=0.3` REJECTS on load | **PROVED.** R7 **CLOSED** |
| 2. Clean write+reload ACCEPT; append-only + identity preserved | **PROVED** |
| 3. Negative regression tests present and measured | **PROVED** (6 R7 tests + independent probes) |
| 4. Prettier-only docs change does not weaken controls | **PROVED** |

No N1–N4 / D1–D4 regress measured. F8 pin unchanged. F10 not touched.

---

## 2. Measured proof

### Claim 1 — contaminated load REJECTS (R7)

Independent probe, same construction as prior Codex residual (valid L0 write, then disk-tamper):

| Disk row | Load | `validate_l0_row` |
|---|---|---|
| top `market_blend=0` + payload `0.3` | REJECT `top-level 'market_blend' conflicts with payload.market_blend (no precedence)` | same REJECT |
| payload-only `0.3` (no top-level key) | REJECT `market_blend MUST = 0 (top-level and payload; no precedence)` | — |
| top `0.3` + payload `0` | REJECT conflict (no precedence either way) | — |
| top `margin_mu=0.16` + payload `9.99` | REJECT `top-level 'margin_mu' conflicts with payload` | — |

Prior `1443d567` load **ACCEPTED** the first row (`_field_from` preferred top-level). That residual does not reproduce on `637c2894`.

Gates: `reject_top_level_payload_conflicts` + `reject_contaminated_market_blend` at the top of `validate_l0_row` (also conflict gate on L1/L4). Load path does not special-case around them.

### Claim 2 — clean write+reload

Clean `append_layer` L0 → JSONL reload: `len==1`, `prediction_id` unchanged (`hl_…`), layer `L0`, label `independent_fair`, `payload.market_blend==0`, re-derived id matches. Append-only: dirty Envelope `payload.market_blend=0.3` still REJECT on `append` and `append_many`, store len 0 (N1 preserved).

### Claim 3 — negatives measured

Module `tests/test_nfl_handicap_clear_a_r7.py` (6 tests, all pass):

1. `test_r7_jsonl_load_rejects_top_zero_payload_dirty_blend`
2. `test_r7_jsonl_load_rejects_payload_only_dirty_blend`
3. `test_r7_jsonl_load_rejects_top_dirty_payload_zero`
4. `test_r7_jsonl_load_rejects_conflicting_margin_mu`
5. `test_r7_clean_l0_write_reload_accepts_same_identity`
6. `test_r7_append_still_rejects_dirty_payload_blend`

Independent `/tmp` probes reproduced 1–6 outcomes (not by trusting pytest alone).

### Claim 4 — prettier does not weaken controls

`637c2894` touches only `docs/ops/NFL_HANDICAP_CLEAR_A_EVIDENCE_t4740u.md` and `docs/ops/NFL_HANDICAP_CLEAR_A_RECEIPT_t4748u_R7.md`. Diff is markdown table padding plus stamp wording (`R7 remotion + Prettier`). No Python, no DDL, no callers. Control surface is `b2cc5d66` only.

---

## 3. No-regress (spot-check; not a reopen)

| Probe | Result |
|---|---|
| D1 `0`/`0.0` exact zero | True |
| D1 `market_blend=0.3` / `False` | REJECT |
| D3/F5 naive as_of | REJECT naive |
| D3/F7 missing `factor` | REJECT missing required |
| N1 dirty payload append | REJECT, len 0 |
| D3(ii) pin | `75ee2ee90dfb423c21cd66c8caab999cea20fda7277676e4944416596fac6224` |

---

## 4. Residuals (unchanged, NON_BLOCKING)

R1/F8 D3(i) oracle still payload-vs-helper, week 8. R2/F10 DDL owner lock still not applied. R8 as_of second-grain vs microsecond (parent residual). Not broken by R7.

---

## 5. Hard stops

#657 `isDraft: true`, base still `209e90aa`. No capture, overlays OFF, no infra/db, no live wiring, no CERT/F2/Coming Soon/#655. Not CLEAR-B.

---

## 6. Close

**`CHALLENGE_FILED` (R7).** Claims 1–4 **PROVED**. R7 load-path field-precedence residual from 7e353b5b is **CLOSED** on tip `637c2894`. N1–N4 / D1–D4 not reopened. IMV grades next. Codex does not grade PASS/FAIL.

Paper only · no repairs · no merge · no deploy · no capture  
NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD · overlays OFF
