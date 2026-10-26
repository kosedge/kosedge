import { describe, expect, it } from "vitest";
import { resolveNflKickoffIso } from "@/lib/nfl-schedule-kickoff";

describe("K2 1A-C caller season", () => {
  it('C2-P1a resolveNflKickoffIso {gameId:"odds-uuid", season:2026, week:1, awayAbbr:"NE", homeAbbr:"SEA", startTime:"2026-09-13T20:00:00.000Z"}', () => {
    expect(
      resolveNflKickoffIso({
        gameId: "odds-uuid",
        season: 2026,
        week: 1,
        awayAbbr: "NE",
        homeAbbr: "SEA",
        startTime: "2026-09-13T20:00:00.000Z",
      }),
    ).toBe("2026-09-10T00:20:00.000Z");
  });

  it('C2-P1b resolveNflKickoffIso {gameId:"odds-uuid", season:2026, seasonType:"REG", awayAbbr:"NE", homeAbbr:"SEA", startTime:"2026-09-13T20:00:00.000Z"}', () => {
    expect(
      resolveNflKickoffIso({
        gameId: "odds-uuid",
        season: 2026,
        seasonType: "REG",
        awayAbbr: "NE",
        homeAbbr: "SEA",
        startTime: "2026-09-13T20:00:00.000Z",
      }),
    ).toBe("2026-09-10T00:20:00.000Z");
  });

  it('C2-P1c resolveNflKickoffIso {gameId:"odds-uuid", season:2026, awayAbbr:"NE", homeAbbr:"SEA", startTime:"2026-09-13T20:00:00.000Z"}', () => {
    expect(
      resolveNflKickoffIso({
        gameId: "odds-uuid",
        season: 2026,
        awayAbbr: "NE",
        homeAbbr: "SEA",
        startTime: "2026-09-13T20:00:00.000Z",
      }),
    ).toBe("2026-09-13T20:00:00.000Z");
  });

  it('C2-P1d resolveNflKickoffIso {gameId:"odds-uuid", week:1, awayAbbr:"NE", homeAbbr:"SEA", startTime:"2026-09-13T20:00:00.000Z"}', () => {
    expect(
      resolveNflKickoffIso({
        gameId: "odds-uuid",
        week: 1,
        awayAbbr: "NE",
        homeAbbr: "SEA",
        startTime: "2026-09-13T20:00:00.000Z",
      }),
    ).toBe("2026-09-13T20:00:00.000Z");
  });

  it('C2-P1e resolveNflKickoffIso {gameId:"x", season:2026, week:18, awayAbbr:"MIA", homeAbbr:"NE", startTime:"2026-09-13T20:00:00.000Z"}', () => {
    expect(
      resolveNflKickoffIso({
        gameId: "x",
        season: 2026,
        week: 18,
        awayAbbr: "MIA",
        homeAbbr: "NE",
        startTime: "2026-09-13T20:00:00.000Z",
      }),
    ).toBeNull();
  });

  it('C2-P1f resolveNflKickoffIso {gameId:"odds-uuid", season:2026, week:1, seasonType:"POST", awayAbbr:"NE", homeAbbr:"SEA", startTime:"2026-09-13T20:00:00.000Z"}', () => {
    expect(
      resolveNflKickoffIso({
        gameId: "odds-uuid",
        season: 2026,
        week: 1,
        seasonType: "POST",
        awayAbbr: "NE",
        homeAbbr: "SEA",
        startTime: "2026-09-13T20:00:00.000Z",
      }),
    ).toBe("2026-09-13T20:00:00.000Z");
  });
});
