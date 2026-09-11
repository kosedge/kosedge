import { describe, expect, it } from "vitest";
import type { EdgeBoardRow } from "@kosedge/contracts";
import {
  applyOddsHorizonToRows,
  classifyOddsHorizon,
  fairDisplayForRow,
  isOddsWithoutKei,
  ODDS_HORIZON_LABELS,
  sortOddsHorizonRows,
  stampOddsHorizon,
} from "@/lib/odds-horizon";
import { CFB_EDGE_BOARD_PUBLIC_ENABLED } from "@/lib/cfb-edge-board-public";

const NOW = Date.parse("2026-09-11T18:00:00Z");

function row(partial: Partial<EdgeBoardRow>): EdgeBoardRow {
  return {
    id: partial.id ?? "r",
    game: partial.game ?? "A @ B",
    market: partial.market ?? "Spread",
    ...partial,
  };
}

describe("odds horizon labels", () => {
  it("labels live/same-day Current, ≤7d Early Market, farther Futures", () => {
    expect(classifyOddsHorizon("2026-09-11T16:00:00Z", NOW)).toBe("current");
    expect(classifyOddsHorizon("2026-09-11T23:30:00Z", NOW)).toBe("current");
    expect(classifyOddsHorizon("2026-09-14T17:00:00Z", NOW)).toBe(
      "early_market",
    );
    expect(classifyOddsHorizon("2026-11-01T18:00:00Z", NOW)).toBe(
      "futures_advance",
    );
    expect(
      stampOddsHorizon(row({ commenceTime: "2026-11-01T18:00:00Z" }), NOW)
        .marketHorizonLabel,
    ).toBe(ODDS_HORIZON_LABELS.futures_advance);
  });

  it("always carries exact market_as_of from linesAsOf (never invents)", () => {
    const stamped = stampOddsHorizon(
      row({
        commenceTime: "2026-09-14T17:00:00Z",
        linesAsOf: "2026-09-11T15:41:00Z",
        best: "-3.5",
        bookKey: "draftkings",
      }),
      NOW,
    );
    expect(stamped.marketAsOf).toBe("2026-09-11T15:41:00Z");
    expect(stamped.marketHorizonLabel).toBe(ODDS_HORIZON_LABELS.early_market);
  });
});

describe("odds horizon sort", () => {
  it("sorts live/current day → nearest upcoming → chronological future", () => {
    const future = row({
      id: "future",
      game: "Far @ Future",
      commenceTime: "2026-12-01T18:00:00Z",
      best: "-7",
      bookKey: "fanduel",
      kei: "-14", // giant model edge must not win sort
    });
    const early = row({
      id: "early",
      game: "Soon @ Early",
      commenceTime: "2026-09-16T00:00:00Z",
      best: "-1",
      bookKey: "draftkings",
    });
    const today = row({
      id: "today",
      game: "Now @ Today",
      commenceTime: "2026-09-11T23:00:00Z",
      best: "+3",
      bookKey: "betmgm",
    });
    const live = row({
      id: "live",
      game: "Live @ Game",
      commenceTime: "2026-09-11T16:00:00Z",
      best: "-2.5",
      bookKey: "draftkings",
    });
    const sorted = sortOddsHorizonRows([future, early, today, live], NOW);
    expect(sorted.map((r) => r.id)).toEqual([
      "live",
      "today",
      "early",
      "future",
    ]);
  });

  it("within the same kickoff window prefers freshest market then book coverage", () => {
    const staleThin = row({
      id: "stale",
      game: "Same @ Window",
      market: "Spread",
      commenceTime: "2026-09-20T17:00:00Z",
      linesAsOf: "2026-09-10T12:00:00Z",
      bookCount: 2,
      best: "-3",
      bookKey: "draftkings",
    });
    const freshCovered = row({
      id: "fresh",
      game: "Same @ Window",
      market: "Spread",
      commenceTime: "2026-09-20T17:00:00Z",
      linesAsOf: "2026-09-11T17:00:00Z",
      bookCount: 8,
      best: "-3.5",
      bookKey: "fanduel",
    });
    const sorted = sortOddsHorizonRows([staleThin, freshCovered], NOW);
    expect(sorted[0]?.id).toBe("fresh");
  });
});

describe("odds without KEI paint", () => {
  it("keeps verified-book rows with blank Fair when KEI is missing", () => {
    const painted = applyOddsHorizonToRows(
      [
        row({
          id: "odds-only",
          game: "Buffalo Bills @ Miami Dolphins",
          commenceTime: "2026-10-04T17:00:00Z",
          best: "-6.5",
          bookKey: "draftkings",
          linesAsOf: "2026-09-11T14:00:00Z",
        }),
      ],
      NOW,
    );
    expect(isOddsWithoutKei(painted[0])).toBe(true);
    expect(painted[0]?.oddsWithoutKei).toBe(true);
    expect(fairDisplayForRow(painted[0])).toBe("—");
    expect(painted[0]?.best).toBe("-6.5");
    expect(painted[0]?.marketAsOf).toBe("2026-09-11T14:00:00Z");
    expect(painted[0]?.marketHorizonLabel).toBe(
      ODDS_HORIZON_LABELS.futures_advance,
    );
  });
});

describe("CFB public kill switch stays off in this PR", () => {
  it("does not flip CFB_EDGE_BOARD_PUBLIC_ENABLED", () => {
    expect(CFB_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
  });
});
