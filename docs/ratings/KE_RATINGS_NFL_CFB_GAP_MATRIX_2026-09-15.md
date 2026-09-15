# KE Ratings gap matrix — NFL + CFB (amended 2026-09-15)

**Source inventory:** [PR #556](https://github.com/kosedge/kosedge/pull/556) `KE_RATINGS_ENGINE_EXISTING_INVENTORY_2026-09-15.md`  
**2026 CFB PBP path:** [PR #558](https://github.com/kosedge/kosedge/pull/558) proof + [path amendment](KE_RATINGS_CFB_2026_PBP_PATH_AMENDMENT_2026-09-15.md)  
**Constraint:** Docs only. Production NFL backbone and CFB SP+ compose are **unchanged**. No rating implementation in this PR.

**Proprietary KE Ratings Engine estimate remains ~28%.** Data on disk ≠ implemented/validated KE.

---

## 1. Scheme

Each cell has three marks:

1. **#556 live-path class** (unchanged vocabulary: REAL_AND_VALIDATED / REAL_UNVALIDATED / PARTIAL / PROXY / DEAD_CODE / PLACEHOLDER / MISSING).
2. **Data:** `DATA_AVAILABLE` or `DATA_MISSING`.
3. **Metric:** `IMPLEMENTED_VALIDATED` / `NEEDS_IMPLEMENTATION` / `NEEDS_VALIDATION` (or n/a if data missing and optional).

Rules:

- Opponent-adjusted KE is **NEEDS_IMPLEMENTATION / NEEDS_VALIDATION**, not DATA_MISSING.
- Havoc / ST: field-completeness first. Do not mark DATA_MISSING while flags/columns exist and are unverified.
- **PPA is optional.** DATA_MISSING only if we insist on CFBD PPA.
- CFB 2026 PBP is SDV (`pbp_current/as_of_YYYYMMDD/`), not CFBD-blocked.

---

## 2. NFL matrix

Live path (unchanged): nflverse PBP → situational / rolling → `efficiency_backbone` v1.1 → Layer-1 / Power desk / True PR / Edge Board.

| KE concept | #556 live class | Data | Metric | Notes |
| --- | --- | --- | --- | --- |
| Offensive efficiency | **REAL_AND_VALIDATED** | DATA_AVAILABLE | IMPLEMENTED_VALIDATED | EPA/play + soft additives; tests + ops smell tests |
| Defensive efficiency | **REAL_AND_VALIDATED** | DATA_AVAILABLE | IMPLEMENTED_VALIDATED | Same spine |
| Special teams | **REAL_UNVALIDATED** | DATA_AVAILABLE | NEEDS_VALIDATION | `st_kav` 2013–2025 cited; desk labels approximate; missing → `st_index=1.0` |
| Pace / tempo | **PARTIAL** | DATA_AVAILABLE | NEEDS_VALIDATION | Measured plays/game / 62. UI pack is PROXY |
| Explosiveness | **PARTIAL** | DATA_AVAILABLE | NEEDS_IMPLEMENTATION | Pass explosive live; **rush split not implemented** |
| Finishing | **PARTIAL** | DATA_AVAILABLE | NEEDS_VALIDATION | RZ TD rate in index; player RZ is a different product |
| Havoc / disruption | **PROXY** | DATA_AVAILABLE | NEEDS_IMPLEMENTATION | Pressure/sack exist; named havoc rate not built |
| EPA / PPA | **REAL_AND_VALIDATED** | EPA: DATA_AVAILABLE · PPA: DATA_MISSING (optional, unused) | EPA IMPLEMENTED_VALIDATED | No NFL PPA |
| Opponent adjustment | **PARTIAL** | DATA_AVAILABLE | NEEDS_VALIDATION | League-center + past SOS + KAV (not Layer-1). Not an external-data gap |
| Strength of schedule | **REAL_UNVALIDATED** | DATA_AVAILABLE | NEEDS_VALIDATION | Past SOS tested; projected SOS outlook only |
| Power ratings | **REAL_AND_VALIDATED** | DATA_AVAILABLE | IMPLEMENTED_VALIDATED | Method B Model PR |
| Team strength | **REAL_AND_VALIDATED** | DATA_AVAILABLE | IMPLEMENTED_VALIDATED | `TeamStrengthState` / True PR |
| Player strength | **PROXY** | DATA_AVAILABLE | NEEDS_IMPLEMENTATION | YPG / QB premium — not a KE player book |

NFL is the only sport with an owned play-level efficiency spine on the **live** path. That is why it carries most of the ~28%.

---

## 3. CFB matrix

Two worlds must stay split:

- **Live compose / KEI:** final-2025 SP+ carry + synthetic success / explosiveness / pace. **Unchanged.**
- **Owned PBP (research):** historical 2014–2025 lake (canonical, not rewritten) + **2026 SDV current-season** on `pbp_current/as_of_YYYYMMDD/`.

| KE concept | #556 live class | Data | Metric | Notes |
| --- | --- | --- | --- | --- |
| Offensive efficiency | **PARTIAL** | DATA_AVAILABLE | NEEDS_IMPLEMENTATION | Live = vendor SP+. Owned EPA (warehouse + 2026 SDV) not compose SoT |
| Defensive efficiency | **PARTIAL** | DATA_AVAILABLE | NEEDS_IMPLEMENTATION | Same dual stack |
| Special teams | **PROXY** | DATA_AVAILABLE | NEEDS_VALIDATION | 2026 raw has kick/punt/FG `type.text` + ~83 ST columns. Completeness first — not DATA_MISSING |
| Pace / tempo | **PROXY** | DATA_AVAILABLE | NEEDS_IMPLEMENTATION | Live = skill−F7 heuristic. Raw `scrimmage_play` available; `/pro/cfb/tempo` is placeholder |
| Explosiveness | **PROXY** | DATA_AVAILABLE | NEEDS_IMPLEMENTATION | Live = SP+ z. Raw EPA≥1 / yards≥15 available; warehouse explosive stored then dropped at adj |
| Finishing | **DEAD_CODE** | DATA_AVAILABLE | NEEDS_IMPLEMENTATION | `rz_epa_raw` / scoring-opp inputs exist; unwired |
| Havoc / disruption | **MISSING** (UI copy) | DATA_AVAILABLE | NEEDS_VALIDATION | 2026 flags: `havoc`, `TFL`, `sack`, `int`, `pass_breakup`, `forced_fumble`. Verify vs published havoc before any external-data claim |
| EPA / PPA | **PARTIAL** | EPA: DATA_AVAILABLE · PPA: DATA_MISSING (optional) | EPA NEEDS_IMPLEMENTATION (live) / NEEDS_VALIDATION (warehouse adj) | 2026 EPA retrieved via SDV. PPA not required |
| Opponent adjustment | **PARTIAL** | DATA_AVAILABLE | **NEEDS_IMPLEMENTATION / NEEDS_VALIDATION** | Warehouse 4-iter EPA adj exists (`used_in_spread: false`). Live uses vendor SP+. **Not NEED_EXTERNAL** |
| Strength of schedule | **PARTIAL** | DATA_AVAILABLE | NEEDS_IMPLEMENTATION / NEEDS_VALIDATION | Implicit in SP+ / season-sim; no owned SOS book |
| Power ratings | **REAL_UNVALIDATED** | DATA_AVAILABLE | NEEDS_VALIDATION | `cfb_power_sot_2026.json` — not PBP KE |
| Team strength | **REAL_UNVALIDATED** | DATA_AVAILABLE | NEEDS_IMPLEMENTATION | Compose indices from SP+; owned prior unused on live path |
| Player / QB / roster | **PARTIAL** | DATA_AVAILABLE | NEEDS_VALIDATION | Roster/QB class formulas exist; numerics approximate |
| 2026 W−1 raw form | *(#556: NEED_EXTERNAL)* | **DATA_AVAILABLE** (85 eligible games in the 2026-09-15 snapshot) | **NEEDS_IMPLEMENTATION** | Gate: actually-completed ∩ PBP ∩ `week < W`. 94 live-status PBP games excluded. 84/84 is STATUS_FINAL-in-snapshot only |

### 2026 reconcile (do not over-claim)

| | Count |
| --- | ---: |
| PBP games | 179 |
| `STATUS_FINAL` ∩ PBP | 84 — **snapshot only** |
| Actually completed ∩ PBP (W−1 eligible) | **85** |
| In-progress / unfinished PBP (excluded) | **94** |
| Unmatched PBP | 0 |
| Actually completed missing PBP | 0 |
| Schedule games with no PBP | 6 (mostly DELAYED 0–0) |

---

## 4. First bounded implementation task (recommended — not built here)

**Name:** CFB 2026 W−1 raw unadjusted team-game metrics, completed-games only.

This is **not** opponent-adjusted KE, not a live-compose swap, not havoc/ST ratings, not PPA.

### Inputs

- Versioned SDV PBP: `/Volumes/KosEdgeData/raw/cfb/pbp_current/as_of_YYYYMMDD/play_by_play_2026.parquet` (VM: `data/cfb/research/pbp_current/as_of_YYYYMMDD/`).
- Refreshed SDV schedule, same as_of folder.
- #555 `owned_metrics` definitions (`EPA_success` = EPA>0; explosive EPA≥1 or yards≥15; opportunity ≤40 yards-to-endzone).
- Completion gate from this proof: `actually_completed` (not `STATUS_FINAL`-only). Unfinished games excluded.
- W−1: `season=2026` and `week < W`.

### Outputs (research-only)

- Team-game table: `game_id`, teams, week, off/def EPA/play, success, standard SR, pace, explosiveness (pass/rush), down-split SR/EPA, opportunity / finish / start field position.
- Eligibility manifest: included `game_id`s, excluded unfinished/unmatched, schedule SHA, PBP SHA.
- No opponent-adj columns. No KEI / fair / Edge Board. No write to `raw/cfb/pbp/` (2014–2025 lake). No change to SP+ snapshot or compose.

### Validation criteria

1. **Eligibility:** every output row’s `game_id` ∈ actually-completed ∩ PBP; **zero** `IN_PROGRESS` / parked-0–0 rows.
2. **Coverage:** included count matches the reconcile manifest for that as_of (this snapshot: 85). Completed-missing-PBP list is empty or explained.
3. **Leakage:** `max(week) < as_of_week`; `assert_available_before_kickoff` if kickoff is known.
4. **Fields:** core-31 present; EPA null rate 0 on scrimmage plays used; no PPA invented.
5. **Checksums:** PBP/schedule SHA match the as_of folder; historical Aug 13 inventory files untouched.
6. **Isolation:** production CFB SP+ compose / KEI hashes unchanged; `opponent_adjusted=false` on every row.
7. **Honesty:** docs say “raw team-game metrics,” never “KE Ratings.”

**Out of scope for that first task:** opponent-adjusted KE, havoc/ST validation study, PPA, live-path unwire of SP+, Edge Board.

After that rollup exists, the *next* candidate (still not authorized here) is validating warehouse opponent-adj on historical PBP — still NEEDS_IMPLEMENTATION / VALIDATION, still not an external purchase.

---

## 5. STOP

- No rating implementation in this PR.
- No CFBD. No vendor shopping.
- ~28% estimate unchanged.
- Live NFL backbone and CFB SP+ compose unchanged.

**STOP.**
