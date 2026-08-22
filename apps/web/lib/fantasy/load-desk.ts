import "server-only";

import {
  fetchFantasyProsAdpBundle,
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
import {
  boardHasKd,
  kdstEnrichableFromArtifact,
} from "@/lib/nfl-kdst-artifact";
import { loadLatestNflPreseasonBundle2026, loadNflWebLaunchPointer } from "@/lib/nfl-preseason-artifacts";

const LIMITATIONS_BASE = [
  "Model rank is projection order, not recommended pick order. Sort is raw KosEdge points (Half-PPR default). ADP and Value Δ are the market comparison — unmatched ADP never invents a Δ.",
  "Draft advice (Builder suggestions + Mock on-the-clock + CPU) is ADP-aware: need + VOR − reach penalty when you would take a player before ADP. Same projections; different action scoring. Not an optimal-pick claim.",
  "Floor–med–ceiling from model quantiles when present; else a band around median.",
  "Schedule softness: W1–6 vs W14–17 opponent expected wins — not a full matchup sim.",
  "No live injury feed. Builder is a private roster; Mock fills other seats (no league sync).",
  "Snake 1QB redraft only — no auction, Superflex, or dynasty.",
  "|modelRank − ADP| ≥ 8 with high ADP-match confidence is flagged High deviation as a data/role warning — not a bet slip.",
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

  const pointer = loadNflWebLaunchPointer();
  const lockBit = pointer?.lock_tag
    ? ` · pin ${pointer.lock_tag}`
    : "";
  const when = pointer?.generated_at_utc?.slice(0, 10);
  const dateBit = when ? ` · ${when}` : "";
  return {
    rows,
    limitations: [
      ...LIMITATIONS_BASE,
      bundle.nTeamSims && bundle.nTeamSims >= 50000
        ? `Launch-current research (${bundle.nTeamSims.toLocaleString()} team paths${lockBit}${dateBit} · ${bundle.bundleDirName}).`
        : `Preseason board from season-engine sim (${bundle.bundleDirName}${lockBit}${dateBit}).`,
    ],
  };
}

function mergeKdstIfMissing(
  rows: EnrichableDraftRow[],
  input: {
    season: number;
    scoringProfile: FantasyScoringProfile;
    position?: string;
  },
): { rows: EnrichableDraftRow[]; note: string | null } {
  const pos = input.position?.toUpperCase();
  if (pos && pos !== "K" && pos !== "DST") {
    return { rows, note: null };
  }
  if (boardHasKd(rows)) {
    return { rows, note: null };
  }
  const extra = kdstEnrichableFromArtifact(input).filter((row) =>
    pos ? row.position === pos : true,
  );
  if (!extra.length) {
    return {
      rows,
      note: "K/DST artifact missing or unscoreable — desk stays skill-only until remat.",
    };
  }
  const ranked = rankSeasonFantasyPlayers(
    [...rows, ...extra].map((row) => ({ ...row, playerKey: row.playerId })),
  );
  const merged = ranked.map(
    ({
      playerKey: _playerKey,
      rankOverall,
      rankPosition,
      tier,
      replacementPoints,
      valueOverReplacement,
      ...rest
    }) => ({
      ...rest,
      rankOverall,
      rankPosition,
      tier,
      replacementPoints,
      valueOverReplacement,
    }),
  );
  const kickers = extra.filter((row) => row.position === "K").length;
  const dst = extra.filter((row) => row.position === "DST").length;
  return {
    rows: merged,
    note: `K/DST merged from nfl_kdst_publish (${kickers} K / ${dst} DST).`,
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

  const [api, adpBundle] = await Promise.all([
    fetchNflFantasyDraftRankings({
      season,
      scoringProfile,
      position: params.position,
      rookiesOnly: params.rookiesOnly,
      limit,
    }),
    fetchFantasyProsAdpBundle({ season, scoringProfile }),
  ]);
  const adpFeed = adpBundle.primary;

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
  } else {
    limitations = [
      ...LIMITATIONS_BASE,
      "Season ranks = SUM of weekly spine means, cap 17 games (Phase 3 contract). Not the preseason launch bundle.",
    ];
    if (season === 2026) {
      limitations.push(
        "2026 preseason gap is elevated (team receiving ≫ QB pass, ~0.42 vs ~0.10 on 2025 3C). Rankings are honest SUM spine, not a 3C-tight receiving board.",
      );
    }
    const games = enrichable.map((row) => Number(row.gamesProjected) || 0);
    const medianGames =
      games.length === 0
        ? 0
        : [...games].sort((a, b) => a - b)[Math.floor(games.length / 2)];
    if (medianGames > 0 && medianGames < 14) {
      limitations.push(
        `Research limit: 2026 schedule/depth still thin — median games projected ${medianGames} (full season is 17).`,
      );
    }
  }

  const kdMerge = mergeKdstIfMissing(enrichable, {
    season,
    scoringProfile,
    position: params.position,
  });
  enrichable = kdMerge.rows;
  if (kdMerge.note) {
    limitations = [...limitations, kdMerge.note];
  }

  const adpMatch = matchAdpToDeskRows(
    enrichable.map((row) => ({
      playerId: row.playerId,
      playerUid: row.playerUid,
      playerName: row.playerName,
      team: row.team,
      position: row.position,
      rankOverall: row.rankOverall,
    })),
    adpFeed.players,
    {
      secondaryPools: adpBundle.secondary,
      logUnmatched: true,
    },
  );

  const rows = enrichDraftRows({
    rows: enrichable,
    scheduleByTeam,
    depthRows,
    adpByPlayerId: adpMatch.byPlayerId,
  });

  const unmatchedPreview = adpMatch.unmatchedRows
    .slice(0, 12)
    .map(
      (row) =>
        `${row.playerName} (${row.team} ${row.position}${
          row.rankOverall != null ? ` #${row.rankOverall}` : ""
        })`,
    )
    .join("; ");

  limitations = [
    ...limitations,
    ...adpFeed.limitations,
    `ADP match coverage: ${adpMatch.matched}/${enrichable.length} linked (${adpMatch.matchedHigh} same-format high-confidence for Value Δ; ${adpMatch.matchedCrossFormat} cross-format ADP display only; ${adpMatch.unmatched} unmatched → —).`,
    "Matching uses deterministic rules (ids, suffix-stripped names, short names, initial+last, unique team/pos keys, then team-agnostic unique keys for roster moves). No fuzzy edit-distance guesses.",
    ...(unmatchedPreview
      ? [`Unmatched sample: ${unmatchedPreview}${adpMatch.unmatched > 12 ? "…" : ""}`]
      : []),
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
    adpMatchedHighCount: adpMatch.matchedHigh,
    adpMatchedCrossFormatCount: adpMatch.matchedCrossFormat,
    adpUnmatched: adpMatch.unmatchedRows,
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
