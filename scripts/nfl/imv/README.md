# IMV local runners (engineering, not certification)

Sealed Mac runners and the file-backed nflverse feature path. These scripts
**do not** write certification data into git. Do not commit snapshot
directories, scores, or SHA256SUMS from a live seal.

| File                             | Role                                                      |
| -------------------------------- | --------------------------------------------------------- |
| `nfl-imv-prestage-nflverse.sh`   | Separate fetch. Network ON. Writes files + sha + cutoff.  |
| `nfl-imv-feature-path-v2.md`     | v2 design (NOT APPROVED — builder was missing).           |
| `nfl-imv-feature-path-v2.1.md`   | fd97f103 addendum: lagged window, pin, builder.           |
| `nfl-imv-feature-path-v2.2.md`   | f9b25e81 addendum: §5.3 rebuild + X-gating.               |
| `nfl-imv-feature-coverage-v2.md` | 41-key sourced / unavailable / flag table.                |
| `nfl-imv-v2.1-c-trace.md`        | C-1..C-8 trace.                                           |
| `nfl-imv-v2.2-x-trace.md`        | X-1..X-9 trace (gating first).                            |
| `nfl_imv_v21.py`                 | Shared v2.1 contracts + builder/parity.                   |
| `nfl_imv_v22.py`                 | v2.2 contracts: §5.3, external pin, cap pair, 5g, parity. |
| `nfl-imv-feature-build-v2.1.sh`  | v2.1 builder (superseded for Mac runs).                   |
| `nfl-imv-feature-build-v2.2.sh`  | v2.2 Darwin deny + EPERM + refuse existing OUT.           |
| `nfl-imv-sealed-v2.sh`           | v2 runner (PASS WITH CONDITIONS).                         |
| `nfl-imv-sealed-v2.1.sh`         | v2.1 Darwin + deny. C-1..C-8. W7 refused.                 |
| `nfl-imv-sealed-v2.2.sh`         | v2.2 runner. X-1 no fallback. W7 refused.                 |

v2.2 is the f9b25e81 response. **Do not run the builder, seal, or W7** until
IMV code-checks it. After that, sha must come from **outside** the store:

```bash
IMV_FEATURE_STORE_SHA=$(cat /var/tmp/operator-pins/FEATURE_STORE.sha256)
bash scripts/nfl/imv/nfl-imv-sealed-v2.2.sh \
  --base /abs/dedicated-b1d857d3-worktree \
  retrospective-w4w6
```

`LATEST` is a **symlink to the stamp directory**. If a host still has the v1
text pointer, v2 resolves `$(cat LATEST)/imv-manifest.tsv`.

Null model output forces BLOCKED. BLOCKED still seals. Reconstructions are
`RETROSPECTIVE`. n=2998 is retracted (`scripts/nfl/nfl_historical_eval_contract.py`).
