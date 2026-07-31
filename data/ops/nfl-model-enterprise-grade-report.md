# NFL Model Enterprise Grade Report

**Date:** 2026-07-31  
**Canary target:** `props-under-bias-20260731b-celery-props-task`  
**Related:** `data/ops/nfl-props-under-bias-diagnosis.md`, DAL@NYG sanity fix (`sanity-fix-20260730i-live-odds-blend`)

---

## Overall enterprise readiness: **B−**

Props research board usable; **2025 W17 PLAY Under 100% → 29%** after canary rematerialize; stake PLAY remains research-only. Sides/totals/ML are market-blended for early season with publish gates. Not yet subscription-grade for stake props.

| Market family | Grade | Confidence |
| --- | :---: | :---: |
| Player props | **C+ → B−** (post-fix) | Medium |
| Spreads / sides | **B** | Medium-high |
| Game totals (O/U) | **B−** | Medium |
| Moneylines | **B** | Medium |

---

## 1. Player Props — **C+ → B−**

### What’s working
- Box-score MC + baseline blend with de-vig edges and sparse PLAY/WATCH tags.
- Disagreement gate blocks extreme model–market gaps.
- Walk-forward / frozen mean+std calibration (`prop-enterprise-cal-v1`).
- Holdout discipline: PLAY **not stake-eligible** after batch-4/5 failures.

### Known biases (pre-fix evidence)
- **Featured WR1 under-projection:** line≥40 mean raw gap ≈ **−14 yd** (2025 W17).
- **Default PLAY board 100% Unders** (W14/16/17); mid-season W10–13 balanced.
- Features `role_confidence` is involvement-scale (p50≈0.21) but shrink/PLAY used starter-scale thresholds (0.55) → everyone “low role”.
- Depth-chart join misses → WR1 floors never applied → ~14 yd collapsed means.

### Fix shipped this cycle
- Usage-rank depth fallback; floored effective role on props path; `model_role_collapse` Under gate; canary bump.
- Offline: role-collapse alone removes **29/63** Under PLAYs (W10–17) while keeping Overs.

### Data gaps
- Snap counts not fully backfilled; pass/rush defensive EPA still shared.
- Prop closing densify limited by Odds API credits.

### P0 remaining
0. ~~Celery props task decorator miswire~~ — fixed in `20260731b` (was blocking all `/api/jobs/run-nfl-player-props`).

1. Rematerialize baselines → box → props on **brave-art** after canary live; re-measure W17 PLAY mix + featured raw gap.
2. Holdout confirm before any stake promotion (`PLAY_STAKE_ELIGIBLE` stays false).
3. Align Vercel `MODEL_SERVICE_URL` with brave-art (`model-service-production-e253`) — agent secret currently points at joyful-clarity stub.

### AFTER verify W17
- PLAY: **30 Over / 12 Under (29% Under)**; 19 `model_role_collapse` blocks
- Celery props task SUCCESS; canary `…20260731b…` live
- Residual: rebuild baselines+box when feature rows available to lift featured WR raw gaps

### Confidence
High on Under-tag root cause + tag fix. Medium on full projection recalibration until baselines/box rebuild completes.

---

## 2. Spreads / sides — **B**

### What’s working
- Framework + early-season supervised **skip** (W1–4 / unplayed season).
- Live Odds consensus fallback + DB odds join; market blend when sides disagree.
- Publish tags with segment evidence + market side-disagreement block.
- DAL@NYG class failure corrected (`worker_build_id=sanity-fix-20260730i-live-odds-blend`); post-resim within ~1.5 pts of market on most games.

### Known biases
- Residual market disagreements remain (~7 games ≥1.5 pts in last sanity pass).
- Parallel Odds-API `game_id` vs schedule UUID still a long-term join debt.

### Data gaps / P0
- Heal snapshot `game_id` alignment; re-enable validated supervised only after ≥3 past-dated REG games/team (automatic).

### Confidence
Medium-high on early-season path; medium on in-sample supervised once season starts.

---

## 3. Game totals (O/U) — **B−**

### What’s working
- Totals modeled with framework decomposition; market blend available.
- Early-season publish often sides-only / gated (by design).

### Known biases
- Totals less sharpened than sides in preseason/W1 path; product treats totals more conservatively.

### P0
- Confirm totals CLV/holdout once REG sample exists; keep publish gates until then.

### Confidence
Medium.

---

## 4. Moneylines — **B**

### What’s working
- Dedicated ML publish policy with EV/thin-price gates.
- Coupled to same early-season market blend / supervised skip as sides.

### Known biases
- ML PLAY sensitive to vig and price shape; blocked when side disagrees with market.

### P0
- Track ML CLV separately through early 2026 REG.

### Confidence
Medium.

---

## Interaction with prior fixes

| Prior fix | Interaction |
| --- | --- |
| Live odds blend | Unchanged; props don’t use game odds blend |
| Early-season supervised skip | Unchanged; props independent |
| Side/total/ML publish gates | Unchanged |
| Prop calibration v1 + disagreement gate | Kept; role-collapse gate is the missing sibling for crushed raw Unders |
| PLAY research-only | Still enforced |

---

## Verify after Railway canary

```bash
curl -sS https://model-service-production-e253.up.railway.app/health
# After worker deploy + rematerialize 2025 W17:
# POST /api/jobs/run-nfl-player-baselines?season=2025&week=17
# POST box-score materialize (player cycle) then
# POST /api/jobs/run-nfl-player-props?season=2025&week=17
# Re-pull /nfl/props/board?season=2025&week=17&tag=PLAY
```

Success: PLAY Under % no longer ~100% for structural reasons; featured line≥40 raw gap materially smaller; canary id visible on sim task results.
