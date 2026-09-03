# NFL dead-tier honesty + confidence ranking — 2026-09-03

**Scoped display/wiring only.** No remat, no KEI mint, no means/projection change,
no `PLAY_STAKE_ELIGIBLE` flip, no Compare Odds book list change.

---

## A) Reliability confidence off the board rank / eligibility drop

| Before | After |
|--------|-------|
| `/nfl/props/board` `ORDER BY tag, confidence DESC NULLS LAST, abs_edge` | `ORDER BY tag ASC, GREATEST(ABS(edge_over), ABS(edge_under)) DESC NULLS LAST` |
| `PLACEHOLDER_CONFIDENCE_MAX = 0.12` dropped low-reliability rows | Gate removed — reliability is not a placeholder signal |

**Sort formula:** tag priority (PLAY → WATCH/LEAN → PASS) then abs-edge magnitude DESC, NULL edges last.

---

## B) Dead tiers hidden (not re-enabled)

| Tier | Why unreachable | UI |
|------|-----------------|----|
| Prop **PLAY** | `PLAY_STAKE_ELIGIBLE = False` | No PLAY filter option; board already nulls tag chrome; API PLAY/STAKE filter ignored |
| Game **BEST VALUE** | Requires HIGH; base 0.72 < 0.75 | Remapped to PLAY on Edge Board badge; omitted from legend |
| Game **HIGH** conf | Same cut | Edges desk drops `75%` min-conf chip; omitted from legend |

Shared flags: `apps/web/lib/nfl-dead-tiers.ts`.

### How to re-enable later (product decision)

1. **Prop PLAY** — clear holdout → set `PLAY_STAKE_ELIGIBLE = True` in `nfl_prop_edge_policy.py` **and** mirror `NFL_PROPS_PLAY_STAKE_ELIGIBLE` in `nfl-dead-tiers.ts`.
2. **BEST VALUE / HIGH** — raise `CONFIDENCE_TIER_BASE` ≥ `CONFIDENCE_BEST_BET_MIN` (0.75) **or** lower the HIGH cut so the tier is earnable; `HIGH_CONFIDENCE_BAND_REACHABLE` / `BEST_VALUE_TIER_REACHABLE` then flip on automatically.

Do **not** unhide from a display-only PR.
