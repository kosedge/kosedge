# t5029u — Lane A CLEAR_ANNOTATE (DEV_RESEARCH)

**Label:** DEV_RESEARCH · CERT=0 · NFL NO-GO · research-consumed only · DRAFT  
**Mode:** passive offline annotation join. **Do not merge · do not deploy · do not pub/bet · no EVAL · no retune.**  
**NOT a forecast quality claim.**

## Authority

| Item                    | Tip / object                                                              |
| ----------------------- | ------------------------------------------------------------------------- |
| OWNER                   | t5029u                                                                    |
| Card                    | `20dd7940` CLEAR_ANNOTATE                                                 |
| Work-package rule       | `2db90f76`                                                                |
| Guardrails              | `52c79ee6`                                                                |
| #682 writer (read-only) | head `7d89a974` / ACCEPT `d17b30fa`                                       |
| #683 Lane A paper       | `eabd49a6`                                                                |
| Wiring card (N2)        | `013ec7f8` (supersedes `1e71808d`)                                        |
| ORDER N1                | `09f70480` (prefer this sealed ORDER-box tip; chat once cited `8a4bd0ab`) |
| Alex formula            | `fa36c679` — **NOT authorized**                                           |

CoS ORDER / CLEAR tips posted after this filing should be cited here when they land. This README names the tips that were in the OWNER work package at write time.

## What this is

Read accepted #682 `Q2AsOfSidecar` writer **outputs**. Exact identity join (`game_id` / `Game.key` = season+week+home+away per #681/#683) onto frozen **2013 REG W2** IF/demo inputs. Emit DEV_RESEARCH annotation labels **beside** rows.

The #682 writer is **not** rewritten and is **not** copied into this tree.

## Frozen-before-run

`frozen/FROZEN_MANIFEST_2013_REG_W2.json` is the sample SoT. Eligible identities only (16). Missing or mismatched rows **refuse** (fail-closed). No silent expansion of the sample.

## Pin binds (refuse-on-mismatch)

games `4fe1cdd7` · fit `70db070d` · FROZEN `aa2b47b3` / md `28c582a1` · as-of `cf514078` · score-only extract `50bda875`

Leakage: reuse `assert_asof_leakage` refuse-on-fail.

## Isolation (HARD)

Never mutate `offense_index_*` / `defense_index_*` / `margin_mu` / `market_blend` / L0.  
Never invoke `nfl_simulator` / `simulate_nfl_game`.  
No extra EVAL. No retune. No runtime / Layer-3 change.  
No edits to `routes/nfl.py` (N3 caller-of-record), `tasks.py`, `NflGameInputs`, ledger, or sealed `score_t4910u.py`.  
No scored `1ee90fac` columns (N4: games.csv provenance mention is keep-identical only).

Out of scope: strength/margin formula (Alex `fa36c679`). No #681 §8 amendment. No Stage C. No merge/deploy/pub/bet. No Odds spend. No 2024–25 / protected holdouts. No reopening Q2 EVAL.

## Reproduce

```bash
python3 research/q2_lane_a_annotate_t5029u/tests/test_lane_a_annotate.py -v
python3 research/q2_lane_a_annotate_t5029u/emit_lane_a_annotations.py
```
