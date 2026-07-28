# Branch Protection Guidelines

## Recommended Branch Protection Rules

Configure these in GitHub Settings → Branches → Branch protection rules

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
