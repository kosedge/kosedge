# NFL Weekly Ops Cadence (REG season)

**Audience:** operators running the subscription desk  
**Product gate:** YELLOW · **PLAY policy:** `spread_play_v2_cap7`  
**Freeze:** see `nfl-factor-freeze-aug25.md` (hard date **2026-08-25**)

---

## Cadence (Tue–Wed after Monday night)

| Step | Command / endpoint | Notes |
| --- | --- | --- |
| 1. Ingest + harden | `SEASON=2026 WEEK=N ./scripts/nfl/run-weekly-inseason-update.sh` | Owned nflverse → features → baselines → props |
| 2. Projection actuals | Included in step 1; or `write_projection_actuals.py --season 2026 --from-db` | Hub Actual column; live API: `GET /nfl/ops/projection-actuals?season=2026` |
| 3. Market sims | Existing launch-hardening / fair-lines refresh | Keep Visual Crossing on Railway |
| 3b. Injury → KEI | `./scripts/nfl/run-injury-kei-reprice.sh --window friday_final` (Thu midweek / Fri 16:00 ET / gameday −90m) | SoT → Active PR → KEI; Model frozen. Config: `data/ops/nfl-injury-kei-cadence/config.json` |
| 4. Paper book | `PYTHONPATH=services/model-service:. .venv/bin/python scripts/nfl/paper_book_tracker.py --season 2026` | Locked thresholds — **do not retune** |
| 5. Publish check | Spot-check `/pro/nfl/fair-lines` + Edge Board | Selective PLAY only; totals PASS; PRE = INFO |
| 6. Deploy web (if JSON artifact changed) | Push `deploy-vercel` | Live actuals API covers most weeks without redeploy |

Task enqueue pattern (Railway model-service):

```bash
curl -X POST "$MODEL_SERVICE_URL/nfl/ops/write-projection-actuals?season=2026"
curl -X POST "$MODEL_SERVICE_URL/api/jobs/run-nfl-weekly-resilience-cycle?season=2026&week=N"
```

---

## Early season (W1–W4)

- Factor **D** (`error_regime`) applies a decaying uncertainty boost (widen stdev / cut confidence).
- **No 50% market blend.** Point estimates stay model-led; size down via confidence.
- Do not widen PLAY bands or re-enable E/B/A.

---

## Do not

- Re-densify 2020–23 odds wastefully.
- Flip `TOTAL_PLAY_ENABLED` or props stake without a new green holdout.
- Mix PRE ATS into season paper / gates.
- Force-push `main`.
