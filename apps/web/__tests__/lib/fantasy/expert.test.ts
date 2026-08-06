import { describe, expect, it } from "vitest";
import {
  EMPLOYEE_EXPERTISE_CONTRACT_PATH,
  buildDrivers,
  buildExpertBlurb,
  notableValueNotes,
} from "@/lib/fantasy/expert";
import type { FantasyDeskRow } from "@/lib/fantasy/types";

describe("fantasy expert voice", () => {
  it("inherits the Employee Expertise Contract path", () => {
    expect(EMPLOYEE_EXPERTISE_CONTRACT_PATH).toBe(
      "employee-expertise-contract.md",
    );
  });

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
      schedule: {
        early: "soft",
        playoff: "hard",
        label: "Soft early · Tough playoffs",
        detail: "",
      },
      riskFlags: [],
      drivers: ["1200 rush yards — feature-back volume on SF"],
    });
    expect(blurb).toContain("C.McCaffrey");
    expect(blurb).toContain("SF");
    expect(blurb).toMatch(/16 picks|value/);
    expect(blurb).not.toMatch(/Driven by/i);
    expect(blurb).toMatch(/soft open|Stack early/i);
    expect(blurb).toMatch(/KosEdge:/);
    expect(blurb).not.toMatch(/Vegas/i);
  });

  it("surfaces committee risk before KosEdge angle (expertise contract)", () => {
    const blurb = buildExpertBlurb({
      playerName: "Committee Back",
      team: "NYJ",
      position: "RB",
      rankOverall: 40,
      rankPosition: 18,
      adp: 55,
      valueDelta: 15,
      tier: "solid",
      floorPoints: 100,
      medianPoints: 140,
      ceilingPoints: 180,
      schedule: {
        early: "neutral",
        playoff: "neutral",
        label: "Neutral",
        detail: "",
      },
      riskFlags: [
        {
          kind: "committee",
          label: "Committee",
          detail: "Split backfield — feature role not locked.",
        },
      ],
      drivers: ["700 rush yards — committee volume on NYJ"],
    });
    const riskAt = blurb.indexOf("Risk (price it)");
    const edgeAt = blurb.indexOf("KosEdge:");
    expect(riskAt).toBeGreaterThan(-1);
    expect(edgeAt).toBeGreaterThan(riskAt);
    expect(blurb).toMatch(/What changes the view/);
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
    } as FantasyDeskRow;
    const notes = notableValueNotes([row], 1);
    expect(notes[0]).toContain("1100 receiving yards");
  });
});
