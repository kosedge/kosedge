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
  it("rejects the TCU-class junk book for Edge/Tag but keeps feed Best", () => {
    const before = trustCfbMarket({
      kei: -20.39,
      best: 8.5,
      open: 7.5,
    });
    expect(before.trusted).toBe(false);
    expect(before.reason).toBe("absurd_vs_kei");
    expect(cfbEdgeTag(Math.abs(-20.39 - 8.5))).toBe("PLAY"); // raw would fire
    expect(cfbEdgeTag(before.market == null ? null : 28)).toBe("PASS");

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
    expect(rows[0]?.best).toBe("-8.5"); // feed kept
    expect(rows[0]?.bookKey).toBe("hardrockbet");
    expect(rows[0]?.cfbMarketTrusted).toBe(false);
    expect(rows[0]?.cfbTrustLabel).toBe("untrusted");
    expect(JSON.stringify(rows[0])).not.toContain('"best":""');
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
    expect(rows[0]?.cfbTrustLabel).toBe("no book");
    expect(rows[0]?.cfbMarketTrusted).toBe(false);
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
    const openAway = 50.5;
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
    expect(rows[0]?.best).toBe("+50.5");
    expect(rows[0]?.cfbMarketTrusted).toBe(true);
    expect(rows[0]?.cfbTrustLabel).toBeUndefined();
  });

  it("AKR@WAKE: paints Current when absurd; Edge/Tag stay PASS", () => {
    const kei = -11.93;
    const openAway = 24.5; // home −24.5
    const openHome = cfbAwayBookToHome(openAway);
    expect(openHome).toBe(-24.5);
    const ssGap = Math.abs(kei - (openHome as number));
    expect(ssGap).toBeGreaterThanOrEqual(CFB_ABSURD_VS_KEI_PTS);

    const rows = applyCfbTrustedMarketToRows([
      {
        market: "Spread",
        kei: "-11.93",
        best: "+24.5",
        open: "+24.5",
        book: "DraftKings",
        bookKey: "draftkings",
      },
    ]);
    expect(rows[0]?.best).toBe("+24.5"); // Current still painted
    expect(rows[0]?.cfbMarketTrusted).toBe(false);
    expect(rows[0]?.cfbTrustReason).toBe("absurd_vs_kei");
    expect(rows[0]?.cfbTrustLabel).toBe("untrusted");
    expect(cfbEdgeTag(null)).toBe("PASS");
  });

  it("UCLA@CAL sign-artifact: feed kept, not trusted for Edge", () => {
    const kei = -12.83;
    const openHome = cfbAwayBookToHome(-1.5);
    expect(openHome).toBe(1.5);
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
    expect(rows[0]?.best).toBe("-1.5");
    expect(rows[0]?.cfbMarketTrusted).toBe(false);
    expect(rows[0]?.cfbTrustLabel).toBe("untrusted");
  });

  it("Total rows: |kei−market| ≥ 12 → untrusted PASS; feed Best kept", () => {
    // FIU@USF-class: KEI 72.5 vs book 52.5 (+20) must not PLAY.
    const gap = Math.abs(72.5 - 52.5);
    expect(gap).toBeGreaterThanOrEqual(CFB_ABSURD_VS_KEI_PTS);
    // Raw magnitude is PLAY-band; totals sit + trust both block PLAY.
    expect(cfbEdgeTag(gap, "total")).toBe("PASS");
    expect(cfbEdgeTag(gap, "spread")).toBe("PLAY"); // totals-only sit

    const rows = applyCfbTrustedMarketToRows([
      {
        market: "Total",
        kei: "72.5",
        best: "52.5",
        open: "52.5",
        book: "DraftKings",
        bookKey: "draftkings",
      },
    ]);
    expect(rows[0]?.best).toBe("52.5");
    expect(rows[0]?.kei).toBe("72.5");
    expect(rows[0]?.cfbMarketTrusted).toBe(false);
    expect(rows[0]?.cfbTrustReason).toBe("absurd_vs_kei");
    expect(rows[0]?.cfbTrustLabel).toBe("untrusted");
    expect(cfbEdgeTag(null, "total")).toBe("PASS");
  });

  it("Total rows: does not flip sign (52.5 stays 52.5, not −52.5)", () => {
    const rows = applyCfbTrustedMarketToRows([
      {
        market: "Total",
        kei: "56.6",
        best: "52.5",
        open: "52.0",
        book: "DraftKings",
        bookKey: "draftkings",
      },
    ]);
    // If we wrongly applied cfbAwayBookToHome, gap would be |56.6−(−52.5)|≈109 → absurd.
    expect(rows[0]?.cfbMarketTrusted).toBe(true);
    expect(rows[0]?.cfbTrustLabel).toBeUndefined();
    // +4.1 was PLAY; totals PLAY now sat → PASS.
    expect(cfbEdgeTag(Math.abs(56.6 - 52.5), "total")).toBe("PASS");
  });

  it("Total rows: PLAY-band sat to PASS; LEAN still LEAN; under band PASS", () => {
    expect(cfbEdgeTag(4.1, "total")).toBe("PASS");
    expect(cfbEdgeTag(3.0, "total")).toBe("LEAN");
    expect(cfbEdgeTag(2.0, "total")).toBe("PASS");
    // Spreads still PLAY at +4.1.
    expect(cfbEdgeTag(4.1, "spread")).toBe("PLAY");

    const playRows = applyCfbTrustedMarketToRows([
      {
        market: "Total",
        kei: "56.6",
        best: "52.5",
        open: "52.5",
        book: "DraftKings",
        bookKey: "draftkings",
      },
    ]);
    expect(playRows[0]?.cfbMarketTrusted).toBe(true);
    expect(cfbEdgeTag(Math.abs(56.6 - 52.5), "total")).toBe("PASS");

    const leanRows = applyCfbTrustedMarketToRows([
      {
        market: "Total",
        kei: "55.5",
        best: "52.5",
        open: "52.5",
        book: "FanDuel",
        bookKey: "fanduel",
      },
    ]);
    expect(leanRows[0]?.cfbMarketTrusted).toBe(true);
    expect(cfbEdgeTag(Math.abs(55.5 - 52.5), "total")).toBe("LEAN");
  });

  it("Total rows: single-book |gap| ≥ 8 → untrusted", () => {
    const rows = applyCfbTrustedMarketToRows([
      {
        market: "Total",
        kei: "60.0",
        best: "51.5",
        open: "",
        book: "Hard Rock Bet",
        bookKey: "hardrockbet",
      },
    ]);
    expect(Math.abs(60.0 - 51.5)).toBeGreaterThanOrEqual(8);
    expect(Math.abs(60.0 - 51.5)).toBeLessThan(CFB_ABSURD_VS_KEI_PTS);
    expect(rows[0]?.best).toBe("51.5");
    expect(rows[0]?.cfbMarketTrusted).toBe(false);
    expect(rows[0]?.cfbTrustReason).toBe("single_book_outlier");
  });

  it("Spread rows still trust independently of Total siblings", () => {
    const rows = applyCfbTrustedMarketToRows([
      {
        market: "Spread",
        kei: "-5.3",
        best: "+3.5",
        open: "+3.0",
        book: "DraftKings",
        bookKey: "draftkings",
      },
      {
        market: "Total",
        kei: "72.5",
        best: "52.5",
        open: "52.5",
        book: "DraftKings",
        bookKey: "draftkings",
      },
    ]);
    expect(rows[0]?.cfbMarketTrusted).toBe(true);
    expect(rows[1]?.cfbMarketTrusted).toBe(false);
    expect(rows[1]?.cfbTrustReason).toBe("absurd_vs_kei");
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

  it("joins UMass Minutemen Odds name to Massachusetts Minutemen slate", () => {
    expect(
      cfbGamesMatch(
        "UMass Minutemen @ Rutgers Scarlet Knights",
        "Massachusetts Minutemen @ Rutgers Scarlet Knights",
      ),
    ).toBe(true);
    expect(
      cfbGamesMatch("UMass Minutemen @ Rutgers Scarlet Knights", "MASS @ RUT"),
    ).toBe(true);
  });

  it("never collapses Miami OH with Miami FL", () => {
    const miaStan = "Miami Hurricanes @ Stanford Cardinal";
    const mohPitt = "Miami (OH) RedHawks @ Pittsburgh Panthers";
    expect(cfbGamesMatch(miaStan, mohPitt)).toBe(false);
    // Same-opponent trap: take(1) used to be bare `miami` for both.
    expect(
      cfbGamesMatch(
        "Miami Hurricanes @ Pittsburgh Panthers",
        "Miami (OH) RedHawks @ Pittsburgh Panthers",
      ),
    ).toBe(false);
    const miaKeys = cfbGameMatchKeys(miaStan).join("|");
    const mohKeys = cfbGameMatchKeys(mohPitt).join("|");
    expect(miaKeys).toContain("miami-florida");
    expect(mohKeys).toContain("miami-ohio");
    expect(miaKeys).not.toMatch(/(^|\|)miami @/);
    expect(mohKeys).not.toMatch(/(^|\|)miami @/);
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

  it("keeps BALL@OSU Week 1 KEI a cupcake (≤ −40, WP in the 90s)", () => {
    const ballOsu = getKeiLines("cfb").find(
      (g) => g.week === 1 && g.homeAbbr === "OSU" && g.awayAbbr === "BALL",
    );
    expect(ballOsu).toBeTruthy();
    expect(ballOsu?.handicapSpreadHome).toBeLessThanOrEqual(-40);
    expect(ballOsu?.handicapSpreadHome).toBe(-40.51);
  });
});
