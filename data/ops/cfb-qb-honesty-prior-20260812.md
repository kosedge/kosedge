# CFB QB Situation Honesty Patch + Prior Recompute

**Date:** 2026-08-12  
**Branch:** `feat/cfb-qb-honesty-prior-recompute` → `deploy-vercel`  
**Depends on:** #216 (efficiency + preseason prior, research-only)  
**Doctrine:** News → expert note → SoT override → recompute. No vibes. No KEI. Prior stays `used_in_spread: false`.

ESPN 2026 roster pack is **not** silently rewritten. Overrides live in one file and apply at universe load + prior build.

| Artifact | Role |
| --- | --- |
| `cfb_qb_situation_overrides_2026.json` | SoT overlay (`as_of=2026-08-12`) |
| `qb_situation_overrides.py` | apply at read time |
| `cfb_preseason_prior_2026.json` | regenerated |
| ESPN snapshot / `cfb_fbs_team_priors_2026.json` | unchanged identity feed |

## Override table (before → after)

Pack heuristic = ESPN 2026 roster QB1 by 2025 attempts. That is not a named-starter lock.

| Team | Pack (before) | Override | Name rule | Reason |
| --- | --- | --- | --- | --- |
| **UGA** | incumbent Ryan Puglisi (27 att), σ 4.27 | **open_competition** | keep pack listed name; **do not invent Stockton** (absent from ESPN) | Public starter Gunner Stockton missing from roster |
| **MICH** | incumbent Brayden Fowler-Nicolosi (82 att), σ 4.27 | **open_competition** | keep pack listed name; **do not invent Underwood** | Public No. 1 absent from ESPN roster |
| **FSU** | incumbent Dean DeNobile (347 Lafayette att), σ 4.26 | **open_competition**, QB1 **Ashton Daniels** (`4838679`) | Daniels is on ESPN roster; named starter 2026-04-21 | Heuristic ranked FCS attempts over Daniels (119). Elevated σ until games confirm |
| **LSU** | incumbent Landen Clark (277 Elon att), σ 4.26 | **open_competition**, QB1 **Sam Leavitt** (`5078810`) | Leavitt is on ESPN roster; public QB1 | Heuristic ranked Elon attempts over Leavitt (239). Elevated σ until games confirm |
| **ALA** | incumbent Austin Mack (32 att), σ 4.26 | **open_competition** | keep pack listed; do not lock Russell | Open camp Mack vs Keelon Russell |
| **UF** | true_freshman Tramell Jones Jr. (35 att), σ 8.02 | **open_competition** | keep pack listed; do not lock Philo | Open camp Jones vs Aaron Philo |

No other teams patched. PSU/BAY portal-class flags remain for a later note if we take them.

## Prior before → after (2026, seasons < 2026)

| Team | Mean before | σ before | Class before | Mean after | σ after | Class after |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| UGA | +16.69 | 4.27 | incumbent | **+13.69** | **7.65** | open_competition |
| MICH | +14.13 | 4.27 | incumbent | **+11.13** | **7.65** | open_competition |
| FSU | +10.42 | 4.26 | incumbent | **+7.42** | **7.65** | open_competition |
| LSU | +13.23 | 4.26 | incumbent | **+10.23** | **7.64** | open_competition |
| ALA | +16.07 | 4.26 | incumbent | **+13.07** | **7.65** | open_competition |
| UF | +7.52 | 8.02 | true_freshman | +7.92 | 7.65 | open_competition |
| OSU (control) | +19.07 | 4.27 | incumbent | +19.07 | 4.27 | incumbent |
| TEX (control) | +15.21 | 4.26 | incumbent | +15.21 | 4.26 | incumbent |
| BALL (control) | −3.62 | 7.65 | open_competition | −3.62 | 7.65 | open_competition |

Mean shift for incumbent → open is **−3.0 pts** (`QB_MEAN` +1.2 → −1.8). σ moves from the ~4.3 incumbent floor to the open-camp band (~7.65), matching BALL.

UF σ ticks **down** slightly (true_freshman 7.6 qb-σ → open 7.2) but the **label** is the honesty fix: it is a camp battle, not a locked freshman starter. Still clearly above OSU/TEX.

## Smell tests

- Patched teams: situation ≠ false incumbent; σ **7.64–7.65** vs OSU/TEX **4.26**
- FSU starter_name = Ashton Daniels; LSU = Sam Leavitt; UGA/MICH do not invent missing ESPN identities
- BALL still wide σ, last in mean
- Leakage tests green; project-game HTTP 200; `research_prior.used_in_spread` is false

## Remaining gaps

- Talent scores for FSU/LSU still inherit pack composites (DeNobile/Clark attempt heuristic). Class + name + σ are the patch; talent is still approximate.
- Open camp names that *are* on ESPN (Puglisi, Fowler-Nicolosi, Mack, Jones) stay listed so the feed is not empty — class is `open_competition`, not a lock.
- PSU Becht / BAY Lagway portal-class errors not in this minimum set.
- Still no published spreads from this prior. Walk-forward vs lake closes is next.

## Rebuild

```bash
python scripts/cfb/build_efficiency_preseason_prior.py --skip-efficiency --prior-year 2026

cd services/model-service
DATABASE_URL=postgresql://test:test@localhost:5432/test \
  pytest tests/test_cfb_qb_honesty_overrides.py \
        tests/test_cfb_efficiency_preseason_prior.py \
        tests/test_cfb_season_engine.py::test_status_and_project_game_http -q
```
