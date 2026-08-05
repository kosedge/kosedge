import { NextResponse } from "next/server";
import { fetchCfbPerformance } from "@/lib/cfb-season-engine";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const limitRaw = url.searchParams.get("limit");
  const limit = limitRaw ? Number(limitRaw) : 200;
  const engineVersion = url.searchParams.get("engine_version") ?? undefined;
  const summary = await fetchCfbPerformance({
    limit: Number.isFinite(limit) ? limit : 200,
    engineVersion: engineVersion || undefined,
  });
  if (summary.error) {
    return NextResponse.json(summary, { status: 502 });
  }
  return NextResponse.json(summary);
}
