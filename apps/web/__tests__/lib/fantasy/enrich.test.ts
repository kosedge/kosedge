import { describe, expect, it } from "vitest";
import { enrichDraftRows } from "@/lib/fantasy/enrich";
import { NEUTRAL_SCHEDULE } from "@/lib/fantasy/schedule-context";

describe("enrichDraftRows", () => {
  it("attaches real ADP and value delta when matched", () => {
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
      adpByPlayerId: new Map([
        [
          "rb1",
          {
            adp: 12.5,
            ecr: 10,
            matchedName: "Test Back",
            matchKind: "full_name",
            confidence: "high",
          },
        ],
      ]),
    });
    expect(rows).toHaveLength(1);
    expect(rows[0]!.adp).toBe(12.5);
    expect(rows[0]!.valueDelta).toBe(9.5);
    expect(rows[0]!.adpMatchedName).toBe("Test Back");
    expect(rows[0]!.adpMatchConfidence).toBe("high");
    expect(rows[0]!.floorPoints).toBeLessThan(rows[0]!.medianPoints);
    expect(rows[0]!.ceilingPoints).toBeGreaterThan(rows[0]!.medianPoints);
    expect(rows[0]!.expertBlurb.length).toBeGreaterThan(20);
    expect(rows[0]!.drivers.length).toBeGreaterThan(0);
  });

  it("leaves ADP null when unmatched (no fake precision)", () => {
    const rows = enrichDraftRows({
      rows: [
        {
          season: 2026,
          scoringProfile: "half_ppr",
          modelVersion: "test",
          playerId: "rb2",
          playerUid: null,
          playerName: "Unknown Back",
          team: "DAL",
          position: "RB",
          gamesProjected: 17,
          passYardsTotal: 0,
          rushYardsTotal: 800,
          receivingYardsTotal: 200,
          receptionsTotal: 30,
          passTdsTotal: 0,
          rushTdsTotal: 6,
          recTdsTotal: 1,
          totalPoints: 180,
          replacementPoints: 140,
          valueOverReplacement: 40,
          rankOverall: 40,
          rankPosition: 18,
          tier: "RB2",
          isRookie: false,
          rookieYear: null,
          draftNumber: null,
          updatedAt: null,
          source: "preseason-fallback",
        },
      ],
      scheduleByTeam: new Map(),
      depthRows: [],
    });
    expect(rows[0]!.adp).toBeNull();
    expect(rows[0]!.valueDelta).toBeNull();
    expect(rows[0]!.adpMatchConfidence).toBeNull();
    expect(rows[0]!.expertBlurb).toMatch(/no clean market ADP/i);
  });

  it("shows ADP but blanks Value Δ for cross-format matches", () => {
    const rows = enrichDraftRows({
      rows: [
        {
          season: 2026,
          scoringProfile: "half_ppr",
          modelVersion: "test",
          playerId: "wr1",
          playerUid: null,
          playerName: "Deep Board",
          team: "CAR",
          position: "WR",
          gamesProjected: 17,
          passYardsTotal: 0,
          rushYardsTotal: 0,
          receivingYardsTotal: 700,
          receptionsTotal: 50,
          passTdsTotal: 0,
          rushTdsTotal: 0,
          recTdsTotal: 4,
          totalPoints: 140,
          replacementPoints: 100,
          valueOverReplacement: 40,
          rankOverall: 80,
          rankPosition: 32,
          tier: "WR3",
          isRookie: false,
          rookieYear: null,
          draftNumber: null,
          updatedAt: null,
          source: "preseason-fallback",
        },
      ],
      scheduleByTeam: new Map(),
      depthRows: [],
      adpByPlayerId: new Map([
        [
          "wr1",
          {
            adp: 280,
            ecr: 250,
            matchedName: "Deep Board",
            matchKind: "initial_last",
            confidence: "cross_format",
            adpScoringProfile: "ppr",
          },
        ],
      ]),
    });
    expect(rows[0]!.adp).toBe(280);
    expect(rows[0]!.valueDelta).toBeNull();
    expect(rows[0]!.adpMatchConfidence).toBe("cross_format");
  });
});
