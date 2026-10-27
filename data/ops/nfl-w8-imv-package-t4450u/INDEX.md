# IMV package — W8 prospective capture (draft #640)

**Authority:** Ryan t4450u (decision sha8 `20ea635f`) — Post-Merge Execution.  
**ACCEPT:** #634–#636 / receipt `6685ba74`.  
**PR:** https://github.com/kosedge/kosedge/pull/640 (DRAFT — do not merge).  
**NFL NO-GO / Coming Soon ON.**

This directory is the **one** reproducible IMV deposit for the engineering draft.
It is **not** a seal-ack. Cursor cannot seal-ack (AC-12).

## Pointers

| What | Path |
| --- | --- |
| This package | `data/ops/nfl-w8-imv-package-t4450u/INDEX.md` |
| Spec-to-code map | `data/ops/nfl-w8-prospective-capture-spec-to-code-t4445u.md` |
| Source inventory | `data/ops/nfl-w8-imv-package-t4450u/FILELIST.txt` |
| Inventory hashes | `data/ops/nfl-w8-imv-package-t4450u/INVENTORY.SHA256SUMS` |
| Hard-stop proof | `data/ops/nfl-w8-imv-package-t4450u/HARD_STOPS.json` |
| Bundle hash-chain | `data/ops/nfl-w8-imv-package-t4450u/evidence.jsonl` |
| Bundle SHA256SUMS | `data/ops/nfl-w8-imv-package-t4450u/SHA256SUMS` |
| Pytest rerun | `scripts/ci/run-nfl-w8-capture-tests.sh` |
| Capture module | `services/model-service/src/services/nfl_w8_capture/` |
| Unit tests | `services/model-service/tests/test_nfl_w8_capture.py` |

## Tip SHA

Recorded in the PR body after the commit that adds this package.
Verify: `git rev-parse HEAD` on `cursor/nfl-w8-prospective-capture-ef3e`.

## Pytest

- Count at package write: **25**.
- Rerun: `bash scripts/ci/run-nfl-w8-capture-tests.sh`
- Or: `cd services/model-service && PYTHONPATH=. python3 -m pytest tests/test_nfl_w8_capture.py -q`

## CI (prior tip `fb38b5f5`)

| Workflow | Run | Result |
| --- | --- | --- |
| Production Gate | https://github.com/kosedge/kosedge/actions/runs/40520636706 | GREEN |
| PR Checks | https://github.com/kosedge/kosedge/actions/runs/40520636740 | RED — Prettier on synthetic JSON fixture (closed in this revision) |

New run IDs belong to the tip that contains this package. PR Checks must include step `W8 prospective capture unit tests`.

## t4450u items 1–4

1. Scheduler: beat `nfl-w8-capture-pre-kickoff-tick` → `src.tasks.run_nfl_w8_capture_tick` (`*/2`, queue `nfl_market`).
2. Alerts: `alerts.deliver_alert` — chained `alerts.jsonl`; default off; hold → `hold_blocked`.
3. Immutable evidence: `store.BundleStore` hash-chain + SHA256SUMS. **Not** prediction seal-ack.
4. CI safeguards: `pr-check.yml` NFL list + named W8 pytest step; Prettier fixture formatted.

## Hard stops (still hard)

- `refuse_odds_fetch` always raises (`OddsApiHoldError`).
- `refuse_seal` always raises (`PermissionError` / AC-12).
- No Odds network / no key use.
- No merge / deploy / Coming Soon OFF.
- No `NFL_ODDS_API_CARRIED_BOOKMAKERS` edit.
- Live capture Needs-Ryan. Do not pull live.

## Remaining gaps

- H-1a / H-1c live Odds pull (Needs-Ryan).
- AC-1/2/8/10 seal, custodian receipt, baselines, grading.
- Webhook POST (hold fail-closes).
