import { describe, expect, it } from "vitest";
import {
  advanceCpuUntilUserOrDone,
  autoCompleteDraft,
  createMockDraftState,
  defaultMockConfig,
  isDraftComplete,
  isUserTurn,
  makeUserPick,
  snakeTeamIndex,
  buildPostDraftReport,
  availablePlayers,
} from "@/lib/fantasy/mock-draft-engine";
import type { FantasyDeskRow } from "@/lib/fantasy/types";
import type { MockDraftPick, MockDraftState } from "@/lib/fantasy/mock-types";

function row(
  partial: Partial<FantasyDeskRow> & {
    playerId: string;
    playerName: string;
    position: string;
    rankOverall: number;
  },
): FantasyDeskRow {
  return {
    season: 2026,
    scoringProfile: "half_ppr",
    modelVersion: "test-model",
    playerUid: null,
    team: "KC",
    gamesProjected: 17,
    passYardsTotal: 0,
    rushYardsTotal: 800,
    receivingYardsTotal: 200,
    receptionsTotal: 30,
    passTdsTotal: 0,
    rushTdsTotal: 6,
    recTdsTotal: 2,
    totalPoints: 200,
    floorPoints: 160,
    medianPoints: 200,
    ceilingPoints: 240,
    replacementPoints: 100,
    valueOverReplacement: 100,
    rankPosition: 1,
    tier: "RB1",
    adp: partial.rankOverall + 5,
    valueDelta: 5,
    adpMatchedName: partial.playerName,
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
    drivers: ["volume"],
    updatedAt: null,
    source: "preseason-fallback",
    ...partial,
  };
}

function makeBoard(n = 180): FantasyDeskRow[] {
  const positions = ["RB", "WR", "QB", "TE", "RB", "WR"] as const;
  return Array.from({ length: n }, (_, i) => {
    const position = positions[i % positions.length]!;
    return row({
      playerId: `p${i + 1}`,
      playerName: `Player ${i + 1}`,
      position,
      rankOverall: i + 1,
      rankPosition: Math.floor(i / 4) + 1,
      adp: i + 1 + (i % 7),
      valueDelta: i % 11 === 0 ? 12 : i % 13 === 0 ? -10 : 3,
      medianPoints: 220 - i * 0.4,
    });
  });
}

describe("mock draft engine", () => {
  it("snake order zigzags", () => {
    expect(snakeTeamIndex(1, 12)).toBe(0);
    expect(snakeTeamIndex(12, 12)).toBe(11);
    expect(snakeTeamIndex(13, 12)).toBe(11);
    expect(snakeTeamIndex(24, 12)).toBe(0);
  });

  it("starts on user turn when they own pick 1", () => {
    const board = makeBoard();
    const state = createMockDraftState({
      config: defaultMockConfig(10, "half_ppr", 1),
      board,
    });
    expect(isUserTurn(state)).toBe(true);
  });

  it("CPU advances to user slot without drafting twice", () => {
    const board = makeBoard();
    let state = createMockDraftState({
      config: defaultMockConfig(12, "half_ppr", 3),
      board,
    });
    state = advanceCpuUntilUserOrDone(board, state);
    expect(isUserTurn(state)).toBe(true);
    expect(state.picks).toHaveLength(2);
    expect(new Set(state.draftedIds).size).toBe(2);
  });

  it("completes a full 10-team mock with CPU + user autopicks", () => {
    const board = makeBoard(200);
    let state = createMockDraftState({
      config: defaultMockConfig(10, "half_ppr", 5),
      board,
    });
    let guard = 0;
    while (!isDraftComplete(state) && guard < 400) {
      state = advanceCpuUntilUserOrDone(board, state);
      if (isDraftComplete(state)) break;
      if (isUserTurn(state)) {
        const nextPlayer = availablePlayers(board, state)[0];
        expect(nextPlayer).toBeTruthy();
        state = makeUserPick(board, state, nextPlayer!.playerId);
      }
      guard += 1;
    }
    expect(isDraftComplete(state)).toBe(true);
    expect(state.picks).toHaveLength(10 * 15);
    expect(state.phase).toBe("results");
    const report = buildPostDraftReport(board, state);
    expect(report.grade).toMatch(/A|B|C|D/);
    expect(report.roster.length).toBe(15);
  });

  it("incomplete roster missing required K/DST is never a B", () => {
    const skill = makeBoard(120);
    const board: FantasyDeskRow[] = [
      ...skill,
      row({
        playerId: "k1",
        playerName: "Kicker One",
        position: "K",
        rankOverall: 200,
        medianPoints: 130,
        adp: 160,
        valueDelta: 0,
      }),
      row({
        playerId: "dst1",
        playerName: "Defense One",
        position: "DST",
        rankOverall: 201,
        medianPoints: 120,
        adp: 165,
        valueDelta: 0,
      }),
    ];

    // High-point skill roster, no K/DST — format requires both.
    const roster = skill.slice(0, 13).map((r, i) =>
      row({
        ...r,
        playerId: `u${i}`,
        medianPoints: 220 - i,
        position: ["QB", "RB", "RB", "WR", "WR", "TE", "WR", "RB", "WR", "RB", "QB", "TE", "WR"][i]!,
      }),
    );

    const userSlot = 1;
    const picks: MockDraftPick[] = roster.map((r, i) => ({
      overall: i + 1,
      round: 1,
      pickInRound: i + 1,
      teamIndex: 0,
      playerId: r.playerId,
      playerName: r.playerName,
      position: r.position,
      team: r.team,
      isUser: true,
      modelRank: r.rankOverall,
      adp: r.adp,
      valueDelta: r.valueDelta,
    }));

    const state: MockDraftState = {
      config: defaultMockConfig(12, "half_ppr", userSlot),
      phase: "results",
      picks,
      nextOverall: 181,
      totalPicks: 180,
      personas: Array.from({ length: 12 }, () => "balanced" as const),
      teamNames: Array.from({ length: 12 }, (_, i) =>
        i === 0 ? "You" : `CPU ${i + 1}`,
      ),
      draftedIds: picks.map((p) => p.playerId),
      modelVersion: "test",
      season: 2026,
      boardSource: "test",
      startedAt: new Date().toISOString(),
    };

    // Patch board so user picks resolve via playerId
    const patchedBoard = [
      ...roster,
      ...board.filter((b) => b.position === "K" || b.position === "DST"),
    ];
    const report = buildPostDraftReport(patchedBoard, state);
    expect(report.detail).toMatch(/K|DST/);
    expect(report.grade).not.toMatch(/^A|^B/);
    expect(["C+", "C", "D"]).toContain(report.grade);
  });

  it("notable reaches copy compares model rank vs ADP (same math as values)", () => {
    const reachPlayer = row({
      playerId: "reach1",
      playerName: "Reach Guy",
      position: "RB",
      rankOverall: 40,
      adp: 25,
      valueDelta: -15,
      medianPoints: 180,
    });
    const fairPlayer = row({
      playerId: "fair1",
      playerName: "Fair Guy",
      position: "WR",
      rankOverall: 10,
      adp: 12,
      valueDelta: 2,
      medianPoints: 210,
    });
    const board = [reachPlayer, fairPlayer];

    const picks: MockDraftPick[] = [
      {
        overall: 24,
        round: 2,
        pickInRound: 12,
        teamIndex: 0,
        playerId: reachPlayer.playerId,
        playerName: reachPlayer.playerName,
        position: reachPlayer.position,
        team: reachPlayer.team,
        isUser: true,
        modelRank: reachPlayer.rankOverall,
        adp: reachPlayer.adp,
        valueDelta: reachPlayer.valueDelta,
      },
      {
        overall: 25,
        round: 3,
        pickInRound: 1,
        teamIndex: 0,
        playerId: fairPlayer.playerId,
        playerName: fairPlayer.playerName,
        position: fairPlayer.position,
        team: fairPlayer.team,
        isUser: true,
        modelRank: fairPlayer.rankOverall,
        adp: fairPlayer.adp,
        valueDelta: fairPlayer.valueDelta,
      },
    ];

    const state: MockDraftState = {
      config: defaultMockConfig(12, "half_ppr", 1),
      phase: "results",
      picks,
      nextOverall: 181,
      totalPicks: 180,
      personas: Array.from({ length: 12 }, () => "balanced" as const),
      teamNames: Array.from({ length: 12 }, (_, i) =>
        i === 0 ? "You" : `CPU ${i + 1}`,
      ),
      draftedIds: picks.map((p) => p.playerId),
      modelVersion: "test",
      season: 2026,
      boardSource: "test",
      startedAt: new Date().toISOString(),
    };

    const report = buildPostDraftReport(board, state);
    expect(report.reaches.length).toBe(1);
    expect(report.reaches[0]).toContain("model #40");
    expect(report.reaches[0]).toContain("ADP ~25");
    expect(report.reaches[0]).toContain("-15");
    // Must not claim pick-vs-ADP when the delta is model-vs-ADP.
    expect(report.reaches[0]).not.toMatch(/took at pick/i);
  });

  it("auto-complete fills required K and DST when board has them", () => {
    const skill = makeBoard(160);
    const kdst = Array.from({ length: 32 }, (_, i) => {
      const isK = i < 16;
      return row({
        playerId: isK ? `k${i}` : `dst${i - 16}`,
        playerName: isK ? `Kicker ${i}` : `Defense ${i - 16}`,
        position: isK ? "K" : "DST",
        rankOverall: 200 + i,
        medianPoints: 130 - i,
        adp: 150 + i,
        valueDelta: 0,
        team: "KC",
      });
    });
    const board = [...skill, ...kdst];
    let state = createMockDraftState({
      config: defaultMockConfig(10, "half_ppr", 1),
      board,
    });
    state = autoCompleteDraft(board, state);
    expect(isDraftComplete(state)).toBe(true);
    const report = buildPostDraftReport(board, state);
    const positions = report.roster.map((r) => r.position.toUpperCase());
    expect(positions).toContain("K");
    expect(positions).toContain("DST");
    expect(report.detail).not.toMatch(/still need.*\bK\b/);
    expect(report.detail).not.toMatch(/still need.*DST/);
  });
});
