import { describe, expect, it } from "vitest";
import {
  PAGE_DATA_CACHE_CONTROL,
  PAGE_DATA_NO_STORE,
  isPageDataCountCacheable,
  pageDataCacheHeaders,
  pageDataJsonResponse,
} from "@/lib/page-data-cache";
import { pageDataUpstreamErrorResponse } from "@/lib/page-data-upstream";
import { UpstreamTimeoutError } from "@/lib/upstream-fetch";

describe("page-data cache headers (45s band)", () => {
  it("sets s-maxage=45 / stale-while-revalidate on cacheable 200", () => {
    expect(PAGE_DATA_CACHE_CONTROL).toBe(
      "public, s-maxage=45, stale-while-revalidate=45",
    );
    expect(isPageDataCountCacheable(200, 241)).toBe(true);
    expect(pageDataCacheHeaders({ cacheable: true })["Cache-Control"]).toBe(
      PAGE_DATA_CACHE_CONTROL,
    );
  });

  it("never caches empty count=0 boards", () => {
    expect(isPageDataCountCacheable(200, 0)).toBe(false);
    expect(isPageDataCountCacheable(200, null)).toBe(false);
    const res = pageDataJsonResponse({
      count: 0,
      lines: [],
      oddsAsOf: null,
    });
    expect(res.status).toBe(200);
    expect(res.headers.get("Cache-Control")).toBe(PAGE_DATA_NO_STORE);
  });

  it("caches non-empty fair-lines / assemble bodies (keeps oddsAsOf, no Date.now)", async () => {
    const fair = pageDataJsonResponse({
      count: 16,
      oddsAsOf: "2026-09-03T14:00:00Z",
      lines: [{ gameId: "g1" }],
    });
    expect(fair.status).toBe(200);
    expect(fair.headers.get("Cache-Control")).toBe(PAGE_DATA_CACHE_CONTROL);
    const fairBody = (await fair.json()) as { oddsAsOf?: string };
    expect(fairBody.oddsAsOf).toBe("2026-09-03T14:00:00Z");

    const assemble = pageDataJsonResponse({
      games: 16,
      linesAsOf: "2026-09-03T14:00:00Z",
      rows: [],
    });
    expect(assemble.headers.get("Cache-Control")).toBe(PAGE_DATA_CACHE_CONTROL);
    const assembleBody = (await assemble.json()) as { linesAsOf?: string };
    expect(assembleBody.linesAsOf).toBe("2026-09-03T14:00:00Z");
  });

  it("never caches 503/504 transport errors", async () => {
    const timedOut = pageDataUpstreamErrorResponse(
      new UpstreamTimeoutError(25_000, "https://model/nfl/fair-lines"),
    );
    expect(timedOut.status).toBe(504);
    expect(timedOut.headers.get("Cache-Control")).toBe(PAGE_DATA_NO_STORE);

    const unreachable = pageDataUpstreamErrorResponse(
      new Error("Unable to reach model service."),
    );
    expect(unreachable.status).toBe(503);
    expect(unreachable.headers.get("Cache-Control")).toBe(PAGE_DATA_NO_STORE);
  });
});
