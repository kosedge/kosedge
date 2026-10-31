# NCAAM holdout package handoff prep — 2026-09-06

**No scoring / unseal / model change / merge / deployment.**  
**Upload not executed. Bucket locking not included.**

## Preserved inventory hash

```
5590fc12bff8edf3425927a85e88ced31ddff1ff47c76270d9f3798a6ef54440
```

Preserved in `handoff_prep_20260906.receipt.json`. **Not re-verified** on this Linux cloud host (staged package absent here).

## Status

| Gate | Value |
| --- | --- |
| EXTERNAL DRIVE SAFE TO EJECT | **no** |
| PRIMARY CLOUD COPY VERIFIED | **no** |
| INDEPENDENT BACKUP VERIFIED | **no** |
| MAC REQUIRED FOR FURTHER WORK | **yes** |

Reason Mac is required: self-containment check (no symlinks/runtime deps on `/Volumes/KosEdgeData` with external archive unavailable), package size measurement, and Ryan Cloudflare/R2 account metadata all require Darwin + local Mac state. Private worker `3c358d2d-51c7-5c49-9a19-6f9fbccd8be6` (`Ryan's MacBook Air`) was connected/idle, but this session could not route onto it.

Independent backup destination remains **UNDECIDED** — not configured, not protected.

## Cloudflare / R2 (metadata only; no credentials shown)

Checked: cloud agent secrets, Railway `model-service` env names, Vercel `kosedge` env names, local `~/.aws` / wrangler — **no R2/Cloudflare keys present**.

Ryan-owned Cloudflare account with R2 enabled: **not confirmed** from cloud-accessible config. Confirm on Mac (`wrangler whoami` / dashboard) without pasting secrets.

## Primary bucket create + upload — AWAITING APPROVAL

Do **not** execute until Ryan approves.

| Field | Value |
| --- | --- |
| Account | Ryan-owned Cloudflare account (**confirm R2 enabled on Mac**) |
| Bucket | `kosedge-ncaam-holdout-primary` (**private**; create if absent) |
| Prefix | `handoff/ncaam_holdout_2024_25/inventory-5590fc12bff8edf3425927a85e88ced31ddff1ff47c76270d9f3798a6ef54440/` |
| Upload size | **TBD on Mac** after staged package path confirmed |
| Credential scopes | R2 Object Read & Write, **bucket-scoped only**; no Account Admin; no Workers/DNS |
| Bucket locking | **Separate** approval (not this op) |
| Optional URI shape | `NCAAM_HOLDOUT_HANDOFF_URI=s3://kosedge-ncaam-holdout-primary/<prefix>` (NFL DR / R2-compatible) |

### Exact ops (after approval)

1. Create private bucket `kosedge-ncaam-holdout-primary` if missing.
2. Issue bucket-scoped R2 read/write token (no admin).
3. Upload staged package + `inventory.sha256` containing the preserved hash above + this receipt.
4. Do **not** enable object-lock / bucket-lock in this step.

### Post-upload independent verify (separate cloud agent)

1. Download package from primary prefix.
2. Verify inventory against  
   `5590fc12bff8edf3425927a85e88ced31ddff1ff47c76270d9f3798a6ef54440`.
3. Reproduce **1,532-event** eligibility result with **zero mismatches**.
4. Still no scoring / unseal / model / merge / deploy.

## Next action

Re-dispatch this handoff verification onto  
`privateWorkerId=3c358d2d-51c7-5c49-9a19-6f9fbccd8be6`  
(or run locally on Ryan’s Mac). After Mac self-containment passes, set EXTERNAL DRIVE SAFE TO EJECT = yes, fill upload size, confirm Cloudflare account, then seek upload approval.
