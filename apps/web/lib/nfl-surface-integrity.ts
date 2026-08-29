/**
 * NFL surface integrity — yards↔TD rates + pack IR overlay for launch CSV.
 * Mirrors model-service `nfl_surface_integrity.py` constants.
 *
 * When the player-production spine (fantasy draft rankings) is available,
 * pages should use that SoT and skip CSV TD recouple — CSV yards mint a
 * second universe.
 */

import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

export const PASS_TD_YARDS_PER = 115;
export const REC_TD_YARDS_PER = 100;

/** Minimal player totals shape (avoids circular import with artifacts). */
export type SurfacePlayerTotals = {
  season: number;
  playerKey: string;
  playerName: string;
  team: string;
  position: string;
  gamesProjected: number;
  passYardsTotal: number;
  rushYardsTotal: number;
  receivingYardsTotal: number;
  receptionsTotal: number;
  passTdsTotal: number;
  rushTdsTotal: number;
  recTdsTotal: number;
  anytimeTdProbTotal: number;
};

const HARD_OUT = new Set([
  "out",
  "ir",
  "pup",
  "suspended",
  "inactive",
  "waived",
]);

function normalizeName(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "")
    .replace(/jr$|sr$|ii$|iii$|iv$/, "");
}

type PackInjuryRow = {
  team: string;
  playerName: string;
  playerId?: string;
  injuryStatus?: string;
};

function findRepoRoot(): string | null {
  let current = process.cwd();
  for (let depth = 0; depth < 6; depth += 1) {
    const dataOps = path.join(current, "data", "ops");
    if (existsSync(dataOps)) return current;
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return null;
}

export function loadPackInjuryRows(season = 2026): PackInjuryRow[] {
  try {
    const root = findRepoRoot();
    if (!root) return [];
    const depthPath = path.join(
      root,
      "services/model-service/src/services/nfl_season_engine/data",
      `nfl_depth_chart_${season}_w1.json`,
    );
    if (!existsSync(depthPath)) return [];
    const parsed = JSON.parse(readFileSync(depthPath, "utf8")) as {
      rows?: Array<{
        team?: string;
        player_name?: string;
        player_id?: string;
        injury_status?: string;
      }>;
    };
    return (parsed.rows ?? []).map((row) => ({
      team: String(row.team ?? "").toUpperCase(),
      playerName: String(row.player_name ?? ""),
      playerId: row.player_id ? String(row.player_id) : undefined,
      injuryStatus: row.injury_status
        ? String(row.injury_status).trim().toLowerCase()
        : undefined,
    }));
  } catch {
    return [];
  }
}

export function recouplePlayerTdsToYards<T extends SurfacePlayerTotals>(
  row: T,
): T {
  const passTds =
    row.passYardsTotal > 1
      ? row.passYardsTotal / PASS_TD_YARDS_PER
      : row.passTdsTotal;
  const recTds =
    row.receivingYardsTotal > 1
      ? row.receivingYardsTotal / REC_TD_YARDS_PER
      : 0;
  return {
    ...row,
    passTdsTotal: passTds,
    recTdsTotal: recTds,
  };
}

/**
 * Pack IR always applied. TD recouple is for CSV-fallback honesty only —
 * spine fantasy pages must not re-rate from CSV yards.
 */
export function applySurfaceIntegrityToPlayerTotals<
  T extends SurfacePlayerTotals,
>(rows: T[], season = 2026, opts?: { recoupleTds?: boolean }): T[] {
  const recoupleTds = opts?.recoupleTds !== false;
  const pack = loadPackInjuryRows(season);
  const byId = new Map<string, PackInjuryRow>();
  const byName = new Map<string, PackInjuryRow>();
  for (const row of pack) {
    if (row.playerId) byId.set(`${row.team}:${row.playerId}`, row);
    byName.set(`${row.team}:${normalizeName(row.playerName)}`, row);
  }

  return rows.map((row) => {
    const team = row.team.toUpperCase();
    const packHit =
      byId.get(`${team}:${row.playerKey}`) ||
      byName.get(`${team}:${normalizeName(row.playerName)}`);
    const status = String(packHit?.injuryStatus || "")
      .trim()
      .toLowerCase();
    if (HARD_OUT.has(status)) {
      return {
        ...row,
        gamesProjected: 0,
        passYardsTotal: 0,
        rushYardsTotal: 0,
        receivingYardsTotal: 0,
        receptionsTotal: 0,
        passTdsTotal: 0,
        rushTdsTotal: 0,
        recTdsTotal: 0,
        anytimeTdProbTotal: 0,
      };
    }
    return recoupleTds ? recouplePlayerTdsToYards(row) : row;
  });
}
