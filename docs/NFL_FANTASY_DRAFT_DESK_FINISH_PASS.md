# Fantasy Draft Desk — Finish Pass (Premium Ready)

Ready-for-use checklist and known limitations after the finish pass.

## Surfaces

| Path | Role |
| ---- | ---- |
| `/pro/nfl/fantasy` | Rankings · Value · Builder tab |
| `/pro/nfl/fantasy/builder` | Dedicated builder |
| `/pro/nfl/fantasy/player/[playerId]` | Player detail |
| `/pro/nfl/fantasy/mock` | Snake mock (CPU others + auto-pick to end) |

## Ready-for-use checklist

| # | Flow | Pass / Fail |
| - | ---- | ----------- |
| 1 | Open rankings; see ADP source + freshness; Model vs ADP coherent for STD / Half / PPR | ☐ |
| 2 | Value board: true values (`\|Δ\| ≥ 8`) scannable; unmatched stay off board / show — | ☐ |
| 3 | Player card opens quickly (desk sticky + detail page); expert note reads KosEdge | ☐ |
| 4 | Rankings → Builder → Mock nav preserves scoring; no dead-end CTAs | ☐ |
| 5 | Build a private roster; grade updates; “Practice in Mock” obvious | ☐ |
| 6 | Start mock (CPU others only); pick manually; sticky needs usable on phone | ☐ |
| 7 | Auto-pick to end still available; finishes including user seats | ☐ |
| 8 | Late-round CPU does not stack QB2 once a starter QB is rostered | ☐ |
| 9 | K/DST unavailable (preseason): clear messaging; slots skipped; grade not dinged | ☐ |
| 10 | Post-draft grade readable; New mock / Builder / Desk CTAs work | ☐ |
| 11 | Mobile: rankings cards clean; draft history readable; tap targets ≥ ~40px | ☐ |
| 12 | Methods collapsed; no “Phase 1 / Not broken / prototype” copy in UI | ☐ |

## Known limitations (honest)

- No live Sleeper / ESPN league sync
- Snake redraft only — no auction, Superflex, or dynasty
- Preseason skill board may omit K/DST; mocks skip those slots
- Value Δ only on high-confidence same-format ADP matches
- No live injury feed; risk flags are depth/projection signals
- Expert blurbs are template-driven (not LLM)
- Builder roster is session scratchpad (not synced into mock seats)

## Finish-pass changes (summary)

- Shared **Rankings / Builder / Mock** nav (`FantasyDeskNav`)
- Value board: true-values filter, muted fair rows, ADP freshness on tab
- Mock: explicit **CPU others only** mode copy; K/DST empty messaging; stronger late QB2 suppress
- Copy polish: remove Phase 1 / “not broken” / “no CPU mock yet”
- Methods & limitations collapsed by default; limitations text updated for mocks
