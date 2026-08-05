# Fantasy Draft Desk — Phase 2 Mock Draft Room

Interactive snake mock drafts on KosEdge rankings + FantasyPros ADP.

## Route

`/pro/nfl/fantasy/mock?scoring=half_ppr&teams=12&slot=1`

Linked from the Draft Desk hero (**Start Mock Draft**).

## Settings

| Setting | Options |
| --- | --- |
| Teams | 10 or 12 |
| Scoring | Standard / Half-PPR / PPR (reloads board) |
| Draft slot | 1…N |
| Rounds | 15 (starters + bench) |
| Roster | QB, 2 RB, 2 WR, TE, FLEX, DST, K + bench |

When the live board lacks K/DST (preseason fallback), those needs are skipped
rather than inventing players.

## Draft engine

- Snake order (`mock-draft-engine.ts`)
- Instant CPU ticks (~280ms) for speed — no live clock in this pass
- Human one-click draft from available list + value/need suggestion rails
- Full draft board + roster needs + recent picks

## CPU logic (tunable)

Personas rotate across CPU seats:

| Persona | Bias |
| --- | --- |
| `balanced` | ADP + need + value |
| `adp_follower` | Market ADP urgency |
| `value_hunter` | KosEdge value Δ (high-confidence only) |
| `need_first` | Fill starter holes / scarcity |

Each candidate scores:

1. **ADP urgency / reach penalty** — prefer players near the current pick; avoid
   huge reaches. Unmatched ADP uses model rank as a **soft CPU prior only**
   (never shown as market ADP).
2. **Value** — high-confidence `valueDelta` when present.
3. **Need** — starter holes, FLEX, late RB/WR depth; heavily penalize early
   QB2 / early K-DST.
4. **Scarcity** — few quality leftovers at the position.
5. **Stable noise** — small seeded jitter so mocks are not identical.

Weights live in `MOCK_CPU_WEIGHTS` (`mock-types.ts`).

## Post-draft

- Team grade + projected starter points (Phase 1 `teamGrade`)
- Strengths / weaknesses
- Notable values / reaches vs market ADP
- One-tap **New mock**

## Version awareness

Results footer shows scoring, slot, and `modelVersion` from the board rows.

## Limitations

- Mocks only — no Sleeper/ESPN/Yahoo sync, no auction, no Superflex/TEP, no
  multi-user lobbies, no dynasty.
- CPU is understandable/tunable, not a full game-theory solver.
- Preseason boards may omit K/DST.
- Available list shows top 60 filtered rows for mobile performance (search +
  position filters cover the rest of the pool).

## Key files

- `apps/web/app/(pro)/pro/nfl/fantasy/mock/page.tsx`
- `apps/web/components/pro/nfl/fantasy/FantasyMockDraftClient.tsx`
- `apps/web/lib/fantasy/mock-types.ts`
- `apps/web/lib/fantasy/mock-draft-engine.ts`
- `apps/web/lib/fantasy/mock-cpu.ts`
- `apps/web/lib/fantasy/mock-roster.ts`
