/**
 * Which Edge Board sports currently have a KEI (handicap) projection source.
 *
 * Markets-only sports (NHL today): Odds / fallback snapshots only.
 * Do NOT invent KEI numbers or a fake model vs handicap split until a real
 * fair-lines / kei_lines path exists for that sport.
 *
 * See also: resolveKeiGames / assembleEdgeBoardRows comments.
 */

const KEI_SOURCE_SPORTS = new Set([
  "mlb",
  "nfl",
  "nba",
  "wnba",
  "ncaam",
  "cfb",
]);

/** Sports with published KEI from fair-lines or kei_lines_*.json. */
export function sportHasKeiSource(sportKey: string | null | undefined): boolean {
  const sport = String(sportKey ?? "")
    .trim()
    .toLowerCase();
  return KEI_SOURCE_SPORTS.has(sport);
}

/**
 * Markets-only board: show books, leave KEI / edge / tags empty and honest.
 * NHL until a model ships — do not invent KEI.
 */
export function sportIsMarketsOnlyEdgeBoard(
  sportKey: string | null | undefined,
): boolean {
  const sport = String(sportKey ?? "")
    .trim()
    .toLowerCase();
  return sport === "nhl";
}
