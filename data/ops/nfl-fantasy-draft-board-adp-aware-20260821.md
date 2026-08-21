# Fantasy draft board — ADP-aware action (2026-08-21)

**Rankings stay raw Model rank.** Builder + Mock advice is ADP-aware. Same projections; different scoring for *when* to take a player.

**LIVE / props / playing-time:** unchanged. No PLAY language on fantasy.

---

## Split

| Surface | Optimizes for |
|---------|----------------|
| Rankings (Model rank tab) | Pure KosEdge order (`rankOverall`) |
| Value tab | Value Δ vs ADP (matched only) |
| Builder suggestions | need + VOR − reach penalty |
| Mock on-the-clock + CPU | same scorer; R1 / late-QB2 guards stay |

No second “official rank.” Methods: *Model rank is projection order, not recommended pick order.*

---

## Formula (draft advice)

```
score = (VOR + need + rank_prior + wait_bonus − reach_penalty) × needMult + scarcity
```

- **VOR** — clamped `valueOverReplacement` (cap 250 × 0.12)
- **need** — unfilled starter slots at the position
- **reach_penalty** — picks before ADP, plus model-ahead vs ADP beyond one round (12). Reduced only for elite + cliff + hole
- **wait_bonus** — positive Value Δ when ADP is still later than this pick
- Unmatched / cross-format ADP is not blended
- User-facing Take / Wait CTAs cap at ±12 vs ADP (Gesicki-class stays unlabeled)

Copy:

- **Take now** — model and market aligned / value at this pick
- **Wait** — available later by ADP
- **Reach** — only if need is extreme

Not an optimal-pick claim.

---

## Before / after (advice, not Model #)

| Situation | Model # stays | Old action | New action |
|-----------|---------------|------------|------------|
| CMC · pick 4 · ADP ~5 | #1 | BPA take | **Take now** — aligned |
| Model WR #18 · ADP 35 · pick 18 | #18 | Often BPA take | **Wait** — available later |
| Elite TE hole + cliff · pick 22 · ADP 28 | #8 | Take now (need/cliff) | **Reach** — only if need is extreme |
| T.Lawrence-class QB #3 · ADP ~85 · pick 12 | #3 | Model BPA QB | **no Take CTA** (Δ > 12) |
| M.Gesicki-class TE #47 · ADP 251 · R1 | #47 | value-hero risk | **fair**, no CTA; CPU hard-blocked |

CPU personas mix the same `scoreValueAwarePlayer` output; R1 ADP reach caps and QB2 suppress still apply.

---

## Honesty

- ADP source + freshness still on the desk
- Unmatched ADP → Value Δ is —
- Preseason K/DST limits unchanged
- Rankings table no longer shows a competing “Board” index

Tunable knobs: `VALUE_AWARE_WEIGHTS` in `apps/web/lib/fantasy/value-aware-recs.ts`.
