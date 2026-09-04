import { afterEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fetchNflFairLines } from "@/lib/nfl-fair-lines";

const root = process.cwd();

function readApp(rel: string): string {
  return readFileSync(path.join(root, rel), "utf8");
}

describe("fetchNflFairLines persist=0 (read-only page-data)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("page-data fair-lines route opts out of odds_snapshots persist", () => {
    const fair = readApp("app/api/nfl/fair-lines/route.ts");
    expect(fair).toContain("persistOdds: false");
    expect(fair).toContain("pageDataJsonResponse");
  });

  it("sends persist=0 on the model-service URL by default", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const href = String(input);
      expect(href).toContain("/nfl/fair-lines");
      expect(href).toContain("persist=0");
      expect(href).not.toMatch(/persist=1/);
      return new Response(
        JSON.stringify({
          season: 2026,
          model_version: "test",
          odds_as_of: "2026-09-03T14:00:00Z",
          current_week: 1,
          count: 1,
          lines: [],
          window: { days_ahead: 200, include_past_days: 0 },
          diagnostics: {
            odds_feed_status: "ok",
            odds_events_seen: 1,
            market_joined_count: 0,
            bookmakers: [],
            kosedge_only: true,
            odds_persisted: {
              events_persisted: 0,
              snapshots_inserted: 0,
              history_upserted: 0,
            },
            odds_ledger_health: {
              last_odds_snapshot_captured_at: "2026-09-04T10:00:00+00:00",
              last_market_history_captured_at: "2026-09-04T09:59:00+00:00",
              history_lag_seconds: 60,
              ledger_health: "history_lagging",
              note: "ops-only: odds_persisted zeros on persist=0 ≠ dark warehouse ledger",
            },
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    const board = await fetchNflFairLines({
      season: 2026,
      daysAhead: 200,
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(board.count).toBe(1);
    expect(board.oddsAsOf).toBe("2026-09-03T14:00:00Z");
    expect(board.diagnostics.oddsPersisted).toEqual({
      eventsPersisted: 0,
      snapshotsInserted: 0,
      historyUpserted: 0,
    });
    expect(board.diagnostics.oddsLedgerHealth).toEqual({
      lastOddsSnapshotCapturedAt: "2026-09-04T10:00:00+00:00",
      lastMarketHistoryCapturedAt: "2026-09-04T09:59:00+00:00",
      historyLagSeconds: 60,
      ledgerHealth: "history_lagging",
      note: "ops-only: odds_persisted zeros on persist=0 ≠ dark warehouse ledger",
    });
  });

  it("sends persist=1 only when persistOdds is explicitly true", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const href = String(input);
      expect(href).toContain("persist=1");
      return new Response(
        JSON.stringify({
          season: 2026,
          count: 0,
          lines: [],
          diagnostics: {},
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchNflFairLines({
      season: 2026,
      persistOdds: true,
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
