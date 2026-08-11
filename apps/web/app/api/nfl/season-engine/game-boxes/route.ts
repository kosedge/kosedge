import { NextResponse } from "next/server";
import { fetchSeasonEngineGameBoxes } from "@/lib/nfl-season-engine";
import {
  NFL_DEFAULT_N_GAME_BOX,
  type InjuryPathInput,
} from "@/lib/nfl-season-engine-format";

export const dynamic = "force-dynamic";
/** Cold research-depth game boxes can exceed default serverless budgets. */
export const maxDuration = 180;

function parseBody(raw: unknown): {
  homeTeam?: string;
  awayTeam?: string;
  week?: number;
  season?: number;
  nReplicates?: number;
  seed?: number;
  demo?: boolean;
  includeDiagnostics?: boolean;
  injuryPaths?: InjuryPathInput[];
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
    nReplicates:
      typeof body.nReplicates === "number"
        ? body.nReplicates
        : typeof body.n_replicates === "number"
          ? body.n_replicates
          : undefined,
    seed: typeof body.seed === "number" ? body.seed : undefined,
    demo: typeof body.demo === "boolean" ? body.demo : undefined,
    includeDiagnostics:
      typeof body.includeDiagnostics === "boolean"
        ? body.includeDiagnostics
        : typeof body.include_diagnostics === "boolean"
          ? body.include_diagnostics
          : undefined,
    injuryPaths: Array.isArray(body.injuryPaths)
      ? (body.injuryPaths as InjuryPathInput[])
      : Array.isArray(body.injury_paths)
        ? (body.injury_paths as InjuryPathInput[])
        : undefined,
  };
}

export async function GET(req: Request) {
  const url = new URL(req.url);
  const homeTeam = url.searchParams.get("home_team") ?? undefined;
  const awayTeam = url.searchParams.get("away_team") ?? undefined;
  if (!homeTeam || !awayTeam) {
    return NextResponse.json(
      { error: "home_team and away_team are required" },
      { status: 400 },
    );
  }
  const result = await fetchSeasonEngineGameBoxes({
    homeTeam,
    awayTeam,
    week: Number(url.searchParams.get("week") ?? 1),
    season: Number(url.searchParams.get("season") ?? 2026),
    nReplicates: Number(
      url.searchParams.get("n_replicates") ?? NFL_DEFAULT_N_GAME_BOX,
    ),
    seed: url.searchParams.has("seed")
      ? Number(url.searchParams.get("seed"))
      : undefined,
    demo: url.searchParams.has("demo")
      ? url.searchParams.get("demo") === "true"
      : undefined,
  });
  if (result.error) {
    const status = result.error.includes("must") ? 400 : 502;
    return NextResponse.json(result, { status });
  }
  return NextResponse.json(result);
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
  const result = await fetchSeasonEngineGameBoxes({
    homeTeam: body.homeTeam,
    awayTeam: body.awayTeam,
    week: body.week,
    season: body.season,
    nReplicates: body.nReplicates,
    seed: body.seed,
    demo: body.demo,
    includeDiagnostics: body.includeDiagnostics,
    injuryPaths: body.injuryPaths,
  });
  if (result.error) {
    const status = result.error.includes("must") ? 400 : 502;
    return NextResponse.json(result, { status });
  }
  return NextResponse.json(result);
}
