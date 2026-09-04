/**
 * Edge Board assemble quarantine scrub (#8 Phase C / NFL-V3).
 *
 * Customer assemble JSON must not expose research quarantine vocabulary:
 * - isBestBet / is_best_bet keys (even when false)
 * - matchupOverview "Watch" section heading (OD-1 / no fourth tag chrome)
 * - mild_edge_watch_list* decision reason tokens
 *
 * Sport Standard publish tags stay PLAY | LEAN | PASS only.
 * Engine internals may still emit watch-list reasons offline — scrub at the
 * customer assemble choke point. No PLAY invent · no WATCH→LEAN.
 */

import type { EdgeBoardRow } from "@kosedge/contracts";
import {
  quarantineDecisionForCustomer,
  scrubCustomerDecisionReason,
} from "@/lib/nfl-dead-tiers";

/** Customer-safe matchup overview section (replaces quarantine "Watch"). */
export const MATCHUP_OVERVIEW_FLIPS_HEADING = "What flips";

/**
 * Rename residual "Watch" overview headings to customer-safe "What flips".
 * Preserves the flip-line body; does not invent tags.
 */
export function scrubMatchupOverviewWatchHeading(text: string): string {
  // Section heading on its own line (formatMatchupOverview shape).
  return text.replace(/(^|\n)Watch(\n|$)/g, `$1${MATCHUP_OVERVIEW_FLIPS_HEADING}$2`);
}

function scrubNestedDecision(value: unknown): unknown {
  if (!value || typeof value !== "object" || Array.isArray(value)) return value;
  return quarantineDecisionForCustomer(value as Record<string, unknown>);
}

/**
 * Scrub one assemble row before it leaves `/api/edge-board/.../assemble`.
 * Idempotent; does not invent publishTag / actionLabel / Conf.
 */
export function scrubEdgeBoardAssembleCustomerRow(
  row: EdgeBoardRow,
): EdgeBoardRow {
  const out: Record<string, unknown> = { ...(row as Record<string, unknown>) };

  delete out.isBestBet;
  delete out.is_best_bet;
  delete out.isBestBetLine;
  delete out.isBestBetOU;

  if (typeof out.matchupOverview === "string") {
    out.matchupOverview = scrubMatchupOverviewWatchHeading(out.matchupOverview);
  }
  if (typeof out.overview === "string") {
    out.overview = scrubMatchupOverviewWatchHeading(out.overview);
  }
  if (typeof out.reason === "string") {
    out.reason = scrubCustomerDecisionReason(out.reason);
  }
  if (out.decision != null) {
    out.decision = scrubNestedDecision(out.decision);
  }

  return out as EdgeBoardRow;
}

/** Scrub all rows in an assemble customer payload. */
export function scrubEdgeBoardAssembleCustomerRows(
  rows: EdgeBoardRow[],
): EdgeBoardRow[] {
  return rows.map(scrubEdgeBoardAssembleCustomerRow);
}
