import { NextResponse } from "next/server";
import { getProAccessState } from "@/lib/auth/pro";
import {
  fairLinesNotConnectedMessage,
  honestEmptyFairLinesBoard,
} from "@/lib/fair-lines-api-board";
import {
  pageDataCacheHeaders,
  pageDataJsonResponse,
} from "@/lib/page-data-cache";

export const dynamic = "force-dynamic";
export const maxDuration = 30;

/**
 * Page-data for /pro/cfb/fair-lines.
 * Model-service has no /cfb/fair-lines (404). Return honest empty JSON —
 * never invent KEI / book prices / as-of clocks.
 */
export async function GET() {
  const access = await getProAccessState();
  if (access !== "authorized") {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401, headers: pageDataCacheHeaders({ cacheable: false }) },
    );
  }

  return pageDataJsonResponse(
    honestEmptyFairLinesBoard({
      sport: "cfb",
      slateStatus: "not_connected",
      message: fairLinesNotConnectedMessage("CFB"),
    }),
  );
}
