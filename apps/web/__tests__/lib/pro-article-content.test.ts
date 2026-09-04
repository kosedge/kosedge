import { describe, expect, it } from "vitest";
import type { LegacyEdgeBoardRow } from "@/lib/flat-rows-to-legacy";
import { buildProArticleContent } from "@/lib/pro-article-content";

function buildRow(
  overrides: Partial<LegacyEdgeBoardRow> = {},
): LegacyEdgeBoardRow {
  return {
    id: "game-1",
    time: "7:30 PM ET",
    teamA: { name: "Away Team", site: "Away" },
    teamB: { name: "Home Team", site: "Home" },
    openOU: {
      top: { label: "o219.5", juice: "-110" },
      bottom: { label: "u219.5", juice: "-110" },
    },
    openLine: {
      top: { label: "+3.5", juice: "-110" },
      bottom: { label: "-3.5", juice: "-110" },
    },
    bestLine: {
      top: { label: "+2.5", juice: "-108" },
      bottom: { label: "-2.5", juice: "-112" },
    },
    bestOU: {
      top: { label: "o221.5", juice: "-110" },
      bottom: { label: "u221.5", juice: "-110" },
    },
    edgeLineNum: 1.4,
    edgeOUNum: 0.8,
    ...overrides,
  };
}

describe("buildProArticleContent", () => {
  it("uses NFL-specific execution language", () => {
    const content = buildProArticleContent({ sport: "nfl", row: buildRow() });
    expect(content.mode).toBe("full");
    expect(content.modelEdge).toContain("key spread bands");
    expect(content.matchupDrivers.length).toBe(3);
  });

  it("uses MLB-specific context without NFL leakage", () => {
    const content = buildProArticleContent({ sport: "mlb", row: buildRow() });
    expect(content.modelEdge.toLowerCase()).toContain("bullpen");
    expect(content.marketContext.toLowerCase()).toContain("starter");
    expect(content.modelEdge.toLowerCase()).not.toContain("key spread bands");
  });

  it("provides conservative fallback when model edges are sparse", () => {
    const content = buildProArticleContent({
      sport: "ncaam",
      row: buildRow({ edgeLineNum: undefined, edgeOUNum: undefined }),
    });
    expect(content.modelEdge).toContain("execution should remain conservative");
    expect(content.riskFactors.length).toBeGreaterThan(0);
  });

  it("returns premium placeholder content when board labels are unavailable", () => {
    const content = buildProArticleContent({
      sport: "mlb",
      row: buildRow({
        bestLine: {
          top: { label: "—", juice: "" },
          bottom: { label: "—", juice: "" },
        },
      }),
    });
    expect(content.mode).toBe("placeholder");
    expect(content.confidence.toLowerCase()).toContain("data pending");
  });
});
