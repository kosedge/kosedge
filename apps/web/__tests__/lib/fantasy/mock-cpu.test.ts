import { describe, expect, it } from "vitest";
import { chooseCpuPlayer, scoreCpuCandidate } from "@/lib/fantasy/mock-cpu";
import { MOCK_CPU_WEIGHTS } from "@/lib/fantasy/mock-types";
import type { FantasyDeskRow } from "@/lib/fantasy/types";

function row(
  partial: Partial<FantasyDeskRow> & {
    playerId: string;
    position: string;
    rankOverall: number;
  },
): FantasyDeskRow {
  return {
    season: 2026,
    scoringProfile: "half_ppr",
    modelVersion: "test",
    playerUid: null,
    playerName: partial.playerId,
    team: "DAL",
    gamesProjected: 17,
    passYardsTotal: 0,
    rushYardsTotal: 0,
    receivingYardsTotal: 0,
    receptionsTotal: 0,
    passTdsTotal: 0,
    rushTdsTotal: 0,
    recTdsTotal: 0,
    totalPoints: 150,
    floorPoints: 120,
    medianPoints: 150,
    ceilingPoints: 180,
    replacementPoints: 100,
    valueOverReplacement: 50,
    rankPosition: 1,
    tier: "RB2",
    adp: partial.rankOverall,
    valueDelta: 0,
    adpMatchedName: null,
    adpMatchConfidence: "high",
    isRookie: false,
    rookieYear: null,
    draftNumber: null,
    schedule: {
      early: "neutral",
      playoff: "neutral",
      label: "Neutral",
      detail: "",
    },
    riskFlags: [],
    expertBlurb: "",
    drivers: [],
    updatedAt: null,
    source: "preseason-fallback",
    ...partial,
  };
}

describe("mock CPU", () => {
  it("avoids early kickers when skill needs remain", () => {
    const available = [
      row({
        playerId: "rb",
        position: "RB",
        rankOverall: 20,
        adp: 22,
        valueDelta: 4,
      }),
      row({
        playerId: "k",
        position: "K",
        rankOverall: 180,
        adp: 150,
        valueDelta: 0,
      }),
    ];
    const choice = chooseCpuPlayer({
      available,
      roster: [],
      board: available,
      overall: 15,
      teamCount: 12,
      persona: "balanced",
      weights: MOCK_CPU_WEIGHTS.balanced,
      teamIndex: 2,
    });
    expect(choice?.playerId).toBe("rb");
  });

  it("boosts high-confidence value for value_hunter", () => {
    const valuePick = row({
      playerId: "value",
      position: "WR",
      rankOverall: 40,
      adp: 55,
      valueDelta: 18,
    });
    const chalk = row({
      playerId: "chalk",
      position: "WR",
      rankOverall: 38,
      adp: 39,
      valueDelta: 0,
    });
    const hunter = scoreCpuCandidate({
      row: valuePick,
      roster: [],
      board: [valuePick, chalk],
      available: [valuePick, chalk],
      overall: 36,
      teamCount: 12,
      persona: "value_hunter",
      weights: MOCK_CPU_WEIGHTS.value_hunter,
      teamIndex: 1,
    });
    const follower = scoreCpuCandidate({
      row: chalk,
      roster: [],
      board: [valuePick, chalk],
      available: [valuePick, chalk],
      overall: 36,
      teamCount: 12,
      persona: "adp_follower",
      weights: MOCK_CPU_WEIGHTS.adp_follower,
      teamIndex: 1,
    });
    expect(hunter).toBeGreaterThan(10);
    expect(follower).toBeGreaterThan(0);
  });
});
