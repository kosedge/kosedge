/**
 * Shared matchup context for Edge Board overview + Stat Drop.
 * Prefer real inputs; omit when missing — never invent.
 */

import { NFL_STRUCTURAL_PACE_2026 } from "@/lib/nfl-structural-pace-2026";
import {
  NFL_STANDARD_HFA_POINTS,
  lookupNflNeutralSite,
  resolveNflSiteContext,
} from "@/lib/nfl-neutral-sites-2026";
import {
  resolveSeasonFormGate,
  type SeasonFormGate,
} from "@/lib/edge-board-season-gates";

export type MatchupPowerSource = "model_ew" | "kei_proxy";

export type EdgeBoardMatchupContext = {
  gameId: string;
  awayName: string;
  homeName: string;
  awayAbbr: string;
  homeAbbr: string;
  week: number | null;
  seasonType: string | null;
  gamesPlayedAway: number | null;
  gamesPlayedHome: number | null;
  seasonGate: SeasonFormGate;

  keiSpreadHome: number | null;
  marketSpreadHome: number | null;
  keiTotal: number | null;
  marketTotal: number | null;
  homeWinProb: number | null;
  awayWinProb: number | null;

  isNeutral: boolean;
  siteCity: string | null;
  siteVenue: string | null;
  hfaPoints: number;
  siteLabel: "Home" | "Road" | "Neutral";

  restDaysAway: number | null;
  restDaysHome: number | null;
  byeAway: boolean;
  byeHome: boolean;

  paceAway: number | null;
  paceHome: number | null;
  structuralTagAway: string | null;
  structuralTagHome: string | null;

  /** Model / launch power (expected wins when available). */
  modelPowerAway: number | null;
  modelPowerHome: number | null;
  /** KEI-relative power in points (always computable when KEI spread exists). */
  keiPowerAway: number | null;
  keiPowerHome: number | null;
  powerSource: MatchupPowerSource | null;

  publishTagSpread?: "PLAY" | "LEAN" | "PASS" | null;
  edgeSpreadAbs?: number | null;
};

function canonAbbr(abbr: string): string {
  const a = String(abbr || "")
    .trim()
    .toUpperCase();
  if (a === "LA") return "LAR";
  if (a === "WSH") return "WAS";
  return a;
}

function shortName(name: string): string {
  const parts = String(name || "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (parts.length === 0) return "—";
  if (parts.length === 1) return parts[0]!;
  return parts[parts.length - 1]!;
}

/** KEI-relative power points (home-positive), stripping HFA. */
export function keiRelativePower(args: {
  keiSpreadHome: number | null;
  hfaPoints: number;
}): { away: number; home: number } | null {
  if (args.keiSpreadHome == null || !Number.isFinite(args.keiSpreadHome)) {
    return null;
  }
  // Home favored when spread negative. Power gap excludes HFA already priced in.
  const homeMargin = -args.keiSpreadHome;
  const pureHomeEdge = homeMargin - args.hfaPoints;
  const home = Math.round(pureHomeEdge * 5) / 10; // half of gap each side
  const away = Math.round(-pureHomeEdge * 5) / 10;
  return { away, home };
}

export function structuralPaceFor(abbr: string): {
  pace: number | null;
  tag: string | null;
} {
  const row = NFL_STRUCTURAL_PACE_2026[canonAbbr(abbr)];
  if (!row) return { pace: null, tag: null };
  return { pace: row.pace, tag: row.tag };
}

export type BuildMatchupContextInput = {
  gameId?: string | null;
  awayName: string;
  homeName: string;
  awayAbbr?: string | null;
  homeAbbr?: string | null;
  week?: number | null;
  seasonType?: string | null;
  gamesPlayedAway?: number | null;
  gamesPlayedHome?: number | null;
  keiSpreadHome?: number | null;
  marketSpreadHome?: number | null;
  keiTotal?: number | null;
  marketTotal?: number | null;
  homeWinProb?: number | null;
  awayWinProb?: number | null;
  restDaysAway?: number | null;
  restDaysHome?: number | null;
  byeAway?: boolean | null;
  byeHome?: boolean | null;
  modelPowerAway?: number | null;
  modelPowerHome?: number | null;
  neutralSite?: boolean | null;
  neutralCity?: string | null;
  neutralVenue?: string | null;
  hfaPoints?: number | null;
  publishTagSpread?: "PLAY" | "LEAN" | "PASS" | null;
  edgeSpreadAbs?: number | null;
};

export function buildMatchupContext(
  input: BuildMatchupContextInput,
): EdgeBoardMatchupContext {
  const awayAbbr = canonAbbr(input.awayAbbr || shortName(input.awayName));
  const homeAbbr = canonAbbr(input.homeAbbr || shortName(input.homeName));

  // Week 1 ⇒ 0 prior games when not supplied. Coerce string weeks from JSON/RSC.
  const weekRaw =
    input.week != null && input.week !== ("" as unknown)
      ? Number(input.week)
      : NaN;
  let week = Number.isFinite(weekRaw) ? Math.trunc(weekRaw) : null;

  const site = resolveNflSiteContext({
    week,
    homeAbbr,
    awayAbbr,
    neutralSite: input.neutralSite,
    neutralCity: input.neutralCity,
    neutralVenue: input.neutralVenue,
    hfaPoints: input.hfaPoints,
  });
  // If week was missing but this pair is a known 2026 international game, adopt that week.
  if (week == null && site.isNeutral) {
    const looked = lookupNflNeutralSite({ week: null, homeAbbr, awayAbbr });
    if (looked?.week != null) week = looked.week;
  }

  const awayStruct = structuralPaceFor(awayAbbr);
  const homeStruct = structuralPaceFor(homeAbbr);
  const keiPow = keiRelativePower({
    keiSpreadHome: input.keiSpreadHome ?? null,
    hfaPoints: site.hfaPoints,
  });
  const hasModel =
    input.modelPowerAway != null &&
    input.modelPowerHome != null &&
    Number.isFinite(input.modelPowerAway) &&
    Number.isFinite(input.modelPowerHome);

  const gameId =
    String(input.gameId || "").trim() ||
    `${awayAbbr}@${homeAbbr}-w${week ?? "?"}`;
  let gamesPlayedAway =
    input.gamesPlayedAway != null && Number.isFinite(Number(input.gamesPlayedAway))
      ? Math.max(0, Math.trunc(Number(input.gamesPlayedAway)))
      : null;
  let gamesPlayedHome =
    input.gamesPlayedHome != null && Number.isFinite(Number(input.gamesPlayedHome))
      ? Math.max(0, Math.trunc(Number(input.gamesPlayedHome)))
      : null;
  if (week === 1) {
    if (gamesPlayedAway == null) gamesPlayedAway = 0;
    if (gamesPlayedHome == null) gamesPlayedHome = 0;
  }

  return {
    gameId,
    awayName: input.awayName,
    homeName: input.homeName,
    awayAbbr,
    homeAbbr,
    week,
    seasonType: input.seasonType ?? null,
    gamesPlayedAway,
    gamesPlayedHome,
    seasonGate: resolveSeasonFormGate({
      week,
      gamesPlayedAway,
      gamesPlayedHome,
      seasonType: input.seasonType,
    }),
    keiSpreadHome: input.keiSpreadHome ?? null,
    marketSpreadHome: input.marketSpreadHome ?? null,
    keiTotal: input.keiTotal ?? null,
    marketTotal: input.marketTotal ?? null,
    homeWinProb: input.homeWinProb ?? null,
    awayWinProb: input.awayWinProb ?? null,
    isNeutral: site.isNeutral,
    siteCity: site.city,
    siteVenue: site.venue,
    hfaPoints: site.hfaPoints,
    siteLabel: site.siteLabel,
    restDaysAway: input.restDaysAway ?? null,
    restDaysHome: input.restDaysHome ?? null,
    byeAway: Boolean(input.byeAway),
    byeHome: Boolean(input.byeHome),
    paceAway: awayStruct.pace,
    paceHome: homeStruct.pace,
    structuralTagAway: awayStruct.tag,
    structuralTagHome: homeStruct.tag,
    modelPowerAway: hasModel ? Number(input.modelPowerAway) : null,
    modelPowerHome: hasModel ? Number(input.modelPowerHome) : null,
    keiPowerAway: keiPow?.away ?? null,
    keiPowerHome: keiPow?.home ?? null,
    powerSource: hasModel ? "model_ew" : keiPow ? "kei_proxy" : null,
    publishTagSpread: input.publishTagSpread ?? null,
    edgeSpreadAbs: input.edgeSpreadAbs ?? null,
  };
}

export function shortTeam(ctx: EdgeBoardMatchupContext, side: "away" | "home"): string {
  return shortName(side === "away" ? ctx.awayName : ctx.homeName);
}

export { NFL_STANDARD_HFA_POINTS };
