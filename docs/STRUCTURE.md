# Repository structure

Canonical places for code and config. Use these so imports and paths stay predictable.

## Root (orchestration only)

- `package.json` – workspace scripts, no app code
- `pnpm-workspace.yaml` – workspace packages
- `turbo.json` – build orchestration
- `docs/` – shared docs (e.g. this file)
- `scripts/` – repo-level scripts
- `.github/` – CI/CD

No `components/`, `public/`, or app-specific config at root. Each app owns its own.

## Apps

- **`apps/web/`** – Next.js app
  - **Components:** `apps/web/components/` (import as `@/components/...`)
  - **Public assets:** `apps/web/public/`
  - **Config:** `apps/web/next.config.ts`, `apps/web/tsconfig.json`, `apps/web/vercel.json`
  - Alias: `@/` → `apps/web/`

## Packages (shared libs)

- **`packages/contracts`** – shared types/contracts for web + model service
- Add `packages/ui` only if you need shared UI across multiple apps.

## Services

- **`services/`** – backends (e.g. model service), independent of the web app.

## Infra

- **`infra/`** – Docker, env templates, infra config (outside pnpm workspace).

## Import rules (web)

- Prefer **direct imports**: `import X from "@/components/X"` (no barrels for app-critical UI).
- Keep `@/` pointing at `apps/web` (see `apps/web/tsconfig.json`).

## CI

- **Lint, typecheck, test, build** run on push/PR (`.github/workflows/ci.yml`).
- **Format check** enforced.
- **CodeQL** security scan on main and PRs.
