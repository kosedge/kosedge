import { describe, expect, it } from "vitest";
import {
  formatSleeperGap,
  selectSleeperRows,
  sleeperWhyLine,
} from "@/lib/fantasy/sleepers";
import type { FantasyDeskRow } from "@/lib/fantasy/types";

function row(partial: Partial<FantasyDeskRow> & Pick<FantasyDeskRow, "playerId" | "playerName">): FantasyDeskRow {
  return {
    season: 2026,
    scoringProfile: "half_ppr",
    modelVersion: "test",
    playerUid: null,
    team: "KC",
    position: "WR",
    gamesProjected: 17,
    passYardsTotal: 0,
    rushYardsTotal: 0,
    receivingYardsTotal: 900,
    receptionsTotal: 70,
    passTdsTotal: 0,
    rushTdsTotal: 0,
    recTdsTotal: 5,
    totalPoints: 200,
    floorPoints: 160,
    medianPoints: 200,
    ceilingPoints: 240,
    replacementPoints: 100,
    valueOverReplacement: 40,
    rankOverall: 90,
    rankPosition: 36,
    tier: "WR3",
    adp: 120,
    valueDelta: 30,
    adpMatchedName: partial.playerName,
    adpMatchConfidence: "high",
    isRookie: false,
    rookieYear: null,
    draftNumber: null,
    schedule: {
      early: "soft",
      playoff: "neutral",
      label: "Soft early",
      detail: "test",
    },
    riskFlags: [],
    expertBlurb: "",
    drivers: ["900 receiving yards (~53/g)"],
    updatedAt: null,
    source: "preseason-fallback",
    ...partial,
  };
}

describe("fantasy sleepers", () => {
  it("selects late-round ADP value and keeps unmatched gap as —", () => {
    const board = [
      row({
        playerId: "a",
        playerName: "Value WR",
        rankOverall: 88,
        adp: 130,
        valueDelta: 42,
      }),
      row({
        playerId: "b",
        playerName: "Early chalk",
        rankOverall: 12,
        adp: 10,
        valueDelta: -2,
      }),
      row({
        playerId: "c",
        playerName: "Late unmatched",
        rankOverall: 95,
        adp: null,
        valueDelta: null,
      }),
    ];
    const sleepers = selectSleeperRows(board, 10);
    expect(sleepers.map((r) => r.playerId)).toEqual(["a", "c"]);
    expect(formatSleeperGap(sleepers[0]!.valueDelta)).toBe("+42");
    expect(formatSleeperGap(sleepers[1]!.valueDelta)).toBe("—");
  });

  it("soft-frames huge TE ADP gaps without lottery smash copy", () => {
    const te = row({
      playerId: "te",
      playerName: "Fringe TE",
      position: "TE",
      rankOverall: 110,
      rankPosition: 18,
      adp: 200,
      valueDelta: 90,
      drivers: ["520 receiving yards (~31/g)"],
    });
    const why = sleeperWhyLine(te);
    expect(why).toMatch(/signal, not lottery/i);
    expect(why).not.toMatch(/\+90/);
  });
});
