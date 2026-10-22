# Parity protocol c57032db (+ 73815046 reader)

Builder / seal / W7 were **not run**.

## c57032db

- **10 keys** vs prod week W−1 by team at tolerance **0.005**:
  off EPA, def EPA allowed, pass rate, success offense, pressure allowed
  (home and away).
- `rest_days` (home/away) and `roof_dome` are **exact same-game** checks
  (73815046: **SOURCE-CHECK**, not feature parity).
- `diff_off_epa` is an **internal** identity: `home − away`.
- **PASS** = zero out-of-tolerance **and** ≥1 matched team-week **and**
  ≥90% coverage **and** 100% on SOURCE-CHECK + internal keys.
- Coverage below 90% = FAIL.

## 7 KAV keys — DEVIATES

The builder does **not produce** `home/away_kav_offense_5g`,
`home/away_kav_defense_5g`, `home/away_kav_net_5g`, `diff_kav_net_5g`.
They are forced null. Fix plan is in
`nfl-imv-deviation-register-t4149u.md` (do not edit frozen v22/v23).

## 73815046 reader

- Prod export is **CSV**. No jsonl converter.
- Columns = ordered SELECT list in
  `ops/platform/PR_PROD_PARITY_EXPORT_v1.sql` (v2 forthcoming).
- Header required. Types fixed. Empty field = null.
- Missing or unknown column = `NOT_RUN`.
- Duplicate schedule rows = `FAIL`.
- Empty or wrong export = `NOT_RUN`.

41-key split: **10 / 3 / 1 / 3 / 24**.
