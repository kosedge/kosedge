# CURSOR_RECEIPT — t5029u Lane A CLEAR_ANNOTATE

**Status:** DRAFT research filing. CERT=0. NFL NO-GO. Do not merge.

## Head

- Branch: `cursor/q2-lane-a-annotate-7e82`
- Head sha: `0119aac8090a4ea4a164f6fde1b4e4c80766c5cb`
- Base: `origin/deploy-vercel` @ `f5e3bb58`

## Changed

- `research/q2_lane_a_annotate_t5029u/emit_lane_a_annotations.py` — new annotation join adapter
- `research/q2_lane_a_annotate_t5029u/frozen/FROZEN_MANIFEST_2013_REG_W2.json` — frozen **before** run
- `research/q2_lane_a_annotate_t5029u/inputs/if_demo_inputs_2013_reg_w2.json` — IF/demo peer
- `research/q2_lane_a_annotate_t5029u/inputs/q2_asof_sidecar_t5018u.json` — byte-identical #682 output
- `research/q2_lane_a_annotate_t5029u/data/*` · `frozen/FROZEN_CONFIG_*` · `q2pb/*` — pin / keep-symbol copies (not rewritten)
- `research/q2_lane_a_annotate_t5029u/tests/test_lane_a_annotate.py`
- `research/q2_lane_a_annotate_t5029u/README.md` · `LANE_A_ANNOTATE_t5029u.md` · this receipt
- `.prettierignore` — ignore sealed FROZEN bytes + generated artifacts

## Not changed

- `services/model-service/src/services/nfl_simulator.py`
- `services/model-service/src/routes/nfl.py` (N3 caller-of-record)
- `services/model-service/src/tasks.py`
- `services/model-service/src/services/nfl_handicap_ledger/*`
- `NflGameInputs`
- sealed `score_t4910u.py`
- #682 writer `emit_q2_asof_sidecar.py` (not copied, not rewritten)
- live strength / IF `margin_mu` / `market_blend` / L0

## Citations

t5029u · card `20dd7940` · work-package `2db90f76` · guardrails `52c79ee6` · #682 `7d89a974` / `d17b30fa` · #683 `eabd49a6` · wiring `013ec7f8` · ORDER N1 `09f70480` · Alex formula `fa36c679` HELD.
