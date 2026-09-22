import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { displayClubDeskTitle } from "@/lib/nfl-club-desk-routes";
import {
  currentNflRegWeekFromSchedule,
  nflRegWeekPostureLine,
  resolveCurrentNflRegWeek,
} from "@/lib/nfl-current-week";

/** Week 1 TNF kickoff — in progress. */
const WEEK1_FRIDAY = Date.parse("2026-09-11T16:00:00.000Z");
/** MNF DEN@KC still inside the 4h final buffer. */
const WEEK1_MNF_LIVE = Date.parse("2026-09-15T02:00:00.000Z");
/** Tuesday after MNF is FINAL — product week flips to 2. */
const WEEK2_TUESDAY = Date.parse("2026-09-15T16:00:00.000Z");
/** Before Week 1 first kickoff — upcoming Week 1 is proven. */
const PRE_WEEK1 = Date.parse("2026-09-08T16:00:00.000Z");

describe("resolveCurrentNflRegWeek", () => {
  it("keeps Week 1 while Sunday/MNF of Week 1 is not yet FINAL", () => {
    expect(resolveCurrentNflRegWeek(WEEK1_FRIDAY)).toEqual({
      week: 1,
      proven: true,
      reason: "in_progress",
      asOfMs: WEEK1_FRIDAY,
    });
    expect(currentNflRegWeekFromSchedule(WEEK1_FRIDAY)).toBe(1);
    expect(resolveCurrentNflRegWeek(WEEK1_MNF_LIVE).week).toBe(1);
  });

  it("flips to Week 2 after Week 1 last game is FINAL (Tue Sep 15 2026)", () => {
    const resolved = resolveCurrentNflRegWeek(WEEK2_TUESDAY);
    expect(resolved.week).toBe(2);
    expect(resolved.proven).toBe(true);
    expect(resolved.reason).toBe("prior_week_final");
    expect(currentNflRegWeekFromSchedule(WEEK2_TUESDAY)).toBe(2);
    expect(nflRegWeekPostureLine(WEEK2_TUESDAY)).toBe(
      "Week 2 REG live · PRE off board",
    );
  });

  it("stays proven Week 2 on Wednesday Sep 16 (TNF not yet kicked)", () => {
    const wed = Date.parse("2026-09-16T21:00:00.000Z");
    const resolved = resolveCurrentNflRegWeek(wed);
    expect(resolved.week).toBe(2);
    expect(resolved.proven).toBe(true);
    expect(resolved.reason).toBe("prior_week_final");
    expect(currentNflRegWeekFromSchedule(wed)).toBe(2);
    expect(nflRegWeekPostureLine(wed)).toBe("Week 2 REG live · PRE off board");
  });

  it("stays proven Week 2 on Thursday Sep 17 (pre-TNF kick)", () => {
    const thu = Date.parse("2026-09-17T20:00:00.000Z");
    const resolved = resolveCurrentNflRegWeek(thu);
    expect(resolved.week).toBe(2);
    expect(resolved.proven).toBe(true);
    expect(resolved.reason).toBe("prior_week_final");
    expect(currentNflRegWeekFromSchedule(thu)).toBe(2);
    expect(nflRegWeekPostureLine(thu)).toBe("Week 2 REG live · PRE off board");
  });

  it("flips to Week 3 after Week 2 last game is FINAL (Tue Sep 22 2026)", () => {
    const tue = Date.parse("2026-09-22T16:00:00.000Z");
    const resolved = resolveCurrentNflRegWeek(tue);
    expect(resolved.week).toBe(3);
    expect(resolved.proven).toBe(true);
    expect(resolved.reason).toBe("prior_week_final");
    expect(currentNflRegWeekFromSchedule(tue)).toBe(3);
    expect(nflRegWeekPostureLine(tue)).toBe("Week 3 REG live · PRE off board");
  });

  it("treats pre-kickoff as upcoming Week 1, not a silent pin", () => {
    const resolved = resolveCurrentNflRegWeek(PRE_WEEK1);
    expect(resolved).toEqual({
      week: 1,
      proven: true,
      reason: "upcoming",
      asOfMs: PRE_WEEK1,
    });
  });

  it("never silently returns Week 1 when the pack cannot prove a week", () => {
    const resolved = resolveCurrentNflRegWeek(WEEK2_TUESDAY, 1999);
    expect(resolved.week).toBeNull();
    expect(resolved.proven).toBe(false);
    expect(resolved.reason).toBe("unproven");
    expect(currentNflRegWeekFromSchedule(WEEK2_TUESDAY, 1999)).toBeNull();
    expect(nflRegWeekPostureLine(WEEK2_TUESDAY, 1999)).toMatch(/fail closed/i);
  });
});

describe("Club Desk / in-season landing redirects", () => {
  it("renames Camp Desk titles for customer chrome", () => {
    expect(displayClubDeskTitle("Camp Desk — Tuesday, Sep 15")).toBe(
      "Club Desk — Tuesday, Sep 15",
    );
    expect(displayClubDeskTitle("Training Camp desk notes")).toBe(
      "Club Desk notes",
    );
  });

  it("keeps /pro/nfl/camp and /pro/nfl/fantasy hops in next.config", () => {
    const src = readFileSync(resolve(process.cwd(), "next.config.ts"), "utf8");
    expect(src).toContain('source: "/pro/nfl/camp"');
    expect(src).toContain('destination: "/pro/nfl/club"');
    expect(src).toContain('source: "/pro/nfl/fantasy"');
    expect(src).toContain('destination: "/pro/nfl/dfs"');
  });

  it("hides mock as the Fantasy landing", () => {
    const landing = readFileSync(
      resolve(process.cwd(), "app/(pro)/pro/nfl/fantasy/page.tsx"),
      "utf8",
    );
    const mock = readFileSync(
      resolve(process.cwd(), "app/(pro)/pro/nfl/fantasy/mock/page.tsx"),
      "utf8",
    );
    expect(landing).toContain('redirect("/pro/nfl/dfs")');
    expect(mock).toMatch(/Drafts are over/i);
    expect(mock).toContain("/pro/nfl/dfs");
    expect(mock).not.toContain("FantasyMockDraftClient");
  });
});
