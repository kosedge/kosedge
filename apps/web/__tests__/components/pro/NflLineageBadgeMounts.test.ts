import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const webRoot = join(__dirname, "../../..");

function readSrc(rel: string) {
  return readFileSync(join(webRoot, rel), "utf8");
}

const CUSTOMER_BOARDS = [
  "app/edge-board/[sport]/page.tsx",
  "app/(pro)/pro/power-ratings/[sport]/page.tsx",
  "app/(pro)/pro/nfl/projections/page.tsx",
  "app/(pro)/pro/[sport]/standings/page.tsx",
  "app/(pro)/pro/[sport]/stats/page.tsx",
  "components/articles/TeamPreviewArticle.tsx",
] as const;

const ENGINE_DESKS = [
  "app/(pro)/pro/nfl/model/page.tsx",
  "app/(pro)/pro/nfl/game-boxes/page.tsx",
  "app/(pro)/pro/nfl/survivor/page.tsx",
] as const;

describe("NflLineageBadge mounts", () => {
  it("stays off customer boards (title + numbers only)", () => {
    for (const rel of CUSTOMER_BOARDS) {
      const src = readSrc(rel);
      expect(src, rel).not.toContain("NflLineageBadge");
      expect(src, rel).not.toMatch(/Method \$\{/);
      expect(src, rel).not.toContain("100,000 paths");
    }
  });

  it("remains on engine desks as a single chip", () => {
    for (const rel of ENGINE_DESKS) {
      const src = readSrc(rel);
      expect(src, rel).toContain("<NflLineageBadge");
      expect(src.match(/<NflLineageBadge/g)?.length, rel).toBe(1);
    }
  });

  it("Power Ratings keeps transparency link and drops Method/run dump", () => {
    const src = readSrc("app/(pro)/pro/power-ratings/[sport]/page.tsx");
    expect(src).toContain('hrefSuffix="#power-ratings"');
    expect(src).toContain("NflTruthStateBadges");
    expect(src).not.toContain("nfl-preseason-sim-2026-");
    expect(src).not.toMatch(/Method \$\{board/);
  });
});
