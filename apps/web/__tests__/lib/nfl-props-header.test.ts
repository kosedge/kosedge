import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { formatNflPropsBoardPeriod } from "@/lib/nfl-props-header";
import { formatNflWeekLabel } from "@/lib/nfl-truth-label";

const webRoot = path.join(__dirname, "../..");

function readRel(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

/** Calendar still inside the Labor Day preseason window (live bug window). */
const SEP_2_2026 = new Date("2026-09-02T23:04:00Z");

describe("formatNflPropsBoardPeriod — Preseason vs Week 1 REG", () => {
  it("labels Week 1 REG spine as Week 1 REG (not calendar Preseason)", () => {
    // Live bug: formatNflWeekLabel(1) still said Preseason on Sep 2 while
    // Edge Board said Week 1 REG. Props period must follow spine week.
    expect(formatNflWeekLabel(1, { season: 2026, now: SEP_2_2026 })).toBe(
      "Preseason",
    );
    expect(formatNflPropsBoardPeriod(2026, 1)).toBe("2026 · Week 1 REG");
    expect(formatNflPropsBoardPeriod(2026, 1, { seasonType: "REG" })).toBe(
      "2026 · Week 1 REG",
    );
    expect(formatNflPropsBoardPeriod(2026, 1)).not.toMatch(/Preseason/i);
  });

  it("reserves Preseason only for explicit PRE season type", () => {
    expect(formatNflPropsBoardPeriod(2026, 1, { seasonType: "PRE" })).toBe(
      "2026 Preseason",
    );
    expect(formatNflPropsBoardPeriod(2026, 3, { seasonType: "pre" })).toBe(
      "2026 Preseason",
    );
  });

  it("labels later REG weeks without inventing Preseason", () => {
    expect(formatNflPropsBoardPeriod(2026, 2)).toBe("2026 · Week 2 REG");
    expect(formatNflPropsBoardPeriod(2026, 18)).toBe("2026 · Week 18 REG");
  });

  it("labels POST when asked; refuses blank week/season chrome", () => {
    expect(formatNflPropsBoardPeriod(2026, 19, { seasonType: "POST" })).toBe(
      "2026 · Week 19 POST",
    );
    expect(formatNflPropsBoardPeriod(NaN, 1)).toBe(
      "Props board week unavailable",
    );
    expect(formatNflPropsBoardPeriod(2026, 0)).toBe(
      "Props board week unavailable",
    );
  });
});

describe("Props page header honesty wiring", () => {
  it("drops editorial August 11; keeps board as-of stamp; uses REG period", () => {
    const page = readRel("app/(pro)/pro/nfl/props/page.tsx");

    expect(page).toContain("formatNflPropsBoardPeriod");
    expect(page).toContain("MarketAsOfStamp");
    expect(page).toContain("boardAsOfFromUpdatedAts");
    expect(page).toContain('data-testid="props-board-period"');
    expect(page).toContain('data-testid="props-board-asof"');
    expect(page).toContain('kind="board"');

    // Stale editorial launch date must not reappear as dual Date: chrome.
    expect(page).not.toMatch(/\bKOSEDGE_DATE\b/);
    expect(page).not.toContain("August 11, 2026");
    expect(page).not.toMatch(/Date:\s*\{/);
    // Calendar truth-label Preseason path must not drive this header.
    expect(page).not.toContain("formatNflWeekLabel");
    // Game-start helpers are not line vintage on this surface.
    expect(page).not.toContain("formatKickoff");
    expect(page).not.toContain("commence_time");
  });
});
