# W8 prospective capture — spec-to-code map (draft)

**Status:** paper/code draft only. NFL NO-GO stays. Coming Soon ON.  
**Owner (build):** Cursor per `DECISION_RYAN_t4445u_RD7_CURSOR_W8_BUILDER_v1` (ops path cite `91aebe69`).  
**Parallel:** t4447u (not this PR).  
**PR:** draft `#640`. Paper-verify continue vs receipt sha8 `2a9164bc`.  
**t4450u:** decision sha8 `20ea635f` — Post-Merge Execution. ACCEPT #634–#636 / receipt `6685ba74`.  
**t4455u:** H-1 auth `89fdd45f`. IMV RETURN sealing-controls pin `e5c84d60` (was mis-cited as `d831`). ENG PASS `86c6dbce` stands for eng-package only — not sealing ACCEPT.  
**t4468u:** B3 ledger RETURN `03a4caca`.  
**IMV package:** `data/ops/nfl-w8-imv-package-t4450u/INDEX.md`  
**RETURN close map:** `data/ops/nfl-w8-imv-return-t4455u-b1-b7.md`  
**Module:** `services/model-service/src/services/nfl_w8_capture/`

Cited sha8 (authority; files not in this checkout — do not invent bodies):

| Cite | sha8 |
| --- | --- |
| `IMV_SPEC_W8_PROSPECTIVE_CAPTURE_ACCEPTANCE_t4191u_v2` | `08808adf` |
| FINAL ADOPT PART B | `0448042a` |
| PART B freeze | `2e40ead4` |
| PR unblock path | `0511c346` |
| PAPER_GAPS receipt | `2a9164bc` |

**no prior grades** for this capture product (`data/knowledge/` has no W8 capture cards).

---

## Hard holds (unchanged)

| Hold | This PR |
| --- | --- |
| Odds API hold (H-1a / H-1c) | **Default ON.** `refuse_odds_fetch` raises unless `NFL_W8_H1_AUTH_CITE=89fdd45f` **and** `NFL_W8_PR_ROTATE_CONFIRM`. No live Odds call in this draft (transport required; none default). |
| Seal-ack (AC-12) | **Still blocking.** `streams.refuse_seal` always raises. `seal.produce_seal` is AC-1/AC-2 only. |
| Merge / deploy / Railway / Coming Soon / public NFL numbers | **Not in scope.** Draft PR only. |

---

## PAPER_GAPS 1–6 (this turn)

| # | Item | Status | Code / config |
| --- | --- | --- | --- |
| 1 | Scheduler wiring | **Closed** | Beat key `nfl-w8-capture-pre-kickoff-tick` in `services/model-service/src/celerybeat_schedule.py`. Task `src.tasks.run_nfl_w8_capture_tick` → `tick.run_capture_tick`. Default `NFL_W8_CAPTURE_TICK_MINUTE=*/2` on queue `nfl_market`. Kickoffs: `NFL_W8_KICKOFFS_JSON` or `NFL_W8_USE_SYNTHETIC_SLATE`. Bundle: `NFL_W8_EVIDENCE_DIR`. Tick never fetches Odds API. |
| 2 | Alert delivery | **Closed (draft path)** | `alerts.deliver_alert`. File sink = hash-chained `alerts.jsonl`. `NFL_W8_ALERTS_ENABLED` default off. `NFL_W8_ALERT_WEBHOOK_URL` name only. Hold → `hold_blocked` (no POST). |
| 3 | Tamper-proof store | **Closed** | `store.BundleStore`: chained JSONL (`prev_entry_sha`/`entry_sha`) + evidence log + `SHA256SUMS` rewritten last. Snapshot writes go through the store. Tamper / overwrite fail closed. |
| 4 | Forecast archiver | **Closed** | `archive.archive_forecasts` writes `forecasts/s_mkt/` and `forecasts/s_ind/` with `prediction=UNSET`. S-IND forbidden-input still fail-closed. No invented predictions. |
| 5 | Restore P-evidence | **Closed (read-only)** | `restore.restore_p_evidence` verifies chain + SHA256SUMS, copies to `p_evidence/<id>/` at 0444, `eval=not_run`. No protected eval. |
| 6 | CI green proof | **Wired** | `.github/workflows/pr-check.yml`: `tests/test_nfl_w8_capture.py` on the NFL pytest list **and** named step `W8 prospective capture unit tests`. Local pytest is the pre-push proof; PR Checks is the CI evidence. |

---

## AC-1..AC-14

| ID | Requirement | Status | Code |
| --- | --- | --- | --- |
| AC-1 | Seal >= 60 min pre-kickoff | **Implemented (producer)** | `seal.produce_seal` refuses inside 60m. Not a seal-ack. |
| AC-2 | Independent seal timestamp / custodian receipt | **Implemented (slot)** | `custodian_receipt.slot=AC-2`; `receipt_id=UNSET` until custodian. Cursor cannot ack. |
| AC-3 | as_of < kickoff and < seal; no default fill | **Partial** | Close / cell logic fail-closed on missing stamps. Full feature as_of proofs not wired to production features. |
| AC-4 | Manifest: code / weights / schema / input shas / interpreter / host | **Implemented (shape)** | `pin.build_pin_manifest` / `validate_pin_manifest`. Empty sha = UNSET. No fake shas. |
| AC-5 | Odds snapshots: book, market, price/line, provider captured_at, received_at, raw sha | **Implemented (offline)** | Snapshot payload + close cells. Live source pull blocked on H-1a/H-1c. |
| AC-6 | SHA256SUMS + append-only hash-chain log | **Implemented** | `store.BundleStore` + `evidence.*`. Secrets redacted. |
| AC-7 | S-MKT vs S-IND; forbidden-input check | **Implemented** | Scaffold + archiver. No invented predictions. |
| AC-8 | Filing-E baselines | **EXPLICIT_CARVE_OUT** | `carveouts.AC8_FILING_E_BASELINES`. No invented baselines. Surfaced in PR body. |
| AC-9 | No post-seal edits | **Partial** | No seal; store refuses artifact overwrite. |
| AC-10 | Blind grading | **EXPLICIT_CARVE_OUT** | `carveouts.AC10_BLIND_GRADING`. Restore stays `eval=not_run`. Surfaced in PR body. |
| AC-11 | Missing/late = FAIL, counted | **Partial** | Close/cadence/alerts mark MISSING; no grader. |
| AC-12 | Cursor cannot seal-ack | **Implemented (refuse)** | `streams.refuse_seal`. |
| AC-13 | Isolated from PIT historical rebuild | **Implemented** | New package; P-evidence restore is a read-only copy, not a shared mutable store. |
| AC-14 | No public NFL numbers; NO-GO stays | **Honored** | No Coming Soon / kill-switch / public number edits. |

---

## PART B / RA / DR

Unchanged from first draft (close definition, five PRIMARY books including circa, k=3, DR-7..DR-10, RA-5). Production `NFL_ODDS_API_CARRIED_BOOKMAKERS` is still not edited.

---

## Still blocked on H-1 live (Needs-IMV ACCEPT + rotate)

- Live Odds HTTP (not wired; transport injection only)
- Condition 5 first sealed capture independent verify
- Webhook live POST (path present, unwired)
- AC-8 / AC-10 remain **EXPLICIT_CARVE_OUT**
