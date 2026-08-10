/**
 * Build the NFL Edge Board from Kosedge fair-lines (spread_home / total_mean),
 * then overlay live Odds API open/best/book when available.
 */

import type { EdgeBoardRow } from "@kosedge/contracts";
import type { NflFairLineRow } from "@/lib/nfl-fair-lines";
import {
  assessConfidence,
  decideGame,
  decisionResultToApi,
  isTierConstantConfidence,
} from "@/lib/nfl-decision-engine";
import { resolveNflKickoffIso } from "@/lib/nfl-schedule-kickoff";
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
  NFL_TEAM_DIRECTORY.map(
    (t) => [t.code.toLowerCase(), t.name.toLowerCase()] as const,
  ),
);
const NFL_NAME_TO_CODE = new Map(
  NFL_TEAM_DIRECTORY.map(
    (t) => [t.name.toLowerCase(), t.code.toLowerCase()] as const,
  ),
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

function formatJuice(price: number | null | undefined): string | undefined {
  if (price == null || !Number.isFinite(price)) return undefined;
  const n = Math.round(price);
  return n > 0 ? `+${n}` : String(n);
}

/**
 * One Spread + one Total row per fair-line game.
 * KEI always set from Kosedge.
 * Open = market consensus average; Best = best number across books when present.
 */
export function fairLinesToEdgeBoardRows(
  lines: NflFairLineRow[],
): EdgeBoardRow[] {
  const rows: EdgeBoardRow[] = [];

  for (const line of lines) {
    const game = `${line.awayTeam} @ ${line.homeTeam}`;
    const commenceTime =
      resolveNflKickoffIso({
        gameId: line.gameId,
        startTime: line.startTime,
        gameDate: line.gameDate,
      }) ?? undefined;
    const time = formatCommence(commenceTime ?? null);
    const idBase =
      line.gameId ||
      `${line.awayAbbr}-${line.homeAbbr}-${commenceTime ?? "tba"}`;

    const handicapSpread = line.handicapSpreadHome ?? line.spreadHome;
    const handicapTotal = line.handicapTotal ?? line.totalMean;
    const keiHome =
      handicapSpread != null ? formatSigned(handicapSpread) : undefined;
    const keiTotal =
      handicapTotal != null
        ? String(Math.round(handicapTotal * 10) / 10)
        : undefined;
    // Research Model (pre-blend) — attached for honesty; Edge Board tags use kei.
    const modelKeiHome =
      line.modelSpreadHome != null
        ? formatSigned(line.modelSpreadHome)
        : undefined;
    const modelKeiTotal =
      line.modelTotal != null
        ? String(Math.round(line.modelTotal * 10) / 10)
        : undefined;
    // Open = consensus average across books (when joined).
    const marketAwaySpread =
      line.marketSpreadHome != null
        ? awaySpreadFromHome(line.marketSpreadHome)
        : undefined;
    const marketTotal =
      line.marketTotal != null
        ? String(Math.round(line.marketTotal * 10) / 10)
        : undefined;
    // Best = best-of-books number + winning book (not consensus).
    const bestAwaySpread =
      line.bestSpreadHome != null
        ? awaySpreadFromHome(line.bestSpreadHome)
        : undefined;
    const bestTotal =
      line.bestTotal != null
        ? String(Math.round(line.bestTotal * 10) / 10)
        : undefined;
    const bestSpreadBook = line.bestSpreadBook ?? undefined;
    const bestTotalBook = line.bestTotalBook ?? undefined;

    const week = line.week ?? undefined;
    const seasonType = line.seasonType ?? undefined;
    const publishTagSpread = line.publishTagSpread ?? undefined;
    const publishTagTotal = line.publishTagTotal ?? undefined;

    // Action layer: prefer server decision (Model fair vs market); else compute locally.
    const decisionBundle =
      line.decision ??
      (() => {
        const compareSpread =
          line.bestSpreadHome ?? line.marketSpreadHome ?? null;
        const compareTotal = line.bestTotal ?? line.marketTotal ?? null;
        const local = decideGame({
          week: line.week,
          fairSpreadHome: line.modelSpreadHome ?? line.spreadHome,
          marketSpreadHome: compareSpread,
          fairTotal: line.modelTotal ?? line.totalMean,
          marketTotal: compareTotal,
          homeAbbr: line.homeAbbr,
          awayAbbr: line.awayAbbr,
          openingSpreadHome: line.marketSpreadHome,
          openingTotal: line.marketTotal,
          confidence: assessConfidence(),
          priceStillAvailableSpread: compareSpread != null,
          priceStillAvailableTotal: compareTotal != null,
        });
        return {
          doctrine: local.doctrine,
          week: local.week,
          weekRegime: local.weekRegime,
          spread: local.spread,
          total: local.total,
          edgeMagnitudeSpread: local.edgeMagnitudeSpread,
          edgeMagnitudeTotal: local.edgeMagnitudeTotal,
          modelConfidence: local.modelConfidence,
          actionLabelSpread: local.actionLabelSpread,
          actionLabelTotal: local.actionLabelTotal,
        };
      })();

    const spreadDecision = decisionBundle.spread;
    const totalDecision = decisionBundle.total;
    const actionLabelSpread =
      line.actionLabelSpread ??
      decisionBundle.actionLabelSpread ??
      spreadDecision?.actionLabel ??
      null;
    const actionLabelTotal =
      line.actionLabelTotal ??
      decisionBundle.actionLabelTotal ??
      totalDecision?.actionLabel ??
      null;

    const sharedMatchup = {
      awayAbbr: line.awayAbbr,
      homeAbbr: line.homeAbbr,
      homeWinProb: line.homeWinProb ?? undefined,
      awayWinProb: line.awayWinProb ?? undefined,
      keiSpreadHome: handicapSpread ?? undefined,
      marketSpreadHome:
        line.bestSpreadHome ?? line.marketSpreadHome ?? undefined,
      keiTotal: handicapTotal ?? undefined,
      marketTotal: line.bestTotal ?? line.marketTotal ?? undefined,
      gamesPlayedAway: week === 1 ? 0 : undefined,
      gamesPlayedHome: week === 1 ? 0 : undefined,
    };

    rows.push({
      id: `${idBase}-spread`,
      game,
      time,
      commenceTime,
      market: "Spread",
      open: marketAwaySpread,
      best: bestAwaySpread ?? marketAwaySpread,
      book:
        bestSpreadBook ??
        (bestAwaySpread || marketAwaySpread ? "market" : undefined),
      bookKey:
        bestSpreadBook ??
        (bestAwaySpread || marketAwaySpread ? "market" : undefined),
      openJuice: undefined,
      openJuiceHome: undefined,
      bestJuice: formatJuice(line.bestSpreadAwayJuice),
      bestJuiceHome: formatJuice(line.bestSpreadHomeJuice),
      kei: keiHome,
      modelKei: modelKeiHome,
      week,
      seasonType,
      publishTag: publishTagSpread,
      actionLabel: actionLabelSpread ?? undefined,
      decision: spreadDecision
        ? decisionResultToApi(spreadDecision)
        : undefined,
      edgeMagnitude: spreadDecision?.edgeMagnitude,
      modelConfidenceScore: decisionBundle.modelConfidence?.score,
      modelConfidenceBand: decisionBundle.modelConfidence?.band,
      modelConfidenceTierConstant: decisionBundle.modelConfidence
        ? isTierConstantConfidence(decisionBundle.modelConfidence)
        : undefined,
      coverProb: spreadDecision?.coverProb ?? undefined,
      playToNotes: spreadDecision?.playTo?.notes,
      playToPlay: spreadDecision?.playTo?.playTo,
      playToLean: spreadDecision?.playTo?.leanTo,
      playToPass: spreadDecision?.playTo?.passFrom,
      fairLine: spreadDecision?.fairLine,
      decisionMarketLine: spreadDecision?.marketLine,
      isBestBet: spreadDecision?.isBestBet,
      keyNumberCross: spreadDecision?.keyNumberCross,
      weekRegime: decisionBundle.weekRegime,
      ...sharedMatchup,
    } as EdgeBoardRow);

    rows.push({
      id: `${idBase}-total`,
      game,
      time,
      commenceTime,
      market: "Total",
      open: marketTotal,
      best: bestTotal ?? marketTotal,
      book: bestTotalBook ?? (bestTotal || marketTotal ? "market" : undefined),
      bookKey:
        bestTotalBook ?? (bestTotal || marketTotal ? "market" : undefined),
      openJuice: undefined,
      openJuiceHome: undefined,
      bestJuice: formatJuice(line.bestTotalOverJuice),
      bestJuiceHome: formatJuice(line.bestTotalUnderJuice),
      kei: keiTotal,
      modelKei: modelKeiTotal,
      week,
      seasonType,
      publishTag: publishTagTotal,
      actionLabel: actionLabelTotal ?? undefined,
      decision: totalDecision
        ? decisionResultToApi(totalDecision)
        : undefined,
      edgeMagnitude: totalDecision?.edgeMagnitude,
      modelConfidenceScore: decisionBundle.modelConfidence?.score,
      modelConfidenceBand: decisionBundle.modelConfidence?.band,
      modelConfidenceTierConstant: decisionBundle.modelConfidence
        ? isTierConstantConfidence(decisionBundle.modelConfidence)
        : undefined,
      coverProb: totalDecision?.coverProb ?? undefined,
      playToNotes: totalDecision?.playTo?.notes,
      playToPlay: totalDecision?.playTo?.playTo,
      playToLean: totalDecision?.playTo?.leanTo,
      playToPass: totalDecision?.playTo?.passFrom,
      fairLine: totalDecision?.fairLine,
      decisionMarketLine: totalDecision?.marketLine,
      isBestBet: totalDecision?.isBestBet,
      keyNumberCross: totalDecision?.keyNumberCross,
      weekRegime: decisionBundle.weekRegime,
      ...sharedMatchup,
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

function rowHasKei(row: EdgeBoardRow): boolean {
  return Boolean(row.kei && String(row.kei).trim() && String(row.kei) !== "—");
}

/**
 * NFL Edge Board is projection-backed (REG fair-lines). Drop odds-only extras
 * (common in PRE) that have Open/Best but no KEINFL — avoids empty-KEI noise.
 */
export function filterNflProjectionBackedRows(
  rows: EdgeBoardRow[],
): EdgeBoardRow[] {
  const keiGames = new Set<string>();
  for (const row of rows) {
    if (row.game && rowHasKei(row)) keiGames.add(row.game);
  }
  if (keiGames.size === 0) return [];
  return rows.filter((row) => row.game != null && keiGames.has(row.game));
}

function rowSeasonType(row: EdgeBoardRow): string {
  return String(
    (row as EdgeBoardRow & { seasonType?: string }).seasonType ?? "",
  )
    .trim()
    .toUpperCase();
}

/**
 * Week 1 / single-week tab: strict week match, REG only.
 * Empty stays empty — never fall through to another week or the full slate.
 * PRE exhibitions are excluded even if they share a week number.
 */
export function filterNflStrictWeekRows(
  rows: EdgeBoardRow[],
  week: number,
): EdgeBoardRow[] {
  const target = Number.isFinite(week) ? Math.max(1, Math.trunc(week)) : 1;
  return rows.filter((row) => {
    if (rowWeek(row) !== target) return false;
    const st = rowSeasonType(row);
    if (st === "PRE" || st === "POST") return false;
    return true;
  });
}

/**
 * Live / current-week helper. If that week is missing from the pull window
 * (early season / clock skew), show the nearest upcoming week — never dump
 * the full multi-week board as a silent fallback.
 * Prefer filterNflStrictWeekRows for the launch Week 1 tab.
 */
export function filterNflCurrentWeekRows(
  rows: EdgeBoardRow[],
  currentWeek: number,
): EdgeBoardRow[] {
  const week = Number.isFinite(currentWeek) ? Math.max(1, currentWeek) : 1;
  const strict = filterNflStrictWeekRows(rows, week);
  if (strict.length > 0) return strict;

  const weeks = [
    ...new Set(
      rows
        .map(rowWeek)
        .filter((w): w is number => typeof w === "number" && Number.isFinite(w)),
    ),
  ].sort((a, b) => a - b);
  if (weeks.length === 0) {
    // Week missing from payload (schema / join gap). Keep rows so the assembler
    // can stamp currentWeek for season gates — do not silently empty the board.
    return rows.filter((row) => {
      const st = rowSeasonType(row);
      return st !== "PRE" && st !== "POST";
    });
  }

  const next = weeks.find((w) => w >= week) ?? weeks[weeks.length - 1]!;
  return filterNflStrictWeekRows(rows, next);
}

/** Full season board = every game we currently have sportsbook odds on. */
export function filterNflOddsPostedRows(rows: EdgeBoardRow[]): EdgeBoardRow[] {
  const pricedGames = new Set<string>();
  for (const row of rows) {
    if (row.game && hasSportsbookPrice(row)) {
      pricedGames.add(row.game);
    }
  }
  // Odds slate with no books yet: keep projection-backed rows (empty Open/Best)
  // rather than inventing a sportsbook slate.
  if (pricedGames.size === 0) return filterNflProjectionBackedRows(rows);
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
    const src = odds as EdgeBoardRow & {
      bookKey?: string;
      openJuice?: string;
      openJuiceHome?: string;
      bestJuice?: string;
      bestJuiceHome?: string;
    };
    if (odds.open) target.open = odds.open;
    if (odds.best) target.best = odds.best;
    if (odds.book)
      (target as EdgeBoardRow & { book?: string }).book = odds.book;
    if (src.bookKey) {
      (target as EdgeBoardRow & { bookKey?: string }).bookKey = src.bookKey;
    }
    if (src.openJuice) {
      (target as EdgeBoardRow & { openJuice?: string }).openJuice =
        src.openJuice;
    }
    if (src.openJuiceHome) {
      (target as EdgeBoardRow & { openJuiceHome?: string }).openJuiceHome =
        src.openJuiceHome;
    }
    if (src.bestJuice) {
      (target as EdgeBoardRow & { bestJuice?: string }).bestJuice =
        src.bestJuice;
    }
    if (src.bestJuiceHome) {
      (target as EdgeBoardRow & { bestJuiceHome?: string }).bestJuiceHome =
        src.bestJuiceHome;
    }
    if (odds.time) target.time = odds.time;
    if (odds.commenceTime) target.commenceTime = odds.commenceTime;
  }

  // Do not append odds-only extras (PRE noise, unmatched books). NFL board is
  // fair-line / KEINFL-backed; Odds overlays prices onto those rows only.
  return fairRows;
}
