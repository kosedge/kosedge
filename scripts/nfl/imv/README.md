# IMV local runners (engineering, not certification)

Sealed Mac runners and the file-backed nflverse feature path. These scripts
**do not** write certification data into git. Do not commit snapshot
directories, scores, or SHA256SUMS from a live seal.

| File | Role |
| --- | --- |
| `nfl-imv-prestage-nflverse.sh` | Separate fetch. Network ON. Writes files + sha + cutoff. |
| `nfl-imv-feature-path-v2.md` | Approved local architecture (no silent defaults). |
| `nfl-imv-sealed-v2.sh` | Darwin + network deny. `--base` dedicated worktree. W7 refused. |

v2 usage (Ryan's Mac, dedicated BASE, not `~/kosedge`):

```bash
bash scripts/nfl/imv/nfl-imv-prestage-nflverse.sh
bash scripts/nfl/imv/nfl-imv-sealed-v2.sh \
  --base /abs/dedicated-b1d857d3-worktree \
  retrospective-w4w6
```

`LATEST` is a **symlink to the stamp directory**. If a host still has the v1
text pointer, v2 resolves `$(cat LATEST)/imv-manifest.tsv`.

Null model output forces BLOCKED. BLOCKED still seals. Reconstructions are
`RETROSPECTIVE`. n=2998 is retracted (`scripts/nfl/nfl_historical_eval_contract.py`).
