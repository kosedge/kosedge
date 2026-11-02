# t5178u M0 — how Worker B wires `#664` validate on `deploy-vercel` base

CERT=0 · DRAFT · product lineage only · **not** a research tree · **not** a disconnected demo helper

Worker B #706 inventory is correct: `nfl_hhl1_capture/*` is **ABSENT** on `deploy-vercel` @ `f5e3bb58`. The attach path is the `#664` Git commit, not a reimplementation.

## Classification

| Pin | Class | Full SHA |
|---|---|---|
| `#664` tip `7abf65a2` | **Git commit** (OPEN DRAFT) | `7abf65a2c85708cc6d4a1cd2b4d9643a4612084a` |

`7abf65a2` is a **Git commit**. It is not a CoS receipt and not a packet digest.

## What A already bound on this product-lineage branch

Branch `cursor/t5178u-wfix-a-fixture-assembly-c003` is cut from `f5e3bb58`. A path-checked out **only** the `#664` capture package (byte-identical blobs) plus its synthetic plumbing test:

```
git checkout 7abf65a2 -- \
  services/model-service/src/services/nfl_hhl1_capture/__init__.py \
  services/model-service/src/services/nfl_hhl1_capture/constants.py \
  services/model-service/src/services/nfl_hhl1_capture/gates.py \
  services/model-service/src/services/nfl_hhl1_capture/identity.py \
  services/model-service/src/services/nfl_hhl1_capture/schema.py \
  services/model-service/src/services/nfl_hhl1_capture/validate.py \
  services/model-service/tests/test_nfl_hhl1_capture_plumbing.py
```

Blob identity vs `7abf65a2` (verified):

| Path | blob SHA match |
|---|---|
| `…/nfl_hhl1_capture/validate.py` | YES `a8cd6054…` |
| `…/nfl_hhl1_capture/schema.py` | YES `0c7c1bf8…` |
| `…/nfl_hhl1_capture/__init__.py` | YES `2e68d602…` |
| `…/nfl_hhl1_capture/constants.py` | YES `82ed5a3f…` |
| `…/nfl_hhl1_capture/gates.py` | YES `40ca6848…` |
| `…/nfl_hhl1_capture/identity.py` | YES `666547f4…` |
| `tests/test_nfl_hhl1_capture_plumbing.py` | YES `f8e4d4e2…` |

**Not** brought from `#664` (do not merge that PR): celery/odds/auth/main.py, fair-lines route edits, receipts, workflow.

## How B attaches the same validate on B's `deploy-vercel` branch

B stays on `cursor/t5178u-wfixb-consumer-a875` (base `f5e3bb58`). Do **one** of these; they are equivalent byte sources.

### Preferred: same Git commit A used

```
git fetch origin pull/664/head
git checkout 7abf65a2 -- \
  services/model-service/src/services/nfl_hhl1_capture \
  services/model-service/tests/test_nfl_hhl1_capture_plumbing.py
```

Confirm: `git rev-parse HEAD:services/model-service/src/services/nfl_hhl1_capture/validate.py` equals `a8cd60546968b30770ab2d1e05251d3512d90b23`.

### Alternate: path-checkout from this M0 tip (same blobs)

After this PR is fetched, path-checkout the seven files above from the M0 tip SHA recorded in `data/ops/t5178u-m0-receipt.md`. Do not merge A's W-FIX-A assembly unless Cos says so. B only needs the `#664` package + the shared contract files:

- `services/model-service/src/services/nfl_fixture_assembly/contract.py` (SoT)
- `apps/web/lib/nfl-fixture-assembly-contract.ts` (TS mirror)
- `data/ops/t5178u-m0-shared-contract.md`

## Import seam B must use (product package, not a helper)

```python
from src.services.nfl_hhl1_capture.validate import (
    reject_market_fields,
    validate_l1_batch,
    validate_l1_candidate,
)
from src.services.nfl_fixture_assembly.contract import (
    FIXTURE_CHANNEL,
    FixtureEligibilityResult,
    # ALLOW_FIXTURE is fixture-channel-only (Alex X1)
)
```

TS consumers:

```ts
import {
  FIXTURE_CHANNEL,
  FIXTURE_ELIGIBILITY_RESULTS,
  FIXTURE_CONTRACT_ID,
} from "@/lib/nfl-fixture-assembly-contract";
```

## Forbidden attach paths

- Sparse research tree / missing-`nfl_simulator.py` hunt
- Reimplementing `validate_l1_candidate` in a demo helper
- Copying NFL into `FAIR_LINES_HONESTY_SPORTS`
- Treating `NFL_EDGE_BOARD_INTERNAL=1` as an `ALLOW_FIXTURE` production upgrade
- Merging all of `#664` (odds/celery/auth)
- Reopening R5 (`#701` `455a8e43` is reference only)
