import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

/**
 * Season actuals for the Projections Hub (Projected | Actual).
 *
 * Until REG weeks settle, every Actual cell is null → UI shows "—".
 * Weekly updater: drop `data/ops/nfl-projection-actuals-YYYY.json`.
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

/** Load actuals for a season. Empty scaffold until weekly file exists. */
export function loadNflProjectionActuals(
  season = 2026,
): NflProjectionActualsBundle {
  const repoRoot = findRepoRoot();
  if (repoRoot) {
    const filePath = path.join(
      repoRoot,
      "data",
      "ops",
      `nfl-projection-actuals-${season}.json`,
    );
    if (existsSync(filePath)) {
      try {
        const parsed = JSON.parse(readFileSync(filePath, "utf8")) as Partial<
          NflProjectionActualsBundle
        >;
        return {
          season,
          asOfUtc: parsed.asOfUtc ?? null,
          source: parsed.source ?? filePath,
          teams: parsed.teams ?? {},
          players: parsed.players ?? {},
        };
      } catch {
        // fall through
      }
    }
  }
  return {
    season,
    asOfUtc: null,
    source: "empty_preseason_scaffold",
    teams: {},
    players: {},
  };
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
