import { describe, expect, it } from "vitest";
import { pickDeskVoice, stableGameHash } from "@/lib/edge-board-desk-voices";
import {
  allowsRecentFormLanguage,
  copyContainsForbiddenWeek1Form,
  resolveSeasonFormGate,
} from "@/lib/edge-board-season-gates";
import { buildMatchupContext } from "@/lib/edge-board-matchup-context";
import { buildMatchupOverview } from "@/lib/edge-board-matchup-overview";
import {
  assertStatDropSchema,
  buildStatDrop,
  STAT_DROP_SLOT_IDS,
} from "@/lib/edge-board-stat-drop";
import { lookupNflNeutralSite } from "@/lib/nfl-neutral-sites-2026";
import { enrichNflEdgeBoardMatchupFields } from "@/lib/edge-board-matchup-enrich";
import type { EdgeBoardRow } from "@kosedge/contracts";

describe("edge-board season gates", () => {
  it("treats week 1 as week1 gate", () => {
    expect(resolveSeasonFormGate({ week: 1 })).toBe("week1");
    expect(allowsRecentFormLanguage("week1")).toBe(false);
  });

  it("treats first team game as week1 even mid schedule", () => {
    expect(
      resolveSeasonFormGate({
        week: 5,
        gamesPlayedAway: 0,
        gamesPlayedHome: 4,
      }),
    ).toBe("week1");
  });

  it("marks games 2–4 as early", () => {
    expect(
      resolveSeasonFormGate({
        week: 3,
        gamesPlayedAway: 2,
        gamesPlayedHome: 2,
      }),
    ).toBe("early");
  });

  it("allows form language midseason", () => {
    expect(
      resolveSeasonFormGate({
        week: 10,
        gamesPlayedAway: 9,
        gamesPlayedHome: 9,
      }),
    ).toBe("mid");
    expect(allowsRecentFormLanguage("mid")).toBe(true);
  });
});

describe("desk voice stability", () => {
  it("is stable for the same game id", () => {
    const a = pickDeskVoice("NE@SEA-w1");
    const b = pickDeskVoice("NE@SEA-w1");
    expect(a).toBe(b);
    expect(stableGameHash("NE@SEA-w1")).toBe(stableGameHash("NE@SEA-w1"));
  });

  it("varies across games", () => {
    const voices = new Set(
      ["g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8"].map(pickDeskVoice),
    );
    expect(voices.size).toBeGreaterThan(1);
  });
});

describe("matchup overview + season honesty", () => {
  it("week-1 overview forbids recent-form language and states uncertainty", () => {
    const ctx = buildMatchupContext({
      gameId: "NE@SEA-2026w1",
      awayName: "New England Patriots",
      homeName: "Seattle Seahawks",
      awayAbbr: "NE",
      homeAbbr: "SEA",
      week: 1,
      keiSpreadHome: -3.5,
      marketSpreadHome: -3.0,
      keiTotal: 41.5,
      marketTotal: 44.5,
      homeWinProb: 0.58,
      awayWinProb: 0.42,
      modelPowerAway: 8.2,
      modelPowerHome: 9.1,
    });
    const overview = buildMatchupOverview(ctx);
    expect(overview.bottomLine.length).toBeGreaterThan(20);
    expect(overview.whatMatters.length).toBeGreaterThanOrEqual(2);
    expect(overview.whatMatters.length).toBeLessThanOrEqual(4);
    expect(overview.watch.length).toBeGreaterThan(10);
    expect(overview.text).toContain("Bottom line");
    expect(overview.text).toContain("What matters");
    expect(overview.text).toContain("What flips");
    expect(overview.text).not.toMatch(/(^|\n)Watch(\n|$)/);
    expect(overview.uncertainty).toMatch(/Early-season/i);
    expect(copyContainsForbiddenWeek1Form(overview.text)).toBe(false);
    expect(overview.text.toLowerCase()).not.toContain("recent form");
    expect(overview.text.toLowerCase()).not.toContain("recent turnover");
  });

  it("neutral Melbourne game labels site and zeros HFA language", () => {
    const site = lookupNflNeutralSite({
      week: 1,
      homeAbbr: "LAR",
      awayAbbr: "SF",
    });
    expect(site?.city).toBe("Melbourne");
    // Pair-only fallback when week is missing on the board row.
    expect(
      lookupNflNeutralSite({ week: null, homeAbbr: "LAR", awayAbbr: "SF" })
        ?.city,
    ).toBe("Melbourne");

    const ctx = buildMatchupContext({
      gameId: "SF@LAR-2026w1-melbourne",
      awayName: "San Francisco 49ers",
      homeName: "Los Angeles Rams",
      awayAbbr: "SF",
      homeAbbr: "LAR",
      week: 1,
      keiSpreadHome: -2.5,
      marketSpreadHome: -2.5,
      keiTotal: 45.5,
      marketTotal: 46.0,
      homeWinProb: 0.55,
      modelPowerAway: 10.1,
      modelPowerHome: 9.8,
    });
    expect(ctx.isNeutral).toBe(true);
    expect(ctx.siteCity).toBe("Melbourne");
    expect(ctx.hfaPoints).toBe(0);
    const overview = buildMatchupOverview(ctx);
    expect(overview.text).toMatch(/Melbourne|Neutral/i);
    expect(overview.text.toLowerCase()).not.toContain("home crowd");
    const drop = buildStatDrop(ctx);
    expect(drop.slots.find((s) => s.id === "site")?.value).toMatch(/Neutral/);
    expect(drop.slots.find((s) => s.id === "site")?.value).toMatch(/Melbourne/);
  });

  it("says so when KEI ≈ market (no forced lean)", () => {
    const ctx = buildMatchupContext({
      gameId: "market-close-1",
      awayName: "Buffalo Bills",
      homeName: "Miami Dolphins",
      awayAbbr: "BUF",
      homeAbbr: "MIA",
      week: 8,
      gamesPlayedAway: 7,
      gamesPlayedHome: 7,
      keiSpreadHome: -3.0,
      marketSpreadHome: -3.0,
      keiTotal: 47.5,
      marketTotal: 47.0,
      modelPowerAway: 11.2,
      modelPowerHome: 8.4,
    });
    const overview = buildMatchupOverview(ctx);
    // market voice may or may not be selected; structure still honest
    const drop = buildStatDrop(ctx);
    expect(drop.hasPower).toBe(true);
    expect(
      overview.text.includes("≈") ||
        overview.text.toLowerCase().includes("no forced") ||
        overview.text.toLowerCase().includes("aligned") ||
        overview.text.toLowerCase().includes("fairly"),
    ).toBe(true);
  });
});

describe("Stat Drop schema", () => {
  it("always emits 8 slots with power when KEI exists", () => {
    const ctx = buildMatchupContext({
      gameId: "stat-drop-1",
      awayName: "Kansas City Chiefs",
      homeName: "Denver Broncos",
      awayAbbr: "KC",
      homeAbbr: "DEN",
      week: 1,
      keiSpreadHome: -6.5,
      marketSpreadHome: -5.5,
      keiTotal: 44.0,
      marketTotal: 45.5,
      homeWinProb: 0.68,
    });
    const drop = buildStatDrop(ctx);
    expect(assertStatDropSchema(drop)).toBe(true);
    expect(drop.slots.map((s) => s.id)).toEqual([...STAT_DROP_SLOT_IDS]);
    expect(drop.hasPower).toBe(true);
    expect(drop.slots[0]!.value).not.toBe("—");
  });

  it("uses em dash for missing optional slots but keeps schema", () => {
    const ctx = buildMatchupContext({
      gameId: "stat-drop-thin",
      awayName: "Away",
      homeName: "Home",
      awayAbbr: "XXX",
      homeAbbr: "YYY",
      week: 2,
      keiSpreadHome: -1.5,
    });
    const drop = buildStatDrop(ctx);
    expect(assertStatDropSchema(drop)).toBe(true);
    expect(drop.hasPower).toBe(true);
    const rest = drop.slots.find((s) => s.id === "rest")!;
    // week 2 without gamesPlayed → early gate, not season open
    expect(rest.value === "—" || rest.value.includes("—")).toBe(true);
  });
});

describe("enrichNflEdgeBoardMatchupFields", () => {
  it("stamps overview + statDrop onto fair-line style rows", () => {
    const rows = [
      {
        id: "g-spread",
        game: "New England Patriots @ Seattle Seahawks",
        market: "Spread",
        kei: "-3.5",
        best: "+3.0",
        week: 1,
        awayAbbr: "NE",
        homeAbbr: "SEA",
        homeWinProb: 0.6,
        keiSpreadHome: -3.5,
        marketSpreadHome: -3.0,
        keiTotal: 41.5,
        marketTotal: 44.5,
        gamesPlayedAway: 0,
        gamesPlayedHome: 0,
      },
      {
        id: "g-total",
        game: "New England Patriots @ Seattle Seahawks",
        market: "Total",
        kei: "41.5",
        best: "44.5",
        week: 1,
        awayAbbr: "NE",
        homeAbbr: "SEA",
      },
    ] as EdgeBoardRow[];

    const out = enrichNflEdgeBoardMatchupFields(rows, {
      powerByAbbr: new Map([
        ["NE", 8.1],
        ["SEA", 9.2],
      ]),
    });
    const spread = out[0] as EdgeBoardRow & {
      matchupOverview?: string;
      statDrop?: ReturnType<typeof buildStatDrop>;
    };
    expect(spread.matchupOverview).toContain("Bottom line");
    expect(spread.statDrop?.hasPower).toBe(true);
    expect(copyContainsForbiddenWeek1Form(spread.matchupOverview || "")).toBe(
      false,
    );
  });
});
