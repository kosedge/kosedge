# Independent validation checklist — NCAAM NEUTRAL lane (post–Grok reset)

Builder findings in this prep are **not** independent approval. After Grok resets, an independent reviewer should:

1. Confirm base SHA `4bd0f87d…` (or later `deploy-vercel`) and that sealed holdout `seal_payload_sha256=af4fd451…` is unchanged.
2. Re-read frozen preregistration **before** looking at Train-A diagnostics numbers.
3. Verify `fair_b2_pace_v1.py` sha256 remains `4a305870fbc55900336566531eca92cd4586d8a04edd62845bcc23a03112f5bd`.
4. Verify `venue_contract.py` sha256 remains `9f48eb266c362c6ae5ed52ed6872293a8388ccb2611bcae05506ff0fb6f8486f`.
5. Re-run focused pytest: `test_ncaam_lab_b2_pace_neutral_v1.py` + parent `test_ncaam_lab_b2_pace_v1.py`.
6. Re-run Train-A script once; confirm deterministic JSON (same metrics under seed `20260909`).
7. Confirm script refuses Test-A / holdout / 2024–25 pack paths.
8. Confirm `materialize_lab_fair` still calls only incumbent `compute_fair_b2`.
9. Spot-check venue identity: home / neutral / unknown / postseason conflict / **non-boolean flag** cases.
10. Confirm August 31 research ratings were **not** written into KEI / production fair paths.
11. Do **not** unseal holdout; do **not** score Test-A as confirmation.
12. File OPEN/BLOCKED (not soft-green) on any gap in identity, PIT, or gate language.

Ryan-only afterward: pocket/holdout unseal authorization; any promotion / materialize switch.
