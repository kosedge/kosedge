/**
 * INC-2026-09-10 — MLB Edge Board totals fail-closed (in-play / missing period).
 * Do not paint PLAY/LEAN/edge from a live or unidentified total vs FG fair.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { flatRowsToLegacy } from "@/lib/flat-rows-to-legacy";
import {
  applyTotalIdentityGateToRows,
  evaluateTotalIdentityGate,
  isFullGameTotalPeriod,
  isOddsInPlayEvent,
  stripFailClosedTotalDecisionChrome,
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
    expect(isFullGameTotalPeriod("fg_pregame")).toBe(true);
    expect(isFullGameTotalPeriod("full_game")).toBe(true);
    expect(isFullGameTotalPeriod("1st5")).toBe(false);
    expect(isFullGameTotalPeriod("live")).toBe(false);
    expect(isFullGameTotalPeriod("fg_live")).toBe(false);
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

  it("MLB: fg_pregame is equivalent FG pregame and compares when T ≡ Q", () => {
    const v = evaluateTotalIdentityGate({
      sport: "mlb",
      market: "Total",
      period: "fg_pregame",
      modelPeriod: "fg",
      commenceTime: "2026-09-11T23:05:00Z",
      linesAsOf: "2026-09-10T16:00:00Z",
    });
    expect(v.failClosed).toBe(false);
    expect(v.reason).toBe("ok");
  });

  it("MLB: stamped fg_live fails closed (in-play remaining ≠ pregame T)", () => {
    const v = evaluateTotalIdentityGate({
      sport: "mlb",
      market: "Total",
      period: "fg_live",
      modelPeriod: "fg",
      commenceTime: "2026-09-10T16:20:00Z",
      linesAsOf: "2026-09-10T18:45:00Z",
    });
    expect(v.failClosed).toBe(true);
    expect(v.reason).toBe("in_play");
    expect(v.inPlay).toBe(true);
  });

  it("T.period fg vs Q.period 1st5 is target_mismatch (no shared-event fill)", () => {
    const v = evaluateTotalIdentityGate({
      sport: "mlb",
      market: "Total",
      period: "1st5",
      modelPeriod: "fg",
      commenceTime: "2026-09-11T23:05:00Z",
      linesAsOf: "2026-09-10T16:00:00Z",
    });
    expect(v.failClosed).toBe(true);
    expect(v.reason).toBe("period_not_fg");
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
          decision: {
            action_label: "PLAY",
            edge_magnitude: 5.5,
            numerical_edge: 5.5,
          },
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
    const decision = stamped[0]?.decision as
      | Record<string, unknown>
      | undefined;
    expect(decision?.action_label).toBeUndefined();
    expect(decision?.edge_magnitude).toBeUndefined();
    expect(stamped[0]?.best).toBe("3.5");
    expect(stamped[0]?.kei).toBe("9");
  });

  it("ingest-stamped fg_live 3.5 vs FG fair 9 never paints PLAY / LEAN / edge", () => {
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
        raysAtlInPlayTotal({
          period: "fg_live",
          modelPeriod: "fg",
          oddsMarketKey: "totals",
        }),
      ],
      "mlb",
    );
    const row = rows[0]!;
    expect(row.bestOU.top.label).toBe("o3.5");
    expect(row.keiOU?.top.label).toBe("o9");
    expect(row.tagOU).toBeUndefined();
    expect(row.playOU).toBeUndefined();
    expect(row.edgeOUNum).toBeUndefined();
    expect(row.edgeMagnitudeOU).toBeUndefined();
  });

  it("pregame FG restore: stamped period=fg + T.period=fg compares (tag rules as before)", () => {
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
          modelPeriod: "fg",
          oddsMarketKey: "totals",
          best: "8.5",
          kei: "9",
          fairLine: 9,
          commenceTime: "2026-09-11T23:05:00Z",
          linesAsOf: "2026-09-10T16:00:00Z",
        }),
      ],
      "mlb",
    );
    const row = rows[0]!;
    expect(row.edgeOUNum).toBeCloseTo(0.5, 5);
    expect(row.tagOU).toBeDefined();
    expect(row.tagOU).toBe("PASS");
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
  });
});

describe("TRUTH RECERT RED check #8 — fail-closed ≠ PASS", () => {
  const NE_SEA = "New England Patriots @ Seattle Seahawks";

  function neSeaInPlayMissingPeriod(overrides: Record<string, unknown> = {}) {
    return {
      id: "ne-sea-total",
      game: NE_SEA,
      market: "Total",
      best: "44.5",
      bookKey: "draftkings",
      book: "DraftKings",
      kei: "43.3",
      fairLine: 43.3,
      modelPeriod: "fg",
      commenceTime: "2026-09-10T00:20:00Z",
      linesAsOf: "2026-09-10T19:00:00Z",
      publishTag: "PASS",
      actionLabel: "PASS",
      edgeMagnitude: 1.2,
      coverProb: 0.58,
      playToNotes: "Under 44.5",
      playToPlay: 43.0,
      playToLean: 43.5,
      playToPass: 44.0,
      decision: {
        action_label: "PASS",
        actionLabel: "PASS",
        edge_magnitude: 1.2,
        numerical_edge: 1.2,
        cover_prob: 0.58,
        play_to: { notes: "Under 44.5" },
      },
      ...overrides,
    };
  }

  function expectNoPassOrEdge(row: {
    tagOU?: unknown;
    actionLabelOU?: unknown;
    edgeOUNum?: unknown;
    edgeMagnitudeOU?: unknown;
    playOU?: unknown;
  }) {
    expect(row.tagOU).toBeUndefined();
    expect(row.tagOU).not.toBe("PASS");
    expect(row.actionLabelOU).toBeUndefined();
    expect(row.edgeOUNum).toBeUndefined();
    expect(row.edgeMagnitudeOU).toBeUndefined();
    expect(row.playOU).toBeUndefined();
  }

  it("NE@SEA in-play + missing period: assemble does not ship PASS or edge", () => {
    const live = evaluateTotalIdentityGate({
      sport: "nfl",
      market: "Total",
      period: undefined,
      modelPeriod: "fg",
      commenceTime: "2026-09-10T00:20:00Z",
      linesAsOf: "2026-09-10T19:00:00Z",
    });
    expect(live.failClosed).toBe(true);
    expect(live.reason).toBe("in_play_missing_period");

    const stamped = applyTotalIdentityGateToRows(
      [neSeaInPlayMissingPeriod()],
      "nfl",
    );
    expect(stamped[0]?.totalCompareEligible).toBe(false);
    expect(stamped[0]?.totalIdentityReason).toBe("in_play_missing_period");
    expect(stamped[0]?.publishTag).toBeUndefined();
    expect(stamped[0]?.actionLabel).toBeUndefined();
    expect(stamped[0]?.edgeMagnitude).toBeUndefined();
    expect(stamped[0]?.coverProb).toBeUndefined();
    expect(stamped[0]?.playToNotes).toBeUndefined();
    expect(stamped[0]?.playToPlay).toBeUndefined();
    expect(stamped[0]?.playToLean).toBeUndefined();
    expect(stamped[0]?.playToPass).toBeUndefined();
    const decision = stamped[0]?.decision as
      | Record<string, unknown>
      | undefined;
    expect(decision?.action_label).toBeUndefined();
    expect(decision?.actionLabel).toBeUndefined();
    expect(decision?.edge_magnitude).toBeUndefined();
    expect(decision?.numerical_edge).toBeUndefined();
    expect(decision?.cover_prob).toBeUndefined();
    expect(decision?.play_to).toBeUndefined();
    expect(stamped[0]?.best).toBe("44.5");
    expect(stamped[0]?.kei).toBe("43.3");
    expect(stamped[0]?.fairLine).toBe(43.3);
  });

  it("NE@SEA in-play + missing period: legacy total decision has no PASS / edge_magnitude", () => {
    const rows = flatRowsToLegacy(
      [
        {
          id: "ne-sea-spread",
          game: NE_SEA,
          market: "Spread",
          best: "-3.5",
          bookKey: "draftkings",
          kei: "-3.8",
          commenceTime: "2026-09-10T00:20:00Z",
          linesAsOf: "2026-09-10T19:00:00Z",
        },
        neSeaInPlayMissingPeriod(),
      ],
      "nfl",
    );
    expect(rows).toHaveLength(1);
    expectNoPassOrEdge(rows[0]!);
    expect(rows[0]!.coverProbOU).toBeUndefined();
    expect(rows[0]!.playToOU).toBeUndefined();
    expect(rows[0]!.playToOUNum).toBeUndefined();
    expect(rows[0]!.leanToOUNum).toBeUndefined();
  });

  it("strip helper never writes PASS as a stand-in", () => {
    const stripped = stripFailClosedTotalDecisionChrome(
      neSeaInPlayMissingPeriod(),
    );
    expect(stripped.publishTag).toBeUndefined();
    expect(stripped.actionLabel).toBeUndefined();
    expect(stripped.edgeMagnitude).toBeUndefined();
    expect(stripped.coverProb).toBeUndefined();
    expect(stripped.playToNotes).toBeUndefined();
    expect(stripped.playToPlay).toBeUndefined();
    const decision = stripped.decision as Record<string, unknown>;
    expect(decision.action_label).toBeUndefined();
    expect(decision.cover_prob).toBeUndefined();
    expect(decision.play_to).toBeUndefined();
    expect(JSON.stringify(stripped)).not.toMatch(/"PASS"/);
  });

  it("wrong event pairing cannot compare (no PASS stand-in)", () => {
    const v = evaluateTotalIdentityGate({
      sport: "nfl",
      market: "Total",
      period: "fg",
      modelPeriod: "fg",
      event: NE_SEA,
      modelEvent: "San Francisco 49ers @ Los Angeles Rams",
      commenceTime: "2026-09-11T00:20:00Z",
      linesAsOf: "2026-09-10T16:00:00Z",
    });
    expect(v.failClosed).toBe(true);
    expect(v.reason).toBe("target_mismatch");

    const stamped = applyTotalIdentityGateToRows(
      [
        neSeaInPlayMissingPeriod({
          period: "fg",
          modelPeriod: "fg",
          modelEvent: "San Francisco 49ers @ Los Angeles Rams",
          commenceTime: "2026-09-11T00:20:00Z",
          linesAsOf: "2026-09-10T16:00:00Z",
        }),
      ],
      "nfl",
    );
    expect(stamped[0]?.totalCompareEligible).toBe(false);
    expect(stamped[0]?.publishTag).toBeUndefined();
    expect(stamped[0]?.edgeMagnitude).toBeUndefined();
  });

  it("stale / incompatible quote as-of fails closed rather than invent", () => {
    const unparseable = evaluateTotalIdentityGate({
      sport: "nfl",
      market: "Total",
      period: "fg",
      modelPeriod: "fg",
      commenceTime: "2026-09-11T00:20:00Z",
      linesAsOf: "yesterday-afternoon",
      modelAsOf: "2026-09-10T18:00:00Z",
    });
    expect(unparseable.failClosed).toBe(true);
    expect(unparseable.reason).toBe("quote_asof_incompatible");

    const expired = evaluateTotalIdentityGate({
      sport: "nfl",
      market: "Total",
      period: "fg",
      modelPeriod: "fg",
      commenceTime: "2026-09-11T00:20:00Z",
      linesAsOf: "2026-09-10T20:00:00Z",
      modelAsOf: "2026-09-10T12:00:00Z",
      modelValidUntil: "2026-09-10T16:00:00Z",
    });
    expect(expired.failClosed).toBe(true);
    expect(expired.reason).toBe("quote_asof_incompatible");

    const rows = flatRowsToLegacy(
      [
        {
          id: "ne-sea-spread",
          game: NE_SEA,
          market: "Spread",
          best: "-3.5",
          bookKey: "draftkings",
          kei: "-3.8",
          commenceTime: "2026-09-11T00:20:00Z",
          linesAsOf: "2026-09-10T16:00:00Z",
        },
        {
          id: "ne-sea-total",
          game: NE_SEA,
          market: "Total",
          period: "fg",
          modelPeriod: "fg",
          best: "44.5",
          bookKey: "draftkings",
          kei: "43.3",
          commenceTime: "2026-09-11T00:20:00Z",
          linesAsOf: "yesterday-afternoon",
          modelAsOf: "2026-09-10T18:00:00Z",
          publishTag: "PASS",
        },
      ],
      "nfl",
    );
    expectNoPassOrEdge(rows[0]!);
  });

  it("book mismatch: displayed decision book ≠ edge-calc quote fails closed", () => {
    const v = evaluateTotalIdentityGate({
      sport: "nfl",
      market: "Total",
      period: "fg",
      modelPeriod: "fg",
      commenceTime: "2026-09-11T00:20:00Z",
      linesAsOf: "2026-09-10T16:00:00Z",
      book: "draftkings",
      decisionBook: "fanduel",
    });
    expect(v.failClosed).toBe(true);
    expect(v.reason).toBe("book_mismatch");

    const stamped = applyTotalIdentityGateToRows(
      [
        neSeaInPlayMissingPeriod({
          period: "fg",
          modelPeriod: "fg",
          commenceTime: "2026-09-11T00:20:00Z",
          linesAsOf: "2026-09-10T16:00:00Z",
          book: "DraftKings",
          bookKey: "draftkings",
          decisionBook: "fanduel",
        }),
      ],
      "nfl",
    );
    expect(stamped[0]?.totalCompareEligible).toBe(false);
    expect(stamped[0]?.totalIdentityReason).toBe("book_mismatch");
    expect(stamped[0]?.publishTag).toBeUndefined();
    expect(stamped[0]?.actionLabel).toBeUndefined();
    expect(stamped[0]?.edgeMagnitude).toBeUndefined();
  });

  it("does not invent book mismatch when only one book is stamped", () => {
    const v = evaluateTotalIdentityGate({
      sport: "nfl",
      market: "Total",
      period: "fg",
      modelPeriod: "fg",
      commenceTime: "2026-09-11T00:20:00Z",
      linesAsOf: "2026-09-10T16:00:00Z",
      book: "draftkings",
      decisionBook: undefined,
    });
    expect(v.failClosed).toBe(false);
    expect(v.reason).toBe("ok");
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

  it("odds ingest stamps period from canonical identity helpers", () => {
    const src = readFileSync(path.join(webRoot, "lib/odds-api.ts"), "utf8");
    expect(src).toContain("stampOddsMarketPeriod");
    expect(src).toContain("selectFeaturedFullGameMarket");
    expect(src).not.toMatch(/totals_1st_5_innings/);
  });

  it("flatRowsToLegacy evaluates the gate (no JSX / no range clamp)", () => {
    const src = readFileSync(
      path.join(webRoot, "lib/flat-rows-to-legacy.ts"),
      "utf8",
    );
    expect(src).toContain("evaluateTotalIdentityGate");
    expect(src).toContain("totalIdentityFail");
    expect(src).toContain("Fail-closed / unavailable total ≠ PASS");
    expect(src).not.toMatch(/3\.5\s*[<>=].*impossible|looks low/i);
  });

  it("assemble stamp strips nested decision PASS/edge (check #8)", () => {
    const src = readFileSync(
      path.join(webRoot, "lib/edge-board-total-identity-gate.ts"),
      "utf8",
    );
    expect(src).toContain("stripFailClosedTotalDecisionChrome");
    expect(src).toContain("book_mismatch");
    expect(src).toContain("quote_asof_incompatible");
  });
});
