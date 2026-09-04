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
 * Odds-API / colloquial alias of CFB fair-lines.
 * Thin route (do not re-export CFB route — Turbopack rejects App Router re-exports).
 * Same honest empty helper; sport=ncaaf.
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
      sport: "ncaaf",
      slateStatus: "not_connected",
      message: fairLinesNotConnectedMessage("NCAAF (CFB alias)"),
    }),
  );
}
