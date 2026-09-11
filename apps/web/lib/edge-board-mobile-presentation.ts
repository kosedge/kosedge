/**
 * Edge Board mobile card — presentation mapping only.
 *
 * Does not recalculate fair / market / edge / confidence / book / game IDs.
 * Reads already-assembled LegacyEdgeBoardRow fields and #508 customer-truth
 * helpers. Fail closed on Fair/Market/Edge or sign/side disagreement.
 *
 * Team labels come from the canonical abbr truth layer already on the row
 * (awayAbbr / homeAbbr, NFL via canonicalizeNflTeam). No UI alias table.
 */

import {
  EDGE_ARITH_TOLERANCE,
  formatSelectedSideLineEdge,
  formatSelectedSideProbEdge,
  isFiniteNumber,
  reconcileHandicapCustomerEdge,
  reconcileTotalCustomerEdge,
} from "@/lib/edge-board-customer-truth";
import { canonicalizeNflTeam } from "@/lib/nfl-canonical-teams";
import {
  displayActionLabel,
  reachableConfidenceBands,
} from "@/lib/nfl-dead-tiers";
import type { ActionLabel, ConfidenceBand } from "@/lib/nfl-decision-engine";
import type {
  LegacyEdgeBoardRow,
  PricePair,
  Tag,
} from "@/lib/flat-rows-to-legacy";

export const UNICODE_MINUS = "\u2212";
/** Locked Kosedge Fair gold — mobile hero only; do not retoken desktop. */
export const KOSEDGE_FAIR_GOLD = "#F6C85F";
export const KOSEDGE_FAIR_GOLD_DIM = "#E5B94E";

export type PublishActionLabel = "PLAY" | "LEAN" | "PASS";

export type MobileTruthFlag =
  | "spread_fair_market_edge_mismatch"
  | "total_fair_market_edge_mismatch"
  | "spread_side_disagrees_favor"
  | "total_side_disagrees_favor"
  | "spread_decision_vs_best_mismatch"
  | "total_decision_vs_best_mismatch"
  | "fair_spread_pair_mismatch"
  | "fair_total_pair_mismatch";

export type MobileLinePaint = {
  teamLabeled: string;
  juice: string | null;
  /** Sportsbook key/name of the exact displayed price — never decorative. */
  bookKey: string | null;
  trustFootnote: string | null;
};

export type MobileTotalPaint = {
  over: string;
  under: string;
  overJuice: string | null;
  underJuice: string | null;
  bookKey: string | null;
  trustFootnote: string | null;
};

export type MobileInterpretation = {
  status: PublishActionLabel | null;
  sideLabel: string | null;
  magnitude: string | null;
  subdued: boolean;
  failClosed: boolean;
};

export type MobileVenue = {
  kind: "neutral" | "ordinary";
  text: string;
};

export type MobileCardModel = {
  matchup: string;
  kickoffDate: string | null;
  kickoffTime: string | null;
  kickoffTz: string | null;
  venue: MobileVenue | null;
  isMoneyline: boolean;
  marketSpread: MobileLinePaint | null;
  fairSpread: MobileLinePaint | null;
  marketTotal: MobileTotalPaint | null;
  fairTotal: { over: string; under: string } | null;
  marketMlAway: string | null;
  marketMlHome: string | null;
  fairMlAway: string | null;
  fairMlHome: string | null;
  spreadInterp: MobileInterpretation | null;
  totalInterp: MobileInterpretation | null;
  /** Existing customer-live band only — omit when absent or unreachable. */
  confidence: string | null;
  openSpread: string | null;
  openTotal: string | null;
  linesAsOfLabel: string | null;
  linesStale: boolean;
  asOfUnavailable: boolean;
  marketHorizonLabel: string | null;
  oddsWithoutKei: boolean;
  overview: string | null;
  /** Raw model — Overview only. */
  modelNote: string | null;
  sizeDown: boolean;
  truthFlags: MobileTruthFlag[];
};

const BLANK = new Set(["", "—", "–", "-", "--", "undefined", "NaN", "null"]);

export function isBlankLabel(value: unknown): boolean {
  if (value == null) return true;
  const s = String(value).trim();
  return !s || BLANK.has(s);
}

export function parseSignedLineLabel(
  raw: string | number | null | undefined,
): number | null {
  if (typeof raw === "number") {
    return isFiniteNumber(raw) ? raw : null;
  }
  if (raw == null) return null;
  const s = String(raw).trim();
  if (isBlankLabel(s)) return null;
  const n = Number(s.replace(/[^+\-\d.]/g, ""));
  return Number.isFinite(n) ? n : null;
}

export function parseTotalLabel(
  raw: string | number | null | undefined,
): number | null {
  if (typeof raw === "number") {
    return isFiniteNumber(raw) ? raw : null;
  }
  if (raw == null) return null;
  const s = String(raw).trim();
  if (isBlankLabel(s)) return null;
  const n = Number(s.replace(/[^\d.]/g, ""));
  return Number.isFinite(n) ? n : null;
}

export function signedLinesAgree(
  a: number,
  b: number,
  tolerance: number = EDGE_ARITH_TOLERANCE,
): boolean {
  return Math.abs(a - b) <= tolerance;
}

export function cleanJuice(raw: string | null | undefined): string | null {
  if (isBlankLabel(raw)) return null;
  const s = String(raw).trim().replace(/[()]/g, "");
  if (isBlankLabel(s)) return null;
  const n = Number(s.replace(/[^\d+\-]/g, ""));
  if (!Number.isFinite(n) || n === 0) return null;
  return n > 0 ? `+${n}` : String(n);
}

export function formatLineAbs(n: number): string {
  const abs = Math.abs(n);
  const rounded = Math.round(abs * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

/** Favorite-labeled spread from a home-signed number + canonical abbrs. */
export function formatTeamLabeledSpread(args: {
  homeSigned: number;
  homeAbbr: string;
  awayAbbr: string;
}): string {
  const home = args.homeAbbr.trim();
  const away = args.awayAbbr.trim();
  if (args.homeSigned === 0 || Object.is(args.homeSigned, -0)) {
    return `${home} PK`;
  }
  const body = `${UNICODE_MINUS}${formatLineAbs(args.homeSigned)}`;
  return args.homeSigned < 0 ? `${home} ${body}` : `${away} ${body}`;
}

export function formatOuLevel(n: number): { over: string; under: string } {
  const level = formatLineAbs(n);
  return { over: `O ${level}`, under: `U ${level}` };
}

export function formatTeamLabeledAmerican(args: {
  abbr: string;
  american: number;
}): string {
  const n = Math.round(args.american);
  const body =
    n === 0 ? "PK" : n > 0 ? `+${n}` : `${UNICODE_MINUS}${Math.abs(n)}`;
  return `${args.abbr.trim()} ${body}`;
}

/**
 * Canonical abbr for customer chrome.
 * NFL: existing truth-layer canonicalizeNflTeam only.
 * Other sports: assembled abbr as-is (already uppercased upstream).
 * No hard-coded UI nickname table.
 */
export function presentationAbbr(args: {
  sportKey: string;
  abbr?: string | null;
  nameFallback?: string | null;
}): string {
  const fromAbbr = String(args.abbr ?? "").trim();
  const fromName = String(args.nameFallback ?? "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  const seed =
    fromAbbr ||
    (fromName.length === 1
      ? fromName[0]!
      : fromName[fromName.length - 1] || "");
  if (!seed) return "";
  const sport = String(args.sportKey).toLowerCase();
  if (sport === "nfl") {
    return canonicalizeNflTeam(seed) ?? seed.toUpperCase();
  }
  return seed.toUpperCase();
}

export function toPublishActionLabel(
  label: ActionLabel | Tag | null | undefined,
): PublishActionLabel | null {
  if (label === "PLAY" || label === "LEAN" || label === "PASS") return label;
  const shown = displayActionLabel(label as ActionLabel | null | undefined);
  if (shown === "PLAY" || shown === "LEAN" || shown === "PASS") return shown;
  if (shown == null) return null;
  return "PASS";
}

export function formatCustomerConfidence(args: {
  band?: ConfidenceBand | null;
  score?: number | null;
  tierConstant?: boolean | null;
}): string | null {
  const band = args.band;
  if (!band) return null;
  if (!reachableConfidenceBands().includes(band)) return null;
  if (args.tierConstant || args.score == null) return `Conf ${band}`;
  return `Conf ${band} ${Math.round(args.score * 100)}%`;
}

export function parseKickoffStack(args: {
  kickoffDate?: string;
  kickoffTime?: string;
  time?: string;
}): { date: string | null; time: string | null; local: string | null } {
  if (args.kickoffDate || args.kickoffTime) {
    return {
      date: isBlankLabel(args.kickoffDate) ? null : String(args.kickoffDate),
      time: isBlankLabel(args.kickoffTime) ? null : String(args.kickoffTime),
      local: "ET",
    };
  }
  const raw = String(args.time ?? "").trim();
  if (!raw || raw === "—") return { date: null, time: null, local: null };
  const m = raw.match(/^(\d{1,2}\/\d{1,2})\s+(.+?)(?:\s+(ET|PT|CT|MT))?$/i);
  if (m) {
    return {
      date: m[1]!,
      time: m[2]!.trim(),
      local: (m[3] || "ET").toUpperCase(),
    };
  }
  return { date: raw, time: null, local: null };
}

export function formatLinesAsOf(iso?: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function shortTeamWord(name: string): string {
  const parts = String(name || "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (parts.length === 0) return "";
  return parts[parts.length - 1]!;
}

function pairHasLine(p?: PricePair | null): boolean {
  if (!p) return false;
  return !isBlankLabel(p.top.label) || !isBlankLabel(p.bottom.label);
}

function decisionBookOrNull(args: {
  book?: string | null;
  trustLabel?: string | null;
  numbersMatch: boolean;
}): { bookKey: string | null; trustFootnote: string | null } {
  const trust =
    args.trustLabel === "untrusted" || args.trustLabel === "no book"
      ? args.trustLabel
      : args.book === "untrusted" || args.book === "no book"
        ? args.book
        : null;
  if (!args.numbersMatch) {
    return { bookKey: null, trustFootnote: trust };
  }
  if (trust) return { bookKey: null, trustFootnote: trust };
  if (isBlankLabel(args.book)) return { bookKey: null, trustFootnote: null };
  return { bookKey: String(args.book), trustFootnote: null };
}

export function composeEdgeBoardMobileCard(args: {
  row: LegacyEdgeBoardRow;
  sportKey: string;
}): MobileCardModel {
  const { row } = args;
  const sport = String(args.sportKey).toLowerCase();
  const isNfl = sport === "nfl";
  const isMlb = sport === "mlb";
  const flags: MobileTruthFlag[] = [];

  const awayAbbr = presentationAbbr({
    sportKey: sport,
    abbr: row.awayAbbr,
    nameFallback: row.teamA.name,
  });
  const homeAbbr = presentationAbbr({
    sportKey: sport,
    abbr: row.homeAbbr,
    nameFallback: row.teamB.name,
  });

  const kick = parseKickoffStack({
    kickoffDate: row.kickoffDate,
    kickoffTime: row.kickoffTime,
    time: row.time,
  });

  const matchup = row.isNeutral
    ? `${row.teamA.name} vs ${row.teamB.name}`
    : `${row.teamA.name} @ ${row.teamB.name}`;

  let venue: MobileVenue | null = null;
  if (row.isNeutral) {
    venue = {
      kind: "neutral",
      text: row.siteLabel || "Neutral",
    };
  } else if (row.teamA.site || row.teamB.site) {
    venue = {
      kind: "ordinary",
      text: `${row.teamA.site} / ${row.teamB.site}`,
    };
  }

  const decisionSpread = isFiniteNumber(row.marketLineCurrent)
    ? row.marketLineCurrent
    : null;
  const bestHomeSpread = parseSignedLineLabel(row.bestLine?.bottom.label);
  const fairSpreadNum = isFiniteNumber(row.fairLineKei)
    ? row.fairLineKei
    : parseSignedLineLabel(row.keiLine?.bottom.label);
  const keiBottom = parseSignedLineLabel(row.keiLine?.bottom.label);
  if (
    isFiniteNumber(row.fairLineKei) &&
    keiBottom != null &&
    !signedLinesAgree(row.fairLineKei, keiBottom)
  ) {
    flags.push("fair_spread_pair_mismatch");
  }

  const spreadDecisionMatchesBest =
    decisionSpread != null &&
    bestHomeSpread != null &&
    signedLinesAgree(decisionSpread, bestHomeSpread);

  if (
    decisionSpread != null &&
    bestHomeSpread != null &&
    !spreadDecisionMatchesBest
  ) {
    flags.push("spread_decision_vs_best_mismatch");
  }

  const displaySpread = decisionSpread ?? bestHomeSpread;
  let marketSpread: MobileLinePaint | null = null;
  if (!isMlb && displaySpread != null) {
    const identity = decisionBookOrNull({
      book: row.bestLineBook,
      trustLabel: row.bestLineTrustLabel,
      numbersMatch:
        decisionSpread == null ||
        bestHomeSpread == null ||
        spreadDecisionMatchesBest,
    });
    marketSpread = {
      teamLabeled: formatTeamLabeledSpread({
        homeSigned: displaySpread,
        homeAbbr,
        awayAbbr,
      }),
      juice: spreadDecisionMatchesBest
        ? (cleanJuice(row.bestLine?.bottom.juice) ??
          cleanJuice(row.bestLine?.top.juice))
        : decisionSpread == null
          ? cleanJuice(row.bestLine?.bottom.juice)
          : null,
      bookKey: identity.bookKey,
      trustFootnote: identity.trustFootnote,
    };
  }

  let fairSpread: MobileLinePaint | null = null;
  if (
    !isMlb &&
    fairSpreadNum != null &&
    !flags.includes("fair_spread_pair_mismatch")
  ) {
    fairSpread = {
      teamLabeled: formatTeamLabeledSpread({
        homeSigned: fairSpreadNum,
        homeAbbr,
        awayAbbr,
      }),
      juice: null,
      bookKey: null,
      trustFootnote: null,
    };
  }

  const decisionTotal = isFiniteNumber(row.marketOUCurrent)
    ? row.marketOUCurrent
    : null;
  const bestTotal = parseTotalLabel(row.bestOU?.top.label);
  const fairTotalNum = isFiniteNumber(row.fairOUKei)
    ? row.fairOUKei
    : parseTotalLabel(row.keiOU?.top.label);
  const keiTotalPair = parseTotalLabel(row.keiOU?.top.label);
  if (
    isFiniteNumber(row.fairOUKei) &&
    keiTotalPair != null &&
    !signedLinesAgree(row.fairOUKei, keiTotalPair)
  ) {
    flags.push("fair_total_pair_mismatch");
  }
  const totalDecisionMatchesBest =
    decisionTotal != null &&
    bestTotal != null &&
    signedLinesAgree(decisionTotal, bestTotal);
  if (decisionTotal != null && bestTotal != null && !totalDecisionMatchesBest) {
    flags.push("total_decision_vs_best_mismatch");
  }
  const displayTotal = decisionTotal ?? bestTotal;
  let marketTotal: MobileTotalPaint | null = null;
  if (displayTotal != null) {
    const ou = formatOuLevel(displayTotal);
    const identity = decisionBookOrNull({
      book: row.bestOUBook,
      trustLabel: row.bestOUTrustLabel,
      numbersMatch:
        decisionTotal == null || bestTotal == null || totalDecisionMatchesBest,
    });
    marketTotal = {
      over: ou.over,
      under: ou.under,
      overJuice: totalDecisionMatchesBest
        ? cleanJuice(row.bestOU?.top.juice)
        : decisionTotal == null
          ? cleanJuice(row.bestOU?.top.juice)
          : null,
      underJuice: totalDecisionMatchesBest
        ? cleanJuice(row.bestOU?.bottom.juice)
        : decisionTotal == null
          ? cleanJuice(row.bestOU?.bottom.juice)
          : null,
      bookKey: identity.bookKey,
      trustFootnote: identity.trustFootnote,
    };
  }

  let fairTotal: { over: string; under: string } | null = null;
  if (fairTotalNum != null && !flags.includes("fair_total_pair_mismatch")) {
    fairTotal = formatOuLevel(fairTotalNum);
  }

  let marketMlAway: string | null = null;
  let marketMlHome: string | null = null;
  let fairMlAway: string | null = null;
  let fairMlHome: string | null = null;
  if (isMlb) {
    const awayAm = parseSignedLineLabel(row.bestLine?.top.label);
    const homeAm = parseSignedLineLabel(row.bestLine?.bottom.label);
    if (awayAm != null) {
      marketMlAway = formatTeamLabeledAmerican({
        abbr: awayAbbr,
        american: awayAm,
      });
    }
    if (homeAm != null) {
      marketMlHome = formatTeamLabeledAmerican({
        abbr: homeAbbr,
        american: homeAm,
      });
    }
    const fairAway = parseSignedLineLabel(row.keiLine?.top.label);
    const fairHome = parseSignedLineLabel(row.keiLine?.bottom.label);
    if (fairAway != null) {
      fairMlAway = formatTeamLabeledAmerican({
        abbr: awayAbbr,
        american: fairAway,
      });
    }
    if (fairHome != null) {
      fairMlHome = formatTeamLabeledAmerican({
        abbr: homeAbbr,
        american: fairHome,
      });
    }
  }

  const claimedSpread = row.edgeMagnitudeLine ?? row.edgeLineNum ?? undefined;
  const spreadReconcile =
    fairSpreadNum != null && displaySpread != null
      ? reconcileHandicapCustomerEdge({
          fairLine: fairSpreadNum,
          marketLine: displaySpread,
          claimedEdge: claimedSpread,
        })
      : null;
  if (spreadReconcile?.status === "DATA_GAP") {
    flags.push("spread_fair_market_edge_mismatch");
  }
  if (
    spreadReconcile?.status === "ok" &&
    spreadReconcile.side &&
    row.edgeLineFavor
  ) {
    const expected = shortTeamWord(
      spreadReconcile.side === "Home" ? row.teamB.name : row.teamA.name,
    );
    if (
      expected &&
      row.edgeLineFavor !== expected &&
      row.edgeLineFavor.toUpperCase() !==
        (spreadReconcile.side === "Home" ? homeAbbr : awayAbbr)
    ) {
      flags.push("spread_side_disagrees_favor");
    }
  }

  const spreadFail =
    flags.includes("spread_fair_market_edge_mismatch") ||
    flags.includes("spread_side_disagrees_favor");
  const spreadStatus = toPublishActionLabel(row.actionLabelLine ?? row.tagLine);
  let spreadInterp: MobileInterpretation | null = null;
  if (!isMlb && (spreadStatus || spreadReconcile?.status === "ok")) {
    const spreadAdv =
      !spreadFail &&
      spreadReconcile?.status === "ok" &&
      spreadReconcile.advantage != null &&
      spreadReconcile.advantage > 0
        ? spreadReconcile.advantage
        : null;
    const sideLabel =
      spreadAdv != null && spreadReconcile?.side
        ? spreadReconcile.side === "Home"
          ? homeAbbr
          : awayAbbr
        : null;
    const magnitude =
      spreadAdv != null ? formatSelectedSideLineEdge(spreadAdv, "pts") : null;
    if (spreadStatus || sideLabel || magnitude) {
      spreadInterp = {
        status: spreadStatus,
        sideLabel: spreadFail ? null : sideLabel,
        magnitude: spreadFail ? null : magnitude,
        subdued: spreadStatus === "PASS" || spreadStatus == null,
        failClosed: spreadFail,
      };
    }
  } else if (isMlb) {
    const spreadStatusMl = toPublishActionLabel(
      row.actionLabelLine ?? row.tagLine,
    );
    const sideLabel = row.edgeLineFavor
      ? presentationAbbr({
          sportKey: sport,
          nameFallback: row.edgeLineFavor,
        })
      : null;
    // MLB ML magnitude is already |modelHomeProb − marketNoVigHome| × 100 (pp).
    // formatSelectedSideProbEdge expects a 0–1 probability advantage.
    const storedMlPp =
      row.edgeMagnitudeLine != null || row.edgeLineNum != null
        ? Math.abs(row.edgeMagnitudeLine ?? row.edgeLineNum ?? 0)
        : null;
    const magnitude =
      storedMlPp != null ? formatSelectedSideProbEdge(storedMlPp / 100) : null;
    if (spreadStatusMl || sideLabel || magnitude) {
      spreadInterp = {
        status: spreadStatusMl,
        sideLabel,
        magnitude,
        subdued: spreadStatusMl === "PASS" || spreadStatusMl == null,
        failClosed: false,
      };
    }
  }

  const claimedTotal = row.edgeMagnitudeOU ?? row.edgeOUNum ?? undefined;
  const totalReconcile =
    fairTotalNum != null && displayTotal != null
      ? reconcileTotalCustomerEdge({
          fairTotal: fairTotalNum,
          marketTotal: displayTotal,
          claimedEdge: claimedTotal,
        })
      : null;
  if (totalReconcile?.status === "DATA_GAP") {
    flags.push("total_fair_market_edge_mismatch");
  }
  if (
    totalReconcile?.status === "ok" &&
    totalReconcile.side &&
    row.edgeOUFavor &&
    row.edgeOUFavor !== totalReconcile.side
  ) {
    flags.push("total_side_disagrees_favor");
  }
  const totalFail =
    flags.includes("total_fair_market_edge_mismatch") ||
    flags.includes("total_side_disagrees_favor");
  const totalStatus = toPublishActionLabel(row.actionLabelOU ?? row.tagOU);
  let totalInterp: MobileInterpretation | null = null;
  if (totalStatus || totalReconcile?.status === "ok") {
    const totalAdv =
      !totalFail &&
      totalReconcile?.status === "ok" &&
      totalReconcile.advantage != null &&
      totalReconcile.advantage > 0
        ? totalReconcile.advantage
        : null;
    const sideLabel =
      totalAdv != null && totalReconcile?.side ? totalReconcile.side : null;
    const magnitude =
      totalAdv != null ? formatSelectedSideLineEdge(totalAdv, "pts") : null;
    if (totalStatus || sideLabel || magnitude) {
      totalInterp = {
        status: totalStatus,
        sideLabel: totalFail ? null : sideLabel,
        magnitude: totalFail ? null : magnitude,
        subdued: totalStatus === "PASS" || totalStatus == null,
        failClosed: totalFail,
      };
    }
  }

  const openSpreadNum = isMlb
    ? null
    : (parseSignedLineLabel(row.openLine?.bottom.label) ??
      (parseSignedLineLabel(row.openLine?.top.label) != null
        ? -(parseSignedLineLabel(row.openLine?.top.label) as number)
        : null));
  const openSpread =
    openSpreadNum != null
      ? formatTeamLabeledSpread({
          homeSigned: openSpreadNum,
          homeAbbr,
          awayAbbr,
        })
      : null;
  const openTotalNum = parseTotalLabel(row.openOU?.top.label);
  const openTotal =
    openTotalNum != null ? formatOuLevel(openTotalNum).over : null;

  const modelBits: string[] = [];
  if (pairHasLine(row.modelLine)) {
    const home = parseSignedLineLabel(row.modelLine?.bottom.label);
    if (home != null) {
      modelBits.push(
        formatTeamLabeledSpread({
          homeSigned: home,
          homeAbbr,
          awayAbbr,
        }),
      );
    }
  }
  if (pairHasLine(row.modelOU)) {
    const tot = parseTotalLabel(row.modelOU?.top.label);
    if (tot != null) modelBits.push(formatOuLevel(tot).over);
  }

  return {
    matchup,
    kickoffDate: kick.date,
    kickoffTime: kick.time,
    kickoffTz: kick.local,
    venue,
    isMoneyline: isMlb,
    marketSpread,
    fairSpread,
    marketTotal,
    fairTotal,
    marketMlAway,
    marketMlHome,
    fairMlAway,
    fairMlHome,
    spreadInterp,
    totalInterp,
    confidence: formatCustomerConfidence({
      band: row.modelConfidenceBand,
      score: row.modelConfidenceScore,
      tierConstant: row.modelConfidenceTierConstant,
    }),
    openSpread,
    openTotal,
    linesAsOfLabel: formatLinesAsOf(row.linesAsOf ?? row.marketAsOf),
    linesStale: Boolean(row.linesStale),
    asOfUnavailable: isNfl && !row.linesAsOf,
    marketHorizonLabel: row.marketHorizonLabel ?? null,
    oddsWithoutKei: Boolean(row.oddsWithoutKei),
    overview: row.overview ?? null,
    modelNote: modelBits.length ? `Model ${modelBits.join(" / ")}` : null,
    sizeDown: Boolean(
      row.edgeOUCaution && totalStatus && totalStatus !== "PASS",
    ),
    truthFlags: flags,
  };
}

export function hasHeroMarket(model: MobileCardModel): boolean {
  if (model.isMoneyline) {
    return Boolean(model.marketMlAway || model.marketMlHome);
  }
  return Boolean(model.marketSpread || model.marketTotal);
}

export function hasHeroFair(model: MobileCardModel): boolean {
  if (model.isMoneyline) {
    return Boolean(model.fairMlAway || model.fairMlHome);
  }
  return Boolean(model.fairSpread || model.fairTotal);
}

export function hasMarketContext(model: MobileCardModel): boolean {
  return Boolean(
    model.openSpread ||
    model.openTotal ||
    model.linesAsOfLabel ||
    model.asOfUnavailable,
  );
}

export function hasInterpretation(model: MobileCardModel): boolean {
  return Boolean(model.spreadInterp || model.totalInterp);
}
