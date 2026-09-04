import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import {
  NFL_PROPS_BOARD_NOT_LIVE_PHRASE,
  NFL_PROPS_BOARD_STALE_HONESTY_TITLE,
  formatNflPropsBoardPeriod,
  nflPropsBoardStaleHonestyBody,
  resolveNflPropsBoardStamp,
} from "@/lib/nfl-props-header";
import { formatNflWeekLabel } from "@/lib/nfl-truth-label";

const webRoot = path.join(__dirname, "../..");

function readRel(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

/** Calendar still inside the Labor Day preseason window (live bug window). */
const SEP_2_2026 = new Date("2026-09-02T23:04:00Z");

/** Live www Jul-vintage board as-of (NFL-V2 / H-2 / 13b). */
const JUL_20_2026_ASOF = "2026-07-20T23:21:00.000Z";
const SEP_4_2026_NOW = Date.parse("2026-09-04T15:00:00.000Z");

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

  it("marks Week chrome not-live when board as-of is stale (13b)", () => {
    expect(formatNflPropsBoardPeriod(2026, 1, { boardStale: true })).toBe(
      `2026 · Week 1 REG · ${NFL_PROPS_BOARD_NOT_LIVE_PHRASE}`,
    );
    expect(formatNflPropsBoardPeriod(2026, 1, { boardStale: true })).toContain(
      "not live board",
    );
    // Fresh board keeps plain Week chrome.
    expect(formatNflPropsBoardPeriod(2026, 1, { boardStale: false })).toBe(
      "2026 · Week 1 REG",
    );
  });
});

describe("13b — Jul-vintage stale as-of honesty (no invent fresher)", () => {
  it("Jul 20 as-of stamps stale and keeps real vintage text", () => {
    const stamp = resolveNflPropsBoardStamp(JUL_20_2026_ASOF, SEP_4_2026_NOW);
    expect(stamp.missing).toBe(false);
    expect(stamp.stale).toBe(true);
    expect(stamp.asOfIso).toBe(JUL_20_2026_ASOF);
    expect(stamp.text).toMatch(/^Board as of /);
    expect(stamp.text).toMatch(/Jul/);
    expect(stamp.text).toContain("stale");
    // Must not invent a Sep / "as of now" clock.
    expect(stamp.text).not.toMatch(/Sep/);
    expect(stamp.text).not.toMatch(/as of now/i);
  });

  it("stale honesty body ties Week chrome to real stamp — never hides Jul", () => {
    const stamp = resolveNflPropsBoardStamp(JUL_20_2026_ASOF, SEP_4_2026_NOW);
    const body = nflPropsBoardStaleHonestyBody({
      season: 2026,
      week: 1,
      stampText: stamp.text,
    });
    expect(body).toContain("2026 · Week 1 REG");
    expect(body).toContain(stamp.text);
    expect(body).toMatch(/not a live\/current props board/i);
    expect(body).toMatch(/do not invent fresher/i);
    expect(body).toMatch(/Jul/);
    expect(NFL_PROPS_BOARD_STALE_HONESTY_TITLE).toMatch(/not live truth/i);
  });

  it("blank as-of is missing (not stale) — no invent clock", () => {
    const stamp = resolveNflPropsBoardStamp(null, SEP_4_2026_NOW);
    expect(stamp.missing).toBe(true);
    expect(stamp.stale).toBe(false);
    expect(stamp.text).toBe("Market as-of unavailable");
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

  it("wires 13b stale honesty banner when board as-of is stale", () => {
    const page = readRel("app/(pro)/pro/nfl/props/page.tsx");

    expect(page).toContain("resolveNflPropsBoardStamp");
    expect(page).toContain("nflPropsBoardStaleHonestyBody");
    expect(page).toContain("NFL_PROPS_BOARD_STALE_HONESTY_TITLE");
    expect(page).toContain('data-testid="props-board-stale-honesty"');
    expect(page).toContain("boardStale");
    // Honesty path only — must not invent fresher clocks or remat.
    expect(page).not.toMatch(/Date\.now\(\)/);
    expect(page).not.toMatch(/new Date\(\)\.toISOString/);
    expect(page).not.toMatch(/\bremat\b/i);
    expect(page).not.toMatch(/\bcelery\b/i);
  });
});
