# CFB P0 structural restore — NAME_TO_CODE + fail-closed + stamp honesty

**Date:** 2026-09-11  
**Branch:** `cursor/cfb-name-to-code-fail-closed-6630`  
**Base:** `deploy-vercel`  
**Draft PR only — do not merge.** Kill switch stays ON. No CFB public reactivation.

Ryan CLEAR: structural packaging restore only. No coefficient / market
shrinkage / clipping / Vegas retune.

## 1) NAME_TO_CODE (11 required + MOST distinct)

Shared SoT: `services/model-service/src/services/cfb_season_engine/name_to_code.py`  
Importer: `scripts/cfb/package_efficiency_2025_carry.py`

| Name | Code |
|------|------|
| Missouri | MIZZ |
| Arkansas State | ARST |
| Colorado State | CSU |
| East Carolina | ECU |
| Jacksonville State | JVST |
| Nevada | NEV |
| Old Dominion | ODU |
| Toledo | TOL |
| UAB | UAB |
| New Mexico | UNM |
| North Texas | UNT |

**Missouri State → MOST stays distinct.** Do not collapse onto MIZZ.

Twin maps in this PR:

- Conference pack: `conferences.py` `_FALLBACK` + `cfb_fbs_conferences_2026.json`
- Slate publisher aliases: `scripts/cfb/publish_official_slate_2026.py`
- Warehouse identity: `cfb_warehouse/identity.py` (`MIZ`/`MIZZ`, short names, MOST)
- Roster ESPN alias: `MIZZ→MIZ` in `package_real_roster_2026.py`
- Display overlay: `CFB_AFFILIATION_OVERLAY.CSU = Pac-12` (universe SoT, not MWC leftover)

## 2) Fail-closed rebuild/pack

Required official-FBS slate teams with missing power / efficiency / mapping
**hard-fail** (raise / non-zero exit). They do **not** hydrate Independent → 1.0.

- Efficiency pack: P0 official codes with no mapped SP+ row → `MissingRequiredTeamFeature` / exit 1
- KEI builder: `hydrate_missing_from_power_sot(..., required=slate∪P0)` raises
- Research-desk pack: P0 rows must have finite power before write
- Non-required / non-FBS placeholders may still sit or fill — never the 11

## 3) Stamp honesty (code path; frozen packs are a follow rematerialize)

W2+ mint **requires** env `CFB_CLOSE_AS_OF` distinct from Week-0 `2026-08-31`.

```bash
export CFB_CLOSE_AS_OF=2026-09-10
python3 scripts/cfb/build_cfb_kei_futures_2026.py --kei-only
```

Version constant: `kei_version_for_weeks((0,1,2))` → `cfb-kei-v1.0-2026w2`  
(`DOCUMENTED_W2_KEI_VERSION` in `cfb_kei.py`). Week-0 `apply_cfb_kei` identity
stays `cfb-kei-v1.0-2026w0`.

**TODO (Alex rematerialize on this branch — do not open a second PR):**
frozen `cfb_kei_w0_w1_2026.json` / web mirror still stamp
`cfb-kei-v1.0-2026w0` / `2026-08-31` after the 2026-09-10 mint. This PR does
**not** rewrite KEI/power numbers. After maps + priors exist, rebuild with
`CFB_CLOSE_AS_OF=2026-09-10` so production stamps match the mint.

## 4) Out of scope

- Kill switch `CFB_EDGE_BOARD_PUBLIC_ENABLED=false` (env cannot flip on)
- No CFB Edge Board public reactivation
- No PLAY / LEAN stake unsat
- No coefficient, shrink, clip, or Vegas retune
