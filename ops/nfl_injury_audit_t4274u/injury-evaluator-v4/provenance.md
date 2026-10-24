# Provenance v4

No secrets. Paths are package-relative (B-4).
- Frozen-fit HEAD: `8e2a15ac581277ecda71ea745c3b3477185d733b`
- Expected-answers commit: `1712c256e510daec885574b701bfa893768a11d8`
- Spec `a156459b545e3b7d6a483f1db34cda7a4d32fc3afc70ed499b3adc726b1b6881` acceptance `54bc78ecc70e6a440481253b9c7eeef0e749690e893f501862f5dd5c54444574` ruling `1a090e3b58e440c79888662813f1a3d64c1761d4ae32d400170ee19a144eb20c`
- Export `d87e6129c451bbdc51d49eb7745a31ebb64ab6108ac58d8f8c4948dcc13e18e8` fit `6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657` expected `2ccdd7530c7a954f5ede635832a079548cfb92be6a98a0f4966b1c5932b6a1c1`
- Seed 20261023 numpy.default_rng n_boot=10000
- Sigma margin 13.5 from C-10 services/model-service/src/services/nfl_injury_null_contract.py L339-341; L410
- Sigma total 14.0 pre-registered in inputs/sigma_preregistration.md
- Command: `python3 run_injury_residual_evaluator.py --mode all`
- Close: nflverse REG spread_line, comparative research, not certified CLV, metric close vs outcome
- NFL_TOTALS_*: unset. Tokens: none.
- B-3: B-3 STOP: sealed export has no source_ts/as_of_ts on game objects; close/outcome join not performed. present_keys=['applied', 'complete', 'continuity_source_away', 'continuity_source_home', 'delta_margin', 'delta_total', 'game_id', 'season', 'week'] n_source_ts=0 n_as_of_ts=0 n_games=2863

