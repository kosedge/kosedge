/**
 * INC-2026-09-07 SEV-2 (C) — NFL Edge Board assemble window semantics.
 *
 * Live / Week 1 customer path uses a narrow fair-lines window (Week 1 slate).
 * Full-slate requests must not silently reuse that narrow pull and label it
 * "full". Full serves from a governed complete assemble (CDN cache after a
 * successful full-window pull, or a live full-window assemble). Transport /
 * assemble failure → fail closed (503/504). Never return a Week-1-window
 * board labeled as full slate.
 *
 * B/D snapshot spine is follow-on — this module only governs window + honesty.
 */

export type NflAssembleWindow = {
  daysAhead: number;
  includePastDays: number;
};

/** Customer-relevant Week 1 / live slate (Thu–Mon + small buffer). */
export const NFL_EDGE_BOARD_LIVE_WINDOW: NflAssembleWindow = {
  daysAhead: 10,
  includePastDays: 2,
};

/**
 * Full multi-week projection window. Used only when slate=full and we are
 * allowed to live-assemble a complete board (not the Week 1 tab path).
 */
export const NFL_EDGE_BOARD_FULL_WINDOW: NflAssembleWindow = {
  daysAhead: 200,
  includePastDays: 14,
};

export function nflAssembleWindowForSlate(
  slate: "week1" | "full",
): NflAssembleWindow {
  return slate === "full"
    ? NFL_EDGE_BOARD_FULL_WINDOW
    : NFL_EDGE_BOARD_LIVE_WINDOW;
}

/**
 * Fail closed if a slate=full path would use the narrow live window.
 * That is the truncated-"full slate" footgun (Week 1 pull labeled full).
 * Early-season boards that honestly only have Week 1 KEI after a full-window
 * pull are allowed — empty future weeks are not invented.
 */
export function assertHonestNflFullSlateWindow(
  slate: "week1" | "full",
  window: NflAssembleWindow,
): void {
  if (slate !== "full") return;
  if (window.daysAhead < NFL_EDGE_BOARD_FULL_WINDOW.daysAhead) {
    throw new Error(
      "NFL full-slate assemble unavailable: refusing narrow live window " +
        `as full (daysAhead=${window.daysAhead}; need ${NFL_EDGE_BOARD_FULL_WINDOW.daysAhead}).`,
    );
  }
}
