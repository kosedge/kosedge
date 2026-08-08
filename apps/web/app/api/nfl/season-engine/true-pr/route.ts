import { NextResponse } from "next/server";
import { fetchTruePrProductSurface } from "@/lib/nfl-true-pr";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const seasonRaw = searchParams.get("season");
  const weekRaw = searchParams.get("as_of_week");
  const team = searchParams.get("team");
  const season = seasonRaw ? Number(seasonRaw) : 2026;
  const asOfWeek = weekRaw ? Number(weekRaw) : 1;

  const surface = await fetchTruePrProductSurface({
    season: Number.isFinite(season) ? season : 2026,
    asOfWeek: Number.isFinite(asOfWeek) ? asOfWeek : 1,
    team: team || null,
  });

  if (surface.error && !surface.teams.length) {
    return NextResponse.json(surface, { status: 502 });
  }
  return NextResponse.json(surface);
}
