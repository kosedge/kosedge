import { describe, expect, it } from "vitest";
import {
  applyDeskRankPolicy,
  assertNoHardReachViolations,
  deskBoardKey,
  draftRank,
} from "@/lib/fantasy/desk-rank-policy";
import type { DeskRankable } from "@/lib/fantasy/desk-rank-policy";
import {
  filterDraftableRows,
  loadDraftAvailabilityBook,
} from "@/lib/fantasy/draft-availability";
import { FANTASY_SCORING_PROFILES } from "@/lib/nfl-fantasy-draft-shared";

function player(
  name: string,
  partial: Partial<DeskRankable> &
    Pick<DeskRankable, "rankOverall" | "position">,
): DeskRankable & { name: string } {
  return {
    name,
    adp: null,
    adpMatchConfidence: null,
    ...partial,
  };
}

describe("fantasy draft rank board smoke", () => {
  it("default scoring profile lists PPR first", () => {
    expect(FANTASY_SCORING_PROFILES[0]?.value).toBe("ppr");
  });

  it("sorts by draft rank 1…N with hard reach cap", () => {
    const rows = applyDeskRankPolicy([
      player("reach-case", {
        rankOverall: 24,
        position: "WR",
        adp: 72,
        adpMatchConfidence: "high",
      }),
      player("anchor", {
        rankOverall: 1,
        position: "RB",
        adp: 3,
        adpMatchConfidence: "high",
      }),
      player("henry", {
        rankOverall: 30,
        position: "RB",
        adp: 40,
        adpMatchConfidence: "high",
      }),
    ]);

    expect(rows.map((r) => r.deskOrder)).toEqual([1, 2, 3]);
    expect(draftRank(rows[0]!)).toBe(1);
    expect(deskBoardKey(rows.find((r) => r.name === "reach-case")!)).toBe(60);
    assertNoHardReachViolations(rows);
  });

  it("four-round model reach uses capped board key not model rank", () => {
    const row = player("X", {
      rankOverall: 24,
      position: "WR",
      adp: 72,
      adpMatchConfidence: "high",
    });
    expect(deskBoardKey(row)).toBe(60);
    expect(deskBoardKey(row)).not.toBe(24);
  });

  it("sits Jacobs before desk rank so he is not draftable", () => {
    const book = loadDraftAvailabilityBook(2026);
    const pool = [
      {
        playerName: "Josh Jacobs",
        team: "GB",
        position: "RB",
        rankOverall: 9,
        adp: 29,
        adpMatchConfidence: "high" as const,
      },
      {
        playerName: "Jahmyr Gibbs",
        team: "DET",
        position: "RB",
        rankOverall: 1,
        adp: 1,
        adpMatchConfidence: "high" as const,
      },
    ];
    const { draftable, sat } = filterDraftableRows(pool, book);
    expect(sat.some((s) => s.row.playerName === "Josh Jacobs")).toBe(true);
    const ranked = applyDeskRankPolicy(draftable);
    expect(ranked.every((r) => r.playerName !== "Josh Jacobs")).toBe(true);
    expect(ranked[0]?.playerName).toBe("Jahmyr Gibbs");
    expect(ranked[0]?.deskOrder).toBe(1);
  });
});
