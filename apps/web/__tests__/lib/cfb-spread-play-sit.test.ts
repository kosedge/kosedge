import { describe, expect, it } from "vitest";
import { flatRowsToLegacy } from "@/lib/flat-rows-to-legacy";
import {
  applyCfbTrustedMarketToRows,
  cfbEdgeTag,
  cfbPublishTagFromEdge,
  CFB_ABSURD_VS_KEI_PTS,
  CFB_LEAN_EDGE_PTS,
  CFB_PLAY_EDGE_PTS,
  CFB_SPREAD_PLAY_ELIGIBLE,
  CFB_TOTALS_PLAY_ELIGIBLE,
} from "@/lib/cfb-trusted-market";

/**
 * Named W1 trusted spread PLAY edges from handicap card / grades
 * (`cfb-w1-handicap-card-20260831` / assemble family). Under
 * CFB_SPREAD_PLAY_ELIGIBLE=false these must tag PASS, not PLAY.
 */
const W1_SPREAD_PLAYS: { pair: string; edge: number }[] = [
  { pair: "OKST@TLSA", edge: 11.7 },
  { pair: "MOST@TAMU", edge: 11.0 },
  { pair: "KENT@SCAR", edge: 10.7 },
  { pair: "UTEP@OU", edge: 10.4 },
  { pair: "BC@CIN", edge: 10.3 },
  { pair: "BALL@OSU", edge: 10.0 },
  { pair: "CLEM@LSU", edge: 9.0 },
  { pair: "UNT@IU", edge: 8.9 },
  { pair: "NIU@IOWA", edge: 8.7 },
  { pair: "TXST@TEX", edge: 7.1 },
  { pair: "WIS@ND", edge: 6.2 },
  { pair: "WYO@CSU", edge: 6.1 },
  { pair: "TOL@MSU", edge: 6.1 },
  { pair: "WKU@NEV", edge: 5.9 },
  { pair: "WSU@WASH", edge: 5.9 },
  { pair: "CCU@WVU", edge: 5.7 },
  { pair: "UNLV@HAW", edge: 5.5 },
  { pair: "SMU@FSU", edge: 5.4 },
  { pair: "MRSH@PSU", edge: 5.3 },
  { pair: "CMU@UNM", edge: 5.2 },
  { pair: "UAB@ILL", edge: 4.9 },
  { pair: "FRES@USC", edge: 4.8 },
  { pair: "LOU@MISS", edge: 4.6 },
  { pair: "TULN@DUKE", edge: 4.4 },
  { pair: "ARST@MEM", edge: 4.1 },
];

const W1_SPREAD_LEANS: { pair: string; edge: number }[] = [
  { pair: "MASS@RUT", edge: 3.9 },
  { pair: "FIU@USF", edge: 3.9 },
  { pair: "LIB@JMU", edge: 2.9 },
  { pair: "BOISE@ORE", edge: 2.5 },
];

describe("CFB spread PLAY sit (tagger only)", () => {
  it("flag is false; LEAN/|12| cuts unchanged; totals sit stays", () => {
    expect(CFB_SPREAD_PLAY_ELIGIBLE).toBe(false);
    expect(CFB_TOTALS_PLAY_ELIGIBLE).toBe(false);
    expect(CFB_PLAY_EDGE_PTS).toBe(4.0);
    expect(CFB_LEAN_EDGE_PTS).toBe(2.5);
    expect(CFB_ABSURD_VS_KEI_PTS).toBe(12);
  });

  it("W1 spread PLAY-band edges become PASS", () => {
    expect(W1_SPREAD_PLAYS.length).toBeGreaterThanOrEqual(24);
    for (const { pair, edge } of W1_SPREAD_PLAYS) {
      expect(Math.abs(edge), pair).toBeGreaterThanOrEqual(CFB_PLAY_EDGE_PTS);
      expect(cfbEdgeTag(Math.abs(edge), "spread"), pair).toBe("PASS");
      expect(cfbPublishTagFromEdge(Math.abs(edge), "spread"), pair).toBe(
        "PASS",
      );
      // Totals sit independently — PLAY-band totals also PASS.
      expect(cfbEdgeTag(Math.abs(edge), "total"), pair).toBe("PASS");
    }
  });

  it("preserves spread LEANs (2.5–4.0)", () => {
    for (const { pair, edge } of W1_SPREAD_LEANS) {
      const abs = Math.abs(edge);
      expect(abs, pair).toBeGreaterThanOrEqual(CFB_LEAN_EDGE_PTS);
      expect(abs, pair).toBeLessThan(CFB_PLAY_EDGE_PTS);
      expect(cfbEdgeTag(abs, "spread"), pair).toBe("LEAN");
      expect(cfbPublishTagFromEdge(abs, "spread"), pair).toBe("LEAN");
    }
  });

  it("|edge|≥4 → PASS; LEAN 2.5–4 still LEAN; below 2.5 PASS", () => {
    expect(cfbEdgeTag(4.0, "spread")).toBe("PASS");
    expect(cfbEdgeTag(11.5, "spread")).toBe("PASS");
    expect(cfbEdgeTag(3.0, "spread")).toBe("LEAN");
    expect(cfbEdgeTag(2.5, "spread")).toBe("LEAN");
    expect(cfbEdgeTag(2.0, "spread")).toBe("PASS");
  });

  it("|12| absurd spreads stay untrusted (no PLAY)", () => {
    const absurdGaps = [
      20.0, 18.5, 16.2, 15.0, 14.1, 13.8, 13.2, 12.9, 12.4, 12.1, 12.0,
    ];
    expect(absurdGaps).toHaveLength(11);
    for (const gap of absurdGaps) {
      expect(gap).toBeGreaterThanOrEqual(CFB_ABSURD_VS_KEI_PTS);
      const rows = applyCfbTrustedMarketToRows([
        {
          market: "Spread",
          // Home-signed KEI vs away-signed board (+gap away → home −gap).
          kei: String(-(50 + gap)),
          best: "+50",
          open: "+50",
          book: "DraftKings",
          bookKey: "draftkings",
        },
      ]);
      expect(rows[0]?.cfbMarketTrusted).toBe(false);
      expect(rows[0]?.cfbTrustReason).toBe("absurd_vs_kei");
      expect(cfbEdgeTag(gap, "spread")).toBe("PASS");
      expect(cfbEdgeTag(null, "spread")).toBe("PASS");
    }
  });

  it("publishTag === display tag after remap (spreads + totals)", () => {
    for (const edge of [11.5, 4.0, 3.8, 2.8, 2.0, null]) {
      for (const market of ["total", "spread"] as const) {
        const display = cfbEdgeTag(edge, market);
        const publish = cfbPublishTagFromEdge(edge, market);
        expect(publish).toBe(display);
      }
    }
  });

  it("totals still never PLAY", () => {
    expect(cfbEdgeTag(4.1, "total")).toBe("PASS");
    expect(cfbEdgeTag(11.5, "total")).toBe("PASS");
    expect(cfbEdgeTag(3.0, "total")).toBe("LEAN");
  });

  it("Edge Board Tag Line does not invent tags when assemble omits publishTag", () => {
    // FRES@USC-class edge — sit tests cover cfbEdgeTag; Edge Board stays blank
    // until assemble ships publishTag (live Week 1: 0 tags on 164 rows).
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
    expect(spreadPlay[0]?.tagLine).toBeUndefined();
    expect(spreadPlay[0]?.tagOU).toBeUndefined();
    expect(Math.abs(spreadPlay[0]?.edgeLineNum ?? 0)).toBeGreaterThanOrEqual(
      CFB_PLAY_EDGE_PTS,
    );

    // When assemble does publish, honor it (no client remap invent).
    const published = flatRowsToLegacy(
      [
        {
          market: "Spread",
          game: "UMass @ Rutgers",
          week: 1,
          kei: "-25.6",
          best: "+29.5",
          open: "+29.5",
          bookKey: "hardrockbet",
          book: "Hard Rock Bet",
          cfbMarketTrusted: true,
          publishTag: "LEAN",
        },
        {
          market: "Total",
          game: "UMass @ Rutgers",
          week: 1,
          kei: "52.0",
          best: "52.0",
          open: "52.0",
          bookKey: "hardrockbet",
          book: "Hard Rock Bet",
          cfbMarketTrusted: true,
          publishTag: "PASS",
        },
      ],
      "cfb",
      1,
    );
    expect(published[0]?.tagLine).toBe("LEAN");
    expect(published[0]?.tagOU).toBe("PASS");
    expect(Math.abs(published[0]?.edgeLineNum ?? 0)).toBeGreaterThanOrEqual(
      CFB_LEAN_EDGE_PTS,
    );
    expect(Math.abs(published[0]?.edgeLineNum ?? 0)).toBeLessThan(
      CFB_PLAY_EDGE_PTS,
    );
  });

  it("kei fields untouched (no KEI edits)", () => {
    const rows = applyCfbTrustedMarketToRows([
      {
        market: "Spread",
        kei: "-29.8",
        best: "+22.5",
        open: "+22.5",
        book: "DraftKings",
        bookKey: "draftkings",
      },
    ]);
    expect(rows[0]?.kei).toBe("-29.8");
    expect(rows[0]?.best).toBe("+22.5");
    expect(rows[0]?.cfbMarketTrusted).toBe(true);
    expect(cfbEdgeTag(Math.abs(-29.8 - -22.5), "spread")).toBe("PASS");
  });
});
