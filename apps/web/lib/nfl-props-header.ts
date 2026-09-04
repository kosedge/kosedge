/**
 * Props board header honesty — period label follows the spine week, not the
 * calendar preseason cutoff. Kickoff / game time is never line vintage.
 *
 * #8 / 13b (KOS-15 / H-2): when board as-of is stale, Week chrome must not
 * read as live/current board truth. Keep the real as-of · stale stamp —
 * never invent a fresher clock.
 */

import {
  marketAsOfStamp,
  type MarketAsOfStampResult,
} from "@/lib/market-asof-stamp";

export type NflPropsSeasonType = "REG" | "PRE" | "POST";

/** Subscriber phrase: Week chrome ≠ live/current board when as-of is stale. */
export const NFL_PROPS_BOARD_NOT_LIVE_PHRASE = "not live board";

export const NFL_PROPS_BOARD_STALE_HONESTY_TITLE =
  "Board vintage stale — Week chrome is not live truth";

/**
 * Subscriber period chrome for `/pro/nfl/props`.
 *
 * Weekly props share the REG player-production spine with Edge Board.
 * Do not call a Week 1 REG board "Preseason" just because Labor Day has not
 * passed — that disagrees with Edge Board ("Week 1 REG").
 *
 * Preseason label is reserved for an explicit PRE season type only.
 *
 * When `boardStale` is true, append "· not live board" so Week chrome cannot
 * be read as a live/current market board (13b Jul-vintage honesty).
 */
export function formatNflPropsBoardPeriod(
  season: number,
  week: number,
  opts?: {
    seasonType?: NflPropsSeasonType | string | null;
    boardStale?: boolean;
  },
): string {
  const s =
    Number.isFinite(season) && season >= 2010 ? Math.trunc(season) : NaN;
  const w = Number.isFinite(week) && week >= 1 ? Math.trunc(week) : NaN;
  if (!Number.isFinite(s) || !Number.isFinite(w)) {
    return "Props board week unavailable";
  }

  const raw = String(opts?.seasonType ?? "REG")
    .trim()
    .toUpperCase();
  const seasonType: NflPropsSeasonType =
    raw === "PRE" || raw === "POST" ? raw : "REG";

  let base: string;
  if (seasonType === "PRE") {
    base = `${s} Preseason`;
  } else if (seasonType === "POST") {
    base = `${s} · Week ${w} POST`;
  } else {
    base = `${s} · Week ${w} REG`;
  }

  if (opts?.boardStale) {
    return `${base} · ${NFL_PROPS_BOARD_NOT_LIVE_PHRASE}`;
  }
  return base;
}

/**
 * Resolve board stamp from row as-of. Never invents a clock.
 * Blank / unparseable → missing (not stale).
 */
export function resolveNflPropsBoardStamp(
  asOf: string | null | undefined,
  nowMs?: number,
): MarketAsOfStampResult {
  return marketAsOfStamp({ asOf, kind: "board", nowMs });
}

/**
 * Amber banner body when Week chrome is paired with a stale board as-of.
 * Keeps the real stamp text (e.g. Jul 20 · stale) — never invents fresher.
 */
export function nflPropsBoardStaleHonestyBody(opts: {
  season: number;
  week: number;
  stampText: string;
}): string {
  const weekChrome = formatNflPropsBoardPeriod(opts.season, opts.week);
  return (
    `${weekChrome} names the requested spine week only. ` +
    `Board numbers are ${opts.stampText} — not a live/current props board. ` +
    `Real as-of stays visible; we do not invent fresher prices.`
  );
}
