# Architecture Boundary Policy

This repo is a monorepo with clear runtime boundaries:

- `apps/web`: Next.js frontend and web APIs.
- `services/*`: backend services and long-running jobs.
- `packages/*`: shared contracts and reusable libraries.

## Current policy (enforced in CI)

`apps/web` currently contains legacy Python data/model scripts. To prevent further drift:

- CI runs `pnpm check:web-python-boundary`.
- The command compares tracked `apps/web/**/*.py` files against
  `policies/web-python-allowlist.txt`.
- Any *new* Python file under `apps/web` fails CI until reviewed and allowlisted.
- `apps/web/package.json` is not allowed to execute Python commands.
- Root `package.json` is not allowed to call Python files directly from `apps/web`.

This freezes architecture drift while migration happens.

## Migration target

Move Python ingestion/pipeline/model logic to `services/`:

- `services/pipeline` (or `services/model-service`) owns Python execution.
- `apps/web` becomes consumer-only (HTTP/API/file artifacts), not execution host.
- Keep `apps/web` wrappers only during transition.

## Current transition state

- Python execution entrypoints have been moved to `services/pipeline` workspace scripts.
- `apps/web` still contains legacy Python source files while migration is completed file-by-file.

## Why this matters

- Single source of truth per runtime.
- Lower deploy risk (web deploys do not accidentally drag pipeline behavior).
- Clear ownership and faster onboarding.

