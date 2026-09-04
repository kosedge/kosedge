/**
 * Shared fair-lines page-data board shape for Pro API routes.
 *
 * Overnight #5 honesty contract:
 * - Never invent book prices, KEI, CLV, or as-of clocks.
 * - Prefer HTTP 200 + empty lines + slateStatus over bare 404 when a desk expects JSON.
 * - asOf / oddsAsOf are null unless upstream supplied a real vintage.
 */

export const FAIR_LINES_HONESTY_SPORTS = [
  "cfb",
  "mlb",
  "nba",
  "nhl",
  "wnba",
] as const;

export type FairLinesHonestySport =
  (typeof FAIR_LINES_HONESTY_SPORTS)[number];

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

export type FairLinesApiBoard<TLine = unknown> = {
  sport: string;
  /** Model / board vintage when known — never request clock. */
  asOf: string | null;
  /** Book odds vintage when known — never request clock. */
  oddsAsOf: string | null;
  count: number;
  lines: TLine[];
  slateStatus: string;
  message: string;
  modelVersion: string;
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

export function honestEmptyFairLinesBoard(opts: {
  sport: string;
  slateStatus: string;
  message: string;
  modelVersion?: string;
  gameDate?: string;
  error?: string;
}): FairLinesApiBoard {
  return {
    sport: opts.sport,
    asOf: null,
    oddsAsOf: null,
    count: 0,
    lines: [],
    slateStatus: opts.slateStatus,
    message: opts.message,
    modelVersion: opts.modelVersion ?? "",
    ...(opts.gameDate ? { gameDate: opts.gameDate } : {}),
    ...(opts.error ? { error: opts.error } : {}),
  };
}

/**
 * Normalize a sport board into the shared API envelope.
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

  return {
    sport: opts.sport,
    asOf: opts.asOf ?? null,
    oddsAsOf: opts.oddsAsOf ?? null,
    count,
    lines: opts.lines,
    slateStatus,
    message,
    modelVersion: opts.modelVersion ?? "",
    ...(opts.gameDate ? { gameDate: opts.gameDate } : {}),
    ...(opts.error ? { error: opts.error } : {}),
  };
}
