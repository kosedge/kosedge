# R7 recorded-date retrospective diagnostic — pre-result design decision

Codex decision, November 3, 2026. Candidate ID R7_RECORD_DATE_RETRO_C1. The original strict actual-kickoff/live-causal profile remains unchanged and DATA_HOLD. This is a separate descriptive research profile for already-consumed2020/21 DEV. No real candidate forecasts, historical rating solves, outcomes joins, scoring or bootstrap are authorized by this document. It authorizes metadata/synthetic implementation and independent design preflight; a later complete execution decision must name actual final code/data/runtime/claim hashes.

## Why this resolves a scientific choice rather than a permission queue

The requested correction is calendar-day rest. Exact historical actual-UTC kickoff/publication data are not established in the available records. Existing pinned PBP-derived schedule metadata does provide recorded historical game dates. A retrospective diagnostic can measure a correction based on those recorded dates while explicitly declining causal/pregame claims. It must not call a scheduled or recorded timestamp ACTUAL_KICKOFF, invent available_at or open the strict live profile.

Before model/error inspection, a metadata-only check found220/496 games with at least one changed rest cell relative to the frozen R4 matrix,297 changed team-side cells and182 games with asymmetric recorded-date rest. These are input diagnostics, not evidence of predictive benefit. The decision is made before any new R7 forecasts/outcome scores. There will be one candidate, no alternate rest conventions or ablations after results.

## Exact new rest rule

REST_RECORDED_GAME_DATE_RETRO_V1 uses the existing `game_date` field from hash-pinned `schedule_results_2020_2023.csv`, projecting only2020/21 REG identity/date metadata. It is a recorded football game calendar date, not a claim of independently certified actual UTC kickoff or publication time. Retain source byte hash, row number, raw date and naive start_time_raw for audit; never infer a timezone from that naive string or use it as UTC.

For each target and each canonical franchise, select the unique most recent same-season REG recorded game with a strictly earlier recorded date. Target/own game and later/equal dates are excluded. Equal latest dates or duplicate/conflicting identities refuse. Missing prior same-season record refuses; no7/default/cap/offseason fallback. Rest is target_recorded_date minus predecessor_recorded_date in integer days. This operation uses date arithmetic, not UTC hours/24. Home/away are calculated independently. Earlier same-assigned-week physical predecessors may be used for rest only; Q2/PBP features still forbid same-assigned-week scored history.

This profile deliberately does not assert that an exact predecessor event instant was verified before KO−60. It records that limitation. Source event-date chronology and strict previous-week feature/history rules govern this retrospective diagnostic. The source target kickoff/cutoff role is separately bound for history/market joins; do not convert the R4 field named pregame_cutoff_utc into a seal merely from its name. All96 independently checked rows equal kickoff, not KO−60. Before real execution, target nominal kickoff and KO−60 must be bound for all496 from an identified frozen source/derivation, checked against recorded date, without claiming an actual live timestamp.

## Inputs, mathematics and exposure

Use the frozen complete27-cell R4 REG496 feature matrix; retain every cell except the two declared rest values and canonical team identities. No raw PBP rebuild, new feature, score-label input, weight/bias/HFA change, weather/QB/market enrichment or tuning. Feature values are historical reconstruction from later archives; publication/observation status remains unverified. A field status string DERIVED_PREGAME does not establish historical availability. Preserve original source/context/hash and disclose retrospective lineage.

Fixed inputs:

- R4 reconstructed REG496 JSON SHA256282f979b52890c7ed943eeb9c0836dd7f50b9a925cf3e82fdfc856834646402c.
- R4 matrix SHA256a3b9d8ecb94902078ddcb89206a5a1ff16d5f1a3b4e8080186238d6578c52409.
- Recorded schedule source SHA2560853342304d269b55033d3474acda853ce00bdb10590f44b09ae569115148479; only2020/21 REG metadata, no target scores from this file.
- Original games metadata source SHA2564fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8; whitelist identity/season/week/team/nominal UTC kickoff only.
- Proposed score-history source SHA25650bda875daa8bf1aadd56dd0a3bc19f1bb52dafe42b6a9c921a5816c7d7dc081. This is an unopened pointer until separately authorized; permitted future role2013–19 REG initial/prior reconstruction plus strictly earlier assigned-week2020/21 REG history. No2017 evaluation, no2022/23 EVAL or protected2024–26 semantic read. The exact identity/REG filter and projected data hash must be independently sealed first.

Canonical state uses one franchise key before team sets, solve dimensions, lookup and carry; duplicate alias states refuse even if equal. Keep Q2 ridge20, prior carry0.5, initial2013None/zero and coefficients2.5637441292077354/1.660624056183471. Retain the new frozen source-default IF configuration adapter, original game-ID seed and4,000 draws, market blend0 and totals calibrationFalse. Keep C=0.5IF+0.5Q2, no extra HFA. Real historical ridge reconstruction is scientific execution even with fixed hyperparameters and remains blocked until the later complete grant.

No claim that an R7-minus-R5 error change isolates rest: franchise-state construction and newly pinned configuration are also different, and the historical effective R5 configuration is not fully recovered. No original artifact is overwritten. New run/claim/outputs must be distinct; original R5 consumed claim remains immutable.

## Fixed comparison and stops

Full cohort is the exact frozen496=240REG2020+256REG2021, old437/new59 retained separately; keep2021W18, exclude six2020wildcards. Identity digest6429f8596a1b605a9f1dc8aec21d81fc4454ff25e985dc77e691ec29d489c640. Same96 market identity558fbfe5de0344925e389650c28b8c0c42546cd98013c0a55968f67de6e7242e and frozen point-reference digest072e99e0c984fbd5ef87a2b419344c89148952a06b9185f52556147caeae70df. Market400missing stays excluded from that secondary comparison only.

Primary endpoint: mean(|R7_C-y|-|archived_R5_C-y|) on full496. Secondary: IF/Q2/C MAE/RMSE/signed bias full496 and per season; paired C-minus-IF and C-minus-R5 absolute loss full496/old437/new59/same96; same96 C-minus-frozen-market absolute loss. Report counts and all failures. No offered price is required for this point-error benchmark. There is no ATS/ROI/CLV/true-opener/true-close/calibration/market-edge endpoint. An unoffered cross-book median remains a statistical point reference.

If later authorized, uncertainty is paired season-week cluster resampling within season, B10000, PCG64 seed20261103; retain all games in sampled clusters and recompute pooled game-weighted statistic. Game sensitivity B10000 seed20261104, percentile2.5/97.5, never choose the favorable interval. Report cluster counts/season coverage and sparse96 selection. Descriptive consumed DEV only; no clean holdout or independent edge claim. No promotion of Q2 alone or NTBB-K from this point diagnostic.

Before any real model call or score-history/target-label transition, require full496 input coverage, exact final code/dependency/runtime/config/history/input/control/label/metric/exposure bindings, independent algorithm and service preflight, a distinct Codex execution decision and one atomic claimed context enforced at every real reader/caller independent of ENV. Missing/unknown required roles, nonfinite cells, forbidden rows, changed hash, cutoff/identity drift, claim failure or incomplete496 stops the intended experiment. No shrinking cohort, retrying a spent claim, automatic rerun, post-result convention change or failure deletion.

## Authorized implementation now

A may add an isolated RECORDED_DATE_RETRO profile, metadata projector and manifest validator with synthetic fixtures. It must refuse real execution until a distinct matching claim/GO is actually present; no fake or placeholder GO, no REAL mode shared by production, no ENABLE environment shortcut. Reader spies must prove zero real score/model/outcome/network/DB/job calls in metadata and invalid cases. Fake fixtures are visibly SYNTHETIC and cannot pass the future real-data gate. Test calendar/asymmetry/bye/alias/date ties/postponement records, target/week1/equal-date exclusion, and unchanged strict actual-kickoff profile. Current machine manifest remains NOT_EXECUTABLE until all real prerequisites are sealed.

The future predictive NTBB-K family is separate. It is not fitted or promoted by this diagnostic. Full eight-target/CERT0 and all reserved release, access, spend, protected-data and original-gate holds persist.
