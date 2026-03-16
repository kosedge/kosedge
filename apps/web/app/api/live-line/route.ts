/**
 * GET /api/live-line
 * Query: pregameSpread, homeScore, awayScore, minutesRemaining (required numbers); marketSpread (optional).
 * Returns model live spread and, if marketSpread provided, edge vs market.
 */
import { z } from "zod";
import { jsonError, jsonOk } from "@/lib/api/response";
import { handleApiError } from "@/lib/api/error-handler";
import { logError } from "@/lib/logger";
import { liveSpreadWithEdge } from "@/lib/live-line";

const liveLineQuerySchema = z.object({
  pregameSpread: z.coerce.number().finite(),
  homeScore: z.coerce.number().int().finite(),
  awayScore: z.coerce.number().int().finite(),
  minutesRemaining: z.coerce.number().finite().nonnegative(),
  marketSpread: z.coerce.number().finite().optional(),
});

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const parsed = liveLineQuerySchema.safeParse({
      pregameSpread: searchParams.get("pregameSpread") ?? undefined,
      homeScore: searchParams.get("homeScore") ?? undefined,
      awayScore: searchParams.get("awayScore") ?? undefined,
      minutesRemaining: searchParams.get("minutesRemaining") ?? undefined,
      marketSpread: searchParams.get("marketSpread") ?? undefined,
    });

    if (!parsed.success) {
      return jsonError(400, "Missing or invalid: pregameSpread, homeScore, awayScore, minutesRemaining", {
        code: "VALIDATION_ERROR",
      });
    }

    const { pregameSpread, homeScore, awayScore, minutesRemaining, marketSpread } = parsed.data;

    const result = liveSpreadWithEdge(
      pregameSpread,
      homeScore,
      awayScore,
      minutesRemaining,
      marketSpread ?? null
    );

    return jsonOk({
      currentMargin: result.currentMargin,
      modelLiveSpreadHome: Math.round(result.modelLiveSpreadHome * 10) / 10,
      edgeVsMarket: result.edgeVsMarket != null ? Math.round(result.edgeVsMarket * 10) / 10 : null,
    });
  } catch (error) {
    logError(error instanceof Error ? error : new Error(String(error)), { route: "live-line" });
    return handleApiError(error);
  }
}
