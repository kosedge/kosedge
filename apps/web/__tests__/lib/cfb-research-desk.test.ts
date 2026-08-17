import { describe, expect, it } from "vitest";
import {
  CFB_AFFILIATION_OVERLAY,
  parseCfbConferenceFilter,
  teamMatchesConferenceFilter,
} from "@/lib/cfb-conferences";
import {
  getCfbConferencePreviews,
  getCfbTeamPreviews,
} from "@/lib/cfb-previews";
import {
  cfbPowerTeams,
  cfbProjectionTeams,
  cfbResearchVersionStrip,
  loadCfbPowerSot,
  loadCfbSeasonProjections,
  projectGameHref,
} from "@/lib/cfb-research-artifacts";

describe("cfb research artifacts", () => {
  it("ships 136 FBS power rows with used_in_spread=false and no KEI", () => {
    const pack = loadCfbPowerSot();
    const teams = cfbPowerTeams();
    expect(pack.used_in_spread).toBe(false);
    expect(pack.kei).toBe(false);
    expect(teams).toHaveLength(136);
    expect(teams[0]?.team).toBe("OSU");
    expect((teams[0]?.rank ?? 0) < 10).toBe(true);
    const g5OverP4 = teams
      .slice(0, 10)
      .filter((t) =>
        ["AAC", "Mountain West", "Sun Belt", "MAC", "CUSA"].includes(
          t.conference ?? "",
        ),
      );
    expect(g5OverP4).toHaveLength(0);
  });

  it("documents frozen N>=2000 win totals and omits CFP", () => {
    const pack = loadCfbSeasonProjections();
    const version = cfbResearchVersionStrip();
    expect(pack.used_in_spread).toBe(false);
    expect(pack.kei).toBe(false);
    expect(pack.cfp_make).toBeNull();
    expect(pack.natty).toBeNull();
    expect(version.n_sims).toBeGreaterThanOrEqual(2000);
    expect(version.used_in_spread).toBe(false);
    expect(cfbProjectionTeams().length).toBe(136);
  });

  it("does not deep-link FCS next opponents into project-game", () => {
    expect(
      projectGameHref({
        team: "UTAH",
        next: { week: 1, opponent: "FCS:IDHO", home: true },
      }),
    ).toBeNull();
    expect(
      projectGameHref({
        team: "OSU",
        next: { week: 1, opponent: "BALL", home: true },
      }),
    ).toContain("home=OSU");
  });
});

describe("cfb conference filter", () => {
  it("treats Power 4 as SEC/B1G/ACC/Big 12 and overlays leftover Independent", () => {
    expect(parseCfbConferenceFilter("p4")).toBe("p4");
    expect(teamMatchesConferenceFilter("OSU", "Big Ten", "p4")).toBe(true);
    expect(teamMatchesConferenceFilter("USF", "AAC", "p4")).toBe(false);
    expect(CFB_AFFILIATION_OVERLAY.MIZZ).toBe("SEC");
    expect(teamMatchesConferenceFilter("MIZZ", "Independent", "sec")).toBe(true);
    expect(teamMatchesConferenceFilter("ND", "Independent", "independent")).toBe(
      true,
    );
  });
});

describe("cfb previews", () => {
  it("ships at least 8 team previews and Power-4 + ND + 2 G5 conferences", () => {
    const teams = getCfbTeamPreviews();
    const confs = getCfbConferencePreviews();
    expect(teams.length).toBeGreaterThanOrEqual(8);
    expect(confs.map((c) => c.slug).sort()).toEqual(
      [
        "aac",
        "acc",
        "big-12",
        "big-ten",
        "independent",
        "mountain-west",
        "sec",
      ].sort(),
    );
    for (const p of teams) {
      expect(p.modelNote).toMatch(/used_in_spread=false/);
      expect(p.modelNote).toMatch(/no KEI/i);
      expect(p.bettingAngles.toLowerCase()).not.toContain("play tag");
      expect(p.bettingAngles.toLowerCase()).not.toContain("this is a play");
    }
  });
});
