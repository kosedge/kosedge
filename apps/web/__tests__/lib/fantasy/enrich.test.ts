import { describe, expect, it } from "vitest";
import { enrichDraftRows } from "@/lib/fantasy/enrich";
import { NEUTRAL_SCHEDULE } from "@/lib/fantasy/schedule-context";

describe("enrichDraftRows", () => {
  it("adds ADP, value delta, bands, and expert blurb", () => {
    const rows = enrichDraftRows({
      rows: [
        {
          season: 2026,
          scoringProfile: "half_ppr",
          modelVersion: "test",
          playerId: "rb1",
          playerUid: null,
          playerName: "Test Back",
          team: "KC",
          position: "RB",
          gamesProjected: 17,
          passYardsTotal: 0,
          rushYardsTotal: 1200,
          receivingYardsTotal: 400,
          receptionsTotal: 50,
          passTdsTotal: 0,
          rushTdsTotal: 10,
          recTdsTotal: 3,
          totalPoints: 280,
          replacementPoints: 140,
          valueOverReplacement: 140,
          rankOverall: 3,
          rankPosition: 1,
          tier: "elite",
          isRookie: false,
          rookieYear: null,
          draftNumber: null,
          updatedAt: null,
          source: "preseason-fallback",
        },
      ],
      scheduleByTeam: new Map([["KC", NEUTRAL_SCHEDULE]]),
      depthRows: [],
    });
    expect(rows).toHaveLength(1);
    expect(rows[0]!.adp).toBeGreaterThan(0);
    expect(rows[0]!.floorPoints).toBeLessThan(rows[0]!.medianPoints);
    expect(rows[0]!.ceilingPoints).toBeGreaterThan(rows[0]!.medianPoints);
    expect(rows[0]!.expertBlurb.length).toBeGreaterThan(20);
    expect(rows[0]!.drivers.length).toBeGreaterThan(0);
  });
});
