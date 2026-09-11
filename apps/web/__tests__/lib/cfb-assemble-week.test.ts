import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  filterCfbCompletedEdgeBoardRows,
  filterCfbEdgeBoardRowsByWeek,
  isCfbAssembleWeekComplete,
  parseCfbAssembleWeek,
  resolveCfbCurrentAssembleWeek,
  scopeCfbLiveEdgeBoardRows,
} from "@/lib/cfb-edge-board-week";
import { stampCfbEdgeBoardWeek } from "@/lib/cfb-kei-artifacts";
import { edgeBoardAssembleHref } from "@/lib/edge-board-assemble-href";
import { cfbGamesMatch } from "@/lib/cfb-match-keys";

const webRoot = path.join(__dirname, "../..");

function readRel(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

/** Thu Sep 10 2026 16:00 UTC — W1 complete, W2 still upcoming. */
const SEP_10_2026 = Date.parse("2026-09-10T16:00:00Z");
/** Sat Aug 22 2026 — W0 still has unplayed accepted kickoffs. */
const AUG_22_2026 = Date.parse("2026-08-22T16:00:00Z");
/** Mon Aug 31 2026 — W0 kicked; W1 still upcoming. */
const AUG_31_2026 = Date.parse("2026-08-31T12:00:00Z");
/** Mon Sep 14 2026 — after W2 weekend. */
const SEP_14_2026 = Date.parse("2026-09-14T16:00:00Z");

describe("CFB assemble week param (customer honesty)", () => {
  it("parses explicit integer week ≥ 0; never coerces 2→1", () => {
    expect(parseCfbAssembleWeek("0", SEP_10_2026)).toBe(0);
    expect(parseCfbAssembleWeek("1", SEP_10_2026)).toBe(1);
    expect(parseCfbAssembleWeek("2", SEP_10_2026)).toBe(2);
    expect(parseCfbAssembleWeek("12", SEP_10_2026)).toBe(12);
  });

  it("missing/invalid week rolls to calendar current week (not pinned 1)", () => {
    expect(parseCfbAssembleWeek(undefined, SEP_10_2026)).toBe(2);
    expect(parseCfbAssembleWeek(null, SEP_10_2026)).toBe(2);
    expect(parseCfbAssembleWeek("", SEP_10_2026)).toBe(2);
    expect(parseCfbAssembleWeek("   ", SEP_10_2026)).toBe(2);
    expect(parseCfbAssembleWeek("foo", SEP_10_2026)).toBe(2);
    expect(parseCfbAssembleWeek("1.5", SEP_10_2026)).toBe(2);
    expect(parseCfbAssembleWeek("-1", SEP_10_2026)).toBe(2);
    expect(parseCfbAssembleWeek("NaN", SEP_10_2026)).toBe(2);
  });

  it("current-week rollover follows official slate kickoffs", () => {
    expect(resolveCfbCurrentAssembleWeek(AUG_22_2026)).toBe(0);
    expect(resolveCfbCurrentAssembleWeek(AUG_31_2026)).toBe(1);
    expect(resolveCfbCurrentAssembleWeek(SEP_10_2026)).toBe(2);
    expect(resolveCfbCurrentAssembleWeek(SEP_14_2026)).toBe(2);
  });

  it("excludes completed / already-started games server-side", () => {
    expect(
      isCfbAssembleWeekComplete({
        commenceTime: "2026-09-03T22:00:00Z",
        nowMs: SEP_10_2026,
      }),
    ).toBe(true);
    expect(
      isCfbAssembleWeekComplete({
        status: "final",
        kickoff: "2026-09-12T16:00:00Z",
        nowMs: SEP_10_2026,
      }),
    ).toBe(true);
    expect(
      isCfbAssembleWeekComplete({
        commenceTime: "2026-09-12T16:00:00Z",
        nowMs: SEP_10_2026,
      }),
    ).toBe(false);

    const mixed = [
      {
        game: "Massachusetts Minutemen @ Rutgers Scarlet Knights",
        week: 1,
        commenceTime: "2026-09-03T22:00:00Z",
      },
      {
        game: "Rutgers Scarlet Knights @ Boston College Eagles",
        week: 2,
        commenceTime: "2026-09-11T23:30:00Z",
      },
    ];
    const live = filterCfbCompletedEdgeBoardRows(mixed, SEP_10_2026);
    expect(live).toHaveLength(1);
    expect(live[0]?.week).toBe(2);
    expect(scopeCfbLiveEdgeBoardRows(mixed, 1, SEP_10_2026)).toEqual([]);
    expect(scopeCfbLiveEdgeBoardRows(mixed, 2, SEP_10_2026)).toHaveLength(1);
  });

  it("does not coerce week=2 onto week-1-stamped games", () => {
    const stamped = stampCfbEdgeBoardWeek([
      { game: "Ball State Cardinals @ Ohio State Buckeyes" },
      { game: "San Jose State Spartans @ USC Trojans" },
      { game: "Hawaii Rainbow Warriors @ Stanford Cardinal" },
    ]);
    expect(stamped.some((r) => r.week === 1)).toBe(true);
    expect(stamped.some((r) => r.week === 0)).toBe(true);

    const week2 = filterCfbEdgeBoardRowsByWeek(stamped, 2);
    expect(week2).toEqual([]);
    expect(week2.some((r) => r.week === 1)).toBe(false);
    expect(week2.some((r) => r.week === 0)).toBe(false);

    const week1 = filterCfbEdgeBoardRowsByWeek(stamped, 1);
    expect(week1.every((r) => r.week === 1)).toBe(true);
    expect(week1.length).toBeGreaterThan(0);
  });

  it("stamps Week 2 from the KEI pack without recycling Week 1", () => {
    const stamped = stampCfbEdgeBoardWeek([
      { game: "Rutgers Scarlet Knights @ Boston College Eagles" },
    ]);
    expect(stamped[0]?.week).toBe(2);
    expect(filterCfbEdgeBoardRowsByWeek(stamped, 1)).toEqual([]);
    expect(filterCfbEdgeBoardRowsByWeek(stamped, 2)).toHaveLength(1);
  });

  it("Fair and Market join the same canonical game identity", () => {
    expect(
      cfbGamesMatch(
        "Rutgers Scarlet Knights @ Boston College Eagles",
        "Rutgers @ Boston College",
      ),
    ).toBe(true);
    expect(
      cfbGamesMatch(
        "Massachusetts Minutemen @ Rutgers Scarlet Knights",
        "UMass Minutemen @ Rutgers Scarlet Knights",
      ),
    ).toBe(true);
    expect(
      cfbGamesMatch(
        "Oklahoma Sooners @ Michigan Wolverines",
        "Ohio State Buckeyes @ Michigan Wolverines",
      ),
    ).toBe(false);
  });

  it("href and SSR parse week=2 without collapsing to week=1", () => {
    expect(edgeBoardAssembleHref({ sportKey: "cfb", cfbWeek: 2 })).toBe(
      "/api/edge-board/cfb/assemble?week=2",
    );
    expect(edgeBoardAssembleHref({ sportKey: "cfb", cfbWeek: 0 })).toBe(
      "/api/edge-board/cfb/assemble?week=0",
    );
    expect(edgeBoardAssembleHref({ sportKey: "cfb", cfbWeek: 1 })).toBe(
      "/api/edge-board/cfb/assemble?week=1",
    );
    expect(edgeBoardAssembleHref({ sportKey: "cfb" })).toMatch(
      /\/api\/edge-board\/cfb\/assemble\?week=\d+/,
    );
    expect(edgeBoardAssembleHref({ sportKey: "cfb" })).not.toBe(
      "/api/edge-board/cfb/assemble?week=1",
    );

    const assemble = readRel("app/api/edge-board/[sport]/assemble/route.ts");
    expect(assemble).toContain("parseCfbAssembleWeek");
    expect(assemble).toContain("scopeCfbLiveEdgeBoardRows");
    const build = readRel("lib/build-edge-board-rows.ts");
    expect(build).toContain("loadCfbCurrentMarketRows");
    expect(build).toContain('sport === "cfb" ? oddsRows : withFallback');
    expect(assemble).toContain("requestedWeek");
    expect(assemble).not.toMatch(/get\("week"\) === ["']0["'] \? 0 : 1/);
    expect(assemble).not.toMatch(/week === ["']0["'] \? 0 : 1/);

    const page = readRel("app/edge-board/[sport]/page.tsx");
    expect(page).toContain("parseCfbAssembleWeek");
    expect(page).not.toMatch(/cfbWeekRaw === ["']0["'] \? 0 : 1/);

    const client = readRel("components/EdgeBoardSportClient.tsx");
    expect(client).toContain("/edge-board/cfb?week=2");
    expect(client).toContain("no silent Week 1 fallthrough");
  });
});
