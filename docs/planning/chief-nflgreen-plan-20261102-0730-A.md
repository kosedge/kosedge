# Worker A — Model/data/E2E path audit

**Scope:** `chief-nflgreen-plan-20261102-0730` · **Worker A** · Cos sole synthesis  
**When:** 2026-11-02 06:43–07:05 EST · **CERT=0** · planning only · not EVAL · not GREEN · not #6  
**Authority:** OWNER CLEAR t5170u sha8 `eb248e91` (upload `OWNER_CLEAR_t5170u_PLAN_20261102_04a4.md`)  
**Eight-target text:** ADDENDUM t5027u sha8 `8667a122` (criteria INSPECTED, not weakened)  
**R5 CLOSED:** HARD END `08aa20a3` · ONE DEV CONSUMED tip `093a51dc` / stamp `3001dcc3` / bind `4eef5d1f` / claim `4fa6d856` · #701 DRAFT head `455a8e43` · HISTORY #703 tip `f7715dce` / stamp `8a7895b9`

**Verdict:** **0/8 full targets can close today.** Closest remaining distance is **#1** (function built; W8 calendar + IMV + E1 CLEAR remain). R5 market-behind-IF is **evidence, not tune permission.** Do not redefine IF-only / research-only / Coming Soon as GREEN.

---

## 0. Access proof (named paths)

| Path / object | Result |
|---|---|
| Upload OWNER CLEAR t5170u | READ · sha256 `eb248e91…` **MATCH** cited sha8 |
| Upload ADDENDUM t5027u | READ · sha256 `8667a122…` |
| Upload COS_HARD_END t5155u | READ · sha256 `08aa20a3…` **MATCH** |
| `NFL_8POINT_READINESS_SCOREBOARD.md` | **MISSING** this clone, `origin/deploy-vercel`, and `git log --all --diff-filter=A`. Criteria reused from ADDENDUM t5027u only. |
| `COS_8TARGET_BOARD_t4862u.md` | **MISSING** same sweep. Notion search returned 2026-09 product cards, not this board. |
| This branch HEAD | `8a7895b9` on `cursor/t5157u-r5-history-id-1adb` (#703 stamp). Thinner research lineage. |
| `origin/deploy-vercel` tip | `f5e3bb58` (`t4984u` noon-dedupe #678) |
| Frozen IF tree `/tmp/t5108u-if-6ca03716` | **PRESENT**. `nfl_simulator.py` sha256 `52d9e909…` **MATCH** pin. `nfl_handicapping_framework.py` sha256 `a0051cc4…` **MATCH**. Entry `simulate_nfl_game_independent_fair` L877 · `independent_fair_mus` L914. |
| This-tree `nfl_simulator.py` / `nfl_handicapping_framework.py` / `nfl.py` routes / `NFL_SPREAD_PLAY_LOCKED.md` / `docs/NFL_ENTERPRISE_GATES.md` / `nfl_offline_if_caller.py` | **ABSENT** on HEAD. Read via `git show origin/deploy-vercel:…` or the `/tmp` worktree. |
| Git objects present | `1b39f4e9` #657 merge · `6ca03716` W8 v2 packet · `b6d019b0` IF caller · `90bf65ab` v3 runner · `f7715dce` / `8a7895b9` #703 · `455a8e43` #701 |
| Git objects **missing** (cited, not in this clone) | `10ca67fe` HARD PASS · `89dcd61d` IF-only R1 · `4223362c` OWNER IF-only accept · `23b34ef3` P1 snap · `c7775dae` AC-S4/S6 · `1ee90fac` scored · `d359ce54` H-HL-1 protocol · `81b6c0fc` R3 STOP (cited in addenda; object absent) · `83646d78` / `50f57195` / `f8897f58` unverified seals |
| PRs via `gh` | #657 MERGED · #664/#688/#695/#697/#701/#703 OPEN DRAFT · #679–#683 OPEN DRAFT |
| Runtime Railway/Vercel invoke of IF/HL/joint | **NOT probed** (forbidden: deploy/config/runtime change). Marked UNKNOWN. |
| Protected 2024–26 / paid odds / outcomes join | **Not opened.** |

---

## 1. Actual current path (code + pinned artifacts)

Three stacks exist. Do not collapse them.

### Layer map (required)

| Layer | What it is | Where | Invoke status |
|---|---|---|---|
| **L1 repo symbols** | CLEAR-A Independent Fair + market-blend=0 assert | `origin/deploy-vercel` `services/model-service/src/services/nfl_simulator.py` `simulate_nfl_game_independent_fair` **L877** · `independent_fair_mus` **L914** · merge `#657` `1b39f4e9` · tip `f5e3bb58` | **Code present + merged.** Presence ≠ prod invoke. |
| **L2 accepted offline IF caller** | Fail-closed produce-μ / W8 diagnostic | Pins: IF tip `6ca03716` · sim `52d9e909` · fw `a0051cc4` · consume `score_t4910u` `@19c6a460` (cited) · caller commit `b6d019b0` (`nfl_offline_if_caller.py` — **not on this branch**) · this-branch adapter `nfl_t5107u/if_produce.py` `produce_if_mu` · `import_frozen_if` · `ensure_if_tree` | **Tested draft / research consumed.** Not E1. |
| **L3 deployed subscriber path** | Railway `nfl.py` + Vercel NFL hubs + public kill switch | `origin/deploy-vercel` `services/model-service/src/routes/nfl.py` (this-tree source **ABSENT**; pycache leftover) · `apps/web/lib/cfb-edge-board-public.ts` `NFL_EDGE_BOARD_PUBLIC_ENABLED=false` · Coming Soon heading · Fair Lines cert slot **unbound** | **Deployed behavior = parked / Coming Soon.** CERT=0. |

### Approved inputs → features → IF/Q2/joint → adapters → surfaces

```
owned PBP archive /Volumes/KosEdgeData/nflverse/archive/pbp/2026-11-01
  (2013–19 identity only on #703; 2020–23 REG via nfl_t5107u/inputs.py)
  refuse SEALED_SEASONS 2024–26
        ↓
inputs.extract_reg_games / sha pins
  games.csv 4fe1cdd7 · outcomes 50bda875 · quote manifest 6a1c1b37
  efficiency/index fields REQUIRED but often MISSING (if_control.REQUIRED_FIELDS)
        ↓
feature/state
  Q2: nfl_t5107u/q2.py  A_Q2/B_Q2 frozen · FIT_POLICY=TRANSFER_FROZEN_DEV_2013_2016
      asof_for_targets · verify_q2_transfer_policy  (no refit)
  IF: if_produce.produce_if_mu → frozen tree simulate_nfl_game_independent_fair
      if_control.resolve_if_margin  ARCHIVED vs RECONSTRUCTED vs IF_LEG_BLOCKED
  joint/challenger: builder.challenger_margin  0.5*mIF+0.5*mQ2  w frozen
      R3 w=0.75 STOP cited 81b6c0fc (object missing; code/tests assert STOP)
        ↓
IF/Q2/joint outputs
  builder.build_forecasts · r5_history_id.complete_q2_and_candidate
  IF496 bytes 96d3aa6f UNTOUCHED · Q2 completed eeb6fff7 · candidate 2f9a73e6
  one_run.bind_one_run  exec_scoring=BOUND_NOT_AUTHORIZED_UNTIL_COS_GO
  eval_result_contract  DEV_IF437 ≠ market contract; IF-only cannot satisfy EVAL
        ↓
HL adapter
  #664 DRAFT tip 7abf65a2  nfl_hhl1_capture/{schema,validate,gates,identity}.py
  NOT wired to tasks/routes/nowcast/simulator/CLEAR-A
  nowcast OFF; env cannot lift
        ↓
Market adapter
  nfl_odds_reader.join_quotes_at_cutoff  (owned 2020–23)
  nfl_odds_comparison_harness  SYNTHETIC only · CERT=0
  market_arm_freeze.py  B1 ∩ REG496 n=96  sha 072e99e0 / 558fbfe5
  evaluator.home_margin_from_handicap
  #701 DRAFT 455a8e43  market96 MARKET schema (descriptive; Q2 not a market substitute)
        ↓
API / UI / export / cache
  Public: NFL_EDGE_BOARD_PUBLIC_ENABLED=false
          FOOTBALL_PUBLIC_NUMBERS_HEADING="Coming soon"
          NFL_FAIR_LINES_CERTIFIED_RUN_ID=null
          /pro/nfl/edges + fair-lines + slate  summary="Coming soon"
  API refuse: #695 DRAFT bff7c734  apps/web/__tests__/api/nfl-c10-consumer-refuse.test.ts
  Export: #697 DRAFT 0aad8d75  test_export_kei_lines_nfl_c10_refuse.py
  Sign-out: #688 DRAFT 6f29b4a2  SportProHeader UserMenu (layout)
  This-branch FastAPI main.py includes ONLY edge_board_router — no nfl.py
  Cache: no IF/Q2/joint production cache found on this branch.
```

**R5 closed metrics (research DEV only; do not retune):** full496 MAE IF 11.191978 · Q2 10.834458 · candidate 10.852834 · cand−IF −0.339144. market96 n=96 MARKET 10.044271 beats IF/Q2/candidate. Candidate does **not** beat Q2 alone. PROTOCOL DEVIATION t5160u stands.

---

## 2. Targets 1–8 — four columns (unchanged full targets)

| # | Existing completed evidence (tip/sha/PR) | Real remaining code/integration gap | Missing runtime/empirical | Permission hold |
|---|---|---|---|---|
| **1 Pinned reproducible E2E** | EVAL_ONLY wiring `6ca03716` · caller `b6d019b0` · v3 runner `90bf65ab` · this-branch `if_produce.produce_if_mu` + `/tmp` tree `52d9e909`/`a0051cc4` **verified this run** · #703 identity 1792/77/0 @ `f7715dce` · IF496 `96d3aa6f` | L2 caller **not on this branch**; L3 not wired; sealed invoke at a **declared E1 tip** missing; recon matrix 2020–23 listed MISSING in `if_control.KNOWN_MISSING_ARTIFACTS` | W8 `DATA_READY` STANDBY ~2026-11-03 → IMV → OWNER E1. `10ca67fe` HARD PASS **object missing** | E1 CLEAR intact. No EVAL. No `--score`. |
| **2 Raw vs handicap fair separate** | `#657` MERGED `1b39f4e9` IF/HF/MIF ledger + `simulate_nfl_game_independent_fair` market_blend=0 · `#664` plumbing `7abf65a2` (55+ synthetic tests, DRAFT) | `#664` **not merged**, not wired to routes/tasks/CLEAR-A; no sealed live raw/adjusted rows | Live HL capture not run; adjustments-over-time absent | Live HL capture not CLEARED. H-HL-1 protocol `d359ce54` object missing. |
| **3 Timestamp + attribute HL** | `#664` L1 schema: `capture_id`, capture_ts triple, kickoff cutoff, missingness, reject reasons | No live attribution path; rating window UNRESOLVED (R3 residual on #664); no writer/parser/eval | Needs elapsed live events | Capture CLEAR + contracts missing. Nowcast OFF. |
| **4 Coherent spread/total/ML** | IF-only R1 cited `89dcd61d`/`4223362c` (**objects missing**) · builder joint 0.5/0.5 · market96 schema #701 `455a8e43` · `eval_result_contract` refuses IF-only as market EVAL | IF-only is a **subcheck**; joint market-relative check not live; L3 Fair Lines gates all `false` | Post-W8/E1 + market prices | Odds HOLD. IF-only ≠ full #4. |
| **5 Vig-correct book compare + economic edge** | Market arm freeze n=96 `072e99e0` · harness synthetic CERT=0 · B-lite PARTIAL cited · P1 snap `23b34ef3` **object missing** | Vig-correct **method** on sealed snap may exist in B-lite (unverified here). Economic-edge path not built | Validated forecast (#7) absent; no paid book compare | Odds HOLD. Paid pauses. Partial ≠ PASS. |
| **6 Fail-closed IF+HL+market** | Diagnostic `#6.1/#6.3` files exist **on commit `6ca03716`** (not this tree). Fail-closed units: `one_run.OneRunRefuse` · `IFProduceRefuse` · `test_nfl_t5116u_quote_hold_failclosed.py` · `#695`/`#697` DRAFT | E2E fail-closed across **live** IF+HL+market not assembled; HL+market adapters unwired | Live HL + market both HOLD | CERT=0 · not #6. Cannot claim path GREEN. |
| **7 Validated market-beating hypothesis** | S1 KILL · Stage C AMEND · scored `1ee90fac` BLOCKED (object missing) · R5: MARKET beats IF/Q2/cand on n=96 | No promotion/winner. Strength/consumption Needs ChatGPT `d7e0a6bc` | H6 lift + one pre-registered look + market prices + independent IMV | Stage C HOLD. Scored BLOCKED. Metrics ≠ tune permission. Exploratory. |
| **8 No uncertified forecasts to subscribers** | Public kill switch ON (`NFL_EDGE_BOARD_PUBLIC_ENABLED=false`) · Coming Soon copy live on www (observed) · `#695`/`#697` accepted **components** DRAFT · `#688` sign-out DRAFT | PASS needs controls on **intended cert surface**. Components not merged. Mobile 320–375 QA separate. AC-S4/S6 `c7775dae` **object missing** | No cert path; Fair Lines `CERTIFIED_RUN_ID=null` | CERT=0 · FREE_PUBLIC/pub/bet HOLD. Coming Soon ≠ #8 PASS. |

---

## 3. Controlling gates + explicit conflicts

| Gate | Source | Binding effect |
|---|---|---|
| Production contract | `origin/deploy-vercel:AGENTS.md` | Ships **only** via `deploy-vercel`. `restore-working-ui` is thinner shell — not production. |
| This-tree `AGENTS.md` | HEAD | Cursor-Cloud secrets/ops only. **Conflicts** with production-contract AGENTS.md (different file contents). |
| NFL PLAY lock | `origin/deploy-vercel:NFL_SPREAD_PLAY_LOCKED.md` + `docs/NFL_ENTERPRISE_GATES.md` | Spread PLAY only `spread_play_v2_cap7`; totals/prop PLAY sat. Betting-product GREEN ≠ eight-target GREEN. |
| Public paint | `cfb-edge-board-public.ts` | NFL public numbers OFF until CoS CLEAR. Cert slot unbound. |
| C10 HOLD | deploy-vercel AGENTS Railway clause | Bare model-service merge must **not** `railway up`. |
| R5 HARD END | `08aa20a3` | Do not restart workers/claims/scoring. Claim `4fa6d856` spent once. |
| R2 coverage HOLD / R3 STOP / Stage C / paid pauses | t5027u + t5155u/t5157u addenda | Preserve failed records + scoring exposure. |
| Workspace spine rule | `.cursor/rules/nfl-production-spine.mdc` | Player-production v3 is a **third** stack (props/fantasy/futures). Not the IF/Q2 eight-target path. |
| #679–#683 | OPEN DRAFT vs `deploy-vercel` | Q2 keep / sidecar / Lane A paper. **No merge.** Card `20dd7940` HOLD. |

**Top conflicts (do not paper over):**

1. **Three branches, three truths.** `deploy-vercel` `f5e3bb58` has L1 IF + production NFL routes + Coming Soon. This/#703 lineage has L2 research builder and **lacks** `nfl_simulator.py` / `nfl.py`. `restore-working-ui` is explicitly not production. A merge of #703 into `restore-working-ui` does not move L3.
2. **Two GREEN bars.** Enterprise ATS/CLV/PLAY lock vs eight research targets. Clearing one does not clear the other. Public boards are Coming Soon under **both**.
3. **Layer confusion.** L1 merged `#657` ≠ L2 offline invoke `6ca03716`/`b6d019b0` ≠ L3 subscriber paint. Tests importing IF (CLEAR-A) are Layer 1 only.
4. **IF-only ≠ #4.** Scoreboard/ADDENDUM: IF-only R1 is a subcheck. `eval_result_contract` also refuses IF-only as market EVAL.
5. **R5 vs market.** MARKET MAE 10.044 < IF/Q2/cand. That is **evidence against** promotion, not a retune ticket.
6. **Missing SoT boards.** `NFL_8POINT_READINESS_SCOREBOARD.md` and `COS_8TARGET_BOARD*` are not in git. Planning must not invent a ninth scoreboard.
7. **Cited seals not in clone.** `10ca67fe`, `c7775dae`, `23b34ef3`, `89dcd61d`, `d359ce54`, `1ee90fac` cannot be independently hashed here. Treat as **unverified citations** until objects are produced.
8. **C10 vs “start local / deploy.”** Railway production up requires explicit C10 CLEAR. Today packages must not touch api/worker/beat.

---

## 4. Smallest TODAY engineering subchecks (not full PASS)

Distinguish: **code present** · **tested draft** · **merged** · **deployed behavior** · **independently qualified performance**.

| Subcheck | State now | File/fn | Acceptance + fault tests | Prerequisites |
|---|---|---|---|---|
| A. Pin/tree identity | code+tree present; hash verified this run | `if_produce.IF_TIP/SIM_SHA256/FW_SHA256` · `/tmp/t5108u-if-6ca03716` · `locate_if_tree`/`ensure_if_tree` | Recompute sha256 of sim+fw; refuse if ≠ `52d9e909`/`a0051cc4`. Fault: missing tree → `IFProduceRefuse` (already coded). **No forecast.** | None. Read-only. |
| B. #1 D2 provenance map | tested draft on other tips; **not on this branch** | `b6d019b0` `nfl_offline_if_caller.py` · `6ca03716` packet · `if_produce.produce_if_mu` | Docs/receipt: L1/L2/L3 table with tips; confirm caller is not E1. Fault: any claim of E1/L3 invoke. | Do not run W8. Do not `--score`. |
| C. C10 empty/malformed **business** semantics | tested DRAFT, not merged | #695 `nfl-c10-consumer-refuse.test.ts` · #697 `test_export_kei_lines_nfl_c10_refuse.py` + fixtures `fair_lines_success.json` / `malformed.json` | Re-run **existing** DRAFT tests only. Inspect success-shaped empty vs transport error. Fault: treat HTTP 200 empty as certified numbers. | Reuse; no new scored tests; no merge. |
| D. Sealed-snap vig method | UNKNOWN vs B-lite | `market_arm_freeze.py` · `nfl_odds_comparison_harness.py` · cited `23b34ef3` | **Stop unless** Cos/Ryan confirm method is inside B-lite. If yes: algebraic vig identity on **already sealed** n=96 rows only. Fault: paid pull / new quotes / economic-edge claim. | Needs Ryan/B-lite scope. Else skip. |
| E. Unverified seal hunt | citations only | `10ca67fe` `c7775dae` `23b34ef3` `83646d78` `50f57195` `f8897f58` | Produce object or mark UNKNOWN. No invention. | Read-only `git cat-file` / artifact dirs. |
| F. Strength D1–D4 mechanical | **NOT AUTHORIZED** by t5170u | Alex `fa36c679` (not re-read as approved) | Only if Ryan names D1–D4 + `20dd7940` pick. | **Blocked.** Planning CLEAR makes no scientific choice. |

No speculative rebuild. No inherited tests that read real outcomes.

---

## 5. Mandatory rows (target/component → dispatch)

| target/component | exact source/evidence | actual gap | owner | next bounded Cursor work order | deterministic done criterion | dependencies/permission | realistic duration | success successor / failure fallback |
|---|---|---|---|---|---|---|---|---|
| Path map L1/L2/L3 | #657 `1b39f4e9` · `6ca03716` · `b6d019b0` · public flag false · this HEAD `8a7895b9` | L3 not IF/Q2; this branch missing sim/routes | Cos (synth) / Cursor Worker 1 | Docs-only pin inventory; re-hash `/tmp` tree; do not invoke sim | Receipt lists 3 layers + sha MATCH/MISS; zero forecasts | t5170u RO | 20–40 min | Successor: D2 provenance. Fallback: keep UNKNOWN on missing objects |
| #1 E2E pin | `if_produce.py` · IF496 `96d3aa6f` · #703 `f7715dce` | E1 tip + W8 DATA_READY + IMV | Calendar / OWNER E1 | **No E1 work today.** Optional D2 provenance note only | No `--score`; `outcome_loader_reads=0` if any script touched | E1 CLEAR **off** | n/a today | Successor after ~2026-11-03 W8 + E1. Fallback: stay IN PROGRESS |
| #2 raw vs HF | #657 merged · #664 `7abf65a2` DRAFT | Unwired plumbing; no live rows | HL owner | Do **not** merge #664. Optional RO re-read validate.py reject paths | Confirm still unwired (grep tasks/routes = 0) | Live capture HOLD | 15–25 min | Successor: capture CLEAR (not today). Fallback: keep DRAFT |
| #3 HL attribute | #664 schema only | No live attribution | HL owner | None today | — | Capture CLEAR missing | — | Calendar + live events |
| #4 joint | builder 0.5/0.5 · #701 `455a8e43` · contract refuses IF-only | Market-relative joint post-W8 | OWNER | Do not redefine IF-only as #4 | — | Odds HOLD · W8/E1 | — | After E1+odds |
| #5 vig/econ | market96 `072e99e0` · harness synthetic | Econ edge needs #7+odds; snap method unverified | Ryan / B-lite | **Package 2 only if scope confirmed** | Algebra on sealed snap **or** STOP Needs Ryan | Odds HOLD | 30–60 min **if** cleared | Success: method note. Fail: STOP, no invent |
| #6 fail-closed E2E | 6.1/6.3 on `6ca03716` · unit refuses here | Live HL+market absent | — | No #6 claim | — | HL+Odds HOLD · CERT=0 | — | Keep IN PROGRESS |
| #7 market-beat | R5 MARKET < models · S1 KILL · Stage C AMEND | Exploratory; cannot construct | — | **Forbidden** (no fit/tune/look) | — | Stage C · H6 · scored BLOCKED | — | Leave BLOCKED |
| #8 uncertified | Coming Soon ON · #695 `bff7c734` · #697 `0aad8d75` | Not on cert path; drafts unmerged | Product / Cursor Worker 2 | Reuse DRAFT tests; inspect empty-success semantics | Existing tests pass; no merge; no public flip | CERT=0 · FREE_PUBLIC HOLD | 30–50 min | Successor: cert path (not today). Fallback: keep Coming Soon |
| Scoreboard files | ADDENDUM 8667a122 only | Files not in git | Cos | Do not recreate bureaucracy | Cite MISSING | — | 5 min | Cos may attach external board; Cursor does not invent |
| AC-S4/S6 | cited `c7775dae` | Object missing | Worker B reuse | Hunt object or UNKNOWN | Hash or UNKNOWN | VERIFY not redo | 10–20 min | Worker B lane |

---

## 6. TODAY packages (max 2 Cursor workers + 1 integration owner + 1 reviewer)

Hard size: **2 isolated Cursor workers.** Cos synthesizes. Alex contradiction pass 07:15. Codex day plan 07:30. No repeated ACK loop. **No merge/deploy.**

### Package A — Pin/provenance (Worker 1)

- **Build:** none. Read `if_produce.py`, `/tmp/t5108u-if-6ca03716`, `b6d019b0` via `git show`, `origin/deploy-vercel` L1 symbols.
- **Tests:** sha256 rematch sim/fw only. Optional: import-path exists check. **No** `produce_if_mu` on real packets. **No** inherited outcome tests.
- **Fix:** docs/receipt only if a pin mismatches (report; do not retune).
- **Review:** one independent RO (Alex columns/guards only).
- **Chief disposition:** ACCEPT pin map or REJECT if anyone claims E1/L3/GREEN.
- **Done:** three-layer table + MATCH/MISS list + “not E1” sentence.

### Package B — C10 business semantics + missing-seal hunt (Worker 2)

- **Build:** none. Check out existing DRAFT tips `bff7c734` / `0aad8d75` **read-only** (or `gh` files).
- **Tests:** re-run the **already written** refuse tests only (`nfl-c10-consumer-refuse.test.ts`, `test_export_kei_lines_nfl_c10_refuse.py`). Inspect `fair_lines_success.json` empty/malformed-success vs transport.
- **Fix:** none unless a DRAFT test cannot be executed because of path/branch; then report, do not rewrite production.
- **Review:** one RO on semantics (200-empty ≠ certified).
- **Chief disposition:** VERIFY component still holds; still not #8 PASS.
- **Also:** `git cat-file` hunt for `c7775dae` `10ca67fe` `23b34ef3` `83646d78` `50f57195` `f8897f58` → hash or UNKNOWN.

### Package C — #664 still-unwired proof (optional slice of Worker 1, 15 min)

- Grep `nfl_hhl1_capture` against `tasks.py` / `routes` / `nfl_simulator` on `deploy-vercel` + #664 branch.
- Done: 0 call sites outside package + tests.

### Package D — vig method (NOT dispatched unless Ryan/B-lite)

- Only if Cos confirms sealed-snap vig-correct is inside B-lite.
- Algebra on n=96 `072e99e0` bytes already on disk. No new quotes.

### Package E — strength D1–D4 (BLOCKED)

- Requires `20dd7940` pick + named D1–D4. t5170u **does not** grant this.

### Package F — W8/E1 (BLOCKED today)

- Calendar: W8 DATA_READY wake ~2026-11-03. Then IMV, then OWNER E1 CLEAR. Not a Cursor package this morning.

**Integration owner (Cos):** merge A+B receipts; do not make a scientific choice; do not flip scoreboard.

**Reviewer:** one pass, columns/guards/semantics only.

---

## 7. What cannot close today (and why)

| Item | Why |
|---|---|
| Full targets 1–8 PASS | ADDENDUM t5027u unchanged: each needs W8 and/or live HL and/or Odds and/or cert path and/or independent market-beat. Scoreboard stays 0/8. |
| #1 E2E sealed invoke | **Calendar** (W8 ~2026-11-03) + **auth** (E1 CLEAR) + IMV. Functionality already built. |
| #2/#3 live HL | **Auth** (capture CLEAR) + **evidence** (elapsed live events). Plumbing is DRAFT. |
| #4 joint market | **Auth** Odds HOLD + **calendar** W8/E1. IF-only must not be redefined. |
| #5 economic edge | **Auth** Odds HOLD + **evidence** (#7). Snap method maybe later; not PASS. |
| #6 E2E fail-closed | **Auth** HL+market live. Diagnostic 6.1/6.3 ≠ path. |
| #7 market-beat | **Evidence** cannot be guaranteed. R5 already shows MARKET ahead. Stage C / scored BLOCKED. |
| #8 cert-surface PASS | **Auth** CERT=0 · FREE_PUBLIC HOLD · no cert path. Controls ON is a subcheck. |
| Merge #664/#688/#695/#697/#701/#703 | Explicit DRAFT≠merge. C10 HOLD on Railway. |
| Strength package | **Auth** — needs Ryan pick on `20dd7940` + D1–D4. Planning CLEAR forbids new scientific choice. |
| Missing boards / missing SHAs | **Evidence** — files/objects not in clone. Do not invent. |

---

## 8. Holds preserved

R5 CLOSED · claim `4fa6d856` spent · no restart · R2 coverage HOLD · R3 STOP · Stage C HOLD · paid pauses · scoring exposure · failed records · Odds HOLD · FREE_PUBLIC/pub/bet HOLD · #679–#683 DRAFT · $0 · CERT=0 · NFL NO-GO.

---

**ETA:** compact deliverable filed 2026-11-02 ~06:50 EST (ahead of 07:05). Cos synthesis 07:15 / Codex day plan 07:30. No further Worker A loop unless Cos asks a named-path reread.
