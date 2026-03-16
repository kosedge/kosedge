/**
 * Application constants: site URL, cache TTLs, and external service base URLs.
 * Single source of truth for tunable values; env overrides where applicable.
 */
import { env } from "@/lib/config/env";

/** Canonical site URL for metadata, canonical links, and redirects. */
export const SITE_URL =
  env.SITE_URL ?? "https://www.kosedge.com";

/** Edge board / today API: in-memory cache TTL (ms). Shorter so KEI merge updates show sooner. */
export const EDGE_BOARD_CACHE_TTL_MS = 10 * 60 * 1000; // 10 minutes

/** Odds compare API: in-memory cache TTL (ms). */
export const ODDS_COMPARE_CACHE_TTL_MS = 6 * 60 * 60 * 1000; // 6 hours

/** NCAAM edge-board route: cache TTL (ms) when using model or Odds API. */
export const EDGE_BOARD_NCAAM_CACHE_TTL_MS = 6 * 60 * 60 * 1000; // 6 hours

/** Cache-Control s-maxage for public API responses (seconds). */
export const CACHE_S_MAXAGE_DEFAULT = 21_600; // 6 hours

/** Cache-Control stale-while-revalidate (seconds). */
export const CACHE_STALE_WHILE_REVALIDATE = 3600; // 1 hour

/** Build public cache-control header value. */
export function cacheControlHeader(
  sMaxAge: number = CACHE_S_MAXAGE_DEFAULT,
  staleWhileRevalidate: number = CACHE_STALE_WHILE_REVALIDATE
): string {
  return `public, s-maxage=${sMaxAge}, stale-while-revalidate=${staleWhileRevalidate}`;
}

/** Odds API widget: base URL for embed proxy. */
export const ODDS_WIDGET_BASE_URL = "https://widget.the-odds-api.com/v1/sports";

/** Odds widget: bookmaker keys query param. */
export const ODDS_WIDGET_BOOKMAKERS = "draftkings,fanduel,circa,betmgm,bet365,fanatics,betrivers,betr";

/** Odds widget: markets query param. */
export const ODDS_WIDGET_MARKETS = "h2h,spreads,totals";

/** Odds widget: market names for display. */
export const ODDS_WIDGET_MARKET_NAMES = "h2h:Moneyline,spreads:Spread,totals:Over/Under";
