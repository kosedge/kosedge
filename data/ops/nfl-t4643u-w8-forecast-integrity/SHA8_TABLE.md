# t4643u WS-A sha8 table (IMV 062197c0 bound)

| artifact | sha256 | sha8 |
|---|---|---|
| `IMV_ACCEPT_CRITERIA_t4643u_WS_C_ENG_CORRECTNESS_CONSUMPTION_v1.txt` | `062197c059326357cb1fee9e484df4d8390607f64d9f08ce17b76ef474e5492a` | `062197c0` |
| `COS_ORDER_CURSOR_t4643u_WS_A_W8_FORECAST_INTEGRITY_v1.txt` | `1114c1d249b995f37a11f72d709a78f0b6653607fa5a35d4d646311623800b50` | `1114c1d2` |
| `C0_C7_CONTRACT.md` | `c1e5c36e32f07d98f034040f28add1e19a4e8ba518e410d3c31caa1ca95f9bc8` | `c1e5c36e` |
| `CODE_PATH_MAP.md` | `72724cda99ef3086a92cbd927c9bd378fd4dd5d02ebedc6642040e94aebf0fd8` | `72724cda` |
| `INPUT_CONSUMPTION_MATRIX.md` | `dee133116ee99b98db3033cd626f6ba8c1120ba5469b4da9a184e45cbf97ee99` | `dee13311` |
| `INPUT_CONSUMPTION_MATRIX.json` | `49224764d7c9a7c4962f0b5920e96e59e7858b640ec1c082dbc60fcaac76aa9c` | `49224764` |
| `WAREHOUSE_AUTHORITY.md` | `ca3dea1b3e2a51bf327bbc97a023197eec732e5fbcbe61502c8e6107e78691af` | `ca3dea1b` |
| `BOUNDED_REPAIR_PLAN.md` | `4dcc04f793ac796c247a4085b909a528a5035945061d4df6389638c1389dd7f6` | `4dcc04f7` |
| `COS_RECEIPT.md` | `7b95cfa63f0b08c3b6a0d2d8a92f37cf636a1219b3addd00f9ea3f95ae1c1898` | `7b95cfa6` |
| `fixtures/C1_base.json` | `fc0f79f827b2cec46a2d54ba21b6badbc380b227142b4ecdc5ee52a0c13fb19e` | `fc0f79f8` |
| `fixtures/C1_epa_home_boost.json` | `2c2cc50b6f2678693055a6a0026a78bb7499dd23a71e6f918ada43842dd55146` | `2c2cc50b` |
| `fixtures/C1_inj_impact_only.json` | `ef31a571c708b782b4aa883485bcfdb7971480ebfe63f0431113ea3544a53c1e` | `ef31a571` |
| `fixtures/C1_rest_home_extra.json` | `1e5f6ce092581abbd2ed006549939b099d8bb72902e27176c3b220adeaae4fe0` | `1e5f6ce0` |
| `fixtures/C2_epa_strength_missing.json` | `43a19746bb2a557f0522cc56ea049d59b5620218522f4deb98ec4d470b9b7ae3` | `43a19746` |
| `fixtures/C2_g3_last_designated.json` | `092d685dfbed9fbfc45d7a13817e81946458d617a5c59c0b42dbaa91171cc68e` | `092d685d` |
| `fixtures/C2_rest_days_schedule.json` | `fb14d4881c9b9cd13e18c877e865817fb8110a30ce1a9b422db1c35ce82301ef` | `fb14d488` |
| `fixtures/C2_rest_home_missing.json` | `e45d6073180d37fcc1cc90edac85e3bc8e492c7d3724d2b1a93764c368b7d9c2` | `e45d6073` |
| `fixtures/C2_sealed_restore_oracle.json` | `6d303b90339867cb744708fd894c84035c6b334cbc2d6ac41edef7a6e00b7103` | `6d303b90` |
| `fixtures/FIXTURES.sha256` | `367f164fbd26357384ea9a3a34516cc49f40179581e77212dd1efaa05cb1866c` | `367f164f` |
| `services/model-service/tests/test_nfl_w8_forecast_consumption_contracts_t4643u.py` | `4875faeb6675123663691198937fa35d0d18149a7de850dbb860fbadddcb6bf4` | `4875faeb` |

CERT=0. C1+C2 hashed oracles. G1 GAP. G2 GAP_SIM_VOLUME. C7 clean. #648 untouched.
Cursor does not self-grade PASS_ENG_CONTRACT. Stop for CoS ACCEPT → IMV grade.

