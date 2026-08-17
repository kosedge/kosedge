import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { cfbKeiGames } from "@/lib/cfb-kei-artifacts";
import {
  gamesForWeek,
  officialSlateAttribution,
  packagedOfficialWeekBoard,
  parseOfficialSlateWeek,
  resolveWeekBoard,
} from "@/lib/cfb-official-slate";
import { buildProjectGameBody } from "@/lib/cfb-season-engine-format";

describe("cfb official slate in-house SoT", () => {
  it("publishes W0 + W1 from the KosEdge artifact, not a remote override", () => {
    const board = packagedOfficialWeekBoard();
    expect(board.used_in_spread).toBe(false);
    expect(board.kei).toBe(false);
    expect(board.official).toBe(true);
    expect(board.source).toBe("kosedge_official_slate");
    expect(board.primary_source).toBe("espn_team_schedule_public");
    expect(board.factcheck_source).toBe("the_odds_api_ncaaf_events");
    expect(board.slate_version).toMatch(/cfb-official-slate/);
    const w0 = gamesForWeek(board, 0);
    const w1 = gamesForWeek(board, 1);
    expect(w0.length).toBe(8);
    expect(w1.length).toBe(89);
    expect(w0.filter((g) => g.fbs_vs_fbs)).toHaveLength(6);
    expect(w1.filter((g) => g.fbs_vs_fbs)).toHaveLength(43);
    expect(w0.some((g) => g.home === "TCU" && g.away === "UNC")).toBe(true);
    expect(w0.some((g) => g.home === "USC" && g.away === "SJSU")).toBe(true);
    expect(w0.some((g) => g.home === "STAN" && g.away === "HAW")).toBe(true);
    expect(officialSlateAttribution(board)).toContain("ESPN");
    expect(officialSlateAttribution(board)).toContain("The Odds API");
  });

  it("keeps the KosEdge artifact when a remote board is present", () => {
    const remote = resolveWeekBoard({
      games: [{ week: 0, home: "AAA", away: "BBB" }],
    });
    expect(remote.games?.some((g) => g.home === "TCU")).toBe(true);
    expect(remote.games?.some((g) => g.home === "AAA")).toBe(false);
  });

  it("fact-checks W0 FBS–FBS and does not invent only-secondary games", () => {
    const board = packagedOfficialWeekBoard();
    const w0Fbs = gamesForWeek(board, 0).filter((g) => g.fbs_vs_fbs);
    expect(w0Fbs.every((g) => g.status === "accepted")).toBe(true);
    expect(board.factcheck?.conflicts).toEqual([]);
    expect(board.games?.some((g) => g.home === "AAA")).toBe(false);
  });

  it("aligns published KEI game_ids to the official slate", () => {
    const slateIds = new Set(
      (packagedOfficialWeekBoard().games ?? [])
        .map((g) => g.game_id)
        .filter(Boolean),
    );
    const kei = cfbKeiGames().filter((g) => g.fbs_vs_fbs && g.game_id);
    expect(kei.length).toBeGreaterThanOrEqual(49);
    for (const g of kei) {
      expect(slateIds.has(String(g.game_id))).toBe(true);
    }
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
    expect(parseOfficialSlateWeek("1")).toBe(1);
    expect(parseOfficialSlateWeek("9")).toBe(0);
  });

  it("registers the missing production routes", () => {
    const root = path.join(__dirname, "../../app/(pro)/pro/cfb");
    for (const page of ["slate", "projections", "teams", "futures"]) {
      const src = readFileSync(path.join(root, page, "page.tsx"), "utf8");
      expect(src).toContain("used_in_spread");
      expect(src).not.toMatch(/auto-tag \"PLAY\"/i);
    }
  });
});
