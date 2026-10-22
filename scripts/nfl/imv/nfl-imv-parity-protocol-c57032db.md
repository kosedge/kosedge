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

## 73815046 reader + v3 SQL pin

- Prod export is **CSV**. No jsonl converter.
- Columns = **exact ordered SELECT list** in
  `ops/platform/PR_PROD_PARITY_EXPORT_v3.sql`.
- Reader pin: `sha256 = b10d6cfd90b0586070c5a4ed3df5cd9782d2d7ad6e6145dcc3719f67a3d5e5c0`.
- Missing file or sha mismatch = `NOT_RUN`. Do not invent the SQL bytes.
- Output is a **41-column** CSV. `roof_vocab_unknown` is an audit column.
- `dome`/`closed` → 1; `outdoors`/`open` → 0; anything else → NULL.
- Rest values come in **raw and derived** form. SOURCE-CHECK prefers derived.
- `roof_vocab_unknown=true` on a row → that row's roof SOURCE-CHECK = `NOT_RUN`.
- Team-code consistency: home/away must be the NFL-32 set after LA→LAR /
  WSH→WAS (and JAC/STL/SD/OAK aliases); `game_id` teams must agree.
- Header required. Types fixed. Empty field = null.
- Missing or unknown column = `NOT_RUN`.
- Duplicate schedule rows = `FAIL`.
- Empty or wrong export = `NOT_RUN`.

41-key split: **10 / 3 / 1 / 3 / 24**.
