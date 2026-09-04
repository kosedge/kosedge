import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { getSportDeskConfig } from "@/lib/pro-sport-desk";
import { getKeiLinesBoardHref, getSportToolNav } from "@/lib/sport-pro-nav";

const STUB_COPY =
  "Run the pipeline export to generate data/processed/kei_lines_*.json";

describe("NFL KEI Lines live board (not pipeline stub)", () => {
  it("resolves NFL KEI Lines to fair-lines, never the stub route", () => {
    expect(getKeiLinesBoardHref("nfl")).toBe("/pro/nfl/fair-lines");
    expect(getKeiLinesBoardHref("nfl")).not.toBe("/pro/kei-lines/nfl");
  });

  it("keeps Pro tool nav + betting desk KEI Lines on the live board", () => {
    const kei = getSportToolNav("nfl").find((i) => i.label === "KEI Lines");
    expect(kei?.href).toBe("/pro/nfl/fair-lines");
    expect(getSportDeskConfig("nfl").cards[0]?.href).toBe(
      "/pro/nfl/fair-lines",
    );
  });

  it("Compare Odds KEI Lines control uses getKeiLinesBoardHref", () => {
    const oddsBoard = readFileSync(
      path.join(process.cwd(), "components/OddsCompareBoard.tsx"),
      "utf8",
    );
    expect(oddsBoard).toContain("getKeiLinesBoardHref");
    expect(oddsBoard).not.toMatch(/href=\{`\/pro\/kei-lines\/\$\{/);
    expect(oddsBoard).not.toContain("/pro/kei-lines/nfl");
  });

  it("redirects /pro/kei-lines/nfl away from the pipeline stub", () => {
    const page = readFileSync(
      path.join(process.cwd(), "app/(pro)/pro/kei-lines/[sport]/page.tsx"),
      "utf8",
    );
    const nextConfig = readFileSync(
      path.join(process.cwd(), "next.config.ts"),
      "utf8",
    );
    expect(page).toMatch(
      /sportKey === "nfl"\) redirect\("\/pro\/nfl\/fair-lines"\)/,
    );
    expect(page).not.toContain(STUB_COPY);
    expect(nextConfig).toContain('source: "/pro/kei-lines/nfl"');
    expect(nextConfig).toContain('destination: "/pro/nfl/fair-lines"');
  });

  it("permanently redirects /pro/{sport}/kei-lines → fair-lines for all six", () => {
    const nextConfig = readFileSync(
      path.join(process.cwd(), "next.config.ts"),
      "utf8",
    );
    expect(nextConfig).toContain(
      'source: "/pro/:sport(nfl|cfb|mlb|nba|nhl|wnba)/kei-lines"',
    );
    expect(nextConfig).toContain('destination: "/pro/:sport/fair-lines"');
    expect(nextConfig).toMatch(
      /source: "\/pro\/:sport\(nfl\|cfb\|mlb\|nba\|nhl\|wnba\)\/kei-lines"[\s\S]*?permanent: true/,
    );
  });

  it("does not leave NFL empty-state invent copy on the live path helper", () => {
    expect(getKeiLinesBoardHref("nfl")).not.toContain("kei-lines");
  });
});
