import { NextResponse } from "next/server";
import {
  fetchModelTrackerPicks,
  fetchModelTrackerStatus,
  fetchModelTrackerSummary,
  postModelTrackerGrade,
  postModelTrackerPick,
} from "@/lib/model-tracker";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const view = url.searchParams.get("view") || "summary";
  const sport = url.searchParams.get("sport") ?? undefined;
  const seasonRaw = url.searchParams.get("season");
  const weekRaw = url.searchParams.get("week");
  const season = seasonRaw ? Number(seasonRaw) : undefined;
  const week = weekRaw ? Number(weekRaw) : undefined;
  const tag = url.searchParams.get("tag") ?? undefined;

  if (view === "status") {
    const status = await fetchModelTrackerStatus();
    return NextResponse.json(status, { status: status.error ? 502 : 200 });
  }
  if (view === "picks") {
    const picks = await fetchModelTrackerPicks({
      sport,
      season: Number.isFinite(season) ? season : undefined,
      week: Number.isFinite(week) ? week : undefined,
      tag: tag || undefined,
      limit: 100,
    });
    return NextResponse.json(picks, { status: picks.error ? 502 : 200 });
  }
  const summary = await fetchModelTrackerSummary({
    sport,
    season: Number.isFinite(season) ? season : undefined,
    week: Number.isFinite(week) ? week : undefined,
    limit: 1000,
  });
  return NextResponse.json(summary, { status: summary.error ? 502 : 200 });
}

export async function POST(req: Request) {
  const body = (await req.json()) as Record<string, unknown>;
  const action = typeof body.action === "string" ? body.action : "log";

  if (action === "grade") {
    const pickId = typeof body.pick_id === "string" ? body.pick_id : "";
    const home = Number(body.home_score);
    const away = Number(body.away_score);
    if (!pickId || !Number.isFinite(home) || !Number.isFinite(away)) {
      return NextResponse.json(
        { error: "pick_id, home_score, away_score required" },
        { status: 400 },
      );
    }
    const result = await postModelTrackerGrade({
      pickId,
      home_score: home,
      away_score: away,
    });
    return NextResponse.json(result, { status: result.error ? 502 : 200 });
  }

  const tag = body.tag === "LEAN" ? "LEAN" : body.tag === "PLAY" ? "PLAY" : null;
  if (!tag) {
    return NextResponse.json({ error: "tag must be PLAY or LEAN" }, { status: 400 });
  }
  const sport = typeof body.sport === "string" ? body.sport : "cfb";
  const home_team = typeof body.home_team === "string" ? body.home_team : "";
  const away_team = typeof body.away_team === "string" ? body.away_team : "";
  const side = typeof body.side === "string" ? body.side : "";
  if (!home_team || !away_team || !side) {
    return NextResponse.json(
      { error: "home_team, away_team, side required" },
      { status: 400 },
    );
  }
  const result = await postModelTrackerPick({
    sport,
    season: Number(body.season) || 2026,
    week: Number.isFinite(Number(body.week)) ? Number(body.week) : 0,
    home_team,
    away_team,
    market_type:
      typeof body.market_type === "string" ? body.market_type : "spread",
    side,
    tag,
    line_at_publish:
      body.line_at_publish != null && Number.isFinite(Number(body.line_at_publish))
        ? Number(body.line_at_publish)
        : undefined,
    odds_american:
      body.odds_american != null && Number.isFinite(Number(body.odds_american))
        ? Number(body.odds_american)
        : -110,
    game_id: typeof body.game_id === "string" ? body.game_id : undefined,
    engine_version:
      typeof body.engine_version === "string" ? body.engine_version : undefined,
    kei_version:
      typeof body.kei_version === "string" ? body.kei_version : undefined,
    edge_pts:
      body.edge_pts != null && Number.isFinite(Number(body.edge_pts))
        ? Number(body.edge_pts)
        : undefined,
    notes: typeof body.notes === "string" ? body.notes : undefined,
  });
  return NextResponse.json(result, { status: result.error ? 502 : 200 });
}
