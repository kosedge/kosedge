# Agent instructions — Kos Edge

**NFL tag lock:** `/NFL_SPREAD_PLAY_LOCKED.md` (Ryan Kos, 2026-09-03) — spread PLAY only in `spread_play_v2_cap7`; totals/prop PLAY sat; publish≡action after remap.

**NFL player value dictionary:** `/NFL_PLAYER_VALUE_DICTIONARY.md` — pts of KEI vs replacement (not WAR/DVOA); v1 live keystones only; v2 research log-only.

## Production contract (one branch, three platforms)

Daily subscription ships go through **`deploy-vercel` only**. Do not mix branches.

| Platform                                                 | Production branch            | How it ships                                                          |
| -------------------------------------------------------- | ---------------------------- | --------------------------------------------------------------------- |
| **Vercel** project `kosedge` (www.kosedge.com)           | **`deploy-vercel`**          | Git integration; Root Directory `apps/web`.                           |
| **Railway** model-service (`brave-art`, api/worker/beat) | **`deploy-vercel`**          | `.github/workflows/deploy-railway.yml` on model-service path changes. |
| **GitHub**                                               | PRs **into `deploy-vercel`** | Production Gate must be green before merge.                           |

**Critical:** Never set the Vercel Production Branch to `restore-working-ui`. That branch is a thinner UI shell. Shipping it makes hubs look empty / “coming soon”.

`restore-working-ui` is **not** production. If GitHub’s default branch is still that name, do not treat it as live. Open and merge PRs against `deploy-vercel`.

Ignore **`kosedge-vercel-push`** — leftover second Vercel Git project. Production aliases live on `kosedge` only.

## How they talk

1. **GitHub → Vercel**: push/merge to `deploy-vercel` auto-deploys project `kosedge`.
2. **GitHub → Railway**: same branch, `deploy-railway.yml` (`RAILWAY_TOKEN`).
3. **Vercel → Railway**: `MODEL_SERVICE_URL` + matching `INTERNAL_API_SECRET`.

## Required checks (do not merge red)

- **Production Gate** — web typecheck + Next build (same command as Vercel). That is the www ship bar.
- **Production Smoke** — after the merge, www + Railway `/health` and CFB status must 200.
- **PR Checks** — quality on the pull_request only. A push run is a no-op (not a deploy failure).

## Useful checks

```bash
curl -sS https://www.kosedge.com/api/ping
curl -sS https://www.kosedge.com/pro/cfb/slate
# Model service
curl -sS https://model-service-production-e253.up.railway.app/health
curl -sS "https://model-service-production-e253.up.railway.app/cfb/season-engine/status?season=2026&as_of_week=1&demo=true"
# Local full smoke
bash scripts/ci/production-smoke.sh
```
