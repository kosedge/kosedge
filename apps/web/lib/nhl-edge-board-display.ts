/**
 * NHL Edge Board customer-facing display copy (honesty / naming).
 *
 * Thresholds are NOT redefined here — import from nhl-trusted-market.ts
 * (twin: services/model-service/.../nhl_kei.py LEAN_EDGE_PTS / PLAY_EDGE_PTS).
 *
 * Internal market keys stay "Spread" / "Moneyline" (no schema migration).
 * Display only: Spread → Puck Line; two-way ML → Game Moneyline — Includes OT/Shootout.
 */

import { NHL_LEAN_EDGE_PTS, NHL_PLAY_EDGE_PTS } from "@/lib/nhl-trusted-market";

/** Customer label for the NHL puck-line (internal market key remains "Spread"). */
export const NHL_PUCK_LINE_LABEL = "Puck Line";

/**
 * Customer label for NHL two-way game moneyline (includes OT/SO).
 * Do not use ambiguous "Regulation ML"; regulation product is 60-Minute 3-Way.
 */
export const NHL_GAME_MONEYLINE_LABEL = "Game Moneyline — Includes OT/Shootout";

/** Edge column subtitle for the puck-line market. */
export const NHL_PUCK_LINE_EDGE_LABEL = "Puck Line edge";

/**
 * Footer tag cuts — must match NHL_LEAN_EDGE_PTS / NHL_PLAY_EDGE_PTS.
 * Before: generic EdgeBoard catch-all "LEAN (≥1) / PLAY (≥2.5)".
 */
export function nhlEdgeBoardTagFooter(): string {
  return (
    `NHL tags — PASS / LEAN (≥${NHL_LEAN_EDGE_PTS}) / PLAY (≥${NHL_PLAY_EDGE_PTS}) ` +
    `goal units vs trusted Best. Research-fair tags (not stake-cleared PLAY). `
  );
}

/**
 * Label for Model≠KEI chrome on NHL Edge Board.
 * Research-only disagreement must not read as stake PLAY/LEAN.
 */
export const NHL_MODEL_DISAGREEMENT_LABEL = "MODEL DISAGREEMENT";

/** Alternate research-only chrome when a softer label fits. */
export const NHL_RESEARCH_SIGNAL_LABEL = "RESEARCH SIGNAL";

/** Map internal assemble market key → customer display label (NHL only). */
export function nhlDisplayMarketLabel(
  market: string | null | undefined,
): string {
  const m = String(market ?? "");
  if (m === "Spread") return NHL_PUCK_LINE_LABEL;
  if (m === "Moneyline") return NHL_GAME_MONEYLINE_LABEL;
  return m || "—";
}
