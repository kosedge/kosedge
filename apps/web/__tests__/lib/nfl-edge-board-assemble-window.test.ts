import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import {
  NFL_EDGE_BOARD_FULL_WINDOW,
  NFL_EDGE_BOARD_LIVE_WINDOW,
  loadGovernedNflFullSlate,
  nflAssembleWindowForSlate,
  requireGovernedNflFullSlate,
} from "@/lib/nfl-edge-board-assemble-window";
import { edgeBoardAssembleHref } from "@/lib/edge-board-assemble-href";
import { UPSTREAM_TIMEOUT_MS } from "@/lib/upstream-fetch";
import { getEdgeBoardFullSlatePath } from "@/lib/data-paths";

const webRoot = path.join(__dirname, "../..");

function readRel(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

describe("INC-2026-09-07 (C) NFL assemble window + full-slate governance", () => {
  it("Week 1 / live window is narrow", () => {
    expect(NFL_EDGE_BOARD_LIVE_WINDOW.daysAhead).toBeLessThanOrEqual(14);
    expect(NFL_EDGE_BOARD_LIVE_WINDOW.daysAhead).toBeLessThan(
      NFL_EDGE_BOARD_FULL_WINDOW.daysAhead,
    );
    expect(nflAssembleWindowForSlate("week1")).toEqual(
      NFL_EDGE_BOARD_LIVE_WINDOW,
    );
  });

  it("refuses live full-slate window (no daysAhead=200 customer path)", () => {
    expect(() => nflAssembleWindowForSlate("full")).toThrow(
      /governed cache\/snapshot required/i,
    );
  });

  it("build-edge-board-rows refuses live full assemble + uses narrow week1 window", () => {
    const src = readRel("lib/build-edge-board-rows.ts");
    expect(src).toContain("nflAssembleWindowForSlate");
    expect(src).toContain('nflAssembleWindowForSlate("week1")');
    expect(src).toContain("refusing live daysAhead=200 path");
    expect(src).toContain("daysAhead: window.daysAhead");
    expect(src).not.toMatch(/daysAhead:\s*200/);
  });

  it("cache keys cannot mix sport/window/run (href + query)", () => {
    expect(edgeBoardAssembleHref({ sportKey: "nfl", slate: "week1" })).toBe(
      "/api/edge-board/nfl/assemble?slate=week1",
    );
    expect(edgeBoardAssembleHref({ sportKey: "nfl", slate: "full" })).toBe(
      "/api/edge-board/nfl/assemble?slate=full",
    );
    expect(edgeBoardAssembleHref({ sportKey: "cfb", cfbWeek: 1 })).toBe(
      "/api/edge-board/cfb/assemble?week=1",
    );
    expect(edgeBoardAssembleHref({ sportKey: "nfl", slate: "week1" })).not.toBe(
      edgeBoardAssembleHref({ sportKey: "nfl", slate: "full" }),
    );
  });

  it("fail-closed: missing governed full snapshot throws (no invent)", () => {
    // No edge_board_full_slate_nfl.json shipped until B/D spine — must fail closed.
    expect(getEdgeBoardFullSlatePath("nfl")).toContain(
      "edge_board_full_slate_nfl.json",
    );
    expect(loadGovernedNflFullSlate()).toBeNull();
    expect(() => requireGovernedNflFullSlate()).toThrow(
      /governed cache\/snapshot missing/i,
    );
  });

  it("assemble route: full = governed snapshot; week1 = live narrow; 25s pageData", () => {
    const assemble = readRel("app/api/edge-board/[sport]/assemble/route.ts");
    expect(assemble).toContain("requireGovernedNflFullSlate");
    expect(assemble).toContain('slate === "full"');
    expect(assemble).toContain('slate: "week1"');
    expect(assemble).toContain("UPSTREAM_TIMEOUT_MS.pageData");
    expect(assemble).toContain("pageDataUpstreamErrorResponse");
    expect(assemble).not.toContain("nflAssembleWindowForSlate(slate)");
    expect(UPSTREAM_TIMEOUT_MS.pageData).toBe(25_000);
  });
});
