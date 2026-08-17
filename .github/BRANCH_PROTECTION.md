# Branch Protection Guidelines

## Production branch (`deploy-vercel`) — do this first

This is the subscription site. Configure GitHub → Settings → Branches (or Rulesets)
for **`deploy-vercel`**:

**Required status checks:**

- Production Gate / Web typecheck
- Production Gate / Web Next build (Vercel-identical)
- Production Gate / Model-service tests

**Restrictions:**

- Do not allow force pushes
- Do not allow deletions
- Require a pull request before merging (no direct pushes if the team can live with that)

Do **not** require the old “PR Checks” push run — that was a 0s false failure.

Optional after merge: watch **Production Smoke**. It is post-deploy (Vercel is async)
so it should not block the merge; it should page if www or Railway did not come up.

### Main Branch Protection

**Required Status Checks:**

- ✅ Lint & Type Check
- ✅ Test
- ✅ Build
- ✅ Format Check

**Required Reviews:**

- Require at least 1 approval
- Dismiss stale reviews when new commits are pushed
- Require review from code owners (if using CODEOWNERS)

**Restrictions:**

- Do not allow force pushes
- Do not allow deletions
- Require linear history (optional)

**Enforcements:**

- Require branches to be up to date before merging
- Require conversation resolution before merging

### Develop Branch Protection

**Required Status Checks:**

- ✅ Lint & Type Check
- ✅ Test
- ✅ Build

**Required Reviews:**

- Require at least 1 approval

**Restrictions:**

- Do not allow force pushes
- Do not allow deletions

## Branch Naming Conventions

- `main` - Production-ready code
- `develop` - Development branch
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Critical production fixes
- `release/*` - Release preparation

## Pull Request Process

1. Create feature branch from `develop`
2. Make changes and commit
3. Push branch and create PR
4. Wait for CI checks to pass
5. Get code review approval
6. Merge to `develop`
7. After testing, merge `develop` → `main`

## CODEOWNERS File

Create `.github/CODEOWNERS` to automatically request reviews:

```
# Global owners
* @your-username

# Frontend
/apps/web/ @frontend-team

# Backend
/apps/api/ @backend-team

# Infrastructure
/infra/ @devops-team
```
