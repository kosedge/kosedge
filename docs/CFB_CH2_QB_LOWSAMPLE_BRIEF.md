# Chapter 2 Phase 1E — low-sample QB talent (not a Hawaii patch)

**Repo:** `kosedge/kosedge`  
**Base:** after 1C taper + 1D `min(22, att/22)`  
**Why:** STAN/BALL print ~50 on 3 attempts — missing sample, not a measured grade. Hawaiʻi (430 att) is out of scope.

## Laws

- Threshold is **attempts**, not conference.
- Fallback must already exist in the packager. If none → blocker (do not invent P4=70).
- BALL is in the treatment set; cupcake canary must still hold.
- No school if. No 1C τ / 1D divisor edits. No `WEIGHT_QB` / `MATCHUP_RESPONSE`.

## Phase 0 (required before code)

1. Quote `talent_from_qb_stats` after 1D.
2. Histogram of 2026 QB attempts → recommend **N** (candidate 80; say whether MICH is in/out).
3. Full list `att < N` with class + current talent.
4. Named fallback field + file:line.

## Phase 1 shape

```text
if attempts >= N:
    talent = talent_from_qb_stats(...)   # 1D formula
else:
    talent = blend(stats_talent, fallback, w(attempts))
```

`w(0)` ~all fallback; `w(N)` all stats. Continuous. No cliff at 79 vs 80.

## This PR

`N=80`. Fallback: `roster.recruiting_class_score`. Blend weight `w=sqrt(att/N)` (linear reordered top-7). Rematerialize QB talent. Scorecard + tests. Hawaii flip not required.

## Forbidden

Team/conference branches. Touching 1C τ or 1D divisor. `WEIGHT_QB` / `MATCHUP_RESPONSE`. Inventing recruiting numbers. Utah / NFL/CBB/MLB.
