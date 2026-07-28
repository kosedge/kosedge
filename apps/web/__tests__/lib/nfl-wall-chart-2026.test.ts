import { describe, expect, it } from "vitest";
import {
  getWallChartConferenceTeams,
  getWallChartOpponent,
  getWallChartSchedule,
  NFL_WALL_CHART_WEEKS,
} from "@/lib/nfl-wall-chart-2026";

describe("nfl-wall-chart-2026", () => {
  it("includes all 32 teams with 17 games and one bye", () => {
    const schedule = getWallChartSchedule();
    expect(Object.keys(schedule)).toHaveLength(32);
    expect(schedule.LAR).toBeTruthy();
    expect(schedule.LA).toBeUndefined();

    for (const [team, weeks] of Object.entries(schedule)) {
      const filled = NFL_WALL_CHART_WEEKS.filter((week) => weeks[String(week)]);
      expect(filled, team).toHaveLength(17);
      const byes = NFL_WALL_CHART_WEEKS.filter((week) => !weeks[String(week)]);
      expect(byes, team).toHaveLength(1);
    }
  });

  it("splits conferences into 16 teams each", () => {
    expect(getWallChartConferenceTeams("AFC")).toHaveLength(16);
    expect(getWallChartConferenceTeams("NFC")).toHaveLength(16);
  });

  it("labels home and away opponents", () => {
    expect(getWallChartOpponent("SEA", 1)).toBe("vs NE");
    expect(getWallChartOpponent("NE", 1)).toBe("@ SEA");
    expect(getWallChartOpponent("LAR", 1)).toBe("vs SF");
  });
});
