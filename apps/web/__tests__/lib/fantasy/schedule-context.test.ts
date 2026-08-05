import { describe, expect, it } from "vitest";
import { buildTeamScheduleNotes } from "@/lib/fantasy/schedule-context";
import { gamesFromWallChart } from "@/lib/fantasy/load-schedule";

describe("schedule context", () => {
  it("labels soft early when opponents are weak", () => {
    const notes = buildTeamScheduleNotes(
      [
        { week: 1, homeTeam: "AAA", awayTeam: "WEAK" },
        { week: 2, homeTeam: "AAA", awayTeam: "WEAK" },
        { week: 3, homeTeam: "AAA", awayTeam: "WEAK" },
        { week: 14, homeTeam: "AAA", awayTeam: "STRONG" },
        { week: 15, homeTeam: "AAA", awayTeam: "STRONG" },
        { week: 16, homeTeam: "AAA", awayTeam: "STRONG" },
      ],
      [
        { team: "AAA", expectedWins: 9 },
        { team: "WEAK", expectedWins: 5 },
        { team: "STRONG", expectedWins: 12 },
      ],
    );
    const aaa = notes.get("AAA")!;
    expect(aaa.early).toBe("soft");
    expect(aaa.playoff).toBe("hard");
    expect(aaa.label).toContain("Soft early");
    expect(aaa.label).toContain("Tough playoffs");
  });

  it("parses wall chart home entries only", () => {
    const games = gamesFromWallChart({
      KC: { "1": "vs BUF", "2": "@ LAC" },
      BUF: { "1": "@ KC", "2": "vs NYJ" },
    });
    expect(games).toEqual(
      expect.arrayContaining([
        { week: 1, homeTeam: "KC", awayTeam: "BUF" },
        { week: 2, homeTeam: "BUF", awayTeam: "NYJ" },
      ]),
    );
    expect(games).toHaveLength(2);
  });
});
