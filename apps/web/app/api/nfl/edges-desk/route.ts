import { NextResponse } from "next/server";
import { getProAccessState } from "@/lib/auth/pro";
import { fetchNflEdgesDesk, type DeskMarketType } from "@/lib/nfl-edges";

export const dynamic = "force-dynamic";

const MARKET_TABS: DeskMarketType[] = ["all", "ml", "spread", "total", "props"];
const MIN_EDGE_OPTIONS = [
  { prob: 0.01, line: 0.5 },
  { prob: 0.02, line: 1.0 },
  { prob: 0.03, line: 1.5 },
] as const;
const MIN_CONF_OPTIONS = [0, 0.4, 0.6, 0.75] as const;

/**
 * Page-data for /pro/nfl/edges.
 * Desk already Promise.all's fair-lines ∥ edges/today ∥ props/board.
 * Client-fetch so HTML is not held open on that waterfall (Alex).
 */
export async function GET(req: Request) {
  const access = await getProAccessState();
  if (access !== "authorized") {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const url = new URL(req.url);
  const seasonRaw = Number(url.searchParams.get("season"));
  const weekRaw = Number(url.searchParams.get("week"));
  const season =
    Number.isFinite(seasonRaw) && seasonRaw >= 2010 ? seasonRaw : 2026;
  const week =
    Number.isFinite(weekRaw) && weekRaw >= 1 && weekRaw <= 25 ? weekRaw : 1;
  const marketRaw = (url.searchParams.get("market") ?? "all").toLowerCase();
  const market = (
    MARKET_TABS.includes(marketRaw as DeskMarketType) ? marketRaw : "all"
  ) as DeskMarketType;
  const minEdgeIdxRaw = Number(url.searchParams.get("minEdge"));
  const minEdgeIdx =
    Number.isFinite(minEdgeIdxRaw) &&
    minEdgeIdxRaw >= 0 &&
    minEdgeIdxRaw < MIN_EDGE_OPTIONS.length
      ? minEdgeIdxRaw
      : 1;
  const minEdge = MIN_EDGE_OPTIONS[minEdgeIdx]!;
  const minConfRaw = Number(url.searchParams.get("minConf"));
  const minConfidence = MIN_CONF_OPTIONS.includes(
    minConfRaw as (typeof MIN_CONF_OPTIONS)[number],
  )
    ? minConfRaw
    : 0;

  // Parallel fan-out lives inside fetchNflEdgesDesk (fair ∥ today ∥ props).
  const desk = await fetchNflEdgesDesk({
    season,
    week,
    market,
    minProbEdge: minEdge.prob,
    minLineEdge: minEdge.line,
    minConfidence,
  });

  return NextResponse.json(desk);
}
