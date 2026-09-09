import { describe, expect, it } from "vitest";
import {
  MARKET_CONTRACT_CATALOG,
  MARKET_CONTRACT_SCHEMA_VERSION,
  americanToDecimal,
  americanToImpliedProb,
  assertPeriodSettlementSeparation,
  decimalToAmerican,
  favoriteFromHomeSignedHandicap,
  getMarketContract,
  handicapSelectedSideEdge,
  impliedProbToAmerican,
  isMarketContractId,
  moneylineSelectedSideEdge,
  pushVoidForContract,
  reconcileDisplayedBookVsEdgeSot,
  refuseCrossContractMix,
  removeVigThreeWay,
  removeVigTwoWay,
  toHomeSignedLine,
  totalSelectedSideEdge,
} from "@/lib/market-contract";

describe("mlb/nhl market contract schema", () => {
  it("exposes versioned schema and nine canonical markets", () => {
    expect(MARKET_CONTRACT_SCHEMA_VERSION).toBe("mlb-nhl-market-contract-v1");
    expect(MARKET_CONTRACT_CATALOG).toHaveLength(9);
    for (const row of MARKET_CONTRACT_CATALOG) {
      expect(isMarketContractId(row.market_contract_id)).toBe(true);
      expect(row.customer_label.length).toBeGreaterThan(0);
    }
  });

  it("separates MLB FG ML vs First Five and NHL Game ML vs Regulation ML", () => {
    const mlb = assertPeriodSettlementSeparation(
      "mlb.ml.fg.incl_extra_innings.v1",
      "mlb.ml.f5.regulation_only.v1",
    );
    expect(mlb.ok).toBe(true);
    const nhl = assertPeriodSettlementSeparation(
      "nhl.ml.fg.incl_ot_so.v1",
      "nhl.ml.regulation.three_way.v1",
    );
    expect(nhl.ok).toBe(true);
    expect(
      getMarketContract("nhl.ml.fg.incl_ot_so.v1")?.customer_label,
    ).toContain("OT/Shootout");
    expect(
      getMarketContract("nhl.ml.regulation.three_way.v1")?.customer_label,
    ).toMatch(/Regulation/i);
    expect(
      getMarketContract("nhl.puck_line.fg.incl_ot_so.v1")?.customer_label,
    ).toBe("Puck Line");
  });

  it("refuses silent FG↔F5 and Game-ML↔Regulation mix", () => {
    expect(
      refuseCrossContractMix(
        "mlb.ml.fg.incl_extra_innings.v1",
        "mlb.ml.f5.regulation_only.v1",
      ).status,
    ).toBe("DATA_GAP");
    expect(
      refuseCrossContractMix(
        "nhl.ml.fg.incl_ot_so.v1",
        "nhl.ml.regulation.three_way.v1",
      ).status,
    ).toBe("DATA_GAP");
    expect(
      refuseCrossContractMix(
        "mlb.ml.fg.incl_extra_innings.v1",
        "mlb.ml.fg.incl_extra_innings.v1",
      ).status,
    ).toBe("ok");
  });
});

describe("american / decimal / vig helpers", () => {
  it("converts American prices and removes two-way vig", () => {
    expect(americanToImpliedProb(-150).impliedProb).toBeCloseTo(0.6, 6);
    expect(americanToImpliedProb(130).impliedProb).toBeCloseTo(100 / 230, 6);
    const novig = removeVigTwoWay(-110, -110);
    expect(novig.status).toBe("ok");
    expect(novig.homeProb).toBeCloseTo(0.5, 6);
    expect(novig.awayProb).toBeCloseTo(0.5, 6);
    const back = impliedProbToAmerican(0.6);
    expect(back.status).toBe("ok");
    expect(back.american).toBe(-150);
  });

  it("converts American ↔ decimal", () => {
    const dec = americanToDecimal(-150);
    expect(dec.status).toBe("ok");
    expect(dec.decimal).toBeCloseTo(1 / 0.6, 6);
    const am = decimalToAmerican(dec.decimal);
    expect(am.status).toBe("ok");
    expect(am.american).toBe(-150);
    expect(decimalToAmerican(1).status).toBe("DATA_GAP");
    expect(decimalToAmerican(0.5).status).toBe("DATA_GAP");
    expect(americanToDecimal(NaN).status).toBe("DATA_GAP");
  });

  it("three-way vig removal requires a draw leg", () => {
    const three = removeVigThreeWay(150, 150, 250);
    expect(three.status).toBe("ok");
    expect(three.drawProb).not.toBeNull();
    const sum =
      (three.homeProb as number) +
      (three.awayProb as number) +
      (three.drawProb as number);
    expect(sum).toBeCloseTo(1, 6);
    expect(removeVigThreeWay(-110, -110, NaN).status).toBe("DATA_GAP");
  });

  it("fail-closes non-finite and malformed Americans", () => {
    expect(americanToImpliedProb(NaN).status).toBe("DATA_GAP");
    expect(americanToImpliedProb(Infinity).status).toBe("DATA_GAP");
    expect(americanToImpliedProb(-66).status).toBe("DATA_GAP");
    expect(americanToImpliedProb(0).status).toBe("DATA_GAP");
    expect(removeVigTwoWay(-110, NaN).status).toBe("DATA_GAP");
  });
});

describe("side orientation and selected-side edge", () => {
  it("orients away-signed NHL book lines to home-signed", () => {
    const got = toHomeSignedLine(1.5, "away_signed");
    expect(got.status).toBe("ok");
    expect(got.homeSigned).toBe(-1.5);
    expect(favoriteFromHomeSignedHandicap(-1.5).favorite).toBe("home");
    expect(favoriteFromHomeSignedHandicap(1.5).favorite).toBe("away");
    expect(toHomeSignedLine(1.5, "not_applicable").status).toBe("DATA_GAP");
  });

  it("ML selected-side edge uses probability points and direction", () => {
    const homeLean = moneylineSelectedSideEdge({
      market_contract_id: "mlb.ml.fg.incl_extra_innings.v1",
      modelHomeProb: 0.58,
      marketNoVigHomeProb: 0.52,
    });
    expect(homeLean.status).toBe("ok");
    expect(homeLean.selectedSide).toBe("home");
    expect(homeLean.advantage).toBeCloseTo(0.06, 6);
    expect(homeLean.favoriteSide).toBe("home");

    const awayLean = moneylineSelectedSideEdge({
      market_contract_id: "nhl.ml.fg.incl_ot_so.v1",
      modelHomeProb: 0.44,
      marketNoVigHomeProb: 0.5,
    });
    expect(awayLean.selectedSide).toBe("away");
  });

  it("refuses silent Regulation ML via two-way helper", () => {
    const reg = moneylineSelectedSideEdge({
      market_contract_id: "nhl.ml.regulation.three_way.v1",
      modelHomeProb: 0.4,
      marketNoVigHomeProb: 0.4,
    });
    expect(reg.status).toBe("DATA_GAP");
    expect(reg.reason).toMatch(/three_way/);
  });

  it("puck/run line and total selected-side edges", () => {
    const puck = handicapSelectedSideEdge({
      market_contract_id: "nhl.puck_line.fg.incl_ot_so.v1",
      fairHomeSigned: -1.2,
      marketHomeSigned: -1.5,
    });
    expect(puck.status).toBe("ok");
    expect(puck.selectedSide).toBe("away");
    expect(puck.advantage).toBeCloseTo(0.3, 6);
    expect(puck.favoriteSide).toBe("home");

    const rl = handicapSelectedSideEdge({
      market_contract_id: "mlb.run_line.fg.incl_extra_innings.v1",
      fairHomeSigned: -1.8,
      marketHomeSigned: -1.5,
    });
    expect(rl.selectedSide).toBe("home");

    const tot = totalSelectedSideEdge({
      market_contract_id: "mlb.total.fg.incl_extra_innings.v1",
      fairTotal: 8.7,
      marketTotal: 8.5,
    });
    expect(tot.selectedSide).toBe("over");

    const f5tot = totalSelectedSideEdge({
      market_contract_id: "mlb.total.f5.regulation_only.v1",
      fairTotal: 4.2,
      marketTotal: 4.5,
    });
    expect(f5tot.selectedSide).toBe("under");
  });
});

describe("push/void, missing market, book vs SoT disagreement", () => {
  it("records push/void semantics per contract", () => {
    expect(pushVoidForContract("mlb.run_line.fg.incl_extra_innings.v1")).toBe(
      "run_line_no_push_at_1_5",
    );
    expect(pushVoidForContract("nhl.puck_line.fg.incl_ot_so.v1")).toBe(
      "puck_line_no_push_at_1_5",
    );
    expect(pushVoidForContract("nhl.ml.regulation.three_way.v1")).toBe(
      "three_way_no_push_on_draw",
    );
    expect(pushVoidForContract("mlb.total.fg.incl_extra_innings.v1")).toBe(
      "total_push_on_exact",
    );
    expect(pushVoidForContract("mlb.ml.f5.regulation_only.v1")).toBe(
      "push_stake_returned",
    );
  });

  it("fail-closes missing authoritative market and book/SoT disagreement", () => {
    expect(
      handicapSelectedSideEdge({
        market_contract_id: "nhl.puck_line.fg.incl_ot_so.v1",
        fairHomeSigned: -1.5,
        marketHomeSigned: null,
      }).status,
    ).toBe("DATA_GAP");
    expect(
      reconcileDisplayedBookVsEdgeSot({
        displayedBook: -1.5,
        edgeSotMarket: -1.5,
      }).status,
    ).toBe("ok");
    expect(
      reconcileDisplayedBookVsEdgeSot({
        displayedBook: -1.5,
        edgeSotMarket: -2.5,
      }).status,
    ).toBe("DATA_GAP");
    expect(
      reconcileDisplayedBookVsEdgeSot({
        displayedBook: NaN,
        edgeSotMarket: -1.5,
      }).status,
    ).toBe("DATA_GAP");
  });

  it("board posture: MLB initial ML+Total; Run Line desk-only; NHL ML not board-primary", () => {
    expect(
      getMarketContract("mlb.ml.fg.incl_extra_innings.v1")?.board_initial,
    ).toBe(true);
    expect(
      getMarketContract("mlb.total.fg.incl_extra_innings.v1")?.board_initial,
    ).toBe(true);
    expect(
      getMarketContract("mlb.run_line.fg.incl_extra_innings.v1")
        ?.desk_research_only,
    ).toBe(true);
    expect(
      getMarketContract("nhl.ml.fg.incl_ot_so.v1")?.desk_research_only,
    ).toBe(true);
    expect(
      getMarketContract("nhl.ml.fg.incl_ot_so.v1")?.board_initial,
    ).toBe(false);
  });
});
