import { describe, expect, it } from "vitest";
import { getTonightGames } from "@/lib/edge-board-tonight";
import { getSportDeskConfig } from "@/lib/pro-sport-desk";
import { getSportGlance } from "@/lib/sport-overview";

describe("NBA overview desk wiring", () => {
  it("getTonightGames returns an array without throwing", async () => {
    const games = await getTonightGames("nba");
    expect(Array.isArray(games)).toBe(true);
  });

  it("glance and desk link Edge Board / Fantasy / Props dark", () => {
    const glance = getSportGlance("nba");
    const hrefs = glance.map((g) => g.href);
    expect(hrefs).toContain("/edge-board/nba");
    expect(hrefs).toContain("/pro/nba/fantasy");
    expect(hrefs).toContain("/pro/nba/props");

    const desk = getSportDeskConfig("nba");
    const cardHrefs = desk.cards.map((c) => c.href);
    expect(cardHrefs).toContain("/edge-board/nba");
    expect(cardHrefs).toContain("/pro/nba/fantasy");
    expect(cardHrefs).toContain("/pro/nba/props");
  });
});
