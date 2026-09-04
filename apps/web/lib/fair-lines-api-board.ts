/**
 * Shared fair-lines page-data board shape for Pro API routes.
 *
 * Overnight #5 honesty contract:
 * - Never invent book prices, KEI, CLV, or as-of clocks.
 * - Prefer HTTP 200 + empty lines + slateStatus over bare 404 when a desk expects JSON.
 * - asOf / oddsAsOf are null unless upstream supplied a real vintage.
 * - Envelope keys mirror NFL `/api/nfl/fair-lines` where possible (Alex #5).
 */

export const FAIR_LINES_HONESTY_SPORTS = [
  "cfb",
  "mlb",
  "nba",
  "nhl",
  "wnba",
  "ncaaf", // CFB Odds-API alias
] as const;

export type FairLinesHonestySport = (typeof FAIR_LINES_HONESTY_SPORTS)[number];

/** Fail-closed statuses for boards that are not inventing prices. */
export const FAIR_LINES_HONEST_EMPTY_STATUSES = new Set([
  "not_connected",
  "no_odds_yet",
  "offseason_empty",
  "no_projections_yet",
  "empty",
  "no_slate",
  "preseason_empty",
  "misconfigured",
  "upstream_error",
  "upstream_unreachable",
]);

/** NFL-shaped diagnostics — zeros/empty only; never invent book joins. */
export type FairLinesApiDiagnostics = {
  oddsFeedStatus: string;
  oddsFeedError: string | null;
  oddsEventsSeen: number;
  marketJoinedCount: number;
  bookmakers: string[];
  kosedgeOnly: boolean;
  oddsPersisted: {
    eventsPersisted: number;
    snapshotsInserted: number;
    historyUpserted: number;
  };
};

export type FairLinesApiBoard<TLine = unknown> = {
  sport: string;
  /** Product season when known — null when not connected (do not invent). */
  season: number | null;
  modelVersion: string;
  /** Model / board vintage when known — never request clock. */
  asOf: string | null;
  /** Book odds vintage when known — never request clock. */
  oddsAsOf: string | null;
  /** Current week when known — null when not connected. */
  currentWeek: number | null;
  count: number;
  lines: TLine[];
  slateStatus: string;
  message: string;
  window: { daysAhead: number; includePastDays: number };
  diagnostics: FairLinesApiDiagnostics;
  gameDate?: string;
  error?: string;
};

export const FAIR_LINES_DO_NOT_INVENT =
  "We do not invent book prices, KEI lines, or as-of stamps.";

export function fairLinesNotConnectedMessage(sportLabel: string): string {
  return `${sportLabel} fair-lines are not connected to Pro yet — no odds / no model board. ${FAIR_LINES_DO_NOT_INVENT}`;
}

export function fairLinesNoOddsYetMessage(sportLabel: string): string {
  return `${sportLabel}: no odds or projections for this window yet. ${FAIR_LINES_DO_NOT_INVENT}`;
}

export function emptyFairLinesDiagnostics(
  oddsFeedStatus = "not_connected",
): FairLinesApiDiagnostics {
  return {
    oddsFeedStatus,
    oddsFeedError: null,
    oddsEventsSeen: 0,
    marketJoinedCount: 0,
    bookmakers: [],
    kosedgeOnly: true,
    oddsPersisted: {
      eventsPersisted: 0,
      snapshotsInserted: 0,
      historyUpserted: 0,
    },
  };
}

export function honestEmptyFairLinesBoard(opts: {
  sport: string;
  slateStatus: string;
  message: string;
  modelVersion?: string;
  gameDate?: string;
  error?: string;
  season?: number | null;
  currentWeek?: number | null;
}): FairLinesApiBoard {
  return {
    sport: opts.sport,
    season: opts.season ?? null,
    modelVersion: opts.modelVersion ?? "",
    asOf: null,
    oddsAsOf: null,
    currentWeek: opts.currentWeek ?? null,
    count: 0,
    lines: [],
    slateStatus: opts.slateStatus,
    message: opts.message,
    window: { daysAhead: 0, includePastDays: 0 },
    diagnostics: emptyFairLinesDiagnostics(
      opts.slateStatus === "not_connected" ? "not_connected" : "unknown",
    ),
    ...(opts.gameDate ? { gameDate: opts.gameDate } : {}),
    ...(opts.error ? { error: opts.error } : {}),
  };
}

/**
 * Normalize a sport board into the NFL-shaped API envelope.
 * Preserves real lines; stamps asOf/oddsAsOf only when provided (never Date.now()).
 */
export function toFairLinesApiBoard<TLine>(opts: {
  sport: string;
  lines: TLine[];
  slateStatus?: string | null;
  message?: string | null;
  modelVersion?: string | null;
  gameDate?: string | null;
  asOf?: string | null;
  oddsAsOf?: string | null;
  error?: string | null;
  sportLabel?: string;
  season?: number | null;
  currentWeek?: number | null;
  daysAhead?: number;
  includePastDays?: number;
  diagnostics?: Partial<FairLinesApiDiagnostics> | null;
}): FairLinesApiBoard<TLine> {
  const count = opts.lines.length;
  const slateStatus =
    (opts.slateStatus?.trim() && opts.slateStatus) ||
    (opts.error ? "upstream_error" : count === 0 ? "no_slate" : "ok");
  const sportLabel = opts.sportLabel ?? opts.sport.toUpperCase();
  const message =
    opts.message?.trim() ||
    (count === 0
      ? fairLinesNoOddsYetMessage(sportLabel)
      : `${sportLabel} fair-lines board.`);

  const baseDiag = emptyFairLinesDiagnostics(
    opts.error ? "upstream_error" : count === 0 ? "no_odds_yet" : "unknown",
  );
  const diagnostics: FairLinesApiDiagnostics = {
    ...baseDiag,
    ...(opts.diagnostics ?? {}),
    oddsPersisted: {
      ...baseDiag.oddsPersisted,
      ...(opts.diagnostics?.oddsPersisted ?? {}),
    },
  };

  return {
    sport: opts.sport,
    season: opts.season ?? null,
    modelVersion: opts.modelVersion ?? "",
    asOf: opts.asOf ?? null,
    oddsAsOf: opts.oddsAsOf ?? null,
    currentWeek: opts.currentWeek ?? null,
    count,
    lines: opts.lines,
    slateStatus,
    message,
    window: {
      daysAhead: opts.daysAhead ?? 0,
      includePastDays: opts.includePastDays ?? 0,
    },
    diagnostics,
    ...(opts.gameDate ? { gameDate: opts.gameDate } : {}),
    ...(opts.error ? { error: opts.error } : {}),
  };
}
