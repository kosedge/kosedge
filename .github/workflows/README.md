# CI/CD Workflows

This directory contains GitHub Actions workflows for automated testing, building, and deployment.

## Workflows

### `production-gate.yml` — subscription ship bar

Runs on pull requests and pushes to **`deploy-vercel`**.

1. **Web typecheck**
2. **Web Next build** — same `apps/web` `pnpm run build` Vercel runs

If this is red, www did not ship. Do not merge.

### `production-smoke.yml` — live www + Railway

Runs after every push to `deploy-vercel`. Retries `/api/ping`, CFB desk routes
(reachability), Railway `/health`, and CFB engine status until they 200 (or the
window expires).

**Does not** assert CFB projections `N=10000` (Desk OS item D). That grain is
soak-only — see `cfb-projections-soak.yml`.

### `cfb-projections-soak.yml` — CFB N=10000 soak/slow

Nightly + `workflow_dispatch`. Same `N=10000` assertion, unchanged. Failure →
ticket; does **not** fail `deploy-vercel` / Desk OS ship bar.
Script: `scripts/ci/cfb-projections-n10000-soak.sh`.

### `ci.yml` - Continuous Integration

Runs on every push and pull request to `main` and `develop`. Do not hang
`deploy-vercel` on this workflow — it still carries historical lint/test debt.
The ship bar on `deploy-vercel` is **Production Gate**.

**Jobs:**

1. **Lint & Type Check** - Runs ESLint and TypeScript type checking
2. **Test** - Runs all tests and uploads coverage
3. **Build** - Builds the application to verify it compiles
4. **Format Check** - Verifies code formatting with Prettier

**Duration:** ~5-10 minutes

### `deploy.yml` - Deployment

Runs on pushes to `main` branch and version tags (`v*`).

**Jobs:**

1. **Deploy Web Application** - Builds and deploys the web app
2. **Deploy Model Service** - Builds/pushes model-service Docker image to GHCR and optionally triggers deploy hook

**Note:** Web deploy targets Vercel. Model-service deploy publishes immutable images and can trigger your runtime rollout via deploy hook.

### `pr-check.yml` - Pull Request Checks

Runs on pull request events (opened, synchronized, reopened). Push events are an
explicit no-op so GitHub does not paint a 0s red X on every merge to `deploy-vercel`.

**Features:**

- Runs all quality checks on the PR
- Comments on PR with results
- Updates comment on subsequent PR pushes

### `codeql.yml` - Security Analysis

Runs CodeQL security analysis on:

- Every push to `main`
- Pull requests to `main`
- Weekly schedule (Sundays)

**Languages:** JavaScript, TypeScript

## Required Secrets

For deployment, configure these secrets in GitHub Settings → Secrets:

- `DATABASE_URL` - Production database URL
- `AUTH_SECRET` - NextAuth secret
- `MODEL_SERVICE_URL` - Backend service URL
- `INTERNAL_API_SECRET` - Internal API secret
- `NEXT_PUBLIC_SENTRY_DSN` - Sentry DSN (optional)

### Platform-Specific Secrets

**Vercel:**

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

**Model Service Deploy:**

- `MODEL_SERVICE_DEPLOY_HOOK_URL` (optional) - Webhook URL for runtime deployment trigger after image publish

**Docker Hub:**

- `DOCKER_USERNAME`
- `DOCKER_PASSWORD`

## Caching

Workflows use caching for:

- pnpm dependencies (via `actions/setup-node`)
- Build artifacts (`.next`, `.turbo`)

## Status Badges

Add these badges to your README (update `YOUR_USERNAME`):

```markdown
[![CI](https://github.com/YOUR_USERNAME/kosedge/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/kosedge/actions/workflows/ci.yml)
[![CodeQL](https://github.com/YOUR_USERNAME/kosedge/actions/workflows/codeql.yml/badge.svg)](https://github.com/YOUR_USERNAME/kosedge/actions/workflows/codeql.yml)
```

## Local CI Testing

Run CI checks locally:

```bash
# Full CI pipeline
pnpm ci

# Individual checks
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm format:check
```

## Troubleshooting

### Workflow Fails

1. Check workflow logs in GitHub Actions tab
2. Run checks locally: `pnpm ci`
3. Verify environment variables are set
4. Check for dependency issues: `pnpm install`

### Tests Failing in CI

- Ensure test environment variables are set
- Check that test database is properly mocked
- Verify test timeout settings

### Build Failing

- Check Node.js version matches (20.x)
- Verify all environment variables are available
- Check for missing dependencies

## Customization

### Add New Jobs

Edit the workflow files to add:

- Additional test suites
- Deployment to multiple environments
- Notification steps (Slack, email, etc.)

### Change Triggers

Modify the `on:` section in workflow files:

```yaml
on:
  push:
    branches: [main, develop, feature/*]
  pull_request:
    branches: [main]
```

### Add Environments

Use GitHub Environments for staging/production:

```yaml
environment:
  name: production
  url: https://www.kosedge.com
```
