# Provenance v5

No secrets. Paths are package-relative (B-4).
- Frozen-fit HEAD: `8e2a15ac581277ecda71ea745c3b3477185d733b`
- Expected-answers commit: `852fe21c638532f45fd57ea55668716b49266e49`
- Spec `a156459b545e3b7d6a483f1db34cda7a4d32fc3afc70ed499b3adc726b1b6881` acceptance `54bc78ecc70e6a440481253b9c7eeef0e749690e893f501862f5dd5c54444574` ruling `0e0d54bc14e47bb3ef817b4e2dd135baa24ccff2a686eccbf5f5cab38fc1130c`
- Export `a38a55bb765e977ed88f8808d76715faddf50098b2354b122a5499f0ec706ac8` fit `6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657` expected `df516feda5ac8a1d4db26a397af83f7bb9c33db2dc11a3df38e31d9bbfbdcbb8`
- Seed 20261023 numpy.default_rng n_boot=10000
- Sigma margin 13.5 from C-10 services/model-service/src/services/nfl_injury_null_contract.py L339-341; L410
- Sigma total 14.0 pre-registered in inputs/sigma_preregistration.md
- Command: `python3 run_injury_residual_evaluator.py --mode all`
- Close: nflverse REG spread_line, comparative research, not certified CLV, metric close vs outcome
- NFL_TOTALS_*: unset. Tokens: none.
- B-3: B-3 export timestamp census present_keys=['applied', 'as_of_ts', 'complete', 'continuity_source_away', 'continuity_source_home', 'delta_margin', 'delta_total', 'game_id', 'kickoff_utc', 'season', 'source_ts', 'source_ts_away', 'source_ts_home', 'week'] n_source_ts=2852 n_as_of_ts=2852 n_kickoff_utc=2852 n_games=2863

