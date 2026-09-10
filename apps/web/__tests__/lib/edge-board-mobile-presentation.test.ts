import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  flatRowsToLegacy,
  type LegacyEdgeBoardRow,
} from "@/lib/flat-rows-to-legacy";
import {
  UNICODE_MINUS,
  composeEdgeBoardMobileCard,
  formatTeamLabeledSpread,
  presentationAbbr,
  toPublishActionLabel,
} from "@/lib/edge-board-mobile-presentation";

const EMPTY_PAIR = {
  top: { label: "—", juice: "—" },
  bottom: { label: "—", juice: "—" },
};

function baseRow(
  partial: Partial<LegacyEdgeBoardRow> = {},
): LegacyEdgeBoardRow {
  return {
    id: "ne-sea",
    teamA: { name: "New England Patriots", site: "Away" },
    teamB: { name: "Seattle Seahawks", site: "Home" },
    awayAbbr: "NE",
    homeAbbr: "SEA",
    openOU: EMPTY_PAIR,
    openLine: EMPTY_PAIR,
    bestLine: EMPTY_PAIR,
    bestOU: EMPTY_PAIR,
    ...partial,
  };
}

describe("canonical team-label presentation mapping", () => {
  it("formats favorite-labeled spreads from home-signed numbers + canonical abbrs", () => {
    expect(
      formatTeamLabeledSpread({
        homeSigned: -2.5,
        homeAbbr: "SEA",
        awayAbbr: "NE",
      }),
    ).toBe(`SEA ${UNICODE_MINUS}2.5`);
    expect(
      formatTeamLabeledSpread({
        homeSigned: 3.5,
        homeAbbr: "SEA",
        awayAbbr: "NE",
      }),
    ).toBe(`NE ${UNICODE_MINUS}3.5`);
    expect(
      formatTeamLabeledSpread({
        homeSigned: 0,
        homeAbbr: "SEA",
        awayAbbr: "NE",
      }),
    ).toBe("SEA PK");
  });

  it("uses nfl-canonical-teams only — LA→LAR, no UI nickname table", () => {
    expect(presentationAbbr({ sportKey: "nfl", abbr: "LA" })).toBe("LAR");
    expect(presentationAbbr({ sportKey: "nfl", abbr: "WSH" })).toBe("WAS");
    expect(presentationAbbr({ sportKey: "nfl", abbr: "SEA" })).toBe("SEA");
    const src = readFileSync(
      path.join(__dirname, "../../lib/edge-board-mobile-presentation.ts"),
      "utf8",
    );
    expect(src).not.toMatch(/Seahawks|Patriots|Chiefs/);
    expect(src).toContain("canonicalizeNflTeam");
  });

  it("paints SEA −2.5 market / SEA −3.9 fair from canonical abbrs", () => {
    const model = composeEdgeBoardMobileCard({
      sportKey: "nfl",
      row: baseRow({
        bestLine: {
          top: { label: "+2.5", juice: "-110" },
          bottom: { label: "-2.5", juice: "-110" },
        },
        bestLineBook: "draftkings",
        marketLineCurrent: -2.5,
        fairLineKei: -3.9,
        keiLine: {
          top: { label: "+3.9", juice: "—" },
          bottom: { label: "-3.9", juice: "—" },
        },
        tagLine: "LEAN",
        actionLabelLine: "LEAN",
        edgeMagnitudeLine: 1.4,
        edgeLineNum: 1.4,
        edgeLineFavor: "Seahawks",
      }),
    });
    expect(model.marketSpread?.teamLabeled).toBe(`SEA ${UNICODE_MINUS}2.5`);
    expect(model.fairSpread?.teamLabeled).toBe(`SEA ${UNICODE_MINUS}3.9`);
    expect(model.marketSpread?.bookKey).toBe("draftkings");
    expect(model.spreadInterp?.status).toBe("LEAN");
    expect(model.spreadInterp?.sideLabel).toBe("SEA");
    expect(model.spreadInterp?.magnitude).toBe("+1.4 pts");
  });
});

describe("#508 magnitude / side — fail closed", () => {
  it("uses reconcile helpers for Home lean when fair is stiffer than market", () => {
    const model = composeEdgeBoardMobileCard({
      sportKey: "nfl",
      row: baseRow({
        marketLineCurrent: 3.5,
        fairLineKei: 1.76,
        bestLine: {
          top: { label: "-3.5", juice: "-110" },
          bottom: { label: "+3.5", juice: "-110" },
        },
        bestLineBook: "fanduel",
        edgeMagnitudeLine: 1.74,
        edgeLineNum: 1.74,
        edgeLineFavor: "Seahawks",
        tagLine: "LEAN",
      }),
    });
    expect(model.spreadInterp?.failClosed).toBe(false);
    expect(model.spreadInterp?.sideLabel).toBe("SEA");
    expect(model.spreadInterp?.magnitude).toBe("+1.7 pts");
    expect(model.truthFlags).not.toContain("spread_fair_market_edge_mismatch");
  });

  it("fails closed when claimed edge disagrees with abs(fair−market)", () => {
    const model = composeEdgeBoardMobileCard({
      sportKey: "nfl",
      row: baseRow({
        marketLineCurrent: -9.5,
        fairLineKei: -8.31,
        bestLine: {
          top: { label: "+9.5", juice: "-110" },
          bottom: { label: "-9.5", juice: "-110" },
        },
        bestLineBook: "draftkings",
        edgeMagnitudeLine: 1.69,
        edgeLineNum: 1.69,
        edgeLineFavor: "Patriots",
        tagLine: "LEAN",
      }),
    });
    expect(model.truthFlags).toContain("spread_fair_market_edge_mismatch");
    expect(model.spreadInterp?.failClosed).toBe(true);
    expect(model.spreadInterp?.magnitude).toBeNull();
    expect(model.spreadInterp?.sideLabel).toBeNull();
    expect(model.spreadInterp?.status).toBe("LEAN");
  });

  it("fails closed when #508 side disagrees with stored favor", () => {
    const model = composeEdgeBoardMobileCard({
      sportKey: "nfl",
      row: baseRow({
        marketLineCurrent: -2.5,
        fairLineKei: -3.9,
        edgeMagnitudeLine: 1.4,
        edgeLineFavor: "Patriots",
        tagLine: "LEAN",
      }),
    });
    expect(model.truthFlags).toContain("spread_side_disagrees_favor");
    expect(model.spreadInterp?.failClosed).toBe(true);
    expect(model.spreadInterp?.sideLabel).toBeNull();
  });

  it("totals: Over/Under from #508, not JSX sign flips", () => {
    const under = composeEdgeBoardMobileCard({
      sportKey: "nfl",
      row: baseRow({
        marketOUCurrent: 47.5,
        fairOUKei: 46.32,
        bestOU: {
          top: { label: "o47.5", juice: "-110" },
          bottom: { label: "u47.5", juice: "-110" },
        },
        edgeMagnitudeOU: 1.18,
        edgeOUFavor: "Under",
        tagOU: "PASS",
      }),
    });
    expect(under.totalInterp?.sideLabel).toBe("Under");
    expect(under.totalInterp?.magnitude).toBe("+1.2 pts");
    expect(under.totalInterp?.subdued).toBe(true);

    const over = composeEdgeBoardMobileCard({
      sportKey: "nfl",
      row: baseRow({
        marketOUCurrent: 44.5,
        fairOUKei: 47.0,
        bestOU: {
          top: { label: "o44.5", juice: "-105" },
          bottom: { label: "u44.5", juice: "-115" },
        },
        edgeMagnitudeOU: 2.5,
        edgeOUFavor: "Over",
        tagOU: "PLAY",
      }),
    });
    expect(over.totalInterp?.sideLabel).toBe("Over");
    expect(over.marketTotal?.over).toBe("O 44.5");
    expect(over.marketTotal?.under).toBe("U 44.5");
  });

  it("INC-2026-09-10: gated MLB total does not paint Over magnitude on mobile", () => {
    const model = composeEdgeBoardMobileCard({
      sportKey: "mlb",
      row: baseRow({
        teamA: { name: "Tampa Bay Rays", site: "Away" },
        teamB: { name: "Atlanta Braves", site: "Home" },
        awayAbbr: "TB",
        homeAbbr: "ATL",
        commenceTime: "2026-09-10T16:20:00Z",
        linesAsOf: "2026-09-10T18:45:00Z",
        totalCompareEligible: false,
        marketOUCurrent: 3.5,
        fairOUKei: 9,
        bestOU: {
          top: { label: "o3.5", juice: "-110" },
          bottom: { label: "u3.5", juice: "-110" },
        },
        keiOU: {
          top: { label: "o9", juice: "—" },
          bottom: { label: "u9", juice: "—" },
        },
        tagOU: "PLAY",
        edgeMagnitudeOU: 5.5,
        edgeOUNum: 5.5,
        edgeOUFavor: "Over",
      }),
    });
    expect(model.truthFlags).toContain("total_identity_ineligible");
    expect(model.totalInterp).toBeNull();
    expect(model.marketTotal?.over).toBe("O 3.5");
    expect(model.fairTotal?.over).toBe("O 9");
  });
});

describe("book badge = decision book of the displayed price", () => {
  it("pairs DraftKings with the exact SEA −2.5 decision price", () => {
    const model = composeEdgeBoardMobileCard({
      sportKey: "nfl",
      row: baseRow({
        marketLineCurrent: -2.5,
        bestLine: {
          top: { label: "+2.5", juice: "-108" },
          bottom: { label: "-2.5", juice: "-108" },
        },
        bestLineBook: "draftkings",
        fairLineKei: -3.9,
      }),
    });
    expect(model.marketSpread?.teamLabeled).toBe(`SEA ${UNICODE_MINUS}2.5`);
    expect(model.marketSpread?.bookKey).toBe("draftkings");
    expect(model.marketSpread?.juice).toBe("-108");
  });

  it("does not attach a consensus/other book when decision ≠ painted best", () => {
    const model = composeEdgeBoardMobileCard({
      sportKey: "nfl",
      row: baseRow({
        marketLineCurrent: -2.5,
        bestLine: {
          top: { label: "+3.5", juice: "-110" },
          bottom: { label: "-3.5", juice: "-110" },
        },
        bestLineBook: "fanduel",
        fairLineKei: -3.9,
      }),
    });
    expect(model.truthFlags).toContain("spread_decision_vs_best_mismatch");
    expect(model.marketSpread?.teamLabeled).toBe(`SEA ${UNICODE_MINUS}2.5`);
    expect(model.marketSpread?.bookKey).toBeNull();
    expect(model.marketSpread?.juice).toBeNull();
  });
});

describe("null / empty collapse", () => {
  it("omits missing juice, open, fair, and edge — no em-dash hero", () => {
    const model = composeEdgeBoardMobileCard({
      sportKey: "cfb",
      row: baseRow({
        id: "cfb-empty",
        teamA: { name: "North Carolina Tar Heels", site: "Away" },
        teamB: { name: "TCU Horned Frogs", site: "Home" },
        awayAbbr: "UNC",
        homeAbbr: "TCU",
        bestLine: {
          top: { label: "+7.0", juice: "—" },
          bottom: { label: "-7.0", juice: "—" },
        },
        bestLineBook: "betrivers",
        marketLineCurrent: -7,
      }),
    });
    expect(model.marketSpread?.juice).toBeNull();
    expect(model.fairSpread).toBeNull();
    expect(model.openSpread).toBeNull();
    expect(model.openTotal).toBeNull();
    expect(model.spreadInterp).toBeNull();
    expect(model.confidence).toBeNull();
    expect(model.marketSpread?.teamLabeled).toBe(`TCU ${UNICODE_MINUS}7`);
  });

  it("does not invent HIGH confidence chrome when band is absent", () => {
    const model = composeEdgeBoardMobileCard({
      sportKey: "nfl",
      row: baseRow({
        marketLineCurrent: -3,
        fairLineKei: -3,
      }),
    });
    expect(model.confidence).toBeNull();
  });

  it("shows existing MEDIUM band once; omits unreachable HIGH", () => {
    const mid = composeEdgeBoardMobileCard({
      sportKey: "nfl",
      row: baseRow({
        modelConfidenceBand: "MEDIUM",
        modelConfidenceTierConstant: true,
      }),
    });
    expect(mid.confidence).toBe("Conf MEDIUM");

    const high = composeEdgeBoardMobileCard({
      sportKey: "nfl",
      row: baseRow({
        modelConfidenceBand: "HIGH",
        modelConfidenceScore: 0.8,
      }),
    });
    expect(high.confidence).toBeNull();
  });
});

describe("publish vocabulary + sign/side through assembled rows", () => {
  it("maps only PLAY/LEAN/PASS via displayActionLabel", () => {
    expect(toPublishActionLabel("ALERT")).toBe("PASS");
    expect(toPublishActionLabel("STAY AWAY")).toBe("PASS");
    expect(toPublishActionLabel("BEST VALUE")).toBe("PLAY");
    expect(toPublishActionLabel("LEAN")).toBe("LEAN");
    expect(toPublishActionLabel(null)).toBeNull();
  });

  it("assembled NFL row: away favorite stays team-labeled, book is bestLineBook", () => {
    const rows = flatRowsToLegacy(
      [
        {
          game: "New England Patriots @ Seattle Seahawks",
          market: "Spread",
          best: "+2.5",
          bookKey: "draftkings",
          book: "DraftKings",
          bestJuice: "-110",
          bestJuiceHome: "-110",
          open: "+3.0",
          kei: "-3.9",
          awayAbbr: "NE",
          homeAbbr: "SEA",
          publishTag: "LEAN",
          actionLabel: "LEAN",
          fairLine: -3.9,
          decisionMarketLine: -2.5,
          edgeMagnitude: 1.4,
          kickoffDate: "09/13",
          kickoffTime: "8:20 PM",
          linesAsOf: "2026-09-10T16:41:00Z",
        },
        {
          game: "New England Patriots @ Seattle Seahawks",
          market: "Total",
          best: "44.5",
          bookKey: "fanduel",
          bestJuice: "-105",
          bestJuiceHome: "-115",
          open: "45.5",
          kei: "45.1",
          awayAbbr: "NE",
          homeAbbr: "SEA",
          publishTag: "PASS",
          actionLabel: "PASS",
          fairLine: 45.1,
          decisionMarketLine: 44.5,
          edgeMagnitude: 0.6,
        },
      ],
      "nfl",
    );
    expect(rows).toHaveLength(1);
    const model = composeEdgeBoardMobileCard({
      sportKey: "nfl",
      row: rows[0]!,
    });
    expect(rows[0]!.awayAbbr).toBe("NE");
    expect(rows[0]!.homeAbbr).toBe("SEA");
    expect(model.marketSpread?.teamLabeled).toBe(`SEA ${UNICODE_MINUS}2.5`);
    expect(model.fairSpread?.teamLabeled).toBe(`SEA ${UNICODE_MINUS}3.9`);
    expect(model.marketSpread?.bookKey).toBe("draftkings");
    expect(model.marketTotal?.over).toBe("O 44.5");
    expect(model.marketTotal?.under).toBe("U 44.5");
    expect(model.openSpread).toBe(`SEA ${UNICODE_MINUS}3`);
    expect(model.spreadInterp?.status).toBe("LEAN");
    expect(model.totalInterp?.status).toBe("PASS");
    expect(model.totalInterp?.subdued).toBe(true);
  });

  it("neutral site is emphasized; ordinary Away/Home stay ordinary", () => {
    const neutral = composeEdgeBoardMobileCard({
      sportKey: "nfl",
      row: baseRow({
        isNeutral: true,
        siteLabel: "Neutral · São Paulo",
      }),
    });
    expect(neutral.venue).toEqual({
      kind: "neutral",
      text: "Neutral · São Paulo",
    });
    expect(neutral.matchup).toContain(" vs ");

    const ordinary = composeEdgeBoardMobileCard({
      sportKey: "nfl",
      row: baseRow(),
    });
    expect(ordinary.venue).toEqual({
      kind: "ordinary",
      text: "Away / Home",
    });
  });
});

describe("locked chrome — no banned customer copy on mobile path", () => {
  it("mobile card + presentation have no Lean-to / KEI hero / giant edge tiles", () => {
    const card = readFileSync(
      path.join(__dirname, "../../components/EdgeBoardMobileCard.tsx"),
      "utf8",
    );
    const pres = readFileSync(
      path.join(__dirname, "../../lib/edge-board-mobile-presentation.ts"),
      "utf8",
    );
    const board = readFileSync(
      path.join(__dirname, "../../components/EdgeBoard.tsx"),
      "utf8",
    );
    for (const src of [card, pres]) {
      expect(src).not.toMatch(/Lean to/);
      expect(src).not.toMatch(/Play to/);
      expect(src).not.toMatch(/KEI ·/);
      expect(src).not.toMatch(/KEINFL/);
      expect(src).not.toMatch(/BEST BET/);
      expect(src).not.toMatch(/STAY AWAY/);
      expect(src).not.toMatch(/Spread Edge/);
      expect(src).not.toMatch(/o\$\{/);
    }
    expect(card).toContain("Kosedge Fair");
    expect(board).toContain("hidden lg:block");
    expect(board).toContain("lg:hidden");
    expect(board).toContain("EdgeBoardMobileCard");
    expect(board).toContain("Lean to");
  });
});
