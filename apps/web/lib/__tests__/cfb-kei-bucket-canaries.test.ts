/**
 * Chapter 0 canaries — KEI pack values that later chapters must not silently drift.
 * No ratings edits in Chapter 0; this locks the exhibit numbers.
 */
import { describe, expect, it } from "vitest";
import pack from "../data/cfb-kei-w0-w1-2026.json";

type KeiGame = {
  week: number;
  home: string;
  away: string;
  kei?: { kei_spread_home?: number | null };
};

const games = (pack as { games: KeiGame[] }).games;

function find(week: number, away: string, home: string): KeiGame | undefined {
  return games.find(
    (g) => g.week === week && g.away === away && g.home === home,
  );
}

describe("CFB KEI Chapter 0 canaries (pack)", () => {
  it("BALL@OSU cupcake KEI ≈ −42.2", () => {
    const g = find(1, "BALL", "OSU");
    expect(g?.kei?.kei_spread_home).toBeCloseTo(-42.2, 1);
  });

  it("UNC@TCU mid KEI ≈ −20.39", () => {
    const g = find(0, "UNC", "TCU");
    expect(g?.kei?.kei_spread_home).toBeCloseTo(-20.39, 1);
  });

  it("HAW@STAN polarity KEI ≈ +10.90 (home)", () => {
    const g = find(0, "HAW", "STAN");
    expect(g?.kei?.kei_spread_home).toBeCloseTo(10.9, 1);
  });
});
