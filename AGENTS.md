# Agent instructions — Kos Edge

## Production branches (do not mix these up)

| Platform | Production / deploy branch | Notes |
|----------|---------------------------|--------|
| **Vercel** (`kosedge` web app) | **`deploy-vercel`** | Full Pro hubs, NFL boards, edge board UX. Root `apps/web`. |
| **Railway** (model-service) | `restore-working-ui` | FastAPI service in project `joyful-clarity`, service `kosedge`. |
| **GitHub** | source of truth | PRs + CI |

**Critical:** Never set the Vercel project Production Branch to `restore-working-ui`. That branch lacks the sport hub / NFL desk work that lives on `deploy-vercel`, and shipping it makes hubs look empty and “coming soon”.

## How they talk

1. **GitHub → Vercel**: auto-deploys; production from `deploy-vercel`.
2. **GitHub → Railway**: service `kosedge` in project `joyful-clarity`.
3. **Vercel → Railway**: shared model-service base URL + matching internal API secret (Cloud / Vercel env vars).

## Useful checks

```bash
curl -sS https://www.kosedge.com/api/ping
# Model service: GET /health and /health/db on the Railway public URL
```
