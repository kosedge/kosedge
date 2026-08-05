import { describe, expect, it } from "vitest";
import {
  advanceCpuUntilUserOrDone,
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
});
