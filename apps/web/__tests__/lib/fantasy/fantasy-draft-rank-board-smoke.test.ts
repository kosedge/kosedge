import { describe, expect, it } from "vitest";
import {
  applyDeskRankPolicy,
  draftRank,
  deskBoardKey,
} from "@/lib/fantasy/desk-rank-policy";
import type { DeskRankable } from "@/lib/fantasy/desk-rank-policy";
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

  it("sorts the default board by draft rank 1…N", () => {
    const rows = applyDeskRankPolicy([
      player("reach-rb", {
        rankOverall: 4,
        position: "RB",
        adp: 133,
        adpMatchConfidence: "high",
      }),
      player("anchor-rb", {
        rankOverall: 1,
        position: "RB",
        adp: 5,
        adpMatchConfidence: "high",
      }),
      player("wait-rb", {
        rankOverall: 17,
        position: "RB",
        adp: 1,
        adpMatchConfidence: "high",
      }),
      player("unmatched-wr", {
        rankOverall: 8,
        position: "WR",
        adp: 40,
        adpMatchConfidence: null,
      }),
    ]);

    expect(rows.map((r) => r.deskOrder)).toEqual([1, 2, 3, 4]);
    expect(rows.map((r) => draftRank(r))).toEqual([1, 2, 3, 4]);
    expect(rows[0]?.name).toBe("anchor-rb");
    expect(rows[1]?.name).toBe("unmatched-wr");
    expect(rows[2]?.name).toBe("wait-rb");
    expect(rows[3]?.name).toBe("reach-rb");
  });

  it("nudges a model darling ranked far ahead of ADP (reach penalty)", () => {
    const reach = player("charbonnet", {
      rankOverall: 4,
      position: "RB",
      adp: 133,
      adpMatchConfidence: "high",
    });
    const fair = player("cmc", {
      rankOverall: 1,
      position: "RB",
      adp: 5,
      adpMatchConfidence: "high",
    });
    expect(deskBoardKey(reach)).toBeGreaterThan(deskBoardKey(fair));
    expect(deskBoardKey(reach)).toBeGreaterThan(reach.rankOverall);
  });

  it("bubbles a falling model favorite modestly vs ADP", () => {
    const gibbs = player("gibbs", {
      rankOverall: 17,
      position: "RB",
      adp: 1,
      adpMatchConfidence: "high",
    });
    expect(deskBoardKey(gibbs)).toBeLessThan(gibbs.rankOverall);
  });

  it("five example moves vs pure model / pure ADP", () => {
    const board = applyDeskRankPolicy([
      player("CMC", {
        rankOverall: 1,
        position: "RB",
        adp: 3,
        adpMatchConfidence: "high",
      }),
      player("Ja'Marr Chase", {
        rankOverall: 2,
        position: "WR",
        adp: 2,
        adpMatchConfidence: "high",
      }),
      player("Josh Allen", {
        rankOverall: 3,
        position: "QB",
        adp: 28,
        adpMatchConfidence: "high",
      }),
      player("Zach Charbonnet", {
        rankOverall: 4,
        position: "RB",
        adp: 120,
        adpMatchConfidence: "high",
      }),
      player("Jahmyr Gibbs", {
        rankOverall: 5,
        position: "RB",
        adp: 8,
        adpMatchConfidence: "high",
      }),
    ]);

    const cmc = board.find((r) => r.name === "CMC")!;
    const chase = board.find((r) => r.name === "Ja'Marr Chase")!;
    const allen = board.find((r) => r.name === "Josh Allen")!;
    const charb = board.find((r) => r.name === "Zach Charbonnet")!;
    const gibbs = board.find((r) => r.name === "Jahmyr Gibbs")!;

    // Pure model top-5 order; draft rank reshuffles reach / QB / wait cases.
    expect(cmc.deskOrder).toBe(1);
    expect(chase.deskOrder).toBe(2);
    expect(gibbs.deskOrder).toBeLessThan(charb.deskOrder!);
    expect(allen.deskOrder).toBeGreaterThan(allen.rankOverall);
    expect(charb.deskOrder).toBeGreaterThan(charb.rankOverall);
    expect(charb.deskOrder).toBe(5);
  });
});
