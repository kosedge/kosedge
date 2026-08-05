import { describe, expect, it } from "vitest";
import {
  matchAdpToDeskRows,
  normalizePlayerName,
  parseNameParts,
} from "@/lib/fantasy/adp-match";
import type { FantasyProsAdpEntry } from "@/lib/fantasy/adp-fantasypros";

function fp(
  partial: Partial<FantasyProsAdpEntry> & {
    playerName: string;
    team: string;
    position: string;
    adp: number;
  },
): FantasyProsAdpEntry {
  return {
    playerId: partial.playerId ?? partial.playerName,
    shortName: partial.shortName ?? null,
    ecr: partial.ecr ?? null,
    sportsdataId: partial.sportsdataId ?? null,
    ...partial,
  };
}

describe("adp name matching", () => {
  it("parses abbreviated board names", () => {
    const parts = parseNameParts("J.Taylor");
    expect(parts.firstInitial).toBe("j");
    expect(parts.lastName).toBe("taylor");
    expect(normalizePlayerName("A.St. Brown")).toContain("st");
  });

  it("matches initial+last+team+pos", () => {
    const { byPlayerId, matched } = matchAdpToDeskRows(
      [
        {
          playerId: "ind:j.taylor",
          playerName: "J.Taylor",
          team: "IND",
          position: "RB",
        },
      ],
      [
        fp({
          playerName: "Jonathan Taylor",
          shortName: "J. Taylor",
          team: "IND",
          position: "RB",
          adp: 8.3,
        }),
      ],
    );
    expect(matched).toBe(1);
    expect(byPlayerId.get("ind:j.taylor")?.adp).toBe(8.3);
    expect(byPlayerId.get("ind:j.taylor")?.matchKind).toBe("initial_last");
  });

  it("matches sportsdata id first", () => {
    const { byPlayerId } = matchAdpToDeskRows(
      [
        {
          playerId: "x",
          playerUid: "sd-1",
          playerName: "Wrong Name",
          team: "DET",
          position: "RB",
        },
      ],
      [
        fp({
          playerName: "Jahmyr Gibbs",
          team: "DET",
          position: "RB",
          adp: 1.3,
          sportsdataId: "sd-1",
        }),
      ],
    );
    expect(byPlayerId.get("x")?.matchKind).toBe("sportsdata_id");
    expect(byPlayerId.get("x")?.adp).toBe(1.3);
  });

  it("does not invent a match when last name is ambiguous", () => {
    const { matched } = matchAdpToDeskRows(
      [
        {
          playerId: "a",
          playerName: "J.Williams",
          team: "DEN",
          position: "RB",
        },
      ],
      [
        fp({
          playerName: "Javonte Williams",
          team: "DAL",
          position: "RB",
          adp: 40,
        }),
        fp({
          playerName: "Jamaal Williams",
          team: "NO",
          position: "RB",
          adp: 120,
        }),
      ],
    );
    expect(matched).toBe(0);
  });

  it("accepts LAR/LA team aliases", () => {
    const { matched } = matchAdpToDeskRows(
      [
        {
          playerId: "puka",
          playerName: "Puka Nacua",
          team: "LAR",
          position: "WR",
        },
      ],
      [
        fp({
          playerName: "Puka Nacua",
          team: "LA",
          position: "WR",
          adp: 15,
        }),
      ],
    );
    expect(matched).toBe(1);
  });

  it("matches Jr./Sr. market names to abbreviated board names", () => {
    const { byPlayerId } = matchAdpToDeskRows(
      [
        {
          playerId: "penix",
          playerName: "M.Penix",
          team: "ATL",
          position: "QB",
        },
        {
          playerId: "btj",
          playerName: "B.Thomas",
          team: "JAX",
          position: "WR",
        },
      ],
      [
        fp({
          playerName: "Michael Penix Jr.",
          team: "ATL",
          position: "QB",
          adp: 239.5,
        }),
        fp({
          playerName: "Brian Thomas Jr.",
          team: "JAC",
          position: "WR",
          adp: 72.67,
        }),
      ],
    );
    expect(byPlayerId.get("penix")?.adp).toBe(239.5);
    expect(byPlayerId.get("btj")?.adp).toBe(72.67);
  });
});
