# NFL survivor — planner error + still slow (2026-08-21)

P0 follow-up to `nfl-survivor-load-fix-20260821.md` / PR #275. Fast path landed, but users still waited, then saw a **red Planner error** card.

## Capture (www, 2026-08-21)

| Surface | Observation |
|---------|-------------|
| UI copy | Heading **Planner error** (red card). Body was typically the 25s abort / 504 warming string: *Engine warming — rankings timed out. Retry in a few seconds; the planner shell stays usable.* (or BFF: *Engine warming — survivor rankings timed out…*) |
| Request | `POST /api/nfl/season-engine/survivor/plan` body `{ picks, nSims: 50, topN: 32, includeDiagnostics: false }` |
| Warm engine | **200**, `n_sims=50`, 18 weeks, **~0.3–0.7s**, **~459 KB** |
| Empty slate | Succeeds (`already_used: []` / `picks: {}`) when Railway is warm |
| Failure class | Not a 400 validation miss. Not suggest-paths (off load). Client **AbortController 25s** and BFF **504** were painted as **Planner error**. Parse of a truncated 459 KB body would also land in the same red card. |

Live page after #275: shell + `n=50` + “Load suggested paths” is deployed. Stored picks `1:SEA,2:ATL` plan **200**. The error was the **timeout/soft-fail wrapper**, not a broken empty-slate contract on a warm worker.

## Root cause

1. **#275 treated every `json.error` / abort as “Planner error”.** Timeouts and 502s used the same red card as bye / duplicate-team validation. After a long spin, users landed on a dead error state even when the engine was only cold or the download was slow.
2. **Interactive JSON was still research-sized (~459 KB).** Each of 18×32 ranked picks included `future_week_win_rates`; `notes` copied the full universe cal dump even with `include_diagnostics: false`. Slow networks / cold Vercel serialization hit the 25s client abort → red card.

## Fix

- Engine: `include_diagnostics=false` omits `future_week_win_rates` and the cal `notes` dump (keeps short depth/cache notes).
- BFF + mapper: `slimInteractiveSurvivorPlan` strips those fields (and diagnostics) so a fat Railway response cannot reach the browser.
- Client: 504 / 502 / abort / incomplete JSON → amber **Engine warming** + one automatic retry + Retry button. **Planner error** reserved for 400 validation (duplicate team, bye, unknown).
- Load contract unchanged: shell first, `defaultWeek` without fair-lines, plan `n=50` after hydrate, suggest-paths on button only, lock while ranks pending.

## Smoke

- Cold `/pro/nfl/survivor?mode=planner`: no red Planner error; weeks visible immediately.
- Ranks fill on n=50, or amber warming with Retry — never a blank hang then error card.
- Lock a team → path updates.
- Fantasy / playing-time untouched.
