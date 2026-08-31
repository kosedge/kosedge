# CFB Engine — Enterprise One-Pass Brief

**Repo:** `kosedge/kosedge`  
**Owner intent:** Close Week 0, fix the CFB research engine in place, make it look and behave like the house NFL/CBB engines. One spine. One `as_of`. Gates. Scorecard. No second model.

You (Cursor) will map the repo. The human does not know the file tree and will not pre-fill paths. Guessing paths is a fail. Inventing a second engine is a fail.

---

## PASTE THIS INTO CURSOR AGENT

```
You are working in kosedge/kosedge.

Follow docs/CFB_ENGINE_ONE_PASS_BRIEF.md exactly.
If that path does not exist yet, create it by copying the brief you were given, then follow it.

This is a two-phase job:
  Phase 0 = READ ONLY discovery. Map the real CFB spine. Write the audit.
  Phase 1 = implement only on paths named in the audit.

Do not edit the WP curve until the audit has real paths you opened.
Do not retune power off Week 0.
Do not train on UNC–TCU or any Week 0 result.
Do not promote E[wins] or natty % into KEI.
Do not write if team == "Utah" or if team == "USF".
Do not blend market into research-fair numbers.
Do not touch NFL, CBB, or MLB trees.
Do not invent a second CFB stack.

Start Phase 0 now. First message back should be the audit outline plus the grep commands you will run, then run them.
```

---

## 0. What “enterprise” means here

Not a new architecture. Not a rewrite. The engine already exists. Enterprise means:

1. **One spine** from results → power → margin → WP → season sim → field constructor → futures → KEI → published surfaces.
2. **One `as_of`** on every CFB research surface after Week 0 close.
3. **Research-fair numbers** never contain market.
4. **Reproducible dump** of canaries from a single command/script.
5. **Gates** that fail the build or fail the PR checklist if laws break.
6. **Scorecard** with before/after from the same functions.
7. **Blocker protocol** when the honest fix does not move Utah off a 5% tail — stop, do not stretch the scale.

If a layer is missing, document `NOT FOUND` and stop that layer. Do not build a replacement engine “so the scorecard has numbers.”

---

## 1. Why this pass exists

The published CFB surface is inconsistent and miscalibrated in a way that looks like noise, not a wrong top-7.

Symptoms (not licenses to special-case teams):

| # | Symptom | Real layer |
|---|---|---|
| 1 | Week 0 not closed; surfaces disagree on `as_of` | snapshot / publisher |
| 2 | Cupcake favorites not printing real 90s | margin → WP |
| 3 | USF-class win-total band as wide as (or wider than) OSU | year-shock + soft WP |
| 4 | Title % tails (Utah ~5%) | shock + field constructor using season tails |
| 5 | KEI at risk of becoming E[wins] or natty % | publisher / KEI definition |

Canaries — diagnostics only. Never appear as `if team ==` in code.

| Canary | Broken look | Fixed look |
|---|---|---|
| USF | E[wins] / band distorted | E[wins] moves **a lot**; win-total width **< OSU** |
| Utah | title % ~5% from tails | title % moves **a lot** down if WP+shock were the cause |
| Top-7 / OSU power | tempting to “fix” futures here | **barely moves** |
| UNC–TCU | tempting training point | **must not retune power** |

If Utah is still ~5% after a real WP + shock fix, write a blocker. Do not stretch the logistic / WP scale (the ~1.617-class constant, whatever the repo names it) to look like Vegas.

---

## 2. Laws (automatic fail)

Same class as NFL/CBB house gates.

1. One CFB engine. One `as_of`. No research-vs-site fork. No preseason sidecar that still ships.
2. Do not reshuffle top-7 power. Drift at noise only.
3. Do not train on Week 0. Close = ingest results + advance snapshot + re-sim from **existing** power.
4. Do not blend market into power, WP, shock, futures, or KEI. Market may exist only as a comparison column.
5. No team-id branches. No G5 haircut. No title-odds clamp.
6. Do not invent a second CFB stack.
7. Do not touch NFL / CBB / MLB. Shared helper that cannot be changed safely = blocker.
8. KEI is not E[wins], not natty %, not playoff %. Guard it. Do not redefine it into a projection dump.
9. Do not stretch the WP scale to Vegas.
10. Do not add dependencies, services, or a new package tree.
11. Do not reformat unrelated files.
12. Every published number in the scorecard must name the function that produced it.

---

## 3. Allowed work (this order only)

1. Map the spine (Phase 0).
2. Close Week 0 — one engine, one `as_of`.
3. Recalibrate margin → WP so cupcake favorites print real 90s.
4. Shrink year-shock so USF-class win-total band < OSU-class band.
5. Re-sim projections + 12-team futures with power-aware at-larges.
6. Guard KEI so season tails cannot become the published line.
7. Add gates, a canary dump script, and a before/after scorecard.

Anything else is out of scope, including “while we’re here” ranking polish.

---

## 4. Phase 0 — Discovery (READ ONLY)

**Stop condition:** No WP, shock, power, KEI, or publisher edits until `docs/CFB_ENGINE_AUDIT_WEEK0.md` exists and lists paths you **opened**.

### 4.1–4.4

Run the discovery commands in this brief (§4.1), identify the spine (§4.2), write `docs/CFB_ENGINE_AUDIT_WEEK0.md` with the required headings (§4.3), and freeze code edits until the audit lists opened paths (§4.4).

---

## 5. Phase 1 — Implementation

Only files on the audit allowlist.

### 5.1 Close Week 0

Close means: Week 0 FBS finals in results; records + remaining schedule + sim start-state reflect those games; every CFB research surface shares one post-Week-0 `as_of`; power used as Week 1 prior is still the pre-Week-0 spine (no refit). Idempotent.

Close does not mean: update power from UNC–TCU or any Week 0 result; blend Week 0 market; bump teams because they “looked real.”

### 5.2 Recalibrate margin → WP

Goal: large favorites on cupcakes print **real 90s**, not 75–85. Edit the existing mapper only. Prefer noise-floor / saturation / scale *application*. Do not fit to Week 0 results or lines. Do not change the named scale constant just to move Utah. Gate: power gap ≥ `T` ⇒ WP ≥ 0.90 on a neutral-or-home favorite against an out-of-class opponent.

### 5.3 Shrink year-shock

Goal: USF-class win-total width (P90–P10 or SD) **<** OSU-class width. Shock is variance, not a stealth rerank. No per-team shock multipliers.

### 5.4 Re-sim projections + 12-team futures

Field rules for 2026 (use repo CFB docs if they already state this; if code contradicts docs, record it):

- 12 teams
- Auto: ACC, Big Ten, Big 12, SEC champions
- One G6 auto: highest-ranked G6 team on the **engine’s ranking/power**, not highest E[wins]
- Remaining at-larges: **power-aware**, not raw win-total tails
- Top 4 on that same ranking get byes
- Title % = simulate the bracket after the field is built

### 5.5 Guard KEI

Read the audit definition. Assert published KEI ≠ E[wins] ≠ natty % ≠ playoff %. If KEI **is** one of those today, write `KEI_EQUALS_TAIL` blocker. Do not invent a new KEI formula.

---

## 6. Enterprise extras

### 6.1 Canary dump script

Add one small script in the existing CFB pattern (e.g. `scripts/cfb/cfb_dump_canaries.py`). Same function path the site uses. No duplicate math.

### 6.2 Gates file

`docs/CFB_ENGINE_GATES.md` cloned in tone from NFL/CBB gates if those exist. CFB-only test module next to existing tests if a runner exists; else manual PR checklist.

### 6.3 Lineage footer

`engine=cfb as_of=… sim_seed=… sim_n=… wp_mapper=… shock=… kei_def=…`

### 6.4 Research vs market wall

Market may join for comparison column on scorecard only. Zero market leakage into power/WP/shock/KEI.

---

## 7. Required deliverable files

| File | When |
|---|---|
| `docs/CFB_ENGINE_ONE_PASS_BRIEF.md` | this brief, in-repo |
| `docs/CFB_ENGINE_AUDIT_WEEK0.md` | end of Phase 0 |
| `docs/CFB_ENGINE_GATES.md` | Phase 1 |
| `docs/CFB_ENGINE_WEEK0_SCORECARD.md` | Phase 1 |
| `docs/CFB_ENGINE_BLOCKER.md` | only if a law forces stop |
| canary dump script on the existing pattern | Phase 1 |
| optional CFB gate tests next to existing tests | Phase 1 if a runner exists |

---

## 8. Done / not-done / blocker

### Done

- Audit has real opened paths
- One engine, one `as_of`, Week 0 closed, close is idempotent
- Cupcake favorites print 90s on the existing mapper
- USF width < OSU width
- USF E[wins] and Utah title % moved a lot (not 5.0 → 4.7)
- Top-7 power barely moved
- Futures rebuilt with power-aware at-larges
- KEI still not E[wins] / natty %
- Dump script + gates + scorecard exist
- Diff stays on the allowlist
- No team-name branches
- NFL/CBB/MLB untouched

### Not done

- Power rerank to match consensus
- Week 0 as a training set
- Market inside research-fair numbers
- A `cfb_v2/` folder
- Utah forced to a vibe number via ~1.617

### Blocker (successful use of this brief)

Write `docs/CFB_ENGINE_BLOCKER.md` and stop if:

- Utah title % still ~5% after real WP + shock work
- only remaining lever is stretching the WP scale
- KEI is implemented as a tail metric
- two live CFB stacks
- shared NFL/CBB helper cannot be changed safely
- year-shock cannot be named
- top-7 must move to make canaries “look right”
- canary dump cannot call the same functions the site uses

A blocker is acceptable. A beauty pass is not.

---

## 9. PR shape

One branch. Preferred name: `cfb/week0-close-wp-shock-gates` (cloud agents may use `cursor/cfb-week0-close-wp-shock-gates-*` prefix).

Commits, if split:

1. `docs: CFB Week 0 audit`
2. `feat(cfb): close Week 0 to single as_of`
3. `fix(cfb): WP saturation + shrink year-shock`
4. `feat(cfb): re-sim futures + KEI guard + canary dump`
5. `docs(cfb): gates + scorecard`

PR body must paste: allowlist, scorecard table, dump script command + output, confirmation no NFL/CBB/MLB files, confirmation no team-id branches, blocker file or “no blocker”.

---

## 10. Operator checklist (human review)

Review the audit or the diff against this list only. Do not review against “does Utah match Vegas.”

- [ ] Audit paths are real files
- [ ] `as_of` unique on CFB surfaces
- [ ] Top-7 power order and gaps essentially unchanged
- [ ] Diff has no USF/Utah/OSU branches
- [ ] Cupcake WPs are 90s for real gaps
- [ ] USF band < OSU band
- [ ] USF E[wins] moved a lot
- [ ] Utah title % moved a lot **or** blocker exists
- [ ] KEI gate exists; KEI is not E[wins]
- [ ] Dump script uses the live engine
- [ ] Market is comparison-only
- [ ] NFL/CBB/MLB untouched
- [ ] Scorecard numbers name their functions
