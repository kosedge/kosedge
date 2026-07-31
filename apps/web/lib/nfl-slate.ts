import "server-only";
import {
  fetchNflFairLines,
  formatKickoff,
  formatSpread,
  formatTotal,
  type NflFairLineRow,
} from "@/lib/nfl-fair-lines";
import {
  fetchEspnPreseasonSlate,
  type EspnNflGame,
} from "@/lib/nfl-espn-schedule";
import {
  campReferenceContextNote,
  campReferenceSpreadHome,
  loadPreseasonStrengthMap,
} from "@/lib/nfl-preseason-desk";
import {
  fetchNflPreseasonOddsMarkets,
  type NflPreseasonMarketSnap,
} from "@/lib/nfl-preseason-odds";
import { safeUpperCase } from "@/lib/sports";

export type NflSlateCard = {
  id: string;
  seasonType: "PRE" | "REG" | "POST";
  week: number | null;
  startTime: string | null;
  kickoffLabel: string;
  awayAbbr: string;
  homeAbbr: string;
  awayTeam: string;
  homeTeam: string;
  marketSpread: string;
  modelSpread: string;
  marketTotal: string;
  modelTotal: string;
  /** UI label for the model/reference column (e.g. Model vs Camp ref). */
  referenceLabel: "Model" | "Camp ref";
  publishTagSpread: "PLAY" | "LEAN" | "PASS" | null;
  publishTagTotal: "PLAY" | "LEAN" | "PASS" | null;
  spreadEdge: number | null;
  totalEdge: number | null;
  bestSpreadBook: string | null;
  bestTotalBook: string | null;
  matchupHref: string;
  previewAwayHref: string;
  previewHomeHref: string;
  source: "fair-lines" | "espn" | "camp-ref";
  note: string;
};

export type NflWeeklySlate = {
  season: number;
  currentWeek: number;
  generatedAt: string;
  modelVersion: string;
  error?: string;
  sections: Array<{
    key: string;
    title: string;
    subtitle: string;
    cards: NflSlateCard[];
  }>;
  diagnostics: {
    fairLineCount: number;
    preseasonCount: number;
    campRefJoinedCount: number;
    preseasonOddsStatus: string;
    preseasonOddsJoinedCount: number;
    marketJoinedCount: number;
    oddsFeedStatus: string;
    campBundle: string | null;
  };
};

function tagNote(row: Pick<NflFairLineRow, "publishTagSpread" | "publishTagTotal" | "seasonType">): string {
  if (safeUpperCase(row.seasonType) === "PRE") {
    return "Preseason — informational only; season PLAY tags stay blocked.";
  }
  const tags = [row.publishTagSpread, row.publishTagTotal].filter(Boolean);
  if (tags.includes("PLAY")) return "Publish desk: PLAY threshold cleared.";
  if (tags.includes("LEAN")) return "Publish desk: LEAN — monitor juice and key numbers.";
  if (tags.includes("PASS")) return "Publish desk: PASS — model vs market separation is thin.";
  return "Model reference loaded for matchup prep.";
}

function fairLineToCard(row: NflFairLineRow): NflSlateCard {
  const seasonType = (safeUpperCase(row.seasonType, "REG") || "REG") as
    | "PRE"
    | "REG"
    | "POST";
  const dateToken = (row.gameDate || row.startTime || "today").slice(0, 10);
  const awayAbbr = safeUpperCase(row.awayAbbr, "AWAY");
  const homeAbbr = safeUpperCase(row.homeAbbr, "HOME");
  const slug = `${awayAbbr}-${homeAbbr}`.toLowerCase();
  return {
    id: row.gameId || `${seasonType}-${row.week}-${slug}`,
    seasonType,
    week: row.week,
    startTime: row.startTime,
    kickoffLabel: formatKickoff(row.startTime),
    awayAbbr,
    homeAbbr,
    awayTeam: row.awayTeam || awayAbbr,
    homeTeam: row.homeTeam || homeAbbr,
    marketSpread: formatSpread(
      row.bestSpreadHome ?? row.marketSpreadHome,
    ),
    modelSpread: formatSpread(row.spreadHome),
    marketTotal: formatTotal(row.bestTotal ?? row.marketTotal),
    modelTotal: formatTotal(row.totalMean),
    referenceLabel: "Model",
    publishTagSpread: row.publishTagSpread,
    publishTagTotal: row.publishTagTotal,
    spreadEdge: row.spreadEdge,
    totalEdge: row.totalEdge,
    bestSpreadBook: row.bestSpreadBook,
    bestTotalBook: row.bestTotalBook,
    matchupHref: `/pro/nfl/matchups/${dateToken}/${slug}`,
    previewAwayHref: `/pro/nfl/previews/${awayAbbr}`,
    previewHomeHref: `/pro/nfl/previews/${homeAbbr}`,
    source: "fair-lines",
    note: tagNote(row),
  };
}

function espnToCard(
  game: EspnNflGame,
  strength: ReturnType<typeof loadPreseasonStrengthMap>,
  oddsSnap?: NflPreseasonMarketSnap | null,
): NflSlateCard {
  const dateToken = (game.startTime || "today").slice(0, 10);
  const awayAbbr = safeUpperCase(game.awayAbbr, "AWAY");
  const homeAbbr = safeUpperCase(game.homeAbbr, "HOME");
  const slug = `${awayAbbr}-${homeAbbr}`.toLowerCase();
  const campSpread = campReferenceSpreadHome(
    homeAbbr,
    awayAbbr,
    strength,
  );
  const marketSpreadNum =
    oddsSnap?.bestSpreadHome ??
    oddsSnap?.marketSpreadHome ??
    game.marketSpreadHome;
  const marketTotalNum =
    oddsSnap?.bestTotal ?? oddsSnap?.marketTotal ?? game.marketTotal;
  const hasMarket = marketSpreadNum != null || marketTotalNum != null;
  const hasCampRef = campSpread != null;
  const spreadEdge =
    hasCampRef && marketSpreadNum != null
      ? Math.round((campSpread! - marketSpreadNum) * 100) / 100
      : null;
  const marketBookLabel = oddsSnap
    ? oddsSnap.bestSpreadBook ?? "Odds API PRE"
    : game.marketDetail
      ? "ESPN consensus"
      : null;

  return {
    id: game.id,
    seasonType: game.seasonType,
    week: game.week,
    startTime: game.startTime,
    kickoffLabel: formatKickoff(game.startTime || null),
    awayAbbr,
    homeAbbr,
    awayTeam: game.awayTeam || awayAbbr,
    homeTeam: game.homeTeam || homeAbbr,
    marketSpread: formatSpread(marketSpreadNum),
    modelSpread: formatSpread(campSpread),
    marketTotal: formatTotal(marketTotalNum),
    // Honest: do not invent PRE totals from REG sims.
    modelTotal: "—",
    referenceLabel: "Camp ref",
    publishTagSpread: null,
    publishTagTotal: null,
    spreadEdge,
    totalEdge: null,
    bestSpreadBook: marketBookLabel,
    bestTotalBook: oddsSnap
      ? oddsSnap.bestTotalBook ?? marketBookLabel
      : marketTotalNum != null
        ? "ESPN consensus"
        : null,
    matchupHref: `/pro/nfl/matchups/${dateToken}/${slug}`,
    previewAwayHref: `/pro/nfl/previews/${awayAbbr}`,
    previewHomeHref: `/pro/nfl/previews/${homeAbbr}`,
    source: hasCampRef ? "camp-ref" : "espn",
    note: campReferenceContextNote({
      hasMarket,
      hasCampRef,
      bundleDirName: strength?.bundleDirName,
    }),
  };
}

function resolveDateToken(date: string | null | undefined): {
  mode: "today" | "week" | "iso";
  week?: number;
  iso?: string;
} {
  const token = String(date ?? "")
    .trim()
    .toLowerCase();
  if (!token || token === "today" || token === "latest") {
    return { mode: "today" };
  }
  const weekMatch = token.match(/^w(?:eek)?-?(\d+)$/);
  if (weekMatch) return { mode: "week", week: Number(weekMatch[1]) };
  if (/^\d{4}-\d{2}-\d{2}$/.test(token)) return { mode: "iso", iso: token };
  return { mode: "today" };
}

export async function buildNflWeeklySlate(
  dateToken = "today",
): Promise<NflWeeklySlate> {
  const season = 2026;
  const resolved = resolveDateToken(dateToken);
  const strength = loadPreseasonStrengthMap();

  const [fairLines, preseasonGames, preseasonOdds] = await Promise.all([
    fetchNflFairLines({
      season,
      daysAhead: 120,
      includePastDays: 2,
    }),
    fetchEspnPreseasonSlate({ year: season, weeks: [1, 2, 3, 4] }),
    fetchNflPreseasonOddsMarkets(),
  ]);

  const fairCards = fairLines.lines.map(fairLineToCard);
  const currentWeek = fairLines.currentWeek || 1;

  let regCards = fairCards.filter((card) => card.seasonType === "REG");
  if (resolved.mode === "week" && resolved.week) {
    regCards = regCards.filter((card) => card.week === resolved.week);
  } else if (resolved.mode === "iso" && resolved.iso) {
    regCards = regCards.filter((card) =>
      (card.startTime || "").startsWith(resolved.iso!),
    );
  } else {
    // Default "today" board: current REG week + next week for depth.
    regCards = regCards.filter(
      (card) =>
        card.week === currentWeek ||
        card.week === currentWeek + 1,
    );
  }

  const now = Date.now();
  const upcomingPre = preseasonGames
    .filter((game) => {
      if (!game.startTime) return true;
      const ts = Date.parse(game.startTime);
      return Number.isFinite(ts) ? ts >= now - 6 * 3600_000 : true;
    })
    .map((game) => {
      const oddsSnap =
        preseasonOdds.byMatchup.get(`${game.awayAbbr}@${game.homeAbbr}`) ??
        null;
      return espnToCard(game, strength, oddsSnap);
    });

  // Prefer PRE week 1–2 as the immediate board before kickoff of REG.
  const preCards =
    resolved.mode === "week" && resolved.week
      ? upcomingPre.filter((card) => card.week === resolved.week)
      : upcomingPre.filter((card) => (card.week ?? 99) <= 2);

  const campRefJoinedCount = preCards.filter(
    (card) => card.source === "camp-ref",
  ).length;
  const preseasonOddsJoinedCount = preCards.filter((card) =>
    Boolean(
      preseasonOdds.byMatchup.get(`${card.awayAbbr}@${card.homeAbbr}`),
    ),
  ).length;

  const sections: NflWeeklySlate["sections"] = [];
  if (preCards.length > 0) {
    sections.push({
      key: "preseason",
      title: "Preseason board",
      subtitle:
        "Hall of Fame / Weeks 1–2 — book/ESPN market when posted, plus camp strength reference from REG expected-wins. Not a PRE-game sim; season PLAY tags stay blocked.",
      cards: preCards,
    });
  }
  if (regCards.length > 0) {
    sections.push({
      key: "regular",
      title:
        resolved.mode === "week"
          ? `Regular season · Week ${resolved.week}`
          : `Regular season · Weeks ${currentWeek}–${currentWeek + 1}`,
      subtitle:
        "Kos Edge fair-lines with live market join, publish tags, and best-book context.",
      cards: regCards.sort((a, b) =>
        (a.startTime || "").localeCompare(b.startTime || ""),
      ),
    });
  }

  return {
    season,
    currentWeek,
    generatedAt: new Date().toISOString(),
    modelVersion: fairLines.modelVersion,
    error: fairLines.error,
    sections,
    diagnostics: {
      fairLineCount: fairLines.count,
      preseasonCount: preCards.length,
      campRefJoinedCount,
      preseasonOddsStatus: preseasonOdds.status,
      preseasonOddsJoinedCount,
      marketJoinedCount: fairLines.diagnostics.marketJoinedCount,
      oddsFeedStatus: fairLines.diagnostics.oddsFeedStatus,
      campBundle: strength?.bundleDirName ?? null,
    },
  };
}
