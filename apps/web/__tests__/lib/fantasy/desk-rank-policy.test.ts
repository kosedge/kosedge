import { describe, expect, it } from "vitest";
import {
  applyDeskRankPolicy,
  boardRank,
  deskBoardKey,
  DESK_RANK_POLICY,
} from "@/lib/fantasy/desk-rank-policy";
import type { DeskRankable } from "@/lib/fantasy/desk-rank-policy";

function player(
  partial: Partial<DeskRankable> &
    Pick<DeskRankable, "rankOverall" | "position">,
): DeskRankable {
  return {
    adp: null,
    adpMatchConfidence: null,
    ...partial,
  };
}

describe("desk rank policy", () => {
  it("does not blend unmatched ADP into the board key", () => {
    const row = player({
      rankOverall: 4,
      position: "RB",
      adp: 133,
      adpMatchConfidence: null,
    });
    expect(deskBoardKey(row)).toBe(4);
  });

  it("does not blend cross-format ADP into the board key", () => {
    const row = player({
      rankOverall: 4,
      position: "RB",
      adp: 133,
      adpMatchConfidence: "cross_format",
    });
    expect(deskBoardKey(row)).toBe(4);
  });

  it("penalizes reaching ADP by more than one round", () => {
    const charbonnet = player({
      rankOverall: 4,
      position: "RB",
      adp: 133,
      adpMatchConfidence: "high",
    });
    const cmc = player({
      rankOverall: 1,
      position: "RB",
      adp: 5,
      adpMatchConfidence: "high",
    });
    expect(deskBoardKey(charbonnet)).toBeGreaterThan(deskBoardKey(cmc));
    expect(deskBoardKey(charbonnet)).toBeGreaterThan(charbonnet.rankOverall);
    const extra = 133 - 4 - DESK_RANK_POLICY.reachFreePicks;
    expect(deskBoardKey(charbonnet)).toBeCloseTo(
      4 + extra * DESK_RANK_POLICY.reachPenaltyPerPick,
      5,
    );
  });

  it("lets a model favorite wait-bubble modestly vs ADP", () => {
    const gibbs = player({
      rankOverall: 17,
      position: "RB",
      adp: 1,
      adpMatchConfidence: "high",
    });
    expect(deskBoardKey(gibbs)).toBeLessThan(17);
    const wait = Math.min(17 - 1, DESK_RANK_POLICY.waitBubbleCapPicks);
    expect(deskBoardKey(gibbs)).toBeCloseTo(
      17 - wait * DESK_RANK_POLICY.waitBubblePerPick,
      5,
    );
  });

  it("adds extra QB suppress when Model ranks a QB 2+ rounds ahead of ADP", () => {
    const qb = player({
      rankOverall: 10,
      position: "QB",
      adp: 80,
      adpMatchConfidence: "high",
    });
    const rb = player({
      rankOverall: 20,
      position: "RB",
      adp: 22,
      adpMatchConfidence: "high",
    });
    expect(deskBoardKey(qb)).toBeGreaterThan(deskBoardKey(rb));
  });

  it("reorders the board without mutating Model rank", () => {
    const rows = [
      player({
        rankOverall: 4,
        position: "RB",
        adp: 133,
        adpMatchConfidence: "high",
      }),
      player({
        rankOverall: 1,
        position: "RB",
        adp: 5,
        adpMatchConfidence: "high",
      }),
      player({
        rankOverall: 17,
        position: "RB",
        adp: 1,
        adpMatchConfidence: "high",
      }),
    ];
    const ordered = applyDeskRankPolicy(rows);
    expect(ordered.map((r) => r.rankOverall)).toEqual([1, 17, 4]);
    expect(ordered.map((r) => r.deskOrder)).toEqual([1, 2, 3]);
    expect(boardRank(ordered[2]!)).toBe(3);
    expect(ordered[2]?.rankOverall).toBe(4);
  });
});
