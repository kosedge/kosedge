import { describe, expect, it } from "vitest";
import {
  formatNflBoardWeekLabel,
  resolveNflProjectionDefaultWeek,
} from "@/lib/nfl-board-week-label";

describe("nfl-board-week-label", () => {
  it("labels ordinary weeks normally", () => {
    expect(formatNflBoardWeekLabel(1)).toBe("Week 1");
    expect(formatNflBoardWeekLabel(17, { hasRowsForCurrentWeek: true })).toBe(
      "Week 17",
    );
  });

  it("does not present Week 18 MAX fallback as current when slate is empty", () => {
    expect(
      formatNflBoardWeekLabel(18, {
        hasRowsForCurrentWeek: false,
        lineCount: 0,
        slateStatus: "preseason_empty",
        now: new Date("2026-08-12T16:00:00Z"),
        season: 2026,
      }),
    ).toBe("Preseason");
  });

  it("treats Week 18 as Preseason in August even without an empty-slate flag", () => {
    expect(
      formatNflBoardWeekLabel(18, {
        now: new Date("2026-08-12T16:00:00Z"),
        season: 2026,
      }),
    ).toBe("Preseason");
  });

  it("clamps projection default week off stale Week 18", () => {
    expect(resolveNflProjectionDefaultWeek(18)).toBe(1);
    expect(resolveNflProjectionDefaultWeek(3)).toBe(3);
    expect(resolveNflProjectionDefaultWeek(null)).toBe(1);
  });
});
