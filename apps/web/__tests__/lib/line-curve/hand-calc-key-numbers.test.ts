import { describe, expect, it } from "vitest";
import {
  americanImpliedProb,
  evPerDollarRisked,
  fairAmericanFromProb,
} from "@/lib/line-curve/american";
import { atsOutcomeMass, type MarginPmf } from "@/lib/line-curve/margin-pmf";

/**
 * Independent hand calculations around football key numbers 3 and 7.
 * Inputs are specified — this does not trust the score generator.
 */

describe("line-curve hand-calc around 3 and 7", () => {
  it("American ↔ implied and fair price match closed-form juice", () => {
    expect(americanImpliedProb(-110)).toBeCloseTo(110 / 210, 10);
    expect(americanImpliedProb(150)).toBeCloseTo(100 / 250, 10);
    expect(fairAmericanFromProb(110 / 210)).toBe(-110);
    expect(fairAmericanFromProb(0.6)).toBe(-150);
  });

  it("EV/$1 treats integer-line push as 0 P/L, not a loss", () => {
    // -110, cover 0.48, push 0.08 (mass at the key), loss 0.44
    const ev = evPerDollarRisked({
      cover: 0.48,
      push: 0.08,
      loss: 0.44,
      americanOdds: -110,
    });
    const hand = 0.48 * (100 / 110) - 0.44;
    expect(ev).toBeCloseTo(hand, 10);
    const asLoss = evPerDollarRisked({
      cover: 0.48,
      push: 0,
      loss: 0.52,
      americanOdds: -110,
    });
    expect(ev).toBeGreaterThan(asLoss!);
  });

  it("half-point marginal cost across +3 uses Δimplied / Δcover", () => {
    const cover25 = 0.51;
    const cover35 = 0.59;
    const implied25 = americanImpliedProb(-110)!;
    const implied35 = americanImpliedProb(-135)!;
    const dProb = cover35 - cover25;
    const dPrice = implied35 - implied25;
    const marginal = dPrice / dProb;
    expect(implied25).toBeCloseTo(110 / 210, 10);
    expect(implied35).toBeCloseTo(135 / 235, 10);
    expect(dProb).toBeCloseTo(0.08, 10);
    expect(marginal).toBeCloseTo((135 / 235 - 110 / 210) / 0.08, 10);
    expect(dProb).toBeGreaterThan(0);
  });

  it("half-point jump across +7 is priced the same way", () => {
    const cover65 = 0.62;
    const cover75 = 0.71;
    const implied65 = americanImpliedProb(-150)!;
    const implied75 = americanImpliedProb(-180)!;
    const marginal = (implied75 - implied65) / (cover75 - cover65);
    expect(implied65).toBeCloseTo(150 / 250, 10);
    expect(implied75).toBeCloseTo(180 / 280, 10);
    expect(marginal).toBeCloseTo((180 / 280 - 150 / 250) / 0.09, 10);
  });

  it("constructed integer PMF pushes at +3 and +7, not at half-points", () => {
    const mass = new Map<number, number>([
      [-7, 0.1],
      [-3, 0.12],
      [0, 0.08],
      [3, 0.18],
      [7, 0.16],
      [10, 0.1],
      [14, 0.06],
      [1, 0.2],
    ]);
    let sum = 0;
    for (const p of mass.values()) sum += p;
    for (const [k, p] of mass) mass.set(k, p / sum);
    const pmf: MarginPmf = {
      mass,
      mean: 0,
      sd: 8,
      winHome: 0.5,
      pushStraightUp: 0.08,
      winAway: 0.42,
    };
    const home3 = atsOutcomeMass(pmf, "home", 3);
    expect(home3.push).toBeCloseTo(mass.get(-3)!, 8);
    const home35 = atsOutcomeMass(pmf, "home", 3.5);
    expect(home35.push).toBe(0);
    expect(home35.cover).toBeGreaterThan(home3.cover);

    const home7 = atsOutcomeMass(pmf, "home", 7);
    expect(home7.push).toBeCloseTo(mass.get(-7)!, 8);
    const home75 = atsOutcomeMass(pmf, "home", 7.5);
    expect(home75.push).toBe(0);
    expect(home75.cover).toBeGreaterThan(home7.cover);
  });
});
