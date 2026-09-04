# Edge Board Product Center (#4) — honesty slice

**Contract start:** the public daily decision center is **`/edge-board/{sport}`**.

## Canonical URL

| Surface                   | Role                                              |
| ------------------------- | ------------------------------------------------- |
| `/edge-board/[sport]`     | **Canonical** public Edge Board (decision center) |
| `/pro/{sport}/edge-board` | **308** → `/edge-board/{sport}` (query preserved) |
| `/pro/nfl/boards`         | **308** → `/edge-board/nfl`                       |

Internal nav (`sport-pro-nav`, desk cards) already links `/edge-board/{sport}` — do not reintroduce `/pro/.../edge-board` hrefs.

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

## Out of scope (other PRs)

Homepage redesign · odds/fair-lines rebuild · PLAY 2.5–7 band / CFB sit · Lab scorecard · mobile redesign.
