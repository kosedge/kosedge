import { describe, expect, it } from "vitest";
import {
  acceptFreshCfbMarketRows,
  CFB_MARKET_MAX_AGE_MS,
  countPricedCfbMarketRows,
  loadFreshCfbEdgeBoardFallback,
} from "@/lib/cfb-edge-board-odds";
import { edgeBoardRowsFromOddsEvents, type OddsEvent } from "@/lib/odds-api";
import { applyCfbTrustedMarketToRows } from "@/lib/cfb-trusted-market";
import { mergeKeiIntoEdgeBoardRows } from "@/lib/edge-board-kei";
import { getKeiLines } from "@/lib/kei-lines";
import type { EdgeBoardRow } from "@kosedge/contracts";

const NOW = Date.parse("2026-09-10T16:00:00Z");

function pricedRow(partial: Partial<EdgeBoardRow> = {}): EdgeBoardRow {
  return {
    id: "ok-spread",
    game: "Rutgers Scarlet Knights @ Boston College Eagles",
    market: "Spread",
    open: "+13.5",
    best: "+14.0",
    book: "DraftKings",
    bookKey: "draftkings",
    commenceTime: "2026-09-11T23:30:00Z",
    linesAsOf: "2026-09-10T15:00:00Z",
    ...partial,
  } as EdgeBoardRow;
}

const liveEvent: OddsEvent = {
  id: "rut-bc",
  sport_key: "americanfootball_ncaaf",
  commence_time: "2026-09-11T23:30:00Z",
  home_team: "Boston College Eagles",
  away_team: "Rutgers Scarlet Knights",
  bookmakers: [
    {
      key: "draftkings",
      title: "DraftKings",
      last_update: "2026-09-10T15:00:00Z",
      markets: [
        {
          key: "spreads",
          last_update: "2026-09-10T15:00:00Z",
          outcomes: [
            { name: "Rutgers Scarlet Knights", point: 13.5, price: -110 },
            { name: "Boston College Eagles", point: -13.5, price: -110 },
          ],
        },
        {
          key: "totals",
          last_update: "2026-09-10T15:00:00Z",
          outcomes: [
            { name: "Over", point: 52.5, price: -110 },
            { name: "Under", point: 52.5, price: -110 },
          ],
        },
      ],
    },
  ],
};

describe("CFB current market attach (fail closed)", () => {
  it("attaches valid current CFB market observations", () => {
    const rows = edgeBoardRowsFromOddsEvents("cfb", [liveEvent]);
    expect(countPricedCfbMarketRows(rows)).toBeGreaterThan(0);
    const accepted = acceptFreshCfbMarketRows(rows, NOW);
    expect(accepted.reason).toBe("ok");
    expect(accepted.capturedAt ?? "").toContain("2026-09-10T15:00:00");
    expect(accepted.rows.some((r) => r.open && r.best)).toBe(true);
  });

  it("missing market fails closed (no Fair→Market)", () => {
    const skeleton: EdgeBoardRow[] = [
      {
        id: "skel-spread",
        game: "Rutgers Scarlet Knights @ Boston College Eagles",
        market: "Spread",
        kei: "+13.5",
        commenceTime: "2026-09-11T23:30:00Z",
      } as EdgeBoardRow,
    ];
    const accepted = acceptFreshCfbMarketRows(skeleton, NOW);
    expect(accepted.reason).toBe("unpriced");
    expect(accepted.rows).toEqual([]);

    const trusted = applyCfbTrustedMarketToRows(skeleton);
    expect(trusted[0]?.cfbTrustReason).toBe("no_market");
    expect(trusted[0]?.open).toBeUndefined();
    expect(trusted[0]?.best).toBeUndefined();
    expect(trusted[0]?.kei).toBe("+13.5");
  });

  it("rejects stale fallback so July 31 cannot masquerade as current", () => {
    const stale = acceptFreshCfbMarketRows(
      [
        pricedRow({
          linesAsOf: "2026-07-31T18:12:23Z",
          commenceTime: "2026-08-29T16:00:00Z",
        }),
      ],
      NOW,
    );
    expect(stale.reason).toBe("stale");
    expect(stale.rows).toEqual([]);
    expect(NOW - Date.parse("2026-07-31T18:12:23Z")).toBeGreaterThan(
      CFB_MARKET_MAX_AGE_MS,
    );

    const shipped = loadFreshCfbEdgeBoardFallback(NOW);
    expect(shipped.source).toBe("none");
    expect(shipped.rows).toEqual([]);
    expect(shipped.reason).toMatch(/fallback_stale|fallback_unpriced/);
  });

  it("joins Fair (KEI pack) and Market (Odds names) on one game identity", () => {
    const oddsRows = edgeBoardRowsFromOddsEvents("cfb", [liveEvent]);
    const kei = getKeiLines("cfb").filter((g) => g.week === 2);
    expect(kei.length).toBeGreaterThan(0);
    const merged = mergeKeiIntoEdgeBoardRows(oddsRows, "cfb", kei);
    const spread = merged.find((r) => r.market === "Spread");
    expect(spread?.open).toBeTruthy();
    expect(spread?.best).toBeTruthy();
    expect(spread?.kei).toBeTruthy();
    expect(spread?.week).toBe(2);
  });
});
