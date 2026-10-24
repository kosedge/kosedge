# INV-1.E — prediction_cutoff rule

Binding from SPEC §2:

```
prediction_cutoff = earliest of (kickoff_utc, declared decision_ts)
```

unless a tighter product cutoff is frozen in a later execution package
(Step 2+, after INV-1 PASS). This INV-1 does **not** freeze a tighter
cutoff.

## Inequality (T-PIT-7)

- `availability_ts < prediction_cutoff` → eligible
- `availability_ts == prediction_cutoff` → allowed only if a later
  frozen rule says closed-at-cutoff. **This draft does not claim
  closed-at-cutoff.** Until that freeze exists, treat `==` as
  **not eligible** (fail closed).
- `availability_ts > prediction_cutoff` → always FAIL / BLOCKED

`kickoff_utc` is the existing `parse_fit_kickoff_utc` value.
`decision_ts` is optional; if absent, cutoff = `kickoff_utc`.

Cutoff must be `<= kickoff`. A cutoff after kickoff is invalid.

Ingest / `updated_at` is never `availability_ts`.
