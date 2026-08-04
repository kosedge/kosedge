import { NextResponse } from "next/server";
import { fetchCfbProjectGame } from "@/lib/cfb-season-engine";

export const dynamic = "force-dynamic";

function parseBody(raw: unknown): {
  homeTeam?: string;
  awayTeam?: string;
  week?: number;
  season?: number;
  neutralSite?: boolean;
  nightGame?: boolean;
  demo?: boolean;
} {
  if (!raw || typeof raw !== "object") return {};
  const body = raw as Record<string, unknown>;
  return {
    homeTeam:
      typeof body.homeTeam === "string"
        ? body.homeTeam
        : typeof body.home_team === "string"
          ? body.home_team
          : undefined,
    awayTeam:
      typeof body.awayTeam === "string"
        ? body.awayTeam
        : typeof body.away_team === "string"
          ? body.away_team
          : undefined,
    week:
      typeof body.week === "number"
        ? body.week
        : typeof body.week === "string"
          ? Number(body.week)
          : undefined,
    season:
      typeof body.season === "number"
        ? body.season
        : typeof body.season === "string"
          ? Number(body.season)
          : undefined,
    neutralSite:
      typeof body.neutralSite === "boolean"
        ? body.neutralSite
        : typeof body.neutral_site === "boolean"
          ? body.neutral_site
          : undefined,
    nightGame:
      typeof body.nightGame === "boolean"
        ? body.nightGame
        : typeof body.night_game === "boolean"
          ? body.night_game
          : undefined,
    demo: typeof body.demo === "boolean" ? body.demo : undefined,
  };
}

export async function POST(req: Request) {
  let raw: unknown = {};
  try {
    raw = await req.json();
  } catch {
    raw = {};
  }
  const body = parseBody(raw);
  if (!body.homeTeam || !body.awayTeam) {
    return NextResponse.json(
      { error: "homeTeam and awayTeam are required" },
      { status: 400 },
    );
  }
  const result = await fetchCfbProjectGame({
    homeTeam: body.homeTeam,
    awayTeam: body.awayTeam,
    week: body.week,
    season: body.season,
    neutralSite: body.neutralSite,
    nightGame: body.nightGame,
    demo: body.demo,
  });
  if (result.error) {
    const status =
      result.error.includes("must") || result.error.includes("differ")
        ? 400
        : 502;
    return NextResponse.json(result, { status });
  }
  return NextResponse.json(result);
}
