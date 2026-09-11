import { describe, expect, it } from "vitest";
import {
  atsOutcomeMass,
  buildMarginPmf,
  massNear,
  teamScorePmf,
} from "@/lib/line-curve/margin-pmf";
import type { ModelMarginInput } from "@/lib/line-curve/types";

function pickEm(): ModelMarginInput {
  return {
    eventId: "pmf-test",
    modelRunId: "pmf-test-run",
    sport: "cfb",
    homeTeam: "Home",
    awayTeam: "Away",
    modelSpreadHome: 0,
    expectedHomeScore: 26,
    expectedAwayScore: 26,
    marginSd: 16,
  };
}

function gaussianIntegerMass(mean: number, sd: number, k: number): number {
  const z = (k - mean) / sd;
  return Math.exp(-0.5 * z * z);
}

describe("line-curve integer margin distribution", () => {
  it("puts mass only on integer scores and margins", () => {
    const scores = teamScorePmf(27);
    expect(scores.every((p, i) => p === 0 || Number.isInteger(i))).toBe(true);
    expect(scores.reduce((a, b) => a + b, 0)).toBeCloseTo(1, 5);

    const pmf = buildMarginPmf(pickEm());
    for (const k of pmf.mass.keys()) {
      expect(Number.isInteger(k)).toBe(true);
    }
    let sum = 0;
    for (const p of pmf.mass.values()) sum += p;
    expect(sum).toBeCloseTo(1, 5);
  });

  it("win + push + loss = 1 at a posted line", () => {
    const pmf = buildMarginPmf(pickEm());
    const half = atsOutcomeMass(pmf, "away", 1.5);
    expect(half.cover + half.push + half.loss).toBeCloseTo(1, 6);
    expect(half.push).toBe(0);

    const integer = atsOutcomeMass(pmf, "away", 3);
    expect(integer.cover + integer.push + integer.loss).toBeCloseTo(1, 6);
    expect(integer.push).toBeGreaterThan(0);
  });

  it("key-number mass emerges from scoring, not a teaser table", () => {
    const pmf = buildMarginPmf(pickEm());
    const keys = [3, 7, 10, 14].reduce(
      (acc, k) => acc + massNear(pmf, k) + massNear(pmf, -k),
      0,
    );
    let gaussKeys = 0;
    let gaussAll = 0;
    for (let k = -40; k <= 40; k += 1) {
      const w = gaussianIntegerMass(pmf.mean, pmf.sd, k);
      gaussAll += w;
      if ([3, 7, 10, 14, -3, -7, -10, -14].includes(k)) gaussKeys += w;
    }
    const gaussShare = gaussKeys / gaussAll;
    const footballShare = keys;
    expect(footballShare).toBeGreaterThan(gaussShare);
  });

  it("buying points raises cover non-linearly across a key number", () => {
    const pmf = buildMarginPmf(pickEm());
    const plus15 = atsOutcomeMass(pmf, "away", 1.5).cover;
    const plus25 = atsOutcomeMass(pmf, "away", 2.5).cover;
    const plus35 = atsOutcomeMass(pmf, "away", 3.5).cover;
    expect(plus25).toBeGreaterThan(plus15);
    expect(plus35).toBeGreaterThan(plus25);
    const stepTo25 = plus25 - plus15;
    const stepAcross3 = plus35 - plus25;
    expect(stepAcross3).toBeGreaterThan(stepTo25);
  });
});
