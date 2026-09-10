/**
 * INC-2026-09-10 — MLB Edge Board totals fail-closed (in-play / missing period).
 * Do not paint PLAY/LEAN/edge from a live or unidentified total vs FG fair.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { flatRowsToLegacy } from "@/lib/flat-rows-to-legacy";
import { composeEdgeBoardMobileCard } from "@/lib/edge-board-mobile-presentation";
import {
  applyTotalIdentityGateToRows,
  evaluateTotalIdentityGate,
  isFullGameTotalPeriod,
  isOddsInPlayEvent,
} from "@/lib/edge-board-total-identity-gate";

const webRoot = path.join(__dirname, "../..");

const RAYS_ATL = "Tampa Bay Rays @ Atlanta Braves";

/** Incident shape: live remaining/period total vs full-game KEI. */
function raysAtlInPlayTotal(overrides: Record<string, unknown> = {}) {
  return {
    id: "rays-atl-total",
    game: RAYS_ATL,
    market: "Total",
    best: "3.5",
    open: "8.5",
    bookKey: "draftkings",
    book: "DraftKings",
    kei: "9",
    fairLine: 9,
    commenceTime: "2026-09-10T16:20:00Z",
    linesAsOf: "2026-09-10T18:45:00Z",
    ...overrides,
  };
}

describe("total identity gate (INC-2026-09-10)", () => {
  it("treats only explicit FG tokens as comparable period identity", () => {
    expect(isFullGameTotalPeriod("fg")).toBe(true);
    expect(isFullGameTotalPeriod("full_game")).toBe(true);
    expect(isFullGameTotalPeriod("1st5")).toBe(false);
    expect(isFullGameTotalPeriod("live")).toBe(false);
    expect(isFullGameTotalPeriod("totals")).toBe(false);
    expect(isFullGameTotalPeriod(undefined)).toBe(false);
    expect(isFullGameTotalPeriod("")).toBe(false);
  });

  it("Odds in-play = commence at or before quote linesAsOf", () => {
    expect(
      isOddsInPlayEvent({
        commenceTime: "2026-09-10T16:20:00Z",
        linesAsOf: "2026-09-10T18:45:00Z",
      }),
    ).toBe(true);
    expect(
      isOddsInPlayEvent({
        commenceTime: "2026-09-11T23:05:00Z",
        linesAsOf: "2026-09-10T16:00:00Z",
      }),
    ).toBe(false);
    expect(
      isOddsInPlayEvent({
        commenceTime: "2026-09-10T16:20:00Z",
        linesAsOf: null,
        allowWallClockOddsRule: false,
      }),
    ).toBe(false);
    expect(
      isOddsInPlayEvent({
        commenceTime: "2026-09-10T16:20:00Z",
        linesAsOf: null,
        allowWallClockOddsRule: true,
        nowMs: Date.parse("2026-09-10T18:00:00Z"),
      }),
    ).toBe(true);
  });

  it("MLB: missing period fails closed even when the event is still pregame", () => {
    const v = evaluateTotalIdentityGate({
      sport: "mlb",
      market: "Total",
      period: undefined,
      commenceTime: "2026-09-11T23:05:00Z",
      linesAsOf: "2026-09-10T16:00:00Z",
    });
    expect(v.failClosed).toBe(true);
    expect(v.reason).toBe("missing_period_identity");
  });

  it("MLB: in-play fails closed even when period is stamped fg", () => {
    const v = evaluateTotalIdentityGate({
      sport: "mlb",
      market: "Total",
      period: "fg",
      commenceTime: "2026-09-10T16:20:00Z",
      linesAsOf: "2026-09-10T18:45:00Z",
    });
    expect(v.failClosed).toBe(true);
    expect(v.reason).toBe("in_play");
    expect(v.inPlay).toBe(true);
  });

  it("MLB: certified FG + not commenced stays comparable", () => {
    const v = evaluateTotalIdentityGate({
      sport: "mlb",
      market: "Total",
      period: "fg",
      commenceTime: "2026-09-11T23:05:00Z",
      linesAsOf: "2026-09-10T16:00:00Z",
    });
    expect(v.failClosed).toBe(false);
    expect(v.reason).toBe("ok");
  });

  it("non-FG period fails closed on any sport (no range heuristic)", () => {
    const v = evaluateTotalIdentityGate({
      sport: "nba",
      market: "Total",
      period: "1st5",
      commenceTime: "2026-09-11T23:05:00Z",
      linesAsOf: "2026-09-10T16:00:00Z",
    });
    expect(v.failClosed).toBe(true);
    expect(v.reason).toBe("period_not_fg");
  });

  it("other sports: missing period + in-play fails closed; pregame still compares", () => {
    const live = evaluateTotalIdentityGate({
      sport: "nba",
      market: "Total",
      period: undefined,
      commenceTime: "2026-09-10T16:00:00Z",
      linesAsOf: "2026-09-10T18:00:00Z",
    });
    expect(live.failClosed).toBe(true);
    expect(live.reason).toBe("in_play_missing_period");

    const pre = evaluateTotalIdentityGate({
      sport: "nba",
      market: "Total",
      period: undefined,
      commenceTime: "2026-09-11T23:00:00Z",
      linesAsOf: "2026-09-10T16:00:00Z",
    });
    expect(pre.failClosed).toBe(false);
  });

  it("does not gate Moneyline / Spread rows", () => {
    const ml = evaluateTotalIdentityGate({
      sport: "mlb",
      market: "Moneyline",
      period: undefined,
      commenceTime: "2026-09-10T16:20:00Z",
      linesAsOf: "2026-09-10T18:45:00Z",
    });
    expect(ml.failClosed).toBe(false);
  });
});

describe("Rays@ATL incident — do not paint PLAY Over", () => {
  it("in-play + period=fg still fails closed (live FG quote ≠ pregame fair)", () => {
    const rows = flatRowsToLegacy(
      [
        {
          id: "rays-atl-ml",
          game: RAYS_ATL,
          market: "Moneyline",
          best: "+110",
          bestJuiceHome: "-130",
          bookKey: "draftkings",
          commenceTime: "2026-09-10T16:20:00Z",
          linesAsOf: "2026-09-10T18:45:00Z",
        },
        raysAtlInPlayTotal({ period: "fg" }),
      ],
      "mlb",
    );
    const row = rows[0]!;
    expect(row.tagOU).toBeUndefined();
    expect(row.edgeOUNum).toBeUndefined();
    expect(row.playOU).toBeUndefined();
    expect(row.edgeMagnitudeOU).toBeUndefined();
  });

  it("in-play 3.5 vs FG fair 9 does not paint PLAY / LEAN / edge magnitude", () => {
    const rows = flatRowsToLegacy(
      [
        {
          id: "rays-atl-ml",
          game: RAYS_ATL,
          market: "Moneyline",
          best: "+110",
          bestJuiceHome: "-130",
          bookKey: "draftkings",
          kei: "-140",
          keiAway: "+120",
          homeWinProb: 0.52,
          commenceTime: "2026-09-10T16:20:00Z",
          linesAsOf: "2026-09-10T18:45:00Z",
        },
        raysAtlInPlayTotal(),
      ],
      "mlb",
    );
    expect(rows).toHaveLength(1);
    const row = rows[0]!;
    expect(row.bestOU.top.label).toBe("o3.5");
    expect(row.keiOU?.top.label).toBe("o9");
    expect(row.tagOU).toBeUndefined();
    expect(row.playOU).toBeUndefined();
    expect(row.edgeOUNum).toBeUndefined();
    expect(row.edgeMagnitudeOU).toBeUndefined();
    expect(row.edgeOUFavor).toBeUndefined();
    expect(row.actionLabelOU).toBeUndefined();
    expect(row.totalCompareEligible).toBe(false);
    expect(row.totalQuoteLive).toBe(true);
  });

  it("missing period fails closed (pregame 3.5 vs 9 is still not compared)", () => {
    const rows = flatRowsToLegacy(
      [
        {
          id: "rays-atl-ml",
          game: RAYS_ATL,
          market: "Moneyline",
          best: "+110",
          bestJuiceHome: "-130",
          bookKey: "draftkings",
          commenceTime: "2026-09-11T23:05:00Z",
          linesAsOf: "2026-09-10T16:00:00Z",
        },
        raysAtlInPlayTotal({
          commenceTime: "2026-09-11T23:05:00Z",
          linesAsOf: "2026-09-10T16:00:00Z",
        }),
      ],
      "mlb",
    );
    const row = rows[0]!;
    expect(row.tagOU).toBeUndefined();
    expect(row.edgeOUNum).toBeUndefined();
    expect(row.edgeMagnitudeOU).toBeUndefined();
    expect(row.playOU).toBeUndefined();
  });

  it("assemble stamp strips PLAY/LEAN/edgeMagnitude and marks LIVE when in-play", () => {
    const stamped = applyTotalIdentityGateToRows(
      [
        raysAtlInPlayTotal({
          publishTag: "PLAY",
          actionLabel: "PLAY",
          edgeMagnitude: 5.5,
        }),
      ],
      "mlb",
    );
    expect(stamped[0]?.totalCompareEligible).toBe(false);
    expect(stamped[0]?.totalIdentityReason).toBe("missing_period_identity");
    expect(stamped[0]?.totalQuoteLive).toBe(true);
    expect(stamped[0]?.publishTag).toBeUndefined();
    expect(stamped[0]?.actionLabel).toBeUndefined();
    expect(stamped[0]?.edgeMagnitude).toBeUndefined();
    expect(stamped[0]?.best).toBe("3.5");
    expect(stamped[0]?.kei).toBe("9");
  });

  it("does not use a 3.5-looks-low clamp: certified FG pregame 3.5 vs 9 still compares", () => {
    const rows = flatRowsToLegacy(
      [
        {
          id: "pre-ml",
          game: RAYS_ATL,
          market: "Moneyline",
          best: "+110",
          bestJuiceHome: "-130",
          bookKey: "draftkings",
          commenceTime: "2026-09-11T23:05:00Z",
          linesAsOf: "2026-09-10T16:00:00Z",
        },
        raysAtlInPlayTotal({
          period: "fg",
          commenceTime: "2026-09-11T23:05:00Z",
          linesAsOf: "2026-09-10T16:00:00Z",
        }),
      ],
      "mlb",
    );
    const row = rows[0]!;
    expect(row.edgeOUNum).toBeCloseTo(5.5, 5);
    expect(row.tagOU).toBe("PLAY");
    expect(row.playOU).toBe("Over 3.5");
    expect(row.totalCompareEligible).toBe(true);
  });

  it("mobile card does not paint Over +5.5 from Fair vs Market when gated", () => {
    const rows = flatRowsToLegacy(
      [
        {
          id: "rays-atl-ml",
          game: RAYS_ATL,
          market: "Moneyline",
          best: "+110",
          bestJuiceHome: "-130",
          bookKey: "draftkings",
          kei: "-140",
          keiAway: "+120",
          homeWinProb: 0.52,
          commenceTime: "2026-09-10T16:20:00Z",
          linesAsOf: "2026-09-10T18:45:00Z",
        },
        raysAtlInPlayTotal({ fairLine: 9 }),
      ],
      "mlb",
    );
    const model = composeEdgeBoardMobileCard({
      sportKey: "mlb",
      row: rows[0]!,
    });
    expect(model.marketTotal?.over).toMatch(/3\.5/);
    expect(model.fairTotal?.over).toMatch(/9/);
    expect(model.totalInterp).toBeNull();
    expect(model.truthFlags).toContain("total_identity_ineligible");
    expect(model.totalInterp?.sideLabel).not.toBe("Over");
    expect(model.totalInterp?.magnitude).not.toBe("+5.5 pts");
  });
});

describe("assemble source-lock", () => {
  it("assembleEdgeBoardRows applies the totals identity gate", () => {
    const src = readFileSync(
      path.join(webRoot, "lib/build-edge-board-rows.ts"),
      "utf8",
    );
    expect(src).toContain("applyTotalIdentityGateToRows");
    expect(src).toContain("edge-board-total-identity-gate");
    expect(src).toContain("INC-2026-09-10");
  });

  it("flatRowsToLegacy evaluates the gate (no JSX / no range clamp)", () => {
    const src = readFileSync(
      path.join(webRoot, "lib/flat-rows-to-legacy.ts"),
      "utf8",
    );
    expect(src).toContain("evaluateTotalIdentityGate");
    expect(src).toContain("totalIdentityFail");
    expect(src).not.toMatch(/3\.5\s*[<>=].*impossible|looks low/i);
  });
});
