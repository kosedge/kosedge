/**
 * Edges desk honesty (#8 Phase C last slice · #4 E4).
 *
 * `/pro/{sport}/edges` stays live as a demoted desk — not a dual primary /
 * competing decision-center truth vs Edge Board research-fair honesty.
 *
 * Edge Board stamp: "KEI vs market. Model is research-fair. Tags never use
 * Model vs market." Desk copy must not reframe as model-vs-market truth.
 */

/** Shared Edge Board research-fair honesty line (customer chrome). */
export const EDGE_BOARD_RESEARCH_FAIR_HONESTY =
  "KEI vs market. Model is research-fair. Tags never use Model vs market.";

/**
 * Hero summary for shared sport edges desks (CFB / NBA / siblings on
 * `/pro/[sport]/edges`). Points to Edge Board as decision center.
 */
export function edgesDeskSummary(pathLabel: string): string {
  return (
    `Demoted desk — Edge Board is the decision center. ` +
    `KEI vs market separations for the current slate. ` +
    `Model is research-fair; tags never use Model vs market. ` +
    `Desk path: ${pathLabel}. Research only — you make the picks.`
  );
}

/** Count line when board-derived KEI separations are present. */
export function edgesDeskQuantifiedLine(count: number): string {
  return `${count} matchups with KEI vs market separation on the current board.`;
}

/** Pending copy when market lines exist but KEI join has not published seps. */
export const EDGES_DESK_SEPARATIONS_PENDING_TITLE =
  "Board slate live — KEI separations pending";

/** NFL edges desk H1 — demoted desk, not model-vs-market decision chrome. */
export const NFL_EDGES_DESK_TITLE = "Edges desk";

/** NFL edges desk subtitle — aligns with Edge Board research-fair honesty. */
export const NFL_EDGES_DESK_SUMMARY =
  "Demoted desk — Edge Board is the decision center. KEI vs market separations vs the joined book. Model is research-fair; tags never use Model vs market. Empty when nothing clears the cut.";
