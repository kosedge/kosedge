# IMV package — W8 prospective capture (draft #640)

**Authority:** Ryan t4450u (decision sha8 `20ea635f`) — Post-Merge Execution.  
**ACCEPT:** #634–#636 / receipt `6685ba74`.  
**PR:** https://github.com/kosedge/kosedge/pull/640 (DRAFT — do not merge).  
**NFL NO-GO / Coming Soon ON.**

This directory is the **one** reproducible IMV deposit for the engineering draft.
It is **not** a seal-ack. Cursor cannot seal-ack (AC-12).

Ops-facing summary (single file): `data/ops/nfl-w8-imv-t4450u-summary.md`.

## Proof tip + CI

| Field | Value |
| --- | --- |
| Proof tip SHA | `ae7624f706380abde2c3740f8c9800e935a5696a` |
| Branch | `cursor/nfl-w8-prospective-capture-ef3e` |
| PR Checks | **GREEN** run **40521208974** — https://github.com/kosedge/kosedge/actions/runs/40521208974 |
| PR Quality Checks job | **GREEN** **122248486585** (named step `W8 prospective capture unit tests`: **25 passed**) |
| Production Gate | run **40521210121** — Web typecheck GREEN; Next build not #640-scoped |
| Prior RED (closed) | `fb38b5f5` PR Checks **40520636740** — Prettier on synthetic JSON fixture |

A later docs-only receipt commit may move HEAD; the green IDs above are for the proof tip.

## Pointers

| What | Path |
| --- | --- |
| Ops summary | `data/ops/nfl-w8-imv-t4450u-summary.md` |
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

## Pytest

- Count: **25** passed (local + CI W8 step).
- Rerun: `bash scripts/ci/run-nfl-w8-capture-tests.sh`
- Or: `cd services/model-service && PYTHONPATH=. python3 -m pytest tests/test_nfl_w8_capture.py -q`

## t4450u items 1–4 (closed)

1. Scheduler: beat `nfl-w8-capture-pre-kickoff-tick` → `src.tasks.run_nfl_w8_capture_tick` (`*/2`, queue `nfl_market`).
2. Alerts: `alerts.deliver_alert` — chained `alerts.jsonl`; default off; hold → `hold_blocked`.
3. Immutable evidence: `store.BundleStore` hash-chain + SHA256SUMS. **Not** prediction seal-ack.
4. CI safeguards: `pr-check.yml` NFL list + named W8 pytest step; Prettier fixture formatted; PR Checks GREEN on proof tip.

## Hard stops (still hard)

- `refuse_odds_fetch` always raises (`OddsApiHoldError`).
- `refuse_seal` always raises (`PermissionError` / AC-12).
- No Odds network / no key use.
- No merge / deploy / Coming Soon OFF.
- No `NFL_ODDS_API_CARRIED_BOOKMAKERS` edit.
- Live capture Needs-Ryan. Do not pull live.

Proof JSON: `data/ops/nfl-w8-imv-package-t4450u/HARD_STOPS.json`.

## Remaining PAPER_GAPS

- H-1a / H-1c live Odds pull (Needs-Ryan).
- AC-1/2/8/10 seal, custodian receipt, baselines, grading.
- Webhook POST (hold fail-closes).
