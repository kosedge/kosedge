/**
 * P0 Odds Expansion — board horizon labels, sort, and odds-without-KEI paint.
 *
 * Sort: live/current day → nearest upcoming → chronological future.
 * Within the same ET kickoff day: freshest market, strongest book coverage,
 * then best-line present. Do NOT sort giant model edges to the top.
 *
 * Labels: Current / Early Market / Futures · Advance Line.
 * Always carry exact market_as_of (never Date.now()).
 */

import type { EdgeBoardRow } from "@kosedge/contracts";

export const ODDS_HORIZON_LABELS = {
  current: "Current",
  early_market: "Early Market",
  futures_advance: "Futures · Advance Line",
} as const;

export type OddsHorizonKey = keyof typeof ODDS_HORIZON_LABELS;

export const EARLY_MARKET_DAYS = 7;
const ET = "America/New_York";

export type OddsHorizonStamp = {
  marketHorizon: OddsHorizonKey;
  marketHorizonLabel: string;
  marketAsOf: string | null;
  oddsWithoutKei: boolean;
  bookCount?: number;
};

function parseIsoMs(raw: string | null | undefined): number | null {
  if (raw == null || !String(raw).trim()) return null;
  const ms = Date.parse(String(raw).trim());
  return Number.isFinite(ms) ? ms : null;
}

function etDateKey(ms: number): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: ET,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(ms));
}

export function rowHasVerifiedMarket(
  row: EdgeBoardRow | null | undefined,
): boolean {
  if (!row) return false;
  const best = String(row.best ?? "").trim();
  const open = String(row.open ?? "").trim();
  const bookKey = String(
    (row as EdgeBoardRow & { bookKey?: string }).bookKey ?? "",
  )
    .trim()
    .toLowerCase();
  const priced = Boolean(best && best !== "—") || Boolean(open && open !== "—");
  if (!priced) return false;
  if (bookKey === "keinfl" || bookKey === "kei" || bookKey === "market") {
    return false;
  }
  return true;
}

export function rowHasKei(row: EdgeBoardRow | null | undefined): boolean {
  if (!row) return false;
  const kei = String(row.kei ?? "").trim();
  return Boolean(kei && kei !== "—");
}

export function isOddsWithoutKei(
  row: EdgeBoardRow | null | undefined,
): boolean {
  return rowHasVerifiedMarket(row) && !rowHasKei(row);
}

export function classifyOddsHorizon(
  commenceTime: string | null | undefined,
  nowMs: number = Date.now(),
): OddsHorizonKey {
  const startMs = parseIsoMs(commenceTime);
  if (startMs == null) return "futures_advance";
  if (startMs <= nowMs) return "current";
  if (etDateKey(startMs) === etDateKey(nowMs)) return "current";
  const days = (startMs - nowMs) / (24 * 60 * 60 * 1000);
  if (days <= EARLY_MARKET_DAYS) return "early_market";
  return "futures_advance";
}

export function marketAsOfFromRow(
  row: EdgeBoardRow | null | undefined,
): string | null {
  const raw = (row as { linesAsOf?: string | null } | null)?.linesAsOf;
  if (raw == null || !String(raw).trim()) return null;
  const ms = parseIsoMs(raw);
  return ms == null ? null : String(raw).trim();
}

export function stampOddsHorizon(
  row: EdgeBoardRow,
  nowMs: number = Date.now(),
): EdgeBoardRow & OddsHorizonStamp {
  const key = classifyOddsHorizon(row.commenceTime, nowMs);
  const bookCount = Number(
    (row as EdgeBoardRow & { bookCount?: number }).bookCount,
  );
  return {
    ...row,
    marketHorizon: key,
    marketHorizonLabel: ODDS_HORIZON_LABELS[key],
    marketAsOf: marketAsOfFromRow(row),
    oddsWithoutKei: isOddsWithoutKei(row),
    ...(Number.isFinite(bookCount) && bookCount > 0 ? { bookCount } : {}),
  };
}

export function stampOddsHorizonRows(
  rows: readonly EdgeBoardRow[],
  nowMs: number = Date.now(),
): Array<EdgeBoardRow & OddsHorizonStamp> {
  return rows.map((row) => stampOddsHorizon(row, nowMs));
}

function marketOrder(row: EdgeBoardRow): number {
  const m = String(row.market ?? "").toLowerCase();
  if (m === "spread" || m === "puck line" || m === "run line") return 0;
  if (m === "moneyline") return 1;
  if (m === "total") return 2;
  return 3;
}

function bookCoverage(row: EdgeBoardRow): number {
  const n = Number((row as EdgeBoardRow & { bookCount?: number }).bookCount);
  if (Number.isFinite(n) && n > 0) return n;
  return rowHasVerifiedMarket(row) ? 1 : 0;
}

function commenceMs(row: EdgeBoardRow): number {
  return parseIsoMs(row.commenceTime) ?? Number.POSITIVE_INFINITY;
}

/**
 * Primary: live/today → upcoming chronological.
 * Same ET kickoff day: freshest as_of, then book coverage, then best-line.
 * Explicitly ignores |edge| / KEI magnitude.
 */
export function sortOddsHorizonRows(
  rows: readonly EdgeBoardRow[],
  nowMs: number = Date.now(),
): EdgeBoardRow[] {
  return [...rows].sort((a, b) => {
    const aStart = commenceMs(a);
    const bStart = commenceMs(b);
    const aLive = aStart <= nowMs ? 0 : 1;
    const bLive = bStart <= nowMs ? 0 : 1;
    if (aLive !== bLive) return aLive - bLive;

    const aToday =
      Number.isFinite(aStart) && etDateKey(aStart) === etDateKey(nowMs) ? 0 : 1;
    const bToday =
      Number.isFinite(bStart) && etDateKey(bStart) === etDateKey(nowMs) ? 0 : 1;
    if (aToday !== bToday) return aToday - bToday;

    if (aStart !== bStart) return aStart - bStart;

    const aAsOf = parseIsoMs(marketAsOfFromRow(a)) ?? Number.NEGATIVE_INFINITY;
    const bAsOf = parseIsoMs(marketAsOfFromRow(b)) ?? Number.NEGATIVE_INFINITY;
    if (aAsOf !== bAsOf) return bAsOf - aAsOf;

    const cov = bookCoverage(b) - bookCoverage(a);
    if (cov !== 0) return cov;

    const aBest = rowHasVerifiedMarket(a) ? 0 : 1;
    const bBest = rowHasVerifiedMarket(b) ? 0 : 1;
    if (aBest !== bBest) return aBest - bBest;

    const game = String(a.game ?? "").localeCompare(String(b.game ?? ""));
    if (game !== 0) return game;
    return marketOrder(a) - marketOrder(b);
  });
}

export function applyOddsHorizonToRows(
  rows: readonly EdgeBoardRow[],
  nowMs: number = Date.now(),
): Array<EdgeBoardRow & OddsHorizonStamp> {
  return stampOddsHorizonRows(sortOddsHorizonRows(rows, nowMs), nowMs);
}

/** Fair/KEI display: blank when odds-without-KEI. Never invent a house print. */
export function fairDisplayForRow(
  row: EdgeBoardRow | null | undefined,
): string {
  if (!rowHasKei(row)) return "—";
  return String(row!.kei).trim();
}
