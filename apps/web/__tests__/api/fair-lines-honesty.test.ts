import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/auth/pro", () => ({
  getProAccessState: vi.fn(),
}));

vi.mock("@/lib/mlb-fair-lines", () => ({
  fetchMlbFairLines: vi.fn(),
}));

vi.mock("@/lib/nba-fair-lines", () => ({
  fetchNbaFairLines: vi.fn(),
}));

vi.mock("@/lib/nhl-fair-lines", () => ({
  fetchNhlFairLines: vi.fn(),
}));

vi.mock("@/lib/wnba-fair-lines", () => ({
  fetchWnbaFairLines: vi.fn(),
}));

import { getProAccessState } from "@/lib/auth/pro";
import { GET as getCfb } from "@/app/api/cfb/fair-lines/route";
import { GET as getMlb } from "@/app/api/mlb/fair-lines/route";
import { GET as getNba } from "@/app/api/nba/fair-lines/route";
import { GET as getNhl } from "@/app/api/nhl/fair-lines/route";
import { GET as getWnba } from "@/app/api/wnba/fair-lines/route";
import { fetchMlbFairLines } from "@/lib/mlb-fair-lines";
import { fetchNbaFairLines } from "@/lib/nba-fair-lines";
import { fetchNhlFairLines } from "@/lib/nhl-fair-lines";
import { fetchWnbaFairLines } from "@/lib/wnba-fair-lines";
import { FAIR_LINES_DO_NOT_INVENT } from "@/lib/fair-lines-api-board";

describe("non-NFL /api/{sport}/fair-lines honesty", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getProAccessState).mockResolvedValue("authorized");
  });

  it("CFB returns 200 honest empty not_connected (never invents)", async () => {
    const res = await getCfb();
    const body = await res.json();
    expect(res.status).toBe(200);
    expect(body.sport).toBe("cfb");
    expect(body.count).toBe(0);
    expect(body.lines).toEqual([]);
    expect(body.asOf).toBeNull();
    expect(body.oddsAsOf).toBeNull();
    expect(body.slateStatus).toBe("not_connected");
    expect(body.message).toContain("not connected");
    expect(body.message).toContain(FAIR_LINES_DO_NOT_INVENT);
  });

  it("MLB empty slate stays empty with null as-of stamps", async () => {
    vi.mocked(fetchMlbFairLines).mockResolvedValue({
      gameDate: "2026-09-04",
      modelVersion: "",
      count: 0,
      lines: [],
    });
    const res = await getMlb(new Request("http://localhost/api/mlb/fair-lines"));
    const body = await res.json();
    expect(res.status).toBe(200);
    expect(body.count).toBe(0);
    expect(body.asOf).toBeNull();
    expect(body.oddsAsOf).toBeNull();
    expect(body.slateStatus).toBe("no_slate");
    expect(body.message).toContain(FAIR_LINES_DO_NOT_INVENT);
  });

  it("NBA proxies real lines without inventing asOf", async () => {
    vi.mocked(fetchNbaFairLines).mockResolvedValue({
      gameDate: "2026-09-04",
      modelVersion: "nba-test",
      workerBuildId: "w1",
      count: 1,
      lines: [
        {
          gameId: "g1",
          gameDate: "2026-09-04",
          startTime: null,
          homeTeam: "Home",
          awayTeam: "Away",
          homeWinProb: 0.55,
          fairHomeMl: -120,
          fairAwayMl: 100,
          totalMean: 220,
          fairTotal: 220,
          fairSpreadHome: -3.5,
          homeCoverProb: 0.52,
          marginMean: 3.1,
          projectedAt: null,
          modelVersion: "nba-test",
          workerBuildId: "w1",
        },
      ],
      slateStatus: "ok",
      message: "ok",
    });
    const res = await getNba(new Request("http://localhost/api/nba/fair-lines"));
    const body = await res.json();
    expect(res.status).toBe(200);
    expect(body.count).toBe(1);
    expect(body.lines).toHaveLength(1);
    expect(body.asOf).toBeNull();
    expect(body.oddsAsOf).toBeNull();
    expect(body.slateStatus).toBe("ok");
  });

  it("NHL offseason_empty stays honest empty", async () => {
    vi.mocked(fetchNhlFairLines).mockResolvedValue({
      gameDate: "2026-09-04",
      modelVersion: "",
      workerBuildId: "",
      count: 0,
      lines: [],
      slateStatus: "offseason_empty",
      message: "Offseason empty",
    });
    const res = await getNhl(new Request("http://localhost/api/nhl/fair-lines"));
    const body = await res.json();
    expect(res.status).toBe(200);
    expect(body.count).toBe(0);
    expect(body.slateStatus).toBe("offseason_empty");
    expect(body.asOf).toBeNull();
    expect(body.oddsAsOf).toBeNull();
  });

  it("WNBA proxies empty without inventing prices", async () => {
    vi.mocked(fetchWnbaFairLines).mockResolvedValue({
      gameDate: "2026-09-04",
      modelVersion: "",
      workerBuildId: "",
      count: 0,
      lines: [],
      slateStatus: "no_projections_yet",
      message: "No projections yet",
    });
    const res = await getWnba(
      new Request("http://localhost/api/wnba/fair-lines"),
    );
    const body = await res.json();
    expect(res.status).toBe(200);
    expect(body.count).toBe(0);
    expect(body.lines).toEqual([]);
    expect(body.asOf).toBeNull();
    expect(body.oddsAsOf).toBeNull();
  });

  it("returns 401 when not authorized", async () => {
    vi.mocked(getProAccessState).mockResolvedValue("unauthenticated");
    const res = await getCfb();
    expect(res.status).toBe(401);
  });
});
