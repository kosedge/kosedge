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

  it("keeps Best for display when untrusted; tags stay PASS", () => {
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
    expect(rows[0].best).toBe("+22.5");
    expect(rows[0].open).toBe("+20.5");
    expect(rows[0].nbaTrustLabel).toBe("untrusted");
  });

  it("preseason keeps book lines; tags untrusted", () => {
    const rows = applyNbaTrustedMarketToRows(
      [{ market: "Total", kei: "224.5", open: "225.5", best: "226.0" }],
      { preseason: true },
    );
    expect(rows[0].nbaMarketTrusted).toBe(false);
    expect(rows[0].best).toBe("226.0");
    expect(rows[0].open).toBe("225.5");
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
