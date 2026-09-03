# Display-honesty kill switch — 2026-09-03

**Purpose:** Blank untrusted confidence chrome on props / Edge Board in seconds — no redeploy, no coding runner, no remat, no KEI/model/paywall changes.

**Store:** Vercel Global Config (formerly Edge Config). Connection string env: `GLOBAL_CONFIG` (falls back to `EDGE_CONFIG`). SDK: `@vercel/global-config`.

**Why not env vars alone:** Flipping `process.env` flags requires a new Vercel deployment. Global Config reads at request time (~1ms), so operators can set `"off"` and the next request hides the number.

## Flags (keys `^[A-Za-z0-9_-]+$`)

| Key | Type | Meaning |
|-----|------|---------|
| `nfl_props_confidence_display` | `"on"` \| `"off"` | Props Confidence column / mobile Conf |
| `nfl_props_confidence_display_off_markets` | `string[]` | Market subset off, e.g. `["anytime_td"]` (global props flag still `"on"`) |
| `nfl_game_confidence_band_display` | `"on"` \| `"off"` | Edge Board `Conf BAND` line |
| `display_suppression_note` | `string` | Subscriber-safe banner when any suppression is active |
| `display_suppression_meta` | `{actor,reason,setAt,trackingPr}` | Logged on load (not required for UI) |

**Fail-open:** Anything not exactly `"off"` means **on**. Missing store / read error → all-on + log `source:"fallback"`.

**Invariants:** Display only. Stored confidence, means, edges, filters’ stored values, KEI, remat, paywall untouched. Suppression returns **null** (renders `—`), never `0` (`0%`).

## Flip (ops)

1. Vercel → Storage → Global Config (or Edge Config) for project `kosedge`.
2. If no store exists yet: **create one**, connect it to `kosedge` (creates `GLOBAL_CONFIG`), seed keys above as `"on"` / `[]` / `""`.
3. To hide props confidence globally: set `nfl_props_confidence_display` = `"off"`. Optionally set `display_suppression_note`.
4. To hide one market only: leave global `"on"`, set `nfl_props_confidence_display_off_markets` = `["anytime_td"]`.
5. To hide Edge Board conf band: set `nfl_game_confidence_band_display` = `"off"`.
6. Restore: set back to `"on"` / `[]`. Takes effect on the next request (no deploy).

CLI (when authenticated): `vercel global-config` (alias `vercel edge-config`).

## Verify

| Check | Expect |
|-------|--------|
| `/pro/nfl/props` with props flag `"off"` | Confidence column / Conf = `—`; row still listed; note banner if note set |
| off_markets `["anytime_td"]` only | ATD Conf = `—`; other markets still show % |
| Edges desk + minConf with suppressed ATD | ATD edge row still present (null conf survives filter) |
| Edge Board game band `"off"` | Decision cell shows `Conf —` (line does not vanish) |
| Store disconnected / missing | All confidence chrome on (fail-open); logs `source:"fallback"` |

## Code

- `apps/web/lib/display-honesty.ts` — load + fail-open
- `apps/web/lib/display-honesty-core.ts` — pure parse / format helpers
- Props: `apps/web/app/(pro)/pro/nfl/props/page.tsx`
- Edges desk filter survival: `apps/web/lib/nfl-edges.ts`
- Edge Board: assemble API meta → `EdgeBoardSportClient` → `EdgeBoard`
