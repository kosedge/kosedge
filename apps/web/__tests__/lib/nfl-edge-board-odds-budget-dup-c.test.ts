import { afterEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fetchNflFairLines } from "@/lib/nfl-fair-lines";

const root = process.cwd();

function readApp(rel: string): string {
  return readFileSync(path.join(root, rel), "utf8");
}

describe("WS-02 DUP-C NFL Week1 Odds budget (S1+S2)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("assemble breaks live∥live Promise.all and uses fair-lines skip", () => {
    const src = readApp("lib/build-edge-board-rows.ts");
    expect(src).toContain('oddsMode: "skip"');
    expect(src).toContain("persistOdds: false");
    expect(src).not.toContain('oddsMode: "reuse"');
    expect(src).not.toContain("oddsPayload:");
    // Must not parallelize live Odds pull with live fair-lines.
    expect(src).not.toMatch(
      /Promise\.all\(\[\s*pullOddsRows\("nfl"\)\s*,\s*fetchNflFairLines/,
    );
    expect(src).toContain('await pullOddsRows("nfl")');
    expect(src).toContain("await fetchNflFairLines");
  });

  it("fetchNflFairLines GET odds_mode=skip keeps persist=0", async () => {
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const href = String(input);
        expect(href).toContain("persist=0");
        expect(href).toContain("odds_mode=skip");
        expect(String(init?.method || "GET").toUpperCase()).toBe("GET");
        return new Response(
          JSON.stringify({
            season: 2026,
            count: 0,
            lines: [],
            diagnostics: {
              odds_mode: "skip",
              odds_persisted: { snapshots_inserted: 0 },
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchNflFairLines({ season: 2026, oddsMode: "skip" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("CFB assemble path untouched (no NFL oddsMode reuse wiring)", () => {
    const src = readApp("lib/build-edge-board-rows.ts");
    // CFB still uses generic pullOddsRows path — oddsMode only inside assembleNfl.
    expect(src).toContain("applyCfbTrustedMarketToRows(merged)");
    expect(src).toMatch(
      /if \(sport === "cfb"\) \{\s*rows = applyCfbTrustedMarketToRows\(merged\);/,
    );
    const nflBlock = src.slice(
      src.indexOf("async function assembleNflEdgeBoardRows"),
      src.indexOf("export async function loadAssembledEdgeBoardRows"),
    );
    expect(nflBlock).toContain('oddsMode: "skip"');
    expect(nflBlock).not.toContain('oddsMode: "reuse"');
    expect(nflBlock).not.toContain("applyCfbTrustedMarketToRows");
  });
});
