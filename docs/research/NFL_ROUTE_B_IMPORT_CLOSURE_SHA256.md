# Route-(b) import-time closure (33 modules)

K-4 pin for IMV pure-diff. Package: `src.services.nfl_season_engine`.
Hashes are SHA-256 of on-disk bytes. Not a gate. Not W8 RA acceptance.

This head also changed sibling engine modules treated as in-closure:
`nfl_simulator.py`, `nfl_handicapping_framework.py`, `nfl_tendency_pricing.py`.

| path | sha256 |
| --- | --- |
| `services/model-service/src/services/nfl_season_engine/__init__.py` | `72efa0ecc0f224b600bee0ece371999ed9bb6513765e39e1ab4a65d844a13adb` |
| `services/model-service/src/services/nfl_season_engine/adjusted_sos.py` | `3f394100a85942d763f04bf7fc373d7af7d424c77ee254cda774222ecc2d95ae` |
| `services/model-service/src/services/nfl_season_engine/calibration.py` | `525b7f11f2bdf5556f78424f0616d2b460503727925bfeaf0628fc9d63bc59a0` |
| `services/model-service/src/services/nfl_season_engine/coaching_staff.py` | `007a7f9f844c0ff099a59dfe006aa78f4960d35001d8df3af6e4f184745296ae` |
| `services/model-service/src/services/nfl_season_engine/coaching_tendencies.py` | `ce0e2a4fa7d81166415ca58fe4ad816e63458d091c32cf3e0093d5120ae5c660` |
| `services/model-service/src/services/nfl_season_engine/continuity_score.py` | `bed1d0f4cc853ae2d460c51db9fde8b3633997dee6eae63ae884e77272c21ddb` |
| `services/model-service/src/services/nfl_season_engine/data_integrity.py` | `ec137321b00788efa3ec21778fbacbd7dfffa82b6672b7b01fd8e272cb6ff15e` |
| `services/model-service/src/services/nfl_season_engine/depth_chart.py` | `8bbfd6d0e282fa2eaf40d3f04cf73cfb20edccf5638eed045f4e5871891f301c` |
| `services/model-service/src/services/nfl_season_engine/efficiency_backbone.py` | `4e4250e066f92432128aa6d0f87d38e7a030cd6102563f22672d7c2b5322bb8e` |
| `services/model-service/src/services/nfl_season_engine/game_query.py` | `ba3b12acf1fa982869515970e315525c569a8bfbfc2df1529ad14f974a3511f2` |
| `services/model-service/src/services/nfl_season_engine/game_script.py` | `f1fd21a73ed9349fe8846e10dded898289c9175aaa660467b1293cc80e259e04` |
| `services/model-service/src/services/nfl_season_engine/historical_replay.py` | `8109b9df13265540c7c784d76a88163492e6fb103959d2e42ce9490f83d2e711` |
| `services/model-service/src/services/nfl_season_engine/injury_paths.py` | `2a952b33188539ca7ac6f16f011aaeabdde0faa1887292ee7f3d57c4e9a8e567` |
| `services/model-service/src/services/nfl_season_engine/kicker_layer.py` | `08aa729249f047419ce97cd5a5fb758c0675a161945d377d09314c5554977f6d` |
| `services/model-service/src/services/nfl_season_engine/loaders.py` | `a191894b57085771dc88e65c3e2fe9c1a8a0904046603af380a13419d4bfff76` |
| `services/model-service/src/services/nfl_season_engine/ol_protection.py` | `8a1965279346b97047a4f55a29648973961a092cd4678bc84476a872c5d10998` |
| `services/model-service/src/services/nfl_season_engine/player_regression.py` | `e7968209fd051456e2a6b28b1ede01e4662d37c63f2a2212f738b7e7a244e6eb` |
| `services/model-service/src/services/nfl_season_engine/player_usage.py` | `7090bb6ab148efaee16297f512b02abb12ada95f20f9e2b020fa0864d49a4098` |
| `services/model-service/src/services/nfl_season_engine/power_ratings_desk.py` | `873e15f167054ff1353721d9d041153d1f85c382274c22848226d874ecea5aa6` |
| `services/model-service/src/services/nfl_season_engine/production.py` | `5f99b6d5a477ba19093114daf3f862bd45f3539b7c61fa6d1569ceb9a2db6f90` |
| `services/model-service/src/services/nfl_season_engine/projected_sos.py` | `125e89505bb6c960bf73be745e9468dbc69138e005f15b9b79c086f4fa89a74f` |
| `services/model-service/src/services/nfl_season_engine/qb_premium.py` | `4a165933509c9e4c551e5ee9dd82b09afe2f6a1622602ddd01054b0a5d198373` |
| `services/model-service/src/services/nfl_season_engine/qb_rushing_profile.py` | `4fbf188fe036af96f68973559cfcc87be59bc7fc333736675cc656482d6af41e` |
| `services/model-service/src/services/nfl_season_engine/red_zone.py` | `053291c3fa709439f4b4cb7bfbfa7431059eabb6761c6958041ef6f382677213` |
| `services/model-service/src/services/nfl_season_engine/scoring_bridge.py` | `35e3a4a9b5dfe6f5bb64e7db05d9f6bc74d423f5c99f8580e4ed9c1bfcfa4b20` |
| `services/model-service/src/services/nfl_season_engine/season_budgets.py` | `d9a157a5994ac1600cfe94fae23dd70dbbe819fa5d08735cac5987562f7203d8` |
| `services/model-service/src/services/nfl_season_engine/season_sim.py` | `4137bc7cd7a63b8b02b7d461448f093c39079fd1091457d0e1cbc0f429387eaf` |
| `services/model-service/src/services/nfl_season_engine/sim_depth.py` | `0ddf65f4f45c1006fcbfb2df397937ec155a1ed8f90e37b204a30db5d6ea98a1` |
| `services/model-service/src/services/nfl_season_engine/survivor.py` | `30510e9bde0d23f866f49cc4cc3174032a4cd592149021e8407ad4a71cc265b1` |
| `services/model-service/src/services/nfl_season_engine/team_strength.py` | `900b2868ca0f736144652aca1908cae0cafc8f959f8e9f9c200d07a6aef26b05` |
| `services/model-service/src/services/nfl_season_engine/true_pr_product.py` | `baa706535add1343a26aa3e94ab0e78c723c4138caf61a71b8d5cf0e4d2dd6bd` |
| `services/model-service/src/services/nfl_season_engine/types.py` | `946b1af4e89ddfd9344891113aa9c957698df5c40a1c43f159d22cbd5be30674` |
| `services/model-service/src/services/nfl_season_engine/usage_roles.py` | `f6f08039d5468fb2a74ea460c8afc8e2bf2fce322dd3a899a86183f704866c83` |

module_count: 33

## Sibling engine modules changed on this head

| path | sha256 |
| --- | --- |
| `services/model-service/src/services/nfl_simulator.py` | `93a5656c8e725eb4759e1d50f58adfd8ad585c19dd265ae3014e3ae23c763639` |
| `services/model-service/src/services/nfl_handicapping_framework.py` | `e2becbcac532806f8cc01c2c8dc43fca36be30f2d1c09350064ed3aee47f7d5f` |
| `services/model-service/src/services/nfl_tendency_pricing.py` | `007ebbb13e96eed4454dc4ecf07737890507b7d68895c592178673e8315582c4` |
