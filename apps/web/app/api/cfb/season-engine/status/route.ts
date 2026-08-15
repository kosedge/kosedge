import { NextResponse } from "next/server";
import { fetchCfbSeasonEngineStatus } from "@/lib/cfb-season-engine";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const status = await fetchCfbSeasonEngineStatus({
    season: Number(url.searchParams.get("season") ?? 2026),
    asOfWeek: Number(url.searchParams.get("as_of_week") ?? 1),
    demo: url.searchParams.has("demo")
      ? url.searchParams.get("demo") === "true"
      : true,
  });
  if (status.error && !status.engine_version) {
    return NextResponse.json(
      {
        ...status,
        used_in_spread: false,
        error: status.error.startsWith("model unreachable")
          ? status.error
          : `model unreachable: ${status.error}`,
      },
      { status: 200 },
    );
  }
  return NextResponse.json({ ...status, used_in_spread: false });
}
