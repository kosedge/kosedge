# Worker K/DST artifact hygiene — 2026-08-21

**Why K=0 on Railway while www shows Butker:** `railway up services/model-service --path-as-root` Docker-copies only that folder. Repo-root `data/ops/artifacts/nfl-kdst-season-2026.json` never entered `/app`. Remat then had no named kickers (`nfl_dp_rosters` K empty on worker DB). DST still filled from `nfl_dp_team_defense_weekly` (32 teams, no names required).

**Fix:** vendor the JSON at `services/model-service/data/ops/artifacts/` (image path `/app/data/ops/artifacts/…`). Loader walks up from the module instead of assuming `parents[4]` is the monorepo root. CI restages via `scripts/nfl/stage_nfl_kdst_into_model_service.sh`. Confirm: `GET /nfl/ops/kdst-publish-status?season=2026` then remat.

After deploy:

```
GET  /nfl/ops/kdst-publish-status?season=2026   # status=ready, kickers=32
POST /nfl/ops/materialize-fantasy-draft-rankings?season=2026
GET  /nfl/fantasy/draft-rankings?season=2026&scoring_profile=half_ppr&position=K&limit=50
```
