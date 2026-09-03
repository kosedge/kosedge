import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchNflFairLines } from "@/lib/nfl-fair-lines";
import { pageDataUpstreamErrorResponse } from "@/lib/page-data-upstream";
import {
  UPSTREAM_TIMEOUT_MS,
  UpstreamTimeoutError,
} from "@/lib/upstream-fetch";

const root = process.cwd();

function readApp(rel: string): string {
  return readFileSync(path.join(root, rel), "utf8");
}

describe("NFL page-data upstream budget (Alex fair-lines timeout)", () => {
  it("declares maxDuration 30 on fair-lines, edges-desk, and assemble only", () => {
    const fair = readApp("app/api/nfl/fair-lines/route.ts");
    const edges = readApp("app/api/nfl/edges-desk/route.ts");
    const assemble = readApp("app/api/edge-board/[sport]/assemble/route.ts");

    for (const src of [fair, edges, assemble]) {
      expect(src).toMatch(/export const maxDuration = 30/);
      expect(src).toContain("UPSTREAM_TIMEOUT_MS.pageData");
      expect(src).toContain("throwOnTransportError: true");
      expect(src).toContain("pageDataUpstreamErrorResponse");
    }

    // Overview / SSR board paths must keep the short board cap — do not raise
    // the shared board constant to pageData.
    expect(UPSTREAM_TIMEOUT_MS.board).toBe(12_000);
    expect(UPSTREAM_TIMEOUT_MS.pageData).toBe(25_000);
    expect(UPSTREAM_TIMEOUT_MS.pageData).toBeGreaterThan(
      UPSTREAM_TIMEOUT_MS.board,
    );
  });

  it("fair-lines client fetches bare /api/nfl/fair-lines (no ?season=)", () => {
    const client = readApp("components/pro/nfl/NflFairLinesClient.tsx");
    expect(client).toContain('"/api/nfl/fair-lines"');
    expect(client).not.toMatch(/fetch\(`\/api\/nfl\/fair-lines\?\$\{qs\}`/);
    expect(client).not.toMatch(
      /URLSearchParams\(\{\s*season:\s*String\(season\)/,
    );
  });

  it("maps timeout → 504 and other transport → 503 (never empty 200)", async () => {
    const timedOut = pageDataUpstreamErrorResponse(
      new UpstreamTimeoutError(25_000, "https://model/nfl/fair-lines"),
    );
    expect(timedOut.status).toBe(504);
    const timedBody = (await timedOut.json()) as { error?: string };
    expect(timedBody.error).toMatch(/timed out/i);
    expect(timedBody).not.toHaveProperty("count");
    expect(timedBody).not.toHaveProperty("oddsAsOf");

    const unreachable = pageDataUpstreamErrorResponse(
      new Error("Unable to reach model service."),
    );
    expect(unreachable.status).toBe(503);
    const body = (await unreachable.json()) as { error?: string };
    expect(body.error).toBe("Unable to reach model service.");
    expect(body).not.toHaveProperty("lines");
  });
});

describe("fetchNflFairLines throwOnTransportError", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  function stubHangingFetch() {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url: string, init?: RequestInit) =>
          new Promise<Response>((_resolve, reject) => {
            const signal = init?.signal;
            if (!signal) return;
            signal.addEventListener("abort", () => {
              reject(new DOMException("Aborted", "AbortError"));
            });
          }),
      ),
    );
  }

  it("soft path returns empty board on timeout (SSR / Overview)", async () => {
    vi.useFakeTimers();
    stubHangingFetch();

    const pending = fetchNflFairLines({
      season: 2026,
      daysAhead: 200,
      timeoutMs: 50,
    });
    const assertion = pending.then((board) => {
      expect(board.count).toBe(0);
      expect(board.oddsAsOf).toBeNull();
      expect(board.error).toBe("Unable to reach model service.");
      expect(board.lines).toEqual([]);
    });
    await vi.advanceTimersByTimeAsync(60);
    await assertion;
  });

  it("page-data path throws UpstreamTimeoutError (route → 504, not fake slate)", async () => {
    vi.useFakeTimers();
    stubHangingFetch();

    const pending = fetchNflFairLines({
      season: 2026,
      daysAhead: 200,
      timeoutMs: 50,
      throwOnTransportError: true,
    });
    const assertion =
      expect(pending).rejects.toBeInstanceOf(UpstreamTimeoutError);
    await vi.advanceTimersByTimeAsync(60);
    await assertion;
  });
});
