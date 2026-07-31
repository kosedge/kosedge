# NFL Model Enterprise Grade Report

**Date:** 2026-07-31  
**Canary target:** `props-under-bias-20260731c-baselines-box-rebuild`  
**Related:** `data/ops/nfl-props-under-bias-diagnosis.md`, DAL@NYG sanity fix (`sanity-fix-20260730i-live-odds-blend`)

---

## Overall enterprise readiness: **B**

Props research board usable after structural Under-bias fix **and** clean features→baselines→box rebuild. W17 PLAY Under **100% → 33%** (sparse PLAY); featured line≥40 mean raw−line **−14/−27 → +8.8**. Stake PLAY remains research-only. Sides/totals/ML market-blended for early season with publish gates.

| Market family | Grade | Confidence |
| --- | :---: | :---: |
| Player props | **C+ → B− → B** (post-rebuild) | Medium |
| Spreads / sides | **B** | Medium-high |
| Game totals (O/U) | **B−** | Medium |
| Moneylines | **B** | Medium |

---

## 1. Player Props — **B** (was C+ → B−)

### What’s working
- Box-score MC + baseline blend with de-vig edges and sparse PLAY/WATCH tags.
- Disagreement + `model_role_collapse` gates block publishing model failure as Under edge.
- Walk-forward / frozen mean+std calibration (`prop-enterprise-cal-v1`).
- Holdout discipline: PLAY **not stake-eligible** after batch-4/5 failures.
- **Clean rematerialize path:** features / box / `rebuild-props-layers` ops; coverage diagnostic.

### Known biases (pre-fix evidence)
- **Featured WR1 under-projection:** line≥40 mean raw gap ≈ **−14 yd** (2025 W17 pre-fix).
- **Default PLAY board 100% Unders** (W14/16/17); mid-season W10–13 balanced.
- Features `role_confidence` involvement-scale vs starter-scale shrink thresholds.
- Depth-chart join misses → WR1 floors never applied → ~14 yd collapsed means.
- Empty `nfl_player_projection_features_weekly` → `baseline_rows_upserted=0` blocked projection lift.

### Fix shipped this cycle
- Usage-rank depth fallback; floored effective role; `model_role_collapse` Under gate (`…20260731a/b…`).
- Features rematerialize + baselines + box rebuild for 2025 W10–17 (`…20260731c…`); lazy `nflreadpy` import so workers can run SQL feature path.
- Featured line≥40 mean raw−line after rebuild: **+8.8** (n=44). T.McMillan 21→57 yd vs 52.5; Chase/Lamb/McBride near books.

### Data gaps
- Snap counts not fully backfilled; pass/rush defensive EPA still shared.
- Residual collapses (Harrison/London/McConkey) and overshoots (Jefferson class) — disagreement PASS, not PLAY Under.
- Prop closing densify limited by Odds API credits.

### P0 remaining
0. ~~Celery props task decorator miswire~~ — fixed in `20260731b`.
1. ~~Rematerialize baselines → box → props~~ — done W10–17 on brave-art (`…20260731c…`).
2. Holdout confirm before any stake promotion (`PLAY_STAKE_ELIGIBLE` stays false).
3. Align Vercel / agent `MODEL_SERVICE_URL` with brave-art (`model-service-production-e253`) — injected secret still points at joyful-clarity stub.
4. Optional: backfill snap counts to tighten residual WR collapses (not a paid feed).

### AFTER verify W17 (post rebuild)
- PLAY: **4 Over / 2 Under (33% Under)**; all rows `box_score`-sourced; canary `…20260731c…`
- `baseline_rows_upserted=324` (was 0); box_upserted=324
- Props letter grade revised to **B** on projection lift (not a market nudge)

### Confidence
High on Under-tag root cause + empty-features upsert diagnosis. Medium on residual player-level MAE until snaps/holdout densify.

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
curl -sS 'https://model-service-production-e253.up.railway.app/nfl/ops/player-layer-coverage?season=2025&week=17'
# POST /nfl/ops/rebuild-props-layers?season=2025&weeks=14,16,17&replace_features=true
# Re-pull /nfl/props/board?season=2025&week=17&tag=PLAY
```

Success criteria met: PLAY Under % not ~100% structurally; featured line≥40 raw gap flipped from largely negative to **+8.8**; canary `props-under-bias-20260731c-baselines-box-rebuild` on props diagnostics.
