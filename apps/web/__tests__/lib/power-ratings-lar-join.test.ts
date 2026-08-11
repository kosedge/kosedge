import { describe, expect, it } from "vitest";
import {
  enrichNflPowerRatingsWithIntel,
  type PowerRatingRow,
} from "@/lib/power-ratings";

function boardRow(
  teamNorm: string,
  rating: number,
  extras?: Partial<PowerRatingRow>,
): PowerRatingRow {
  return {
    rank: 1,
    team: teamNorm,
    teamNorm,
    rating,
    offense: null,
    defense: null,
    record: null,
    ...extras,
  };
}

describe("enrichNflPowerRatingsWithIntel — LA/LAR join", () => {
  it("fills Off/Def/Record for LAR when intel still keys Rams as LA", () => {
    const board = [
      boardRow("LAR", 9.69, { rank: 8 }),
      boardRow("PHI", 11.2, { rank: 1 }),
      boardRow("KC", 10.5, { rank: 3 }),
    ];
    const standings = [
      { team: "LA", wins: 10, losses: 7, ties: 0 },
      { team: "PHI", wins: 14, losses: 3, ties: 0 },
      { team: "KC", wins: 15, losses: 2, ties: 0 },
    ];
    const stats = [
      {
        team: "LA",
        epa_per_play_offense: 0.112,
        epa_per_play_defense_allowed: -0.041,
      },
      {
        team: "PHI",
        epa_per_play_offense: 0.15,
        epa_per_play_defense_allowed: -0.08,
      },
      {
        team: "KC",
        epa_per_play_offense: 0.13,
        epa_per_play_defense_allowed: -0.05,
      },
    ];

    const enriched = enrichNflPowerRatingsWithIntel(board, standings, stats);
    const lar = enriched.find((r) => r.teamNorm === "LAR");
    const phi = enriched.find((r) => r.teamNorm === "PHI");
    const kc = enriched.find((r) => r.teamNorm === "KC");

    expect(lar?.offense).toBe(0.112);
    expect(lar?.defense).toBe(-0.041);
    expect(lar?.record).toBe("10-7");
    expect(phi?.offense).toBe(0.15);
    expect(phi?.record).toBe("14-3");
    expect(kc?.offense).toBe(0.13);
    expect(kc?.record).toBe("15-2");
  });

  it("does not invent a second Rams row when both LA and LAR appear in intel", () => {
    const board = [boardRow("LAR", 9.69)];
    const standings = [
      { team: "LA", wins: 10, losses: 7, ties: 0 },
      { team: "LAR", wins: 10, losses: 7, ties: 0 },
    ];
    const stats = [
      {
        team: "LA",
        epa_per_play_offense: 0.1,
        epa_per_play_defense_allowed: -0.02,
      },
    ];
    const enriched = enrichNflPowerRatingsWithIntel(board, standings, stats);
    expect(enriched).toHaveLength(1);
    expect(enriched[0]?.teamNorm).toBe("LAR");
    expect(enriched[0]?.record).toBe("10-7");
    expect(enriched[0]?.offense).toBe(0.1);
  });

  it("leaves Off/Def/Record null only when intel truly lacks the franchise", () => {
    const board = [boardRow("LAR", 9.69), boardRow("PHI", 11.2)];
    const standings = [{ team: "PHI", wins: 14, losses: 3, ties: 0 }];
    const stats = [
      {
        team: "PHI",
        epa_per_play_offense: 0.15,
        epa_per_play_defense_allowed: -0.08,
      },
    ];
    const enriched = enrichNflPowerRatingsWithIntel(board, standings, stats);
    const lar = enriched.find((r) => r.teamNorm === "LAR");
    expect(lar?.offense).toBeNull();
    expect(lar?.defense).toBeNull();
    expect(lar?.record).toBeNull();
  });
});
