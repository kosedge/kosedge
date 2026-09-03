/**
 * Display-honesty kill switch — confidence chrome only.
 *
 * Reads Vercel Global Config (formerly Edge Config) at request time so operators
 * can blank untrusted confidence numbers without a redeploy. Env vars alone are
 * insufficient: changing GLOBAL_CONFIG / EDGE_CONFIG requires a new deployment.
 *
 * Connection string: SDK reads `GLOBAL_CONFIG`, falling back to `EDGE_CONFIG`.
 *
 * Fail-open: anything not exactly `"off"` means on. Store/read errors → all-on
 * with `source:"fallback"`. Suppression is display-only; it does not change
 * stored confidence, KEI, means, edges, leans, thresholds, floors, calibration,
 * remat, or paywall.
 */
import "server-only";
import { get } from "@vercel/global-config";
import { logInfo, logWarn } from "@/lib/logger";
import {
  DISPLAY_HONESTY_FLAG_KEYS,
  failOpenDisplayHonestyFlags,
  parseDisplayHonestyFlags,
  type DisplayHonestyFlags,
} from "@/lib/display-honesty-core";

export * from "@/lib/display-honesty-core";

type GetFn = (key: string) => Promise<unknown>;

async function readFlagItems(getFn: GetFn): Promise<{
  items: Partial<Record<string, unknown>>;
  source: DisplayHonestyFlags["source"];
}> {
  const keys = Object.values(DISPLAY_HONESTY_FLAG_KEYS);
  const entries = await Promise.all(
    keys.map(async (key) => {
      const value = await getFn(key);
      return [key, value] as const;
    }),
  );
  const items: Partial<Record<string, unknown>> = {};
  for (const [key, value] of entries) {
    if (value !== undefined) items[key] = value;
  }
  return { items, source: "global-config" };
}

/**
 * Load display-honesty flags from Global Config.
 * Fail-open on missing connection string / read errors.
 */
export async function loadDisplayHonestyFlags(opts?: {
  getFn?: GetFn;
}): Promise<DisplayHonestyFlags> {
  const getFn = opts?.getFn ?? ((key: string) => get(key));
  try {
    const { items, source } = await readFlagItems(getFn);
    const flags = parseDisplayHonestyFlags(items, source);
    logInfo("display_honesty_flags_loaded", {
      source: flags.source,
      nfl_props_confidence_display: flags.nfl_props_confidence_display,
      nfl_props_confidence_display_off_markets:
        flags.nfl_props_confidence_display_off_markets,
      nfl_game_confidence_band_display: flags.nfl_game_confidence_band_display,
      has_note: Boolean(flags.display_suppression_note),
      meta: flags.display_suppression_meta,
    });
    return flags;
  } catch (err) {
    logWarn("display_honesty_flags_fallback", {
      source: "fallback",
      err: err instanceof Error ? err.message : String(err),
    });
    const flags = failOpenDisplayHonestyFlags();
    logInfo("display_honesty_flags_loaded", {
      source: flags.source,
      nfl_props_confidence_display: flags.nfl_props_confidence_display,
      nfl_props_confidence_display_off_markets:
        flags.nfl_props_confidence_display_off_markets,
      nfl_game_confidence_band_display: flags.nfl_game_confidence_band_display,
      has_note: false,
      meta: null,
    });
    return flags;
  }
}
