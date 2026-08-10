# NFL Phase 3 Path A2 — Closeout (bank) (2026-08-09)

**PR:** [#167](https://github.com/kosedge/kosedge/pull/167) merge → `deploy-vercel`  
**Merge SHA:** `6fa8349b1ae69748ee1df45235350c68589ddc04`  
**Live engine version:** `nfl-season-engine-v1.26-phase3-pathA2-usage-prior`  
**Protocol / artifacts:** [`nfl-phase3-pathA2-rerun-20260809.md`](./nfl-phase3-pathA2-rerun-20260809.md), diagnosis [`nfl-phase3-diagnose-player-yards-A2-20260809.md`](./nfl-phase3-diagnose-player-yards-A2-20260809.md)

## Bank decision

| Path | Status |
|------|--------|
| **Path A** (path-end player yard blend) | **Reverted** — path-end blend is dead (pass MAE worsened 785→848). |
| **Path A2** (usage-input Y−1 share anchor) | **KEEP** — 80% prior-year team volume share on returning players’ `target_share` / `rush_share` at usage construction. |

No new modeling in this closeout. No second share blend. No props / PLAY labels. No baseline freeze.

## Scorecard (identical 2019–2025 replay)

| Metric | Before → After (pooled MAE) |
|--------|----------------------------:|
| player pass yards | **785 → 782** |
| player rush yards | **202 → 200** |
| player rec yards | **252 → 239** |
| team wins / PF / PA | **not worse** (wins 2.524→2.515, PF/PA improved or flat) |

## Claims status

- **Wins claim:** still **blocked** — model wins MAE **2.515** remains above prior+reg **2.463**.
- **Pass yards:** still far from the published prior headline (~228); **no value claim** on pass yards or season wins. (Aligned prior+reg pass MAE ≈1078 on QB-matched universe; model still beats that prior but the Phase 3 gap vs the diluted ~228 headline is not closed as a product claim.)
- **Settled:** returning players see Y−1 volume at **usage construction** (Path A2 lever kept on live `v1.26`).

## Deploy confirmation (post-merge)

| Surface | Status |
|---------|--------|
| **GitHub** | #167 merged; tip `6fa8349b…` on `deploy-vercel` |
| **Vercel Production (`kosedge`)** | Ready on merge SHA `6fa8349b…` |
| **Railway model-service** | Deploy SUCCESS (`cliMessage: ci 6fa8349b1ae6 api`) |
| **Live Railway status / game-box lineage** | `engine_version=nfl-season-engine-v1.26-phase3-pathA2-usage-prior` |
| **Live BFF (`www.kosedge.com`) status / game-box** | same `v1.26` / `pathA2` stamp |

## Explicitly not started

- Path A3
- Prop Engine
- Phase 4 calibration suite
- Phase 5 Decision Engine

## References

- Path A revert note: [`nfl-phase3-pathA-rerun-20260809.md`](./nfl-phase3-pathA-rerun-20260809.md)
- Path A2 KEEP rerun: [`nfl-phase3-pathA2-rerun-20260809.md`](./nfl-phase3-pathA2-rerun-20260809.md)
