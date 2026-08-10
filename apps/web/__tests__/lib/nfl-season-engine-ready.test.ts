import { describe, expect, it } from "vitest";
import {
  isSeasonEngineReady,
  seasonEnginePackagedNotice,
} from "@/lib/nfl-season-engine";

describe("isSeasonEngineReady", () => {
  it("accepts packaged real mode with full schedule/depth", () => {
    expect(
      isSeasonEngineReady({
        mode: "real",
        schedule_game_count: 272,
        depth_named_skill_teams: 32,
      }),
    ).toBe(true);
  });

  it("rejects errors and incomplete universe", () => {
    expect(
      isSeasonEngineReady({
        error: "Upstream timed out",
        mode: "real",
        schedule_game_count: 272,
        depth_named_skill_teams: 32,
      }),
    ).toBe(false);
    expect(
      isSeasonEngineReady({
        mode: "demo",
        schedule_game_count: 272,
        depth_named_skill_teams: 32,
      }),
    ).toBe(false);
  });
});

describe("seasonEnginePackagedNotice", () => {
  it("surfaces packaged sources as informational", () => {
    expect(
      seasonEnginePackagedNotice({
        schedule_source: "packaged_wall_chart_2026",
        depth_source: "packaged_nflverse_depth_2026",
      }),
    ).toBe(
      "Not current 2026 depth/usage — packaged schedule/depth (synthetic roles until live feeds land)",
    );
  });

  it("returns null when sources are not packaged", () => {
    expect(
      seasonEnginePackagedNotice({
        schedule_source: "db_schedules",
        depth_source: "db_depth",
      }),
    ).toBeNull();
  });
});
