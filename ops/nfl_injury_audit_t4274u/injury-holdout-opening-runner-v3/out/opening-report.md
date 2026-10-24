# Opening runner v3 report (77d9c00a B-1..B-10)

RETURN `77d9c00a`. Ryan `t4335s14919` / `fabf8732`. Real lock not written. 2024/25 not opened.
Expected answers commit `fd2ed658166c068c088bb8d971e899da87017ab9` before this runner. Log sha `e5f31be825c96384ad15d664fe7726d6e7b69177deddb70087fc7ca23e3adc5c`.

## Fixtures

- `F-DEFAULT-HOLDOUT` STOP: `STOP: O-1 opening blocked: IMV has not passed this opening runner; real lock not written; 2024/25 not opened`
- `F-PRODUCTION-LOCK-BLOCKED` STOP: `STOP: O-3 lock: production lock requires verified IMV opening-runner PASS sha`
- `F-LOCK-PRESENT` STOP: `STOP: O-3 lock: existing lock /tmp/opening-v3-lock-present-19nekxod/lock-present/holdout-once.lock`
- `F-DOUBLE-OPEN` STOP: `STOP: O-3 lock: existing lock /tmp/opening-v3-e2e-hodi9_we/e2e/holdout-once.lock`
- `F-REFIT` STOP: `STOP: O-1 refuse: no tuning or refit path`
- `F-PER-SIDE` STOP: `STOP: O-5 incomplete: complete row has a null per-side timestamp game_id=2022_1_BBB_AAA field=source_ts_home`
- `F-E2E` recorded {'stop': False, 'writer_invoked': True, 'producer_invoked': True, 'receipt_kind': 'opening_receipt', 'export_on_disk_sha': '3d310e6f34ddd2dab2a83c7fef4cc1ca6048c6b9de107e1dc154c5adbb74a794', 'n_incomplete': 1, 'i4': 'INCONCLUSIVE', 'fold_years': {'F1': 2098, 'F2': 2099}, 'workspace': '/tmp/opening-v3-e2e-auqm8puz/e2e'}
- `F-MARKER-NO-2024` recorded {'stop': False, 'admitted_2024_2025': False, 'synthetic_after_lock': True}

## le2023 guards

- listings 58653: Z=58653 naive=0
- n_incomplete=11 ids=['2013_1_CIN_CHI', '2013_1_NYG_DAL', '2014_15_SF_SEA', '2015_1_NO_ARI', '2017_1_IND_LA', '2020_1_GB_MIN', '2020_6_KC_BUF', '2022_2_IND_JAX', '2022_7_CHI_NE', '2022_12_BAL_JAX', '2023_5_HOU_ATL']

NO-GO. Coming Soon ON. No merge. No real lock. No opening.
