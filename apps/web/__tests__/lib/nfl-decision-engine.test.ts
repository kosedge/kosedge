import { describe, expect, it } from "vitest";
import {
  BREAKEVEN_ATS_MINUS_110,
  EARLY_SIDE,
  INSEASON_SIDE,
  STANDARD_SIDE,
  assessConfidence,
  assessMarketConfirmation,
  buildSidePlayToLadder,
  buildTotalPlayToLadder,
  crossesKeyNumber,
  decideGame,
  decideSide,
  decideTotal,
  evaluateBestBet,
  gradeCoverProb,
  gradeSidePoints,
  gradeTotalPoints,
  preferKeyNumberEdge,
  sideThresholdsForWeek,
  weekRegime,
} from "@/lib/nfl-decision-engine";

describe("nfl-decision-engine doctrine", () => {
  it("keeps break-even at ≈52.38%", () => {
    expect(BREAKEVEN_ATS_MINUS_110).toBeCloseTo(0.5238, 4);
  });
});

describe("week regimes", () => {
  it("defaults to early (weeks 1–2) at season start", () => {
    expect(weekRegime(null)).toBe("early");
    expect(weekRegime(1)).toBe("early");
    expect(weekRegime(2)).toBe("early");
    expect(weekRegime(3)).toBe("standard");
    expect(weekRegime(6)).toBe("inseason");
    expect(weekRegime(12)).toBe("inseason");
    expect(weekRegime(14)).toBe("late");
    expect(sideThresholdsForWeek(null)).toEqual(EARLY_SIDE);
    expect(sideThresholdsForWeek(4)).toEqual(STANDARD_SIDE);
    expect(sideThresholdsForWeek(9)).toEqual(INSEASON_SIDE);
  });
});

describe("side point threshold bands", () => {
  const cases: Array<[number, number, string]> = [
    [1.4, 1, "PASS"],
    [1.5, 1, "LEAN"],
    [2.0, 1, "LEAN"],
    [2.5, 1, "PLAY"],
    [3.5, 1, "STRONG PLAY"],
    [0.9, 4, "PASS"],
    [1.0, 4, "LEAN"],
    [2.0, 4, "PLAY"],
    [3.0, 4, "STRONG PLAY"],
    [0.9, 8, "PASS"],
    [1.0, 8, "LEAN"],
    [2.0, 8, "PLAY"],
  ];
  it.each(cases)("|edge|=%s week=%s → %s", (edge, week, expected) => {
    expect(gradeSidePoints(edge, week)).toBe(expected);
  });
});

describe("totals point threshold bands", () => {
  const cases: Array<[number, string]> = [
    [1.4, "PASS"],
    [1.5, "LEAN"],
    [2.0, "LEAN"],
    [2.5, "PLAY"],
    [3.0, "PLAY"],
    [3.5, "STRONG PLAY"],
  ];
  it.each(cases)("|edge|=%s → %s", (edge, expected) => {
    expect(gradeTotalPoints(edge)).toBe(expected);
  });
});

describe("cover probability bands", () => {
  const cases: Array<[number, string]> = [
    [0.52, "PASS"],
    [0.53, "LEAN"],
    [0.54, "PLAY"],
    [0.56, "STRONG PLAY"],
    [0.58, "EXCEPTIONAL"],
    [0.62, "EXCEPTIONAL"],
  ];
  it.each(cases)("p=%s → %s", (p, expected) => {
    expect(gradeCoverProb(p)).toBe(expected);
  });
  it("returns null when missing", () => {
    expect(gradeCoverProb(null)).toBeNull();
  });
});

describe("key-number preference", () => {
  it("detects crossing 3", () => {
    expect(crossesKeyNumber(-6, -2.5, "spread")).toBe(true);
    expect(crossesKeyNumber(-4, -3.5, "spread")).toBe(false);
  });
  it("prefers equal-edge that crosses key number", () => {
    expect(preferKeyNumberEdge(2.5, true, 2.5, false)).toBe("a");
    expect(preferKeyNumberEdge(2.5, false, 2.5, true)).toBe("b");
  });
});

describe("play-to ladders", () => {
  it("matches BUF −6 fair / −3 market example", () => {
    const ladder = buildSidePlayToLadder({
      fairSpreadHome: 6,
      marketSpreadHome: 3,
      homeAbbr: "MIA",
      awayAbbr: "BUF",
    });
    expect(ladder.playTo).toBe(-4);
    expect(ladder.leanTo).toBe(-4.5);
    expect(ladder.passFrom).toBe(-5);
    expect(ladder.notes).toContain("BUF");
  });

  it("matches Over 44 market / 47.2 model example", () => {
    const ladder = buildTotalPlayToLadder({
      fairTotal: 47.2,
      marketTotal: 44,
    });
    expect(ladder.playTo).toBe(44.5);
    expect(ladder.passFrom).toBe(46);
    expect(ladder.notes).toContain("Over");
  });
});

describe("PLAY triple requirement", () => {
  it("requires numerical edge + confidence + price", () => {
    const conf = assessConfidence({ baseScore: 0.8 });
    const play = decideSide({
      fairSpreadHome: -7,
      marketSpreadHome: -3,
      week: 8,
      confidence: conf,
      priceStillAvailable: true,
    });
    expect(["PLAY", "BEST VALUE"]).toContain(play.actionLabel);

    const gone = decideSide({
      fairSpreadHome: -7,
      marketSpreadHome: -3,
      week: 8,
      confidence: conf,
      priceStillAvailable: false,
    });
    expect(gone.actionLabel).toBe("ALERT");

    const low = decideSide({
      fairSpreadHome: -7,
      marketSpreadHome: -3,
      week: 8,
      confidence: assessConfidence({ baseScore: 0.4, qbClear: false }),
      priceStillAvailable: true,
    });
    expect(low.actionLabel).not.toBe("PLAY");
    expect(low.actionLabel).not.toBe("BEST VALUE");
  });
});

describe("Best Bet strictness", () => {
  it("rejects largest raw discrepancy alone", () => {
    const out = decideSide({
      fairSpreadHome: -10,
      marketSpreadHome: -3,
      week: 8,
      confidence: assessConfidence({ baseScore: 0.6, injuryClear: false }),
      priceStillAvailable: true,
    });
    expect(out.isBestBet).toBe(false);
    expect(out.actionLabel).not.toBe("BEST VALUE");
  });

  it("requires all Best Bet gates", () => {
    const conf = assessConfidence({ baseScore: 0.9 });
    expect(
      evaluateBestBet({
        pointGrade: "STRONG PLAY",
        confidence: conf,
        priceAvailable: true,
        keyNumberCross: true,
        marketConfirmation: assessMarketConfirmation({
          modelFair: -7,
          opening: -3,
          current: -3.5,
          likesHomeOrOver: true,
        }),
        matchupSupport: true,
        liquidityOk: true,
      }),
    ).toBe(true);
    expect(
      evaluateBestBet({
        pointGrade: "STRONG PLAY",
        confidence: conf,
        priceAvailable: true,
        keyNumberCross: true,
        marketConfirmation: assessMarketConfirmation({
          modelFair: -7,
          opening: -3,
          current: -3.5,
          likesHomeOrOver: true,
        }),
        matchupSupport: false,
        liquidityOk: true,
      }),
    ).toBe(false);
  });

  it("labels BEST VALUE when all clear", () => {
    const out = decideSide({
      fairSpreadHome: -7,
      marketSpreadHome: -3,
      week: 8,
      confidence: assessConfidence({ baseScore: 0.9 }),
      priceStillAvailable: true,
      matchupSupport: true,
      liquidityOk: true,
    });
    expect(out.actionLabel).toBe("BEST VALUE");
    expect(out.isBestBet).toBe(true);
    expect(out.playTo).not.toBeNull();
  });
});

describe("edge magnitude vs confidence", () => {
  it("keeps fields separate", () => {
    const out = decideSide({
      fairSpreadHome: -6,
      marketSpreadHome: -3,
      week: 8,
      confidence: assessConfidence({ baseScore: 0.9 }),
    });
    expect(out.edgeMagnitude).toBeCloseTo(3.0);
    expect(out.modelConfidence.score).toBeGreaterThanOrEqual(0.75);
    expect(out).not.toHaveProperty("combinedScore");
  });
});

describe("market confirmation", () => {
  it("records open/current without mutating fair", () => {
    const mc = assessMarketConfirmation({
      modelFair: -6,
      opening: -3,
      current: -4,
      likesHomeOrOver: true,
    });
    expect(mc.modelFair).toBe(-6);
    expect(mc.note.toLowerCase()).toMatch(/fair/);
  });
});

describe("ALERT / STAY AWAY / doctrine price dependence", () => {
  it("ALERT on material uncertainty with edge", () => {
    const out = decideSide({
      fairSpreadHome: -7,
      marketSpreadHome: -3,
      week: 1,
      confidence: assessConfidence({ baseScore: 0.7, qbClear: false }),
    });
    expect(out.actionLabel).toBe("ALERT");
  });

  it("STAY AWAY on conflicting inputs", () => {
    const out = decideSide({
      fairSpreadHome: -7,
      marketSpreadHome: -3,
      week: 8,
      confidence: assessConfidence({ conflictingInputs: true }),
    });
    expect(out.actionLabel).toBe("STAY AWAY");
  });

  it("same game PLAY or PASS depending only on market number", () => {
    const conf = assessConfidence({ baseScore: 0.8 });
    const good = decideSide({
      fairSpreadHome: -6,
      marketSpreadHome: -3,
      week: 8,
      confidence: conf,
    });
    const tight = decideSide({
      fairSpreadHome: -6,
      marketSpreadHome: -5.5,
      week: 8,
      confidence: conf,
    });
    expect(["PLAY", "BEST VALUE", "LEAN"]).toContain(good.actionLabel);
    expect(tight.actionLabel).toBe("PASS");
  });
});

describe("decideGame sample output", () => {
  it("emits full action payload for a qualified game", () => {
    const game = decideGame({
      week: 1,
      fairSpreadHome: 6,
      marketSpreadHome: 3,
      fairTotal: 47.2,
      marketTotal: 44,
      homeAbbr: "MIA",
      awayAbbr: "BUF",
      confidence: assessConfidence({ baseScore: 0.8 }),
    });
    expect(game.doctrine).toBe("We bet prices, not teams.");
    expect(game.weekRegime).toBe("early");
    expect(game.spread.playTo?.playTo).toBe(-4);
    expect(game.total.playTo?.playTo).toBe(44.5);
    expect(game.actionLabelSpread).toBeTruthy();
    expect(game.actionLabelTotal).toBeTruthy();
  });

  it("decideTotal grades overs", () => {
    const total = decideTotal({
      fairTotal: 47.2,
      marketTotal: 44,
      week: 1,
      confidence: assessConfidence({ baseScore: 0.8 }),
    });
    expect(["PLAY", "BEST VALUE"]).toContain(total.actionLabel);
  });
});
