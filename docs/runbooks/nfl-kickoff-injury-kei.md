# NFL Kickoff Injury → KEI Cadence runbook

**Config:** `data/ops/nfl-injury-kei-cadence/config.json`  
**Module:** `services/model-service/src/services/nfl_injury_kei_cadence.py`  
**Script:** `scripts/nfl/injury_kei_reprice.py`  
**Wrapper:** `scripts/nfl/run-injury-kei-reprice.sh`

## Windows (US/Eastern)

| Window | Default | Scope |
|--------|---------|-------|
| `midweek` | Thu **16:00** ET | Affected games only |
| `friday_final` | Fri **16:00** ET | Full slate |
| `gameday_inactives` | ~**90 min** before kickoff | That game; lock pre-kick KEI for CLV |
| `post_game` | After final | No KEI change; Tuesday PR only |

```bash
./scripts/nfl/run-injury-kei-reprice.sh --explain-friday
```

## Doctrine

- Update: SoT depth, Active PR, KEI handicap, Edge tags (KEI vs Current).
- Do **not** overwrite Model research fair or Model PR midweek.
- Use `line_role=handicap` + prior `model_markets`.

## Preseason / dry-run

```bash
# QB1 Out → restore fixture (no DB required)
./scripts/nfl/run-injury-kei-reprice.sh --window friday_final --fixture --dry-run

# Heartbeat with empty SoT
./scripts/nfl/run-injury-kei-reprice.sh --window midweek --dry-run
```

## In-season (manual SoT until feed live)

1. Diff official report into SoT pack (daily intel checklist) **or** pass JSON:
   - `--sot-before` / `--sot-after` player status lists
   - `--games` with `home_team`, `away_team`, `kei_*`, `model_*`, `market_spread_home`
2. Run the window:

```bash
SEASON=2026 WEEK=1 ./scripts/nfl/run-injury-kei-reprice.sh \
  --window friday_final --dry-run \
  --sot-before data/ops/nfl-injury-kei-cadence/example-sot-before.json \
  --sot-after data/ops/nfl-injury-kei-cadence/example-sot-after.json \
  --games data/ops/nfl-injury-kei-cadence/example-games.json
```

3. On write mode (omit `--dry-run`), latest log lands at  
   `data/ops/nfl-injury-kei-cadence/latest-run.json`.
4. Publish path: fair-lines / Edge Board already regrade from KEI vs Current on next pull.
5. Active PR: job refreshes injury-aware Active while freezing Tuesday `model_pr` from  
   `data/ops/nfl-power-ratings-desk/latest.json` when present.

## QB1 rules

- Out / Doubtful → force KEI reprice, confidence ↓, ALERT bias.
- Log moves ≥ 0.25 spread pts or ≥ 0.5 total pts.

## Railway / Vercel

- Model-service (Railway): ship this branch with the cadence module + job.
- Web (Vercel `deploy-vercel`): no tag-threshold changes; boards consume updated KEI.
