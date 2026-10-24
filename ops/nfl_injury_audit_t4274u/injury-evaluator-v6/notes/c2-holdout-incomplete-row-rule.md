# C-2 — pinned C-5 IDs and holdout incomplete-row rule

Filed before the v6 scorer change. Ruling `1ef1f0a7`.

## le2023 pin (identity, not only the count)

These 11 `game_id`s are the C-5 `complete=false` set in `a38a55bb`
(IMV `d18ebf22` §(d); package census matches):

```
2013_1_CIN_CHI
2013_1_NYG_DAL
2014_15_SF_SEA
2015_1_NO_ARI
2017_1_IND_LA
2020_1_GB_MIN
2020_6_KC_BUF
2022_2_IND_JAX
2022_7_CHI_NE
2022_12_BAL_JAX
2023_5_HOU_ATL
```

Season counts: 2013:2, 2014:1, 2015:1, 2017:1, 2020:2, **2022:3**, **2023:1**.
Total 11. On every pinned row the export has:

- `complete=false`
- `delta_margin` = `delta_total` = null
- `source_ts` = `as_of_ts` = `kickoff_utc` = `source_ts_home` = `source_ts_away` = null

The scorer must pin this set and require those nulls. Unexpected incomplete
`game_id`, a pinned id that is complete, or a non-null delta / per-side
timestamp on a pinned row → STOP.

Exclusion is identical in both arms (applied on the export, before the arms
split, before close/outcome join).

## Holdout incomplete-row rule (pre-declared; no 2024/25 count)

Counts are **not** pre-declared for 2024/25 (holdout CLOSED; not opened).

After CLEAR, from the **holdout export**, before any outcome or close join:

1. A row is incomplete iff `complete=false`.
2. Require: all five timestamps null (`source_ts`, `as_of_ts`, `kickoff_utc`,
   `source_ts_home`, `source_ts_away`) **and** both deltas null.
3. complete + any null timestamp → STOP.
4. incomplete + any non-null timestamp or non-null delta → STOP.
5. Exclude the incomplete set identically in both arms.
6. Record `n_incomplete` total and by season from that export census.
   Pin the observed holdout `game_id` set in the holdout provenance
   (identity, not only the count).
7. Do not join close or outcome onto an incomplete row.
