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

const webRoot = path.join(__dirname, "../..");

/**
 * #8 honesty slice 13b / NFL-V2 H-2 — Week 1 REG chrome must not imply
 * live/current board truth when board as-of is Jul-vintage stale.
 * KOS-15: no silent stale fallback; freshness = honesty only, not remat.
 * Keep real as-of · stale visible; never invent fresher prices.
 */
describe("NFL props 13b stale as-of honesty (source lock)", () => {
  it("page mounts stale honesty banner + period not-live qualifier", () => {
    const page = readFileSync(
      path.join(webRoot, "app/(pro)/pro/nfl/props/page.tsx"),
      "utf8",
    );

    expect(page).toContain('data-testid="props-board-stale-honesty"');
    expect(page).toContain('data-testid="props-board-asof"');
    expect(page).toContain('data-testid="props-board-period"');
    expect(page).toContain("NFL_PROPS_BOARD_STALE_HONESTY_TITLE");
    expect(page).toContain("nflPropsBoardStaleHonestyBody");
    expect(page).toContain("resolveNflPropsBoardStamp");
    expect(page).toContain("boardStale");
    // Real stamp path preserved — no invent-now / editorial date.
    expect(page).toContain("MarketAsOfStamp");
    expect(page).toContain("boardAsOfFromUpdatedAts");
    expect(page).not.toContain("August 11, 2026");
    expect(page).not.toMatch(/Date\.now\(\)/);
  });

  it("Jul-vintage stamp stays stale; Week chrome gains not-live phrase", () => {
    const asOf = "2026-07-20T23:21:00.000Z";
    const nowMs = Date.parse("2026-09-04T15:00:00.000Z");
    const stamp = resolveNflPropsBoardStamp(asOf, nowMs);

    expect(stamp.stale).toBe(true);
    expect(stamp.asOfIso).toBe(asOf);
    expect(stamp.text).toMatch(/Jul/);
    expect(stamp.text).toContain("stale");

    const period = formatNflPropsBoardPeriod(2026, 1, {
      boardStale: stamp.stale,
    });
    expect(period).toBe(`2026 · Week 1 REG · ${NFL_PROPS_BOARD_NOT_LIVE_PHRASE}`);

    const body = nflPropsBoardStaleHonestyBody({
      season: 2026,
      week: 1,
      stampText: stamp.text,
    });
    expect(body).toContain(stamp.text);
    expect(body).toMatch(/not a live\/current props board/i);
    expect(NFL_PROPS_BOARD_STALE_HONESTY_TITLE).toMatch(/Week chrome/i);
  });
});
