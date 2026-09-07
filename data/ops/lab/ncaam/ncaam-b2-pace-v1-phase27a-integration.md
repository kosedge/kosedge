# B2-PACE-v1 Phase 2.7A integration receipt

**Append-only.** Does not rewrite Phase 2.5 Train-A diagnostics or feasibility receipts.

## Identity

- Candidate: `B2-PACE-v1` / `kenpom_adjem_pit_tempo_plus_game_hca_v1`
- Production base: `beae001342cdd15ad929e53783e6973530ffda44`
- HEAD at receipt generation: `515b32fb84d4f190e71608babea5f380297574f2`
- Originating formula commit (pre-rebase): `0d08b963014c5c3f51378cf4c2558cf0a8e287bc`
- Old impl ref used for parity bytes: `0d08b963014c5c3f51378cf4c2558cf0a8e287bc`

## Implementation hashes

| Side | sha256(`apps/web/src/ncaam_lab/fair_b2_pace_v1.py`) |
|---|---|
| Old (frozen) | `ae5a34cdc7a2d5324fe4b372e31820464c5f385fffba7583ff5ffa43cb123707` |
| New (2.7A) | `4a305870fbc55900336566531eca92cd4586d8a04edd62845bcc23a03112f5bd` |

## Frozen contract (unchanged math)

```
adjem_diff = clip(home_adjem - away_adjem, ±30)
possessions = (home_adjt + away_adjt) / 2
margin = clip(adjem_diff * possessions / 100 + 2.8696, ±28)
```

HCA pinned at `2.8696`; `weights_path` / mismatched custom HCA refused; non-finite AdjEM/AdjT/HCA fail closed.

## Train-A valid-domain parity

- Rows (valid-domain finite fair): **3676** (historical eligible 3676)
- `max_abs_fair_diff`: **0.0**
- Exact equality: **True**
- Incumbent B2 columns unchanged when challenger attached: **True**
- Materializer incumbent-only: **True**

## Holdout governance (additive)

- Phase 2.5 verdict ("no valid untouched OOS window") remains historically accurate.
- Current foundation from Phase 2.6F: `ncaam_holdout_2024_25_v1_1`.
- **No** features+labels open together, **no** performance calculation, **no** scoring, **no** unseal.

## Hard locks

No merge / deploy / promote / incumbent-default change. B2-PACE-NEUTRAL-v1 remains unimplemented. PR #490 stays draft.

---

## Acceptance restack (append-only, procedural)

- Historical production base (preserved): `beae001342cdd15ad929e53783e6973530ffda44`
- Acceptance base (live `origin/deploy-vercel` tip): `9d379818c548b09a4155a50624961ac93f1038aa`
- HEAD at append: `a10629c82990a4da547d6375100a4ab3928f15b2`
- Hardening commit (post-restack OID): `065bd6a16b8fb1b0e0383ae1c789cebad53ba37a`
- Impl sha256 unchanged: `4a305870fbc55900336566531eca92cd4586d8a04edd62845bcc23a03112f5bd` (old `ae5a34cdc7a2d5324fe4b372e31820464c5f385fffba7583ff5ffa43cb123707`)
- Train-A parity re-run: n=3676, max_abs_fair_diff=0.0
- behind vs acceptance base: **0**; merge-base == acceptance base
- Lab pytest: 69 passed; Holdout/DR: 70 passed; web-python-boundary: passed
- No merge / unseal / score / promote / default / math change
- Local Production Gate equiv: typecheck + Next build: passed

