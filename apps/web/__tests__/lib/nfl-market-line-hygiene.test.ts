import { describe, expect, it } from "vitest";
import {
  isPlausibleNflCurrentDisplay,
  sanitizeNflMl,
  sanitizeNflSpread,
  sanitizeNflTotal,
} from "@/lib/nfl-market-line-hygiene";

describe("nfl-market-line-hygiene", () => {
  it("keeps posted NFL book shapes", () => {
    expect(sanitizeNflSpread(-3.5).value).toBe(-3.5);
    expect(sanitizeNflSpread(-3).value).toBe(-3);
    expect(sanitizeNflSpread(0.5).value).toBe(0.5);
    expect(sanitizeNflTotal(44.5).value).toBe(44.5);
    expect(sanitizeNflMl(-150).value).toBe(-150);
    expect(sanitizeNflMl(1.91).value).toBe(1.91);
  });

  it("rejects 3.8 / 2.4 / AVG tenths and does not round them", () => {
    expect(sanitizeNflSpread(-3.58)).toEqual({
      value: null,
      reason: "not_half_point",
    });
    expect(sanitizeNflSpread(3.8).value).toBeNull();
    expect(sanitizeNflSpread(2.4).value).toBeNull();
    expect(sanitizeNflSpread(0.17).value).toBeNull();
    expect(sanitizeNflTotal(44.42).value).toBeNull();
    expect(sanitizeNflTotal(2.4).value).toBeNull();
    expect(sanitizeNflSpread(-110).reason).toBe("looks_like_ml");
  });

  it("accepts away-spread display labels only when book-shaped", () => {
    expect(isPlausibleNflCurrentDisplay("+3.5", "spread")).toBe(true);
    expect(isPlausibleNflCurrentDisplay("+3.8", "spread")).toBe(false);
    expect(isPlausibleNflCurrentDisplay("44.5", "total")).toBe(true);
    expect(isPlausibleNflCurrentDisplay("2.4", "total")).toBe(false);
  });
});
