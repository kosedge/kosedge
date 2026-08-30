/**
 * NFL Fantasy Pick’em card — straight-up winners ranked by confidence.
 *
 * Sort key (stable):
 * 1. Tag bucket: PLAY (spread or ML publish tag) → LEAN → everything else
 * 2. Inside a bucket: larger KEI win-prob gap (max(home, away) − 0.5).
 *    Fallback: larger |KEI spread|. Never invent a number.
 * 3. Tie-break: earlier kickoff, then gameId.
 *
 * Games missing both win probs get side: null and sink to the bottom
 * (leftover low confidence ranks). Side is always SU from KEI — spread
 * PLAY only boosts rank, it is not an ATS pick.
 */

import type { NflFairLineRow } from "@/lib/nfl-fair-lines";

export type NflPickemSide = "home" | "away" | null;
export type NflPickemTag = "PLAY" | "LEAN" | "PASS" | null;

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
  /** Unique confidence N … 1 (N = most confident = slate size). */
  confidence: number;
  /** Effective publish tag for sort/display (spread or ML). */
  tag: NflPickemTag;
};

type Rankable = {
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

function compareRankable(a: Rankable, b: Rankable): number {
  // Missing-side games sink to the bottom regardless of tag.
  const aHasSide = a.side != null ? 0 : 1;
  const bHasSide = b.side != null ? 0 : 1;
  if (aHasSide !== bHasSide) return aHasSide - bHasSide;

  if (a.tagBucket !== b.tagBucket) return a.tagBucket - b.tagBucket;

  // Larger gap first; null gap sorts after known gaps (never invent).
  if (a.gap != null && b.gap != null && a.gap !== b.gap) {
    return b.gap - a.gap;
  }
  if (a.gap != null && b.gap == null) return -1;
  if (a.gap == null && b.gap != null) return 1;

  // Fallback: larger |KEI spread|.
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

export function buildNflPickemCard(lines: NflFairLineRow[]): NflPickemPick[] {
  const rankable: Rankable[] = lines.map((row) => {
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

  rankable.sort(compareRankable);

  const n = rankable.length;
  return rankable.map((item, index) => {
    const confidence = n - index;
    const { row, side, winProb, keiSpreadHome, tag } = item;
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
      winProb,
      keiSpreadHome,
      keiSpreadPick,
      confidence,
      tag,
    };
  });
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
