import { NextResponse } from "next/server";
import { fetchSeasonEngineSurvivorPlan } from "@/lib/nfl-season-engine";
import {
  duplicateSurvivorPlanTeams,
  NFL_INTERACTIVE_N_SURVIVOR_PATHS,
  slimInteractiveSurvivorPlan,
  type InjuryPathInput,
} from "@/lib/nfl-season-engine-format";
import {
  emptySurvivorPlanCacheKey,
  getEmptySurvivorPlan,
  setEmptySurvivorPlan,
} from "@/lib/nfl-survivor-empty-plan-cache";
import { UPSTREAM_TIMEOUT_MS } from "@/lib/upstream-fetch";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

function isEmptyPicks(picks: Record<string, string>): boolean {
  return Object.keys(picks).length === 0;
}

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

  const dupes = duplicateSurvivorPlanTeams(picks);
  if (dupes.length) {
    return NextResponse.json(
      {
        error: `Team ${dupes.join(", ")} locked in multiple weeks; survivor allows one use`,
        used_teams: Object.values(picks),
        locked_picks: picks,
        weeks: [],
      },
      { status: 400 },
    );
  }

  const nSims =
    typeof raw.nSims === "number"
      ? raw.nSims
      : typeof raw.n_sims === "number"
        ? raw.n_sims
        : NFL_INTERACTIVE_N_SURVIVOR_PATHS;
  const topN =
    typeof raw.topN === "number"
      ? raw.topN
      : typeof raw.top_n === "number"
        ? raw.top_n
        : undefined;
  const seed = typeof raw.seed === "number" ? raw.seed : 42;
  const season =
    typeof raw.season === "number"
      ? raw.season
      : typeof raw.season === "string"
        ? Number(raw.season)
        : 2026;
  const includeDiagnostics =
    typeof raw.includeDiagnostics === "boolean"
      ? raw.includeDiagnostics
      : typeof raw.include_diagnostics === "boolean"
        ? raw.include_diagnostics
        : false;
  const injuryPaths = Array.isArray(raw.injuryPaths)
    ? (raw.injuryPaths as InjuryPathInput[])
    : Array.isArray(raw.injury_paths)
      ? (raw.injury_paths as InjuryPathInput[])
      : undefined;

  const cacheKey =
    isEmptyPicks(picks) && !injuryPaths?.length
      ? emptySurvivorPlanCacheKey({
          season,
          nSims,
          seed,
          topN: topN ?? 32,
          includeDiagnostics,
        })
      : null;
  if (cacheKey) {
    const cached = getEmptySurvivorPlan(cacheKey);
    if (cached && typeof cached === "object") {
      return NextResponse.json(
        includeDiagnostics
          ? cached
          : slimInteractiveSurvivorPlan(cached as Record<string, unknown>),
      );
    }
  }

  const interactive = nSims <= 200;
  const result = await fetchSeasonEngineSurvivorPlan({
    picks,
    nSims,
    season,
    seed,
    demo: typeof raw.demo === "boolean" ? raw.demo : undefined,
    topN,
    injuryPaths,
    includeDiagnostics,
    timeoutMs: interactive
      ? UPSTREAM_TIMEOUT_MS.seasonEngineInteractive
      : UPSTREAM_TIMEOUT_MS.seasonEngine,
  });

  if (result.error) {
    const status = /bye|not scheduled|multiple weeks|Unknown team|Invalid/i.test(
      result.error,
    )
      ? 400
      : /timed out/i.test(result.error)
        ? 504
        : 502;
    const warming =
      status === 504
        ? {
            ...result,
            error:
              "Engine warming — survivor rankings timed out. Retry in a few seconds; this is not a blank hang.",
          }
        : result;
    return NextResponse.json(warming, { status });
  }
  const payload =
    includeDiagnostics
      ? result
      : slimInteractiveSurvivorPlan(result as unknown as Record<string, unknown>);
  if (cacheKey) setEmptySurvivorPlan(cacheKey, payload);
  return NextResponse.json(payload);
}
