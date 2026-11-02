# PRE-REGISTER — Full-engine rerun (memo sha8 `f4c61237`)

**Status:** DRAFT PRE-REGISTER. **Not executed.**  
**Ticket:** Ryan t4422u  
**Cited memo:** IMV `f4c61237` (8-char prefix only; full SHA256 **not in this public repo**)  
**Also cites:** `78f5ee7e` C-2 (n=2998 re-earn); frozen criteria `4f832c91` + `132ee26c` under `6a3aa3d9`  
**Owner to accept:** IMV. Engineering files the command; IMV runs / grades.  
**Hard stop:** 2024–25 holdout stays sealed. No holdout-tuning. No protected files.

This is the pre-register the t4359u spec required ("Full-engine FAIL stands until a pre-registered rerun (`f4c61237`)"). Filing it does **not** flip FAIL → PASS.

---

## What will be run (when IMV accepts)

Pin:

| Pin | Value |
|-----|--------|
| Git | `deploy-vercel` tip **or** this draft PR head (record SHA at run time; do not silently move) |
| Framework | `nfl-handicap-core-v3.1` / `LOCKED_SCORING` |
| Model | `nfl-v1.5-matchup-sim` |
| Overlays | OFF (`force_overlays_off=true`, `unlock_overlays=false`) |
| Totals PLAY | `TOTAL_PLAY_ENABLED=false` |
| Public | `NFL_EDGE_BOARD_PUBLIC_ENABLED=false` |
| Record class for any 2026 W4–W7 reconstruction | **RETROSPECTIVE** (no stored pregame snapshot on this tree) |
| Seed (if blended holdout is in scope later) | blend bootstrap **7** (`full_pipeline_holdout_backtest.py`) — **not authorized here** |

Authorized now (engineering, unused of holdout):

```bash
cd services/model-service
PYTHONPATH=. python3 -m pytest \
  tests/test_nfl_simulator.py \
  tests/test_nfl_regression_decompose.py \
  tests/test_nfl_564_remediation.py \
  tests/test_nfl_enterprise_gates.py \
  tests/test_nfl_efficiency_backbone.py \
  tests/test_nfl_week_cap_bind.py \
  --tb=line -rs

bash scripts/nfl/nfl-fair-lines-production-cert-smoke.sh
```

**Not authorized by this filing (IMV / Ryan only):**

- `scripts/nfl/full_pipeline_holdout_backtest.py` against 2024–25 or any unused window
- `scripts/nfl/imv/nfl-imv-sealed-*.sh` W4–W6 seals
- Any n=2998 reconstruction
- Injury overlay ON / NR-1 archive
- Coming Soon OFF / cert bind / deploy

---

## Pass / fail for this pre-register (engineering only)

| Check | PASS if | FAIL if |
|-------|---------|---------|
| FE-1 identity | live `framework_version == nfl-handicap-core-v3.1` | pin drifted or test deleted |
| FE-2 week-1 pack | `test_week1_pack_aligned_indices_stay_dog_side_of_market` collected and asserted (spread `> -1.5` / dog-side) | skipped, deleted, or import-blocked |
| Cert smoke | 43/43 and public flags false | any public/market/stake true or cert bound |
| T-08 | local Postgres proof run **or** still labeled NOT EVIDENCED | skip claimed as PASS |
| Predictive gates | still report committed RED/GREEN honestly | floors edited or artifact rewritten to GREEN |

IMV may reject this pre-register if the memo `f4c61237` required a different unused window or a sealed feature-store pin. **Do not invent that window here.**

---

## Mac vs cloud

| Step | Cloud VM (this run) | Mac / local |
|------|---------------------|-------------|
| § engineering pytest | **55 passed / 1 skipped** | same IDs expected |
| Cert smoke | **43/43** | same |
| T-08 Postgres proof | SKIP / NOT EVIDENCED | required for T-08 close |
| IMV sealed W4–W6 | scripts not on `deploy-vercel` (PR #609) | Mac runbook v2.4.10; no cert data in git |
| Memo `f4c61237` body | **absent** | IMV private box |

---

## Explicit non-claims

- This filing is **not** a certification PASS.
- This filing is **not** a holdout result.
- n=2998 is **not** re-earned.
- Enterprise overall remains **RED**.
- Fair Lines PRODUCTION-CERT remains **NO CLEAR** / unbound.
