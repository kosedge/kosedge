import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  getSportEdgeBoardHref,
  getSportPrimaryNav,
} from "@/lib/sport-pro-nav";
import { SPORTS } from "@/lib/sports";
import {
  BEST_VALUE_TIER_REACHABLE,
  displayActionLabel,
  reachableActionLabels,
} from "@/lib/nfl-dead-tiers";

const webRoot = path.join(__dirname, "../..");

describe("Edge Board Product Center #4 — canonical URL", () => {
  it("permanently redirects /pro/{sport}/edge-board → /edge-board/{sport}", () => {
    const nextConfig = readFileSync(
      path.join(webRoot, "next.config.ts"),
      "utf8",
    );
    expect(nextConfig).toContain(
      'source: "/pro/:sport(nfl|cfb|mlb|nba|nhl|wnba|ncaam)/edge-board"',
    );
    expect(nextConfig).toContain('destination: "/edge-board/:sport"');
    expect(nextConfig).toMatch(
      /source: "\/pro\/:sport\(nfl\|cfb\|mlb\|nba\|nhl\|wnba\|ncaam\)\/edge-board"[\s\S]*?permanent: true/,
    );
  });

  it("permanently redirects /pro/nfl/boards → /edge-board/nfl", () => {
    const nextConfig = readFileSync(
      path.join(webRoot, "next.config.ts"),
      "utf8",
    );
    expect(nextConfig).toContain('source: "/pro/nfl/boards"');
    expect(nextConfig).toContain('destination: "/edge-board/nfl"');
    expect(nextConfig).toMatch(
      /source: "\/pro\/nfl\/boards"[\s\S]*?permanent: true/,
    );
  });

  it("NFL Pro alias pages permanentRedirect to canonical /edge-board/nfl", () => {
    const edgeAlias = readFileSync(
      path.join(webRoot, "app/(pro)/pro/nfl/edge-board/page.tsx"),
      "utf8",
    );
    const boardsAlias = readFileSync(
      path.join(webRoot, "app/(pro)/pro/nfl/boards/page.tsx"),
      "utf8",
    );
    expect(edgeAlias).toContain("permanentRedirect");
    expect(edgeAlias).toMatch(/permanentRedirect\(`?\/edge-board\/nfl/);
    expect(edgeAlias).not.toMatch(/\bredirect\(/);
    expect(boardsAlias).toContain('permanentRedirect("/edge-board/nfl")');
  });

  it("internal nav links Edge Board at /edge-board/{sport}, never /pro/.../edge-board", () => {
    for (const sport of SPORTS) {
      const href = getSportEdgeBoardHref(sport.key);
      expect(href.startsWith("/edge-board/")).toBe(true);
      expect(href).not.toMatch(/\/pro\/.+\/edge-board/);
      const primary = getSportPrimaryNav(sport.key);
      const edge = primary.find((i) => i.label === "Edge Board");
      expect(edge?.href.startsWith("/edge-board/")).toBe(true);
      expect(edge?.href).not.toMatch(/\/pro\/.+\/edge-board/);
    }
  });
});

describe("Edge Board Product Center #4 — tag quarantine (no Best Bet chrome)", () => {
  it("subscriber display collapses BEST VALUE → PLAY while tier is dark", () => {
    expect(BEST_VALUE_TIER_REACHABLE).toBe(false);
    expect(displayActionLabel("BEST VALUE")).toBe("PLAY");
    expect(reachableActionLabels()).toEqual(
      expect.arrayContaining(["PASS", "LEAN", "PLAY"]),
    );
    expect(reachableActionLabels()).not.toContain("BEST VALUE");
  });

  it("EdgeBoard UI has no Best Bet / BEST VALUE customer chrome", () => {
    const src = readFileSync(
      path.join(webRoot, "components/EdgeBoard.tsx"),
      "utf8",
    );
    // Publish grammar only — gold Best Value / Best Bet chrome stays dark.
    expect(src).toContain("toPublishActionLabel");
    expect(src).toContain('type PublishActionLabel = "PLAY" | "LEAN" | "PASS"');
    expect(src).not.toMatch(/bg-kos-gold text-black/);
    expect(src).not.toMatch(/shownLabel === "BEST VALUE"/);
    expect(src).not.toMatch(/>\s*Best Bet\s*</);
    expect(src).not.toMatch(/>\s*BEST VALUE\s*</);
    expect(src).not.toMatch(/isBestBet/);
    expect(src).not.toMatch(/point_grade|pointGrade/);
    // Legend promises reachable labels only (PLAY / LEAN / PASS while dark).
    expect(src).toContain("reachableActionLabels().join");
  });

  it("customer decision quarantine strips point_grade fork", () => {
    const src = readFileSync(
      path.join(webRoot, "lib/nfl-dead-tiers.ts"),
      "utf8",
    );
    expect(src).toContain("delete out.point_grade");
    expect(src).toContain("delete out.pointGrade");
    expect(src).toContain("delete out.cover_grade");
  });

  it("CFB Edge Board does not invent tags from edge without publishTag", () => {
    const src = readFileSync(
      path.join(webRoot, "lib/flat-rows-to-legacy.ts"),
      "utf8",
    );
    expect(src).toContain("Never invent PLAY/LEAN/PASS from edge");
    expect(src).not.toMatch(/return cfbEdgeTag\(/);
  });
});
