# CI/CD Workflows

This directory contains GitHub Actions workflows for automated testing, building, and deployment.

## Workflows

### `ci.yml` - Continuous Integration

Runs on every push and pull request to `main` and `develop` branches.

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

**Note:** Deployment steps need to be configured based on your hosting platform (Vercel, Docker, etc.)

### `pr-check.yml` - Pull Request Checks

Runs on pull request events (opened, synchronized, reopened).

**Features:**
- Runs all quality checks
- Comments on PR with results
- Updates comment on subsequent pushes

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
