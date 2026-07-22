import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ALLOWED_BOOKS,
  fetchEdgeBoard,
  fetchOddsComparison,
  pickBestSpreadEntry,
  pickBestTotalEntry,
} from "@/lib/odds-api";

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
  it("requests NFL odds across all 9 configured books by default", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse([]));

    await fetchEdgeBoard("nfl", "fake-key");

    const url = String(fetchSpy.mock.calls[0]?.[0] ?? "");
    expect(url).toContain(`bookmakers=${encodeURIComponent(ALLOWED_BOOKS.join(","))}`);
    expect(ALLOWED_BOOKS).toHaveLength(9);
  });

  it("picks Best Line / Best O/U across books with juice tiebreak", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse([
        {
          id: "game-best",
          sport_key: "americanfootball_nfl",
          commence_time: "2026-09-10T00:20:00Z",
          away_team: "New England Patriots",
          home_team: "Seattle Seahawks",
          bookmakers: [
            {
              key: "draftkings",
              title: "DraftKings",
              markets: [
                {
                  key: "spreads",
                  outcomes: [
                    { name: "New England Patriots", point: 3.0, price: -110 },
                    { name: "Seattle Seahawks", point: -3.0, price: -110 },
                  ],
                },
                {
                  key: "totals",
                  outcomes: [
                    { name: "Over", point: 43.5, price: -110 },
                    { name: "Under", point: 43.5, price: -110 },
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
                    { name: "New England Patriots", point: 3.5, price: -115 },
                    { name: "Seattle Seahawks", point: -3.5, price: -105 },
                  ],
                },
                {
                  key: "totals",
                  outcomes: [
                    { name: "Over", point: 44.0, price: -108 },
                    { name: "Under", point: 44.0, price: -112 },
                  ],
                },
              ],
            },
            {
              key: "circa",
              title: "Circa",
              markets: [
                {
                  key: "spreads",
                  outcomes: [
                    { name: "New England Patriots", point: 3.5, price: -105 },
                    { name: "Seattle Seahawks", point: -3.5, price: -115 },
                  ],
                },
                {
                  key: "totals",
                  outcomes: [
                    { name: "Over", point: 44.0, price: -102 },
                    { name: "Under", point: 44.0, price: -118 },
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
    const total = rows.find((row) => row.market === "Total");

    expect(spread?.open).toBe("+3");
    expect(spread?.bookKey).toBe("circa");
    expect(spread?.best).toBe("+3.5");
    expect(spread?.bestJuice).toBe("-105");
    expect(total?.bookKey).toBe("circa");
    expect(total?.best).toBe("44");
    expect(total?.bestJuice).toBe("-102");
  });

  it("pickBestSpreadEntry prefers higher away point then better juice", () => {
    const best = pickBestSpreadEntry([
      { book: "draftkings", line: "+3", point: 3, canonical: true, juiceAway: "-110" },
      { book: "fanduel", line: "+3.5", point: 3.5, canonical: true, juiceAway: "-115" },
      { book: "circa", line: "+3.5", point: 3.5, canonical: true, juiceAway: "-105" },
    ]);
    expect(best?.book).toBe("circa");
  });

  it("pickBestTotalEntry prefers higher total then better Over juice", () => {
    const best = pickBestTotalEntry([
      { book: "draftkings", line: "43.5", point: 43.5, juiceOver: "-110" },
      { book: "fanduel", line: "44", point: 44, juiceOver: "-108" },
      { book: "circa", line: "44", point: 44, juiceOver: "-102" },
    ]);
    expect(best?.book).toBe("circa");
  });

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
    expect(rows[0]?.spread?.draftkings).toMatchObject({
      away: "ALT +5.5",
      home: "ALT -5.5",
    });
  });
});
