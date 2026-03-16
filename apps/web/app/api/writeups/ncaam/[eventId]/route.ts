// apps/web/app/api/writeups/ncaam/[eventId]/route.ts
import { NextResponse } from "next/server";
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { buildNcaamWriteup, type NcaamGameContext } from "@/lib/writeups/ncaam";

type Params = { eventId: string };

export async function GET(
  _req: Request,
  { params }: { params: Promise<Params> }
) {
  const { eventId } = await params;

  const dataPath = join(
    process.cwd(),
    "data",
    "processed",
    "upcoming_ncaam_games.json"
  );

  if (!existsSync(dataPath)) {
    return NextResponse.json(
      { error: "No upcoming games export found" },
      { status: 404 }
    );
  }

  let games: any[];
  try {
    const raw = readFileSync(dataPath, "utf-8");
    games = JSON.parse(raw);
  } catch (e) {
    return NextResponse.json(
      { error: "Failed to read upcoming games", details: String(e) },
      { status: 500 }
    );
  }

  const game = games.find((g) => g.event_id === eventId);
  if (!game) {
    return NextResponse.json(
      { error: "Game not found", eventId },
      { status: 404 }
    );
  }

  const ctx: NcaamGameContext = {
    eventId: game.event_id,
    gameDate: game.commence_time?.slice(0, 10),
    homeTeam: game.home_team,
    awayTeam: game.away_team,
    neutral: Boolean(game.neutral),
    conferenceHome: game.conference_home ?? null,
    conferenceAway: game.conference_away ?? null,
    isTournament: false, // can be refined later based on date/conference
    modelSpread: Number(game.ensemble_spread),
    marketSpreadClose:
      game.consensus_close_spread != null
        ? Number(game.consensus_close_spread)
        : null,
    edgeClose:
      game.spread_edge != null ? Number(game.spread_edge) : null,
    modelTotal:
      game.ensemble_total != null ? Number(game.ensemble_total) : null,
    marketTotalClose:
      game.consensus_close_total != null
        ? Number(game.consensus_close_total)
        : null,
    totalEdge:
      game.total_edge != null ? Number(game.total_edge) : null,
    restDaysHome:
      game.days_rest_home != null ? Number(game.days_rest_home) : null,
    restDaysAway:
      game.days_rest_away != null ? Number(game.days_rest_away) : null,
    travelMilesAway:
      game.travel_miles_away != null ? Number(game.travel_miles_away) : null,
    keyPlayerOutHome:
      game.key_player_out_home != null
        ? Boolean(game.key_player_out_home)
        : null,
    keyPlayerOutAway:
      game.key_player_out_away != null
        ? Boolean(game.key_player_out_away)
        : null,
  };

  const writeup = buildNcaamWriteup(ctx);

  return NextResponse.json({
    eventId: ctx.eventId,
    homeTeam: ctx.homeTeam,
    awayTeam: ctx.awayTeam,
    writeup,
    edges: {
      spread: ctx.edgeClose,
      total: ctx.totalEdge,
    },
  });
}

