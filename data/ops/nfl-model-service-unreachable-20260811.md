# Ops note — NFL model-service “unreachable” (KEI Lines) — 2026-08-11

## Symptom

Production KEI Lines (`/pro/nfl/fair-lines`) showed:

> Model service is temporarily unreachable. Retry shortly — local fallbacks may still load below.

Edge Board / Game Boxes / Season Model could still look healthy because they hit other endpoints.

## Evidence

| Probe | Result |
|-------|--------|
| `GET https://model-service-production-e253.up.railway.app/health` | **200** `{"status":"ok","service":"kosedge"}` |
| `GET …/health/db` | **200** connected |
| `GET …/nfl/season-engine/status` | **200** |
| `GET …/mlb/fair-lines` | **200** |
| `GET …/nfl/fair-lines` | **500** plain text `Internal Server Error` |

Railway logs (`brave-art` / `model-service`):

```text
File "/app/src/routes/nfl.py", line 3664, in nfl_fair_lines
    season_run = _load_nfl_web_active_run()
File "/app/src/routes/nfl.py", line 3871, in _load_nfl_web_active_run
    Path(__file__).resolve().parents[4]
IndexError: 4
```

Odds API pull succeeded immediately before the crash (`[ODDS_API] request succeeded`), so this was not a cold start, wrong `MODEL_SERVICE_URL`, or network partition.

## Root cause

Truth Layer lineage pointer load (`_load_nfl_web_active_run`) assumed monorepo layout:

`services/model-service/src/routes/nfl.py` → `parents[4]` = repo root → `data/ops/nfl-web-launch-bundle.json`.

Railway deploys with `railway up services/model-service --path-as-root`, so the file lives at `/app/src/routes/nfl.py` and only has parents through `/`. Indexing `parents[4]` raises `IndexError` **after** the fair-lines SQL/odds work completed, turning a successful board build into HTTP 500.

Web BFF (`apps/web/lib/nfl-fair-lines.ts`) maps non-OK upstream to `Model service returned 500.` → KEI Lines unreachable banner (`modelUnreachableCopy`).

Introduced with Truth Layer / lineage wiring on `deploy-vercel` (active tip ~`fed0eda8` lineage badge era); process and DB were healthy the whole time.

## Fix

1. Resolve launch-bundle candidates with bounded `len(parents)` checks (same pattern as MLB unused-holdout path-as-root guards).
2. Wrap lineage load at the fair-lines return site so pointer failures never 500 the board (fallback lineage uses `model_version`).
3. Redeploy model-service from `deploy-vercel` via GitHub Actions `Deploy Railway model-service` (path: `services/model-service/**`).

## Verify

```bash
BASE=https://model-service-production-e253.up.railway.app
curl -sS -o /dev/null -w "%{http_code}\n" "$BASE/health"
curl -sS -w "\n%{http_code} %{time_total}s\n" \
  "$BASE/nfl/fair-lines?season=2026&days_ahead=200&include_past_days=0" | tail -5
# Expect HTTP 200 + non-zero count / lines for Week 1 REG

# Product smoke
open https://www.kosedge.com/pro/nfl/fair-lines
open https://www.kosedge.com/edge-board/nfl
```

### Post-fix smoke (2026-08-11 ~16:18–16:20Z)

| Check | Result |
|-------|--------|
| `/nfl/fair-lines?season=2026&days_ahead=200` | **200** — count 241, **16 Week 1** rows |
| `/health`, `/health/db` | **200** |
| `/nfl/season-engine/game-boxes?…demo=true` | **200** |
| www KEI Lines hard load | **Week 1 · 16 games**, no unreachable banner |
| PR | https://github.com/kosedge/kosedge/pull/187 merged → `deploy-vercel` (`1201c7e0`); Railway workflow `31511558608` success |

## Non-goals / not changed

- Fantasy expert copy
- Vercel `MODEL_SERVICE_URL` / secret (correct; service was reachable)
- Railway project realign (already on `brave-art` model-service from `deploy-vercel` pushes)
