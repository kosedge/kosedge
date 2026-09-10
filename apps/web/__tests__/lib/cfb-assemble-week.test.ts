import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  filterCfbEdgeBoardRowsByWeek,
  parseCfbAssembleWeek,
} from "@/lib/cfb-edge-board-week";
import { stampCfbEdgeBoardWeek } from "@/lib/cfb-kei-artifacts";
import { edgeBoardAssembleHref } from "@/lib/edge-board-assemble-href";

const webRoot = path.join(__dirname, "../..");

function readRel(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

describe("CFB assemble week param (customer honesty)", () => {
  it("parses integer week ≥ 0; default 1 when missing or invalid", () => {
    expect(parseCfbAssembleWeek(undefined)).toBe(1);
    expect(parseCfbAssembleWeek(null)).toBe(1);
    expect(parseCfbAssembleWeek("")).toBe(1);
    expect(parseCfbAssembleWeek("   ")).toBe(1);
    expect(parseCfbAssembleWeek("foo")).toBe(1);
    expect(parseCfbAssembleWeek("1.5")).toBe(1);
    expect(parseCfbAssembleWeek("-1")).toBe(1);
    expect(parseCfbAssembleWeek("NaN")).toBe(1);
    expect(parseCfbAssembleWeek("0")).toBe(0);
    expect(parseCfbAssembleWeek("1")).toBe(1);
    expect(parseCfbAssembleWeek("2")).toBe(2);
    expect(parseCfbAssembleWeek("12")).toBe(12);
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

  it("href and SSR parse week=2 without collapsing to week=1", () => {
    expect(edgeBoardAssembleHref({ sportKey: "cfb", cfbWeek: 2 })).toBe(
      "/api/edge-board/cfb/assemble?week=2",
    );
    expect(edgeBoardAssembleHref({ sportKey: "cfb", cfbWeek: 0 })).toBe(
      "/api/edge-board/cfb/assemble?week=0",
    );
    expect(edgeBoardAssembleHref({ sportKey: "cfb" })).toBe(
      "/api/edge-board/cfb/assemble?week=1",
    );

    const assemble = readRel("app/api/edge-board/[sport]/assemble/route.ts");
    expect(assemble).toContain("parseCfbAssembleWeek");
    expect(assemble).toContain("filterCfbEdgeBoardRowsByWeek");
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
