import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import {
  slimOddsComparisonForBoard,
  type OddsComparisonRow,
} from "@/lib/odds-api";

describe("Compare Odds fat-payload fix", () => {
  it("slims unused book fields off compare rows", () => {
    const fat: OddsComparisonRow = {
      id: "g1",
      game: "NE @ SEA",
      time: "Thu 8:20 PM ET",
      commenceTime: "2026-09-10T00:20:00Z",
      spread: {
        draftkings: {
          away: "+3.0",
          home: "-3.0",
          awayJuice: "-110",
          homeJuice: "-110",
          awayPoint: 3,
          homePoint: -3,
        },
      },
      moneyline: {
        draftkings: {
          away: "+145",
          home: "-170",
          awayPrice: 145,
          homePrice: -170,
        },
      },
      total: {
        draftkings: {
          line: "43.5",
          overJuice: "-110",
          underJuice: "-110",
          point: 43.5,
        },
      },
      bestSpreadBook: "draftkings",
      bestTotalBook: "draftkings",
      bestMlAwayBook: "draftkings",
      bestMlHomeBook: "draftkings",
    };

    const slim = slimOddsComparisonForBoard([fat])[0]!;
    expect(slim).not.toHaveProperty("commenceTime");
    expect(slim.spread.draftkings).toEqual({
      away: "+3.0",
      awayJuice: "-110",
    });
    expect(slim.moneyline.draftkings).toEqual({
      away: "+145",
      home: "-170",
    });
    expect(slim.total.draftkings).toEqual({
      line: "43.5",
      overJuice: "-110",
    });
    expect(JSON.stringify(slim)).not.toContain("awayPoint");
    expect(JSON.stringify(slim)).not.toContain("underJuice");
    expect(JSON.stringify(slim)).not.toContain("homeJuice");
  });

  it("SSR page shells the board and does not inline compare rows", () => {
    const page = readFileSync(
      path.join(process.cwd(), "app/odds/[sport]/page.tsx"),
      "utf8",
    );
    const board = readFileSync(
      path.join(process.cwd(), "components/OddsCompareBoard.tsx"),
      "utf8",
    );

    expect(page).toContain("OddsCompareBoard");
    expect(page).not.toContain("getOddsData");
    expect(page).not.toMatch(/fetch\s*\(/);
    expect(page).not.toMatch(/\brows\.map\b/);
    expect(page).not.toContain("OddsComparisonRow");

    expect(board).toContain('"use client"');
    expect(board).toContain("/api/odds/${sportKey}/compare");
    expect(board).toContain('data-testid="odds-compare-board"');
    expect(board).toContain('data-testid="odds-compare-table"');
    expect(board).toContain("compare-odds-asof");
    expect(board).toContain("Odds by book");
  });

  it("compare API route serves slim board payload (cache v7)", () => {
    const route = readFileSync(
      path.join(process.cwd(), "app/api/odds/[sport]/compare/route.ts"),
      "utf8",
    );
    expect(route).toContain("slimOddsComparisonForBoard");
    expect(route).toContain("odds:${sport}:compare:v7");
  });
});
