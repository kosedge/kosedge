/**
 * Build the NFL Edge Board from Kosedge fair-lines (spread_home / total_mean),
 * then overlay live Odds API open/best/book when available.
 */

import type { EdgeBoardRow } from "@kosedge/contracts";
import type { NflFairLineRow } from "@/lib/nfl-fair-lines";
import { NFL_TEAM_DIRECTORY } from "@/lib/nfl-team-intel";

const ET = "America/New_York";

function formatSigned(point: number): string {
  const rounded = Math.round(point * 10) / 10;
  if (Object.is(rounded, -0) || rounded === 0) return "+0";
  return rounded > 0 ? `+${rounded}` : String(rounded);
}

function formatCommence(iso: string | null): string | undefined {
  if (!iso) return undefined;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return undefined;
  const date = d.toLocaleDateString("en-US", {
    timeZone: ET,
    month: "2-digit",
    day: "2-digit",
  });
  const time = d.toLocaleTimeString("en-US", {
    timeZone: ET,
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
  return `${date} ${time} ET`;
}

function normalizeGameKey(game: string): string {
  return game
    .toLowerCase()
    .replace(/\s+/g, " ")
    .replace(/\s*@\s*/g, " @ ")
    .replace(/['.]/g, "")
    .trim();
}

const NFL_CODE_TO_NAME = new Map(
  NFL_TEAM_DIRECTORY.map((t) => [t.code.toLowerCase(), t.name.toLowerCase()] as const),
);
const NFL_NAME_TO_CODE = new Map(
  NFL_TEAM_DIRECTORY.map((t) => [t.name.toLowerCase(), t.code.toLowerCase()] as const),
);

function nflAliases(label: string): string[] {
  const raw = label.trim().toLowerCase().replace(/['.]/g, "");
  if (!raw) return [];
  const out = new Set<string>([raw]);
  const code = NFL_NAME_TO_CODE.get(raw);
  if (code) out.add(code);
  const name = NFL_CODE_TO_NAME.get(raw);
  if (name) out.add(name);
  const words = raw.split(/\s+/);
  if (words.length > 1) out.add(words[words.length - 1]!);
  return [...out];
}

export function nflEdgeBoardMatchKeys(game: string): string[] {
  const n = normalizeGameKey(game);
  const parts = n.split(/\s*@\s*/);
  if (parts.length !== 2) return [n];
  const keys: string[] = [n];
  for (const a of nflAliases(parts[0]!)) {
    for (const h of nflAliases(parts[1]!)) {
      keys.push(`${a} @ ${h}`);
    }
  }
  return [...new Set(keys)];
}

/** Away-spread convention (matches Odds API edge-board rows). */
function awaySpreadFromHome(homeSpread: number): string {
  return formatSigned(-homeSpread);
}

/**
 * One Spread + one Total row per fair-line game.
 * KEI always set from Kosedge; Open/Best set from joined market when present.
 */
export function fairLinesToEdgeBoardRows(lines: NflFairLineRow[]): EdgeBoardRow[] {
  const rows: EdgeBoardRow[] = [];

  for (const line of lines) {
    const game = `${line.awayTeam} @ ${line.homeTeam}`;
    const commenceTime = line.startTime ?? line.gameDate ?? undefined;
    const time = formatCommence(commenceTime ?? null);
    const idBase = line.gameId || `${line.awayAbbr}-${line.homeAbbr}-${commenceTime ?? "tba"}`;

    const keiHome =
      line.spreadHome != null ? formatSigned(line.spreadHome) : undefined;
    const keiTotal =
      line.totalMean != null
        ? String(Math.round(line.totalMean * 10) / 10)
        : undefined;
    // Open/Best only from real market (or Odds overlay later) — never fake sportsbook
    // prices with KEINFL. KEI columns carry Kosedge numbers for every game.
    const marketAwaySpread =
      line.marketSpreadHome != null
        ? awaySpreadFromHome(line.marketSpreadHome)
        : undefined;
    const marketTotal =
      line.marketTotal != null
        ? String(Math.round(line.marketTotal * 10) / 10)
        : undefined;

    const week = line.week ?? undefined;

    rows.push({
      id: `${idBase}-spread`,
      game,
      time,
      commenceTime,
      market: "Spread",
      open: marketAwaySpread,
      best: marketAwaySpread,
      book: marketAwaySpread ? "Market" : undefined,
      bookKey: marketAwaySpread ? "market" : undefined,
      kei: keiHome,
      week,
    } as EdgeBoardRow);

    rows.push({
      id: `${idBase}-total`,
      game,
      time,
      commenceTime,
      market: "Total",
      open: marketTotal,
      best: marketTotal,
      book: marketTotal ? "Market" : undefined,
      bookKey: marketTotal ? "market" : undefined,
      kei: keiTotal,
      week,
    } as EdgeBoardRow);
  }

  return rows;
}

function rowWeek(row: EdgeBoardRow): number | null {
  const w = (row as EdgeBoardRow & { week?: number }).week;
  return typeof w === "number" && Number.isFinite(w) ? w : null;
}

function hasSportsbookPrice(row: EdgeBoardRow): boolean {
  const bookKey = String(
    (row as EdgeBoardRow & { bookKey?: string }).bookKey ?? "",
  ).toLowerCase();
  return Boolean(row.best) && Boolean(bookKey) && bookKey !== "keinfl";
}

/** Live market = current NFL week slate (all scheduled games that week). */
export function filterNflCurrentWeekRows(
  rows: EdgeBoardRow[],
  currentWeek: number,
): EdgeBoardRow[] {
  const filtered = rows.filter((row) => rowWeek(row) === currentWeek);
  return filtered.length > 0 ? filtered : rows;
}

/** Full season board = every game we currently have sportsbook odds on. */
export function filterNflOddsPostedRows(rows: EdgeBoardRow[]): EdgeBoardRow[] {
  const pricedGames = new Set<string>();
  for (const row of rows) {
    if (row.game && hasSportsbookPrice(row)) {
      pricedGames.add(row.game);
    }
  }
  if (pricedGames.size === 0) return rows;
  return rows.filter((row) => row.game != null && pricedGames.has(row.game));
}

/** @deprecated use filterNflCurrentWeekRows / filterNflOddsPostedRows */
export function filterNflLiveMarketRows(rows: EdgeBoardRow[]): EdgeBoardRow[] {
  return filterNflOddsPostedRows(rows);
}

/** Put live-book games first so Open/Best aren't buried under provisional rows. */
export function sortNflEdgeBoardRows(rows: EdgeBoardRow[]): EdgeBoardRow[] {
  const rank = (row: EdgeBoardRow): number => {
    const bookKey = String(
      (row as EdgeBoardRow & { bookKey?: string }).bookKey ?? "",
    ).toLowerCase();
    if (bookKey && bookKey !== "keinfl" && bookKey !== "market") return 0;
    if (bookKey === "market") return 1;
    return 2;
  };
  return [...rows].sort((a, b) => {
    const rd = rank(a) - rank(b);
    if (rd !== 0) return rd;
    return String(a.commenceTime ?? a.time ?? "").localeCompare(
      String(b.commenceTime ?? b.time ?? ""),
    );
  });
}

/**
 * Prefer Odds API open/best/book when the same game+market is present.
 * Keeps fair-line KEI and fills any games Odds doesn't cover.
 */
export function overlayOddsOntoFairLineRows(
  fairRows: EdgeBoardRow[],
  oddsRows: EdgeBoardRow[],
): EdgeBoardRow[] {
  if (!oddsRows.length) return fairRows;

  const byKey = new Map<string, EdgeBoardRow>();
  for (const row of fairRows) {
    const game = String(row.game ?? "");
    const market = String(row.market ?? "");
    for (const gk of nflEdgeBoardMatchKeys(game)) {
      byKey.set(`${gk}|${market}`, row);
    }
  }

  const usedOdds = new Set<string>();
  for (const odds of oddsRows) {
    const game = String(odds.game ?? "");
    const market = String(odds.market ?? "");
    if (!game || !market) continue;
    let target: EdgeBoardRow | undefined;
    for (const gk of nflEdgeBoardMatchKeys(game)) {
      target = byKey.get(`${gk}|${market}`);
      if (target) break;
    }
    if (!target) continue;
    usedOdds.add(String(odds.id ?? `${game}|${market}`));
    const src = odds as EdgeBoardRow & {
      bookKey?: string;
      openJuice?: string;
      openJuiceHome?: string;
      bestJuice?: string;
      bestJuiceHome?: string;
    };
    if (odds.open) target.open = odds.open;
    if (odds.best) target.best = odds.best;
    if (odds.book) (target as EdgeBoardRow & { book?: string }).book = odds.book;
    if (src.bookKey) {
      (target as EdgeBoardRow & { bookKey?: string }).bookKey = src.bookKey;
    }
    if (src.openJuice) {
      (target as EdgeBoardRow & { openJuice?: string }).openJuice = src.openJuice;
    }
    if (src.openJuiceHome) {
      (target as EdgeBoardRow & { openJuiceHome?: string }).openJuiceHome =
        src.openJuiceHome;
    }
    if (src.bestJuice) {
      (target as EdgeBoardRow & { bestJuice?: string }).bestJuice = src.bestJuice;
    }
    if (src.bestJuiceHome) {
      (target as EdgeBoardRow & { bestJuiceHome?: string }).bestJuiceHome =
        src.bestJuiceHome;
    }
    if (odds.time) target.time = odds.time;
    if (odds.commenceTime) target.commenceTime = odds.commenceTime;
  }

  // Odds-only games (shouldn't happen often) — append so we don't drop them.
  const extras: EdgeBoardRow[] = [];
  for (const odds of oddsRows) {
    const id = String(odds.id ?? `${odds.game}|${odds.market}`);
    if (usedOdds.has(id)) continue;
    const game = String(odds.game ?? "");
    const market = String(odds.market ?? "");
    let covered = false;
    for (const gk of nflEdgeBoardMatchKeys(game)) {
      if (byKey.has(`${gk}|${market}`)) {
        covered = true;
        break;
      }
    }
    if (!covered) extras.push(odds);
  }

  return extras.length ? [...fairRows, ...extras] : fairRows;
}
