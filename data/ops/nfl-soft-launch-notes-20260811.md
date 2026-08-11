# NFL Soft-Launch Notes (user-facing) — 2026-08-11

## What shipped

Public desk primer at **`/pro/nfl/launch-notes`** (Model vs KEI vs Tag, Week 1–2, Edge Board, Fantasy incl. Guillotine + Sleepers, lineage, responsibility).

## Links

- `/pro/nfl/overview` — header CTA + inline “Soft Launch Notes”
- `/edge-board/nfl` — methods line footer link

## Access

Allowlisted in `apps/web/lib/pro-public-paths.ts` + `app/(pro)/pro/layout.tsx` via `x-pathname`. Anonymous users can open launch notes even when `OPEN_ACCESS_PREVIEW=false`.

## Smoke

```bash
# With paywall preview off in env, should still 200 (not redirect to sign-in)
curl -sI http://127.0.0.1:3000/pro/nfl/launch-notes | head -n 5
```
