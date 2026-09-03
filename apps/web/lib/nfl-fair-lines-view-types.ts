/** Client-safe KEI / fair-lines row shapes (no server-only). */

export type NflKeiRepriceFactor = {
  factor: string;
  applied: boolean;
  team: string | null;
  direction: string;
  spreadPts: number;
  totalPts: number;
  confidenceDelta: number;
  reason: string;
};

export type NflKeiRepriceLog = {
  applied: boolean;
  skipped: boolean;
  reason: string;
  spreadDelta: number;
  totalDelta: number;
  qbClear: boolean | null;
  injuryClear: boolean | null;
  capped: boolean;
  appliedFactors: NflKeiRepriceFactor[];
  consideredNotApplied: NflKeiRepriceFactor[];
};

export type NflFairLineRow = {
  gameId: string;
  week: number | null;
  startTime: string | null;
  awayTeam: string;
  homeTeam: string;
  awayAbbr: string;
  homeAbbr: string;
  handicapSpreadHome: number | null;
  spreadHome: number | null;
  handicapTotal: number | null;
  totalMean: number | null;
  modelSpreadHome: number | null;
  modelTotal: number | null;
  fairHomeMl: number | null;
  fairAwayMl: number | null;
  homeWinProb: number | null;
  awayWinProb: number | null;
  marketHomeMl: number | null;
  marketAwayMl: number | null;
  marketTotal: number | null;
  marketJoined: boolean;
  mlEdgeProb: number | null;
  keiReprice: NflKeiRepriceLog | null;
};

export type NflFairLinesResponse = {
  season: number;
  modelVersion: string;
  asOf: string | null;
  oddsAsOf: string | null;
  currentWeek: number;
  count: number;
  lines: NflFairLineRow[];
  window: { daysAhead: number; includePastDays: number };
  diagnostics: {
    oddsFeedStatus: string;
    oddsFeedError: string | null;
    oddsEventsSeen: number;
    marketJoinedCount: number;
    bookmakers: string[];
    kosedgeOnly: boolean;
  };
  error?: string;
  slateStatus?: string;
};
