import { describe, expect, it } from "vitest";
import {
  buildDrivers,
  buildExpertBlurb,
  displayRecTdsForExpert,
  notableValueNotes,
  shouldSoftFrameAdpGap,
} from "@/lib/fantasy/expert";
import type { FantasyDeskRow } from "@/lib/fantasy/types";

const softSchedule = {
  early: "soft" as const,
  playoff: "hard" as const,
  label: "Soft early · Tough playoffs",
  detail: "",
};

function baseTeRow(overrides: Partial<FantasyDeskRow> = {}): FantasyDeskRow {
  return {
    season: 2026,
    scoringProfile: "half_ppr",
    modelVersion: "test",
    playerId: "te-test",
    playerUid: null,
    playerName: "M.Gesicki",
    team: "CIN",
    position: "TE",
    gamesProjected: 17,
    passYardsTotal: 0,
    rushYardsTotal: 0,
    receivingYardsTotal: 620,
    receptionsTotal: 55,
    passTdsTotal: 0,
    rushTdsTotal: 0,
    recTdsTotal: 7.7,
    totalPoints: 140,
    floorPoints: 100,
    medianPoints: 140,
    ceilingPoints: 180,
    replacementPoints: 90,
    valueOverReplacement: 50,
    rankOverall: 47,
    rankPosition: 8,
    tier: "TE2",
    adp: 268,
    valueDelta: 221,
    adpMatchedName: "Mike Gesicki",
    adpMatchConfidence: "high",
    isRookie: false,
    rookieYear: null,
    draftNumber: null,
    schedule: softSchedule,
    riskFlags: [],
    expertBlurb: "",
    drivers: ["620 receiving yards (~36/g)"],
    updatedAt: null,
    source: "preseason-fallback",
    ...overrides,
  };
}

describe("fantasy expert voice", () => {
  it("names team and concrete volume in drivers", () => {
    const drivers = buildDrivers({
      position: "RB",
      team: "SF",
      passYardsTotal: 0,
      rushYardsTotal: 1200,
      receivingYardsTotal: 400,
      receptionsTotal: 55,
      passTdsTotal: 0,
      rushTdsTotal: 10,
      recTdsTotal: 3,
      valueOverReplacement: 80,
      tier: "elite",
      gamesProjected: 17,
    });
    expect(drivers[0]).toMatch(/1200/);
    expect(drivers.some((d) => d.includes("SF"))).toBe(true);
  });

  it("blurb cites pick gap and avoids generic filler", () => {
    const blurb = buildExpertBlurb({
      playerName: "C.McCaffrey",
      team: "SF",
      position: "RB",
      rankOverall: 2,
      rankPosition: 1,
      adp: 18,
      valueDelta: 16,
      tier: "elite",
      floorPoints: 220,
      medianPoints: 290,
      ceilingPoints: 350,
      schedule: softSchedule,
      riskFlags: [],
      drivers: ["1200 rush yards — feature-back volume on SF"],
    });
    expect(blurb).toContain("C.McCaffrey");
    expect(blurb).toContain("SF");
    expect(blurb).toMatch(/16 picks|value/);
    expect(blurb).not.toMatch(/Driven by/i);
    expect(blurb).toMatch(/soft open|Stack early/i);
  });

  it("value notes include a concrete driver", () => {
    const row = {
      playerName: "Test WR",
      team: "DET",
      position: "WR",
      rankPosition: 4,
      rankOverall: 22,
      adp: 40,
      valueDelta: 18,
      drivers: ["1100 receiving yards (~65/g)"],
      source: "model-service",
    } as FantasyDeskRow;
    const notes = notableValueNotes([row], 1);
    expect(notes[0]).toContain("1100 receiving yards");
    expect(notes[0]).toMatch(/\+18/);
  });
});

describe("TE TD display honesty", () => {
  it("suppresses ~7 rec TDs for TE2/TE3 (Gesicki-style)", () => {
    expect(
      displayRecTdsForExpert({
        position: "TE",
        tier: "TE2",
        rankPosition: 8,
        recTdsTotal: 7.7,
      }),
    ).toBeNull();

    const drivers = buildDrivers({
      position: "TE",
      team: "CIN",
      passYardsTotal: 0,
      rushYardsTotal: 0,
      receivingYardsTotal: 620,
      receptionsTotal: 55,
      passTdsTotal: 0,
      rushTdsTotal: 0,
      recTdsTotal: 7.7,
      valueOverReplacement: 50,
      tier: "TE2",
      gamesProjected: 17,
      rankPosition: 8,
    });
    expect(drivers.join(" ")).not.toMatch(/7\.7|receiving TDs/i);
    expect(drivers.some((d) => /receiving yards|catches/i.test(d))).toBe(true);
  });

  it("suppresses Engram / Parkinson-style TE2 TD cliffs", () => {
    for (const sample of [
      { name: "E.Engram", tier: "TE2", rankPosition: 10, recTds: 7.1 },
      { name: "C.Parkinson", tier: "TE3", rankPosition: 14, recTds: 6.9 },
    ]) {
      const shown = displayRecTdsForExpert({
        position: "TE",
        tier: sample.tier,
        rankPosition: sample.rankPosition,
        recTdsTotal: sample.recTds,
      });
      expect(shown).toBeNull();
      const drivers = buildDrivers({
        position: "TE",
        team: "DEN",
        passYardsTotal: 0,
        rushYardsTotal: 0,
        receivingYardsTotal: 580,
        receptionsTotal: 52,
        passTdsTotal: 0,
        rushTdsTotal: 0,
        recTdsTotal: sample.recTds,
        valueOverReplacement: 35,
        tier: sample.tier,
        gamesProjected: 17,
        rankPosition: sample.rankPosition,
      });
      expect(drivers.join(" ")).not.toMatch(/receiving TDs/i);
    }
  });

  it("allows elite TE1 TD headlines only inside the soft-cap band", () => {
    expect(
      displayRecTdsForExpert({
        position: "TE",
        tier: "elite",
        rankPosition: 1,
        recTdsTotal: 7.2,
      }),
    ).toBe(7.2);

    expect(
      displayRecTdsForExpert({
        position: "TE",
        tier: "elite",
        rankPosition: 1,
        recTdsTotal: 11.5,
      }),
    ).toBe(8);

    // Elite tier but deep positional rank — still not a true TE1 volume headline.
    expect(
      displayRecTdsForExpert({
        position: "TE",
        tier: "elite",
        rankPosition: 8,
        recTdsTotal: 7.5,
      }),
    ).toBeNull();
  });
});

describe("ADP gap framing honesty", () => {
  it("soft-frames TE with +200 ADP gap when model rank is not early-round", () => {
    expect(
      shouldSoftFrameAdpGap({
        position: "TE",
        rankOverall: 47,
        rankPosition: 8,
        valueDelta: 221,
      }),
    ).toBe(true);

    const blurb = buildExpertBlurb({
      playerName: "M.Gesicki",
      team: "CIN",
      position: "TE",
      rankOverall: 47,
      rankPosition: 8,
      adp: 268,
      valueDelta: 221,
      tier: "TE2",
      floorPoints: 100,
      medianPoints: 140,
      ceilingPoints: 180,
      schedule: softSchedule,
      riskFlags: [],
      drivers: ["620 receiving yards (~36/g)"],
      source: "preseason-fallback",
    });
    expect(blurb).toMatch(/likes him more than market/i);
    expect(blurb).toMatch(/not a lottery smash/i);
    expect(blurb).not.toMatch(/221 picks|about 221/i);
    expect(blurb).toMatch(/preseason sim/i);
    expect(blurb).toMatch(/Camp-season sim/i);
  });

  it("keeps pick-gap framing for credible early-round value", () => {
    expect(
      shouldSoftFrameAdpGap({
        position: "TE",
        rankOverall: 24,
        rankPosition: 3,
        valueDelta: 70,
      }),
    ).toBe(false);

    const blurb = buildExpertBlurb({
      playerName: "T.Kelce",
      team: "KC",
      position: "TE",
      rankOverall: 24,
      rankPosition: 3,
      adp: 94,
      valueDelta: 70,
      tier: "elite",
      floorPoints: 160,
      medianPoints: 200,
      ceilingPoints: 240,
      schedule: softSchedule,
      riskFlags: [],
      drivers: ["900 receiving yards (~53/g)"],
      source: "model-service",
    });
    expect(blurb).toMatch(/70 picks of value/i);
    expect(blurb).not.toMatch(/lottery smash/i);
  });

  it("soft-frames QB2 lottery ADP gaps", () => {
    expect(
      shouldSoftFrameAdpGap({
        position: "QB",
        rankOverall: 55,
        rankPosition: 14,
        valueDelta: 120,
      }),
    ).toBe(true);
  });

  it("notableValueNotes avoid +200 hero framing for Gesicki-style TE", () => {
    const notes = notableValueNotes(
      [
        baseTeRow(),
        baseTeRow({
          playerId: "engram",
          playerName: "E.Engram",
          team: "DEN",
          rankOverall: 52,
          rankPosition: 10,
          adp: 240,
          valueDelta: 188,
          drivers: ["580 receiving yards (~34/g)"],
        }),
        baseTeRow({
          playerId: "parkinson",
          playerName: "C.Parkinson",
          team: "LAR",
          rankOverall: 61,
          rankPosition: 14,
          tier: "TE3",
          adp: 255,
          valueDelta: 194,
          drivers: ["510 receiving yards (~30/g)"],
        }),
      ],
      3,
    );
    expect(notes.length).toBe(3);
    for (const note of notes) {
      expect(note).toMatch(/likes him more than ADP/i);
      expect(note).not.toMatch(/\+22[0-9]|\+18[0-9]|\+19[0-9]/);
      expect(note).not.toMatch(/7\.7 receiving TDs|receiving TDs/i);
      expect(note).toMatch(/preseason sim/i);
    }
  });
});
