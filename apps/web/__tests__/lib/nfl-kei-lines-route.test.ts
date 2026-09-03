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
    const oddsPage = readFileSync(
      path.join(process.cwd(), "app/odds/[sport]/page.tsx"),
      "utf8",
    );
    expect(oddsPage).toContain("getKeiLinesBoardHref");
    expect(oddsPage).not.toMatch(/href=\{`\/pro\/kei-lines\/\$\{/);
    expect(oddsPage).not.toContain("/pro/kei-lines/nfl");
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

  it("does not leave NFL empty-state invent copy on the live path helper", () => {
    expect(getKeiLinesBoardHref("nfl")).not.toContain("kei-lines");
  });
});
