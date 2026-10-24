# O-7 — D-2 expected-answers commit order (`ff3b3b0b`)

IMV `b7364186` graded “filed before the runner” as **secondhand** because
`ff3b3b0b` is the COMMIT recorded in `inputs/expected_answers_commit.txt`,
not a fact IMV can read without git.

Git is out of IMV method. This note records the inspectable first-parent
order on `cursor/nfl-injury-holdout-runner-d2-1a07`. Author and committer
dates are identical (`%ci` = `%ai`).

```
ff3b3b0bfe91a42d4165a2cd81d5a811277b38c7  2026-10-24 15:05:39 +0000
  File D-2 expected answers, CLEAR fabf8732, and le2023-only fixtures before the runner.

7741e286  2026-10-24 15:07:20 +0000
  Record the D-2 expected-answers commit hash before any runner change.

62c6f8d6d0a0103a9cad421e628be55417de6e7b  2026-10-24 15:07:24 +0000
  Add D-2 runner: TZ census, incomplete-row before join, provenance IDs, .v2 pin.
```

`ff3b3b0b` (15:05:39Z) before runner file commit `62c6f8d6` (15:07:24Z).

## Label

- **Inspectable on that branch:** expected-answers commit before the D-2 runner file.
- **Log channel / IMV method:** still secondhand (no git in IMV method; the D-2
  runner log does not embed `ff3b3b0b`).
- This opening package files its own expected answers before its runner
  (same order).
