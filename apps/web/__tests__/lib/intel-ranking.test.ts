import { describe, expect, it } from "vitest";
import {
  buildMetricRankMaps,
  computeMetricRanks,
  getMetricRankDirection,
} from "@/lib/intel-ranking";

describe("intel-ranking helpers", () => {
  it("uses explicit rank direction map for known metrics", () => {
    expect(getMetricRankDirection("wins")).toBe("desc");
    expect(getMetricRankDirection("losses")).toBe("asc");
    expect(getMetricRankDirection("points_against")).toBe("asc");
    expect(getMetricRankDirection("unknown_metric")).toBeNull();
  });

  it("applies competition tie ranking with deterministic ordering", () => {
    const ranks = computeMetricRanks(
      [
        { team: "BUF", wins: 12 },
        { team: "MIA", wins: 12 },
        { team: "NE", wins: 9 },
      ],
      "wins",
    );
    expect(ranks.get(0)).toBe(1);
    expect(ranks.get(1)).toBe(1);
    expect(ranks.get(2)).toBe(3);
  });

  it("ignores null and missing values", () => {
    const ranks = computeMetricRanks(
      [
        { team: "BUF", point_diff: 40 },
        { team: "MIA", point_diff: null },
        { team: "NE" },
        { team: "NYJ", point_diff: -10 },
      ],
      "point_diff",
    );
    expect(ranks.get(0)).toBe(1);
    expect(ranks.has(1)).toBe(false);
    expect(ranks.has(2)).toBe(false);
    expect(ranks.get(3)).toBe(2);
  });

  it("builds rank maps for multiple metrics", () => {
    const rankMaps = buildMetricRankMaps(
      [
        { team: "A", wins: 10, losses: 7 },
        { team: "B", wins: 12, losses: 5 },
        { team: "C", wins: 8, losses: 9 },
      ],
      ["wins", "losses"],
    );
    expect(rankMaps.wins?.get(1)).toBe(1);
    expect(rankMaps.losses?.get(1)).toBe(1);
    expect(rankMaps.wins?.get(2)).toBe(3);
  });
});
