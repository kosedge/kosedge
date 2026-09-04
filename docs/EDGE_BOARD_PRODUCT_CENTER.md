# Edge Board Product Center (#4) — honesty slice

**Contract start:** the public daily decision center is **`/edge-board/{sport}`**.

## Canonical URL

| Surface                   | Role                                              |
| ------------------------- | ------------------------------------------------- |
| `/edge-board/[sport]`     | **Canonical** public Edge Board (decision center) |
| `/pro/{sport}/edge-board` | **308** → `/edge-board/{sport}` (query preserved) |
| `/pro/nfl/boards`         | **308** → `/edge-board/nfl`                       |

Internal nav (`sport-pro-nav`, desk cards) already links `/edge-board/{sport}` — do not reintroduce `/pro/.../edge-board` hrefs.

## Desk Edges demotion (follow-up)

| Surface                         | Role                                                                 |
| ------------------------------- | -------------------------------------------------------------------- |
| `/edge-board/{sport}`           | **Primary** decision CTA (green emphasis in sport subnav)            |
| `/pro/{sport}/edges`            | **Desk** surface — deep links stay live; **not** a dual primary CTA  |

**Choice:** demote desk Edges from the primary sport strip into **More tools** as **“Edges desk”**. Do **not** 308 `/pro/{sport}/edges` (Pro desk users still need that page). Confusing Edge Board aliases (`/pro/.../edge-board`, `/pro/nfl/boards`) already permanent-redirect to canonical.

## Tag quarantine (product surfaces)

Customer chrome is **PLAY / LEAN / PASS** only.

- Assemble may still carry engine `actionLabel` / `isBestBet` internals.
- Edge Board UI remaps via `displayActionLabel` + `toPublishActionLabel` — no Best Bet / BEST VALUE / WATCH / ALERT productization.
- **`point_grade` / `cover_grade` stripped** from customer `decision` blobs — can fork from `publishTag` (e.g. PASS publish + PLAY ladder). UI uses **publishTag / actionLabel only**.
- **CFB:** do not invent tags from edge when assemble omits `publishTag` (research-only / blank tag cells).
- No live PLAY band or threshold changes in this slice.

## Honesty stamps

- Board header + `MarketAsOfStamp` read **`linesAsOf`** from assemble.
- Blank / unparseable → “as-of unavailable” / “Market as-of unavailable”.
- Never mint “as of now” from the request clock.

## Assemble 10s honesty (follow-up)

- Past **`EDGE_BOARD_ASSEMBLE_HONESTY_MS` (10s)** while assemble is still pending: escalate from bare “Loading…” to honesty copy + `MarketAsOfStamp` (last good `linesAsOf` when known, else unavailable).
- Fetch stays alive until assemble returns or fails (cold ~16s can still succeed). Fail-closed on error — no invented rows.
- No odds rebuild · no PLAY threshold changes.
- Route `maxDuration = 30` / `UPSTREAM_TIMEOUT_MS.pageData` unchanged — UX only.

## Out of scope (other PRs)

Homepage redesign · odds/fair-lines rebuild · PLAY 2.5–7 band / CFB sit · Lab scorecard · mobile redesign.
