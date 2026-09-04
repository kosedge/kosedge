import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();

function readRel(rel: string): string {
  return readFileSync(path.join(root, rel), "utf8");
}

describe("GO-1c warm-page-data cron (no invent SoT)", () => {
  it("source-locks cron warm to assemble GETs only (≤40s, no Date.now as-of)", () => {
    const route = readRel("app/api/cron/warm-page-data/route.ts");
    expect(route).toMatch(/export const maxDuration = 40/);
    expect(route).toContain("/api/edge-board/nfl/assemble?slate=week1");
    expect(route).toContain("/api/edge-board/cfb/assemble?week=1");
    expect(route).toContain("CRON_SECRET");
    expect(route).not.toContain("loadAssembledEdgeBoardRows");
    expect(route).not.toContain("linesAsOf:");
    expect(route).not.toContain("oddsAsOf:");
    // Timing of warm GETs may use Date.now(); must not stamp board as-of.
    expect(route).not.toMatch(/linesAsOf\s*:\s*Date\.now/);
    expect(route).not.toMatch(/oddsAsOf\s*:\s*Date\.now/);
    expect(route).not.toMatch(/asOf\s*:\s*new Date/);
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
