import { describe, expect, it } from "vitest";
import {
  coerceNflWeek,
  lookupNflScheduleWeek,
  stampNflEdgeBoardWeeksFromSchedule,
} from "@/lib/nfl-edge-board-week";
import { filterNflStrictWeekRows } from "@/lib/nfl-edge-board-from-fair-lines";
import type { EdgeBoardRow } from "@kosedge/contracts";

describe("nfl-edge-board-week schedule pack", () => {
  it("coerces numeric strings and rejects junk", () => {
    expect(coerceNflWeek(1)).toBe(1);
    expect(coerceNflWeek("1")).toBe(1);
    expect(coerceNflWeek("01")).toBe(1);
    expect(coerceNflWeek(null)).toBeNull();
    expect(coerceNflWeek("")).toBeNull();
    expect(coerceNflWeek("week1")).toBeNull();
  });

  it("looks up Melbourne SF@LAR as REG Week 1", () => {
    expect(
      lookupNflScheduleWeek({ homeAbbr: "LAR", awayAbbr: "SF" }),
    ).toBe(1);
    expect(
      lookupNflScheduleWeek({ homeAbbr: "LA", awayAbbr: "SF" }),
    ).toBe(1);
  });

  it("stamps missing weeks so Week 1 filter is non-empty", () => {
    const rows: EdgeBoardRow[] = [
      {
        id: "mel-spread",
        game: "San Francisco 49ers @ Los Angeles Rams",
        market: "Spread",
        kei: "-1.4",
        best: "+3.5",
        awayAbbr: "SF",
        homeAbbr: "LAR",
      } as EdgeBoardRow,
      {
        id: "mel-total",
        game: "San Francisco 49ers @ Los Angeles Rams",
        market: "Total",
        kei: "44.3",
        best: "48.5",
        awayAbbr: "SF",
        homeAbbr: "LAR",
      } as EdgeBoardRow,
      {
        id: "w2-spread",
        game: "Green Bay Packers @ Minnesota Vikings",
        market: "Spread",
        kei: "-2",
        best: "-1.5",
        week: 2,
        seasonType: "REG",
        awayAbbr: "GB",
        homeAbbr: "MIN",
      } as EdgeBoardRow,
      {
        id: "pre-spread",
        game: "Houston Texans @ Buffalo Bills",
        market: "Spread",
        kei: "+3",
        best: "+3",
        week: 1,
        seasonType: "PRE",
        awayAbbr: "HOU",
        homeAbbr: "BUF",
      } as EdgeBoardRow,
    ];

    // Before stamp: Melbourne has no week → strict Week 1 empty for that game.
    expect(
      filterNflStrictWeekRows(rows, 1).some((r) =>
        String(r.game).includes("49ers"),
      ),
    ).toBe(false);

    const stamped = stampNflEdgeBoardWeeksFromSchedule(rows);
    const week1 = filterNflStrictWeekRows(stamped, 1);
    const games = new Set(week1.map((r) => r.game));

    expect(games.has("San Francisco 49ers @ Los Angeles Rams")).toBe(true);
    expect(games.has("Green Bay Packers @ Minnesota Vikings")).toBe(false);
    expect(games.has("Houston Texans @ Buffalo Bills")).toBe(false);

    const mel = stamped.find((r) => r.id === "mel-spread") as {
      week?: number;
      seasonType?: string;
    };
    expect(mel.week).toBe(1);
    expect(mel.seasonType).toBe("REG");
  });

  it("does not overwrite an upstream week", () => {
    const rows: EdgeBoardRow[] = [
      {
        id: "x",
        game: "San Francisco 49ers @ Los Angeles Rams",
        market: "Spread",
        kei: "-1",
        week: 11,
        awayAbbr: "SF",
        homeAbbr: "LAR",
      } as EdgeBoardRow,
    ];
    stampNflEdgeBoardWeeksFromSchedule(rows);
    expect((rows[0] as { week?: number }).week).toBe(11);
  });
});
