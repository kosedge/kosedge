import { describe, expect, it } from "vitest";
import {
  isHighConfidenceAdp,
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

describe("adp name matching polish", () => {
  it("parses abbreviated board names and suffixes", () => {
    const parts = parseNameParts("J.Taylor");
    expect(parts.firstInitial).toBe("j");
    expect(parts.lastName).toBe("taylor");
    expect(parseNameParts("Odell Beckham Jr.").coreKey).toBe("odell beckham");
    expect(parseNameParts("Pierre Strong Jr.").coreKey).toBe("pierre strong");
    expect(normalizePlayerName("A.St. Brown")).toContain("st");
  });

  it("matches initial+last+team+pos as high confidence", () => {
    const { byPlayerId, matchedHigh } = matchAdpToDeskRows(
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
    expect(matchedHigh).toBe(1);
    expect(byPlayerId.get("ind:j.taylor")?.confidence).toBe("high");
    expect(byPlayerId.get("ind:j.taylor")?.adp).toBe(8.3);
    expect(["short_name", "initial_last"]).toContain(
      byPlayerId.get("ind:j.taylor")?.matchKind,
    );
  });

  it("matches Jr. market names and JAX/JAC aliases", () => {
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
        {
          playerId: "strong",
          playerName: "Pierre Strong",
          team: "GB",
          position: "RB",
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
          shortName: "B. Thomas Jr.",
          team: "JAC",
          position: "WR",
          adp: 72.67,
        }),
        fp({
          playerName: "Pierre Strong Jr.",
          shortName: "P. Strong Jr.",
          team: "GB",
          position: "RB",
          adp: 366,
        }),
      ],
    );
    expect(byPlayerId.get("penix")?.adp).toBe(239.5);
    expect(byPlayerId.get("btj")?.adp).toBe(72.67);
    expect(byPlayerId.get("strong")?.matchKind).toMatch(/core_name|initial_last/);
    expect(isHighConfidenceAdp(byPlayerId.get("strong"))).toBe(true);
  });

  it("matches roster moves via unique initial+last+pos", () => {
    const { byPlayerId } = matchAdpToDeskRows(
      [
        {
          playerId: "thielen",
          playerName: "A.Thielen",
          team: "MIN",
          position: "WR",
        },
      ],
      [
        fp({
          playerName: "Adam Thielen",
          shortName: "A. Thielen",
          team: "CAR",
          position: "WR",
          adp: 190,
        }),
      ],
    );
    expect(byPlayerId.get("thielen")?.adp).toBe(190);
    expect(byPlayerId.get("thielen")?.confidence).toBe("high");
    expect(["short_name_pos", "initial_last_pos"]).toContain(
      byPlayerId.get("thielen")?.matchKind,
    );
  });

  it("uses cross-format secondary pool without inventing weak primary hits", () => {
    const { byPlayerId, matchedHigh, matchedCrossFormat, unmatchedRows } =
      matchAdpToDeskRows(
        [
          {
            playerId: "ewers",
            playerName: "Q.Ewers",
            team: "MIA",
            position: "QB",
            rankOverall: 54,
          },
          {
            playerId: "ghost",
            playerName: "Z.Knight",
            team: "ARI",
            position: "RB",
            rankOverall: 170,
          },
        ],
        [
          fp({
            playerName: "Jahmyr Gibbs",
            team: "DET",
            position: "RB",
            adp: 1.3,
          }),
        ],
        {
          secondaryPools: [
            {
              scoringProfile: "ppr",
              players: [
                fp({
                  playerName: "Quinn Ewers",
                  shortName: "Q. Ewers",
                  team: "MIA",
                  position: "QB",
                  adp: 311,
                }),
              ],
            },
          ],
        },
      );
    expect(matchedHigh).toBe(0);
    expect(matchedCrossFormat).toBe(1);
    expect(byPlayerId.get("ewers")?.confidence).toBe("cross_format");
    expect(byPlayerId.get("ewers")?.adpScoringProfile).toBe("ppr");
    expect(unmatchedRows.map((r) => r.playerName)).toContain("Z.Knight");
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
    const { matchedHigh } = matchAdpToDeskRows(
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
    expect(matchedHigh).toBe(1);
  });
});
