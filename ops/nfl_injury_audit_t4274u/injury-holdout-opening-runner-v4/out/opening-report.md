# Opening runner v4 report (4fd6cfbe B-1/B-4/B-6/B-8a/B-13)

RETURN `4fd6cfbe` + erratum `b746e5eb`. Ryan `t4335s14919` / `fabf8732`. Real lock not written. 2024/25 not opened.
Expected answers commit `74c8028b20ba24d62e995b28a1d51f237ef70ecc` before this runner. Active scorer `ca98ae0e`. v6.2 `1129354a` PENDING_RYAN. Log sha `52551c45256e475bbd04e0aabf91a1bfd99ecf3888cbbb896534b07573c00170`.

## Fixtures

- `F-DEFAULT-HOLDOUT` STOP: `STOP: O-1 opening blocked: IMV has not passed this opening runner; real lock not written; 2024/25 not opened`
- `F-PRODUCTION-INPUTS-MISSING` STOP: `STOP: B-13 production input: missing /workspace/ops/nfl_injury_audit_t4274u/games.json`
- `F-PRODUCTION-LOCK-BLOCKED` STOP: `STOP: O-3 lock: production lock requires verified IMV opening-runner PASS sha`
- `F-LOCK-PRESENT` STOP: `STOP: O-3 lock: existing lock /tmp/opening-v4-lock-present-k9iv7n9u/lock-present/holdout-once.lock`
- `F-DOUBLE-OPEN` STOP: `STOP: O-3 lock: existing lock /tmp/opening-v4-e2e-dyi8gr4m/e2e/holdout-once.lock`
- `F-REFIT` STOP: `STOP: O-1 refuse: no tuning or refit path`
- `F-PER-SIDE` STOP: `STOP: O-5 incomplete: complete row has a null per-side timestamp game_id=2022_1_BBB_AAA field=source_ts_home`
- `F-POST-LOCK-BASEEXCEPTION` recorded {'stop': True, 'consumed': True, 'receipt_0444': True, 'lock_unrewritten': True}
- `F-E2E` recorded {'stop': False, 'writer_invoked': True, 'producer_invoked': True, 'receipt_kind': 'opening_receipt', 'export_on_disk_sha': '3d310e6f34ddd2dab2a83c7fef4cc1ca6048c6b9de107e1dc154c5adbb74a794', 'n_incomplete': 1, 'i4': 'INCONCLUSIVE', 'fold_years': {'F1': 2098, 'F2': 2099}, 'scorer_sha': 'ca98ae0e70fcdee77d46aed3c4f9be5644079da6adf08411891e1d5b7970e6c6', 'workspace': '/tmp/opening-v4-e2e-gwwkwezt/e2e'}
- `F-MARKER-NO-2024` recorded {'stop': False, 'admitted_2024_2025': False, 'synthetic_after_lock': True}
- `F-SCORER-STILL-CA98AE0E` recorded {'stop': False, 'active': 'ca98ae0e70fcdee77d46aed3c4f9be5644079da6adf08411891e1d5b7970e6c6', 'pending': '1129354a06c7c747d7021e1448ff028163314c81c3eee35cc0fb6345deddb9be'}
- `F-B8A-SUBSTRING-REJECT` recorded {'stop': False, 'substring_rejected': True, 'exact_accepted': True}
- `F-SCORER-GUARDS-CLOSED` recorded {'stop': False, 'default_closed': True, 'permit_2024_2025': True, 'year_2026': 'never'}

## le2023 guards

- listings 58653: Z=58653 naive=0
- n_incomplete=11 ids=['2013_1_CIN_CHI', '2013_1_NYG_DAL', '2014_15_SF_SEA', '2015_1_NO_ARI', '2017_1_IND_LA', '2020_1_GB_MIN', '2020_6_KC_BUF', '2022_2_IND_JAX', '2022_7_CHI_NE', '2022_12_BAL_JAX', '2023_5_HOU_ATL']

NO-GO. Coming Soon ON. No merge. No real lock. No opening.
