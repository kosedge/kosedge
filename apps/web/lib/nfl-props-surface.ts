/**
 * One Props ↔ Edges availability contract.
 * Edges must not present a full prop-edge sheet when Props is gated/empty.
 *
 * Dual gate (Coming Soon / NO-GO): LIVE=false AND the football public
 * numbers kill switch. Either control alone must keep fair/edge dark.
 */

import { isFootballPublicNumbersDisabled } from "@/lib/cfb-edge-board-public";
import {
  NFL_WEEKLY_PROPS_GATE_BODY,
  NFL_WEEKLY_PROPS_GATE_TITLE,
  NFL_WEEKLY_PROPS_LIVE,
} from "@/lib/nfl-weekly-props-live";

export type NflPropsSurfaceState =
  | "gated"
  | "unreachable"
  | "empty"
  | "research-only"
  | "book-joined";

export type NflPropsSurfaceSnapshot = {
  error?: string;
  rows: Array<{ marketJoined: boolean }>;
  diagnostics: {
    notLive?: boolean;
    marketJoinedCount?: number;
    kosedgeOnly?: boolean;
  };
};

/**
 * True only when weekly props may hit model-service / paint fair/edge.
 * LIVE and the public-numbers kill switch are independent: either one
 * dark keeps the board from fetching or showing subscriber numbers.
 */
export function nflWeeklyPropsBoardMayFetch(opts?: {
  live?: boolean;
  publicNumbersDisabled?: boolean;
}): boolean {
  const live = opts?.live ?? NFL_WEEKLY_PROPS_LIVE;
  const publicNumbersDisabled =
    opts?.publicNumbersDisabled ?? isFootballPublicNumbersDisabled("nfl");
  return live && !publicNumbersDisabled;
}

export function nflPropsSurfaceState(
  board: NflPropsSurfaceSnapshot,
): NflPropsSurfaceState {
  if (!nflWeeklyPropsBoardMayFetch() || board.diagnostics.notLive) {
    return "gated";
  }
  if (board.error) return "unreachable";
  const joined =
    board.diagnostics.marketJoinedCount ??
    board.rows.filter((row) => row.marketJoined).length;
  if (joined > 0) return "book-joined";
  if (board.rows.length > 0 || board.diagnostics.kosedgeOnly) {
    return "research-only";
  }
  return "empty";
}

export function nflPropsSurfaceCopy(state: NflPropsSurfaceState): {
  title: string;
  body: string;
} {
  switch (state) {
    case "gated":
      return {
        title: NFL_WEEKLY_PROPS_GATE_TITLE,
        body: NFL_WEEKLY_PROPS_GATE_BODY,
      };
    case "unreachable":
      return {
        title: "Props board unreachable",
        body: "Model service did not return prop rows. Edges will not invent a props sheet.",
      };
    case "empty":
      return {
        title: "No live prop rows yet",
        body: "Player props fill when markets and model hooks join. Game lines stay on Edge Board. No fake rows.",
      };
    case "research-only":
      return {
        title: "Model means only",
        body: "Showing research means. Book edge stays blank until a market joins. Same truth on Props and Edges.",
      };
    case "book-joined":
      return {
        title: "Props vs market",
        body: "Edge vs joined books. No PLAY / LEAN stake tags.",
      };
  }
}

/** Prop-edge rows belong on Edges only when Props can explain them. */
export function edgesMayShowPropRows(state: NflPropsSurfaceState): boolean {
  return state === "book-joined";
}
