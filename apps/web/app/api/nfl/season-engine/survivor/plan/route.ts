import { NextResponse } from "next/server";
import { fetchSeasonEngineSurvivorPlan } from "@/lib/nfl-season-engine";
import type { InjuryPathInput } from "@/lib/nfl-season-engine-format";

export const dynamic = "force-dynamic";
export const maxDuration = 180;

export async function POST(req: Request) {
  let raw: Record<string, unknown> = {};
  try {
    raw = (await req.json()) as Record<string, unknown>;
  } catch {
    raw = {};
  }

  const picksRaw = raw.picks;
  const picks =
    picksRaw && typeof picksRaw === "object" && !Array.isArray(picksRaw)
      ? (picksRaw as Record<string, string>)
      : {};

  const result = await fetchSeasonEngineSurvivorPlan({
    picks,
    nSims:
      typeof raw.nSims === "number"
        ? raw.nSims
        : typeof raw.n_sims === "number"
          ? raw.n_sims
          : undefined,
    season:
      typeof raw.season === "number"
        ? raw.season
        : typeof raw.season === "string"
          ? Number(raw.season)
          : undefined,
    seed: typeof raw.seed === "number" ? raw.seed : undefined,
    demo: typeof raw.demo === "boolean" ? raw.demo : undefined,
    topN:
      typeof raw.topN === "number"
        ? raw.topN
        : typeof raw.top_n === "number"
          ? raw.top_n
          : undefined,
    injuryPaths: Array.isArray(raw.injuryPaths)
      ? (raw.injuryPaths as InjuryPathInput[])
      : Array.isArray(raw.injury_paths)
        ? (raw.injury_paths as InjuryPathInput[])
        : undefined,
    includeDiagnostics:
      typeof raw.includeDiagnostics === "boolean"
        ? raw.includeDiagnostics
        : typeof raw.include_diagnostics === "boolean"
          ? raw.include_diagnostics
          : undefined,
  });

  if (result.error) {
    const status = /bye|not scheduled|multiple weeks|Unknown team|Invalid/i.test(
      result.error,
    )
      ? 400
      : 502;
    return NextResponse.json(result, { status });
  }
  return NextResponse.json(result);
}
