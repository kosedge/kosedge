/**
 * Canonical Edge Board identity — T ≡ Q_target (INC-2026-09-10 follow-on).
 * No numerical-range heuristics. F5 keys never become FG.
 */
import { describe, expect, it } from "vitest";
import {
  booksEquivalent,
  canonicalComparePeriod,
  isFeaturedFullGameOddsKey,
  isFirstFiveInningsOddsKey,
  isFullGameLivePeriod,
  isFullGamePregamePeriod,
  periodFamilyFromOddsMarketKey,
  quoteAsOfCompatibleWithModelTarget,
  quoteTargetEqualsModel,
  selectFeaturedFullGameMarket,
  stampOddsMarketPeriod,
} from "@/lib/edge-board-market-identity";

describe("Odds market key → period family", () => {
  it("featured keys are the only FG family", () => {
    expect(isFeaturedFullGameOddsKey("totals")).toBe(true);
    expect(isFeaturedFullGameOddsKey("h2h")).toBe(true);
    expect(isFeaturedFullGameOddsKey("spreads")).toBe(true);
    expect(isFeaturedFullGameOddsKey("totals_1st_5_innings")).toBe(false);
    expect(isFeaturedFullGameOddsKey("alternate_totals")).toBe(false);
    expect(periodFamilyFromOddsMarketKey("totals")).toBe("fg");
    expect(periodFamilyFromOddsMarketKey("totals_1st_5_innings")).toBe("1st5");
    expect(periodFamilyFromOddsMarketKey("h2h_1st_5_innings")).toBe("1st5");
    expect(periodFamilyFromOddsMarketKey("alternate_totals")).toBe("alternate");
  });

  it("never treats F5 / derivative keys as featured FG", () => {
    expect(isFirstFiveInningsOddsKey("totals_1st_5_innings")).toBe(true);
    const markets = [
      {
        key: "totals_1st_5_innings",
        outcomes: [{ name: "Over", point: 3.5 }],
      },
      {
        key: "alternate_totals",
        outcomes: [{ name: "Over", point: 11.5 }],
      },
    ];
    expect(selectFeaturedFullGameMarket(markets, "totals")).toBeNull();
  });

  it("selects exact featured totals when F5 shares the event", () => {
    const markets = [
      {
        key: "totals_1st_5_innings",
        outcomes: [{ name: "Over", point: 3.5 }],
      },
      {
        key: "totals",
        outcomes: [{ name: "Over", point: 8.5 }],
      },
    ];
    const fg = selectFeaturedFullGameMarket(markets, "totals");
    expect(fg?.key).toBe("totals");
    expect(fg?.outcomes?.[0]?.point).toBe(8.5);
  });
});

describe("stampOddsMarketPeriod (Odds rules, not line size)", () => {
  it("featured totals + not commenced → fg", () => {
    expect(
      stampOddsMarketPeriod({
        marketKey: "totals",
        sport: "mlb",
        commenceTime: "2026-09-11T23:05:00Z",
        linesAsOf: "2026-09-10T16:00:00Z",
      }),
    ).toBe("fg");
  });

  it("featured totals + in-play → fg_live (not comparable to pregame T)", () => {
    expect(
      stampOddsMarketPeriod({
        marketKey: "totals",
        sport: "mlb",
        commenceTime: "2026-09-10T16:20:00Z",
        linesAsOf: "2026-09-10T18:45:00Z",
      }),
    ).toBe("fg_live");
  });

  it("does not infer F5 from a 3.5 pregame featured total", () => {
    // INC-2026-09-10: line magnitude is not identity.
    expect(
      stampOddsMarketPeriod({
        marketKey: "totals",
        sport: "mlb",
        commenceTime: "2026-09-11T23:05:00Z",
        linesAsOf: "2026-09-10T16:00:00Z",
      }),
    ).toBe("fg");
  });

  it("F5 key stamps 1st5 even when the event is pregame", () => {
    expect(
      stampOddsMarketPeriod({
        marketKey: "totals_1st_5_innings",
        sport: "mlb",
        commenceTime: "2026-09-11T23:05:00Z",
        linesAsOf: "2026-09-10T16:00:00Z",
      }),
    ).toBe("1st5");
  });

  it("other sports: no as-of → cannot certify FG pregame (null)", () => {
    expect(
      stampOddsMarketPeriod({
        marketKey: "totals",
        sport: "nba",
        commenceTime: "2026-09-11T23:05:00Z",
        linesAsOf: null,
      }),
    ).toBeNull();
  });

  it("MLB wall-clock fallback certifies pregame vs live without inventing as-of", () => {
    expect(
      stampOddsMarketPeriod({
        marketKey: "totals",
        sport: "mlb",
        commenceTime: "2026-09-11T23:05:00Z",
        linesAsOf: null,
        nowMs: Date.parse("2026-09-10T18:00:00Z"),
      }),
    ).toBe("fg");
    expect(
      stampOddsMarketPeriod({
        marketKey: "totals",
        sport: "mlb",
        commenceTime: "2026-09-10T16:20:00Z",
        linesAsOf: null,
        nowMs: Date.parse("2026-09-10T18:00:00Z"),
      }),
    ).toBe("fg_live");
  });
});

describe("T ≡ Q_target", () => {
  it("fg and fg_pregame are equivalent; fg_live and 1st5 are not", () => {
    expect(isFullGamePregamePeriod("fg")).toBe(true);
    expect(isFullGamePregamePeriod("fg_pregame")).toBe(true);
    expect(isFullGamePregamePeriod("fg_live")).toBe(false);
    expect(isFullGameLivePeriod("fg_live")).toBe(true);
    expect(canonicalComparePeriod("fg_pregame")).toBe("fg");
    expect(canonicalComparePeriod("fg_live")).toBe("fg_live");
    expect(canonicalComparePeriod("1st5")).toBe("1st5");

    expect(
      quoteTargetEqualsModel(
        { event: "a @ b", sport: "mlb", market: "Total", period: "fg" },
        { event: "a @ b", sport: "mlb", market: "Total", period: "fg_pregame" },
      ),
    ).toBe(true);
    expect(
      quoteTargetEqualsModel(
        { event: "a @ b", sport: "mlb", market: "Total", period: "fg" },
        { event: "a @ b", sport: "mlb", market: "Total", period: "fg_live" },
      ),
    ).toBe(false);
    expect(
      quoteTargetEqualsModel(
        { event: "a @ b", sport: "mlb", market: "Total", period: "fg" },
        { event: "a @ b", sport: "mlb", market: "Total", period: "1st5" },
      ),
    ).toBe(false);
    expect(
      quoteTargetEqualsModel(
        { event: "a @ b", sport: "mlb", market: "Total", period: "fg" },
        { event: "a @ b", sport: "mlb", market: "Total", period: null },
      ),
    ).toBe(false);
  });

  it("wrong event pairing cannot compare", () => {
    expect(
      quoteTargetEqualsModel(
        {
          event: "New England Patriots @ Seattle Seahawks",
          sport: "nfl",
          market: "Total",
          period: "fg",
        },
        {
          event: "San Francisco 49ers @ Los Angeles Rams",
          sport: "nfl",
          market: "Total",
          period: "fg",
        },
      ),
    ).toBe(false);
  });
});

describe("book + quote as-of identity", () => {
  it("displayed decision book must equal the edge-calc quote book", () => {
    expect(booksEquivalent("draftkings", "DK")).toBe(true);
    expect(booksEquivalent("FanDuel", "fanduel")).toBe(true);
    expect(booksEquivalent("draftkings", "fanduel")).toBe(false);
    expect(booksEquivalent("draftkings", null)).toBeNull();
  });

  it("unparseable or expired quote as-of is incompatible with the model target", () => {
    expect(
      quoteAsOfCompatibleWithModelTarget({
        linesAsOf: "yesterday-afternoon",
        modelAsOf: "2026-09-10T18:00:00Z",
        commenceTime: "2026-09-11T00:20:00Z",
      }),
    ).toBe(false);
    expect(
      quoteAsOfCompatibleWithModelTarget({
        linesAsOf: "2026-09-10T20:00:00Z",
        modelAsOf: "2026-09-10T12:00:00Z",
        commenceTime: "2026-09-11T00:20:00Z",
        modelValidUntil: "2026-09-10T16:00:00Z",
      }),
    ).toBe(false);
    expect(
      quoteAsOfCompatibleWithModelTarget({
        linesAsOf: "2026-09-10T18:00:00Z",
        edgeCalcAsOf: "2026-09-10T12:00:00Z",
        commenceTime: "2026-09-11T00:20:00Z",
      }),
    ).toBe(false);
    expect(
      quoteAsOfCompatibleWithModelTarget({
        linesAsOf: "2026-09-10T16:00:00Z",
        modelAsOf: "2026-09-10T12:00:00Z",
        commenceTime: "2026-09-11T00:20:00Z",
      }),
    ).toBe(true);
  });
});
