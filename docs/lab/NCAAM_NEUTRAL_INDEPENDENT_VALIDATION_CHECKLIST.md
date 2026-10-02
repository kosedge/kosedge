# Independent validation checklist — NCAAM NEUTRAL lane (post–Grok reset)

Builder findings in this prep are **not** independent approval. After Grok resets, an independent reviewer should:

1. Confirm base SHA `4bd0f87d…` (or later `deploy-vercel`) and that sealed holdout seal hashes are unchanged.
2. Re-read frozen preregistration **before** looking at Train-A diagnostics numbers.
3. Verify `fair_b2_pace_v1.py` content hash / behavior unchanged vs Phase 2.7A pin.
4. Re-run focused pytest: `test_ncaam_lab_b2_pace_neutral_v1.py` + parent `test_ncaam_lab_b2_pace_v1.py`.
5. Re-run Train-A script once; confirm deterministic JSON (same metrics under same seed).
6. Confirm script refuses Test-A / holdout / 2024–25 pack paths.
7. Confirm `materialize_lab_fair` still calls only incumbent `compute_fair_b2`.
8. Spot-check venue identity: home / neutral / unknown / postseason conflict cases.
9. Do **not** unseal holdout; do **not** score Test-A as confirmation.
10. File OPEN/BLOCKED (not soft-green) on any gap in identity, PIT, or gate language.

Ryan-only afterward: pocket/holdout unseal authorization; any promotion / materialize switch.
