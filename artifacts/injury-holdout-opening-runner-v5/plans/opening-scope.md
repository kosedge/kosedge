# Opening runner v5 scope

`0505e492` shortest path, with Ryan t4340s14953 / `592e0bb9`
authorizing scorer v6.2 only if IMV passes the final diff as
holdout-allowance-only with no metric change:

1. File expected answers v5 first (decision path+sha `592e0bb9`,
   single scorer `755d30a8`, builder `aa9d512b`, raw pins, QB1
   source `ebd3dac0`, naive→STOP, `i3_holm_scorer`).
2. One runner sha: remove the runtime switch (B-14), pin
   `755d30a8`, call the frozen row builder (B-4b), STOP on naive
   timestamps (B-4c).
3. IMV re-checks the `755d30a8` vs `ca98ae0e` diff (S-2 wording
   changed the sha from `1129354a`).
4. Adversarial file:line provenance: every production input to a pin.
5. STOP for IMV changes-only review.

Do not write the real lock. Do not open 2024/25. No merge.
