# Edge Board canonical market identity (2026-09-10)

**PR target:** `deploy-vercel` (do not merge from agent — CoS / Ryan merges)  
**Follow-up to:** PR #517 (merged @ `61132895`) — **new PR, do not reopen 517**  
**Incident:** INC-2026-09-10 — live Odds `totals` 3.5 vs FG fairTotal 9 painted PLAY Over (Rays@ATL). Raw Odds: `totals_1st_5_innings` **ABSENT** (not F5). Featured `totals` had no period; commence was past.

#516 Overview/Stats polish stays **BLOCKED** until truth recert is GREEN after this PR + audit.  
#515 mobile redesign is out of scope.

## Locked invariant

```
Quote:  Q = (event, sport, market, period, side, line, price, book, timestamp)
Model:  T = (event, sport, market, period, side)
Legal comparison ONLY when T ≡ Q_target BEFORE Edge = f(Model, Market).
```

Missing / ambiguous identity → **FAIL CLOSED**.  
Book + timestamp stay on the selected decision quote through calc/render.  
**No numerical-range heuristics** (do not infer F5 because a total “looks” like 3.5).

## Identity schema

| Token | Meaning | Comparable to FG pregame T? |
| ----- | ------- | --------------------------- |
| `fg` / `fg_pregame` / `full_game` / … | Certified full-game **pregame** | Yes |
| `fg_live` / `live` | Featured FG family, **in-play remaining** | **No** |
| `1st5` / `f5` | First 5 innings (`totals_1st_5_innings`, …) | **No** |
| (absent) | Unknown | **No** (MLB always; other sports only when also in-play) |

T for KEI / model-service `fair_fg_*` totals is **`fg`** (full-game pregame).

## What restores MLB pregame tags

1. Odds ingest (`odds-api.ts`) stamps `period` from **Odds rules**, not line size:
   - Featured key `totals` + commence **after** quote as-of → `fg`
   - Featured key `totals` + commenced (in-play) → `fg_live`
   - `totals_1st_5_innings` (if it ever appears) → `1st5`; **never** fills the FG total slot
2. KEI merge stamps `modelPeriod=fg` (T). Q.period is not overwritten.
3. #517 gate kept and evolved: certified FG pregame + `T.period ≡ Q.period` → compare; missing / live / non-FG → fail closed. In-play still fails even if someone stamps `fg`.

Until ingest stamps `fg` on a pregame featured total, MLB totals stay fail-closed (same as #517). After this PR, **pregame FG** can tag again; **live remaining** (Rays@ATL 3.5 vs 9) cannot.

## #517 kill switch (not weakened)

- MLB totals with no period still fail closed (pregame or live).
- In-play still fail closed (even `period=fg`).
- Non-FG period (`1st5`, `alternate`, …) still fail closed.
- No “3.5 looks low” clamp — a certified FG pregame 3.5 vs fair 9 still compares.

## Verify `/edge-board/mlb`

1. **Live / commenced** game with featured `totals` ~2.5–3.5 and KEI ~9: quote may still paint, **no PLAY / LEAN / edge** on the total. Row should carry `period=fg_live` (or missing → fail closed).
2. **Pregame** game with featured `totals` and KEI FG total: `period=fg`, `modelPeriod=fg`, tags follow existing MLB total cuts (not the #517 blanket mute).
3. If `totals_1st_5_innings` is the only totals key: FG total slot stays empty / untagged. Never borrow F5 by event id.
4. Do **not** recert #516 polish on this change alone. Truth recert GREEN = this identity + a separate audit.

## Out of scope

- ML pts→pp label
- KEI fairTotal quantization
- #516 polish / #515 mobile
- Line Curve / alt-line lake
- Merging to production
