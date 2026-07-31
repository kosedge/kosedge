import "server-only";
import { env } from "@/lib/config/env";
import {
  deskEdgesFromTodayRow,
  deskRunLineFromFairLine,
  formatQuality,
  formatStakeFraction,
  type MlbDeskEdgeRow,
  type MlbDeskMarketType,
} from "@/lib/mlb-desk-helpers";
import { fetchMlbFairLines } from "@/lib/mlb-fair-lines";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";

export type { MlbDeskEdgeRow, MlbDeskMarketType };
export {
  deskEdgesFromTodayRow,
  deskRunLineFromFairLine,
  formatQuality,
  formatStakeFraction,
};

export type MlbEdgesDeskResponse = {
  modelVersion: string;
  count: number;
  rows: MlbDeskEdgeRow[];
  filters: {
    market: MlbDeskMarketType;
    minProbEdge: number;
    minLineEdge: number;
    minQuality: number;
  };
  diagnostics: {
    edgesTodayError?: string;
    candidateCount: number;
  };
};

export async function fetchMlbEdgesDesk(params: {
  market?: MlbDeskMarketType;
  minProbEdge?: number;
  minLineEdge?: number;
  minQuality?: number;
  includeRunLine?: boolean;
  gameDate?: string;
}): Promise<MlbEdgesDeskResponse> {
  const market = params.market ?? "all";
  const minProbEdge = params.minProbEdge ?? 0.02;
  const minLineEdge = params.minLineEdge ?? 0.5;
  const minQuality = params.minQuality ?? 0;
  const base = env.MODEL_SERVICE_URL;

  const empty: MlbEdgesDeskResponse = {
    modelVersion: "",
    count: 0,
    rows: [],
    filters: { market, minProbEdge, minLineEdge, minQuality },
    diagnostics: { candidateCount: 0 },
  };

  if (!base) {
    return {
      ...empty,
      diagnostics: {
        candidateCount: 0,
        edgesTodayError: "MODEL_SERVICE_URL is not configured.",
      },
    };
  }

  const url = new URL(`${base.replace(/\/+$/, "")}/mlb/edges/today`);

  let edgesTodayError: string | undefined;
  let modelVersion = "";
  let todayRows: MlbDeskEdgeRow[] = [];

  try {
    const response = await upstreamFetch(url.toString(), {
      cache: "no-store",
      timeoutMs: UPSTREAM_TIMEOUT_MS.board,
      headers: {
        accept: "application/json",
        ...(env.INTERNAL_API_SECRET
          ? { "x-kosedge-secret": env.INTERNAL_API_SECRET }
          : {}),
      },
    });
    if (!response.ok) {
      edgesTodayError = `Model service returned ${response.status}.`;
    } else {
      const payload = (await response.json()) as {
        model_version?: string;
        edges?: Array<Record<string, unknown>>;
      };
      modelVersion = String(payload.model_version ?? "");
      const edges = Array.isArray(payload.edges) ? payload.edges : [];
      todayRows = edges.flatMap((row) =>
        deskEdgesFromTodayRow(row, { minProbEdge, minLineEdge, minQuality }),
      );
    }
  } catch {
    edgesTodayError = "Unable to reach model service.";
  }

  let runLineRows: MlbDeskEdgeRow[] = [];
  if (
    params.includeRunLine !== false &&
    (market === "all" || market === "run_line")
  ) {
    const board = await fetchMlbFairLines({ gameDate: params.gameDate });
    if (!board.error) {
      if (!modelVersion) modelVersion = board.modelVersion;
      runLineRows = board.lines
        .map((row) =>
          deskRunLineFromFairLine(row, { minCoverLean: minProbEdge }),
        )
        .filter((row): row is MlbDeskEdgeRow => row !== null);
    }
  }

  const merged = [...todayRows, ...runLineRows].filter((row) =>
    market === "all" ? true : row.marketType === market,
  );
  merged.sort((a, b) => Math.abs(b.edge) - Math.abs(a.edge));

  return {
    modelVersion,
    count: merged.length,
    rows: merged,
    filters: { market, minProbEdge, minLineEdge, minQuality },
    diagnostics: {
      edgesTodayError,
      candidateCount: todayRows.length + runLineRows.length,
    },
  };
}
