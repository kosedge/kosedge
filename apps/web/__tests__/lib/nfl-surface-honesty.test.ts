import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  NFL_AWARDS_SOURCE_NAME,
  NFL_AWARDS_SOURCE_STAMP,
  NFL_DEPTH_NOT_LIVE_CAMP_PHRASE,
  NFL_DEPTH_SOURCE_NAME,
  NFL_DEPTH_SOURCE_STAMP,
  NFL_FUTURES_SOURCE_NAME,
  NFL_FUTURES_SOURCE_STAMP,
} from "@/lib/nfl-surface-honesty";

const webRoot = path.join(__dirname, "../..");

function readRel(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

/** Engineering jargon that must not appear in subscriber-facing stamps. */
const ENGINEERING_NOTE =
  /silently reconciled|do not invent a merge|combined ranking|live roster SoT/i;

describe("NFL awards vs futures source stamps", () => {
  it("exports distinct source names in subscriber English", () => {
    expect(NFL_AWARDS_SOURCE_NAME).toMatch(/award-score/i);
    expect(NFL_FUTURES_SOURCE_NAME).toMatch(/player-production|season sim/i);
    expect(NFL_AWARDS_SOURCE_STAMP).toMatch(/Source:/i);
    expect(NFL_AWARDS_SOURCE_STAMP).toMatch(/last materialize/i);
    expect(NFL_AWARDS_SOURCE_STAMP).toMatch(/Separate from Futures/i);
    expect(NFL_AWARDS_SOURCE_STAMP).toMatch(/different ranking/i);
    expect(NFL_AWARDS_SOURCE_STAMP).toMatch(/odds not joined/i);
    expect(NFL_AWARDS_SOURCE_STAMP).not.toMatch(ENGINEERING_NOTE);
    expect(NFL_FUTURES_SOURCE_STAMP).toMatch(/Source:/i);
    expect(NFL_FUTURES_SOURCE_STAMP).toMatch(/Separate from Awards/i);
    expect(NFL_FUTURES_SOURCE_STAMP).toMatch(/Leader odds not joined/i);
    expect(NFL_FUTURES_SOURCE_STAMP).not.toMatch(ENGINEERING_NOTE);
    expect(NFL_AWARDS_SOURCE_STAMP).not.toEqual(NFL_FUTURES_SOURCE_STAMP);
  });

  it("awards and futures pages stamp their own source labels", () => {
    const awards = readRel("app/(pro)/pro/nfl/awards/page.tsx");
    const futures = readRel("app/(pro)/pro/nfl/projections/page.tsx");

    expect(awards).toContain("NFL_AWARDS_SOURCE_STAMP");
    expect(awards).toContain('data-testid="nfl-awards-source-stamp"');
    expect(awards).toContain("/pro/nfl/projections");
    expect(awards).not.toMatch(ENGINEERING_NOTE);

    expect(futures).toContain("NFL_FUTURES_SOURCE_STAMP");
    expect(futures).toContain('data-testid="nfl-futures-source-stamp"');
    expect(futures).toContain("/pro/nfl/awards");
    expect(futures).not.toMatch(ENGINEERING_NOTE);
  });
});

describe("NFL depth charts are not claimed as live camp", () => {
  it("labels packaged model depth — not live Camp Desk", () => {
    expect(NFL_DEPTH_SOURCE_NAME).toMatch(/packaged|model/i);
    expect(NFL_DEPTH_SOURCE_STAMP).toMatch(/Source:/i);
    expect(NFL_DEPTH_SOURCE_STAMP).toContain(NFL_DEPTH_NOT_LIVE_CAMP_PHRASE);
    expect(NFL_DEPTH_SOURCE_STAMP).toMatch(/Named QB1, IR, and claims/i);
    expect(NFL_DEPTH_SOURCE_STAMP).toMatch(/Camp Desk/i);
    expect(NFL_DEPTH_SOURCE_STAMP).not.toMatch(ENGINEERING_NOTE);
  });

  it("depth surfaces keep the chart visible with a not-live-camp stamp", () => {
    const league = readRel("app/(pro)/pro/[sport]/depth-charts/page.tsx");
    const teamHub = readRel("app/(pro)/pro/nfl/teams/[team]/[view]/page.tsx");
    const intel = readRel("components/pro/NflIntelTablePage.tsx");

    expect(league).toContain("NFL_DEPTH_SOURCE_STAMP");
    expect(league).toContain('sourceHonestyTestId="nfl-depth-source-stamp"');
    expect(league).toContain('campHref="/pro/nfl/camp"');
    expect(league).not.toMatch(/hidden|coming soon|paywall/i);

    expect(teamHub).toContain("NFL_DEPTH_SOURCE_STAMP");
    expect(teamHub).toContain('data-testid="nfl-depth-source-stamp"');
    expect(teamHub).toContain("DepthChartRenderer");
    expect(teamHub).toContain("/pro/nfl/camp");
    expect(teamHub).not.toMatch(/live roster SoT/i);

    expect(intel).toContain("sourceHonesty");
    expect(intel).not.toMatch(/live roster SoT/i);
    expect(intel).not.toMatch(/return null.*depth|hide.*depth/i);
  });
});
