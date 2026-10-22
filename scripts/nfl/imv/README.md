# IMV local runners (engineering, not certification)

Sealed Mac runners and the file-backed nflverse feature path. These scripts
**do not** write certification data into git. Do not commit snapshot
directories, scores, or SHA256SUMS from a live seal.

| File                                   | Role                                                                    |
| -------------------------------------- | ----------------------------------------------------------------------- |
| `nfl-imv-prestage-nflverse.sh`         | Separate fetch. Network ON. Writes files + sha + cutoff.                |
| `nfl-imv-feature-path-v2.md`           | v2 design (NOT APPROVED — builder was missing).                         |
| `nfl-imv-feature-path-v2.1.md`         | fd97f103 addendum: lagged window, pin, builder.                         |
| `nfl-imv-feature-path-v2.2.md`         | f9b25e81 addendum: §5.3 rebuild + X-gating.                             |
| `nfl-imv-feature-path-v2.3.md`         | ccecea74 addendum: P-1..P-5 + X-3 export.                               |
| `nfl-imv-v2.3-p-trace.md`              | P-1..P-5 + X-3 trace.                                                   |
| `nfl-imv-v2.4-c-trace.md`              | 47616a70 C-1..C-6 + returned runbook.                                   |
| `nfl-imv-parity-protocol-c57032db.md`  | c57032db PASS bar + 73815046 CSV reader + v3 SQL pin.                   |
| `PR_PROD_PARITY_EXPORT_v1.sql`         | Historical 27-col SELECT. Not the live reader bind.                     |
| `PR_PROD_PARITY_EXPORT_v3.sha256`      | Pin `b10d6cfd…`. File bytes live at `ops/platform/…_v3.sql`.            |
| `nfl-imv-deviation-register-t4149u.md` | Local vs prod 41 keys / strength / model (not a 2nd model).             |
| `nfl-imv-prod-export-spec-v2.3.md`     | Prod export query/columns/weeks for X-3.                                |
| `nfl-imv-prod-export-spec-v2.4.md`     | C-4 capture / data_as_of / query_sha.                                   |
| `nfl-imv-feature-path-v2.4.md`         | 47616a70 addendum: pins, cert tols, bundle.                             |
| `nfl-imv-mac-runbook-v2.3.md`          | One-page Mac commands + Desktop tar (P-4).                              |
| `nfl-imv-mac-runbook-v2.4.md`          | RETURNED: IMV outside BASE, box paths, no parquet tar.                  |
| `nfl-imv-feature-coverage-v2.md`       | 41-key sourced / unavailable / flag table.                              |
| `nfl-imv-v2.1-c-trace.md`              | C-1..C-8 trace.                                                         |
| `nfl-imv-v2.2-x-trace.md`              | X-1..X-9 trace (gating first).                                          |
| `nfl_imv_v21.py`                       | Shared v2.1 contracts (pin `05027146…`).                                |
| `nfl_imv_v22.py`                       | v2.2 contracts: §5.3, external pin, cap pair, 5g.                       |
| `nfl_imv_v23.py`                       | v2.3: helper stamps, lagged parity, P-1/P-2/P-5. **Frozen `fe66b374`.** |
| `nfl_imv_v24.py`                       | v2.4: C-1..C-6, c57032db cert bar. Does not edit v22/v23.               |
| `nfl-imv-feature-build-v2.3.sh`        | v2.3 Darwin builder. Both helper shas. OUT/store.                       |
| `nfl-imv-feature-build-v2.4.sh`        | v2.4 Darwin builder. C-5 pins. SHA256SUMS last.                         |
| `nfl-imv-sealed-v2.3.sh`               | v2.3 runner. PLUMBING-ONLY. W7 refused.                                 |
| `nfl-imv-sealed-v2.4.sh`               | v2.4 runner. IMV outside BASE. Bundle in seal.                          |

v2.4 is the 47616a70 response. Frozen: v22 `57a419b4…`, v23 `fe66b374…`.
IMV scripts live in a **sha-checked folder outside BASE**. Mac grade is
still **PLUMBING-ONLY** until cert parity PASSes. See the v2.4 runbook.

```bash
IMV=/var/tmp/nfl-imv-bundle-v24
IMV_FEATURE_STORE_SHA=$(cat /var/tmp/operator-pins/w6.sha256)
bash "$IMV/nfl-imv-sealed-v2.4.sh" \
  --base /abs/dedicated-b1d857d3-worktree \
  retrospective-w4w6
```

`LATEST` is a **symlink to the stamp directory**. If a host still has the v1
text pointer, v2 resolves `$(cat LATEST)/imv-manifest.tsv`.

Null model output forces BLOCKED. BLOCKED still seals. Reconstructions are
`RETROSPECTIVE`. n=2998 is retracted (`scripts/nfl/nfl_historical_eval_contract.py`).
