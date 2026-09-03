/** Client-safe Edges desk types (no server-only). */

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
  marketAsOf: string | null;
  marketBooks: string[];
  diagnostics: {
    gameCandidates: number;
    propCandidates: number;
    fairLinesError?: string;
    edgesTodayError?: string;
    propsError?: string;
  };
};
