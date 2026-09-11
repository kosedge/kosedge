import { describe, expect, it } from "vitest";
import {
  inventedCeilingFromMean,
  scoreCountingLine,
  scoreProductionForSite,
} from "@/lib/nfl-dfs-scoring";
import {
  pointsPer1k,
  salaryRelativePositionalValue,
} from "@/lib/nfl-dfs-value";
import {
  leverageFromUpsideAndOwn,
  unavailableOwnership,
} from "@/lib/nfl-dfs-ownership";
import { certifyDfsGameQuote } from "@/lib/nfl-dfs-game-env";

describe("DFS site scoring", () => {
  it("uses full PPR on DK and half PPR on FD", () => {
    const line = {
      passYards: 0,
      passTds: 0,
      rushYards: 10,
      rushTds: 0,
      receivingYards: 80,
      receptions: 8,
      recTds: 1,
      applyThresholdBonuses: false,
    };
    const dk = scoreCountingLine({ scoringSystem: "dk_classic", ...line });
    const fd = scoreCountingLine({ scoringSystem: "fd_classic", ...line });
    expect(dk - fd).toBeCloseTo(4, 5);
  });

  it("does not invent floor/ceiling without a distribution", () => {
    const scored = scoreProductionForSite(
      {
        passYards: 0,
        passTds: 0,
        rushYards: 8,
        rushTds: 0.1,
        receivingYards: 92,
        receptions: 7,
        recTds: 0.6,
      },
      "DK",
    );
    expect(scored.projection).toBeGreaterThan(0);
    expect(scored.floor).toBeNull();
    expect(scored.ceiling).toBeNull();
    expect(scored.ceiling).not.toBe(inventedCeilingFromMean(scored.projection));
  });

  it("scores spine outcomes instead of projection × 1.35", () => {
    const scored = scoreProductionForSite(
      {
        passYards: 0,
        passTds: 0,
        rushYards: 8,
        rushTds: 0.1,
        receivingYards: 92,
        receptions: 7,
        recTds: 0.6,
        receivingYardsStd: 28,
        rushYardsStd: 6,
        passYardsStd: 4,
      },
      "DK",
      {
        floor: {
          pass_yards: 0,
          rush_yards: 2,
          receiving_yards: 50,
          receptions: 4,
          touchdowns: 0.2,
        },
        ceiling: {
          pass_yards: 0,
          rush_yards: 20,
          receiving_yards: 140,
          receptions: 10,
          touchdowns: 1.4,
        },
      },
    );
    expect(scored.distributionAvailable).toBe(true);
    expect(scored.floor).not.toBeNull();
    expect(scored.ceiling).not.toBeNull();
    expect(scored.ceiling).not.toBeCloseTo(
      inventedCeilingFromMean(scored.projection),
      1,
    );
  });
});

describe("DFS value + ownership", () => {
  it("exposes points per $1K without pretending it is a rating", () => {
    expect(pointsPer1k(21, 7000)).toBe(3);
    const rel = salaryRelativePositionalValue({
      projection: 22,
      salary: 7000,
      peerSalariesAndProjections: [
        [7000, 22],
        [6900, 18],
        [6800, 17],
      ],
    });
    expect(rel.salaryRelDelta).not.toBeNull();
    expect(rel.salaryRelDelta).toBeGreaterThan(0);
  });

  it("keeps ownership and leverage unavailable", () => {
    const own = unavailableOwnership({
      site: "DK",
      season: 2026,
      week: 1,
      slateId: "151307",
      playerUid: "uid",
    });
    expect(own.status).toBe("unavailable");
    expect(own.projectedOwn).toBeNull();
    expect(
      leverageFromUpsideAndOwn({
        upsideProbability: 0.4,
        expectedOwnership: 0.1,
      }),
    ).toBeNull();
  });
});

describe("DFS game environment identity", () => {
  it("refuses F5 contamination", () => {
    const env = certifyDfsGameQuote(
      {
        market: "totals_1st_5_innings",
        period: "1st5",
        line: 3.5,
        homeTeam: "HOU",
        awayTeam: "BUF",
        season: 2026,
        week: 1,
      },
      { season: 2026, week: 1, team: "BUF", opponent: "HOU" },
    );
    expect(env.available).toBe(false);
    expect(env.reason).toBe("period_not_fg");
  });

  it("refuses a certified FG total from the wrong game", () => {
    const env = certifyDfsGameQuote(
      {
        market: "totals",
        period: "fg",
        line: 47.5,
        homeTeam: "LAC",
        awayTeam: "KC",
        season: 2026,
        week: 1,
      },
      { season: 2026, week: 1, team: "BUF", opponent: "HOU" },
    );
    expect(env.available).toBe(false);
    expect(env.reason).toBe("event_mismatch");
  });
});
