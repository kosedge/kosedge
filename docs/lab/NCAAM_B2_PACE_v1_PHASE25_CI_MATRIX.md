# B2-PACE-v1 Phase 2.5 — Canonical CI matrix

Generated during enterprise hardening. No merge/deploy.

## Authoritative CI surfaces (deploy-vercel PR)

| Check | Source | Command | Relevance to PR #490 |
|---|---|---|---|
| Web Python boundary | `pr-check.yml` / `ci.yml` | `pnpm check:web-python-boundary` | **Required** |
| Format (Prettier) | `pr-check.yml` / `ci.yml` | `pnpm format:check` (or changed-files) | Docs/md/json may be in scope |
| Lint / typecheck | `ci.yml` (main/develop) | `pnpm lint` + `pnpm typecheck` | Not deploy-vercel ship bar |
| Pipeline tests | `ci.yml` `pipeline-tests` | `pip install -r apps/web/requirements-pipeline.txt` then `python -m pytest apps/web/tests_pipeline -v` | Lab Python surface |
| Production Gate | `production-gate.yml` | Web typecheck + Next build | Ship bar into deploy-vercel |

## Tooling

| Tool | In declared deps? | Result |
|---|---|---|
| Ruff | **No** (`apps/web/requirements-pipeline.txt` has no ruff) | **INFRASTRUCTURE GAP** — do not install unpinned global Ruff to greenwash |
| pytest / polars | Yes | Used |
| Black / mypy (Lab) | Not in workflows | N/A |

## Local results (Phase 2.5)

| Command | Exit | Notes |
|---|---|---|
| `pnpm check:web-python-boundary` | 0 | After allowlisting new Lab files |
| `pytest …/test_ncaam_lab_b2_pace_v1.py …/test_ncaam_lab_fair.py …/test_ncaam_lab_scorecard.py …/test_ncaam_lab_results_attach.py -q` | 0 | 40 passed |
| Densify version assertion | fixed | Expect densify → v1.2 (was stale v1.1). No scorecard rewrite |
| Ruff | not run | Absent from declared deps |

## Versions used

- pytest 9.1.1, polars 1.44.1, numpy 2.4.4, scipy 1.18.1
- Python 3.12.3

## Merge gate

Do not recommend merge until boundary + focused Lab pipeline tests + Production Gate are green. Ruff is not a declared gate; claiming Ruff-green requires a separate infra PR to pin it.
