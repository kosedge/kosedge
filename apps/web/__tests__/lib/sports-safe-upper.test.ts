import { describe, expect, it } from "vitest";
import {
  resolveSportKey,
  safeUpperCase,
  sportDisplayLabel,
} from "@/lib/sports";

describe("safeUpperCase / sport display helpers", () => {
  it("safeUpperCase never throws on nullish or empty values", () => {
    expect(safeUpperCase(undefined)).toBe("");
    expect(safeUpperCase(null)).toBe("");
    expect(safeUpperCase("")).toBe("");
    expect(safeUpperCase("  ")).toBe("");
    expect(safeUpperCase(undefined, "NFL")).toBe("NFL");
    expect(safeUpperCase("nfl")).toBe("NFL");
    expect(safeUpperCase(" kc ")).toBe("KC");
  });

  it("resolveSportKey normalizes and falls back", () => {
    expect(resolveSportKey(undefined)).toBe("");
    expect(resolveSportKey(null, "nfl")).toBe("nfl");
    expect(resolveSportKey("NFL")).toBe("nfl");
    expect(resolveSportKey("  Mlb ")).toBe("mlb");
  });

  it("sportDisplayLabel matches the production crash pattern safely", () => {
    // Historical crash: `sport?.fullName ?? sportKey.toUpperCase()` when sportKey is undefined
    expect(sportDisplayLabel(undefined)).toBe("Sport");
    expect(sportDisplayLabel(null)).toBe("Sport");
    expect(sportDisplayLabel("nfl")).toBe("NFL");
    expect(sportDisplayLabel("cfb")).toBe("College Football");
    expect(sportDisplayLabel("unknown-sport")).toBe("UNKNOWN-SPORT");
  });
});
