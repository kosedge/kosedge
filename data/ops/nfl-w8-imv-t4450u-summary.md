# W8 prospective capture — IMV ops summary (t4450u)

**Authority:** Ryan t4450u (decision sha8 `20ea635f`) — Post-Merge Execution.  
**ACCEPT:** #634–#636 / receipt `6685ba74`.  
**PR:** https://github.com/kosedge/kosedge/pull/640 (**DRAFT** — do not merge).  
**NFL NO-GO / Coming Soon ON.** Not a seal-ack. `CURSOR_CANNOT_SEAL_ACK`.

This is the **single ops-facing summary**. The reproducible deposit is
`data/ops/nfl-w8-imv-package-t4450u/`.

## Proof tip + CI

| Field | Value |
| --- | --- |
| Proof tip SHA | `ae7624f706380abde2c3740f8c9800e935a5696a` |
| Branch | `cursor/nfl-w8-prospective-capture-ef3e` |
| Base | `deploy-vercel` `bfc89f57` |
| PR Checks | **GREEN** run **40521208974** — https://github.com/kosedge/kosedge/actions/runs/40521208974 |
| PR Quality Checks job | **GREEN** **122248486585** (named step `W8 prospective capture unit tests`: **25 passed**) |
| Production Gate | run **40521210121** — https://github.com/kosedge/kosedge/actions/runs/40521210121 — Web typecheck GREEN; Next build not #640-scoped |
| Prior RED (closed) | tip `fb38b5f5` PR Checks **40520636740** — Prettier on `synthetic_w8_reg_game.json` only |

A later docs-only receipt commit may move HEAD. Green IDs above belong to the proof tip.

## Pytest (reproducible)

- Count: **25** passed (local + CI W8 step).
- Command: `bash scripts/ci/run-nfl-w8-capture-tests.sh`
- Or: `cd services/model-service && PYTHONPATH=. python3 -m pytest tests/test_nfl_w8_capture.py -q`

## Package paths

| What | Path |
| --- | --- |
| This summary | `data/ops/nfl-w8-imv-t4450u-summary.md` |
| Package index | `data/ops/nfl-w8-imv-package-t4450u/INDEX.md` |
| File list | `data/ops/nfl-w8-imv-package-t4450u/FILELIST.txt` |
| Inventory hashes | `data/ops/nfl-w8-imv-package-t4450u/INVENTORY.SHA256SUMS` |
| Hard-stop proof | `data/ops/nfl-w8-imv-package-t4450u/HARD_STOPS.json` |
| Bundle hash-chain | `data/ops/nfl-w8-imv-package-t4450u/evidence.jsonl` |
| Bundle SHA256SUMS | `data/ops/nfl-w8-imv-package-t4450u/SHA256SUMS` |
| Spec-to-code | `data/ops/nfl-w8-prospective-capture-spec-to-code-t4445u.md` |
| Capture module | `services/model-service/src/services/nfl_w8_capture/` |
| Unit tests | `services/model-service/tests/test_nfl_w8_capture.py` |

## Closed vs stubbed

**Closed (t4450u items 1–4 + Prettier):**

1. Scheduler: beat `nfl-w8-capture-pre-kickoff-tick` → `src.tasks.run_nfl_w8_capture_tick` (`*/2`, queue `nfl_market`). Never fetches Odds API.
2. Alerts: `alerts.deliver_alert` — chained `alerts.jsonl`; `NFL_W8_ALERTS_ENABLED` default off; hold → `hold_blocked` (no webhook POST).
3. Immutable evidence: `store.BundleStore` hash-chain + SHA256SUMS. **Not** prediction seal-ack.
4. CI safeguards: `pr-check.yml` NFL list + named W8 pytest step; Prettier fixture formatted.

**Still hard (proved in HARD_STOPS.json):**

- `refuse_odds_fetch` always raises `OddsApiHoldError`.
- `refuse_seal` always raises `PermissionError` (AC-12).
- No Odds network / no key use.
- No merge / deploy / Coming Soon OFF.
- No `NFL_ODDS_API_CARRIED_BOOKMAKERS` edit.

**Remaining PAPER_GAPS (Needs-Ryan / stubbed):**

- H-1a / H-1c live Odds pull including circa.
- AC-1/2/8/10 seal, custodian receipt, baselines, grading.
- Webhook POST (hold fail-closes).
