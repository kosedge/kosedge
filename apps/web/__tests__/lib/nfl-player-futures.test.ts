import { describe, expect, it } from "vitest";
import {
  AWARD_CURRENT_CONVENTION,
  formatCurrentOdds,
  formatCurrentYtd,
  formatProjectedValue,
  sumNullable,
} from "@/lib/nfl-player-futures";

describe("nfl-player-futures columns", () => {
  it("formats projected counting and percent values with units", () => {
    expect(formatProjectedValue(1245.6, { unit: "yds" })).toBe("1246 yds");
    expect(formatProjectedValue(12.34, { digits: 1, unit: "TDs" })).toBe(
      "12.3 TDs",
    );
    expect(formatProjectedValue(0.452, { digits: 1, percent: true })).toBe(
      "45.2%",
    );
    expect(formatProjectedValue(null)).toBe("—");
  });

  it("uses 0 for counting Current when YTD is missing (preseason)", () => {
    expect(formatCurrentYtd(null, "counting")).toBe("0");
    expect(formatCurrentYtd(undefined, "counting", 1)).toBe("0.0");
    expect(formatCurrentYtd(18, "counting")).toBe("18");
  });

  it("uses em dash for award Current (no fake progress)", () => {
    expect(AWARD_CURRENT_CONVENTION).toBe("emdash");
    expect(formatCurrentYtd(null, "award")).toBe("—");
    expect(formatCurrentYtd(0, "award")).toBe("—");
    expect(formatCurrentYtd(5, "award")).toBe("—");
  });

  it("never invents Current odds", () => {
    expect(formatCurrentOdds(null)).toBe("—");
    expect(formatCurrentOdds({ american: null, book: null, asOfUtc: null })).toBe(
      "—",
    );
    expect(
      formatCurrentOdds({ american: 650, book: "DraftKings", asOfUtc: null }),
    ).toBe("+650");
    expect(
      formatCurrentOdds({ american: -150, book: "FanDuel", asOfUtc: null }),
    ).toBe("-150");
  });

  it("sums nullable YTD fields without inventing when all null", () => {
    expect(sumNullable(null, null, null)).toBeNull();
    expect(sumNullable(10, null, 5)).toBe(15);
  });
});
