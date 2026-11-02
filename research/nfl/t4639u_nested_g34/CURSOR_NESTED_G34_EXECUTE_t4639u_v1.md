# CURSOR_NESTED_G34_EXECUTE_t4639u_v1

**RESEARCH_DIAGNOSTIC · CERT=0 · NFL NO-GO · F2 FROZEN · Coming Soon ON · #648 DRAFT · do not merge**

**VERDICT (protocol 59161fbb stop rules only): `FAIL_RESEARCH`**

invariants hold; B1 criterion not met

Filed `2026-10-28T16:45:01Z`. Paper/file evidence only. No CERT claim. No beats-market claim.

## Authority

| item | sha8 |
|---|---|
| DECISION_RYAN_t4639u | `c51b4280` |
| COS_ORDER | `5b8d2482` |
| Protocol v2 unchanged | `59161fbb` |
| IMV PASS_PROTOCOL | `1fc4d103` |
| F_B1 | `14d25d4c` |
| counts.json | `890533db` |

## B1 binding (2019–2022 pooled)

- selected `G52` vs frozen ref `G27`
- winner==ref: `False`
- selection_n P_sel games=1335 seasons [2014, 2015, 2016, 2017, 2018]
- inner-CV n_oof=1068 validate [2015, 2016, 2017, 2018]
- scored_n=1105 seasons [2019, 2020, 2021, 2022]
- selection∩scored=∅: TRUE (n_overlap=0)
- MAE_model=10.213651 MAE_ref=10.208793 **ΔMAE_ref=-0.004858**
- binding CI (paired game B=10000 seed 4141): [-0.134735, 0.126522] excludes0=False
- ΔMAE_mkt=-0.362973 **REPORT-ONLY NOTE** (no beats-market claim; expected sign < 0)
- c=0.056558 **REPORT-ONLY NOTE** (HC1 diagnostic)
- season-block CI report-only: [-0.104287, 0.085916]
- n_rows season≥2024 source counted only=586; derived=0

## Supportive (cannot PASS/FAIL)

- B2 pooled ΔMAE_ref=0.094425 (UNSTABLE=False)
- 2023 ΔMAE_ref=0.135857
- A1 winner=G34 ΔMAE_ref=0.059253
- A2 winner=G34 ΔMAE_ref=0.051772

## Scope

PASS_PROTOCOL ≠ CLEAR ≠ PASS_RESEARCH ≠ CERT; Lane B label applies only to new nested artifacts; does not reclassify Exp A 0d1f4f9b or the existing G34 ≤2022 OOF (stays Lane A DEVELOPMENT_ONLY).

Existing G34 ≤2022 OOF stays Lane A DEVELOPMENT_ONLY. Exp A 0d1f4f9b / Exp D-R 93a79857 untouched.

**CERT=0. RESEARCH_DIAGNOSTIC. NFL NO-GO. F2 frozen. Coming Soon ON.**
