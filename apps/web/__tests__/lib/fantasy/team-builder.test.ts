import { describe, expect, it } from "vitest";
import {
  bestAvailableByNeed,
  rosterNeeds,
  teamGrade,
} from "@/lib/fantasy/team-builder";
import type { FantasyDeskRow } from "@/lib/fantasy/types";

function row(
  partial: Partial<FantasyDeskRow> & {
    playerId: string;
    position: string;
    medianPoints: number;
  },
): FantasyDeskRow {
  return {
    season: 2026,
    scoringProfile: "half_ppr",
    modelVersion: "test",
    playerUid: null,
    playerName: partial.playerId,
    team: "KC",
    gamesProjected: 17,
    passYardsTotal: 0,
    rushYardsTotal: 0,
    receivingYardsTotal: 0,
    receptionsTotal: 0,
    passTdsTotal: 0,
    rushTdsTotal: 0,
    recTdsTotal: 0,
    totalPoints: partial.medianPoints,
    floorPoints: partial.medianPoints * 0.8,
    ceilingPoints: partial.medianPoints * 1.2,
    replacementPoints: 100,
    valueOverReplacement: 20,
    rankOverall: 1,
    rankPosition: 1,
    tier: "RB1",
    adp: 20,
    valueDelta: 5,
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

describe("team builder", () => {
  it("tracks roster needs", () => {
    const needs = rosterNeeds([
      row({ playerId: "qb", position: "QB", medianPoints: 300 }),
      row({ playerId: "rb1", position: "RB", medianPoints: 250 }),
    ]);
    expect(needs.QB).toBe(0);
    expect(needs.RB).toBe(1);
    expect(needs.WR).toBe(2);
  });

  it("suggests by need before raw board order", () => {
    const board = [
      row({
        playerId: "wr1",
        position: "WR",
        medianPoints: 220,
        rankOverall: 5,
      }),
      row({
        playerId: "rb2",
        position: "RB",
        medianPoints: 200,
        rankOverall: 8,
      }),
    ];
    const roster = [
      row({ playerId: "rb1", position: "RB", medianPoints: 250 }),
    ];
    const suggestions = bestAvailableByNeed(board, roster, 2);
    expect(suggestions[0]?.row.position).toBe("WR");
  });

  it("grades empty roster poorly", () => {
    expect(teamGrade([]).grade).toBe("D");
  });

  it("does not penalize missing K/DST when board has none (preseason)", () => {
    const skillBoard = [
      row({ playerId: "qb", position: "QB", medianPoints: 320 }),
      row({ playerId: "rb1", position: "RB", medianPoints: 280 }),
      row({ playerId: "rb2", position: "RB", medianPoints: 260 }),
      row({ playerId: "wr1", position: "WR", medianPoints: 250 }),
      row({ playerId: "wr2", position: "WR", medianPoints: 240 }),
      row({ playerId: "te", position: "TE", medianPoints: 200 }),
      row({ playerId: "flex", position: "WR", medianPoints: 190 }),
    ];
    const fullSkillRoster = skillBoard;

    const needs = rosterNeeds(fullSkillRoster, skillBoard);
    expect(needs.K).toBe(0);
    expect(needs.DST).toBe(0);
    expect(needs.QB).toBe(0);
    expect(needs.RB).toBe(0);
    expect(needs.WR).toBe(0);
    expect(needs.TE).toBe(0);
    expect(needs.FLEX).toBe(0);

    const grade = teamGrade(fullSkillRoster, skillBoard);
    expect(grade.detail).not.toMatch(/\bK\b/);
    expect(grade.detail).not.toContain("DST");
    expect(grade.detail).not.toContain("still need");
    // Skill starters clear the A threshold without K/DST points.
    expect(grade.grade).toBe("A");

    // Empty roster still grades poorly, but holes omit K/DST.
    const emptyNeeds = rosterNeeds([], skillBoard);
    expect(emptyNeeds.K).toBe(0);
    expect(emptyNeeds.DST).toBe(0);
    expect(emptyNeeds.QB).toBe(1);
    const emptyGrade = teamGrade([], skillBoard);
    expect(emptyGrade.grade).toBe("D");
    expect(emptyGrade.detail).not.toMatch(/\bK\b/);
    expect(emptyGrade.detail).not.toContain("DST");
  });

  it("still requires K/DST when board includes them", () => {
    const board = [
      row({ playerId: "qb", position: "QB", medianPoints: 320 }),
      row({ playerId: "k", position: "K", medianPoints: 120 }),
      row({ playerId: "dst", position: "DST", medianPoints: 110 }),
    ];
    const needs = rosterNeeds(
      [row({ playerId: "qb", position: "QB", medianPoints: 320 })],
      board,
    );
    expect(needs.K).toBe(1);
    expect(needs.DST).toBe(1);
  });

  it("incomplete roster with K/DST holes is never a B (even with high points)", () => {
    const board = [
      row({ playerId: "qb", position: "QB", medianPoints: 320 }),
      row({ playerId: "rb1", position: "RB", medianPoints: 280 }),
      row({ playerId: "rb2", position: "RB", medianPoints: 260 }),
      row({ playerId: "wr1", position: "WR", medianPoints: 250 }),
      row({ playerId: "wr2", position: "WR", medianPoints: 240 }),
      row({ playerId: "te", position: "TE", medianPoints: 200 }),
      row({ playerId: "flex", position: "WR", medianPoints: 190 }),
      row({ playerId: "k", position: "K", medianPoints: 120 }),
      row({ playerId: "dst", position: "DST", medianPoints: 110 }),
    ];
    // Full skill starters, missing only K + DST — historically inflated to B.
    const almostFull = board.filter((r) => r.position !== "K" && r.position !== "DST");
    const needs = rosterNeeds(almostFull, board);
    expect(needs.K).toBe(1);
    expect(needs.DST).toBe(1);
    const grade = teamGrade(almostFull, board);
    expect(grade.grade).not.toMatch(/^A|^B/);
    expect(["C+", "C", "D"]).toContain(grade.grade);
    expect(grade.detail).toMatch(/\bK\b/);
    expect(grade.detail).toContain("DST");
  });
});
