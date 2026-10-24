# D-2 runner report

Ryan `t4335s14919` / `fabf8732`: `CLEAR: build the runner, IMV reviews, then open once`.
IMV review of this runner is still required. 2024/25 was not opened.

## Fixtures

- `F-NAIVE` STOP: `STOP: D-2 listings TZ: naive/zoneless date_modified file=listings_2022.csv value='2022-09-11T16:00:00'`
- `F-INC-TS` STOP: `STOP: D-2 incomplete: incomplete row has a timestamp game_id=2022_2_CCC_DDD`
- `F-INC-DELTA` STOP: `STOP: D-2 incomplete: incomplete row has non-null delta_margin game_id=2022_2_CCC_DDD`
- `F-COMP-NULL` STOP: `STOP: D-2 incomplete: complete row has a null timestamp game_id=2022_1_BBB_AAA`
- `F-V2-MISSING` STOP: `STOP: D-2 export pin: missing on-disk .v2 sidecar fixtures/v2-missing/export.json.sha256.v2`
- `F-V2-BLOB` STOP: `STOP: D-2 export pin: sidecar uses blob hash; pin must be on-disk sha`
- `F-V2-MISMATCH` STOP: `STOP: D-2 export pin: sidecar sha != on-disk sha (blob hash is not a pin) listed=0000000000000000000000000000000000000000000000000000000000000000 on_disk=fd2bac05b2560417da056c4d50486e9af4c568b254723dd307742877eb1a81f7`
- `F-JOIN-FIRST` STOP: `STOP: D-2 order: incomplete-row count must be taken before any join`
- `F-NAME` STOP: `STOP: D-2 refuse: holdout year 2024 in path listings_2024.csv`
- `F-HOLDOUT` STOP: `STOP: D-2 opening blocked: IMV has not passed this runner; lock not written; 2024/25 not opened`
- `F-OK` recorded n_incomplete=1 ids=['2022_2_CCC_DDD']

## le2023

- listings 58653: Z=58653 offset=0 naive=0
- years [2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023]
- n_incomplete=11 by_season={'2013': 2, '2014': 1, '2015': 1, '2017': 1, '2020': 2, '2022': 3, '2023': 1}
- excluded_game_ids=['2013_1_CIN_CHI', '2013_1_NYG_DAL', '2014_15_SF_SEA', '2015_1_NO_ARI', '2017_1_IND_LA', '2020_1_GB_MIN', '2020_6_KC_BUF', '2022_2_IND_JAX', '2022_7_CHI_NE', '2022_12_BAL_JAX', '2023_5_HOU_ATL']
- export on-disk pin `a38a55bb765e977ed88f8808d76715faddf50098b2354b122a5499f0ec706ac8`

NO-GO. Coming Soon ON. No merge. No lock. No opening.
