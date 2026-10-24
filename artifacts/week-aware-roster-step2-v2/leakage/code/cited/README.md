# Cited production loaders (exact copies)

| file | sha256 | INV-1 symbol |
| --- | --- | --- |
| `run_injury_residual_fit.py` | `8d188da27d3c9f802acdca76763e1ca05e714040cc5ea3722e4922853f28167c` | `load_rosters` L289–314 |
| `holdout_frozen_row_builder.py` | `247744d23fef6f289e11da78523bdb007ada136f070916cf66a2bfee161e9cad` | `load_rosters_dir` L267–302 |

Byte-identical to the INV-1-cited artifacts. Do not execute `main` /
`build_rows` from these copies (those paths can touch le2023 raw).
T-PIT-10 execs only `load_rosters_dir` L267–302 against the synthetic
2098 season CSV. Holdout years are not passed.
