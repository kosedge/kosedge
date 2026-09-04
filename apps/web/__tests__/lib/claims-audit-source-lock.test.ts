import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const webRoot = path.join(__dirname, "../..");

function readCustomer(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

/**
 * #10 Trust/Claims Audit — KOS-22 bounded FLAG removals (Riley CLEAR).
 * Source-lock: flagged claim strings must not silently return to customer surfaces.
 * Not a methodology rewrite; removals only.
 */
describe("KOS-22 claims audit source-lock (bounded FLAG removals)", () => {
  it("C03 homepage has no Sharper Data. Smarter Bets. tagline", () => {
    const page = readCustomer("app/page.tsx");
    expect(page).not.toContain("Sharper Data. Smarter Bets.");
  });

  it("C07 methodology has no real-framework promise clause", () => {
    const page = readCustomer("app/methodology/page.tsx");
    expect(page).not.toContain(
      "betting with a real framework beats betting without",
    );
  });

  it("C09 about has no real-process promise clause", () => {
    const page = readCustomer("app/about/page.tsx");
    expect(page).not.toContain(
      "betting with a real process beats betting without one",
    );
  });

  it("C20 NFL props uses N/A—DATA GAP (not no mkt)", () => {
    const page = readCustomer("app/(pro)/pro/nfl/props/page.tsx");
    expect(page).not.toContain("no mkt");
    expect(page).toContain("N/A—DATA GAP");
  });

  it("C21 pricing has no Built for long-term edge", () => {
    const page = readCustomer("components/ProPricing.tsx");
    expect(page).not.toContain("Built for long-term edge");
  });

  it("C23 NFL overview edges copy is side-only (no and confidence)", () => {
    const ia = readCustomer("lib/pro-sport-ia.ts");
    const desk = readCustomer("lib/pro-sport-desk.ts");
    expect(ia).not.toContain(
      "Thresholded game + prop edges with side and confidence.",
    );
    expect(desk).not.toContain(
      "Thresholded game + prop edges with side and confidence.",
    );
    expect(ia).toContain("Thresholded game + prop edges with side.");
    expect(desk).toContain("Thresholded game + prop edges with side.");
  });

  it("C24 Performance hint has no ROI/EV live-performance claim", () => {
    const ia = readCustomer("lib/pro-sport-ia.ts");
    expect(ia).not.toContain("ROI / EV");
    expect(ia).not.toContain(
      "Closest live performance metrics surface",
    );
    expect(ia).toMatch(/Performance page TBD/i);
  });

  it("C25 edges desk has no Min confidence chrome", () => {
    const client = readCustomer("components/pro/nfl/NflEdgesDeskClient.tsx");
    const page = readCustomer("app/(pro)/pro/nfl/edges/page.tsx");
    expect(client).not.toContain("Min confidence:");
    expect(client).not.toContain("MIN_CONF_OPTIONS");
    expect(client).not.toContain("minConfidence");
    expect(page).not.toContain("minConfidence");
    expect(page).not.toContain("minConf");
  });

  it("C26 CLV Tracker darks public beat-% / avg CLV metrics", () => {
    const page = readCustomer("app/(pro)/pro/clv-tracker/page.tsx");
    expect(page).toContain('pageTitle="CLV Tracker"');
    expect(page).not.toMatch(/pageTitle=["']Signal Ledger["']/);
    // Metric chrome that previously painted customer beat-% / avg CLV cards.
    expect(page).not.toContain("avg CLV");
    expect(page).not.toContain("Beat close %");
    expect(page).not.toContain("of plays beat the closing line");
    expect(page).not.toContain("loadNflClvBenchmarkReport");
    expect(page).not.toContain("positiveRate");
    expect(page).not.toContain("resultsCombined");
    expect(page).toContain("clv-tracker-unavailable");
    expect(page).toMatch(/unavailable/i);
  });
});

