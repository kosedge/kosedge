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
  publishTagSpread: "PLAY" | "LEAN" | "PASS" | null;
  publishTagTotal: "PLAY" | "LEAN" | "PASS" | null;
  spreadEdge: number | null;
  totalEdge: number | null;
  bestSpreadBook: string | null;
  bestTotalBook: string | null;
  matchupHref: string;
  previewAwayHref: string;
  previewHomeHref: string;
  source: "fair-lines" | "espn";
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
    marketJoinedCount: number;
    oddsFeedStatus: string;
  };
};

function tagNote(row: Pick<NflFairLineRow, "publishTagSpread" | "publishTagTotal" | "seasonType">): string {
  if ((row.seasonType ?? "").toUpperCase() === "PRE") {
    return "Preseason — informational only; season PLAY tags stay blocked.";
  }
  const tags = [row.publishTagSpread, row.publishTagTotal].filter(Boolean);
  if (tags.includes("PLAY")) return "Publish desk: PLAY threshold cleared.";
  if (tags.includes("LEAN")) return "Publish desk: LEAN — monitor juice and key numbers.";
  if (tags.includes("PASS")) return "Publish desk: PASS — model vs market separation is thin.";
  return "Model reference loaded for matchup prep.";
}

function fairLineToCard(row: NflFairLineRow): NflSlateCard {
  const seasonType = ((row.seasonType ?? "REG").toUpperCase() || "REG") as
    | "PRE"
    | "REG"
    | "POST";
  const dateToken = (row.gameDate || row.startTime || "today").slice(0, 10);
  const slug = `${row.awayAbbr}-${row.homeAbbr}`.toLowerCase();
  return {
    id: row.gameId || `${seasonType}-${row.week}-${slug}`,
    seasonType,
    week: row.week,
    startTime: row.startTime,
    kickoffLabel: formatKickoff(row.startTime),
    awayAbbr: row.awayAbbr,
    homeAbbr: row.homeAbbr,
    awayTeam: row.awayTeam,
    homeTeam: row.homeTeam,
    marketSpread: formatSpread(
      row.bestSpreadHome ?? row.marketSpreadHome,
    ),
    modelSpread: formatSpread(row.spreadHome),
    marketTotal: formatTotal(row.bestTotal ?? row.marketTotal),
    modelTotal: formatTotal(row.totalMean),
    publishTagSpread: row.publishTagSpread,
    publishTagTotal: row.publishTagTotal,
    spreadEdge: row.spreadEdge,
    totalEdge: row.totalEdge,
    bestSpreadBook: row.bestSpreadBook,
    bestTotalBook: row.bestTotalBook,
    matchupHref: `/pro/nfl/matchups/${dateToken}/${slug}`,
    previewAwayHref: `/pro/nfl/previews/${row.awayAbbr}`,
    previewHomeHref: `/pro/nfl/previews/${row.homeAbbr}`,
    source: "fair-lines",
    note: tagNote(row),
  };
}

function espnToCard(game: EspnNflGame): NflSlateCard {
  const dateToken = (game.startTime || "today").slice(0, 10);
  const slug = `${game.awayAbbr}-${game.homeAbbr}`.toLowerCase();
  return {
    id: game.id,
    seasonType: game.seasonType,
    week: game.week,
    startTime: game.startTime,
    kickoffLabel: formatKickoff(game.startTime || null),
    awayAbbr: game.awayAbbr,
    homeAbbr: game.homeAbbr,
    awayTeam: game.awayTeam,
    homeTeam: game.homeTeam,
    marketSpread: formatSpread(game.marketSpreadHome),
    modelSpread: "—",
    marketTotal: formatTotal(game.marketTotal),
    modelTotal: "—",
    publishTagSpread: null,
    publishTagTotal: null,
    spreadEdge: null,
    totalEdge: null,
    bestSpreadBook: game.marketDetail ? "ESPN consensus" : null,
    bestTotalBook: game.marketTotal != null ? "ESPN consensus" : null,
    matchupHref: `/pro/nfl/matchups/${dateToken}/${slug}`,
    previewAwayHref: `/pro/nfl/previews/${game.awayAbbr}`,
    previewHomeHref: `/pro/nfl/previews/${game.homeAbbr}`,
    source: "espn",
    note:
      "Preseason board from ESPN schedule. Kos Edge fair-lines attach when sims cover PRE games.",
  };
}

function resolveDateToken(date: string): {
  mode: "today" | "week" | "iso";
  week?: number;
  iso?: string;
} {
  const token = date.trim().toLowerCase();
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

  const [fairLines, preseasonGames] = await Promise.all([
    fetchNflFairLines({
      season,
      daysAhead: 120,
      includePastDays: 2,
    }),
    fetchEspnPreseasonSlate({ year: season, weeks: [1, 2, 3, 4] }),
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
    .map(espnToCard);

  // Prefer PRE week 1–2 as the immediate board before kickoff of REG.
  const preCards =
    resolved.mode === "week" && resolved.week
      ? upcomingPre.filter((card) => card.week === resolved.week)
      : upcomingPre.filter((card) => (card.week ?? 99) <= 2);

  const sections: NflWeeklySlate["sections"] = [];
  if (preCards.length > 0) {
    sections.push({
      key: "preseason",
      title: "Preseason board",
      subtitle:
        "Hall of Fame / Weeks 1–2 from the league schedule. Market numbers when ESPN posts consensus; model fair-lines join as PRE sims publish.",
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
      marketJoinedCount: fairLines.diagnostics.marketJoinedCount,
      oddsFeedStatus: fairLines.diagnostics.oddsFeedStatus,
    },
  };
}
