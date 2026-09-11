import { describe, expect, it } from "vitest";
import {
  americanImpliedProb,
  americanToDecimal,
  bookmakerHold,
  evPerDollarRisked,
  fairAmericanFromProb,
  isValidAmericanOdds,
} from "@/lib/line-curve/american";

describe("line-curve American / EV", () => {
  it("converts even money and -110 juice", () => {
    expect(americanImpliedProb(100)).toBeCloseTo(0.5, 6);
    expect(americanImpliedProb(-110)).toBeCloseTo(110 / 210, 6);
    expect(americanToDecimal(-110)).toBeCloseTo(1 + 100 / 110, 6);
  });

  it("rejects invalid American mid-range prices", () => {
    expect(isValidAmericanOdds(-66)).toBe(false);
    expect(isValidAmericanOdds(0)).toBe(false);
    expect(americanImpliedProb(-66)).toBeNull();
  });

  it("tracks bookmaker hold separately from implied", () => {
    const hold = bookmakerHold(-110, -110);
    expect(hold).toBeCloseTo(220 / 210 - 1, 6);
    expect(hold).toBeGreaterThan(0);
    expect(americanImpliedProb(-110)).not.toBeCloseTo(0.5, 2);
  });

  it("EV per $1 at -110 is positive when cover is 0.55 and push is 0", () => {
    const ev = evPerDollarRisked({
      cover: 0.55,
      push: 0,
      loss: 0.45,
      americanOdds: -110,
    });
    expect(ev).toBeGreaterThan(0);
  });

  it("push mass is not treated as a loss", () => {
    const noPush = evPerDollarRisked({
      cover: 0.5,
      push: 0,
      loss: 0.5,
      americanOdds: -110,
    });
    const withPush = evPerDollarRisked({
      cover: 0.5,
      push: 0.08,
      loss: 0.42,
      americanOdds: -110,
    });
    expect(withPush).toBeGreaterThan(noPush!);
  });

  it("fair American is roughly -110 near 52.38%", () => {
    expect(fairAmericanFromProb(110 / 210)).toBe(-110);
  });
});
