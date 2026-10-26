/** Client-safe Edges desk types (no server-only). */

import type {
  NflEdgesPropsStatus,
  NflSurfaceProvenance,
} from "@/lib/nfl-surface-provenance";

export type DeskMarketType = "all" | "ml" | "spread" | "total" | "props";

export type DeskEdgeRow = {
  id: string;
  marketType: Exclude<DeskMarketType, "all">;
  matchupOrPlayer: string;
  detail: string;
  kosedgeLine: string;
  marketLine: string;
  edge: number;
  edgeDisplay: string;
  side: string;
  confidence: number | null;
  kickoff: string | null;
  source: "fair-lines" | "edges-today" | "props";
  /** Per-row capture vintage. Never inherit desk marketAsOf (E-3). */
  linesAsOf: string | null;
};

export type NflEdgesDeskResponse = {
  season: number;
  week: number;
  count: number;
  rows: DeskEdgeRow[];
  filters: {
    market: DeskMarketType;
    minProbEdge: number;
    minLineEdge: number;
    minConfidence: number;
  };
  propsSurface:
    | "gated"
    | "unreachable"
    | "empty"
    | "research-only"
    | "book-joined";
  /**
   * Q3 / N-1 / X-4 — explicit omit. First build is "unavailable";
   * UI must not present the desk as a complete slate.
   */
  propsStatus: NflEdgesPropsStatus;
  /** Shared customer-truth envelope (runId/sha/linesAsOf/certStatus). */
  observed: NflSurfaceProvenance;
  /** Legacy alias of observed.linesAsOf. Must not mask a missing row vintage. */
  marketAsOf: string | null;
  marketBooks: string[];
  deskComplete: false;
  diagnostics: {
    gameCandidates: number;
    propCandidates: number;
    fairLinesError?: string;
    edgesTodayError?: string;
    propsError?: string;
    propsOmitted?: true;
    edgeRowsBlocked?: true;
    bindReason?: string;
    provenanceReason?: string;
  };
};
