# CURSOR PREVERIFY — t5075u G2 DIAGNOSTIC

**CERT=0 · NFL NO-GO · DRAFT #686 family @ 43b5a622. STOP for Alex pre-compute verify.**

CoS ORDER **2ce38509** · OWNER_CLEAR **00159454** under **d7e0a6bc**.
Joint consume (not a new planning cycle). Diagnostic **not executed**.

## Step 1 — pins re-hashed on this checkout

| Prefix | Live sha256 | Path | Status |
|---|---|---|---|
| `5076421e` | `5076421ef1fba943df9c1e8eeaefede4f7a7e30a36ae2ed792a7f2bc295c4e27` | `joint/artifacts/Q2S_JOINT_W7W17.json` | OK |
| `ce6b1244` | `ce6b1244895df065ea8428851261becbb8012c7379d6184770116a7dfbcb0fc5` | `joint/artifacts/Q2S_JOINT_DRAWS_W7W17.npz` | OK |
| `32e97434` | `32e9743483259f2a9c13efe9826e550f610a6068995fad3bc9fdb6b1698d5d43` | `phase4/artifacts/IF_MUS_W7W17.json` | OK |
| `55d8c8bc` | `55d8c8bc2155705c04e9ef88ba5637ea491bf5c245e4f7bb8fcfb3523f9ec925` | `phase4/artifacts/q2s_rows_w7w17.json` | OK |
| `50bda875` | `50bda875daa8bf1aadd56dd0a3bc19f1bb52dafe42b6a9c921a5816c7d7dc081` | `pins/outcomes_2013_2022_score_only.csv` | OK checksum-only |
| `013d270a` | `013d270a815511ebe6a77dc559eb2e2df47c47670c9dfc6b1f2a0f0193a46331` | `phase4/artifacts/LOOK_CONSUMED.json` | OK checksum-only |

Cited tips (not files on this tree): LOOK **8bea4ca3** · ACCEPT **bd51eb3e**.
Q2 EVAL **03a4dd90** CLOSED. No LOOK invocation.

## Step 2 — frozen manifest (bind this)

| Item | Value |
|---|---|
| `g2_diagnostic/FROZEN_MANIFEST.json` | **d4f24894** / `d4f24894f62a5dd27df874178f13c256efdcb01aa8afac9ff64e3c085a0d3a4c` |
| Protocol | `g2-diagnostic-t5075u-v1` + `PROTOCOL.md` |
| Identities | **141** 2017 REG W7–17 from joint/q2s/IF alignment (outcomes not parsed) |
| Status | **PREVERIFY** · `executed=false` |
| Alex GO present | **false** |

Alex GO, when issued, must bind `binds_frozen_manifest_sha256` =
`d4f24894f62a5dd27df874178f13c256efdcb01aa8afac9ff64e3c085a0d3a4c`
and `authorizes_g2_diagnostic_execute: true`. Until then `run.py` refuses
and does not parse `50bda875`.

## Implementation (research tree only)

`research/q2s_w7w17_t5044u/g2_diagnostic/` — metrics, 141-identity guards,
log-loss clip N=4000, CRPS, 50/80/90 coverage, UNAVAILABLE for IF
distribution / point-candidate total+WP. 34 COND + J14 NOT_EMITTED
re-checked via the existing joint consume handoff. No forecast rewrite.

Tests: **32/32 OK** (synthetic + pin checksums + guards). No real outcome
join in tests. Default runner → `G2_REFUSE: Alex pre-compute GO absent`.

## Not done (by design)

- ONE diagnostic execution — **held for Alex GO**
- `CURSOR_DONE` with results sha8 — **not written**
- Merge / deploy / C10 / cert / LOOK / Q2 EVAL / IF-draw regen / retune
