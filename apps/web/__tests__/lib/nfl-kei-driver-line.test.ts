import { describe, expect, it } from "vitest";
import { keiRepriceDriverLine } from "@/lib/nfl-kei-driver-line";

describe("keiRepriceDriverLine honesty", () => {
  it("surfaces applied factors and honest not-applied chips", () => {
    const line = keiRepriceDriverLine({
      appliedFactors: [
        { factor: "injury", reason: "Mahomes questionable — current vs full" },
      ],
      consideredNotApplied: [
        {
          factor: "weather",
          reason: "weather not applied (indoor)",
        },
        {
          factor: "short_week",
          reason: "short_week not applied (Week 1, no prior REG rest gap)",
        },
        {
          factor: "weather",
          reason: "weather not applied (duplicate)",
        },
      ],
    });
    expect(line).toContain("Mahomes questionable");
    expect(line).toContain("weather not applied (indoor)");
    expect(line).toContain("short_week not applied");
    expect(line).not.toContain("duplicate");
  });

  it("returns null when skipped or empty", () => {
    expect(keiRepriceDriverLine(null)).toBeNull();
    expect(
      keiRepriceDriverLine({
        skipped: true,
        appliedFactors: [{ factor: "weather", reason: "x" }],
        consideredNotApplied: [],
      }),
    ).toBeNull();
    expect(
      keiRepriceDriverLine({ appliedFactors: [], consideredNotApplied: [] }),
    ).toBeNull();
  });
});
