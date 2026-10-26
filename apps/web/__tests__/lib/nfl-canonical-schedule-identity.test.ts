import { describe, expect, it } from "vitest";
import {
  NFL_CANONICAL_SCHEDULE_SEASON,
  NFL_REG_GAME_COUNT,
  lookupCanonicalNflGame,
} from "@/lib/nfl-canonical-schedule";

describe("canonical NFL game identity", () => {
  it("CTRL-keeps the 2026 REG pack constants", () => {
    expect(NFL_CANONICAL_SCHEDULE_SEASON).toBe(2026);
    expect(NFL_REG_GAME_COUNT).toBe(272);
  });

  it("T04 matches season, ordered home/away, and REG when that type is specified", () => {
    const game = lookupCanonicalNflGame({
      season: 2026,
      week: 1,
      awayAbbr: "NE",
      homeAbbr: "SEA",
      seasonType: "REG",
    });
    expect(game).toMatchObject({
      game_id: "2026-W01-NE@SEA",
      season: 2026,
      week: 1,
      game_type: "REG",
      away_team_id: "NE",
      home_team_id: "SEA",
    });
  });

  it("CTRL-matches a game id only when the supplied season and REG type agree", () => {
    expect(
      lookupCanonicalNflGame({
        gameId: "2026-W01-SF@LAR",
        season: 2026,
        seasonType: "REG",
      }),
    ).toMatchObject({
      game_id: "2026-W01-SF@LAR",
      season: 2026,
      game_type: "REG",
      away_team_id: "SF",
      home_team_id: "LAR",
      international: true,
    });
  });

  it("T04b does not let a null season establish identity", () => {
    expect(
      lookupCanonicalNflGame({ gameId: "2026-W01-NE@SEA", season: null }),
    ).toBeNull();
    expect(lookupCanonicalNflGame({ gameId: "2026-W01-NE@SEA" })).toBeNull();
    expect(
      lookupCanonicalNflGame({
        gameId: "2026-W01-SF@LAR",
        season: null,
        seasonType: "REG",
      }),
    ).toBeNull();
    expect(
      lookupCanonicalNflGame({
        week: 1,
        awayAbbr: "NE",
        homeAbbr: "SEA",
        seasonType: "REG",
      }),
    ).toBeNull();
  });

  it("CTRL-canonicalizes LA to LAR without swapping orientation", () => {
    expect(
      lookupCanonicalNflGame({
        season: 2026,
        week: 1,
        awayAbbr: "SF",
        homeAbbr: "LA",
        seasonType: "REG",
      })?.game_id,
    ).toBe("2026-W01-SF@LAR");
  });

  it("T13-CAN covers null season on week lookup, null and foreign seasons on ID lookup, and the valid-season control", () => {
    expect(
      lookupCanonicalNflGame({
        season: null,
        week: 1,
        awayAbbr: "NE",
        homeAbbr: "SEA",
        seasonType: "REG",
      }),
    ).toBeNull();
    expect(
      lookupCanonicalNflGame({
        gameId: "2026-W01-NE@SEA",
        season: null,
      }),
    ).toBeNull();
    expect(
      lookupCanonicalNflGame({
        gameId: "2026-W01-NE@SEA",
        season: 2025,
      }),
    ).toBeNull();
    expect(
      lookupCanonicalNflGame({
        gameId: "2026-W01-NE@SEA",
        season: 2024,
        seasonType: "REG",
      }),
    ).toBeNull();
    expect(
      lookupCanonicalNflGame({
        gameId: "2026-W01-NE@SEA",
        season: 2026,
      }),
    ).toMatchObject({
      game_id: "2026-W01-NE@SEA",
      season: 2026,
      away_team_id: "NE",
      home_team_id: "SEA",
    });
  });

  it("T14-CAN does not match when home and away are swapped", () => {
    expect(
      lookupCanonicalNflGame({
        season: 2026,
        week: 1,
        awayAbbr: "SEA",
        homeAbbr: "NE",
        seasonType: "REG",
      }),
    ).toBeNull();
    expect(
      lookupCanonicalNflGame({
        season: 2026,
        awayAbbr: "SEA",
        homeAbbr: "NE",
        seasonType: "REG",
      }),
    ).toBeNull();
    expect(
      lookupCanonicalNflGame({
        gameId: "2026-W01-NE@SEA",
        season: 2026,
        awayAbbr: "SEA",
        homeAbbr: "NE",
      }),
    ).toBeNull();
    expect(
      lookupCanonicalNflGame({
        season: 2026,
        week: 1,
        awayAbbr: "LA",
        homeAbbr: "SF",
        seasonType: "REG",
      }),
    ).toBeNull();
  });

  it("CTRL-does not match a non-REG type when supplied, or directed-unique lookup without REG", () => {
    expect(
      lookupCanonicalNflGame({
        season: 2025,
        week: 1,
        awayAbbr: "NE",
        homeAbbr: "SEA",
        seasonType: "REG",
      }),
    ).toBeNull();
    expect(
      lookupCanonicalNflGame({
        season: 2026,
        week: 1,
        awayAbbr: "NE",
        homeAbbr: "SEA",
        seasonType: "PRE",
      }),
    ).toBeNull();
    expect(
      lookupCanonicalNflGame({
        season: 2026,
        week: 1,
        awayAbbr: "NE",
        homeAbbr: "SEA",
        seasonType: "POST",
      }),
    ).toBeNull();
    expect(
      lookupCanonicalNflGame({
        gameId: "2026-W01-SF@LAR",
        season: 2026,
        seasonType: "PRE",
      }),
    ).toBeNull();
    expect(
      lookupCanonicalNflGame({
        season: 2026,
        awayAbbr: "MIN",
        homeAbbr: "SF",
        seasonType: null,
      }),
    ).toBeNull();
    expect(
      lookupCanonicalNflGame({
        season: 2026,
        awayAbbr: "MIN",
        homeAbbr: "SF",
      }),
    ).toBeNull();
  });

  it("T09-INT-CAN does not match a non-integer week", () => {
    expect(
      lookupCanonicalNflGame({
        season: 2026,
        week: 1.7,
        awayAbbr: "NE",
        homeAbbr: "SEA",
        seasonType: "REG",
      }),
    ).toBeNull();
  });

  it("CTRL-matches the directed pair when week is omitted, season is 2026, and type is REG", () => {
    expect(
      lookupCanonicalNflGame({
        season: 2026,
        awayAbbr: "MIN",
        homeAbbr: "SF",
        seasonType: "REG",
      })?.game_id,
    ).toBe("2026-W11-MIN@SF");
  });
});
