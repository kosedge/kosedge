/**
 * WNBA Chapter 4 trusted-market + tag thresholds.
 */
import { describe, expect, it } from "vitest";
import {
  WNBA_LEAN_EDGE_PTS,
  WNBA_PLAY_EDGE_PTS,
  applyWnbaTrustedMarketToRows,
  trustWnbaMarket,
  wnbaEdgeTag,
} from "@/lib/wnba-trusted-market";

describe("wnba-trusted-market", () => {
  it("registers Ch4 thresholds", () => {
    expect(WNBA_LEAN_EDGE_PTS).toBe(2.5);
    expect(WNBA_PLAY_EDGE_PTS).toBe(4.0);
  });

  it("PASS without trusted Best / already final", () => {
    expect(wnbaEdgeTag(5, { trusted: false })).toBe("PASS");
    expect(wnbaEdgeTag(5, { alreadyFinal: true })).toBe("PASS");
    expect(wnbaEdgeTag(4, { trusted: true })).toBe("PLAY");
    expect(wnbaEdgeTag(2.5, { trusted: true })).toBe("LEAN");
  });

  it("keeps Best for display when untrusted; tags stay PASS", () => {
    const rows = applyWnbaTrustedMarketToRows([
      {
        market: "Spread",
        kei: "-8.5",
        open: "+20.5",
        best: "+22.5",
      },
    ]);
    expect(rows[0].wnbaMarketTrusted).toBe(false);
    expect(rows[0].best).toBe("+22.5");
    expect(rows[0].open).toBe("+20.5");
    expect(rows[0].wnbaTrustLabel).toBe("untrusted");
  });

  it("leftover Aug-1 ids force already_final / untrusted", () => {
    const rows = applyWnbaTrustedMarketToRows([
      {
        id: "401857105-spread",
        market: "Spread",
        kei: "4.5",
        open: "+4.5",
        best: "+4.5",
      },
    ]);
    expect(rows[0].wnbaMarketTrusted).toBe(false);
    expect(rows[0].wnbaTrustReason).toBe("already_final");
  });

  it("keeps Best when trusted", () => {
    const verdict = trustWnbaMarket({
      kei: -8.5,
      best: -8.0,
      open: -7.5,
      bookCount: 2,
    });
    expect(verdict.trusted).toBe(true);
    const rows = applyWnbaTrustedMarketToRows([
      { market: "Spread", kei: "-8.5", open: "+7.5", best: "+8.0" },
    ]);
    expect(rows[0].wnbaMarketTrusted).toBe(true);
    expect(rows[0].best).toBe("+8.0");
  });
});
