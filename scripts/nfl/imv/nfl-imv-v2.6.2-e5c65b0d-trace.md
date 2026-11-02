# v2.6.2 — e5c65b0d closures (runbook v2.4.4 + RD/P-2)

Frozen: v21–v27, three v2.4 shells, builder v2.4.1, runbooks through
v2.4.3, parent register `39561f48…`. No Mac run. No parity evidence.

| Item | Where |
| --- | --- |
| 1 ABORTED-PARTIAL | runbook §0: `$W4_PARTIAL` recorded in run report only; no edit/delete/seal/reuse; fresh OUT |
| 2 PRE_RETRO | CoS box-copy of Desktop manifest; STOP until `COS_BOX_MANIFEST_OK=1`; `sha256sum -c` vs `20261022T173338Z` (no `--ignore-missing`); `chmod -R a-w` |
| 3 no re-download | retro does not run §1 prestage/curl; W8 keeps own prestage on/after 2026-10-27 ET |
| 4 plumb2 ×7 | listed once, then repeated before W4/W5/W6/W8; STOP on fail |
| 5 register | `nfl-imv-deviation-register-rd-p2.md`: RD-1, RD-2, RD-3, P-2 |
| 6 L-1 / L-2 | every block `set -euo pipefail`; `SUMS_V25="$SRC/SHA256SUMS.v2.5"` |
| 7 pins | full sha `5d64a848…`; v27 `check-pins --sums --sums-v25`; exit 0 and `ok=true` |

P-2 logged. v27 frozen (no write of v26/v27/build-v2.4.1 into the store).
