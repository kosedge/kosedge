# IMV acceptance gate — Phase 1

CoS routes inventory v1 + this spec to IMV.

IMV accepts when it signs that:

1. The inventory's site list is complete enough (or names the
   missing sites).
2. The reconstruction sources, `availability_ts` rule, and
   missing→ineligible rule are sufficient to kill B-4b(n)-PIT.
3. The leakage-control predicate covers every time-sensitive
   feature Ryan listed.
4. The required tests, including the synthetic PIT / trade /
   replacement / practice-squad cases, are the right bar.
5. Frozen scoring rules for a future refit are still the C-1
   contract (or IMV names the delta).

IMV returns the exact gaps if any item fails.

Until that acceptance (or an exact gap list) exists:

- no production refit
- no week-aware rebuild implementation beyond fixtures IMV asked for
- no holdout request
- no `holdout-once.lock`
- no merge / deploy / publish
- opening-runner work stays paused
- prior CLEAR `fabf8732` and v6.2 allowance `592e0bb9` stay
  superseded for the season-level-roster route

This spec is not a PASS. It is a request for IMV to accept or
correct the rebuild plan.
