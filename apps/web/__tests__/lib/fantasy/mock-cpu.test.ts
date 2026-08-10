import { describe, expect, it } from "vitest";
import {
  chooseCpuPlayer,
  isCpuReachHardBlocked,
  scoreCpuCandidate,
} from "@/lib/fantasy/mock-cpu";
import { MOCK_CPU_WEIGHTS, type MockCpuPersona } from "@/lib/fantasy/mock-types";
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

  it("suppresses QB2 once a starter QB is rostered (late rounds)", () => {
    const qb2 = row({
      playerId: "qb2",
      position: "QB",
      rankOverall: 90,
      adp: 95,
      valueDelta: 12,
    });
    const wr = row({
      playerId: "wr",
      position: "WR",
      rankOverall: 88,
      adp: 90,
      valueDelta: 2,
    });
    const roster = [
      row({
        playerId: "qb1",
        position: "QB",
        rankOverall: 45,
        adp: 50,
        valueDelta: 0,
      }),
    ];
    const choice = chooseCpuPlayer({
      available: [qb2, wr],
      roster,
      board: [...roster, qb2, wr],
      overall: 110, // ~round 10 in 12-team
      teamCount: 12,
      persona: "balanced",
      weights: MOCK_CPU_WEIGHTS.balanced,
      teamIndex: 3,
    });
    expect(choice?.playerId).toBe("wr");
  });

  it("hard-blocks lottery ADP reaches in Round 1", () => {
    expect(
      isCpuReachHardBlocked({
        marketAdp: 269,
        overall: 3,
        teamCount: 12,
        position: "TE",
        round: 1,
      }),
    ).toBe(true);
    expect(
      isCpuReachHardBlocked({
        marketAdp: 4,
        overall: 3,
        teamCount: 12,
        position: "RB",
        round: 1,
      }),
    ).toBe(false);
  });

  it("never selects Gesicki-class late-ADP fringe TE at 1.03 under stress", () => {
    const chalk = [
      row({
        playerId: "rb1",
        position: "RB",
        rankOverall: 1,
        adp: 1.2,
        valueDelta: 0,
        valueOverReplacement: 140,
        medianPoints: 280,
      }),
      row({
        playerId: "wr1",
        position: "WR",
        rankOverall: 2,
        adp: 2.1,
        valueDelta: 0,
        valueOverReplacement: 130,
        medianPoints: 270,
      }),
      row({
        playerId: "rb2",
        position: "RB",
        rankOverall: 3,
        adp: 3.4,
        valueDelta: 0,
        valueOverReplacement: 120,
        medianPoints: 260,
      }),
      row({
        playerId: "wr2",
        position: "WR",
        rankOverall: 4,
        adp: 4.5,
        valueDelta: 0,
        valueOverReplacement: 115,
        medianPoints: 250,
      }),
      row({
        playerId: "rb3",
        position: "RB",
        rankOverall: 5,
        adp: 5.8,
        valueDelta: 0,
        valueOverReplacement: 110,
        medianPoints: 245,
      }),
    ];
    // Fringe TE in top-80 model pool with absurd ADP "value" (pre-fix failure).
    const gesicki = row({
      playerId: "gesicki",
      position: "TE",
      rankOverall: 48,
      adp: 269,
      valueDelta: 221,
      valueOverReplacement: 35,
      medianPoints: 145,
    });
    const depth = Array.from({ length: 30 }, (_, i) =>
      row({
        playerId: `d${i}`,
        position: i % 2 === 0 ? "RB" : "WR",
        rankOverall: 10 + i,
        adp: 10 + i,
        valueDelta: 0,
        valueOverReplacement: 80 - i,
        medianPoints: 200 - i,
      }),
    );
    const available = [...chalk, gesicki, ...depth];
    const personas = Object.keys(MOCK_CPU_WEIGHTS) as MockCpuPersona[];

    for (const persona of personas) {
      const choice = chooseCpuPlayer({
        available,
        roster: [],
        board: available,
        overall: 3, // pick 1.03
        teamCount: 12,
        persona,
        weights: MOCK_CPU_WEIGHTS[persona],
        teamIndex: 2,
      });
      expect(choice?.playerId).not.toBe("gesicki");
      expect(choice).not.toBeNull();
      expect(choice!.adp).not.toBeNull();
      expect(choice!.adp!).toBeLessThan(40);
      expect(["RB", "WR"]).toContain(choice!.position.toUpperCase());
    }
  });
});
