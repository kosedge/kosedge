import { describe, expect, it } from "vitest";
import {
  competitionImpliesOpenRace,
  formatCompetitionAwareIntelCell,
  formatCompetitionLabel,
  formatCompetitionStatus,
  formatDepthSlotLabel,
  humanizeCompetitionTokensInText,
  isPackagedDepthStale,
  NFL_DEPTH_PACK_AS_OF,
  NFL_DEPTH_PACK_MAX_AGE_DAYS,
  packagedDepthAgeDays,
} from "@/lib/nfl-depth-pack-freshness";

describe("nfl-depth-pack-freshness", () => {
  it("humanizes competition_status without snake_case", () => {
    expect(formatCompetitionStatus("open_competition")).toBe(
      "Open competition",
    );
    expect(formatCompetitionLabel("open_competition")).toBe("Open competition");
    expect(formatCompetitionStatus("named_starter")).toBe("Named starter");
    expect(formatCompetitionStatus("camp_arm")).toBe("Camp arm");
    expect(formatCompetitionStatus(null)).toBeNull();
    expect(formatCompetitionStatus("")).toBeNull();
  });

  it("humanizes competition tokens inside free-text reasons (API serialize)", () => {
    expect(
      humanizeCompetitionTokensInText(
        "open_competition Tua Tagovailoa, Michael Penix Jr. — no crown; mixture; wider uncertainty",
      ),
    ).toBe(
      "Open competition Tua Tagovailoa, Michael Penix Jr. — no crown; mixture; wider uncertainty",
    );
    expect(
      humanizeCompetitionTokensInText(
        "QB1 confirmed Aaron Rodgers (named_starter; confirmation=med)",
      ),
    ).toBe("QB1 confirmed Aaron Rodgers (Named starter; confirmation=med)");
    expect(humanizeCompetitionTokensInText("no status")).toBe("no status");
    expect(humanizeCompetitionTokensInText("")).toBe("");
  });

  it("maps competition-as-slot to order-based starter/backup labels", () => {
    expect(formatDepthSlotLabel("open_competition", 1)).toBe("starter");
    expect(formatDepthSlotLabel("open_competition", 2)).toBe("backup");
    expect(formatDepthSlotLabel("named_starter", 1)).toBe("starter");
    expect(formatDepthSlotLabel("starter", 1)).toBe("starter");
    expect(formatDepthSlotLabel("backup", 2)).toBe("backup");
  });

  it("formats Roster Pulse / intel depth_slot cells without snake_case", () => {
    expect(
      formatCompetitionAwareIntelCell("depth_slot", "open_competition"),
    ).toBe("Open competition");
    expect(
      formatCompetitionAwareIntelCell("competition_status", "open_competition"),
    ).toBe("Open competition");
    expect(formatCompetitionAwareIntelCell("depth_slot", "camp_arm")).toBe(
      "Camp arm",
    );
    expect(formatCompetitionAwareIntelCell("depth_slot", "starter")).toBe(
      "starter",
    );
    expect(formatCompetitionAwareIntelCell("player_name", "Tua")).toBeNull();
  });

  it("flags open races that must not read as locked crowns", () => {
    expect(competitionImpliesOpenRace("open_competition")).toBe(true);
    expect(competitionImpliesOpenRace("camp_arm")).toBe(true);
    expect(competitionImpliesOpenRace("named_starter")).toBe(false);
  });

  it("marks pack stale after max_age_days_camp_season", () => {
    const asOfDay = new Date(`${NFL_DEPTH_PACK_AS_OF}T12:00:00Z`);
    expect(isPackagedDepthStale(asOfDay)).toBe(false);
    expect(packagedDepthAgeDays(asOfDay)).toBe(0);

    const stillFresh = new Date(asOfDay);
    stillFresh.setUTCDate(
      stillFresh.getUTCDate() + NFL_DEPTH_PACK_MAX_AGE_DAYS,
    );
    expect(isPackagedDepthStale(stillFresh)).toBe(false);

    const stale = new Date(asOfDay);
    stale.setUTCDate(stale.getUTCDate() + NFL_DEPTH_PACK_MAX_AGE_DAYS + 1);
    expect(isPackagedDepthStale(stale)).toBe(true);

    // Live clock (2026-09-04 agent date) is past Aug 13 + 7.
    expect(isPackagedDepthStale(new Date("2026-09-04T12:00:00Z"))).toBe(true);
  });
});
