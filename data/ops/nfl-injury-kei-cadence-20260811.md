# NFL Kickoff Injury → KEI Cadence — 2026-08-11

Branch: `feat/nfl-injury-kei-cadence` → `deploy-vercel` (+ Railway model-service).

Depends on: KEI = model + handicap; SoT depth; Active PR / injury shocks (#198 Power Ratings desk).

## Doctrine

| Layer | Midweek / Friday / inactives |
|-------|------------------------------|
| **Model research fair** | Frozen (`line_role=handicap` preserves `model_markets`) |
| **Model PR** | Frozen (Tuesday shrink only) |
| **SoT depth / availability** | Updated |
| **Active PR** | Refreshed from injury-aware indices (+ Ryan Adj) |
| **KEI** | Repriced |
| **Edge tags / play-to** | Recompute vs **Current** after KEI moves (Tag = KEI vs Current only) |

## Report windows (ET) — configurable

Source: `data/ops/nfl-injury-kei-cadence/config.json`  
Module defaults: `services/model-service/src/services/nfl_injury_kei_cadence.py`

| Window | When | Action |
|--------|------|--------|
| Midweek | Thu 16:00 ET | Ingest → SoT → KEI for **affected** games |
| Friday final | Fri 16:00 ET | Full slate reprice |
| Gameday inactives | ~90 min before kickoff | Final KEI stamp; lock pre-kick KEI for CLV |
| Post-game | After final | No KEI change for played game; Tuesday PR path only |

**What happens Friday at 4 ET?**  
Ingest injury report → diff SoT → `snapshot_id` → Active PR refresh + full-slate KEI reprice (`line_role=handicap`) → refresh Edge tags vs Current → ops line. Model research fair / Model PR unchanged.

```bash
./scripts/nfl/run-injury-kei-reprice.sh --explain-friday
```

## Status → participation (config)

| Status | Participation |
|--------|---------------|
| Out | 0% |
| Doubtful | ~25% (or out) |
| Questionable | ~50% / scenario for high-impact |
| Limited | minor (~85%) |
| Full / healthy | expected (100%) |

QB1 Out/Doubtful: **force KEI reprice** + confidence ↓ / ALERT bias.  
Log status changes that move KEI ≥ **0.25** pts spread or ≥ **0.5** total (`log_thresholds` in config).

## Pipeline per window

```
Ingest → Diff SoT → snapshot_id → Active PR + KEI (affected | full Friday)
      → refresh tags → ops line
No-diff → heartbeat no-op
```

## Job / script

| Piece | Path |
|-------|------|
| Config | `data/ops/nfl-injury-kei-cadence/config.json` |
| Module | `services/model-service/src/services/nfl_injury_kei_cadence.py` |
| Job | `scripts/nfl/injury_kei_reprice.py` |
| Wrapper | `scripts/nfl/run-injury-kei-reprice.sh` |
| Runbook | `docs/runbooks/nfl-kickoff-injury-kei.md` |
| Tests | `services/model-service/tests/test_nfl_injury_kei_cadence.py` |

```bash
# Preseason readiness — QB1 Out → KEI/tag move; restore → back
./scripts/nfl/run-injury-kei-reprice.sh --window friday_final --fixture --dry-run

# Midweek heartbeat (no SoT payload → no-op)
./scripts/nfl/run-injury-kei-reprice.sh --window midweek --dry-run

# Operator SoT + games JSON
SEASON=2026 WEEK=1 ./scripts/nfl/run-injury-kei-reprice.sh \
  --window friday_final --dry-run \
  --sot-before /path/before.json --sot-after /path/after.json --games /path/games.json
```

## Manual SoT until feed live

Official injury feed is thin in preseason. **SoT pack edits remain manual** until the live feed is wired (`manual_sot_until_feed_live: true` in config). Cadence job accepts `--sot-before` / `--sot-after` JSON diffs from the depth pack / daily intel checklist.

Checklist: `scripts/nfl/daily_roster_injury_intel_checklist.md` (step: → KEI reprice).

## Fixture test results (2026-08-11)

Local: `16 passed` (`test_nfl_injury_kei_cadence.py` + `test_nfl_model_handicap.py`).

Dry-run fixture (`--window friday_final --fixture --dry-run`):

| Step | KEI | Model | Tag |
|------|-----|-------|-----|
| QB1 Out | −6.5 → **−3.0** | −7.0 unchanged | PLAY → **PASS** (STRONG PLAY → PASS) |
| QB1 restore | −3.0 → **−6.5** | unchanged | snaps back |

Midweek empty SoT → `HEARTBEAT no-diff` no-op.

## Does not

- Rewrite Model PR from injuries
- Beat-writer NLP
- Props inactive board
- Change tag thresholds (`nfl_tag_policy`)
