/**
 * Single player-production SoT for public NFL pages.
 *
 * Spine = fantasy draft rankings (SUM weekly means + pack IR overlay +
 * yards↔TD recouple). Launch CSV is fallback only when the model service
 * is unreachable — never a second TD universe on the same page.
 */

import "server-only";

import { fetchNflFantasyDraftRankings } from "@/lib/nfl-fantasy-draft";
import {
  applySurfaceIntegrityToPlayerTotals,
  type SurfacePlayerTotals,
} from "@/lib/nfl-surface-integrity";
import {
  loadLatestNflPreseasonBundle2026,
  type PlayerProjectionTotalsRow,
} from "@/lib/nfl-preseason-artifacts";

export type PlayerSeasonTotalsSource = "spine-fantasy" | "csv-fallback";

export type PlayerSeasonTotalsBundle = {
  rows: PlayerProjectionTotalsRow[];
  source: PlayerSeasonTotalsSource;
  modelVersion: string | null;
  error?: string;
};

function draftRowToProjectionTotals(row: {
  season: number;
  playerId: string;
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
}): PlayerProjectionTotalsRow {
  return {
    season: row.season,
    playerKey: row.playerId,
    playerName: row.playerName,
    team: row.team,
    position: row.position,
    gamesProjected: row.gamesProjected,
    passYardsTotal: row.passYardsTotal,
    rushYardsTotal: row.rushYardsTotal,
    receivingYardsTotal: row.receivingYardsTotal,
    receptionsTotal: row.receptionsTotal,
    passTdsTotal: row.passTdsTotal,
    rushTdsTotal: row.rushTdsTotal,
    recTdsTotal: row.recTdsTotal,
    anytimeTdProbTotal: 0,
  };
}

/**
 * Prefer spine fantasy rankings (same numbers as /pro/nfl/fantasy).
 * CSV launch bundle is last-resort fallback only.
 */
export async function loadPlayerSeasonTotalsSpine(params?: {
  season?: number;
  limit?: number;
}): Promise<PlayerSeasonTotalsBundle> {
  const season = params?.season ?? 2026;
  const limit = params?.limit ?? 500;

  const draft = await fetchNflFantasyDraftRankings({
    season,
    scoringProfile: "half_ppr",
    limit,
  });

  if (!draft.error && draft.rows.length > 0) {
    // API already applied pack IR + TD recouple; do not re-rate from CSV.
    return {
      rows: draft.rows.map(draftRowToProjectionTotals),
      source: "spine-fantasy",
      modelVersion: draft.rows[0]?.modelVersion ?? "nfl-player-v1",
    };
  }

  const bundle = loadLatestNflPreseasonBundle2026();
  const csvRows = (bundle?.playerTotalsRegular ??
    []) as SurfacePlayerTotals[] as PlayerProjectionTotalsRow[];
  // Fallback still gets pack IR + yards↔TD so we never print illegal rows.
  // This path is last resort only — spine fantasy is the public SoT.
  const rows = applySurfaceIntegrityToPlayerTotals(csvRows, season, {
    recoupleTds: true,
  });
  return {
    rows,
    source: "csv-fallback",
    modelVersion: null,
    error: draft.error || "spine fantasy rankings empty",
  };
}
