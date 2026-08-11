import { describe, expect, it } from "vitest";
import {
  coerceNflWeek,
  diffNflBoardVsScheduleWeek,
  ensureNflScheduleWeekOnBoard,
  listNflRegWeekScheduleGames,
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

  it("lists exactly 16 REG Week 1 schedule-pack games", () => {
    const w1 = listNflRegWeekScheduleGames(1);
    expect(w1).toHaveLength(16);
    expect(w1.every((g) => g.week === 1 && g.seasonType === "REG")).toBe(true);
    const ids = new Set(w1.map((g) => g.gameId));
    expect(ids.size).toBe(16);
    expect(ids.has("2026-W01-SF@LA")).toBe(true);
    expect(ids.has("2026-W01-DAL@NYG")).toBe(true);
    expect(ids.has("2026-W01-DEN@KC")).toBe(true);
    expect(ids.has("2026-W01-GB@MIN")).toBe(true);
  });

  it("seeds missing Week 1 games with honest empties (no KEI/odds required)", () => {
    // Live gap 2026-08-10: board had 13; missing DAL@NYG, DEN@KC, GB@MIN.
    const present = listNflRegWeekScheduleGames(1).filter(
      (g) =>
        !(
          (g.awayAbbr === "DAL" && g.homeAbbr === "NYG") ||
          (g.awayAbbr === "DEN" && g.homeAbbr === "KC") ||
          (g.awayAbbr === "GB" && g.homeAbbr === "MIN")
        ),
    );
    expect(present).toHaveLength(13);

    const rows: EdgeBoardRow[] = present.flatMap((g) => [
      {
        id: `${g.gameId}-spread`,
        game: `${g.awayAbbr} @ ${g.homeAbbr}`,
        market: "Spread",
        kei: "-3",
        best: "-2.5",
        week: 1,
        seasonType: "REG",
        awayAbbr: g.awayAbbr,
        homeAbbr: g.homeAbbr,
      } as EdgeBoardRow,
      {
        id: `${g.gameId}-total`,
        game: `${g.awayAbbr} @ ${g.homeAbbr}`,
        market: "Total",
        kei: "44",
        week: 1,
        seasonType: "REG",
        awayAbbr: g.awayAbbr,
        homeAbbr: g.homeAbbr,
      } as EdgeBoardRow,
    ]);

    const before = diffNflBoardVsScheduleWeek(rows, 1);
    expect(before.ok).toBe(false);
    expect(before.missingGameIds.sort()).toEqual(
      ["2026-W01-DAL@NYG", "2026-W01-DEN@KC", "2026-W01-GB@MIN"].sort(),
    );

    const ensured = ensureNflScheduleWeekOnBoard(rows, 1);
    const week1 = filterNflStrictWeekRows(ensured, 1);
    const games = new Set(
      week1.map((r) => `${(r as { awayAbbr?: string }).awayAbbr}|${(r as { homeAbbr?: string }).homeAbbr}`),
    );
    expect(games.size).toBe(16);

    const after = diffNflBoardVsScheduleWeek(week1, 1);
    expect(after.ok).toBe(true);
    expect(after.missingGameIds).toEqual([]);

    // Seeded rows stay on the board without KEI / odds (honest empties).
    const dal = week1.find(
      (r) =>
        (r as { awayAbbr?: string }).awayAbbr === "DAL" &&
        (r as { homeAbbr?: string }).homeAbbr === "NYG" &&
        r.market === "Spread",
    );
    expect(dal).toBeTruthy();
    expect(dal?.kei == null || dal?.kei === "" || dal?.kei === "—").toBe(true);
    expect(dal?.best == null || dal?.best === "" || dal?.best === "—").toBe(
      true,
    );
  });

  it("does not seed PRE games and keeps PRE out of Week 1 filter", () => {
    const rows: EdgeBoardRow[] = [
      {
        id: "pre",
        game: "Houston Texans @ Buffalo Bills",
        market: "Spread",
        kei: "+3",
        week: 1,
        seasonType: "PRE",
        awayAbbr: "HOU",
        homeAbbr: "BUF",
      } as EdgeBoardRow,
    ];
    const ensured = ensureNflScheduleWeekOnBoard(rows, 1);
    const week1 = filterNflStrictWeekRows(ensured, 1);
    // PRE HOU@BUF must not survive; REG BUF@HOU from the schedule pack may.
    expect(
      week1.some(
        (r) =>
          (r as { seasonType?: string }).seasonType === "PRE" ||
          ((r as { awayAbbr?: string }).awayAbbr === "HOU" &&
            (r as { homeAbbr?: string }).homeAbbr === "BUF"),
      ),
    ).toBe(false);
    expect(
      week1.some(
        (r) =>
          (r as { awayAbbr?: string }).awayAbbr === "BUF" &&
          (r as { homeAbbr?: string }).homeAbbr === "HOU",
      ),
    ).toBe(true);
    expect(diffNflBoardVsScheduleWeek(week1, 1).scheduleCount).toBe(16);
    expect(diffNflBoardVsScheduleWeek(week1, 1).boardCount).toBe(16);
  });
});
