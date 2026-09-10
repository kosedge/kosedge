import { describe, expect, it } from "vitest";
import {
  MLB_FAIR_TOTAL_QUANTIZATION,
  formatMlbTotalMean,
  mlbKeiDiffersFromMean,
  quantizeMlbFairTotal,
  resolveMlbKeiTotal,
  roundHalfEven,
} from "@/lib/mlb-fair-total";

describe("mlb fair-total quantization (nearest_half_run)", () => {
  it("smoking gun: 9.09–9.11 → KEI 9.0 is half-run policy, not a stub", () => {
    expect(quantizeMlbFairTotal(9.09)).toBe(9.0);
    expect(quantizeMlbFairTotal(9.1)).toBe(9.0);
    expect(quantizeMlbFairTotal(9.11)).toBe(9.0);
    expect(MLB_FAIR_TOTAL_QUANTIZATION).toBe("nearest_half_run");
  });

  it("varied means do not collapse to a constant 9", () => {
    expect(quantizeMlbFairTotal(8.24)).toBe(8.0);
    expect(quantizeMlbFairTotal(8.26)).toBe(8.5);
    expect(quantizeMlbFairTotal(8.74)).toBe(8.5);
    expect(quantizeMlbFairTotal(8.76)).toBe(9.0);
    expect(quantizeMlbFairTotal(9.24)).toBe(9.0);
    expect(quantizeMlbFairTotal(9.26)).toBe(9.5);
    expect(quantizeMlbFairTotal(7.5)).toBe(7.5);
    const kei = new Set([8.24, 8.26, 9.26].map((m) => quantizeMlbFairTotal(m)));
    expect(kei).toEqual(new Set([8.0, 8.5, 9.5]));
  });

  it("half-even ties match Python 3 round(mean * 2) / 2", () => {
    expect(roundHalfEven(2.5)).toBe(2);
    expect(roundHalfEven(3.5)).toBe(4);
    expect(roundHalfEven(-2.5)).toBe(-2);
    expect(roundHalfEven(-3.5)).toBe(-4);
    expect(quantizeMlbFairTotal(8.25)).toBe(8.0);
    expect(quantizeMlbFairTotal(8.75)).toBe(9.0);
  });

  it("resolve prefers published fairTotal over raw mean", () => {
    const resolved = resolveMlbKeiTotal({
      fairTotal: 9.0,
      handicapTotal: 9.0,
      totalMean: 9.09,
    });
    expect(resolved.kei).toBe(9.0);
    expect(resolved.mean).toBe(9.09);
    expect(resolved.quantizedFromMean).toBe(false);
    expect(mlbKeiDiffersFromMean(resolved.kei, resolved.mean)).toBe(true);
    expect(formatMlbTotalMean(resolved.mean)).toBe("9.09");
  });

  it("resolve quantizes mean when published fair is missing", () => {
    const resolved = resolveMlbKeiTotal({
      fairTotal: null,
      totalMean: 9.09,
    });
    expect(resolved.kei).toBe(9.0);
    expect(resolved.mean).toBe(9.09);
    expect(resolved.quantizedFromMean).toBe(true);
    expect(resolved.quantization).toBe("nearest_half_run");
  });
});
