import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/config/env", () => ({
  env: {
    MODEL_SERVICE_URL: "http://model-service.local",
    INTERNAL_API_SECRET: "test-secret",
  },
}));

import {
  fetchNflIntel,
  formatIntelValue,
  formatTeamRecordWithRank,
  formatIntelValueWithRank,
  groupStandingsRows,
  sortStandingsRows,
} from "@/lib/nfl-intel";

describe("fetchNflIntel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("passes explicit filters and returns selection metadata", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        season: 2026,
        week: 1,
        team: null,
        count: 0,
        rows: [],
        selection: {
          used_default: { season: false, week: false, any: false },
          latest_available: { season: 2025, week: 22, row_count: 320, team_count: 32 },
          requested_availability: {
            season: 2026,
            week: 1,
            row_count: 0,
            team_count: 0,
            has_data: false,
          },
        },
      }),
    } as Response);

    const payload = await fetchNflIntel("rosters", {
      season: 2026,
      week: 1,
      team: "buf",
    });

    const requestedUrl = String(fetchSpy.mock.calls[0]?.[0]);
    expect(requestedUrl).toContain("/nfl/intel/rosters");
    expect(requestedUrl).toContain("season=2026");
    expect(requestedUrl).toContain("week=1");
    expect(requestedUrl).toContain("team=BUF");
    expect(payload.selection?.requested_availability?.has_data).toBe(false);
    expect(payload.selection?.latest_available?.season).toBe(2025);
    expect(payload.selection?.latest_available?.week).toBe(22);
  });

  it("sorts standings by conference, division, and rank inputs", () => {
    const sorted = sortStandingsRows([
      { team: "SEA", wins: 10, win_pct: 0.625, point_diff: 35, conference: "NFC", division: "West" },
      { team: "MIA", wins: 11, win_pct: 0.688, point_diff: 40, conference: "AFC", division: "East" },
      { team: "BUF", wins: 12, win_pct: 0.75, point_diff: 60, conference: "AFC", division: "East" },
      { team: "XYZ", wins: 9, win_pct: 0.56, point_diff: 10, conference: null, division: null },
      { team: "BAL", wins: 11, win_pct: 0.688, point_diff: 50, conference: "AFC", division: "North" },
    ]);

    expect(sorted.map((row) => row.team)).toEqual(["BUF", "MIA", "BAL", "SEA", "XYZ"]);
    expect(sorted[4]?.conference).toBe("Unknown");
    expect(sorted[4]?.division).toBe("Unknown");
  });

  it("derives missing conference/division from team map", () => {
    const sorted = sortStandingsRows([
      { team: "BUF", wins: 12, win_pct: 0.75, point_diff: 60, conference: null, division: null },
      { team: "MIA", wins: 11, win_pct: 0.688, point_diff: 40, conference: null, division: null },
    ]);

    expect(sorted[0]?.conference).toBe("AFC");
    expect(sorted[0]?.division).toBe("East");
    expect(sorted[1]?.conference).toBe("AFC");
    expect(sorted[1]?.division).toBe("East");
  });

  it("groups sorted standings by conference and division", () => {
    const groups = groupStandingsRows([
      { team: "SEA", wins: 10, win_pct: 0.625, point_diff: 35, conference: "NFC", division: "West" },
      { team: "MIA", wins: 11, win_pct: 0.688, point_diff: 40, conference: "AFC", division: "East" },
      { team: "BUF", wins: 12, win_pct: 0.75, point_diff: 60, conference: "AFC", division: "East" },
      { team: "BAL", wins: 11, win_pct: 0.688, point_diff: 50, conference: "AFC", division: "North" },
    ]);

    expect(groups.map((group) => `${group.conference}-${group.division}`)).toEqual([
      "AFC-East",
      "AFC-North",
      "NFC-West",
    ]);
    expect(groups[0]?.rows.map((row) => row.team)).toEqual(["BUF", "MIA"]);
  });

  it("formats non-integer numerics to 3 decimals", () => {
    expect(formatIntelValue(0.8571)).toBe("0.857");
    expect(formatIntelValue(12.34567)).toBe("12.346");
    expect(formatIntelValue(7)).toBe("7");
  });

  it("appends rank when numeric rank is provided", () => {
    expect(formatIntelValueWithRank(12.34567, 3)).toBe("12.346 (3)");
    expect(formatIntelValueWithRank(-3.1254, 5, true)).toBe("-3.125 (5)");
    expect(formatIntelValueWithRank("BUF", 2)).toBe("BUF");
  });

  it("formats team record with optional ties and rank", () => {
    expect(formatTeamRecordWithRank({ wins: 15, losses: 2, ties: 0 }, 1)).toBe("15-2 (1)");
    expect(formatTeamRecordWithRank({ wins: 10, losses: 6, ties: 1 }, 4)).toBe("10-6-1 (4)");
    expect(formatTeamRecordWithRank({ wins: 9, losses: 8, ties: 0 })).toBe("9-8");
    expect(formatTeamRecordWithRank({ wins: 9 })).toBe("—");
  });
});
