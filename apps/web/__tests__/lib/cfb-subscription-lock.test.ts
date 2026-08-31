import { describe, expect, it } from "vitest";
import { cfbGameMatchKeys, cfbGamesMatch } from "@/lib/cfb-match-keys";
import { stampCfbEdgeBoardWeek } from "@/lib/cfb-kei-artifacts";
import { getKeiLines } from "@/lib/kei-lines";
import {
  applyCfbTrustedMarketToRows,
  cfbAwayBookToHome,
  cfbEdgeTag,
  CFB_ABSURD_VS_KEI_PTS,
  trustCfbMarket,
} from "@/lib/cfb-trusted-market";

describe("cfb trusted market", () => {
  it("rejects the TCU-class junk book so it cannot PLAY", () => {
    // Home-side junk: KEI −20 vs home book +8.5 (gap ~28.9 ≥ 12).
    const before = trustCfbMarket({
      kei: -20.39,
      best: 8.5,
      open: 7.5,
    });
    expect(before.trusted).toBe(false);
    expect(before.reason).toBe("absurd_vs_kei");
    expect(cfbEdgeTag(Math.abs(-20.39 - 8.5))).toBe("PLAY"); // raw would fire
    expect(cfbEdgeTag(before.market == null ? null : 28)).toBe("PASS");

    // Board rows store away: home +8.5 ⇒ away −8.5.
    const rows = applyCfbTrustedMarketToRows([
      {
        market: "Spread",
        kei: "-20.4",
        best: "-8.5",
        open: "-7.5",
        book: "Hard Rock Bet",
        bookKey: "hardrockbet",
      },
    ]);
    expect(rows[0]?.best).toBe("");
    expect(rows[0]?.book).toBe("untrusted");
    expect(rows[0]?.bookKey).toBe("");
  });

  it("labels no_market as no book when Best is missing", () => {
    const rows = applyCfbTrustedMarketToRows([
      {
        market: "Spread",
        kei: "-7.5",
        best: "",
        open: "",
        book: "",
        bookKey: "",
      },
    ]);
    expect(rows[0]?.best).toBe("");
    expect(rows[0]?.book).toBe("no book");
  });

  it("keeps a normal multi-book number inside the KEI neighborhood", () => {
    const ok = trustCfbMarket({
      kei: -5.3,
      best: -3.5,
      open: -3.0,
      bookCount: 2,
    });
    expect(ok.trusted).toBe(true);
    expect(ok.market).toBe(-3.5);
    expect(cfbEdgeTag(Math.abs(-5.3 - -3.5))).toBe("PASS");
  });

  it("cfbAwayBookToHome flips Odds away point to home", () => {
    expect(cfbAwayBookToHome("+50.5")).toBe(-50.5);
    expect(cfbAwayBookToHome(-3.5)).toBe(3.5);
    expect(cfbAwayBookToHome("")).toBeNull();
    expect(CFB_ABSURD_VS_KEI_PTS).toBe(12);
  });

  it("BALL@OSU: same-side gap ~8.3 keeps Best; KEI stays −42.2", () => {
    const kei = -42.2;
    const openAway = 50.5; // book home −50.5
    const openHome = cfbAwayBookToHome(openAway);
    expect(openHome).toBe(-50.5);
    const ssGap = Math.abs(kei - (openHome as number));
    expect(ssGap).toBeCloseTo(8.3, 5);
    expect(ssGap).toBeLessThan(CFB_ABSURD_VS_KEI_PTS);

    const verdict = trustCfbMarket({
      kei,
      best: openHome,
      open: openHome,
      bookCount: 2,
    });
    expect(verdict.trusted).toBe(true);
    expect(verdict.market).toBe(-50.5);
    expect(verdict.reason).toBe("best");

    const rows = applyCfbTrustedMarketToRows([
      {
        market: "Spread",
        kei: "-42.2",
        best: "+50.5",
        open: "+50.5",
        book: "DraftKings",
        bookKey: "draftkings",
      },
    ]);
    expect(rows[0]?.best).toBe("+50.5"); // kept; storage still away
    expect(rows[0]?.book).toBe("DraftKings");

    const edge = kei - (verdict.market as number);
    expect(edge).toBeCloseTo(8.3, 5);
    expect(cfbEdgeTag(Math.abs(edge))).toBe("PLAY"); // threshold-eligible, not a fire card
  });

  it("UCLA@CAL sign-artifact PLAY is cleared on home vs home", () => {
    // Before: away open −1.5 vs home KEI −12.83 → raw gap 11.33 kept → edge −14.33 PLAY.
    // After: home open +1.5 vs −12.83 → gap 14.33 ≥ 12 → absurd.
    const kei = -12.83;
    const openAway = -1.5;
    const openHome = cfbAwayBookToHome(openAway);
    expect(openHome).toBe(1.5);
    const ssGap = Math.abs(kei - (openHome as number));
    expect(ssGap).toBeCloseTo(14.33, 2);
    expect(ssGap).toBeGreaterThanOrEqual(CFB_ABSURD_VS_KEI_PTS);

    const verdict = trustCfbMarket({
      kei,
      best: openHome,
      open: openHome,
      bookCount: 2,
    });
    expect(verdict.trusted).toBe(false);
    expect(verdict.reason).toBe("absurd_vs_kei");

    const rows = applyCfbTrustedMarketToRows([
      {
        market: "Spread",
        kei: "-12.83",
        best: "-1.5",
        open: "-1.5",
        book: "FanDuel",
        bookKey: "fanduel",
      },
    ]);
    expect(rows[0]?.best).toBe("");
    expect(rows[0]?.book).toBe("untrusted");
  });
});

describe("cfb name match", () => {
  it("matches San José / San Jose and Hawaii aliases", () => {
    expect(
      cfbGamesMatch(
        "San José State Spartans @ USC Trojans",
        "San Jose State Spartans @ USC Trojans",
      ),
    ).toBe(true);
    expect(
      cfbGamesMatch(
        "Hawaii Rainbow Warriors @ Stanford Cardinal",
        "Hawai'i Rainbow Warriors @ Stanford Cardinal",
      ),
    ).toBe(true);
    expect(cfbGameMatchKeys("SJSU @ USC").length).toBeGreaterThan(0);
  });

  it("stamps week 0 on accent-mismatched Odds rows", () => {
    const stamped = stampCfbEdgeBoardWeek([
      { game: "San Jose State Spartans @ USC Trojans" },
      { game: "Hawaii Rainbow Warriors @ Stanford Cardinal" },
    ]);
    expect(stamped[0]?.week).toBe(0);
    expect(stamped[1]?.week).toBe(0);
  });
});

describe("cfb kei lines bundle", () => {
  it("publishes every W0 FBS KEI game with names the board can match", () => {
    const w0 = getKeiLines("cfb").filter((g) => g.week === 0);
    const homes = w0.map((g) => g.homeAbbr);
    expect(homes).toEqual(
      expect.arrayContaining(["TCU", "USC", "STAN", "FSU", "UNLV", "UVA"]),
    );
    expect(w0).toHaveLength(6);
  });

  it("keeps BALL@OSU Week 1 KEI at −42.2 (cupcake saturation exhibit)", () => {
    const ballOsu = getKeiLines("cfb").find(
      (g) => g.week === 1 && g.homeAbbr === "OSU" && g.awayAbbr === "BALL",
    );
    expect(ballOsu).toBeTruthy();
    expect(ballOsu?.handicapSpreadHome).toBe(-42.2);
  });
});
