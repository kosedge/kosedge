/**
 * Attach matchup overview / Stat Drop context fields onto NFL Edge Board rows.
 * Pure where possible; power map is optional (assemble can load launch E[wins]).
 */

import type { EdgeBoardRow } from "@kosedge/contracts";
import { buildMatchupContext } from "@/lib/edge-board-matchup-context";
import { buildMatchupOverview } from "@/lib/edge-board-matchup-overview";
import { buildStatDrop } from "@/lib/edge-board-stat-drop";
import { NFL_TEAM_DIRECTORY } from "@/lib/nfl-team-intel";
import { resolveNflSiteContext } from "@/lib/nfl-neutral-sites-2026";
import { structuralPaceFor } from "@/lib/edge-board-matchup-context";

export type MatchupPowerMap = Map<string, number>;

const NAME_TO_ABBR = new Map(
  NFL_TEAM_DIRECTORY.map((t) => [t.name.toLowerCase(), t.code] as const),
);
const ABBR_SET = new Set(NFL_TEAM_DIRECTORY.map((t) => t.code));

function canonAbbr(raw: string): string {
  const a = String(raw || "")
    .trim()
    .toUpperCase();
  if (a === "LA") return "LAR";
  if (a === "WSH") return "WAS";
  return a;
}

function abbrFromLabel(label: string): string {
  const raw = String(label || "").trim();
  if (!raw) return "";
  const asAbbr = canonAbbr(raw);
  if (ABBR_SET.has(asAbbr) || asAbbr === "LAR") return asAbbr === "LA" ? "LAR" : asAbbr;
  const byName = NAME_TO_ABBR.get(raw.toLowerCase());
  if (byName) return canonAbbr(byName);
  const words = raw.split(/\s+/);
  const last = words[words.length - 1] || "";
  const nick = NAME_TO_ABBR.get(raw.toLowerCase());
  if (nick) return canonAbbr(nick);
  // Last-word nicknames: "Patriots" etc.
  for (const t of NFL_TEAM_DIRECTORY) {
    const nickWord = t.name.split(/\s+/).pop()?.toLowerCase();
    if (nickWord && nickWord === last.toLowerCase()) return canonAbbr(t.code);
  }
  return asAbbr;
}

function parseGameTeams(game: string): { away: string; home: string } {
  const parts = game.includes(" @ ")
    ? game.split(" @ ")
    : game.split(" vs ");
  return {
    away: (parts[0] ?? "Away").trim() || "Away",
    home: (parts[1] ?? "Home").trim() || "Home",
  };
}

function parseSigned(raw: unknown): number | null {
  if (raw == null) return null;
  const n = parseFloat(String(raw).replace(/[^+\-\d.]/g, ""));
  return Number.isFinite(n) ? n : null;
}

function parseTotal(raw: unknown): number | null {
  if (raw == null) return null;
  const n = parseFloat(String(raw).replace(/[^\d.]/g, ""));
  return Number.isFinite(n) ? n : null;
}

type RowExtra = EdgeBoardRow & {
  week?: number;
  seasonType?: string;
  homeWinProb?: number;
  awayWinProb?: number;
  homeAbbr?: string;
  awayAbbr?: string;
  keiSpreadHome?: number;
  marketSpreadHome?: number;
  keiTotal?: number;
  marketTotal?: number;
  modelPowerAway?: number;
  modelPowerHome?: number;
  restDaysAway?: number;
  restDaysHome?: number;
  byeAway?: boolean;
  byeHome?: boolean;
  gamesPlayedAway?: number;
  gamesPlayedHome?: number;
  neutralSite?: boolean;
  neutralCity?: string;
  neutralVenue?: string;
  hfaPoints?: number;
  structuralTagAway?: string;
  structuralTagHome?: string;
  paceAway?: number;
  paceHome?: number;
  matchupOverview?: string;
  matchupVoice?: string;
  statDrop?: ReturnType<typeof buildStatDrop>;
  publishTag?: "PLAY" | "LEAN" | "PASS";
};

/**
 * Enrich every NFL edge-board row with site / power / pace / overview / Stat Drop.
 * Safe to call multiple times (idempotent overwrite).
 */
export function enrichNflEdgeBoardMatchupFields(
  rows: EdgeBoardRow[],
  options?: { powerByAbbr?: MatchupPowerMap | null },
): EdgeBoardRow[] {
  if (!rows.length) return rows;
  const power = options?.powerByAbbr ?? null;

  // Group by game so spread+total share one context.
  const byGame = new Map<string, RowExtra[]>();
  for (const row of rows) {
    const game = String(row.game ?? "").trim() || "unknown";
    const list = byGame.get(game) ?? [];
    list.push(row as RowExtra);
    byGame.set(game, list);
  }

  for (const [game, group] of byGame) {
    const { away, home } = parseGameTeams(game);
    const spread = group.find((r) => r.market === "Spread") ?? group[0]!;
    const total = group.find((r) => r.market === "Total");
    const weekRaw = spread.week ?? total?.week ?? null;
    const week =
      weekRaw == null || weekRaw === ("" as unknown)
        ? null
        : Number.isFinite(Number(weekRaw))
          ? Math.trunc(Number(weekRaw))
          : null;
    const awayAbbr = canonAbbr(
      spread.awayAbbr || abbrFromLabel(away),
    );
    const homeAbbr = canonAbbr(
      spread.homeAbbr || abbrFromLabel(home),
    );

    // KEI spread on board is home-side in fair-lines assembly.
    const keiSpreadHome =
      spread.keiSpreadHome ??
      (spread.market === "Spread" ? parseSigned(spread.kei) : null);
    const marketSpreadHome =
      spread.marketSpreadHome ??
      (spread.market === "Spread" && spread.best
        ? (() => {
            const awaySpread = parseSigned(spread.best);
            return awaySpread != null ? -awaySpread : null;
          })()
        : null);
    const keiTotal =
      total?.keiTotal ??
      (total ? parseTotal(total.kei) : null) ??
      (spread.keiTotal ?? null);
    const marketTotal =
      total?.marketTotal ??
      (total?.best ? parseTotal(total.best) : null);

    const site = resolveNflSiteContext({
      week,
      homeAbbr,
      awayAbbr,
      neutralSite: spread.neutralSite,
      neutralCity: spread.neutralCity,
      neutralVenue: spread.neutralVenue,
      hfaPoints: spread.hfaPoints,
    });
    const awayStruct = structuralPaceFor(awayAbbr);
    const homeStruct = structuralPaceFor(homeAbbr);

    const modelPowerAway = power?.get(awayAbbr) ?? spread.modelPowerAway ?? null;
    const modelPowerHome = power?.get(homeAbbr) ?? spread.modelPowerHome ?? null;

    const edgeSpreadAbs =
      keiSpreadHome != null && marketSpreadHome != null
        ? Math.abs(keiSpreadHome - marketSpreadHome)
        : null;

    const ctx = buildMatchupContext({
      gameId: String(spread.id || `${awayAbbr}@${homeAbbr}-w${week ?? "?"}`).replace(
        /-spread$|-total$/,
        "",
      ),
      awayName: away,
      homeName: home,
      awayAbbr,
      homeAbbr,
      week,
      seasonType: spread.seasonType ?? total?.seasonType ?? null,
      gamesPlayedAway: spread.gamesPlayedAway ?? null,
      gamesPlayedHome: spread.gamesPlayedHome ?? null,
      keiSpreadHome,
      marketSpreadHome,
      keiTotal,
      marketTotal,
      homeWinProb: spread.homeWinProb ?? null,
      awayWinProb: spread.awayWinProb ?? null,
      restDaysAway: spread.restDaysAway ?? null,
      restDaysHome: spread.restDaysHome ?? null,
      byeAway: spread.byeAway ?? false,
      byeHome: spread.byeHome ?? false,
      modelPowerAway,
      modelPowerHome,
      neutralSite: site.isNeutral,
      neutralCity: site.city,
      neutralVenue: site.venue,
      hfaPoints: site.hfaPoints,
      publishTagSpread: spread.publishTag ?? null,
      edgeSpreadAbs,
    });

    const overview = buildMatchupOverview(ctx);
    const drop = buildStatDrop(ctx);

    for (const row of group) {
      row.awayAbbr = awayAbbr;
      row.homeAbbr = homeAbbr;
      row.keiSpreadHome = keiSpreadHome ?? undefined;
      row.marketSpreadHome = marketSpreadHome ?? undefined;
      row.keiTotal = keiTotal ?? undefined;
      row.marketTotal = marketTotal ?? undefined;
      row.neutralSite = ctx.isNeutral;
      row.neutralCity = ctx.siteCity ?? undefined;
      row.neutralVenue = ctx.siteVenue ?? undefined;
      row.hfaPoints = ctx.hfaPoints;
      row.paceAway = awayStruct.pace ?? undefined;
      row.paceHome = homeStruct.pace ?? undefined;
      row.structuralTagAway = awayStruct.tag ?? undefined;
      row.structuralTagHome = homeStruct.tag ?? undefined;
      row.modelPowerAway = ctx.modelPowerAway ?? undefined;
      row.modelPowerHome = ctx.modelPowerHome ?? undefined;
      row.matchupOverview = overview.text;
      row.matchupVoice = overview.voice;
      row.statDrop = drop;
      if (ctx.homeWinProb != null) row.homeWinProb = ctx.homeWinProb;
      if (ctx.awayWinProb != null) row.awayWinProb = ctx.awayWinProb;
    }
  }

  return rows;
}
