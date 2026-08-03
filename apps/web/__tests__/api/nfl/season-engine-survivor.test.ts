import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/nfl-season-engine", () => ({
  fetchSeasonEngineSurvivor: vi.fn(),
}));

import { POST } from "@/app/api/nfl/season-engine/survivor/route";
import { fetchSeasonEngineSurvivor } from "@/lib/nfl-season-engine";

describe("POST /api/nfl/season-engine/survivor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("requires week", async () => {
    const res = await POST(
      new Request("http://localhost/api/nfl/season-engine/survivor", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ alreadyUsed: ["KC"] }),
      }),
    );
    expect(res.status).toBe(400);
    expect(fetchSeasonEngineSurvivor).not.toHaveBeenCalled();
  });

  it("proxies shaped body and returns ranked picks", async () => {
    vi.mocked(fetchSeasonEngineSurvivor).mockResolvedValue({
      mode: "demo",
      season: 2026,
      week: 5,
      n_sims: 200,
      engine_version: "nfl-season-engine-v1.4.1-hardened",
      already_used: ["KC"],
      ranked_picks: [
        {
          team: "DEN",
          week: 5,
          win_rate: 0.71,
          save_score: 0.56,
          pick_now_score: 0.47,
          opponent: "TEN",
          home_away: "home",
        },
      ],
    });

    const res = await POST(
      new Request("http://localhost/api/nfl/season-engine/survivor", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          week: 5,
          alreadyUsed: ["KC"],
          nSims: 200,
        }),
      }),
    );
    const data = await res.json();

    expect(res.status).toBe(200);
    expect(fetchSeasonEngineSurvivor).toHaveBeenCalledWith(
      expect.objectContaining({
        week: 5,
        alreadyUsed: ["KC"],
        nSims: 200,
      }),
    );
    expect(data.ranked_picks[0].team).toBe("DEN");
  });
});
