import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ALLOWED_BOOKS,
  fetchEdgeBoard,
  fetchOddsComparison,
  pickBestMoneylineEntry,
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

describe("odds-api edge board markets", () => {
  it("requests NFL odds across all 9 configured books by default", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse([]));

    await fetchEdgeBoard("nfl", "fake-key");

    const url = String(fetchSpy.mock.calls[0]?.[0] ?? "");
    expect(url).toContain(
      `bookmakers=${encodeURIComponent(ALLOWED_BOOKS.join(","))}`,
    );
    expect(url).toContain("markets=spreads,totals");
    expect(ALLOWED_BOOKS).toHaveLength(9);
  });

  it("requests MLB h2h+totals (moneyline board, not run line)", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse([]));

    await fetchEdgeBoard("mlb", "fake-key");

    const url = String(fetchSpy.mock.calls[0]?.[0] ?? "");
    expect(url).toContain("markets=h2h,totals");
    expect(url).not.toContain("markets=spreads");
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
      {
        book: "draftkings",
        line: "+3",
        point: 3,
        canonical: true,
        juiceAway: "-110",
      },
      {
        book: "fanduel",
        line: "+3.5",
        point: 3.5,
        canonical: true,
        juiceAway: "-115",
      },
      {
        book: "circa",
        line: "+3.5",
        point: 3.5,
        canonical: true,
        juiceAway: "-105",
      },
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

  it("emits Moneyline rows for MLB and picks best away American", async () => {
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
                  key: "h2h",
                  outcomes: [
                    { name: "New York Mets", price: -105 },
                    { name: "Toronto Blue Jays", price: -115 },
                  ],
                },
                {
                  key: "totals",
                  outcomes: [
                    { name: "Over", point: 8.5, price: -110 },
                    { name: "Under", point: 8.5, price: -110 },
                  ],
                },
              ],
            },
            {
              key: "fanduel",
              title: "FanDuel",
              markets: [
                {
                  key: "h2h",
                  outcomes: [
                    { name: "New York Mets", price: 110 },
                    { name: "Toronto Blue Jays", price: -130 },
                  ],
                },
              ],
            },
          ],
        },
      ]),
    );

    const rows = await fetchEdgeBoard("mlb", "fake-key");
    const ml = rows.find((row) => row.market === "Moneyline");
    const total = rows.find((row) => row.market === "Total");

    expect(ml?.open).toBe("-105");
    expect(ml?.best).toBe("+110");
    expect(ml?.bookKey).toBe("fanduel");
    expect(ml?.bestJuiceHome).toBe("-130");
    expect(total?.best).toBe("8.5");
    expect(rows.some((row) => row.market === "Spread")).toBe(false);
  });

  it("pickBestMoneylineEntry prefers higher away American", () => {
    const best = pickBestMoneylineEntry([
      {
        book: "draftkings",
        away: "-110",
        home: "-110",
        awayPrice: -110,
        homePrice: -110,
      },
      {
        book: "fanduel",
        away: "+105",
        home: "-125",
        awayPrice: 105,
        homePrice: -125,
      },
    ]);
    expect(best?.book).toBe("fanduel");
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

    const result = await fetchOddsComparison("mlb", "fake-key");
    expect(result.rows[0]?.spread?.draftkings).toMatchObject({
      away: "ALT +5.5",
      home: "ALT -5.5",
    });
    // No last_update on bookmakers → honest null (do not invent fetch time).
    expect(result.asOf).toBeNull();
    expect(result.bookAsOf).toEqual([
      { key: "draftkings", label: "DraftKings", asOf: null },
    ]);
  });

  it("plumbs book last_update into Compare Odds asOf (no fabricated clock)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse([
        {
          id: "game-asof",
          sport_key: "americanfootball_nfl",
          commence_time: "2026-09-10T00:20:00Z",
          away_team: "New England Patriots",
          home_team: "Seattle Seahawks",
          bookmakers: [
            {
              key: "draftkings",
              title: "DraftKings",
              last_update: "2026-09-02T16:00:00Z",
              markets: [
                {
                  key: "spreads",
                  last_update: "2026-09-02T16:05:00Z",
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
                {
                  key: "h2h",
                  outcomes: [
                    { name: "New England Patriots", price: 150 },
                    { name: "Seattle Seahawks", price: -175 },
                  ],
                },
              ],
            },
            {
              key: "fanduel",
              title: "FanDuel",
              last_update: "2026-09-02T17:00:00Z",
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
                {
                  key: "h2h",
                  outcomes: [
                    { name: "New England Patriots", price: 145 },
                    { name: "Seattle Seahawks", price: -170 },
                  ],
                },
              ],
            },
          ],
        },
      ]),
    );

    const result = await fetchOddsComparison("nfl", "fake-key");
    expect(result.rows).toHaveLength(1);
    expect(result.asOf).toBe("2026-09-02T17:00:00Z");
    expect(result.bookAsOf.find((b) => b.key === "draftkings")?.asOf).toBe(
      "2026-09-02T16:05:00Z",
    );
    expect(result.bookAsOf.find((b) => b.key === "fanduel")?.asOf).toBe(
      "2026-09-02T17:00:00Z",
    );
  });
});
