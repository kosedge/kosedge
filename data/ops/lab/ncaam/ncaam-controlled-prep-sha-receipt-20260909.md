# Lane A — SHA & hash receipt (NCAAM NEUTRAL)

## Base (preflight)

- `origin/deploy-vercel` tip: `4bd0f87de71d23cca8d61c980530a0902b3e8b36`
- Merged verification:
  - Phase 2.6F PR #500: `729c07ce…` MERGED (ancestor)
  - Phase 2.6F PR #501: `beae0013…` MERGED (ancestor)
  - B2-PACE-v1 PR #490: `9e755056…` MERGED (research challenger; materialize incumbent)
  - NHL honesty PR #504: `2832bc5f…` MERGED (Lane B context; not mutated here)

## Frozen content hashes (unchanged this lane)

| Artifact | sha256 |
| --- | --- |
| `apps/web/src/ncaam_lab/fair_b2_pace_v1.py` | `4a305870fbc55900336566531eca92cd4586d8a04edd62845bcc23a03112f5bd` |
| `apps/web/src/ncaam_lab/fair_b2.py` | `b2887148cd0c85e340c8e57367316660209e620f921b25ebe4b71b4aa6882148` |
| `apps/web/src/ncaam_lab/holdout_2425/venue_contract.py` | `9f48eb266c362c6ae5ed52ed6872293a8388ccb2611bcae05506ff0fb6f8486f` |
| holdout `seal/seal_receipt.json` | `82852e2460bf876d75aae647232860820a998814b4bef76c236bdf058f0ddca2` |
| holdout `seal_payload_sha256` | `af4fd4513272e8cc784de7db02d33c74c16b0a0ed7e256e851f3da73d5543d84` |

## Lane A branch

- Branch: `cursor/ncaam-neutral-hca-prep-ae7a`
- Generating commit: *(stamped after first code commit)*
- Evidence commit: *(stamped after Train-A diagnostics)*
- Acceptance tip: *(stamped once; no receipt chase)*

## Demonstrated non-changes

- No holdout unseal / join / score
- No production model promotion
- No PLAY/LEAN / KEI enablement
- No deploy / production-ready PR
- Isolated from Lane B (`cursor/mlb-nhl-market-contract-prep-ae7a`)
