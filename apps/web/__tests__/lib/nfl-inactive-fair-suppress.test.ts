/**
 * SOP v1.1 — NFL inactive remat-or-failclosed display suppress.
 * Ryan ACCEPT + CoS LOCK 2026-09-13.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { flatRowsToLegacy } from "@/lib/flat-rows-to-legacy";
import {
  applyNflInactiveFairSuppressToRows,
  evaluateNflInactiveFairSuppress,
  isNflInactiveFlagExpired,
  isNflInactiveFlagRevoked,
  lookupNflInactiveSuppressFlag,
  NFL_INACTIVE_REMAT_NONE,
  NFL_INACTIVE_SUPPRESS_REASON_MAJOR,
  resolveNflInactiveGameId,
  stripSuppressedFairEdgeChrome,
} from "@/lib/nfl-inactive-fair-suppress";
import { resolveInjuryClear } from "@/lib/nfl-decision-engine";
import { CFB_EDGE_BOARD_PUBLIC_ENABLED } from "@/lib/cfb-edge-board-public";
import {
  applyTotalIdentityGateToRows,
  evaluateTotalIdentityGate,
} from "@/lib/edge-board-total-identity-gate";

const webRoot = path.join(__dirname, "../..");

const ATL_PIT_GAME = "Atlanta Falcons @ Pittsburgh Steelers";
const ATL_PIT_ID = "2026-W01-ATL@PIT";

function atlPitSpread(overrides: Record<string, unknown> = {}) {
  return {
    id: `${ATL_PIT_ID}-spread`,
    gameId: ATL_PIT_ID,
    game: ATL_PIT_GAME,
    market: "Spread",
    awayAbbr: "ATL",
    homeAbbr: "PIT",
    open: "+2.5",
    best: "+3.5",
    book: "DraftKings",
    bookKey: "draftkings",
    linesAsOf: "2026-09-13T16:40:00Z",
    commenceTime: "2026-09-13T17:00:00Z",
    kei: "-2.79",
    fairLine: -2.79,
    edgeMagnitude: 6.29,
    publishTag: "PASS",
    actionLabel: "PASS",
    unresolvedFlags: ["qb_unresolved"],
    decision: {
      actionLabel: "PASS",
      action_label: "PASS",
      edgeMagnitude: 6.29,
      edge_magnitude: 6.29,
      numerical_edge: 6.29,
    },
    ...overrides,
  };
}

function atlPitTotal(overrides: Record<string, unknown> = {}) {
  return {
    id: `${ATL_PIT_ID}-total`,
    gameId: ATL_PIT_ID,
    game: ATL_PIT_GAME,
    market: "Total",
    awayAbbr: "ATL",
    homeAbbr: "PIT",
    open: "44.5",
    best: "45.5",
    book: "DraftKings",
    bookKey: "draftkings",
    linesAsOf: "2026-09-13T16:40:00Z",
    commenceTime: "2026-09-13T17:00:00Z",
    kei: "43.5",
    fairLine: 43.5,
    period: "fg",
    modelPeriod: "fg",
    edgeMagnitude: 2.0,
    publishTag: "LEAN",
    actionLabel: "LEAN",
    unresolvedFlags: ["qb_unresolved"],
    ...overrides,
  };
}

const MAJOR_FLAG = {
  reason: NFL_INACTIVE_SUPPRESS_REASON_MAJOR,
  classes: ["MAJOR"],
  players: ["Kirk Cousins"],
  setBy: "product",
  setAt: "2026-09-13T15:00:00Z",
  rematRunId: null as string | null,
};

describe("nfl inactive fair suppress (SOP v1.1)", () => {
  it("uses fair-lines / schedule game_id as the canonical join key", () => {
    expect(
      resolveNflInactiveGameId({
        gameId: ATL_PIT_ID,
        id: `${ATL_PIT_ID}-spread`,
        awayAbbr: "ATL",
        homeAbbr: "PIT",
      }),
    ).toBe(ATL_PIT_ID);
    expect(
      resolveNflInactiveGameId({
        id: `${ATL_PIT_ID}-total`,
        awayAbbr: "ATL",
        homeAbbr: "PIT",
      }),
    ).toBe(ATL_PIT_ID);
  });

  it("CLEAR when no flag — does not suppress the rest of the NFL board", () => {
    const other = {
      id: "2026-W01-NE@SEA-spread",
      gameId: "2026-W01-NE@SEA",
      game: "New England Patriots @ Seattle Seahawks",
      market: "Spread",
      kei: "-3",
      fairLine: -3,
      publishTag: "LEAN",
      actionLabel: "LEAN",
      edgeMagnitude: 1.5,
      best: "+2.5",
      open: "+3",
      bookKey: "draftkings",
    };
    const stamped = applyNflInactiveFairSuppressToRows(
      [atlPitSpread(), other],
      "nfl",
      { flags: { [ATL_PIT_ID]: MAJOR_FLAG } },
    );
    expect(stamped[0]?.inactiveSuppress?.state).toBe("SUPPRESSED");
    expect(stamped[0]?.kei).toBeUndefined();
    expect(stamped[1]?.inactiveSuppress?.state).toBe("CLEAR");
    expect(stamped[1]?.kei).toBe("-3");
    expect(stamped[1]?.publishTag).toBe("LEAN");
    expect(stamped[1]?.fairCompareEligible).toBe(true);
  });

  it("strips fair/edge/tags and keeps street fields", () => {
    const stamped = applyNflInactiveFairSuppressToRows(
      [atlPitSpread()],
      "nfl",
      { flags: { [ATL_PIT_ID]: MAJOR_FLAG } },
    );
    const row = stamped[0]!;
    expect(row.inactiveSuppress?.state).toBe("SUPPRESSED");
    expect(row.inactiveSuppress?.reason).toBe(
      NFL_INACTIVE_SUPPRESS_REASON_MAJOR,
    );
    expect(row.inactiveSuppress?.players).toEqual(["Kirk Cousins"]);
    expect(row.inactiveSuppress?.rematRunId).toBe(NFL_INACTIVE_REMAT_NONE);
    expect(row.fairCompareEligible).toBe(false);
    expect(row.publishTag).toBeUndefined();
    expect(row.actionLabel).toBeUndefined();
    expect(row.edgeMagnitude).toBeUndefined();
    expect(row.kei).toBeUndefined();
    expect(row.fairLine).toBeUndefined();
    const decision = row.decision as Record<string, unknown>;
    expect(decision.action_label).toBeUndefined();
    expect(decision.edge_magnitude).toBeUndefined();
    expect(row.best).toBe("+3.5");
    expect(row.open).toBe("+2.5");
    expect(row.bookKey).toBe("draftkings");
    expect(row.linesAsOf).toBe("2026-09-13T16:40:00Z");
  });

  it("qb_unresolved alone without MAJOR / flag does not invent suppress", () => {
    const stamped = applyNflInactiveFairSuppressToRows(
      [atlPitSpread({ unresolvedFlags: ["qb_unresolved"] })],
      "nfl",
      { store: { games: {} } },
    );
    expect(stamped[0]?.inactiveSuppress?.state).toBe("CLEAR");
    expect(stamped[0]?.kei).toBe("-2.79");
    expect(stamped[0]?.fairCompareEligible).toBe(true);
  });

  it("MAJOR known on the row fail-closes fair+edge without an ops flag", () => {
    const stamped = applyNflInactiveFairSuppressToRows(
      [atlPitSpread({ majorInactiveKnown: true })],
      "nfl",
    );
    expect(stamped[0]?.inactiveSuppress?.state).toBe("SUPPRESSED");
    expect(stamped[0]?.fairCompareEligible).toBe(false);
    expect(stamped[0]?.kei).toBeUndefined();
    expect(stamped[0]?.publishTag).toBeUndefined();
  });

  it("TTL expiry clears suppress", () => {
    const expired = {
      ...MAJOR_FLAG,
      ttlUntil: "2026-09-13T16:00:00Z",
    };
    const stamped = applyNflInactiveFairSuppressToRows(
      [atlPitSpread()],
      "nfl",
      {
        flags: { [ATL_PIT_ID]: expired },
        nowMs: Date.parse("2026-09-13T16:05:00Z"),
      },
    );
    expect(stamped[0]?.inactiveSuppress?.state).toBe("CLEAR");
    expect(stamped[0]?.kei).toBe("-2.79");
    expect(
      isNflInactiveFlagExpired(expired, {
        nowMs: Date.parse("2026-09-13T16:05:00Z"),
      }),
    ).toBe(true);
  });

  it("remat receipt run_id revokes suppress", () => {
    const revoked = { ...MAJOR_FLAG, rematRunId: "remat-run-abc" };
    expect(isNflInactiveFlagRevoked(revoked)).toBe(true);
    const stamped = applyNflInactiveFairSuppressToRows(
      [atlPitSpread()],
      "nfl",
      { flags: { [ATL_PIT_ID]: revoked } },
    );
    expect(stamped[0]?.inactiveSuppress?.state).toBe("CLEAR");
    expect(stamped[0]?.kei).toBe("-2.79");
  });

  it("CoS clear revokes suppress", () => {
    const stamped = applyNflInactiveFairSuppressToRows(
      [atlPitSpread()],
      "nfl",
      { flags: { [ATL_PIT_ID]: { ...MAJOR_FLAG, clearedBy: "cos" } } },
    );
    expect(stamped[0]?.inactiveSuppress?.state).toBe("CLEAR");
  });

  it("AWAY@HOME alias resolves to the same flag", () => {
    const flag = lookupNflInactiveSuppressFlag(
      { games: { "ATL@PIT": MAJOR_FLAG } },
      ATL_PIT_ID,
      ["ATL@PIT"],
    );
    expect(flag?.reason).toBe(NFL_INACTIVE_SUPPRESS_REASON_MAJOR);
  });

  it("strip also removes win probs, keiAway, and nested decision fair", () => {
    const stamped = applyNflInactiveFairSuppressToRows(
      [
        atlPitSpread({
          homeWinProb: 0.61,
          awayWinProb: 0.39,
          keiAway: "+2.79",
          decision: {
            action_label: "PASS",
            fair_line: -2.79,
            cover_prob: 0.44,
            edge_magnitude: 6.29,
          },
        }),
      ],
      "nfl",
      { flags: { [ATL_PIT_ID]: MAJOR_FLAG } },
    );
    const row = stamped[0]!;
    expect(row.homeWinProb).toBeUndefined();
    expect(row.awayWinProb).toBeUndefined();
    expect(row.keiAway).toBeUndefined();
    const decision = row.decision as Record<string, unknown>;
    expect(decision.fair_line).toBeUndefined();
    expect(decision.cover_prob).toBeUndefined();
    expect(decision.edge_magnitude).toBeUndefined();
    expect(row.best).toBe("+3.5");
  });

  it("listed market subset leaves other customer markets painted", () => {
    const stamped = applyNflInactiveFairSuppressToRows(
      [atlPitSpread(), atlPitTotal()],
      "nfl",
      {
        flags: {
          [ATL_PIT_ID]: { ...MAJOR_FLAG, markets: ["Spread"] },
        },
      },
    );
    expect(stamped[0]?.inactiveSuppress?.state).toBe("SUPPRESSED");
    expect(stamped[0]?.kei).toBeUndefined();
    expect(stamped[1]?.inactiveSuppress?.state).toBe("CLEAR");
    expect(stamped[1]?.kei).toBe("43.5");
  });

  it("legacy game receipt prefers SUPPRESSED total over CLEAR spread", () => {
    const stamped = applyNflInactiveFairSuppressToRows(
      [atlPitSpread(), atlPitTotal()],
      "nfl",
      {
        flags: {
          [ATL_PIT_ID]: { ...MAJOR_FLAG, markets: ["Total"] },
        },
      },
    );
    expect(stamped[0]?.inactiveSuppress?.state).toBe("CLEAR");
    expect(stamped[1]?.inactiveSuppress?.state).toBe("SUPPRESSED");
    const legacy = flatRowsToLegacy(stamped, "nfl");
    expect(legacy[0]?.inactiveSuppress?.state).toBe("SUPPRESSED");
    expect(legacy[0]?.fairCompareEligible).toBe(false);
    expect(legacy[0]?.keiOU?.top.label).toBe("—");
    expect(legacy[0]?.tagOU).toBeUndefined();
    expect(legacy[0]?.bestOU.top.label).toBe("o45.5");
  });

  it("does not restore suppressed spread KEI from a CLEAR total sibling", () => {
    const stamped = applyNflInactiveFairSuppressToRows(
      [
        atlPitSpread({ keiSpreadHome: -2.79 }),
        atlPitTotal({ keiSpreadHome: -2.79, keiTotal: 43.5 }),
      ],
      "nfl",
      {
        flags: {
          [ATL_PIT_ID]: { ...MAJOR_FLAG, markets: ["Spread"] },
        },
      },
    );
    expect(stamped[0]?.keiSpreadHome).toBeUndefined();
    expect(stamped[1]?.keiSpreadHome).toBe(-2.79);
    const legacy = flatRowsToLegacy(stamped, "nfl");
    expect(legacy[0]?.keiLine?.top.label).toBe("—");
    expect(legacy[0]?.fairLineKei).toBeUndefined();
    expect(legacy[0]?.tagLine).toBeUndefined();
    expect(legacy[0]?.keiOU?.top.label).toBe("o43.5");
    expect(legacy[0]?.bestLine.top.label).toBe("+3.5");
  });

  it("injury_clear missing / unknown → false (no silent True)", () => {
    expect(resolveInjuryClear(undefined)).toBe(false);
    expect(resolveInjuryClear(null)).toBe(false);
    expect(resolveInjuryClear(false)).toBe(false);
    expect(resolveInjuryClear(true)).toBe(true);
  });
});

describe("ATL@PIT adversarial — street moved + stale fair + qb_unresolved", () => {
  it("suppresses fair/edge chrome and does not paint PASS-with-fair", () => {
    const stamped = applyNflInactiveFairSuppressToRows(
      [
        atlPitSpread({
          best: "+3.5",
          kei: "-2.79",
          fairLine: -2.79,
          publishTag: "PASS",
          actionLabel: "PASS",
          unresolvedFlags: ["qb_unresolved"],
        }),
        atlPitTotal(),
      ],
      "nfl",
      { flags: { [ATL_PIT_ID]: MAJOR_FLAG } },
    );
    expect(stamped[0]?.best).toBe("+3.5");
    expect(stamped[0]?.open).toBe("+2.5");
    expect(stamped[0]?.linesAsOf).toBe("2026-09-13T16:40:00Z");
    expect(stamped[0]?.kei).toBeUndefined();
    expect(stamped[0]?.fairLine).toBeUndefined();
    expect(stamped[0]?.publishTag).toBeUndefined();
    expect(stamped[0]?.actionLabel).toBeUndefined();
    expect(stamped[0]?.edgeMagnitude).toBeUndefined();
    expect(stamped[0]?.fairCompareEligible).toBe(false);

    const legacy = flatRowsToLegacy(stamped, "nfl");
    const row = legacy[0]!;
    expect(row.bestLine.top.label).toBe("+3.5");
    expect(row.openLine.top.label).toBe("+2.5");
    expect(row.keiLine?.top.label).toBe("—");
    expect(row.keiOU?.top.label).toBe("—");
    expect(row.tagLine).toBeUndefined();
    expect(row.tagOU).toBeUndefined();
    expect(row.actionLabelLine).toBeUndefined();
    expect(row.actionLabelOU).toBeUndefined();
    expect(row.edgeLineNum).toBeUndefined();
    expect(row.edgeOUNum).toBeUndefined();
    expect(row.fairLineKei).toBeUndefined();
    expect(row.fairOUKei).toBeUndefined();
    expect(row.inactiveSuppress?.state).toBe("SUPPRESSED");
    expect(row.fairCompareEligible).toBe(false);
  });
});

describe("regressions — CFB / other sports / identity-gate", () => {
  it("does not touch CFB kill-switch or apply suppress to CFB rows", () => {
    expect(CFB_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    const cfb = [
      {
        id: "cfb-1-spread",
        game: "Alabama @ Georgia",
        market: "Spread",
        kei: "-7",
        publishTag: "LEAN",
        actionLabel: "LEAN",
        edgeMagnitude: 2,
        best: "-6.5",
      },
    ];
    const out = applyNflInactiveFairSuppressToRows(cfb, "cfb", {
      flags: { "cfb-1": MAJOR_FLAG },
    });
    expect(out[0]?.kei).toBe("-7");
    expect(out[0]?.publishTag).toBe("LEAN");
    expect(out[0]?.inactiveSuppress).toBeUndefined();
  });

  it("leaves NBA / NHL / MLB rows unchanged", () => {
    for (const sport of ["nba", "nhl", "mlb", "wnba"]) {
      const row = {
        id: `${sport}-1-spread`,
        market: "Spread",
        kei: "-4",
        publishTag: "PLAY" as const,
        best: "-3.5",
      };
      const out = applyNflInactiveFairSuppressToRows([row], sport, {
        flags: { [`${sport}-1`]: MAJOR_FLAG },
      });
      expect(out[0]?.kei).toBe("-4");
      expect(out[0]?.publishTag).toBe("PLAY");
    }
  });

  it("identity-gate totals still fail-closed independently", () => {
    const v = evaluateTotalIdentityGate({
      sport: "mlb",
      market: "Total",
      period: undefined,
      commenceTime: "2026-09-11T23:05:00Z",
      linesAsOf: "2026-09-10T16:00:00Z",
    });
    expect(v.failClosed).toBe(true);
    const stamped = applyTotalIdentityGateToRows(
      [
        {
          market: "Total",
          kei: "9",
          best: "3.5",
          publishTag: "PLAY",
          actionLabel: "PLAY",
          edgeMagnitude: 5.5,
          commenceTime: "2026-09-10T16:20:00Z",
          linesAsOf: "2026-09-10T18:45:00Z",
        },
      ],
      "mlb",
    );
    expect(stamped[0]?.totalCompareEligible).toBe(false);
    expect(stamped[0]?.publishTag).toBeUndefined();
    expect(stamped[0]?.kei).toBe("9");
  });

  it("strip helper does not invent PASS", () => {
    const stripped = stripSuppressedFairEdgeChrome(atlPitSpread());
    expect(stripped.publishTag).toBeUndefined();
    expect(stripped.actionLabel).toBeUndefined();
  });

  it("evaluate is CLEAR when rematRunId is a real receipt", () => {
    const v = evaluateNflInactiveFairSuppress({
      gameId: ATL_PIT_ID,
      market: "Spread",
      flag: { ...MAJOR_FLAG, rematRunId: "run-1" },
    });
    expect(v.state).toBe("CLEAR");
    expect(v.failClosed).toBe(false);
  });
});

describe("assemble source-lock", () => {
  it("NFL assemble applies inactive suppress after the totals identity gate", () => {
    const src = readFileSync(
      path.join(webRoot, "lib/build-edge-board-rows.ts"),
      "utf8",
    );
    expect(src).toContain("applyTotalIdentityGateToRows");
    expect(src).toContain("applyNflInactiveFairSuppressToRows");
    expect(src).toContain('sport === "nfl"');
    expect(src).not.toMatch(/CFB_EDGE_BOARD_PUBLIC_ENABLED\s*=\s*true/);
  });

  it("does not flip the CFB public board constant", () => {
    const pub = readFileSync(
      path.join(webRoot, "lib/cfb-edge-board-public.ts"),
      "utf8",
    );
    expect(pub).toContain("CFB_EDGE_BOARD_PUBLIC_ENABLED = false");
  });

  it("full-slate assemble still evaluates suppress (snapshot bypass)", () => {
    const src = readFileSync(
      path.join(webRoot, "app/api/edge-board/[sport]/assemble/route.ts"),
      "utf8",
    );
    expect(src).toContain("applyNflInactiveFairSuppressToRows");
    expect(src).toContain("loadNflInactiveSuppressStore");
  });
});
