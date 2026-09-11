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
import { formatNflBoardWeekLabel } from "@/lib/nfl-board-week-label";
import {
  currentNflRegWeekFromSchedule,
  lookupCanonicalNflGame,
} from "@/lib/nfl-canonical-schedule";
import { listNflRegWeekScheduleGames } from "@/lib/nfl-edge-board-week";
import { teamDisplayName } from "@/lib/nfl-team-intel";
import { MODEL_DATA_UNAVAILABLE_COPY } from "@/lib/model-service-status";

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
  source: "fair-lines" | "espn" | "camp-ref" | "schedule";
  note: string;
};

export type NflWeeklySlate = {
  season: number;
  currentWeek: number;
  generatedAt: string;
  modelVersion: string;
  error?: string;
  /** True when schedule/market cards rendered without a bound model run. */
  modelUnavailable?: boolean;
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

function tagNote(
  row: Pick<
    NflFairLineRow,
    "publishTagSpread" | "publishTagTotal" | "seasonType"
  >,
): string {
  if (safeUpperCase(row.seasonType) === "PRE") {
    return "Preseason — informational only; season PLAY tags stay blocked.";
  }
  const tags = [row.publishTagSpread, row.publishTagTotal].filter(Boolean);
  if (tags.includes("PLAY")) return "Publish desk: PLAY threshold cleared.";
  if (tags.includes("LEAN"))
    return "Publish desk: LEAN — monitor juice and key numbers.";
  if (tags.includes("PASS"))
    return "Publish desk: PASS — model vs market separation is thin.";
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
    marketSpread: formatSpread(row.bestSpreadHome ?? row.marketSpreadHome),
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
  const campSpread = campReferenceSpreadHome(homeAbbr, awayAbbr, strength);
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
    ? (oddsSnap.bestSpreadBook ?? "Odds API PRE")
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
      ? (oddsSnap.bestTotalBook ?? marketBookLabel)
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

/** Schedule-only REG card. Model fields stay em-dash — never invent KEI/tags. */
export function scheduleGameToSlateCard(args: {
  week: number;
  awayAbbr: string;
  homeAbbr: string;
  gameId?: string;
  season?: number;
}): NflSlateCard {
  const season = args.season ?? 2026;
  const awayAbbr = safeUpperCase(args.awayAbbr, "AWAY");
  const homeAbbr = safeUpperCase(args.homeAbbr, "HOME");
  const packed = lookupCanonicalNflGame({
    gameId: args.gameId,
    season,
    week: args.week,
    awayAbbr,
    homeAbbr,
  });
  const startTime = packed?.kickoff_utc ?? null;
  const dateToken = (startTime || "today").slice(0, 10);
  const slug = `${awayAbbr}-${homeAbbr}`.toLowerCase();
  const gameId =
    args.gameId ||
    packed?.game_id ||
    `${season}-W${String(args.week).padStart(2, "0")}-${awayAbbr}@${homeAbbr}`;
  return {
    id: gameId,
    seasonType: "REG",
    week: args.week,
    startTime,
    kickoffLabel: formatKickoff(startTime),
    awayAbbr,
    homeAbbr,
    awayTeam: teamDisplayName(awayAbbr),
    homeTeam: teamDisplayName(homeAbbr),
    marketSpread: "—",
    modelSpread: "—",
    marketTotal: "—",
    modelTotal: "—",
    referenceLabel: "Model",
    publishTagSpread: null,
    publishTagTotal: null,
    spreadEdge: null,
    totalEdge: null,
    bestSpreadBook: null,
    bestTotalBook: null,
    matchupHref: `/pro/nfl/matchups/${dateToken}/${slug}`,
    previewAwayHref: `/pro/nfl/previews/${awayAbbr}`,
    previewHomeHref: `/pro/nfl/previews/${homeAbbr}`,
    source: "schedule",
    note: MODEL_DATA_UNAVAILABLE_COPY,
  };
}

export function buildRegCardsFromSchedule(
  weeks: number[],
  season = 2026,
): NflSlateCard[] {
  const seen = new Set<string>();
  const cards: NflSlateCard[] = [];
  for (const week of weeks) {
    if (!Number.isFinite(week) || week < 1) continue;
    for (const game of listNflRegWeekScheduleGames(week, season)) {
      const key = `${game.week}|${game.awayAbbr}|${game.homeAbbr}`;
      if (seen.has(key)) continue;
      seen.add(key);
      cards.push(
        scheduleGameToSlateCard({
          week: game.week,
          awayAbbr: game.awayAbbr,
          homeAbbr: game.homeAbbr,
          gameId: game.gameId,
          season: game.season,
        }),
      );
    }
  }
  return cards;
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
  const scheduleWeek = currentNflRegWeekFromSchedule();
  const currentWeek =
    fairLines.lines.length > 0 && Number.isFinite(fairLines.currentWeek)
      ? fairLines.currentWeek
      : scheduleWeek;

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
      (card) => card.week === currentWeek || card.week === currentWeek + 1,
    );
  }

  let usedScheduleFallback = false;
  if (regCards.length === 0) {
    const weeks =
      resolved.mode === "week" && resolved.week
        ? [resolved.week]
        : resolved.mode === "iso"
          ? [scheduleWeek]
          : [currentWeek, currentWeek + 1];
    let scheduled = buildRegCardsFromSchedule(weeks, season);
    if (resolved.mode === "iso" && resolved.iso) {
      scheduled = scheduled.filter((card) =>
        (card.startTime || "").startsWith(resolved.iso!),
      );
    }
    if (scheduled.length > 0) {
      regCards = scheduled;
      usedScheduleFallback = true;
    }
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
    Boolean(preseasonOdds.byMatchup.get(`${card.awayAbbr}@${card.homeAbbr}`)),
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
    const regWeekLabel = formatNflBoardWeekLabel(
      resolved.mode === "week" ? resolved.week : currentWeek,
      { season, lineCount: regCards.length },
    );
    sections.push({
      key: "regular",
      title:
        regWeekLabel === "Preseason"
          ? "Regular season (upcoming)"
          : resolved.mode === "week"
            ? `Regular season · ${regWeekLabel}`
            : `Regular season · ${regWeekLabel}–${formatNflBoardWeekLabel(currentWeek + 1, { season })}`,
      subtitle: usedScheduleFallback
        ? "Scheduled matchups. Model lines and publish tags are unavailable."
        : "Kos Edge fair-lines with live market join, publish tags, and best-book context.",
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
    modelUnavailable: Boolean(fairLines.error) || usedScheduleFallback,
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
