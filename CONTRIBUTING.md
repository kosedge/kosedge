# Contributing to Kos Edge

## Quick Start

1. **Fork & clone**
2. **Install:** `pnpm install`
3. **Set up env:** `cp apps/web/.env.example apps/web/.env.local` (edit as needed)
4. **Run:** `pnpm dev:web:3000`

## Code Standards

- **Lint:** `pnpm lint` must pass
- **Type check:** `pnpm typecheck` must pass
- **Tests:** `pnpm test` must pass
- **Format:** `pnpm format:check` — use `pnpm format` to fix

## CI

Push/PR triggers: lint, typecheck, test, build, format check, CodeQL.

See [docs/STRUCTURE.md](docs/STRUCTURE.md) for layout and import rules.
