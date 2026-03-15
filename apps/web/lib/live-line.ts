/**
 * Live line: theoretical spread/total for in-game betting from pre-game model + current score + time.
 * Use when you have live score and time remaining; no live odds feed required.
 */

/** Total game length in minutes (college basketball). */
const NCAAM_TOTAL_MINUTES = 40;

/**
 * Compute fair live spread (home perspective) from pre-game model and current game state.
 * Assumes the rest of the game plays to pre-game expectation.
 *
 * @param pregameSpreadHome - Pre-game model spread (home minus away), e.g. -5.5 = home favored by 5.5
 * @param homeScore - Current home team score
 * @param awayScore - Current away team score
 * @param minutesRemaining - Minutes left in the game
 * @param totalMinutes - Total game length (default 40 for NCAAM)
 * @returns Fair live spread (home). Positive = home favored from this point to the end.
 */
export function liveSpread(
  pregameSpreadHome: number,
  homeScore: number,
  awayScore: number,
  minutesRemaining: number,
  totalMinutes: number = NCAAM_TOTAL_MINUTES
): number {
  const currentMargin = homeScore - awayScore;
  const fractionRemaining = Math.max(0, Math.min(1, minutesRemaining / totalMinutes));
  // Expected final margin = current + (pregame expectation for the rest of the game)
  const expectedFinalMargin = currentMargin + pregameSpreadHome * fractionRemaining;
  // Fair live spread (from now to end) = what spread makes expected final margin zero from bettor's view
  // Live spread for "home from now" = expectedFinalMargin - currentMargin = pregameSpreadHome * fractionRemaining.
  return pregameSpreadHome * fractionRemaining;
}

/**
 * Same as liveSpread but returns the current margin and the "edge" vs a provided live line.
 * Useful to see: model says home -X live, market has home -Y live → edge = X - Y.
 */
export function liveSpreadWithEdge(
  pregameSpreadHome: number,
  homeScore: number,
  awayScore: number,
  minutesRemaining: number,
  marketLiveSpreadHome: number | null,
  totalMinutes: number = NCAAM_TOTAL_MINUTES
): { currentMargin: number; modelLiveSpreadHome: number; edgeVsMarket: number | null } {
  const currentMargin = homeScore - awayScore;
  const modelLiveSpreadHome = liveSpread(pregameSpreadHome, homeScore, awayScore, minutesRemaining, totalMinutes);
  const edgeVsMarket =
    marketLiveSpreadHome != null ? modelLiveSpreadHome - marketLiveSpreadHome : null;
  return { currentMargin, modelLiveSpreadHome, edgeVsMarket };
}
