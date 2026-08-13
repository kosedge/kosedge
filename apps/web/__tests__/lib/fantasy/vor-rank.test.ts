import { describe, expect, it } from "vitest";
import { rankSeasonFantasyPlayers } from "@/lib/fantasy/vor-rank";

describe("rankSeasonFantasyPlayers", () => {
  it("ranks overall by projected points (VOR still computed)", () => {
    const qbPool = Array.from({ length: 19 }, (_, i) => ({
      playerKey: `qb${i + 1}`,
      position: "QB",
      totalPoints: 210 - (i + 1),
    }));
    const rbPool = Array.from({ length: 5 }, (_, i) => ({
      playerKey: `rb${i + 1}`,
      position: "RB",
      totalPoints: 200 - (i + 1) * 15,
    }));
    const ranked = rankSeasonFantasyPlayers([...qbPool, ...rbPool]);
    const byKey = Object.fromEntries(ranked.map((p) => [p.playerKey, p]));
    expect(byKey.qb1!.rankOverall).toBeLessThan(byKey.rb1!.rankOverall);
    expect(byKey.rb1!.valueOverReplacement).toBeGreaterThan(
      byKey.qb1!.valueOverReplacement,
    );
  });

  it("appends K/DST after skill positions", () => {
    const ranked = rankSeasonFantasyPlayers([
      { playerKey: "k1", position: "K", totalPoints: 170 },
      { playerKey: "wr_deep", position: "WR", totalPoints: 8 },
    ]);
    const byKey = Object.fromEntries(ranked.map((p) => [p.playerKey, p]));
    expect(byKey.wr_deep!.rankOverall).toBeLessThan(byKey.k1!.rankOverall);
  });
});
