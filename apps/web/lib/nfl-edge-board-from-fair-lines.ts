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
import { coerceNflWeek } from "@/lib/nfl-edge-board-week";
import { NFL_TEAM_DIRECTORY } from "@/lib/nfl-team-intel";

const ET = "America/New_York";

function formatSigned(point: number): string {
  const rounded = Math.round(point * 10) / 10;
  if (Object.is(rounded, -0) || rounded === 0) return "+0";
  return rounded > 0 ? `+${rounded}` : String(rounded);
}

function formatKickoffParts(iso: string | null): {
  time?: string;
  kickoffDate?: string;
  kickoffTime?: string;
} {
  if (!iso) return {};
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return {};
  const kickoffDate = d.toLocaleDateString("en-US", {
    timeZone: ET,
    month: "2-digit",
    day: "2-digit",
  });
  const kickoffTime = d.toLocaleTimeString("en-US", {
    timeZone: ET,
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
  return {
    kickoffDate,
    kickoffTime,
    time: `${kickoffDate} ${kickoffTime} ET`,
  };
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
 * Open = first-captured open when available (never invented as current).
 * Best = current best-of-books / consensus (moves on odds refresh).
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
    const kickoff = formatKickoffParts(commenceTime ?? null);
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
    // Current = latest consensus / best-of-books (moves with odds refresh).
    const marketAwaySpread =
      line.marketSpreadHome != null
        ? awaySpreadFromHome(line.marketSpreadHome)
        : undefined;
    const marketTotal =
      line.marketTotal != null
        ? String(Math.round(line.marketTotal * 10) / 10)
        : undefined;
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
    // Open = first-captured / official open only. Never invent open = current.
    const openAwaySpread =
      line.openSpreadHome != null
        ? awaySpreadFromHome(line.openSpreadHome)
        : undefined;
    const openTotal =
      line.openTotal != null
        ? String(Math.round(line.openTotal * 10) / 10)
        : undefined;
    const linesAsOf = line.oddsCapturedAt ?? undefined;

    const week = coerceNflWeek(line.week) ?? undefined;
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
          openingSpreadHome: line.openSpreadHome,
          openingTotal: line.openTotal,
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
      time: kickoff.time,
      kickoffDate: kickoff.kickoffDate,
      kickoffTime: kickoff.kickoffTime,
      commenceTime,
      market: "Spread",
      // Open immutable once set from first capture; Current in `best`.
      open: openAwaySpread,
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
      linesAsOf,
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
      time: kickoff.time,
      kickoffDate: kickoff.kickoffDate,
      kickoffTime: kickoff.kickoffTime,
      commenceTime,
      market: "Total",
      open: openTotal,
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
      linesAsOf,
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
  return coerceNflWeek((row as EdgeBoardRow & { week?: unknown }).week);
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
      kickoffDate?: string;
      kickoffTime?: string;
      linesAsOf?: string;
      /** True open from first capture — rare on Odds API path. */
      openIsImmutable?: boolean;
    };
    const tgt = target as EdgeBoardRow & {
      open?: string;
      best?: string;
      book?: string;
      bookKey?: string;
      openJuice?: string;
      openJuiceHome?: string;
      bestJuice?: string;
      bestJuiceHome?: string;
      kickoffDate?: string;
      kickoffTime?: string;
      linesAsOf?: string;
    };
    // Current line moves with odds. Never overwrite a set Open with live books
    // (Odds API "open" is preferred-book current, not first-captured open).
    if (odds.best) tgt.best = odds.best;
    if (odds.book) tgt.book = odds.book;
    if (src.bookKey) tgt.bookKey = src.bookKey;
    if (src.bestJuice) tgt.bestJuice = src.bestJuice;
    if (src.bestJuiceHome) tgt.bestJuiceHome = src.bestJuiceHome;
    // Fill Open only when missing AND the odds row marks a true immutable open.
    if (!tgt.open && src.openIsImmutable && odds.open) {
      tgt.open = odds.open;
      if (src.openJuice) tgt.openJuice = src.openJuice;
      if (src.openJuiceHome) tgt.openJuiceHome = src.openJuiceHome;
    }
    if (odds.time) tgt.time = odds.time;
    if (odds.commenceTime) tgt.commenceTime = odds.commenceTime;
    if (src.kickoffDate) tgt.kickoffDate = src.kickoffDate;
    if (src.kickoffTime) tgt.kickoffTime = src.kickoffTime;
    if (src.linesAsOf) tgt.linesAsOf = src.linesAsOf;
  }

  // Do not append odds-only extras (PRE noise, unmatched books). NFL board is
  // fair-line / KEINFL-backed; Odds overlays prices onto those rows only.
  return fairRows;
}
