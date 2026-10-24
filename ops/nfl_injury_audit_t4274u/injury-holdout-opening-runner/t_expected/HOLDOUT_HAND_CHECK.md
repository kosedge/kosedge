# Holdout expected answers — hand check (filed before the runner)

Gate table + receipt schema only. **No holdout values.**

`F-HOLDOUT` must call `main(["--mode","holdout","--workspace", …])`.
Default `main(["--mode","holdout"])` STOPs with `O-1 opening blocked` and
does not write the real lock.

Complete rows need per-side timestamps (O-5).
`ff3b3b0b` before `62c6f8d6` is in `notes/o7-d2-expected-answers-commit-order.md`.
