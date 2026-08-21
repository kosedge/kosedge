# NFL survivor load — fast path (2026-08-21)

Planner **features and scoring unchanged**. Default load is light; path math still runs.

## Before / after (feel)

| | Before | After |
|--|--------|--------|
| RSC | Wait on status + fair-lines matchups | Shell paints; status in Suspense (4s timeout → “engine warming”) |
| First weeks UI | Hidden until 2000-sim plan (475 KB) | 18-week shell immediately; chips fill when ranks land |
| n on page load | 2000 plan **and** 2000 suggest-paths | **50** plan only (low-depth badge) |
| Suggest-paths | Auto on hydrate | Button: Load suggested paths |
| Empty plan | Resim / re-rank every visit | TTL cache (engine ~10 min, Next ~5 min), keyed by universe fingerprint + n |
| Hang | Spinner until Railway 180s budget | 25s interactive timeout + honest warming copy |

Warm Railway n=50 plan: **~0.4s**. Cached empty plan: skip Railway. Cold 2k is no longer the default page view.

**2026-08-21 follow-up:** the 25s abort was still a red **Planner error** card, and n=50 JSON was still ~459 KB. See `nfl-survivor-planner-error-20260821.md`.

## Knobs

- Web: `NFL_INTERACTIVE_N_SURVIVOR_PATHS = 50` (`nfl-season-engine-format.ts`)
- Research: `NFL_DEFAULT_N_SURVIVOR_PATHS = 2000` / CLI 50k–100k unchanged
- `UPSTREAM_TIMEOUT_MS.seasonEngineInteractive = 25_000`

## Smoke

- Cold `/pro/nfl/survivor?mode=planner`: week cards visible immediately; ranks in a few seconds
- Lock a team → remaining weeks update without full-page death (existing debounce, n=50)
- Mobile sticky path strip unchanged
- Fantasy / Overview / Edge Board not in this diff
