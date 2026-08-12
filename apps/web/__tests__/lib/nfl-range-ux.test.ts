import { describe, expect, it } from "vitest";
import {
  HIDE_PERCENTILES_LABEL,
  RANGE_LABEL,
  RANGE_TOOLTIP,
  SHOW_PERCENTILES_LABEL,
  formatPercentileReveal,
  formatRangeBand,
} from "@/lib/nfl-range-ux";

describe("nfl range UX copy", () => {
  it("keeps the casual column label free of percentile jargon", () => {
    expect(RANGE_LABEL).toBe("Range");
    expect(RANGE_LABEL.toLowerCase()).not.toContain("p10");
    expect(SHOW_PERCENTILES_LABEL).toBe("Show percentiles");
    expect(HIDE_PERCENTILES_LABEL).toBe("Hide percentiles");
  });

  it("explains the band without calling it a floor or ceiling", () => {
    expect(RANGE_TOOLTIP).toBe(
      "Most simulated seasons fall in this band (10th–90th percentile). Not a guaranteed floor or ceiling.",
    );
  });

  it("formats the sim band from p10–p90 values without relabeling them", () => {
    expect(formatRangeBand(8, 14)).toBe("8–14");
    expect(formatRangeBand(5.2, 15.8, 1)).toBe("5.2–15.8");
  });

  it("reveals p10 / p50 / p90 plus replicate count", () => {
    expect(
      formatPercentileReveal({
        p10: 8,
        p50: 11.2,
        p90: 14,
        nSims: 100_000,
        digits: 1,
      }),
    ).toBe("p10 8.0 · p50 11.2 · p90 14.0 · 100,000 sims");
  });
});
