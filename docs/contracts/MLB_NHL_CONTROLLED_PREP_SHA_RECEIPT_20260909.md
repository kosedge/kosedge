# Lane B — SHA & hash receipt (MLB/NHL market contract)

## Base (preflight)

- `origin/deploy-vercel` tip: `4bd0f87de71d23cca8d61c980530a0902b3e8b36`
- PR #504 NHL Edge Board honesty: `2832bc5f…` MERGED (ancestor)
- Later production (#505–#509): odds budget + NFL customer-truth + camp desk — **not** mutated this lane

## Frozen production pins (must remain unchanged)

| Artifact                                                  | Note                                             |
| --------------------------------------------------------- | ------------------------------------------------ |
| `apps/web/lib/nhl-trusted-market.ts`                      | `NHL_LEAN_EDGE_PTS=2.5`, `NHL_PLAY_EDGE_PTS=4.0` |
| `apps/web/lib/nhl-edge-board-display.ts`                  | Puck Line / Game ML OT/SO labels                 |
| `apps/web/lib/mlb-edges.ts`                               | desk mins 0.02 / 0.5 — not retuned               |
| Any `app/(pro)/pro/mlb/**` or `app/(pro)/pro/nhl/**` page | no edits this lane                               |

## Lane B branch

- Branch: `cursor/mlb-nhl-market-contract-prep-ae7a`
- Generating commit: `20694a4feb08d5558617c81faad504beff5b56c7`
- Evidence commit: _(filled at acceptance tip)_
- Acceptance tip: _(filled once after evidence)_

## Demonstrated non-changes

- No production UI edits
- No PLAY/LEAN threshold derivation
- No deploy / production-ready PR
- Isolated from Lane A (`cursor/ncaam-neutral-hca-prep-ae7a`)
