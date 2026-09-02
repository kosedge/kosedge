/**
 * Which Edge Board sports currently have a KEI (handicap) projection source.
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
  "nhl",
]);

/** Sports with published KEI from fair-lines or kei_lines_*.json. */
export function sportHasKeiSource(
  sportKey: string | null | undefined,
): boolean {
  const sport = String(sportKey ?? "")
    .trim()
    .toLowerCase();
  return KEI_SOURCE_SPORTS.has(sport);
}

/**
 * Markets-only board: show books, leave KEI / edge / tags empty and honest.
 * No sports currently markets-only after NHL Ch4 team KEI.
 */
export function sportIsMarketsOnlyEdgeBoard(
  sportKey: string | null | undefined,
): boolean {
  void sportKey;
  return false;
}
