import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { currentNflRegWeekFromSchedule } from "@/lib/nfl-canonical-schedule";
import { listNflRegWeekScheduleGames } from "@/lib/nfl-edge-board-week";
import {
  LEGITIMATE_EMPTY_SLATE_COPY,
  MODEL_DATA_UNAVAILABLE_COPY,
} from "@/lib/model-service-status";
import {
  buildRegCardsFromSchedule,
  scheduleGameToSlateCard,
} from "@/lib/nfl-slate";
import { NFL_WEEKLY_SLATE_MAX_DAYS_AHEAD } from "@/lib/nfl-slate-window";

vi.mock("@/lib/nfl-fair-lines", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/nfl-fair-lines")>();
  return {
    ...actual,
    fetchNflFairLines: vi.fn(),
  };
});

vi.mock("@/lib/nfl-espn-schedule", () => ({
  fetchEspnPreseasonSlate: vi.fn(async () => []),
}));

vi.mock("@/lib/nfl-preseason-odds", () => ({
  fetchNflPreseasonOddsMarkets: vi.fn(async () => ({
    byMatchup: new Map(),
    status: "empty",
    eventCount: 0,
  })),
}));

import { fetchNflFairLines, type NflFairLineRow } from "@/lib/nfl-fair-lines";
import { fetchEspnPreseasonSlate } from "@/lib/nfl-espn-schedule";
import { fetchNflPreseasonOddsMarkets } from "@/lib/nfl-preseason-odds";
import { buildNflWeeklySlate } from "@/lib/nfl-slate";

const emptyFairLines = {
  season: 2026,
  modelVersion: "",
  asOf: null,
  oddsAsOf: null,
  currentWeek: 1,
  count: 0,
  lines: [],
  window: { daysAhead: 16, includePastDays: 2 },
  diagnostics: {
    oddsFeedStatus: "unknown",
    oddsFeedError: null,
    oddsEventsSeen: 0,
    marketJoinedCount: 0,
    bookmakers: [] as string[],
    kosedgeOnly: true,
  },
  error: "Unable to reach model service.",
};

describe("NFL Weekly Slate schedule vs model outage", () => {
  beforeEach(() => {
    vi.mocked(fetchNflFairLines).mockResolvedValue(emptyFairLines);
  });

  it("renders scheduled REG games when the model is down", async () => {
    const week1 = listNflRegWeekScheduleGames(1);
    expect(week1.length).toBeGreaterThanOrEqual(16);

    const slate = await buildNflWeeklySlate("week-1");
    expect(fetchNflFairLines).toHaveBeenCalledWith(
      expect.objectContaining({
        season: 2026,
        oddsMode: "skip",
        daysAhead: expect.any(Number),
        includePastDays: expect.any(Number),
      }),
    );
    const fairArgs = vi.mocked(fetchNflFairLines).mock.calls[0][0];
    expect(fairArgs.daysAhead).toBeLessThanOrEqual(
      NFL_WEEKLY_SLATE_MAX_DAYS_AHEAD,
    );
    expect(fairArgs.daysAhead).toBeLessThan(120);
    const regular = slate.sections.find((s) => s.key === "regular");
    expect(regular).toBeDefined();
    expect(regular!.cards.length).toBe(week1.length);
    expect(slate.modelUnavailable).toBe(true);

    for (const card of regular!.cards) {
      expect(card.source).toBe("schedule");
      expect(card.modelSpread).toBe("—");
      expect(card.modelTotal).toBe("—");
      expect(card.publishTagSpread).toBeNull();
      expect(card.publishTagTotal).toBeNull();
      expect(card.spreadEdge).toBeNull();
      expect(card.note).toBe(MODEL_DATA_UNAVAILABLE_COPY);
    }
  });

  it("fills an ISO slate from that date's week, not today's week", async () => {
    const slate = await buildNflWeeklySlate("2026-09-20");
    const regular = slate.sections.find((s) => s.key === "regular");
    expect(regular).toBeDefined();
    expect(regular!.cards.length).toBeGreaterThan(0);
    expect(regular!.cards.every((card) => card.week === 2)).toBe(true);
    expect(
      regular!.cards.every((card) =>
        (card.startTime || "").startsWith("2026-09-20"),
      ),
    ).toBe(true);
  });

  it("does not duplicate a painted game when fair-lines uses LA for LAR", async () => {
    const week1 = listNflRegWeekScheduleGames(1);
    const rams = week1.find(
      (game) => game.homeAbbr === "LAR" || game.awayAbbr === "LAR",
    );
    expect(rams).toBeDefined();
    const row = {
      gameId: "2026-W01-SF@LA",
      season: 2026,
      week: 1,
      seasonType: "REG",
      startTime: "2026-09-11T00:35:00.000Z",
      gameDate: "2026-09-11",
      homeTeam: "Los Angeles Rams",
      awayTeam: "San Francisco 49ers",
      homeAbbr: rams!.homeAbbr === "LAR" ? "LA" : rams!.homeAbbr,
      awayAbbr: rams!.awayAbbr === "LAR" ? "LA" : rams!.awayAbbr,
      spreadHome: -4.5,
      totalMean: 46.2,
      marketSpreadHome: -3.5,
      marketTotal: 45.5,
      bestSpreadHome: -3.5,
      bestTotal: 45.5,
      modelVersion: "test",
    } as NflFairLineRow;
    vi.mocked(fetchNflFairLines).mockResolvedValue({
      ...emptyFairLines,
      modelVersion: "test",
      currentWeek: 1,
      count: 1,
      lines: [row],
      error: undefined,
    });

    const slate = await buildNflWeeklySlate("week-1");
    const regular = slate.sections.find((s) => s.key === "regular");
    expect(regular?.cards).toHaveLength(week1.length);
    const ramsCards = regular!.cards.filter((card) => {
      const pair = [card.awayAbbr, card.homeAbbr];
      return pair.includes("LAR") || pair.includes("LA");
    });
    expect(ramsCards).toHaveLength(1);
    expect(ramsCards[0].source).toBe("fair-lines");
    expect(ramsCards[0].modelSpread).toBe("-4.50");
  });

  it("uses a legitimate empty state when no schedule games exist", async () => {
    const slate = await buildNflWeeklySlate("week-99");
    expect(slate.sections.every((s) => s.cards.length === 0)).toBe(true);
    expect(slate.sections.length).toBe(0);
  });

  it("does not invent model numbers on a schedule card", () => {
    const card = scheduleGameToSlateCard({
      week: 1,
      awayAbbr: "NE",
      homeAbbr: "SEA",
      gameId: "2026-W01-NE@SEA",
    });
    expect(card.awayAbbr).toBe("NE");
    expect(card.homeAbbr).toBe("SEA");
    expect(card.modelSpread).toBe("—");
    expect(card.marketSpread).toBe("—");
    expect(card.publishTagSpread).toBeNull();
  });

  it("resolves the Sept 11 2026 board week from schedule, not the model", () => {
    expect(
      currentNflRegWeekFromSchedule(Date.parse("2026-09-11T16:00:00.000Z")),
    ).toBe(1);
    expect(buildRegCardsFromSchedule([1]).length).toBeGreaterThanOrEqual(16);
  });

  it("fills missing matchups from schedule without inventing model numbers", async () => {
    const row = {
      gameId: "2026-W01-NE@SEA",
      season: 2026,
      week: 1,
      seasonType: "REG",
      startTime: "2026-09-10T00:20:00.000Z",
      gameDate: "2026-09-09",
      homeTeam: "Seattle Seahawks",
      awayTeam: "New England Patriots",
      homeAbbr: "SEA",
      awayAbbr: "NE",
      spreadHome: -3.87,
      totalMean: 43.4,
      marketSpreadHome: -2.5,
      marketTotal: 44.5,
      bestSpreadHome: -2.5,
      bestTotal: 44.5,
      publishTagSpread: "LEAN",
      publishTagTotal: "PASS",
      spreadEdge: 1.37,
      totalEdge: -1.1,
      modelVersion: "test",
    } as NflFairLineRow;
    vi.mocked(fetchNflFairLines).mockResolvedValue({
      ...emptyFairLines,
      modelVersion: "test",
      currentWeek: 1,
      count: 1,
      lines: [row],
      error: undefined,
    });

    const week1 = listNflRegWeekScheduleGames(1);
    const slate = await buildNflWeeklySlate("week-1");
    const regular = slate.sections.find((s) => s.key === "regular");
    expect(regular?.cards).toHaveLength(week1.length);
    expect(slate.modelUnavailable).toBe(false);

    const painted = regular!.cards.find(
      (card) => card.awayAbbr === "NE" && card.homeAbbr === "SEA",
    );
    expect(painted?.source).toBe("fair-lines");
    expect(painted?.modelSpread).toBe("-3.87");
    expect(painted?.publishTagSpread).toBe("LEAN");

    const filled = regular!.cards.filter((card) => card.source === "schedule");
    expect(filled.length).toBe(week1.length - 1);
    for (const card of filled) {
      expect(card.modelSpread).toBe("—");
      expect(card.marketSpread).toBe("—");
      expect(card.publishTagSpread).toBeNull();
      expect(card.note).toBe(MODEL_DATA_UNAVAILABLE_COPY);
    }
  });

  it("paints model/market fields when fair-lines returns the displayed week", async () => {
    const row = {
      gameId: "2026-W01-NE@SEA",
      season: 2026,
      week: 1,
      seasonType: "REG",
      startTime: "2026-09-10T00:20:00.000Z",
      gameDate: "2026-09-09",
      homeTeam: "Seattle Seahawks",
      awayTeam: "New England Patriots",
      homeAbbr: "SEA",
      awayAbbr: "NE",
      spreadHome: -3.87,
      totalMean: 43.4,
      marketSpreadHome: -2.5,
      marketTotal: 44.5,
      bestSpreadHome: -2.5,
      bestTotal: 44.5,
      bestSpreadBook: "draftkings",
      bestTotalBook: "draftkings",
      publishTagSpread: "LEAN",
      publishTagTotal: "PASS",
      spreadEdge: 1.37,
      totalEdge: -1.1,
      modelVersion: "test",
    } as NflFairLineRow;
    vi.mocked(fetchNflFairLines).mockResolvedValue({
      ...emptyFairLines,
      modelVersion: "test",
      currentWeek: 1,
      count: 1,
      lines: [row],
      error: undefined,
    });

    const slate = await buildNflWeeklySlate("week-1");
    const regular = slate.sections.find((s) => s.key === "regular");
    expect(slate.modelUnavailable).toBe(false);
    const card = regular!.cards.find(
      (row) => row.awayAbbr === "NE" && row.homeAbbr === "SEA",
    );
    expect(card?.source).toBe("fair-lines");
    expect(card?.modelSpread).toBe("-3.87");
    expect(card?.marketSpread).toBe("-2.50");
    expect(card?.publishTagSpread).toBe("LEAN");
    expect(card?.note).not.toBe(MODEL_DATA_UNAVAILABLE_COPY);
  });

  it("does not fetch ESPN / Odds preseason during REG", async () => {
    await buildNflWeeklySlate("today");
    expect(fetchEspnPreseasonSlate).not.toHaveBeenCalled();
    expect(fetchNflPreseasonOddsMarkets).not.toHaveBeenCalled();
  });
});

describe("NFL Weekly Slate customer copy", () => {
  it("does not leak tokens, ESPN joins, week-1 debug, or service names", () => {
    const page = readFileSync(
      resolve(process.cwd(), "app/(pro)/pro/nfl/slate/[date]/page.tsx"),
      "utf8",
    );
    expect(page).toContain("LEGITIMATE_EMPTY_SLATE_COPY");
    expect(page).toContain("MODEL_DATA_UNAVAILABLE_COPY");
    expect(page).not.toMatch(/token hasn/);
    expect(page).not.toMatch(/ESPN schedule joins/);
    expect(page).not.toMatch(/week-1/);
    expect(page).not.toMatch(/model service/i);
    expect(page).not.toMatch(/Unable to reach/);
    expect(page).not.toMatch(/MODEL_SERVICE_URL/);
    expect(LEGITIMATE_EMPTY_SLATE_COPY).toBe(
      "No games currently scheduled for this slate.",
    );
    expect(MODEL_DATA_UNAVAILABLE_COPY).toBe(
      "Model data temporarily unavailable.",
    );
  });
});
