import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { env } from "@/lib/config/env";

/**
 * Season actuals for the Projections Hub (Projected | Actual).
 *
 * Prefer live model-service `/nfl/ops/projection-actuals` (DB-backed).
 * Fall back to `data/ops/nfl-projection-actuals-YYYY.json` for static deploys.
 * Until REG weeks settle, every Actual cell is null → UI shows "—".
 */

export type TeamActuals = {
  wins: number | null;
  losses: number | null;
};

export type PlayerActuals = {
  passYards: number | null;
  rushYards: number | null;
  receivingYards: number | null;
  receptions: number | null;
  passTds: number | null;
  rushTds: number | null;
  recTds: number | null;
};

export type NflProjectionActualsBundle = {
  season: number;
  asOfUtc: string | null;
  source: string;
  teams: Record<string, TeamActuals>;
  players: Record<string, PlayerActuals>;
};

function emptyPlayer(): PlayerActuals {
  return {
    passYards: null,
    rushYards: null,
    receivingYards: null,
    receptions: null,
    passTds: null,
    rushTds: null,
    recTds: null,
  };
}

function emptyBundle(season: number): NflProjectionActualsBundle {
  return {
    season,
    asOfUtc: null,
    source: "empty_preseason_scaffold",
    teams: {},
    players: {},
  };
}

function findRepoRoot(): string | null {
  let current = process.cwd();
  for (let depth = 0; depth < 6; depth += 1) {
    if (existsSync(path.join(current, "data", "ops"))) return current;
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return null;
}

function normalizeBundle(
  season: number,
  parsed: Partial<NflProjectionActualsBundle> & Record<string, unknown>,
): NflProjectionActualsBundle {
  return {
    season,
    asOfUtc:
      typeof parsed.asOfUtc === "string"
        ? parsed.asOfUtc
        : parsed.asOfUtc === null
          ? null
          : null,
    source: typeof parsed.source === "string" ? parsed.source : "unknown",
    teams: (parsed.teams as Record<string, TeamActuals>) ?? {},
    players: (parsed.players as Record<string, PlayerActuals>) ?? {},
  };
}

function loadFromFile(season: number): NflProjectionActualsBundle | null {
  const repoRoot = findRepoRoot();
  if (!repoRoot) return null;
  const filePath = path.join(
    repoRoot,
    "data",
    "ops",
    `nfl-projection-actuals-${season}.json`,
  );
  if (!existsSync(filePath)) return null;
  try {
    const parsed = JSON.parse(readFileSync(filePath, "utf8")) as Partial<
      NflProjectionActualsBundle
    > &
      Record<string, unknown>;
    return normalizeBundle(season, parsed);
  } catch {
    return null;
  }
}

async function loadFromModelService(
  season: number,
): Promise<NflProjectionActualsBundle | null> {
  const base = env.MODEL_SERVICE_URL;
  if (!base) return null;
  const url = new URL(
    `${base.replace(/\/+$/, "")}/nfl/ops/projection-actuals`,
  );
  url.searchParams.set("season", String(season));
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(url.toString(), {
      cache: "no-store",
      signal: controller.signal,
      headers: {
        accept: "application/json",
        ...(env.INTERNAL_API_SECRET
          ? { "x-kosedge-secret": env.INTERNAL_API_SECRET }
          : {}),
      },
    });
    if (!response.ok) return null;
    const parsed = (await response.json()) as Partial<NflProjectionActualsBundle> &
      Record<string, unknown>;
    const bundle = normalizeBundle(season, parsed);
    // Treat empty scaffold from API as usable (preseason).
    return bundle;
  } catch {
    return null;
  } finally {
    clearTimeout(timeout);
  }
}

/** Sync file/scaffold load (tests / fallback). */
export function loadNflProjectionActuals(
  season = 2026,
): NflProjectionActualsBundle {
  return loadFromFile(season) ?? emptyBundle(season);
}

/** Prefer live DB actuals via model-service; fall back to ops JSON file. */
export async function loadNflProjectionActualsAsync(
  season = 2026,
): Promise<NflProjectionActualsBundle> {
  const live = await loadFromModelService(season);
  if (live) return live;
  return loadNflProjectionActuals(season);
}

export function teamActualWins(
  bundle: NflProjectionActualsBundle,
  team: string,
): number | null {
  return bundle.teams[team]?.wins ?? null;
}

export function playerActualsFor(
  bundle: NflProjectionActualsBundle,
  playerKey: string,
): PlayerActuals {
  return bundle.players[playerKey] ?? emptyPlayer();
}

export function formatActual(
  value: number | null | undefined,
  digits = 0,
): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return digits > 0 ? value.toFixed(digits) : String(Math.round(value));
}

/** Compact "200 / —" style for Projected | Actual cells. */
export function formatProjectedActual(
  projected: number,
  actual: number | null | undefined,
  digits = 0,
): { projected: string; actual: string } {
  const p =
    digits > 0 ? projected.toFixed(digits) : String(Math.round(projected));
  return { projected: p, actual: formatActual(actual, digits) };
}
