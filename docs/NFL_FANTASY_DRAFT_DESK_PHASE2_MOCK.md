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
- **Auto-pick to end** — finishes remaining seats with the same CPU logic and
  lands on the post-draft grade
- Full draft board (desktop) + compact recent-pick feed (mobile)
- Sticky mobile needs/roster strip while on the clock

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

## Round 1 CPU (post-hotfix)

1QB structure is enforced even when model VOR creates huge QB “value” vs ADP:

- Soft need for first QB in R1–R2
- Value/rank weights dampened for QBs through ~R5
- Stronger penalties against QB2+ until mid/late rounds

Stress test: elite model QBs with ADP 55–85 must not flood Round 1
(`mock-r1-cpu.test.ts` expects ≤1 R1 QB on that board).

## Limitations / remaining UX gaps

- Mocks only — no Sleeper/ESPN/Yahoo sync, no auction, no Superflex/TEP, no
  multi-user lobbies, no dynasty.
- CPU is understandable/tunable, not a full game-theory solver.
- Preseason boards may omit K/DST.
- Available list shows top 60 filtered rows for mobile performance (search +
  position filters cover the rest of the pool).
- Desktop still uses a wide snake board; phones use a recent-pick feed instead.
- Auto-pick uses CPU personas for the human seat too (by design for speed).
- No pause/undo mid-auto-complete.

## Key files

- `apps/web/app/(pro)/pro/nfl/fantasy/mock/page.tsx`
- `apps/web/components/pro/nfl/fantasy/FantasyMockDraftClient.tsx`
- `apps/web/lib/fantasy/mock-types.ts`
- `apps/web/lib/fantasy/mock-draft-engine.ts`
- `apps/web/lib/fantasy/mock-cpu.ts`
- `apps/web/lib/fantasy/mock-roster.ts`
