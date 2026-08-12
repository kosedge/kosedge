import { valueDelta } from "@/lib/fantasy/adp-proxy";
import {
  isHighConfidenceAdp,
  type AdpMatchResult,
} from "@/lib/fantasy/adp-match";
import { resolveAdpQaFlag } from "@/lib/fantasy/adp-qa-flags";
import { buildDrivers, buildExpertBlurb } from "@/lib/fantasy/expert";
import { buildRiskFlags, type DepthRow } from "@/lib/fantasy/risk-signals";
import {
  floorMedianCeilingFromMean,
} from "@/lib/fantasy/scoring";
import { NEUTRAL_SCHEDULE } from "@/lib/fantasy/schedule-context";
import type {
  FantasyDeskRow,
  FantasyScoringProfile,
  ScheduleWindowNote,
} from "@/lib/fantasy/types";

export type EnrichableDraftRow = {
  season: number;
  scoringProfile: FantasyScoringProfile;
  modelVersion: string;
  playerId: string;
  playerUid: string | null;
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
  totalPoints: number;
  floorPoints?: number | null;
  medianPoints?: number | null;
  ceilingPoints?: number | null;
  replacementPoints: number;
  valueOverReplacement: number;
  rankOverall: number;
  rankPosition: number;
  tier: string;
  isRookie: boolean;
  rookieYear: number | null;
  draftNumber: number | null;
  updatedAt: string | null;
  source: "model-service" | "preseason-fallback";
};

export function enrichDraftRows(input: {
  rows: EnrichableDraftRow[];
  scheduleByTeam: Map<string, ScheduleWindowNote>;
  depthRows: DepthRow[];
  /** Real market ADP by desk playerId. Missing → null ADP / value. */
  adpByPlayerId?: Map<string, AdpMatchResult>;
}): FantasyDeskRow[] {
  const rushByTeam = new Map<string, Array<{ playerName: string; rushYards: number }>>();
  for (const row of input.rows) {
    if (row.position.toUpperCase() !== "RB") continue;
    const list = rushByTeam.get(row.team.toUpperCase()) ?? [];
    list.push({ playerName: row.playerName, rushYards: row.rushYardsTotal });
    rushByTeam.set(row.team.toUpperCase(), list);
  }

  const adpByPlayerId = input.adpByPlayerId ?? new Map();

  return input.rows.map((row) => {
    const committeeProbe = buildRiskFlags({
      playerName: row.playerName,
      team: row.team,
      position: row.position,
      isRookie: row.isRookie,
      gamesProjected: row.gamesProjected,
      rushYardsTotal: row.rushYardsTotal,
      depthRows: input.depthRows,
      teammateRushYards: rushByTeam.get(row.team.toUpperCase()) ?? [],
    });
    const hasCommittee = committeeProbe.some((f) => f.kind === "committee");

    const hasQuantiles =
      row.floorPoints != null &&
      row.medianPoints != null &&
      row.ceilingPoints != null &&
      Number.isFinite(row.floorPoints) &&
      Number.isFinite(row.medianPoints) &&
      Number.isFinite(row.ceilingPoints);

    const band = hasQuantiles
      ? {
          floorPoints: Number(row.floorPoints),
          medianPoints: Number(row.medianPoints),
          ceilingPoints: Number(row.ceilingPoints),
        }
      : floorMedianCeilingFromMean({
          medianPoints: row.totalPoints,
          position: row.position,
          isRookie: row.isRookie,
          committeeRisk: hasCommittee,
        });

    const adpHit = adpByPlayerId.get(row.playerId);
    const adp = adpHit?.adp ?? null;
    // Value Δ only for high-confidence (same-format) matches — no weak clutter.
    const delta =
      adp != null && isHighConfidenceAdp(adpHit)
        ? valueDelta(row.rankOverall, adp)
        : null;
    const schedule =
      input.scheduleByTeam.get(row.team.toUpperCase()) ?? NEUTRAL_SCHEDULE;
    const riskFlags = committeeProbe;
    const drivers = buildDrivers({
      position: row.position,
      team: row.team,
      passYardsTotal: row.passYardsTotal,
      rushYardsTotal: row.rushYardsTotal,
      receivingYardsTotal: row.receivingYardsTotal,
      receptionsTotal: row.receptionsTotal,
      passTdsTotal: row.passTdsTotal,
      rushTdsTotal: row.rushTdsTotal,
      recTdsTotal: row.recTdsTotal,
      valueOverReplacement: row.valueOverReplacement,
      tier: row.tier,
      gamesProjected: row.gamesProjected,
      rankPosition: row.rankPosition,
    });
    const expertBlurb = buildExpertBlurb({
      playerName: row.playerName,
      team: row.team,
      position: row.position,
      rankOverall: row.rankOverall,
      rankPosition: row.rankPosition,
      adp,
      valueDelta: delta,
      tier: row.tier,
      floorPoints: band.floorPoints,
      medianPoints: band.medianPoints,
      ceilingPoints: band.ceilingPoints,
      schedule,
      riskFlags,
      drivers,
      source: row.source,
    });
    const adpQaFlag = resolveAdpQaFlag({
      position: row.position,
      rankPosition: row.rankPosition,
      rankOverall: row.rankOverall,
      tier: row.tier,
      team: row.team,
      gamesProjected: row.gamesProjected,
      passYardsTotal: row.passYardsTotal,
      rushYardsTotal: row.rushYardsTotal,
      receivingYardsTotal: row.receivingYardsTotal,
      receptionsTotal: row.receptionsTotal,
      valueOverReplacement: row.valueOverReplacement,
      adp,
      valueDelta: delta,
      existingDrivers: drivers,
      riskFlags,
      schedule,
      source: row.source,
    });

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
      floorPoints: band.floorPoints,
      medianPoints: band.medianPoints,
      ceilingPoints: band.ceilingPoints,
      replacementPoints: row.replacementPoints,
      valueOverReplacement: row.valueOverReplacement,
      rankOverall: row.rankOverall,
      rankPosition: row.rankPosition,
      tier: row.tier,
      adp,
      valueDelta: delta,
      adpMatchedName: adpHit?.matchedName ?? null,
      adpMatchConfidence: adpHit?.confidence ?? null,
      isRookie: row.isRookie,
      rookieYear: row.rookieYear,
      draftNumber: row.draftNumber,
      schedule,
      riskFlags,
      expertBlurb,
      drivers,
      adpQaFlag,
      updatedAt: row.updatedAt,
      source: row.source,
    };
  });
}
