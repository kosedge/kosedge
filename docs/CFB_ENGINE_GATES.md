# CFB Engine Gates — Week 0 close pass

Tone cloned from `docs/NFL_ENTERPRISE_GATES.md`. CFB-only. Default posture: research-fair; KEI is the published **game** line, not a season dump.

## Status vocabulary

| Status      | Meaning                                              |
| ----------- | ---------------------------------------------------- |
| **GREEN**   | Clears the bar                                       |
| **YELLOW**  | Partial / document and watch                         |
| **RED**     | Fail — do not merge as “enterprise close done”       |
| **BLOCKER** | Law forces stop — write `docs/CFB_ENGINE_BLOCKER.md` |

## Checkable assertions

| #   | Gate                                                                                                                                          | Floor                                        | Code / checklist               |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- | ------------------------------ |
| 1   | Unique `as_of` across CFB research surfaces (power, projections, futures, KEI)                                                                | exactly 1                                    | `test_cfb_enterprise_gates.py` |
| 2   | Cupcake WP ≥ 0.90 when projected \|margin\| implies gap ≥ `T` (`priors.WP_POWER_GAP_T` on power units; margin saturation uses `WP_CUPCAKE_Z`) | WP ≥ 0.90                                    | mapper unit test + dump        |
| 3   | width(USF-class) < width(OSU-class)                                                                                                           | prefer `std`; p90−p10 when not discrete-tied | canary dump                    |
| 4   | Top-7 max-abs power drift                                                                                                                     | ≤ 0.01 (noise)                               | dump vs audit baseline         |
| 5   | KEI ≠ E[wins] ≠ natty% ≠ playoff%                                                                                                             | `assert_kei_not_tail`                        | `cfb_kei.py` + test            |
| 6   | Diff has no `if team ==` / `"Utah"` / `"USF"` special cases                                                                                   | zero                                         | PR `rg` checklist              |
| 7   | Path allowlist — no NFL/CBB/MLB trees                                                                                                         | zero                                         | PR checklist                   |
| 8   | Market not inside power / WP / shock / KEI math                                                                                               | zero                                         | PR `rg` checklist              |
| 9   | Utah title % moved a lot off ~5% **or** blocker file exists                                                                                   | one of two                                   | scorecard                      |

## Manual PR checklist

```bash
# Surfaces share as_of
python3 scripts/cfb/cfb_dump_canaries.py

# No team-id branches in the diff
git diff origin/deploy-vercel...HEAD -G 'if team ==|== "Utah"|== "USF"' -- '*.py' '*.ts'

# No NFL/CBB/MLB path edits
git diff --name-only origin/deploy-vercel...HEAD | rg -i 'nfl|cbb|mlb' && echo FAIL || echo OK

# Market leak into research math (should be empty in engine files)
git diff origin/deploy-vercel...HEAD -- services/model-service/src/services/cfb_season_engine/ | rg -n 'vegas|implied_prob|market_blend' || true
```

## Pytest module

`services/model-service/tests/test_cfb_enterprise_gates.py` — run with the existing model-service pytest runner. Does not stand up a new CI product.
