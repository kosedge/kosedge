# Opening runner v2 report (a8958e85 R-1..R-9)

RETURN `a8958e85`. Ryan `t4335s14919` / `fabf8732`. Real lock not written. 2024/25 not opened.
Expected answers commit `73b537b2e394def333e2ad5ce22a24ecc42d9ff2` before this runner. Log sha `ffea30d02b6c0279824f55c0420720aa3c9833b8a8f1aae2cdd5b4990cfd7228`.

## Fixtures

- `F-DEFAULT-HOLDOUT` STOP: `STOP: O-1 opening blocked: IMV has not passed this opening runner; real lock not written; 2024/25 not opened`
- `F-PRODUCTION-LOCK-BLOCKED` STOP: `STOP: O-3 lock: production lock requires verified IMV opening-runner PASS sha`
- `F-LOCK-PRESENT` STOP: `STOP: O-3 lock: existing lock /tmp/opening-v2-lock-present-f_x1priy/lock-present/holdout-once.lock`
- `F-DOUBLE-OPEN` STOP: `STOP: O-3 lock: existing lock /tmp/opening-v2-e2e-f0ocxc5o/e2e/holdout-once.lock`
- `F-REFIT` STOP: `STOP: O-1 refuse: no tuning or refit path`
- `F-PER-SIDE` STOP: `STOP: O-5 incomplete: complete row has a null per-side timestamp game_id=2022_1_BBB_AAA field=source_ts_home`
- `F-E2E` recorded writer_invoked=True i4=INCONCLUSIVE n_incomplete=1

## le2023 guards

- listings 58653: Z=58653 naive=0
- n_incomplete=11 ids=['2013_1_CIN_CHI', '2013_1_NYG_DAL', '2014_15_SF_SEA', '2015_1_NO_ARI', '2017_1_IND_LA', '2020_1_GB_MIN', '2020_6_KC_BUF', '2022_2_IND_JAX', '2022_7_CHI_NE', '2022_12_BAL_JAX', '2023_5_HOU_ATL']

NO-GO. Coming Soon ON. No merge. No real lock. No opening.
