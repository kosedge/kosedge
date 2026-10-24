# Opening runner v6 report (2c71e4d0 L-1/B-4b(R)/B-4b(P)/B-4b(n))

RETURN `2c71e4d0`. Ryan `t4335s14919` / `fabf8732`. Scorer decision t4340s14953 / `592e0bb9`. V62 PASS on `755d30a8`. Real lock not written. 2024/25 not opened.
Expected answers commit `daf94a7d7383400cac78c5b8adf6ee4096ea83dd` before this runner. Active scorer `8b482cb9`. L-1 DIFF `280d9785`. Log sha `762e04f7c0244eed2c6c575e20ced20eedbbfe3ef61880e708d84030c119e9b9`.

## Fixtures

- `F-DEFAULT-HOLDOUT` STOP: `STOP: O-1 opening blocked: IMV has not passed this opening runner; real lock not written; 2024/25 not opened`
- `F-PRODUCTION-INPUTS-MISSING` STOP: `STOP: B-13 production input: missing /workspace/ops/nfl_injury_audit_t4274u/games.json`
- `F-PRODUCTION-LOCK-BLOCKED` STOP: `STOP: O-3 lock: production lock requires verified IMV opening-runner PASS sha`
- `F-LOCK-PRESENT` STOP: `STOP: O-3 lock: existing lock /tmp/opening-v6-lock-present-4tjd0dj1/lock-present/holdout-once.lock`
- `F-DOUBLE-OPEN` STOP: `STOP: O-3 lock: existing lock /tmp/opening-v6-e2e-7tl913dq/e2e/holdout-once.lock`
- `F-REFIT` STOP: `STOP: O-1 refuse: no tuning or refit path`
- `F-PER-SIDE` STOP: `STOP: O-5 incomplete: complete row has a null per-side timestamp game_id=2022_1_BBB_AAA field=source_ts_home`
- `F-POST-LOCK-BASEEXCEPTION` recorded {'stop': True, 'consumed': True, 'receipt_0444': True, 'lock_unrewritten': True}
- `F-E2E` recorded {'stop': False, 'writer_invoked': True, 'producer_invoked': True, 'receipt_kind': 'opening_receipt', 'export_on_disk_sha': 'ac6b5c2f492f217aa46b2ab2ff97229d32555682292fb03b3d8c13004a9f16a5', 'n_incomplete': 1, 'i4': 'INCONCLUSIVE', 'fold_years': {'F1': 2098, 'F2': 2099}, 'scorer_sha': '8b482cb9ddf46ea3bfb80cbfc429978467cbccc126fb0d9d7ca8013ef2f34b37', 'workspace': '/tmp/opening-v6-e2e-ltwop93c/e2e'}
- `F-MARKER-NO-2024` recorded {'stop': False, 'admitted_2024_2025': False, 'synthetic_after_lock': True}
- `F-SCORER-PINNED-V62` recorded {'stop': False, 'active': '8b482cb9ddf46ea3bfb80cbfc429978467cbccc126fb0d9d7ca8013ef2f34b37', 'baseline_755d30a8': '755d30a8ce0dde7cd31b2e5ded9d4e06240e73f963b68a6ae4bd9af30d90ea5f', 'diff_sha': '280d9785ffc1a313e9415e0b3cf8f75f7d0156908aba29a9902e4bb8a8788c55', 'decision_sha': '592e0bb9e57ef4c7d997d48b336cb37594f7353a891b8ab56d6a70b55492e021', 'runtime_switch': False, 'docstring_draft': False}
- `F-B8A-SUBSTRING-REJECT` recorded {'stop': False, 'substring_rejected': True, 'exact_accepted': True}
- `F-SCORER-GUARDS-CLOSED` recorded {'stop': False, 'default_closed': True, 'permit_2024_2025': True, 'year_2026': 'never'}
- `F-NAIVE-TIMESTAMP` recorded {'stop': True, 'naive': 'STOP'}
- `F-GAMES-JSON-VALUES` recorded {'stop': True, 'games_json_values': 'refused'}

## le2023 guards

- listings 58653: Z=58653 naive=0
- n_incomplete=11 ids=['2013_1_CIN_CHI', '2013_1_NYG_DAL', '2014_15_SF_SEA', '2015_1_NO_ARI', '2017_1_IND_LA', '2020_1_GB_MIN', '2020_6_KC_BUF', '2022_2_IND_JAX', '2022_7_CHI_NE', '2022_12_BAL_JAX', '2023_5_HOU_ATL']
- B-4b(R) rebuild 0_DIFF n=2863 deltas=8af44a7eaa96ff695e10a61c827f942020c534f578ee36893701409857429394

NO-GO. Coming Soon ON. No merge. No real lock. No opening.
