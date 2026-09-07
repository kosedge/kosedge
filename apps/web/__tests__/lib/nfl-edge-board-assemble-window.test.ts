import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import {
  NFL_EDGE_BOARD_FULL_WINDOW,
  NFL_EDGE_BOARD_LIVE_WINDOW,
  assertHonestNflFullSlateWindow,
  nflAssembleWindowForSlate,
} from "@/lib/nfl-edge-board-assemble-window";
import { edgeBoardAssembleHref } from "@/lib/edge-board-assemble-href";
import { UPSTREAM_TIMEOUT_MS } from "@/lib/upstream-fetch";

const webRoot = path.join(__dirname, "../..");

function readRel(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

describe("INC-2026-09-07 (C) NFL assemble window + full-slate honesty", () => {
  it("Week 1 / live window is narrow; full window is wider", () => {
    expect(NFL_EDGE_BOARD_LIVE_WINDOW.daysAhead).toBeLessThanOrEqual(14);
    expect(NFL_EDGE_BOARD_LIVE_WINDOW.daysAhead).toBeLessThan(
      NFL_EDGE_BOARD_FULL_WINDOW.daysAhead,
    );
    expect(nflAssembleWindowForSlate("week1")).toEqual(
      NFL_EDGE_BOARD_LIVE_WINDOW,
    );
    expect(nflAssembleWindowForSlate("full")).toEqual(
      NFL_EDGE_BOARD_FULL_WINDOW,
    );
  });

  it("build-edge-board-rows uses slate-scoped window (not hard-coded 200 on week1)", () => {
    const src = readRel("lib/build-edge-board-rows.ts");
    expect(src).toContain("nflAssembleWindowForSlate");
    expect(src).toContain("daysAhead: window.daysAhead");
    expect(src).toContain("includePastDays: window.includePastDays");
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
    expect(
      edgeBoardAssembleHref({ sportKey: "nfl", slate: "week1" }),
    ).not.toBe(edgeBoardAssembleHref({ sportKey: "nfl", slate: "full" }));
  });

  it("fail-closed: refuses narrow live window labeled as full slate", () => {
    expect(() =>
      assertHonestNflFullSlateWindow("full", NFL_EDGE_BOARD_LIVE_WINDOW),
    ).toThrow(/full-slate assemble unavailable/i);

    expect(() =>
      assertHonestNflFullSlateWindow("full", NFL_EDGE_BOARD_FULL_WINDOW),
    ).not.toThrow();

    expect(() =>
      assertHonestNflFullSlateWindow("week1", NFL_EDGE_BOARD_LIVE_WINDOW),
    ).not.toThrow();
  });

  it("assemble route wires honesty + keeps pageData 25s ceiling", () => {
    const assemble = readRel("app/api/edge-board/[sport]/assemble/route.ts");
    expect(assemble).toContain("assertHonestNflFullSlateWindow");
    expect(assemble).toContain("nflAssembleWindowForSlate");
    expect(assemble).toContain("UPSTREAM_TIMEOUT_MS.pageData");
    expect(assemble).toContain("pageDataUpstreamErrorResponse");
    expect(UPSTREAM_TIMEOUT_MS.pageData).toBe(25_000);
  });
});
