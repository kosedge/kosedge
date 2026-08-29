# Desk OS item D — CFB N=10000 enterprise flake quarantine (2026-08-29)

**Book off limits. No pack/scanner edits.**

## Problem

`Production Smoke` on every `deploy-vercel` push asserted
`/pro/cfb/projections` contains `N=10000`. Intermittent CFB page grain painted
deploy-vercel red while Railway health + the rest of the CFB suite were fine —
blocking NFL Desk OS confidence without an NFL fault.

## Fix

| Path | N=10000? |
|------|----------|
| `production-smoke.yml` → `scripts/ci/production-smoke.sh` | **No** (projections URL still 200-checked) |
| `cfb-projections-soak.yml` → `scripts/ci/cfb-projections-n10000-soak.sh` | **Yes** (N unchanged) |

Soak triggers: nightly cron + `workflow_dispatch`. Marker: `soak/slow` in the
soak script (not `pytest.skip`). Failure → ticket; does not fail Desk OS /
deploy-vercel.

## Comment in soak script

States why it moved and links the soak workflow. N is not retuned.
