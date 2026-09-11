import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";

const root = process.cwd();

function readRel(rel: string): string {
  return readFileSync(path.join(root, rel), "utf8");
}

describe("GO-1c / INC-2026-09-07 (E) warm-page-data cron (public cache path)", () => {
  it("source-locks cron warm to assemble GETs only (≤40s, no Date.now as-of)", () => {
    const route = readRel("app/api/cron/warm-page-data/route.ts");
    expect(route).toMatch(/export const maxDuration = 40/);
    expect(route).toContain("/api/edge-board/nfl/assemble?slate=week1");
    expect(route).toContain("/api/edge-board/cfb/assemble");
    expect(route).not.toContain("/api/edge-board/cfb/assemble?week=1");
    expect(route).toContain("CRON_SECRET");
    expect(route).not.toContain("loadAssembledEdgeBoardRows");
    expect(route).not.toContain("linesAsOf:");
    expect(route).not.toContain("oddsAsOf:");
    // Timing of warm GETs may use Date.now(); must not stamp board as-of.
    expect(route).not.toMatch(/linesAsOf\s*:\s*Date\.now/);
    expect(route).not.toMatch(/oddsAsOf\s*:\s*Date\.now/);
    expect(route).not.toMatch(/asOf\s*:\s*new Date/);
  });

  it("warms authentic public cache path (no Authorization on assemble GET)", () => {
    const route = readRel("app/api/cron/warm-page-data/route.ts");
    // Cron route still authorizes inbound with Bearer CRON_SECRET.
    expect(route).toContain("Bearer ${secret}");
    // Outbound warm must not forward Authorization (CDN BYPASS).
    expect(route).toContain('"x-kosedge-warm": "1"');
    expect(route).not.toMatch(
      /fetch\([^)]*authorization:\s*`Bearer \$\{process\.env\.CRON_SECRET\}`/s,
    );
    expect(route).not.toMatch(/headers:\s*\{[^}]*authorization:\s*`Bearer/s);
    // Do not warm full slate (Odds spend bound).
    expect(route).not.toContain("slate=full");
    // Freshness / alert hooks for observe.
    expect(route).toContain("x-vercel-cache");
    expect(route).toContain("cdn_bypass");
    expect(route).toContain("freshness");
    expect(route).toContain("alerts");
  });

  it("registers vercel cron path every minute", () => {
    const vercel = JSON.parse(readRel("vercel.json")) as {
      crons?: Array<{ path?: string; schedule?: string }>;
    };
    const warm = vercel.crons?.find(
      (c) => c.path === "/api/cron/warm-page-data",
    );
    expect(warm?.schedule).toBe("* * * * *");
  });

  it("rate-limit skips cron/warm traffic", () => {
    const rl = readRel("lib/security/rate-limit.ts");
    expect(rl).toContain("isCronOrWarmRequest");
    expect(rl).toContain("x-kosedge-warm");
    expect(rl).toContain("/api/cron/");
  });
});
