/**
 * GET /api/live-line
 * Query: pregameSpread (number), homeScore (int), awayScore (int), minutesRemaining (number), [marketSpread] (optional)
 * Returns model live spread and, if marketSpread provided, edge vs market.
 */
import { liveSpreadWithEdge } from "@/lib/live-line";
import { jsonError, jsonOk } from "@/lib/api/response";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const pregameSpread = Number(searchParams.get("pregameSpread"));
  const homeScore = Number(searchParams.get("homeScore"));
  const awayScore = Number(searchParams.get("awayScore"));
  const minutesRemaining = Number(searchParams.get("minutesRemaining"));
  const marketSpread = searchParams.get("marketSpread") != null ? Number(searchParams.get("marketSpread")) : null;

  if (Number.isNaN(pregameSpread) || Number.isNaN(homeScore) || Number.isNaN(awayScore) || Number.isNaN(minutesRemaining)) {
    return jsonError(400, "Missing or invalid: pregameSpread, homeScore, awayScore, minutesRemaining", { code: "INVALID_PARAMS" });
  }

  const result = liveSpreadWithEdge(
    pregameSpread,
    homeScore,
    awayScore,
    minutesRemaining,
    marketSpread
  );

  return jsonOk({
    currentMargin: result.currentMargin,
    modelLiveSpreadHome: Math.round(result.modelLiveSpreadHome * 10) / 10,
    edgeVsMarket: result.edgeVsMarket != null ? Math.round(result.edgeVsMarket * 10) / 10 : null,
  });
}
