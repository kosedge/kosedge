# IMV local runners (engineering, not certification)

Sealed Mac runners and the file-backed nflverse feature path. These scripts
**do not** write certification data into git. Do not commit snapshot
directories, scores, or SHA256SUMS from a live seal.

| File                                   | Role                                                        |
| -------------------------------------- | ----------------------------------------------------------- |
| `nfl-imv-prestage-nflverse.sh`         | Separate fetch. Network ON. Writes files + sha + cutoff.    |
| `nfl-imv-feature-path-v2.md`           | v2 design (NOT APPROVED — builder was missing).             |
| `nfl-imv-feature-path-v2.1.md`         | fd97f103 addendum: lagged window, pin, builder.             |
| `nfl-imv-feature-path-v2.2.md`         | f9b25e81 addendum: §5.3 rebuild + X-gating.                 |
| `nfl-imv-feature-path-v2.3.md`         | ccecea74 addendum: P-1..P-5 + X-3 export.                   |
| `nfl-imv-v2.3-p-trace.md`              | P-1..P-5 + X-3 trace.                                       |
| `nfl-imv-deviation-register-t4149u.md` | Local vs prod 41 keys / strength / model (not a 2nd model). |
| `nfl-imv-prod-export-spec-v2.3.md`     | Prod export query/columns/weeks for X-3.                    |
| `nfl-imv-mac-runbook-v2.3.md`          | One-page Mac commands + Desktop tar (P-4).                  |
| `nfl-imv-feature-coverage-v2.md`       | 41-key sourced / unavailable / flag table.                  |
| `nfl-imv-v2.1-c-trace.md`              | C-1..C-8 trace.                                             |
| `nfl-imv-v2.2-x-trace.md`              | X-1..X-9 trace (gating first).                              |
| `nfl_imv_v21.py`                       | Shared v2.1 contracts (pin `05027146…`).                    |
| `nfl_imv_v22.py`                       | v2.2 contracts: §5.3, external pin, cap pair, 5g.           |
| `nfl_imv_v23.py`                       | v2.3: helper stamps, lagged parity, P-1/P-2/P-5.            |
| `nfl-imv-feature-build-v2.3.sh`        | v2.3 Darwin builder. Both helper shas. OUT/store.           |
| `nfl-imv-sealed-v2.3.sh`               | v2.3 runner. PLUMBING-ONLY. W7 refused.                     |

v2.3 is the ccecea74 response. Mac grade is **PLUMBING-ONLY**. Sha from
**outside** the store; runner reads `OUT/store`. See the Mac runbook.

```bash
IMV_FEATURE_STORE_SHA=$(cat /var/tmp/operator-pins/w6.sha256)
bash scripts/nfl/imv/nfl-imv-sealed-v2.3.sh \
  --base /abs/dedicated-b1d857d3-worktree \
  retrospective-w4w6
```

`LATEST` is a **symlink to the stamp directory**. If a host still has the v1
text pointer, v2 resolves `$(cat LATEST)/imv-manifest.tsv`.

Null model output forces BLOCKED. BLOCKED still seals. Reconstructions are
`RETROSPECTIVE`. n=2998 is retracted (`scripts/nfl/nfl_historical_eval_contract.py`).
