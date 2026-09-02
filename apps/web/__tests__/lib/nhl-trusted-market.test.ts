import { describe, expect, it } from "vitest";
import {
  NHL_LEAN_EDGE_PTS,
  NHL_PLAY_EDGE_PTS,
  isNhlPreseason,
  nhlAwayBookToHome,
  nhlEdgeTag,
  trustNhlMarket,
} from "@/lib/nhl-trusted-market";

describe("nhl-trusted-market", () => {
  it("uses LEAN 2.5 / PLAY 4.0", () => {
    expect(NHL_LEAN_EDGE_PTS).toBe(2.5);
    expect(NHL_PLAY_EDGE_PTS).toBe(4.0);
    expect(nhlEdgeTag(4.0, { trusted: true })).toBe("PLAY");
    expect(nhlEdgeTag(2.5, { trusted: true })).toBe("LEAN");
    expect(nhlEdgeTag(2.0, { trusted: true })).toBe("PASS");
    expect(nhlEdgeTag(5.0, { trusted: false })).toBe("PASS");
    expect(nhlEdgeTag(5.0, { trusted: true, preseason: true })).toBe("PASS");
  });

  it("flips away-signed book to home", () => {
    expect(nhlAwayBookToHome(1.5)).toBe(-1.5);
    expect(nhlAwayBookToHome(-1.5)).toBe(1.5);
  });

  it("treats early September as preseason and late Sep as RS", () => {
    expect(isNhlPreseason(new Date("2026-09-02T12:00:00Z"))).toBe(true);
    expect(isNhlPreseason(new Date("2026-09-29T12:00:00Z"))).toBe(false);
    expect(isNhlPreseason(new Date("2026-10-15T12:00:00Z"))).toBe(false);
  });

  it("rejects missing Best / absurd gaps", () => {
    expect(
      trustNhlMarket({ kei: -0.94, best: null, open: null }).trusted,
    ).toBe(false);
    expect(
      trustNhlMarket({
        kei: -0.94,
        best: -0.94,
        open: -1.0,
        bookCount: 2,
        preseason: false,
      }).trusted,
    ).toBe(true);
    expect(
      trustNhlMarket({
        kei: -0.94,
        best: 5.0,
        open: 5.0,
        bookCount: 2,
        preseason: false,
      }).reason,
    ).toBe("absurd_vs_kei");
  });
});
