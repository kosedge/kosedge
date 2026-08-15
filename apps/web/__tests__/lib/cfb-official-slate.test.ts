import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  gamesForWeek,
  packagedOfficialWeekBoard,
  resolveWeekBoard,
} from "@/lib/cfb-official-slate";
import { buildProjectGameBody } from "@/lib/cfb-season-engine-format";

describe("cfb official slate fallback", () => {
  it("ships Week 0 and Week 1 games without KEI", () => {
    const board = packagedOfficialWeekBoard();
    expect(board.used_in_spread).toBe(false);
    expect(board.kei).toBe(false);
    expect(board.official).toBe(true);
    const w0 = gamesForWeek(board, 0);
    const w1 = gamesForWeek(board, 1);
    expect(w0.length).toBeGreaterThanOrEqual(6);
    expect(w1.length).toBeGreaterThanOrEqual(20);
    expect(w0.some((g) => g.home === "TCU" && g.away === "UNC")).toBe(true);
  });

  it("prefers a remote board when it has games", () => {
    const remote = resolveWeekBoard({
      games: [{ week: 0, home: "AAA", away: "BBB" }],
    });
    expect(remote.games?.[0]?.home).toBe("AAA");
    const fallback = resolveWeekBoard({ games: [] });
    expect((fallback.games?.length ?? 0) > 0).toBe(true);
  });

  it("allows Week 0 project-game bodies", () => {
    expect(
      buildProjectGameBody({
        homeTeam: "TCU",
        awayTeam: "UNC",
        week: 0,
        neutralSite: true,
      }).week,
    ).toBe(0);
  });

  it("registers the missing production routes", () => {
    const root = path.join(__dirname, "../../app/(pro)/pro/cfb");
    for (const page of ["slate", "projections", "teams"]) {
      const src = readFileSync(path.join(root, page, "page.tsx"), "utf8");
      expect(src).toContain("used_in_spread");
      expect(src.toLowerCase()).not.toContain("play tag");
    }
  });
});
