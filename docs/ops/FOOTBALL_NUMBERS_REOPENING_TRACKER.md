# Football numbers reopening tracker

**Authority:** Ryan OS 2026-09-15 (locked).  
**SoT:** this file + machine rows in [`football-reopening-tracker.json`](./football-reopening-tracker.json).  
**As of:** 2026-09-15.  
**Posture:** Coming soon is live. NFL and CFB public number boards stay dark until **that sport** clears its gates and CoS CLEAR. Trustworthy numbers first. No silent board reopen. No model change from this tracker.

This is the single enterprise tracker for Kos Edge football **published numbers** (fair / KEI / edges / power that customers can see). Editorial desk copy, fantasy DFS without house KEI, and non-football sports are out of scope.

---

## How to use

1. Update the matching row in the JSON twin, then the table here (same `id`).
2. Status vocab is closed: `NOT_STARTED` / `IN_PROGRESS` / `BLOCKED` / `PASS` / `FAIL`.
3. Leave **owner**, **evidence**, or **blocker** blank rather than invent.
4. A research ADVANCE is not a reopen PASS. One successful run is not enough.
5. Spreads and totals may CLEAR on different dates. Do not bundle them.
6. Flipping `NFL_EDGE_BOARD_PUBLIC_ENABLED` or `CFB_EDGE_BOARD_PUBLIC_ENABLED` is a **Release** action after CoS review — not a side effect of a research merge.

---

## Locked current state (2026-09-15)

| Fact                                          | Evidence                                                                                                                                                                                                                                                                                                                       | Implication                                                                  |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| Coming soon live for NFL + CFB public numbers | [#561](https://github.com/kosedge/kosedge/pull/561) merge `9b6669e5`; Production Smoke **PASS** [run 35002902210](https://github.com/kosedge/kosedge/actions/runs/35002902210)                                                                                                                                                 | Customer surfaces fail closed. No invented KEI / fair / PLAY.                |
| CFB opp-adj O/D EPA research ADVANCE (sealed) | [#560](https://github.com/kosedge/kosedge/pull/560) merge `60ec7051`; [`docs/cfb/CFB_RESEARCH_OPP_ADJ_EPA_AUDIT_2026-09-15.md`](../cfb/CFB_RESEARCH_OPP_ADJ_EPA_AUDIT_2026-09-15.md); [`data/ops/cfb-research-opp-adj-epa-20260915/ryan_audit_560.json`](../../data/ops/cfb-research-opp-adj-epa-20260915/ryan_audit_560.json) | Efficiency research only. `production_promote=false`. Not a spread or total. |
| CFB scoring research in flight                | #560 audit next path + agent [CFB research: efficiency → points/margin/total](https://cursor.com/agents/bc-c2ffc94b-f6dc-52ce-877e-d72e9fbd61ba)                                                                                                                                                                               | Do not reopen on EPA MAE. Status `IN_PROGRESS`.                              |
| CFB kill switch / board dark until CLEAR      | `CFB_EDGE_BOARD_PUBLIC_ENABLED = false` in `apps/web/lib/cfb-edge-board-public.ts`                                                                                                                                                                                                                                             | Independent of NFL.                                                          |
| NFL public numbers parked until CLEAR         | `NFL_EDGE_BOARD_PUBLIC_ENABLED = false` (same module, #561)                                                                                                                                                                                                                                                                    | Independent of CFB.                                                          |
| NFL regression investigation                  | **IN_PROGRESS** — #564 diagnose `cf0324f1`; remediating path in flight ([#564 remediation](../../data/ops/nfl-564-remediation-20260915.md))                                                                                                                                                                                 | Pre-model-change diagnosis + fail-closed remat. Not a reopen.                |

Parked customer surfaces (from #561; not an exhaustive product IA): `/edge-board/nfl`, `/edge-board/cfb`, `/pro/nfl/edges`, `/pro/cfb/edges`, `/pro/nfl/fair-lines`, `/pro/cfb/fair-lines`, `/pro/power-ratings/nfl`, `/pro/cfb/teams`, `/pro/nfl/slate/[date]`, homepage Edge Board hero, NFL/CFB overview widgets that painted edge pts, NFL pick’em. Assemble returns 503 empty while disabled.

Not parked: Club Desk / camp recap, fantasy DFS without house KEI, MLB / NBA / CBB / WNBA number surfaces, research libs / remat.

QA without reopen: `NFL_EDGE_BOARD_INTERNAL=1` or `CFB_EDGE_BOARD_INTERNAL=1` (and matching `NEXT_PUBLIC_*` for chrome).

---

## Owners

| Role                     | Call                                                                                      |
| ------------------------ | ----------------------------------------------------------------------------------------- |
| **CoS**                  | Execution call. Only CoS CLEAR enables a sport/market.                                    |
| **Product**              | Website verification — every listed surface shows the same approved numbers + provenance. |
| **Alex**                 | NFL model and NFL data / identities.                                                      |
| **Validation Lead**      | Predictive gates. Frozen eval vs predefined criteria.                                     |
| **Platform Reliability** | Production rehearsal, observability, rollback drills, smoke-contract fit.                 |

CFB model/data owner is blank until named.

---

## Status legend

| Status        | Meaning                                         |
| ------------- | ----------------------------------------------- |
| `NOT_STARTED` | No linked evidence package yet.                 |
| `IN_PROGRESS` | Work exists; gate not cleared.                  |
| `BLOCKED`     | Cannot proceed until a named blocker clears.    |
| `PASS`        | Reviewed evidence meets the gate as written.    |
| `FAIL`        | Evidence was run and missed the bar. Stay dark. |

---

## Tracks

NFL and CFB are **independent**. Shared protections apply to both but cannot reopen either sport.

| Track  | Public constants (must stay false until Release PASS) | Current board                           |
| ------ | ----------------------------------------------------- | --------------------------------------- |
| NFL    | `NFL_EDGE_BOARD_PUBLIC_ENABLED`                       | Coming soon / dark                      |
| CFB    | `CFB_EDGE_BOARD_PUBLIC_ENABLED`                       | Coming soon / dark                      |
| Shared | Provenance, pre-publish, rollback, smoke              | Protections live; reopen not authorized |

---

## NFL gates

Workstream **NFL regression investigation** is `IN_PROGRESS` (#564 diagnose `cf0324f1`; remediating ingest/EPA-or-refuse/overlays-off remat). Calculation integrity is the matching gate; it is **not PASS**. `production_promote=false`. Coming soon stays.

| Gate                  | Status      | Evidence                                                                                                                                                                                                                                                                             | Unresolved blocker                                                                                                     | Owner                | Next action                                                                                                                    | Last updated |
| --------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------ |
| Input integrity       | IN_PROGRESS | #564 remediating: W1 outcomes ingest path + readiness fold (`sample_size` 0→16, `last_game_date` 2026-09-14). [`data/ops/nfl-564-remediation-20260915.md`](../../data/ops/nfl-564-remediation-20260915.md); [`week1_outcomes_coverage.json`](../../data/ops/nfl-564-remediation-20260915/week1_outcomes_coverage.json). `current_week` advances past completed W1. | Live Railway ingest not yet attested on this remediating merge. Reopen-grade identity/venue/exclusion pack still incomplete. | Alex                 | Run `pull_nfl_outcomes` on Railway. Confirm live readiness `sample_size=16` and `current_week=2`. Do not treat ingest as Release. | 2026-09-15   |
| Calculation integrity | IN_PROGRESS | #564 diagnose + remediating: packaged EPA authoritative on batch remat **and** ad-hoc POST (EPA-or-refuse). W2 remat overlays OFF (`run_id=nfl-564-remediation-20260915-w2`, sha `11878ee10c52b541…`). Multi-matchup integrity **pass** on DET@BUF / CAR@ATL / ATL@PIT / CHI@CAR ([`multi_matchup_integrity.json`](../../data/ops/nfl-564-remediation-20260915/multi_matchup_integrity.json)). Scoring equation **not** edited. | Overlays remain OFF by design. Live W2 remat on Railway not attested. Predictive validation not run. Not a reopen PASS. | Alex                 | Keep overlays off. Shadow remat W2 dates with `force_overlays_off` + `prefer_packaged_epa`. Do not retune the equation.        | 2026-09-15   |
| Predictive validation | NOT_STARTED | Protocol exists: [`docs/lab/NFL_SPREAD_VALIDATION_PROTOCOL_v1.md`](../lab/NFL_SPREAD_VALIDATION_PROTOCOL_v1.md) (spread-only, `cos_signed`). Enterprise floors: [`docs/NFL_ENTERPRISE_GATES.md`](../NFL_ENTERPRISE_GATES.md). Totals PLAY remains sat (`NFL_SPREAD_PLAY_LOCKED.md`). | No frozen reopen eval has been run against predefined criteria for the candidate that would be shown. Protocol ≠ PASS. | Validation Lead      | Freeze eval rules (below), then run the unused/frozen package. Score margin and total separately.                              | 2026-09-15   |
| Production rehearsal  | NOT_STARTED |                                                                                                                                                                                                                                                                                      | No scheduled candidate runs that include weekly update, injuries, and missing-data paths.                              | Platform Reliability | Stand up private shadow (see §6). Exercise a weekly update, not a single snapshot.                                             | 2026-09-15   |
| Website verification  | BLOCKED     | Parked surfaces: #561. Prior display-contract work (not a reopen verify): [`docs/incidents/INC-2026-09-08-NFL-EDGE-BOARD-CUSTOMER-TRUTH/`](../incidents/INC-2026-09-08-NFL-EDGE-BOARD-CUSTOMER-TRUTH/). SOP v1.1 inactive suppress still stamps when numbers are shown.              | No approved NFL numbers to paint. Coming soon is not this gate.                                                        | Product              | After calculation + predictive PASS, INTERNAL-verify every parked NFL URL + assemble: same number, same provenance, no clamp.  | 2026-09-15   |
| Release — spread      | BLOCKED     | #561 Coming soon; `NFL_EDGE_BOARD_PUBLIC_ENABLED=false`                                                                                                                                                                                                                              | Upstream NFL gates not PASS.                                                                                           | CoS                  | Review evidence pack. Enable NFL spread only if that market’s gates PASS.                                                      | 2026-09-15   |
| Release — total       | BLOCKED     | Totals PLAY sat: `NFL_SPREAD_PLAY_LOCKED.md`. Coming soon #561.                                                                                                                                                                                                                      | Totals may stay dark after spreads CLEAR. Totals need their own predictive PASS.                                       | CoS                  | Do not piggyback totals on a spread CLEAR.                                                                                     | 2026-09-15   |

---

## CFB gates

Workstream **CFB scoring research** is `IN_PROGRESS` ([efficiency → points/margin/total](https://cursor.com/agents/bc-c2ffc94b-f6dc-52ce-877e-d72e9fbd61ba)). #560 sealed **opponent-adjusted EPA/play** only. Next authorized path is scoring → margin/totals conversion. Prior draft scoring PRs (#539, #543, #544, #546) are not reopen evidence and are not promoted here.

| Gate                  | Status      | Evidence                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Unresolved blocker                                                                                     | Owner                | Next action                                                                                                                       | Last updated |
| --------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ | -------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Input integrity       | IN_PROGRESS | #560 excluded incomplete PBP `401868140` (Q2 28–0 cut vs official 49–7). Closed set 84. Owned-metrics / W1 raw work: [`docs/cfb/`](../cfb/) (`CFB_OWNED_DATA_INVENTORY_GAP_2026-09-15.md`, `CFB_2026_W1_RAW_TEAM_GAME_METRICS_2026-09-15.md`). Historical P0 name-map: [`data/ops/cfb-p0-residual-audit-20260911.md`](../../data/ops/cfb-p0-residual-audit-20260911.md).                                                                                                             | Scoring conversion does not yet have a reopen-grade coverage / identity / freshness / exclusions pack. |                      | Finish scoring-path inventory: identities, freshness, explicit exclusions. Do not treat EPA holdout n as published-line coverage. | 2026-09-15   |
| Calculation integrity | IN_PROGRESS | #560 ADVANCE sealed: holdout n=1,713 / 930 games; MAE 0.1673 vs unadj 0.1911 / blend 0.1837; λ=40, n0=4, decay=0.75; `production_promote=false`. Audit: [`docs/cfb/CFB_RESEARCH_OPP_ADJ_EPA_AUDIT_2026-09-15.md`](../cfb/CFB_RESEARCH_OPP_ADJ_EPA_AUDIT_2026-09-15.md). `h≈0.244` is EPA/play on the home **offense** row — not a spread. In-flight conversion: [CFB research: efficiency → points/margin/total](https://cursor.com/agents/bc-c2ffc94b-f6dc-52ce-877e-d72e9fbd61ba). | Scoring / margin / totals conversion not sealed. EPA ADVANCE must not be published as KEI or points.   |                      | Continue scoring research. Reproduce conversion outputs. Close known bugs before any production candidate.                        | 2026-09-15   |
| Predictive validation | NOT_STARTED | EPA holdout is efficiency MAE, not spread/total ATS or close-MAE. CFB engine gates ([`docs/CFB_ENGINE_GATES.md`](../CFB_ENGINE_GATES.md)) are Week-0 research-engine checks, not this reopen eval.                                                                                                                                                                                                                                                                                   | No frozen scoring/margin/total eval against predefined reopen criteria.                                | Validation Lead      | After conversion exists: freeze eval rules, run unused/frozen package, margin and total separately + bias + calibration.          | 2026-09-15   |
| Production rehearsal  | NOT_STARTED |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | No private CFB candidate shadow that survives weekly update + missing PBP/odds.                        | Platform Reliability | Shadow beside the dark board. One holdout score ≠ rehearsal.                                                                      | 2026-09-15   |
| Website verification  | BLOCKED     | Kill switch + Coming soon (#529 lineage, #561 extend). `CFB_EDGE_BOARD_PUBLIC_ENABLED=false`.                                                                                                                                                                                                                                                                                                                                                                                        | Board dark until CLEAR. No approved CFB numbers to cross-check across surfaces.                        | Product              | After predictive PASS, INTERNAL-verify every parked CFB URL + assemble.                                                           | 2026-09-15   |
| Release — spread      | BLOCKED     | Kill switch off. #560 `production_promote=false`.                                                                                                                                                                                                                                                                                                                                                                                                                                    | Scoring research in flight; predictive + website gates not PASS.                                       | CoS                  | CLEAR CFB spread only from a reviewed evidence pack. Never from EPA MAE alone.                                                    | 2026-09-15   |
| Release — total       | BLOCKED     | Same as spread. Spreads and totals are separable.                                                                                                                                                                                                                                                                                                                                                                                                                                    | Same. Totals conversion is its own bar.                                                                | CoS                  | CLEAR CFB totals independently if evidence supports it.                                                                           | 2026-09-15   |

---

## Shared platform protections

These rows protect customers while sports are dark. They do **not** reopen a board.

| Gate                                              | Status      | Evidence                                                                                                                                                                                                                                                                                                      | Unresolved blocker                                                                                                       | Owner                         | Next action                                                                                                       | Last updated |
| ------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ----------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------ |
| Coming soon / kill-switch independence            | PASS        | #561 `9b6669e5`. Constants both `false`. INTERNAL overrides are per-sport. Production Smoke on that merge **PASS**. Tests: `apps/web/__tests__/lib/football-public-numbers.test.ts`.                                                                                                                          | —                                                                                                                        | CoS (policy) / Product (copy) | Keep both public flags false. Do not flip either from a research PR.                                              | 2026-09-15   |
| Provenance on every published number              | NOT_STARTED | Required fields listed in §4. Prior customer-truth contract: `apps/web/lib/edge-board-customer-truth.ts` (sign + line identity).                                                                                                                                                                              | No reopen candidate is publishing, so store↔page provenance for an approved snapshot is unproven on the parked surfaces. | Platform Reliability          | When a candidate exists, stamp version / snapshot / cutoff / gen time on store and page.                          | 2026-09-15   |
| Pre-publish checks                                | NOT_STARTED | Checklist in §4. Coming soon withholds (correct fail-closed).                                                                                                                                                                                                                                                 | Formal pre-publish job is not wired as the reopen gate; clamp-and-publish remains forbidden.                             | Platform Reliability          | Implement/attest the checklist against the candidate. Fail → withhold + explain.                                  | 2026-09-15   |
| Rollback                                          | NOT_STARTED | Reversible flags documented in #561 (public constant or INTERNAL).                                                                                                                                                                                                                                            | No drilled rollback of a **cleared** sport (flag off + stale-page check) because nothing is cleared.                     | Platform Reliability          | Write/attest: flip flag false, assemble 503/empty, pages Coming soon, no ghost table.                             | 2026-09-15   |
| Observability / smoke contract vs parked football | IN_PROGRESS | #561 smoke PASS ([35002902210](https://github.com/kosedge/kosedge/actions/runs/35002902210)). Later #560 push smoke **FAIL** ([35004134896](https://github.com/kosedge/kosedge/actions/runs/35004134896)): `/pro/cfb/teams` HTTP 200 missing needle `136` — expected once Coming soon parked the power table. | Smoke still assumes a live CFB teams census (`136`) after #561 parked that page.                                         | Platform Reliability          | Retarget smoke needles for parked football pages (Coming soon / heading), without treating that edit as a reopen. | 2026-09-15   |

---

## 1. Model vs handicap separation

- **Model / fair** is the house number from the production spine for that sport. It is not a book.
- **Handicap / KEI** is the published house line after the versioned menu (and only those documented steps).
- **Market** is a comparison layer (best / stake / consensus as labeled). Edge = fair-or-KEI vs the painted market line.
- Never silently overwrite fair with a discretionary “looks right” number, a book number, or an unpublished component.
- If model and handicap disagree, show both with provenance — do not hide the gap by blending market into research-fair math.
- Existing doctrine echoes: CFB research-fair must not contain market ([`docs/CFB_ENGINE_ONE_PASS_BRIEF.md`](../CFB_ENGINE_ONE_PASS_BRIEF.md)); NFL publish tags stay on `spread_play_v2_cap7` ([`NFL_SPREAD_PLAY_LOCKED.md`](../../NFL_SPREAD_PLAY_LOCKED.md)).

---

## 2. Component accounting

Add a component only if frozen validation improves **or** there is a documented operational need (identity, injury, weather feed). Avoid double-counting the same variance in two rows.

| Component                 | Counts toward                                              | Do not also count as                                                   | Reopen rule                                                                                  |
| ------------------------- | ---------------------------------------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| O/D strength              | Efficiency / power that drives expected score              | Pace, explosiveness, or matchup if those are already inside the rating | Must be PIT and opponent-adjusted only if that method is the sealed one                      |
| Pace                      | Play volume / tempo → totals and some margin variance      | O/D EPA/play (rate) treated as volume                                  | Missing pace → no silent default that invents a total                                        |
| Explosiveness / finishing | Big-play or red-zone conversion **beyond** base efficiency | Base O/D if the rating already includes scoring rate                   | Add only with an ablation that improves totals or margin, not because the narrative wants it |
| Special teams             | FG / punt / return expected points                         | Offense or defense EPA                                                 | Omit rather than impute if coverage fails                                                    |
| Personnel                 | Documented availability / depth that changes usage         | A second injury haircut on the same player                             | Depth SoT is who gets volume; do not steal starter share from last-year priors               |
| Matchup / conditions      | Residual after O/D + pace (weather, travel, rest, surface) | HFA counted twice; market “side” as a factor                           | Bounded, logged, killable                                                                    |
| Uncertainty               | Width / withhold / tag eligibility                         | A mean shift                                                           | Uncertainty may widen or withhold; it must not silently move the fair mean                   |

NFL factor freeze (product path, not a reopen PASS): [`docs/NFL_ENTERPRISE_GATES.md`](../NFL_ENTERPRISE_GATES.md) § Factor freeze. CFB #560 EPA is an O/D-strength research component only.

---

## 3. Eval rules freeze checklist

Freeze **before** looking at reopen-candidate results. Bump a protocol version to change a cut; do not edit silently.

- [ ] Chronological walk-forward only. No future week in a past fit.
- [ ] Point-in-time cutoffs on every rating, injury, and depth snapshot (as-of ≤ kickoff).
- [ ] Identical game set for model vs baseline vs market (same IDs; publish the exclusion list).
- [ ] Grade **margin** and **total** separately. Report signed **bias** on each.
- [ ] Calibrate means/errors **before** publishing cover / over probabilities.
- [ ] Predeclare strata (home/away, favorite/dog, week bands, roof, edge bucket). No post-hoc pooling to clear n.
- [ ] Timestamped market benchmarks (open and close owned, or documented join).
- [ ] Closing line is never an input to the number being graded against that close.

NFL spread protocol v1.0 is registered and spread-only. CFB scoring/margin/total reopen eval is **not** registered yet — Validation Lead writes that freeze before the first look.

---

## 4. Pre-publish protection checklist

Run on the candidate snapshot. Any fail → **withhold and explain**. Never clamp-and-publish.

- [ ] Version, snapshot id, data cutoff, generation time on the store row and the page.
- [ ] Identity / venue / kickoff agree across schedule, model, and market join.
- [ ] Freshness: as-of within the sport’s SLA; stale → withhold that game or the slate, as policy says.
- [ ] Finite numbers; correct units (points vs EPA/play vs yards); signs consistent with home/away and over/under.
- [ ] Cross-field consistency (home + away ≈ total; edge identity = painted market).
- [ ] Unexpected deltas vs prior snapshot flagged (team, game, slate).
- [ ] Extreme components flagged (HFA, weather, personnel) — not silently accepted.
- [ ] Store ↔ page agreement (same fair, same market, same edge, same provenance).
- [ ] Fail closed: Coming soon / omit / DATA GAP. No invented KEI. No ghost table.

When numbers **are** shown, SOP v1.1 NFL inactive fair suppress still applies (`stampInactiveFairSuppress`). Coming soon does not disable that path.

---

## 5. Spreads vs totals release separately

- A sport may CLEAR **spread** and keep **total** dark (NFL Week-1 doctrine already does this for PLAY tags).
- A sport may CLEAR **total** later, or never, without rolling back a valid spread CLEAR.
- Inverse is allowed if totals evidence is ready and spreads are not — still a CoS call.
- Shared kill switch today parks **both** markets per sport. A later split (spread-only public) needs an explicit product flag design — do not overload the current boolean without a tracker row.

---

## 6. Private candidate shadow

- Run the reopen candidate **beside** the existing (dark) system. Do not replace production means to “try it.”
- One successful batch is not enough.
- Must exercise a **weekly update**, including injuries / inactives and **missing** data (late PBP, missing odds, incomplete depth).
- Shadow output stays INTERNAL / research until Release PASS.
- Compare shadow vs frozen eval, not vs an operator’s preferred book.

---

## What this tracker does not do

- Does not reopen NFL or CFB boards.
- Does not change models, KEI, PLAY bands, or `production_promote`.
- Does not treat #560 EPA ADVANCE or #561 Coming soon as number quality PASS.
- NFL regression and CFB scoring agents are evidence of work in flight, not reopen CLEAR.
