import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/cfb-season-engine", () => ({
  fetchCfbProjectGame: vi.fn(),
}));

import { POST } from "@/app/api/cfb/season-engine/project-game/route";
import { fetchCfbProjectGame } from "@/lib/cfb-season-engine";

describe("POST /api/cfb/season-engine/project-game", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("requires home and away teams", async () => {
    const res = await POST(
      new Request("http://localhost/api/cfb/season-engine/project-game", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ week: 1 }),
      }),
    );
    expect(res.status).toBe(400);
    expect(fetchCfbProjectGame).not.toHaveBeenCalled();
  });

  it("proxies shaped camelCase body to project-game client", async () => {
    vi.mocked(fetchCfbProjectGame).mockResolvedValue({
      ok: true,
      home_team: "UGA",
      away_team: "CLEM",
      spread_home: -4.2,
      expected_total: 57.5,
      home_win_prob: 0.61,
      engine_version: "cfb-season-engine-v0.5.1-ui",
    });

    const res = await POST(
      new Request("http://localhost/api/cfb/season-engine/project-game", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          homeTeam: "UGA",
          awayTeam: "CLEM",
          week: 2,
          neutralSite: true,
          nightGame: false,
        }),
      }),
    );
    const data = await res.json();

    expect(res.status).toBe(200);
    expect(fetchCfbProjectGame).toHaveBeenCalledWith(
      expect.objectContaining({
        homeTeam: "UGA",
        awayTeam: "CLEM",
        week: 2,
        neutralSite: true,
        nightGame: false,
      }),
    );
    expect(data.spread_home).toBe(-4.2);
    expect(data.engine_version).toContain("v0.5.1");
  });
});
