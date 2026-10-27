# W8 prospective capture — spec-to-code map (draft)

**Status:** paper/code draft only. NFL NO-GO stays. Coming Soon unchanged.  
**Owner (build):** Cursor per `DECISION_RYAN_t4445u_RD7_CURSOR_W8_BUILDER_v1` (ops path cite `91aebe69`).  
**Parallel:** t4447u (not this PR).  
**Base:** `deploy-vercel` `bfc89f57`.  
**Module:** `services/model-service/src/services/nfl_w8_capture/`

Cited sha8 (authority; files not in this checkout — do not invent bodies):

| Cite | sha8 |
| --- | --- |
| `IMV_SPEC_W8_PROSPECTIVE_CAPTURE_ACCEPTANCE_t4191u_v2` | `08808adf` |
| FINAL ADOPT PART B | `0448042a` |
| PART B freeze | `2e40ead4` |
| PR unblock path | `0511c346` |

v1 AC text was read from the IMV attachment (`IMV_SPEC_W8_PROSPECTIVE_CAPTURE_ACCEPTANCE_t4191u_v1`). v2 deltas that are not in-repo are implemented only where PART B / this ticket states them.

**no prior grades** for this capture product (`data/knowledge/` has no W8 capture cards).

---

## Hard holds (unchanged)

| Hold | This PR |
| --- | --- |
| Odds API hold (H-1a / H-1c) | **Still blocking.** `hold.refuse_odds_fetch` always raises. No key use. |
| Seal-ack (AC-12) | **Still blocking.** `streams.refuse_seal` always raises. |
| Merge / deploy / Railway / Coming Soon / public NFL numbers | **Not in scope.** Draft PR only. |

---

## AC-1..AC-14

| ID | Requirement | Status | Code |
| --- | --- | --- | --- |
| AC-1 | Seal >= 60 min pre-kickoff | **Stubbed** | Documented in pin manifest `seal_ack`. No seal runner. |
| AC-2 | Independent seal timestamp / custodian receipt | **Stubbed** | Cursor cannot mint seal time of record. |
| AC-3 | as_of < kickoff and < seal; no default fill | **Partial** | Close / cell logic fail-closed on missing stamps. Full feature as_of proofs not wired to production features. |
| AC-4 | Manifest: code / weights / schema / input shas / interpreter / host | **Implemented (shape)** | `pin.build_pin_manifest` / `validate_pin_manifest`. Empty sha = UNSET. No fake shas. |
| AC-5 | Odds snapshots: book, market, price/line, provider captured_at, received_at, raw sha | **Implemented (offline)** | Snapshot payload + close cells. Live source pull blocked on H-1a/H-1c. |
| AC-6 | SHA256SUMS + append-only hash-chain log | **Implemented** | `evidence.append_evidence_entry` / `verify_evidence_chain` / `write_sha256sums`. Secrets redacted. |
| AC-7 | S-MKT vs S-IND; forbidden-input check | **Implemented (scaffold)** | `streams.scaffold_streams` + `check_s_ind_forbidden_inputs`. No invented predictions. |
| AC-8 | Filing-E baselines | **Stubbed** | Not adopted in this draft; no baseline numbers. |
| AC-9 | No post-seal edits | **Stubbed** | No seal; snapshot/log files are append-only. |
| AC-10 | Blind grading | **Out of scope** | Performers do not grade. |
| AC-11 | Missing/late = FAIL, counted | **Partial** | Close/cadence alerts mark MISSING; no grader. |
| AC-12 | Cursor cannot seal-ack | **Implemented (refuse)** | `streams.refuse_seal`. |
| AC-13 | Isolated from PIT historical rebuild | **Implemented** | New package; no shared mutable store; no hist numbers in bundle. |
| AC-14 | No public NFL numbers; NO-GO stays | **Honored** | No web/Coming Soon/kill-switch edits. |

---

## PART B / RA / DR (this ticket)

| ID | Rule | Status | Code / test |
| --- | --- | --- | --- |
| PART B books | PRIMARY exactly DK, FD, BetMGM, Fanatics, Circa; Bally Bet optional secondary | **Implemented** | `books.PRIMARY_BOOKS` / `OPTIONAL_SECONDARY_BOOKS` |
| PART B request | `bookmakers=` must include `circa` (carried list without circa is insufficient) | **Implemented** | `books.build_w8_odds_request_params` |
| PART B circa cell | Missing circa = MISSING, never impute | **Implemented** | `close.evaluate_game_market_close` + DR-10 test |
| PART B stamps | Store provider server ts **and** market `last_update` | **Implemented** | `BookMarketCell` + snapshot payload |
| PART B close | Last snap with provider server ts <= kickoff and age <= S=10 min | **Implemented** | `close.py` |
| PART B last_update | Missing `last_update` => UNKNOWN => not a close | **Implemented** | DR-7 |
| PART B receive | Client receive time alone is not a close | **Implemented** | DR-8 |
| PART B k=3 | k=3 PRIMARY present + non-stale else close=MISSING | **Implemented** | DR-9 |
| Cadence | <=10 min pre-kickoff sample for REG; alerts missing/stale/partial | **Implemented (planner)** | `cadence.py` — not wired to Celery beat |
| RA-5 | Stale (age > S) fail-closed | **Implemented** | STALE cells do not count toward k |
| DR-7 | missing last_update | **Tested** | `test_dr7_missing_last_update_is_unknown_not_close` |
| DR-8 | client receive only | **Tested** | `test_dr8_client_receive_alone_is_not_a_close` |
| DR-9 | k<3 => MISSING | **Tested** | `test_dr9_k_lt_3_close_missing` |
| DR-10 | circa hole never imputed | **Tested** | `test_dr10_missing_circa_never_imputed` |
| DR-2 analog | tamper breaks sha | **Tested** | evidence chain |
| DR-5 analog | edit/delete log line breaks chain | **Tested** | evidence chain |
| DR-6 analog | market field in S-IND fails closed | **Tested** | streams |

DR-7..DR-10 labels are the fail-closed behaviors named in this ticket. Full v2 DR prose for `08808adf` is not in-repo.

---

## Still blocked on H-1a / H-1c (Odds hold)

- Live `bookmakers=` pull including `circa`
- Provider HTTP Date / API server timestamp from a real response
- Real W8 REG slate snapshots
- Any dry-run that consumes credits
- Seal bundle against live odds vintage

This PR does **not** lift those holds.
