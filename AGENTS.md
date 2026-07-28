# Agent instructions — Kos Edge

## Cursor Cloud specific instructions

Use these when running as a Cursor Cloud agent (web/mobile/desktop Cloud).

### Platform roles

| Platform | Role |
|----------|------|
| **GitHub** (`kosedge/kosedge`) | Source of truth; PRs, Actions CI, deploy triggers |
| **Vercel** | Hosts the Next.js web app (`apps/web`) |
| **Railway** | Hosts the FastAPI model service (`services/model-service`) |

### How they talk to each other

1. **GitHub → Vercel**: Vercel GitHub integration auto-deploys on push/PR (already connected; see GitHub Environments named `Preview` / `Production`).
2. **GitHub → Railway**: Connected as service `kosedge` in project `joyful-clarity` (`1873f728-9c20-4350-9dbe-802153ecc835`). Root `/services/model-service`, config `/services/model-service/railway.toml`. Public URL: `https://kosedge-production.up.railway.app`.
3. **Vercel → Railway**: Set `MODEL_SERVICE_URL` on Vercel to `https://kosedge-production.up.railway.app`. Set matching `INTERNAL_API_SECRET` on both.
4. **Cursor Cloud → all three**: GitHub is available via `gh` + git. For Vercel/Railway CLIs, add secrets below so `scripts/setup-cloud-tooling.sh` installs them on boot.

### Required Cursor Cloud secrets

Add at [Cloud Agents dashboard → Secrets](https://cursor.com/dashboard/cloud-agents):

| Secret | Purpose |
|--------|---------|
| `VERCEL_TOKEN` | Deploy/inspect Vercel from cloud agents |
| `VERCEL_ORG_ID` | Optional; speeds `vercel` project targeting |
| `VERCEL_PROJECT_ID` | Optional; speeds `vercel` project targeting |
| `RAILWAY_TOKEN` | Deploy/inspect Railway from cloud agents (project token for `joyful-clarity` works for `railway api` / deploy; account token needed for `railway whoami` / trigger edits) |
| `RAILWAY_SERVICE_ID` | Optional; model-service is `117410e8-bcc0-4f51-8631-5f1785c8e2d1` |
| `DATABASE_URL` | App/DB work in cloud |
| `AUTH_SECRET` | Auth-related local runs |
| `MODEL_SERVICE_URL` | Point web at Railway (or local) model service |
| `INTERNAL_API_SECRET` | Shared secret between web and model service |

### Vercel MCP

Interactive Vercel MCP login only works in the **Cursor desktop IDE**. After you authenticate once on desktop, cloud agents can use the linked Vercel MCP tools. From phone-only cloud runs, prefer the Vercel CLI with `VERCEL_TOKEN`.

### Useful commands

```bash
# Web
pnpm install --frozen-lockfile
pnpm --filter @kosedge/web lint
pnpm --filter @kosedge/web test run
pnpm build:web

# Deploy (requires secrets)
vercel --prod --token "$VERCEL_TOKEN"
railway up --service "${RAILWAY_SERVICE_ID:-}" --ci

# GitHub
gh pr view
gh run list --limit 5
```

### Do not

- Commit `.env`, tokens, or `AUTH_SECRET` values
- Double-deploy Vercel from Actions if the Vercel GitHub app is already deploying the same branch
- Change production env vars without confirming with the user
