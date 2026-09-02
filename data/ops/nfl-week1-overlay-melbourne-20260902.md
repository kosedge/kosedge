# NFL Week 1 desk — live FAIL fix after #401 (2026-09-02)

**PR target:** `deploy-vercel` (do not merge from agent — CoS merges)  
**Branch:** `cursor/nfl-w1-overlay-melbourne-1b4e`  
**Base tip:** `9aab5e7` (#401)

## Live FAILs (Alex Rourke, numbers-only)

### 1. Game Boxes overlay silent no-op
Drake Maye NE@SEA showed MC median **160** with `spine_version` stamped / `yards_headline=spine_mean` while `notes.spine_overlay.ok=false rows=0`.
Box `player_key` = `NE-QB1-DrakeMaye`. Props still **216.2**.

**Root causes:**
- SQL `team = ANY(:teams)` without `CAST(... AS text[])` → 0 baseline rows
- Name key missed nflverse `D.Maye` vs engine `Drake Maye` / `player_key`
- Overlay miss still stamped spine_version

**Fix:** text[] cast + `prop_player_match_keys` + `player_key` parse/index; props-edges fallback; **HTTP 503** on overlay_count=0; never stamp spine without replacing the number.

### 2. KEI Lines SF@LAR chips still legacy LA (Edge Board already PASS)
Edge Board already has Melbourne / 8:35 — **do not rewrite Edge Board**.
Fair-lines page header already shows 8:35 via canonical pack — **do not retune header**.
FAIL is considered chips: `same-coast (SF → LA)` + `visual_crossing` SoFi weather.

**Fix:** retry without weather → schedule stubs; never legacy LA path. Emit factor=`travel` (page HONEST_FACTORS) + rewrite weather to Melbourne. Expose `venue` / `location` / `neutral_site` on fair-lines rows. API `start_time` overlays canonical so `/nfl/fair-lines` matches Edge Board commenceTime.

## Do not regress
Holani Under, GB@MIN Love/McCarthy, Murray ARI, no abs-tie Over, no paywall, no KEI mint. Odds API 401 is context — canonical schedule wins.
