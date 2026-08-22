import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

import type { EnrichableDraftRow } from "@/lib/fantasy/enrich";
import type { FantasyScoringProfile } from "@/lib/fantasy/types";

export type NflKdstKickerRow = {
  player_id?: string;
  player_name?: string;
  team?: string;
  fg_attempts?: number;
  xp_attempts?: number;
  fantasy_points?: number;
};

export type NflKdstDstRow = {
  team?: string;
  points_allowed_mean?: number;
  sacks?: number;
  fantasy_points?: number;
};

export type NflKdstArtifact = {
  season?: number;
  source?: string;
  kickers?: NflKdstKickerRow[];
  dst?: NflKdstDstRow[];
  gaps?: string[];
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

export function loadNflKdstPublishArtifact(
  season = 2026,
): NflKdstArtifact | null {
  const repoRoot = findRepoRoot();
  if (!repoRoot) return null;
  const artifactPath = path.join(
    repoRoot,
    "data",
    "ops",
    "artifacts",
    `nfl-kdst-season-${season}.json`,
  );
  if (!existsSync(artifactPath)) return null;
  try {
    const raw = JSON.parse(readFileSync(artifactPath, "utf8")) as NflKdstArtifact;
    if (raw.season != null && Number(raw.season) !== Number(season)) return null;
    return raw;
  } catch {
    return null;
  }
}

function asRow(input: {
  season: number;
  scoringProfile: FantasyScoringProfile;
  playerId: string;
  playerName: string;
  team: string;
  position: "K" | "DST";
  totalPoints: number;
}): EnrichableDraftRow {
  return {
    season: input.season,
    scoringProfile: input.scoringProfile,
    modelVersion: "nfl-kdst-publish",
    playerId: input.playerId,
    playerUid: null,
    playerName: input.playerName,
    team: input.team,
    position: input.position,
    gamesProjected: 17,
    passYardsTotal: 0,
    rushYardsTotal: 0,
    receivingYardsTotal: 0,
    receptionsTotal: 0,
    passTdsTotal: 0,
    rushTdsTotal: 0,
    recTdsTotal: 0,
    totalPoints: input.totalPoints,
    floorPoints: null,
    medianPoints: null,
    ceilingPoints: null,
    replacementPoints: 0,
    valueOverReplacement: 0,
    rankOverall: 0,
    rankPosition: 0,
    tier: "bench",
    isRookie: false,
    rookieYear: null,
    draftNumber: null,
    updatedAt: null,
    source: "preseason-fallback",
  };
}

/** Named K/DST rows from the publish artifact. Empty if the file is missing. */
export function kdstEnrichableFromArtifact(input: {
  season: number;
  scoringProfile: FantasyScoringProfile;
}): EnrichableDraftRow[] {
  const art = loadNflKdstPublishArtifact(input.season);
  if (!art) return [];
  const rows: EnrichableDraftRow[] = [];
  for (const kicker of art.kickers ?? []) {
    const team = String(kicker.team || "").trim().toUpperCase();
    const playerId = String(kicker.player_id || "").trim();
    const pts = Number(kicker.fantasy_points);
    if (!team || !playerId || !Number.isFinite(pts)) continue;
    rows.push(
      asRow({
        season: input.season,
        scoringProfile: input.scoringProfile,
        playerId,
        playerName: String(kicker.player_name || playerId),
        team: team === "LA" ? "LAR" : team,
        position: "K",
        totalPoints: pts,
      }),
    );
  }
  for (const dst of art.dst ?? []) {
    const teamRaw = String(dst.team || "").trim().toUpperCase();
    const team = teamRaw === "LA" ? "LAR" : teamRaw;
    const pts = Number(dst.fantasy_points);
    if (!team || !Number.isFinite(pts)) continue;
    rows.push(
      asRow({
        season: input.season,
        scoringProfile: input.scoringProfile,
        playerId: `${team}:DST`,
        playerName: `${team} DST`,
        team,
        position: "DST",
        totalPoints: pts,
      }),
    );
  }
  return rows;
}

export function boardHasKd(
  rows: Array<{ position?: string | null }>,
): boolean {
  return rows.some((row) =>
    ["K", "DST"].includes(String(row.position || "").toUpperCase()),
  );
}
