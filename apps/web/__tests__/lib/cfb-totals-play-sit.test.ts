import { describe, expect, it } from "vitest";
import { flatRowsToLegacy } from "@/lib/flat-rows-to-legacy";
import {
  applyCfbTrustedMarketToRows,
  cfbEdgeTag,
  cfbPublishTagFromEdge,
  CFB_ABSURD_VS_KEI_PTS,
  CFB_LEAN_EDGE_PTS,
  CFB_PLAY_EDGE_PTS,
  CFB_TOTALS_PLAY_ELIGIBLE,
} from "@/lib/cfb-trusted-market";

/**
 * Named W1 PLAY Overs from live assemble 2026-09-03 (edge = KEI − mkt).
 * Under CFB_TOTALS_PLAY_ELIGIBLE=false these must tag PASS, not PLAY.
 */
const W1_PLAY_OVERS: { pair: string; edge: number }[] = [
  { pair: "UNLV@HAW", edge: 11.5 },
  { pair: "TOL@MSU", edge: 11.3 },
  { pair: "MASS@RUT", edge: 11.2 },
  { pair: "MIA@STAN", edge: 11.1 },
  { pair: "LOU@MISS", edge: 10.4 },
  { pair: "WSU@WASH", edge: 10.1 },
  { pair: "WIS@ND", edge: 9.7 },
  { pair: "NIU@IOWA", edge: 9.6 },
  { pair: "UAB@ILL", edge: 8.3 },
  { pair: "WKU@NEV", edge: 8.2 },
  { pair: "KENT@SC", edge: 8.1 },
  { pair: "LIB@JMU", edge: 7.8 },
  { pair: "ARST@MEM", edge: 7.7 },
  { pair: "FRES@USC", edge: 7.4 },
  { pair: "UNT@IU", edge: 7.3 },
  { pair: "ECU@ALA", edge: 7.1 },
  { pair: "SMU@FSU", edge: 7.0 },
  { pair: "BAY@AUB", edge: 5.9 },
  { pair: "COLO@GT", edge: 5.5 },
  { pair: "SHSU@TROY", edge: 5.2 },
  { pair: "BALL@OSU", edge: 5.1 },
  { pair: "WYO@CSU", edge: 4.7 },
  { pair: "ULM@MSST", edge: 4.5 },
  { pair: "ORST@HOU", edge: 4.3 },
];

const W1_LEANS: { pair: string; edge: number }[] = [
  { pair: "UCLA@Cal", edge: 3.8 },
  { pair: "OKST@Tulsa", edge: -2.8 },
];

describe("CFB totals PLAY sit (tagger only)", () => {
  it("flag is false; spread/LEAN cuts unchanged", () => {
    expect(CFB_TOTALS_PLAY_ELIGIBLE).toBe(false);
    expect(CFB_PLAY_EDGE_PTS).toBe(4.0);
    expect(CFB_LEAN_EDGE_PTS).toBe(2.5);
    expect(CFB_ABSURD_VS_KEI_PTS).toBe(12);
  });

  it("24 named W1 PLAY Overs become PASS when tagged as totals", () => {
    expect(W1_PLAY_OVERS).toHaveLength(24);
    for (const { pair, edge } of W1_PLAY_OVERS) {
      expect(Math.abs(edge), pair).toBeGreaterThanOrEqual(CFB_PLAY_EDGE_PTS);
      expect(cfbEdgeTag(Math.abs(edge), "total"), pair).toBe("PASS");
      expect(cfbPublishTagFromEdge(Math.abs(edge), "total"), pair).toBe("PASS");
      // Spreads also sat — PLAY-band → PASS on both markets.
      expect(cfbEdgeTag(Math.abs(edge), "spread"), pair).toBe("PASS");
    }
  });

  it("preserves totals LEANs (UCLA@Cal Over +3.8, OKST@Tulsa Under −2.8)", () => {
    for (const { pair, edge } of W1_LEANS) {
      const abs = Math.abs(edge);
      expect(abs, pair).toBeGreaterThanOrEqual(CFB_LEAN_EDGE_PTS);
      expect(abs, pair).toBeLessThan(CFB_PLAY_EDGE_PTS);
      expect(cfbEdgeTag(abs, "total"), pair).toBe("LEAN");
      expect(cfbPublishTagFromEdge(abs, "total"), pair).toBe("LEAN");
    }
  });

  it("|12| absurd totals stay untrusted (no PLAY)", () => {
    // FIU@USF-class + ten more ≥12 gaps — trust clears Edge; tagger also sits PLAY.
    const absurdGaps = [
      20.0, 18.5, 16.2, 15.0, 14.1, 13.8, 13.2, 12.9, 12.4, 12.1, 12.0,
    ];
    expect(absurdGaps).toHaveLength(11);
    for (const gap of absurdGaps) {
      expect(gap).toBeGreaterThanOrEqual(CFB_ABSURD_VS_KEI_PTS);
      const rows = applyCfbTrustedMarketToRows([
        {
          market: "Total",
          kei: String(50 + gap),
          best: "50",
          open: "50",
          book: "DraftKings",
          bookKey: "draftkings",
        },
      ]);
      expect(rows[0]?.cfbMarketTrusted).toBe(false);
      expect(rows[0]?.cfbTrustReason).toBe("absurd_vs_kei");
      // Untrusted → no edge on board; even raw gap must not PLAY as total.
      expect(cfbEdgeTag(gap, "total")).toBe("PASS");
      expect(cfbEdgeTag(null, "total")).toBe("PASS");
    }
  });

  it("publishTag === display tag after remap (totals + spreads)", () => {
    for (const edge of [11.5, 4.0, 3.8, 2.8, 2.0, null]) {
      for (const market of ["total", "spread"] as const) {
        const display = cfbEdgeTag(edge, market);
        const publish = cfbPublishTagFromEdge(edge, market);
        expect(publish).toBe(display);
      }
    }
  });

  it("spread PLAY also sat; LEAN unchanged", () => {
    expect(cfbEdgeTag(4.0, "spread")).toBe("PASS");
    expect(cfbEdgeTag(11.5, "spread")).toBe("PASS");
    expect(cfbEdgeTag(3.0, "spread")).toBe("LEAN");
    expect(cfbEdgeTag(2.0, "spread")).toBe("PASS");
  });

  it("Edge Board Tag O/U uses totals sit (flatRowsToLegacy)", () => {
    const mkt = 52.5;
    const playKei = mkt + 5.1; // BALL@OSU-class Over
    const leanKei = mkt + 3.8; // UCLA@Cal-class Over
    const playRows = flatRowsToLegacy(
      [
        {
          market: "Spread",
          game: "Ball State @ Ohio State",
          week: 1,
          kei: "-42.2",
          best: "+50.5",
          open: "+50.5",
          bookKey: "draftkings",
          book: "DraftKings",
          cfbMarketTrusted: true,
        },
        {
          market: "Total",
          game: "Ball State @ Ohio State",
          week: 1,
          kei: String(playKei),
          best: String(mkt),
          open: String(mkt),
          bookKey: "draftkings",
          book: "DraftKings",
          cfbMarketTrusted: true,
        },
      ],
      "cfb",
      1,
    );
    expect(playRows[0]?.tagOU).toBe("PASS");
    expect(playRows[0]?.edgeOUNum).toBeCloseTo(5.1, 5);

    const leanRows = flatRowsToLegacy(
      [
        {
          market: "Spread",
          game: "UCLA @ California",
          week: 1,
          kei: "-3.5",
          best: "+3.0",
          open: "+3.0",
          bookKey: "fanduel",
          book: "FanDuel",
          cfbMarketTrusted: true,
        },
        {
          market: "Total",
          game: "UCLA @ California",
          week: 1,
          kei: String(leanKei),
          best: String(mkt),
          open: String(mkt),
          bookKey: "fanduel",
          book: "FanDuel",
          cfbMarketTrusted: true,
        },
      ],
      "cfb",
      1,
    );
    expect(leanRows[0]?.tagOU).toBe("LEAN");
    expect(leanRows[0]?.edgeOUNum).toBeCloseTo(3.8, 5);

    // Spread PLAY sat — trusted large edge tags PASS.
    const spreadPlay = flatRowsToLegacy(
      [
        {
          market: "Spread",
          game: "Fresno State @ USC",
          week: 1,
          kei: "-29.8",
          best: "+22.5",
          open: "+22.5",
          bookKey: "draftkings",
          book: "DraftKings",
          cfbMarketTrusted: true,
        },
        {
          market: "Total",
          game: "Fresno State @ USC",
          week: 1,
          kei: "55.0",
          best: "55.0",
          open: "55.0",
          bookKey: "draftkings",
          book: "DraftKings",
          cfbMarketTrusted: true,
        },
      ],
      "cfb",
      1,
    );
    expect(spreadPlay[0]?.tagLine).toBe("PASS");
    expect(spreadPlay[0]?.tagOU).toBe("PASS");
  });

  it("kei_total == model_total identity path untouched (no KEI edits)", () => {
    // Tagger sit must not rewrite KEI fields on Total rows.
    const rows = applyCfbTrustedMarketToRows([
      {
        market: "Total",
        kei: "56.6",
        best: "52.5",
        open: "52.5",
        book: "DraftKings",
        bookKey: "draftkings",
      },
    ]);
    expect(rows[0]?.kei).toBe("56.6");
    expect(rows[0]?.best).toBe("52.5");
    expect(rows[0]?.cfbMarketTrusted).toBe(true);
    // Would have been PLAY before sit; now PASS.
    expect(cfbEdgeTag(Math.abs(56.6 - 52.5), "total")).toBe("PASS");
  });
});
