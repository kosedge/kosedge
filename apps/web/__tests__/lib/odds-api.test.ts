import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchEdgeBoard, fetchOddsComparison } from "@/lib/odds-api";

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

describe("odds-api MLB run line guardrails", () => {
  it("prefers canonical MLB run line over alternate values", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse([
        {
          id: "game-1",
          sport_key: "baseball_mlb",
          commence_time: "2026-07-01T23:00:00Z",
          away_team: "New York Mets",
          home_team: "Toronto Blue Jays",
          bookmakers: [
            {
              key: "draftkings",
              title: "DraftKings",
              markets: [
                {
                  key: "spreads",
                  outcomes: [
                    { name: "New York Mets", point: 5.5, price: -110 },
                    { name: "Toronto Blue Jays", point: -5.5, price: -110 },
                  ],
                },
              ],
            },
            {
              key: "fanduel",
              title: "FanDuel",
              markets: [
                {
                  key: "spreads",
                  outcomes: [
                    { name: "New York Mets", point: 1.5, price: -120 },
                    { name: "Toronto Blue Jays", point: -1.5, price: 100 },
                  ],
                },
              ],
            },
          ],
        },
      ]),
    );

    const rows = await fetchEdgeBoard("mlb", "fake-key");
    const spread = rows.find((row) => row.market === "Spread");

    expect(spread?.open).toBe("+1.5");
    expect(spread?.best).toBe("+1.5");
  });

  it("tags MLB alternate run lines when no canonical line exists", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse([
        {
          id: "game-2",
          sport_key: "baseball_mlb",
          commence_time: "2026-07-01T23:00:00Z",
          away_team: "New York Mets",
          home_team: "Toronto Blue Jays",
          bookmakers: [
            {
              key: "draftkings",
              title: "DraftKings",
              markets: [
                {
                  key: "spreads",
                  outcomes: [
                    { name: "New York Mets", point: 5.5, price: -110 },
                    { name: "Toronto Blue Jays", point: -5.5, price: -110 },
                  ],
                },
              ],
            },
          ],
        },
      ]),
    );

    const rows = await fetchEdgeBoard("mlb", "fake-key");
    const spread = rows.find((row) => row.market === "Spread");

    expect(spread?.open).toBe("ALT +5.5");
    expect(spread?.best).toBe("ALT +5.5");
  });

  it("keeps non-MLB spreads unchanged", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse([
        {
          id: "game-3",
          sport_key: "americanfootball_nfl",
          commence_time: "2026-09-01T23:00:00Z",
          away_team: "Team A",
          home_team: "Team B",
          bookmakers: [
            {
              key: "draftkings",
              title: "DraftKings",
              markets: [
                {
                  key: "spreads",
                  outcomes: [
                    { name: "Team A", point: 5.5, price: -110 },
                    { name: "Team B", point: -5.5, price: -110 },
                  ],
                },
              ],
            },
          ],
        },
      ]),
    );

    const rows = await fetchEdgeBoard("nfl", "fake-key");
    const spread = rows.find((row) => row.market === "Spread");

    expect(spread?.best).toBe("+5.5");
  });

  it("tags alternate MLB spreads in comparison rows", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse([
        {
          id: "game-4",
          sport_key: "baseball_mlb",
          commence_time: "2026-07-01T23:00:00Z",
          away_team: "New York Mets",
          home_team: "Toronto Blue Jays",
          bookmakers: [
            {
              key: "draftkings",
              title: "DraftKings",
              markets: [
                {
                  key: "spreads",
                  outcomes: [
                    { name: "New York Mets", point: 5.5, price: -110 },
                    { name: "Toronto Blue Jays", point: -5.5, price: -110 },
                  ],
                },
              ],
            },
          ],
        },
      ]),
    );

    const rows = await fetchOddsComparison("mlb", "fake-key");
    expect(rows[0]?.spread?.draftkings).toEqual({
      away: "ALT +5.5",
      home: "ALT -5.5",
    });
  });
});
