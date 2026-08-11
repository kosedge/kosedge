import { NextResponse } from "next/server";
import { fetchSeasonEngineSurvivor } from "@/lib/nfl-season-engine";
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

  const week =
    typeof raw.week === "number"
      ? raw.week
      : typeof raw.week === "string"
        ? Number(raw.week)
        : NaN;
  if (!Number.isFinite(week)) {
    return NextResponse.json({ error: "week is required" }, { status: 400 });
  }

  const alreadyUsed =
    typeof raw.alreadyUsed === "string" || Array.isArray(raw.alreadyUsed)
      ? (raw.alreadyUsed as string | string[])
      : typeof raw.already_used === "string" || Array.isArray(raw.already_used)
        ? (raw.already_used as string | string[])
        : [];

  const result = await fetchSeasonEngineSurvivor({
    week,
    alreadyUsed,
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
    return NextResponse.json(result, { status: 502 });
  }
  return NextResponse.json(result);
}
