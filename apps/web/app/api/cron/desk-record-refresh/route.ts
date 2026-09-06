import { NextResponse } from "next/server";
import { PAGE_DATA_NO_STORE } from "@/lib/page-data-cache";
import { loadDeskRecord } from "@/lib/desk-record";

export const dynamic = "force-dynamic";

/**
 * Morning desk-record refresh stub.
 * Auth mirrors /api/cron/warm-page-data (CRON_SECRET Bearer).
 *
 * Vercel serverless cannot durably rewrite repo ledger files — settlement
 * remains a morning commit of data/desk-record/** after rebuild_summary.py.
 * This endpoint returns the live computed summary for CoS/PA monitoring.
 */
function authorizeCron(req: Request): boolean {
  const secret = process.env.CRON_SECRET?.trim();
  if (secret) {
    return (req.headers.get("authorization") || "") === `Bearer ${secret}`;
  }
  return process.env.NODE_ENV !== "production";
}

export async function GET(req: Request) {
  if (!authorizeCron(req)) {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401, headers: { "Cache-Control": PAGE_DATA_NO_STORE } },
    );
  }

  const url = new URL(req.url);
  const sport = (url.searchParams.get("sport") || "cfb").toLowerCase();
  const seasonRaw = url.searchParams.get("season");
  const season = seasonRaw ? Number(seasonRaw) : 2026;
  if (!Number.isFinite(season) || season < 2020 || season > 2100) {
    return NextResponse.json(
      { error: "Invalid season" },
      { status: 400, headers: { "Cache-Control": PAGE_DATA_NO_STORE } },
    );
  }

  const summary = loadDeskRecord(sport, season);
  const { tickets: _tickets, ...rest } = summary;
  void _tickets;

  return NextResponse.json(
    {
      ok: true,
      mode: "read_only_summary",
      note: "Ledger settles via morning commit; this stub does not invent juice or rewrite FS.",
      rebuild:
        "python3 scripts/desk-record/rebuild_summary.py --sport cfb --season 2026",
      docs: "docs/DESK_ATS_ROI_RECORD.md",
      summary: rest,
    },
    { headers: { "Cache-Control": PAGE_DATA_NO_STORE } },
  );
}
