/**
 * NFL Fantasy Pick’em cards — straight-up and ATS, ranked 1–N.
 *
 * SU sort (stable):
 * 1. Tag bucket: PLAY (spread or ML) → LEAN → everything else
 * 2. Inside bucket: larger KEI win-prob gap; fallback |KEI spread|
 * 3. Tie-break: earlier kickoff, then gameId
 *
 * ATS sort (stable):
 * 1. No-pick / missing line sinks last
 * 2. Tag bucket from publishTagSpread only: PLAY → LEAN → other
 * 3. Inside bucket: larger |keiHome − marketHome|
 * 4. Tie-break: earlier kickoff, then gameId
 *
 * Rank is always index + 1 after sort (1 = strongest on the week).
 */

import type { NflFairLineRow } from "@/lib/nfl-fair-lines";

export type NflPickemSide = "home" | "away" | null;
export type NflPickemTag = "PLAY" | "LEAN" | "PASS" | null;
export type NflPickemTab = "ats" | "su";

export type NflPickemPick = {
  gameId: string;
  week: number | null;
  seasonType: string | null;
  kickoff: string | null;
  homeTeam: string;
  awayTeam: string;
  homeAbbr: string;
  awayAbbr: string;
  /** SU side from KEI win probs; null when both probs missing. */
  side: NflPickemSide;
  pickAbbr: string | null;
  oppAbbr: string | null;
  /** Win prob of the picked side (0–1); null when no pick. */
  winProb: number | null;
  /** KEI home spread (handicapSpreadHome ?? spreadHome); null when missing. */
  keiSpreadHome: number | null;
  /**
   * KEI spread from the pick’s perspective (negative = favorite).
   * Null when no pick or no spread.
   */
  keiSpreadPick: number | null;
  /** Unique rank 1 … N (1 = strongest pick on the week). */
  rank: number;
  /** Effective publish tag for sort/display (spread or ML on SU). */
  tag: NflPickemTag;
};

export type NflAtsPickemPick = NflPickemPick & {
  /** Stake line home (stake → DK → FD → consensus). */
  marketSpreadHome: number | null;
  /** Market/stake number from the pick’s perspective. */
  marketSpreadPick: number | null;
  /** keiHome − marketHome (home-spread convention). Null when no ATS pick. */
  atsEdge: number | null;
  /** Book of the stake line when known. */
  stakeBook: string | null;
};

type SuRankable = {
  row: NflFairLineRow;
  side: NflPickemSide;
  homeWin: number | null;
  awayWin: number | null;
  winProb: number | null;
  gap: number | null;
  keiSpreadHome: number | null;
  absSpread: number | null;
  tag: NflPickemTag;
  tagBucket: number;
  kickoffMs: number;
};

type AtsRankable = {
  row: NflFairLineRow;
  side: NflPickemSide;
  keiSpreadHome: number | null;
  marketSpreadHome: number | null;
  atsEdge: number | null;
  absEdge: number | null;
  stakeBook: string | null;
  tag: NflPickemTag;
  tagBucket: number;
  kickoffMs: number;
};

function resolveWinProbs(row: NflFairLineRow): {
  home: number | null;
  away: number | null;
} {
  const home = row.handicapHomeWinProb ?? row.homeWinProb;
  const away = row.handicapAwayWinProb ?? row.awayWinProb;
  return {
    home: home != null && Number.isFinite(home) ? home : null,
    away: away != null && Number.isFinite(away) ? away : null,
  };
}

function resolveKeiSpreadHome(row: NflFairLineRow): number | null {
  const spread = row.handicapSpreadHome ?? row.spreadHome;
  return spread != null && Number.isFinite(spread) ? spread : null;
}

/**
 * Contest / stake line for ATS — never best-of-books.
 * Order: stake → DK → FD → consensus market.
 */
export function resolveAtsMarketLineHome(row: NflFairLineRow): {
  marketHome: number | null;
  stakeBook: string | null;
} {
  const candidates: Array<{ value: number | null; book: string | null }> = [
    { value: row.stakeSpreadHome, book: row.stakeSpreadBook },
    { value: row.dkSpreadHome, book: "DraftKings" },
    { value: row.fdSpreadHome, book: "FanDuel" },
    { value: row.marketSpreadHome, book: null },
  ];
  for (const c of candidates) {
    if (c.value != null && Number.isFinite(c.value)) {
      return { marketHome: c.value, stakeBook: c.book };
    }
  }
  return { marketHome: null, stakeBook: null };
}

/**
 * PLAY if either spread or ML publish tag is PLAY; else LEAN if either;
 * else PASS if either; else null. Tag only affects sort — side stays SU.
 */
export function resolvePickemTag(row: NflFairLineRow): NflPickemTag {
  const tags = [row.publishTagSpread, row.publishTagMl];
  if (tags.includes("PLAY")) return "PLAY";
  if (tags.includes("LEAN")) return "LEAN";
  if (tags.includes("PASS")) return "PASS";
  return null;
}

/** ATS tag — spread publish tag only. ML PLAY must not promote an ATS row. */
export function resolveAtsPickemTag(row: NflFairLineRow): NflPickemTag {
  const tag = row.publishTagSpread;
  if (tag === "PLAY" || tag === "LEAN" || tag === "PASS") return tag;
  return null;
}

function tagBucket(tag: NflPickemTag): number {
  if (tag === "PLAY") return 0;
  if (tag === "LEAN") return 1;
  return 2;
}

function resolveSide(home: number | null, away: number | null): NflPickemSide {
  if (home == null && away == null) return null;
  if (home != null && away != null) {
    if (home === away) {
      // Exact tie: prefer home for a deterministic side (still ranks by gap=0).
      return "home";
    }
    return home > away ? "home" : "away";
  }
  if (home != null) return "home";
  return "away";
}

/**
 * ATS side from home-spread edge (negative home = home favored).
 * edgeHome = keiHome − marketHome
 *   < 0 → home covers vs the number
 *   > 0 → away covers vs the number
 *   = 0 → no edge → sink
 */
export function resolveAtsSide(
  keiHome: number | null,
  marketHome: number | null,
): { side: NflPickemSide; atsEdge: number | null } {
  if (keiHome == null || marketHome == null) {
    return { side: null, atsEdge: null };
  }
  const atsEdge = keiHome - marketHome;
  if (atsEdge === 0) return { side: null, atsEdge: 0 };
  if (atsEdge < 0) return { side: "home", atsEdge };
  return { side: "away", atsEdge };
}

function winProbGap(home: number | null, away: number | null): number | null {
  if (home == null && away == null) return null;
  const max = Math.max(
    home ?? Number.NEGATIVE_INFINITY,
    away ?? Number.NEGATIVE_INFINITY,
  );
  if (!Number.isFinite(max)) return null;
  return max - 0.5;
}

function kickoffMs(startTime: string | null): number {
  if (!startTime) return Number.POSITIVE_INFINITY;
  const t = new Date(startTime).getTime();
  return Number.isFinite(t) ? t : Number.POSITIVE_INFINITY;
}

function compareSuRankable(a: SuRankable, b: SuRankable): number {
  const aHasSide = a.side != null ? 0 : 1;
  const bHasSide = b.side != null ? 0 : 1;
  if (aHasSide !== bHasSide) return aHasSide - bHasSide;

  if (a.tagBucket !== b.tagBucket) return a.tagBucket - b.tagBucket;

  if (a.gap != null && b.gap != null && a.gap !== b.gap) {
    return b.gap - a.gap;
  }
  if (a.gap != null && b.gap == null) return -1;
  if (a.gap == null && b.gap != null) return 1;

  if (
    a.absSpread != null &&
    b.absSpread != null &&
    a.absSpread !== b.absSpread
  ) {
    return b.absSpread - a.absSpread;
  }
  if (a.absSpread != null && b.absSpread == null) return -1;
  if (a.absSpread == null && b.absSpread != null) return 1;

  if (a.kickoffMs !== b.kickoffMs) return a.kickoffMs - b.kickoffMs;
  return a.row.gameId.localeCompare(b.row.gameId);
}

function compareAtsRankable(a: AtsRankable, b: AtsRankable): number {
  const aHasSide = a.side != null ? 0 : 1;
  const bHasSide = b.side != null ? 0 : 1;
  if (aHasSide !== bHasSide) return aHasSide - bHasSide;

  if (a.tagBucket !== b.tagBucket) return a.tagBucket - b.tagBucket;

  if (a.absEdge != null && b.absEdge != null && a.absEdge !== b.absEdge) {
    return b.absEdge - a.absEdge;
  }
  if (a.absEdge != null && b.absEdge == null) return -1;
  if (a.absEdge == null && b.absEdge != null) return 1;

  if (a.kickoffMs !== b.kickoffMs) return a.kickoffMs - b.kickoffMs;
  return a.row.gameId.localeCompare(b.row.gameId);
}

function toPickFields(
  row: NflFairLineRow,
  side: NflPickemSide,
  keiSpreadHome: number | null,
): Pick<
  NflPickemPick,
  | "gameId"
  | "week"
  | "seasonType"
  | "kickoff"
  | "homeTeam"
  | "awayTeam"
  | "homeAbbr"
  | "awayAbbr"
  | "side"
  | "pickAbbr"
  | "oppAbbr"
  | "keiSpreadHome"
  | "keiSpreadPick"
> {
  const pickAbbr =
    side === "home" ? row.homeAbbr : side === "away" ? row.awayAbbr : null;
  const oppAbbr =
    side === "home" ? row.awayAbbr : side === "away" ? row.homeAbbr : null;
  let keiSpreadPick: number | null = null;
  if (side === "home" && keiSpreadHome != null) {
    keiSpreadPick = keiSpreadHome;
  } else if (side === "away" && keiSpreadHome != null) {
    keiSpreadPick = -keiSpreadHome;
  }
  return {
    gameId: row.gameId,
    week: row.week,
    seasonType: row.seasonType,
    kickoff: row.startTime,
    homeTeam: row.homeTeam,
    awayTeam: row.awayTeam,
    homeAbbr: row.homeAbbr,
    awayAbbr: row.awayAbbr,
    side,
    pickAbbr,
    oppAbbr,
    keiSpreadHome,
    keiSpreadPick,
  };
}

/** Straight-up card: KEI winner, ranked 1–N. */
export function buildNflPickemCard(lines: NflFairLineRow[]): NflPickemPick[] {
  const rankable: SuRankable[] = lines.map((row) => {
    const { home, away } = resolveWinProbs(row);
    const side = resolveSide(home, away);
    const keiSpreadHome = resolveKeiSpreadHome(row);
    const tag = resolvePickemTag(row);
    const gap = winProbGap(home, away);
    return {
      row,
      side,
      homeWin: home,
      awayWin: away,
      winProb: side === "home" ? home : side === "away" ? away : null,
      gap,
      keiSpreadHome,
      absSpread: keiSpreadHome != null ? Math.abs(keiSpreadHome) : null,
      tag,
      tagBucket: tagBucket(tag),
      kickoffMs: kickoffMs(row.startTime),
    };
  });

  rankable.sort(compareSuRankable);

  return rankable.map((item, index) => {
    const { row, side, winProb, keiSpreadHome, tag } = item;
    return {
      ...toPickFields(row, side, keiSpreadHome),
      winProb,
      rank: index + 1,
      tag,
    };
  });
}

/** ATS card: cover vs stake line, ranked 1–N. */
export function buildNflAtsPickemCard(
  lines: NflFairLineRow[],
): NflAtsPickemPick[] {
  const rankable: AtsRankable[] = lines.map((row) => {
    const keiSpreadHome = resolveKeiSpreadHome(row);
    const { marketHome, stakeBook } = resolveAtsMarketLineHome(row);
    const { side, atsEdge } = resolveAtsSide(keiSpreadHome, marketHome);
    const tag = resolveAtsPickemTag(row);
    return {
      row,
      side,
      keiSpreadHome,
      marketSpreadHome: marketHome,
      atsEdge,
      absEdge: atsEdge != null ? Math.abs(atsEdge) : null,
      stakeBook,
      tag,
      tagBucket: tagBucket(tag),
      kickoffMs: kickoffMs(row.startTime),
    };
  });

  rankable.sort(compareAtsRankable);

  return rankable.map((item, index) => {
    const {
      row,
      side,
      keiSpreadHome,
      marketSpreadHome,
      atsEdge,
      stakeBook,
      tag,
    } = item;
    let marketSpreadPick: number | null = null;
    if (side === "home" && marketSpreadHome != null) {
      marketSpreadPick = marketSpreadHome;
    } else if (side === "away" && marketSpreadHome != null) {
      marketSpreadPick = -marketSpreadHome;
    }

    return {
      ...toPickFields(row, side, keiSpreadHome),
      winProb: null,
      marketSpreadHome,
      marketSpreadPick,
      atsEdge,
      stakeBook,
      rank: index + 1,
      tag,
    };
  });
}

export function parsePickemTab(raw: string | undefined): NflPickemTab {
  return raw === "su" ? "su" : "ats";
}

/** REG season week chips — do not derive from a near-term fair-lines window. */
export const PICKEM_REG_WEEK_CHIPS: readonly number[] = Array.from(
  { length: 18 },
  (_, i) => i + 1,
);

export function isPickemRegSeasonType(
  seasonType: string | null | undefined,
): boolean {
  const st = (seasonType ?? "").trim().toUpperCase();
  return st === "" || st === "REG";
}

/** REG weeks that currently have fair-line rows (may be a near-term subset). */
export function listPickemRegWeeksWithLines(lines: NflFairLineRow[]): number[] {
  const weeks = new Set<number>();
  for (const row of lines) {
    if (row.week == null || !Number.isFinite(row.week)) continue;
    if (!isPickemRegSeasonType(row.seasonType)) continue;
    weeks.add(row.week);
  }
  return [...weeks].sort((a, b) => a - b);
}

/**
 * Default week: currentWeek when it has REG rows; else earliest REG week in
 * the payload; else 1. Avoid landing on an empty bye week when Week 1 is present.
 */
export function resolvePickemDefaultWeek(
  lines: NflFairLineRow[],
  currentWeek: number,
): number {
  const weeksWithLines = listPickemRegWeeksWithLines(lines);
  if (
    Number.isFinite(currentWeek) &&
    currentWeek > 0 &&
    weeksWithLines.includes(Math.floor(currentWeek))
  ) {
    return Math.floor(currentWeek);
  }
  if (weeksWithLines.length > 0) return weeksWithLines[0]!;
  return 1;
}

/** Filter REG (or matching product week season type) lines for a week. */
export function filterPickemWeekLines(
  lines: NflFairLineRow[],
  week: number,
  opts?: { seasonType?: string },
): NflFairLineRow[] {
  const seasonType = (opts?.seasonType ?? "REG").toUpperCase();
  return lines.filter((row) => {
    if (row.week !== week) return false;
    const st = (row.seasonType ?? "").trim().toUpperCase();
    // Never mix PRE/POST onto a REG card. Null seasonType treated as REG
    // only when the product week filter is REG (labeled PRE always wins).
    if (seasonType === "REG") {
      return st === "" || st === "REG";
    }
    return st === seasonType;
  });
}
