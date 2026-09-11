import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  NFL_WEEKLY_SLATE_MAX_DAYS_AHEAD,
  nflWeeklySlateFairLinesWindow,
  resolveNflWeeklySlateWeeks,
} from "@/lib/nfl-slate-window";

const SEP_11_2026 = Date.parse("2026-09-11T16:00:00.000Z");

describe("nflWeeklySlateFairLinesWindow", () => {
  it("sizes today to current + next REG week, not a season pull", () => {
    const window = nflWeeklySlateFairLinesWindow("today", SEP_11_2026);
    expect(window.weeks).toEqual([1, 2]);
    expect(window.daysAhead).toBeLessThanOrEqual(
      NFL_WEEKLY_SLATE_MAX_DAYS_AHEAD,
    );
    expect(window.daysAhead).toBeGreaterThanOrEqual(10);
    expect(window.includePastDays).toBeLessThanOrEqual(7);
    expect(window.daysAhead).toBeLessThan(120);
  });

  it("sizes an explicit week to that week's kickoffs only", () => {
    const window = nflWeeklySlateFairLinesWindow("week-1", SEP_11_2026);
    expect(window.weeks).toEqual([1]);
    expect(window.daysAhead).toBeLessThanOrEqual(8);
    expect(window.daysAhead).toBeLessThan(NFL_WEEKLY_SLATE_MAX_DAYS_AHEAD);
  });

  it("never returns the 120-day season horizon", () => {
    for (const token of ["today", "week-1", "week-2", "2026-09-13"]) {
      const window = nflWeeklySlateFairLinesWindow(token, SEP_11_2026);
      expect(window.daysAhead).toBeLessThanOrEqual(
        NFL_WEEKLY_SLATE_MAX_DAYS_AHEAD,
      );
    }
  });

  it("resolves today weeks from the schedule, not the model", () => {
    expect(resolveNflWeeklySlateWeeks("today", SEP_11_2026)).toEqual([1, 2]);
    expect(resolveNflWeeklySlateWeeks("week-99", SEP_11_2026)).toEqual([99]);
  });
});

describe("Weekly Slate SSR request shape", () => {
  it("does not hardcode a 120-day live fair-lines pull", () => {
    const src = readFileSync(
      resolve(process.cwd(), "lib/nfl-slate.ts"),
      "utf8",
    );
    expect(src).not.toMatch(/daysAhead:\s*120/);
    expect(src).toContain("nflWeeklySlateFairLinesWindow");
    expect(src).toContain('oddsMode: "skip"');
    expect(src).toContain("isNflPreseasonDeskWindow");
  });
});
