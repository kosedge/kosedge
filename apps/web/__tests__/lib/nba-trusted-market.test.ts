/**
 * NBA Chapter 4 trusted-market + tag thresholds.
 */
import { describe, expect, it } from "vitest";
import {
  NBA_LEAN_EDGE_PTS,
  NBA_PLAY_EDGE_PTS,
  applyNbaTrustedMarketToRows,
  nbaEdgeTag,
  trustNbaMarket,
} from "@/lib/nba-trusted-market";

describe("nba-trusted-market", () => {
  it("registers Ch4 thresholds", () => {
    expect(NBA_LEAN_EDGE_PTS).toBe(2.5);
    expect(NBA_PLAY_EDGE_PTS).toBe(4.0);
  });

  it("PASS without trusted Best / preseason", () => {
    expect(nbaEdgeTag(5, { trusted: false })).toBe("PASS");
    expect(nbaEdgeTag(5, { preseason: true })).toBe("PASS");
    expect(nbaEdgeTag(4, { trusted: true })).toBe("PLAY");
    expect(nbaEdgeTag(2.5, { trusted: true })).toBe("LEAN");
  });

  it("clears Best when untrusted", () => {
    const rows = applyNbaTrustedMarketToRows(
      [
        {
          market: "Spread",
          kei: "-4.5",
          open: "+20.5", // home −20.5 — absurd vs KEI even as open fallback
          best: "+22.5",
        },
      ],
      { preseason: false },
    );
    expect(rows[0].nbaMarketTrusted).toBe(false);
    expect(rows[0].best).toBe("—");
  });

  it("keeps Best when trusted", () => {
    const verdict = trustNbaMarket({
      kei: -4.5,
      best: -4.0,
      open: -3.5,
      bookCount: 2,
      preseason: false,
    });
    expect(verdict.trusted).toBe(true);
    const rows = applyNbaTrustedMarketToRows(
      [{ market: "Spread", kei: "-4.5", open: "+3.5", best: "+4.0" }],
      { preseason: false },
    );
    expect(rows[0].nbaMarketTrusted).toBe(true);
    expect(rows[0].best).toBe("+4.0");
  });
});
