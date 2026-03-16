// apps/web/app/api/top-edges/ncaam/route.ts
import { NextResponse } from "next/server";
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

type TopEdgesQuery = {
  limit?: number;
};

export async function GET(req: Request) {
  const url = new URL(req.url);
  const params: TopEdgesQuery = {
    limit: url.searchParams.get("limit")
      ? Number(url.searchParams.get("limit"))
      : undefined,
  };

  const limit = Number.isFinite(params.limit ?? NaN)
    ? Math.max(1, Math.min(50, params.limit as number))
    : 10;

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

  if (!Array.isArray(games) || games.length === 0) {
    return NextResponse.json({ games: [] });
  }

  // Sort by absolute spread edge descending; fallback to total edge when spread edge missing.
  const scored = games
    .map((g) => {
      const spreadEdge =
        g.spread_edge != null ? Number(g.spread_edge) : null;
      const totalEdge =
        g.total_edge != null ? Number(g.total_edge) : null;
      const magnitude =
        spreadEdge != null
          ? Math.abs(spreadEdge)
          : totalEdge != null
          ? Math.abs(totalEdge)
          : 0;
      return { ...g, spreadEdge, totalEdge, magnitude };
    })
    .filter((g) => g.magnitude > 0)
    .sort((a, b) => b.magnitude - a.magnitude)
    .slice(0, limit)
    .map((g) => ({
      eventId: g.event_id,
      gameDate: g.commence_time?.slice(0, 10),
      homeTeam: g.home_team,
      awayTeam: g.away_team,
      spreadEdge: g.spreadEdge,
      consensusCloseSpread: g.consensus_close_spread,
      ensembleSpread: g.ensemble_spread,
      totalEdge: g.totalEdge,
      consensusCloseTotal: g.consensus_close_total,
      ensembleTotal: g.ensemble_total,
    }));

  return NextResponse.json({ games: scored });
}

