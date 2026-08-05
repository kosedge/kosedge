import "server-only";

import {
  fetchFantasyProsAdpFeed,
  formatAdpFreshness,
} from "@/lib/fantasy/adp-fantasypros";
import { matchAdpToDeskRows } from "@/lib/fantasy/adp-match";
import {
  enrichDraftRows,
  type EnrichableDraftRow,
} from "@/lib/fantasy/enrich";
import { loadNfl2026DepthRows, loadNfl2026ScheduleGames } from "@/lib/fantasy/load-schedule";
import { fantasyPointsFromBox } from "@/lib/fantasy/scoring";
import {
  buildTeamScheduleNotes,
} from "@/lib/fantasy/schedule-context";
import type {
  FantasyDeskBoard,
  FantasyScoringProfile,
} from "@/lib/fantasy/types";
import { rankSeasonFantasyPlayers } from "@/lib/fantasy/vor-rank";
import {
  fetchNflFantasyDraftRankings,
  type NflFantasyDraftRankingRow,
} from "@/lib/nfl-fantasy-draft";
import { loadLatestNflPreseasonBundle2026 } from "@/lib/nfl-preseason-artifacts";

const LIMITATIONS_BASE = [
  "Rankings convert season-engine / projection-baseline box-score totals into fantasy points by format (Standard / Half-PPR / PPR).",
  "Floor / median / ceiling use distribution quantiles when the model service provides them; otherwise a position-aware uncertainty band around the median.",
  "Schedule notes compare opponent expected wins in weeks 1–6 vs fantasy playoff weeks 14–17 — a simple softness signal, not full matchup sim.",
  "Risk flags are concise signals from depth chart + projection shape; there is no live injury feed on this desk yet.",
  "Phase 1 team builder is manual (no multi-team CPU mock room).",
];

function apiRowToEnrichable(row: NflFantasyDraftRankingRow & {
  floorPoints?: number | null;
  medianPoints?: number | null;
  ceilingPoints?: number | null;
}): EnrichableDraftRow {
  return {
    season: row.season,
    scoringProfile: row.scoringProfile,
    modelVersion: row.modelVersion,
    playerId: row.playerId,
    playerUid: row.playerUid,
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
    totalPoints: row.totalPoints,
    floorPoints: row.floorPoints ?? null,
    medianPoints: row.medianPoints ?? null,
    ceilingPoints: row.ceilingPoints ?? null,
    replacementPoints: row.replacementPoints,
    valueOverReplacement: row.valueOverReplacement,
    rankOverall: row.rankOverall,
    rankPosition: row.rankPosition,
    tier: row.tier,
    isRookie: row.isRookie,
    rookieYear: row.rookieYear,
    draftNumber: row.draftNumber,
    updatedAt: row.updatedAt,
    source: "model-service" as const,
  };
}

function buildFallbackBoard(input: {
  season: number;
  scoringProfile: FantasyScoringProfile;
  position?: string;
  rookiesOnly?: boolean;
  limit: number;
}): {
  rows: EnrichableDraftRow[];
  limitations: string[];
} | null {
  const bundle = loadLatestNflPreseasonBundle2026();
  if (!bundle?.playerTotalsRegular?.length) return null;

  const scored = bundle.playerTotalsRegular
    .filter((p) => ["QB", "RB", "WR", "TE"].includes(p.position.toUpperCase()))
    .map((p) => {
      const totalPoints = fantasyPointsFromBox({
        scoringProfile: input.scoringProfile,
        passYards: p.passYardsTotal,
        passTds: p.passTdsTotal,
        rushYards: p.rushYardsTotal,
        rushTds: p.rushTdsTotal,
        receivingYards: p.receivingYardsTotal,
        receptions: p.receptionsTotal,
        recTds: p.recTdsTotal,
      });
      return {
        playerKey: p.playerKey || `${p.team}:${p.playerName}`,
        position: p.position.toUpperCase(),
        totalPoints,
        season: p.season || input.season,
        playerName: p.playerName,
        team: p.team,
        gamesProjected: p.gamesProjected,
        passYardsTotal: p.passYardsTotal,
        rushYardsTotal: p.rushYardsTotal,
        receivingYardsTotal: p.receivingYardsTotal,
        receptionsTotal: p.receptionsTotal,
        passTdsTotal: p.passTdsTotal,
        rushTdsTotal: p.rushTdsTotal,
        recTdsTotal: p.recTdsTotal,
      };
    });

  const ranked = rankSeasonFantasyPlayers(scored);
  let rows = ranked.map((player) => ({
    season: input.season,
    scoringProfile: input.scoringProfile,
    modelVersion: "preseason-bundle-fallback",
    playerId: String(player.playerKey),
    playerUid: null,
    playerName: String(player.playerName),
    team: String(player.team),
    position: String(player.position),
    gamesProjected: Number(player.gamesProjected) || 0,
    passYardsTotal: Number(player.passYardsTotal) || 0,
    rushYardsTotal: Number(player.rushYardsTotal) || 0,
    receivingYardsTotal: Number(player.receivingYardsTotal) || 0,
    receptionsTotal: Number(player.receptionsTotal) || 0,
    passTdsTotal: Number(player.passTdsTotal) || 0,
    rushTdsTotal: Number(player.rushTdsTotal) || 0,
    recTdsTotal: Number(player.recTdsTotal) || 0,
    totalPoints: Number(player.totalPoints) || 0,
    floorPoints: null,
    medianPoints: null,
    ceilingPoints: null,
    replacementPoints: player.replacementPoints,
    valueOverReplacement: player.valueOverReplacement,
    rankOverall: player.rankOverall,
    rankPosition: player.rankPosition,
    tier: player.tier,
    isRookie: false,
    rookieYear: null,
    draftNumber: null,
    updatedAt: bundle.generatedAtUtc,
    source: "preseason-fallback" as const,
  }));

  if (input.position) {
    rows = rows.filter(
      (r) => r.position.toUpperCase() === input.position!.toUpperCase(),
    );
  }
  if (input.rookiesOnly) {
    rows = rows.filter((r) => r.isRookie);
  }
  rows = rows.slice(0, input.limit);

  return {
    rows,
    limitations: [
      ...LIMITATIONS_BASE,
      `Live draft-rankings API empty/unreachable — board built from preseason sim bundle ${bundle.bundleDirName} (skill positions only; K/DST omitted).`,
    ],
  };
}

export async function loadFantasyDraftDesk(params: {
  season?: number;
  scoringProfile?: FantasyScoringProfile;
  position?: string;
  rookiesOnly?: boolean;
  limit?: number;
}): Promise<FantasyDeskBoard> {
  const season = params.season ?? 2026;
  const scoringProfile = params.scoringProfile ?? "half_ppr";
  const limit = params.limit ?? 200;

  const [api, adpFeed] = await Promise.all([
    fetchNflFantasyDraftRankings({
      season,
      scoringProfile,
      position: params.position,
      rookiesOnly: params.rookiesOnly,
      limit,
    }),
    fetchFantasyProsAdpFeed({ season, scoringProfile }),
  ]);

  const scheduleGames = loadNfl2026ScheduleGames();
  const depthRows = loadNfl2026DepthRows();
  const bundle = loadLatestNflPreseasonBundle2026();
  const scheduleByTeam = buildTeamScheduleNotes(
    scheduleGames,
    (bundle?.teamRows ?? []).map((t) => ({
      team: t.team,
      expectedWins: t.expectedWins,
    })),
  );

  let enrichable: EnrichableDraftRow[] = api.rows.map((row) =>
    apiRowToEnrichable(row),
  );
  let source: FantasyDeskBoard["source"] = "model-service";
  let limitations = [...LIMITATIONS_BASE];
  let error = api.error;

  if (enrichable.length === 0) {
    const fallback = buildFallbackBoard({
      season,
      scoringProfile,
      position: params.position,
      rookiesOnly: params.rookiesOnly,
      limit,
    });
    if (fallback) {
      enrichable = fallback.rows;
      source = "preseason-fallback";
      limitations = fallback.limitations;
      error = undefined;
    } else {
      source = "empty";
    }
  }

  const adpMatch = matchAdpToDeskRows(
    enrichable.map((row) => ({
      playerId: row.playerId,
      playerUid: row.playerUid,
      playerName: row.playerName,
      team: row.team,
      position: row.position,
    })),
    adpFeed.players,
  );

  const rows = enrichDraftRows({
    rows: enrichable,
    scheduleByTeam,
    depthRows,
    adpByPlayerId: adpMatch.byPlayerId,
  });

  limitations = [
    ...limitations,
    ...adpFeed.limitations,
    `ADP match coverage: ${adpMatch.matched}/${enrichable.length} desk rows linked to FantasyPros (${adpMatch.unmatched} unmatched → ADP shown as —).`,
  ];

  const adpOrigin =
    adpFeed.players.length === 0
      ? ("none" as const)
      : adpFeed.origin;

  return {
    season,
    scoringProfile,
    count: rows.length,
    rows,
    source,
    adpSourceLabel: adpFeed.sourceLabel,
    adpFreshnessLabel: formatAdpFreshness(adpFeed),
    adpOrigin,
    adpMatchedCount: adpMatch.matched,
    limitations,
    error,
    slateStatus: api.slateStatus,
  };
}

export function findDeskPlayer(
  board: FantasyDeskBoard,
  playerId: string,
): FantasyDeskBoard["rows"][number] | undefined {
  const needle = decodeURIComponent(playerId);
  return board.rows.find(
    (row) =>
      row.playerId === needle ||
      row.playerId === playerId ||
      `${row.team}:${row.playerName}` === needle,
  );
}
