import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/kei-lines", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/kei-lines")>();
  return {
    ...actual,
    getKeiLines: vi.fn(),
  };
});

import { getKeiLines } from "@/lib/kei-lines";
import {
  ensureAllKeiGamesOnBoard,
  mergeKeiIntoEdgeBoardRows,
} from "@/lib/edge-board-kei";

type Row = {
  id: string;
  game: string;
  market: "Spread" | "Total";
  commenceTime?: string;
  kei?: string;
};

describe("mergeKeiIntoEdgeBoardRows", () => {
  it("adds KEI spread and total to matching rows", () => {
    vi.mocked(getKeiLines).mockReturnValue([
      {
        awayTeam: "Duke",
        homeTeam: "North Carolina",
        commenceTime: "2026-04-07T23:00:00Z",
        projSpreadHome: -3.5,
        projTotal: 149.5,
      },
    ]);

    const rows: Row[] = [
      {
        id: "1-spread",
        game: "Duke @ North Carolina",
        market: "Spread",
        commenceTime: "2026-04-07T23:00:00Z",
      },
      {
        id: "1-total",
        game: "Duke @ North Carolina",
        market: "Total",
        commenceTime: "2026-04-07T23:00:00Z",
      },
    ];

    const out = mergeKeiIntoEdgeBoardRows(rows as any, "ncaam");
    expect(out[0].kei).toBe("-3.5");
    expect(out[1].kei).toBe("149.5");
  });

  it("matches by team names when commenceTime is missing", () => {
    vi.mocked(getKeiLines).mockReturnValue([
      {
        awayTeam: "Houston",
        homeTeam: "Iowa State",
        projSpreadHome: 1.0,
        projTotal: 133.0,
      },
    ]);

    const rows: Row[] = [
      {
        id: "2-spread",
        game: "Houston @ Iowa State",
        market: "Spread",
      },
    ];

    const out = mergeKeiIntoEdgeBoardRows(rows as any, "ncaam");
    expect(out[0].kei).toBe("+1");
  });

  it("does not mutate rows when no KEI games exist", () => {
    vi.mocked(getKeiLines).mockReturnValue([]);
    const rows: Row[] = [
      {
        id: "3-spread",
        game: "Team A @ Team B",
        market: "Spread",
      },
    ];
    const out = mergeKeiIntoEdgeBoardRows(rows as any, "ncaam");
    expect(out[0].kei).toBeUndefined();
  });

  it("seeds missing KEI games onto the board so PASS games still appear", () => {
    const seeded = ensureAllKeiGamesOnBoard(
      [
        {
          id: "odds-spread",
          game: "New England Patriots @ Seattle Seahawks",
          market: "Spread",
          best: "+3.5",
          book: "DraftKings",
          bookKey: "draftkings",
        } as any,
      ],
      "nfl",
      [
        {
          awayTeam: "New England Patriots",
          homeTeam: "Seattle Seahawks",
          projSpreadHome: -3.5,
          projTotal: 41.3,
        },
        {
          awayTeam: "Green Bay Packers",
          homeTeam: "Minnesota Vikings",
          projSpreadHome: 1.5,
          projTotal: 43.5,
          commenceTime: "2026-09-13T17:00:00Z",
        },
      ],
    );

    const games = new Set(seeded.map((r) => r.game));
    expect(games.has("New England Patriots @ Seattle Seahawks")).toBe(true);
    expect(games.has("Green Bay Packers @ Minnesota Vikings")).toBe(true);
    expect(seeded.filter((r) => r.game?.includes("Green Bay")).length).toBe(2);
  });

  it("seeds MLB Moneyline + Total and merges fair ML + win prob", () => {
    const seeded = ensureAllKeiGamesOnBoard(
      [],
      "mlb",
      [
        {
          awayTeam: "New York Yankees",
          homeTeam: "Chicago Cubs",
          projSpreadHome: -1.5,
          projTotal: 9.0,
          projHomeMl: -120,
          projAwayMl: 100,
          homeWinProb: 0.55,
        },
      ],
    );
    expect(seeded.map((r) => r.market).sort()).toEqual([
      "Moneyline",
      "Total",
    ]);

    const merged = mergeKeiIntoEdgeBoardRows(seeded as any, "mlb", [
      {
        awayTeam: "New York Yankees",
        homeTeam: "Chicago Cubs",
        projSpreadHome: -1.5,
        projTotal: 9.0,
        projHomeMl: -120,
        projAwayMl: 100,
        homeWinProb: 0.55,
      },
    ]);
    const ml = merged.find((r) => r.market === "Moneyline") as any;
    const total = merged.find((r) => r.market === "Total") as any;
    expect(ml?.kei).toBe("-120");
    expect(ml?.keiAway).toBe("+100");
    expect(ml?.homeWinProb).toBe(0.55);
    expect(total?.kei).toBe("9");
  });

  it("matches NFL Odds full names to KEINFL abbr or full-name exports", () => {
    vi.mocked(getKeiLines).mockReturnValue([
      {
        awayTeam: "NE",
        homeTeam: "SEA",
        awayAbbr: "NE",
        homeAbbr: "SEA",
        projSpreadHome: -3.5,
        projTotal: 41.3,
      },
    ]);

    const rows: Row[] = [
      {
        id: "nfl-spread",
        game: "New England Patriots @ Seattle Seahawks",
        market: "Spread",
      },
      {
        id: "nfl-total",
        game: "New England Patriots @ Seattle Seahawks",
        market: "Total",
      },
    ];

    const out = mergeKeiIntoEdgeBoardRows(rows as any, "nfl");
    expect(out[0].kei).toBe("-3.5");
    expect(out[1].kei).toBe("41.3");
  });

  it("merges handicap into kei and attaches model fields without using them for kei", () => {
    const rows: Row[] = [
      {
        id: "mlb-ml",
        game: "Away @ Home",
        market: "Moneyline" as any,
      },
      {
        id: "mlb-total",
        game: "Away @ Home",
        market: "Total",
      },
    ];
    const out = mergeKeiIntoEdgeBoardRows(rows as any, "mlb", [
      {
        awayTeam: "Away",
        homeTeam: "Home",
        projSpreadHome: -1.5,
        projTotal: 9.0,
        projHomeMl: -140,
        projAwayMl: 120,
        homeWinProb: 0.6,
        handicapHomeMl: -140,
        handicapAwayMl: 120,
        handicapHomeWinProb: 0.6,
        handicapTotal: 9.0,
        modelHomeMl: -110,
        modelAwayMl: -110,
        modelHomeWinProb: 0.52,
        modelTotal: 8.2,
      },
    ]);
    const ml = out.find((r) => r.market === "Moneyline") as any;
    const total = out.find((r) => r.market === "Total") as any;
    expect(ml?.kei).toBe("-140");
    expect(ml?.keiAway).toBe("+120");
    expect(ml?.homeWinProb).toBe(0.6);
    expect(ml?.modelKei).toBe("-110");
    expect(ml?.modelHomeWinProb).toBe(0.52);
    expect(total?.kei).toBe("9");
    expect(total?.modelKei).toBe("8.2");
  });

  it("identity fallback: handicap missing uses model for kei", () => {
    const rows: Row[] = [
      {
        id: "s1",
        game: "A @ B",
        market: "Spread",
      },
    ];
    const out = mergeKeiIntoEdgeBoardRows(rows as any, "ncaam", [
      {
        awayTeam: "A",
        homeTeam: "B",
        projSpreadHome: null,
        projTotal: null,
        modelSpreadHome: -4.5,
        modelTotal: 140,
      },
    ]);
    expect(out[0]?.kei).toBe("-4.5");
  });
});
