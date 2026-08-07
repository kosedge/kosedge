import { afterEach, describe, expect, it, vi } from "vitest";
import {
  fetchNflDataFreshness,
  isNflSeasonEngineDeskPath,
  NFL_DATA_FRESHNESS_TIMEOUT_MS,
  shouldShowNflDataFreshnessBanner,
} from "@/lib/nfl-data-freshness";
import { UpstreamTimeoutError } from "@/lib/upstream-fetch";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("isNflSeasonEngineDeskPath", () => {
  it("matches season-engine desks only", () => {
    expect(isNflSeasonEngineDeskPath("/pro/nfl/model")).toBe(true);
    expect(isNflSeasonEngineDeskPath("/pro/nfl/game-boxes")).toBe(true);
    expect(isNflSeasonEngineDeskPath("/pro/nfl/survivor")).toBe(true);
    expect(isNflSeasonEngineDeskPath("/pro/nfl/survivor?tab=planner")).toBe(
      true,
    );
    expect(isNflSeasonEngineDeskPath("/pro/nfl/edge-board")).toBe(false);
    expect(isNflSeasonEngineDeskPath("/pro/nfl/fair-lines")).toBe(false);
  });
});

describe("shouldShowNflDataFreshnessBanner", () => {
  it("hides ok and probe_unavailable", () => {
    expect(shouldShowNflDataFreshnessBanner({ status: "ok" })).toBe(false);
    expect(
      shouldShowNflDataFreshnessBanner({
        status: "probe_unavailable",
        blockers: ["freshness_timeout"],
      }),
    ).toBe(false);
  });

  it("hides transport-only failures", () => {
    expect(
      shouldShowNflDataFreshnessBanner({
        status: "failed",
        blockers: ["freshness_fetch_failed"],
      }),
    ).toBe(false);
    expect(
      shouldShowNflDataFreshnessBanner({
        status: "degraded",
        blockers: ["freshness_http_error"],
      }),
    ).toBe(false);
  });

  it("shows real owned-data SLO degradation", () => {
    expect(
      shouldShowNflDataFreshnessBanner({
        status: "degraded",
        in_season: true,
        blockers: ["player_props_odds:stale"],
      }),
    ).toBe(true);
    expect(
      shouldShowNflDataFreshnessBanner({
        status: "failed",
        blockers: ["injuries:stale_30h>24h"],
      }),
    ).toBe(true);
  });

  it("hides ops-only DR backup lag (not board data degradation)", () => {
    expect(
      shouldShowNflDataFreshnessBanner({
        status: "degraded",
        in_season: false,
        blockers: ["dr_backup:stale_296.3h>192.0h"],
      }),
    ).toBe(false);
    expect(
      shouldShowNflDataFreshnessBanner({
        status: "failed",
        blockers: ["dr_backup:missing_timestamp"],
      }),
    ).toBe(false);
    // Mixed board + ops still shows (board failure is real).
    expect(
      shouldShowNflDataFreshnessBanner({
        status: "degraded",
        blockers: ["dr_backup:stale_200h>192h", "injuries:stale_30h>24h"],
      }),
    ).toBe(true);
  });
});

describe("fetchNflDataFreshness", () => {
  it("caps freshness probe timeout for hang protection", () => {
    expect(NFL_DATA_FRESHNESS_TIMEOUT_MS).toBeLessThanOrEqual(3_000);
  });

  it("maps UpstreamTimeoutError to probe_unavailable (no degraded banner)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new UpstreamTimeoutError(3000, "https://example/health");
      }),
    );
    const result = await fetchNflDataFreshness();
    expect(result.status).toBe("probe_unavailable");
    expect(result.blockers).toContain("freshness_timeout");
    expect(shouldShowNflDataFreshnessBanner(result)).toBe(false);
  });

  it("keeps real degraded payload from 503 detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              detail: {
                status: "degraded",
                in_season: true,
                blockers: ["injuries:stale"],
              },
            }),
            { status: 503 },
          ),
      ),
    );
    const result = await fetchNflDataFreshness();
    expect(result.status).toBe("degraded");
    expect(result.blockers).toEqual(["injuries:stale"]);
    expect(shouldShowNflDataFreshnessBanner(result)).toBe(true);
  });
});
