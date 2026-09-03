import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import { resolveEdgeBoardBoardLinesAsOf } from "@/lib/nfl-edge-board-from-fair-lines";
import { marketAsOfHeaderSuffix } from "@/lib/market-asof-stamp";
import { fetchEdgeBoard } from "@/lib/odds-api";

function jsonResponse(body: unknown) {
  return {
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as Response;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("CFB Edge Board market as-of honesty", () => {
  it("assemble resolves linesAsOf from rows (not hardcoded null)", () => {
    const assemble = readFileSync(
      path.join(
        process.cwd(),
        "app/api/edge-board/[sport]/assemble/route.ts",
      ),
      "utf8",
    );
    expect(assemble).toContain('sport === "cfb"');
    expect(assemble).toContain("resolveEdgeBoardBoardLinesAsOf(rows)");
    // CFB block must not hardcode null (other sports may still).
    const cfbBlock = assemble.slice(
      assemble.indexOf('if (sport === "cfb")'),
      assemble.indexOf("const rows = await loadAssembledEdgeBoardRows(sport"),
    );
    expect(cfbBlock).toContain("resolveEdgeBoardBoardLinesAsOf(rows)");
    expect(cfbBlock).not.toMatch(/linesAsOf:\s*null/);
  });

  it("client uses NFL-style as-of for CFB — never bare · ET", () => {
    const client = readFileSync(
      path.join(process.cwd(), "components/EdgeBoardSportClient.tsx"),
      "utf8",
    );
    expect(client).toContain('sportKey === "nfl" || sportKey === "cfb"');
    expect(client).toContain("marketAsOfHeaderSuffix");
    expect(client).toContain("usesMarketAsOf");
    expect(client).toContain('data-testid="edge-board-asof"');
    // Bare ET only for sports without market as-of wiring.
    expect(client).toContain("usesMarketAsOf ? <> · {headerAsOf}</> : <> · ET</>");
  });

  it("blank board as-of → unavailable copy (no empty · ET)", () => {
    expect(marketAsOfHeaderSuffix({ asOf: null, kind: "lines" })).toBe(
      "as-of unavailable",
    );
    expect(resolveEdgeBoardBoardLinesAsOf([])).toBeNull();
    expect(
      resolveEdgeBoardBoardLinesAsOf([{ game: "A @ B" }], null),
    ).toBeNull();
  });

  it("fetchEdgeBoard stamps CFB rows with book last_update as linesAsOf", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse([
        {
          id: "cfb-1",
          sport_key: "americanfootball_ncaaf",
          commence_time: "2026-09-05T16:00:00Z",
          away_team: "Ball State Cardinals",
          home_team: "Ohio State Buckeyes",
          bookmakers: [
            {
              key: "draftkings",
              title: "DraftKings",
              last_update: "2026-09-03T18:30:00Z",
              markets: [
                {
                  key: "spreads",
                  last_update: "2026-09-03T18:30:00Z",
                  outcomes: [
                    { name: "Ball State Cardinals", point: 50.5, price: -110 },
                    { name: "Ohio State Buckeyes", point: -50.5, price: -110 },
                  ],
                },
                {
                  key: "totals",
                  last_update: "2026-09-03T18:45:00Z",
                  outcomes: [
                    { name: "Over", point: 55.5, price: -110 },
                    { name: "Under", point: 55.5, price: -110 },
                  ],
                },
              ],
            },
          ],
        },
      ]),
    );

    const rows = await fetchEdgeBoard("cfb", "fake-key");
    expect(rows.length).toBeGreaterThanOrEqual(2);
    const spread = rows.find((r) => r.market === "Spread") as {
      linesAsOf?: string;
    };
    const total = rows.find((r) => r.market === "Total") as {
      linesAsOf?: string;
    };
    expect(spread?.linesAsOf).toBe("2026-09-03T18:30:00.000Z");
    expect(total?.linesAsOf).toBe("2026-09-03T18:45:00.000Z");

    const boardAsOf = resolveEdgeBoardBoardLinesAsOf(
      rows as Array<{ linesAsOf?: string }>,
    );
    expect(boardAsOf).toBe("2026-09-03T18:45:00.000Z");
    expect(
      marketAsOfHeaderSuffix({ asOf: boardAsOf, kind: "lines" }),
    ).toMatch(/^as of /);
    expect(
      marketAsOfHeaderSuffix({ asOf: boardAsOf, kind: "lines" }),
    ).not.toBe("as-of unavailable");
  });

  it("missing book last_update → no invented linesAsOf", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse([
        {
          id: "cfb-2",
          sport_key: "americanfootball_ncaaf",
          commence_time: "2026-09-05T16:00:00Z",
          away_team: "Team A",
          home_team: "Team B",
          bookmakers: [
            {
              key: "fanduel",
              title: "FanDuel",
              markets: [
                {
                  key: "spreads",
                  outcomes: [
                    { name: "Team A", point: 3.5, price: -110 },
                    { name: "Team B", point: -3.5, price: -110 },
                  ],
                },
                {
                  key: "totals",
                  outcomes: [
                    { name: "Over", point: 48.5, price: -110 },
                    { name: "Under", point: 48.5, price: -110 },
                  ],
                },
              ],
            },
          ],
        },
      ]),
    );

    const rows = await fetchEdgeBoard("cfb", "fake-key");
    for (const r of rows) {
      expect((r as { linesAsOf?: string }).linesAsOf).toBeUndefined();
    }
    expect(resolveEdgeBoardBoardLinesAsOf(rows as Array<{ linesAsOf?: string }>)).toBeNull();
  });
});
