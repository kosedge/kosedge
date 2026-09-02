# NFL Week 1 desk — live FAIL fix after #401 (2026-09-02)

**PR target:** `deploy-vercel` (do not merge from agent — CoS merges)  
**Branch:** `cursor/nfl-w1-overlay-melbourne-1b4e`  
**Base tip:** `9aab5e7` (#401)

## Live FAILs (Alex Rourke, numbers-only)

### 1. Game Boxes overlay silent no-op
Drake Maye NE@SEA showed MC median **160** with `spine_version` stamped `player-production-v3-phase3c`. Props/Edges still **216.2**.
Root causes:
- SQL `team = ANY(:teams)` without `CAST(... AS text[])` → 0 baseline rows
- Name key `{team}|{lower full name}` missed nflverse `D.Maye` vs engine `Drake Maye`
- Overlay miss still stamped spine_version

**Fix:** text[] cast + `prop_player_match_keys` join; **HTTP 503** on overlay_count=0; never stamp spine without replacing the number. Test fails if Maye overlay_count is 0.

### 2. KEI Lines SF@LAR still legacy LA
`source_week_game_cards` throw fell through to legacy same-coast / Visual Crossing SoFi weather. Kickoff stuck at `2026-09-10T20:00:00Z` (4pm ET) vs official **8:35pm ET** Melbourne.

**Fix:** retry without weather → schedule-only stubs; **never** legacy same-coast for Week 1 card failure. Rewrite all international weather chips (not just visual_crossing/SoFi tokens). Overlay canonical kickoff on fair-lines `start_time`.

## Do not regress
Holani Under, GB@MIN Love/McCarthy, Murray ARI, no abs-tie Over, no paywall, no KEI mint. Odds API 401 is context — canonical schedule wins.
