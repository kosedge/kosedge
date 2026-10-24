# Opening runner v6 scope

`2c71e4d0` shortest path. Do not write a lock. Do not open.

1. File expected answers v6 first (RETURN `2c71e4d0`, V62 PASS on
   `755d30a8`, L-1 final `8b482cb9`, DIFF `280d9785`, B-4b(R)
   deposited `8af44a7e`/`bc89721f`, B-4b(P) raw-input-sha contract,
   B-4b(n) roster years, decision `592e0bb9`, builder `247744d2`,
   producer `ae8f9585`).
2. One runner sha: pin `8b482cb9`, hash production raw inputs into
   lock+receipt before any row parse, enforce declared roster
   years, call `deposit_le2023_rebuild` and assert the deposited
   compare is `0_DIFF`.
3. IMV changes-only: confirm DIFF `280d9785` is docstring-only;
   then the `755d30a8` PASS carries over.
4. Every provenance claim points to a deposited output file.
5. STOP for IMV changes-only review.

Do not write the real lock. Do not open 2024/25. No merge.
