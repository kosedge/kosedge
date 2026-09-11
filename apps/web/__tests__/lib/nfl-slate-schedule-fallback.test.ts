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

import { fetchNflFairLines } from "@/lib/nfl-fair-lines";
import { buildNflWeeklySlate } from "@/lib/nfl-slate";

const emptyFairLines = {
  season: 2026,
  modelVersion: "",
  asOf: null,
  oddsAsOf: null,
  currentWeek: 1,
  count: 0,
  lines: [],
  window: { daysAhead: 120, includePastDays: 2 },
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
