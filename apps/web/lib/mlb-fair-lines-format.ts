export type MlbFairLineRow = {
  gameId: string;
  gameDate: string | null;
  startTime: string | null;
  homeTeam: string;
  awayTeam: string;
  /** @deprecated Handicap home win prob — use handicapHomeWinProb. */
  homeWinProb: number | null;
  /** @deprecated Handicap home ML — use handicapHomeMl. fair_fg_* alias. */
  fairHomeMl: number | null;
  /** @deprecated Handicap away ML — use handicapAwayMl. */
  fairAwayMl: number | null;
  /** Continuous FG sim mean (`fg_total_mean`). Not the board KEI. */
  totalMean: number | null;
  /** @deprecated Handicap total — use handicapTotal. */
  fairTotal: number | null;
  /** @deprecated Handicap run line — use handicapSpreadHome. */
  fairSpreadHome: number | null;
  runLineCoverProbHome: number | null;
  marginMean: number | null;
  projectedAt: string | null;
  modelVersion: string;

  // Handicap = KEI product line
  handicapHomeWinProb?: number | null;
  handicapHomeMl?: number | null;
  handicapAwayMl?: number | null;
  /** Board / KEI total — nearest half-run of the matching mean. */
  handicapTotal?: number | null;
  handicapTotalMean?: number | null;
  handicapSpreadHome?: number | null;
  /** Provenance: `nearest_half_run`. */
  fairTotalQuantization?: string | null;

  // Model = pure sim / research
  modelHomeWinProb?: number | null;
  modelHomeMl?: number | null;
  modelAwayMl?: number | null;
  modelTotal?: number | null;
  modelTotalMean?: number | null;
  modelSpreadHome?: number | null;
};

export function formatAmericanOdds(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const rounded = Math.round(value);
  return rounded > 0 ? `+${rounded}` : String(rounded);
}

export function formatRunLine(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const rounded = Math.round(value * 100) / 100;
  return rounded > 0 ? `+${rounded.toFixed(1)}` : rounded.toFixed(1);
}

/** Board / KEI total (half-run). Continuous means use `formatMlbTotalMean`. */
export function formatTotal(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return value.toFixed(1);
}

export function formatWinProb(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatKickoff(value: string | null): string {
  if (!value) return "TBD";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "TBD";
  return date.toLocaleString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
}
