import { describe, expect, it } from "vitest";
import {
  applyDeskRankPolicy,
  assertNoHardReachViolations,
  deskBoardKey,
  deskDraftBadge,
  DESK_RANK_POLICY,
  draftRank,
  isReachCapped,
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

  it("hard caps a four-round model reach vs ADP", () => {
    const row = player({
      rankOverall: 24,
      position: "WR",
      adp: 72,
      adpMatchConfidence: "high",
    });
    expect(deskBoardKey(row)).toBe(60);
    expect(isReachCapped(row)).toBe(true);
    expect(deskDraftBadge(row).label).toBe("Wait");
  });

  it("allows a small reach within the cap", () => {
    const henry = player({
      rankOverall: 30,
      position: "RB",
      adp: 40,
      adpMatchConfidence: "high",
    });
    expect(deskBoardKey(henry)).toBe(30);
    expect(deskDraftBadge(henry).label).toBe("Reach");
  });

  it("bubbles a falling model favorite modestly vs ADP", () => {
    const gibbs = player({
      rankOverall: 17,
      position: "RB",
      adp: 1,
      adpMatchConfidence: "high",
    });
    expect(deskBoardKey(gibbs)).toBeLessThan(17);
    expect(deskDraftBadge(gibbs).label).toBe("Value");
  });

  it("reorders without mutating model rank", () => {
    const rows = [
      player({
        rankOverall: 24,
        position: "WR",
        adp: 72,
        adpMatchConfidence: "high",
      }),
      player({
        rankOverall: 1,
        position: "RB",
        adp: 5,
        adpMatchConfidence: "high",
      }),
      player({
        rankOverall: 30,
        position: "RB",
        adp: 40,
        adpMatchConfidence: "high",
      }),
    ];
    const ordered = applyDeskRankPolicy(rows);
    expect(ordered.map((r) => r.rankOverall)).toEqual([1, 30, 24]);
    expect(deskBoardKey(ordered.find((r) => r.rankOverall === 24)!)).toBe(60);
    assertNoHardReachViolations(ordered);
  });

  it("never places a board slot more than reachCap before ADP", () => {
    const rows = applyDeskRankPolicy([
      player({
        rankOverall: 4,
        position: "RB",
        adp: 133,
        adpMatchConfidence: "high",
      }),
      player({
        rankOverall: 10,
        position: "QB",
        adp: 80,
        adpMatchConfidence: "high",
      }),
      player({
        rankOverall: 3,
        position: "QB",
        adp: 28,
        adpMatchConfidence: "high",
      }),
    ]);
    for (const row of rows) {
      if (row.adp == null || row.adpMatchConfidence !== "high") continue;
      const reach = row.adp - deskBoardKey(row);
      expect(reach).toBeLessThanOrEqual(DESK_RANK_POLICY.reachCapPicks);
    }
  });
});
