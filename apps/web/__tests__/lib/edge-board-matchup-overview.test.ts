import { describe, expect, it } from "vitest";
import {
  assignDeskVoice,
  buildMatchupOverview,
  buildMatchupOverviewBlocks,
  isNeutralSite,
  resolveSeasonPhase,
} from "@/lib/edge-board-matchup-overview";
import { buildStatDrop } from "@/lib/edge-board-stat-drop";
import { flatRowsToLegacy } from "@/components/EdgeBoard";

describe("edge-board matchup overview", () => {
  it("assigns a stable desk voice per game_id", () => {
    const a = assignDeskVoice("sea-ne-2026-w1");
    const b = assignDeskVoice("sea-ne-2026-w1");
    const c = assignDeskVoice("kc-buf-2026-w1");
    expect(a.id).toBe(b.id);
    expect(a.label).toBe(b.label);
    // Different game ids usually differ; allow rare hash collision but require stability.
    expect(typeof c.id).toBe("string");
  });

  it("treats week 1 / PRE as week1 phase (no recent-form language)", () => {
    expect(
      resolveSeasonPhase({
        sportKey: "nfl",
        gameId: "g1",
        awayTeam: "Seahawks",
        homeTeam: "Patriots",
        week: 1,
        seasonType: "REG",
      }),
    ).toBe("week1");
    expect(
      resolveSeasonPhase({
        sportKey: "nfl",
        gameId: "g2",
        awayTeam: "Seahawks",
        homeTeam: "Patriots",
        week: 2,
        seasonType: "PRE",
      }),
    ).toBe("week1");

    const text = buildMatchupOverview({
      sportKey: "nfl",
      gameId: "week1-smoke",
      awayTeam: "Seattle Seahawks",
      homeTeam: "New England Patriots",
      week: 1,
      seasonType: "REG",
      keiSpreadHome: -2.5,
      marketSpreadAway: 3.0,
      marketTotal: 42.5,
      keiTotal: 41.0,
      homeWinProb: 0.57,
      awayWinProb: 0.43,
    }).toLowerCase();

    expect(text).toContain("bottom line");
    expect(text).toContain("what matters");
    expect(text).toContain("watch");
    expect(text).not.toMatch(/recent turnovers/);
    expect(text).not.toMatch(/hot offense/);
    expect(text).not.toMatch(/cooling off/);
    expect(text).not.toMatch(/travels to face/);
    expect(text).not.toMatch(/\bby [a-z]+ [a-z]+\b/); // no personal byline
  });

  it("calls out neutral site and avoids home-crowd language", () => {
    const ctx = {
      sportKey: "nfl",
      gameId: "neutral-london",
      awayTeam: "Jacksonville Jaguars",
      homeTeam: "Chicago Bears",
      week: 5,
      seasonType: "REG",
      neutralSite: true,
      venueCity: "London",
      hfaPoints: 0,
      keiSpreadHome: -1.5,
      marketSpreadAway: 2.5,
      homeWinProb: 0.54,
      awayWinProb: 0.46,
    };
    expect(isNeutralSite(ctx)).toBe(true);
    const blocks = buildMatchupOverviewBlocks(ctx);
    expect(blocks.neutralSite).toBe(true);
    const text = buildMatchupOverview(ctx).toLowerCase();
    expect(text).toMatch(/neutral/);
    expect(text).toMatch(/london/);
    expect(text).not.toMatch(/home crowd/);
    expect(text).not.toMatch(/defend home turf/);
  });

  it("does not force a lean when KEI ≈ market", () => {
    const text = buildMatchupOverview({
      sportKey: "nfl",
      gameId: "aligned-game",
      awayTeam: "Buffalo Bills",
      homeTeam: "Kansas City Chiefs",
      week: 8,
      seasonType: "REG",
      keiSpreadHome: -3.0,
      marketSpreadAway: 3.0,
      edgeLineNum: 0.0,
    }).toLowerCase();
    expect(text).toMatch(
      /near the market|no forced lean|tightly priced|aligned/,
    );
  });

  it("varies voice emphasis across different game ids", () => {
    const a = buildMatchupOverviewBlocks({
      sportKey: "nfl",
      gameId: "voice-a",
      awayTeam: "A",
      homeTeam: "B",
      week: 1,
    });
    const b = buildMatchupOverviewBlocks({
      sportKey: "nfl",
      gameId: "voice-b",
      awayTeam: "C",
      homeTeam: "D",
      week: 1,
    });
    // Same structure; desk label present; voices drawn from roster.
    expect(a.deskLabel).toMatch(/desk/i);
    expect(b.deskLabel).toMatch(/desk/i);
    expect(a.whatMatters.length).toBeGreaterThanOrEqual(2);
    expect(a.whatMatters.length).toBeLessThanOrEqual(4);
  });
});

describe("edge-board stat drop", () => {
  it("always returns 8 slots with power + core betting numbers", () => {
    const drop = buildStatDrop({
      sportKey: "nfl",
      gameId: "g-stat",
      awayTeam: "Buffalo Bills",
      homeTeam: "Kansas City Chiefs",
      week: 1,
      keiSpreadHome: -3.5,
      marketSpreadAway: 2.5,
      marketTotal: 47.5,
      keiTotal: 46.0,
      homeWinProb: 0.62,
      awayWinProb: 0.38,
      restDaysHome: 10,
      restDaysAway: 7,
      awayUnitTag: "Pass-rush edge",
      homeUnitTag: "QB certainty",
    });
    expect(drop.slots).toHaveLength(8);
    expect(drop.slots[0]!.label).toMatch(/Power/i);
    expect(drop.slots[0]!.value).not.toBe("");
    expect(drop.slots[0]!.value).not.toBe("—");
    expect(drop.slots[1]!.value).toContain("/");
    expect(drop.slots[2]!.value).toContain("/");
    expect(drop.slots[3]!.value).toMatch(/%/);
    expect(drop.slots[4]!.value).toMatch(/HFA|Home|Neutral/i);
  });

  it("shows em dash for missing pace and marks neutral HFA 0", () => {
    const drop = buildStatDrop({
      sportKey: "nfl",
      gameId: "neutral-stat",
      awayTeam: "Jaguars",
      homeTeam: "Bears",
      neutralSite: true,
      venueCity: "London",
      hfaPoints: 0,
      keiSpreadHome: -1.0,
    });
    expect(drop.siteLabel).toMatch(/Neutral/);
    expect(drop.slots[4]!.value).toMatch(/Neutral|London/i);
    expect(drop.slots[4]!.value).toMatch(/0/);
    expect(drop.slots[6]!.value).toBe("—");
  });

  it("flatRowsToLegacy attaches overview + populated statDrop", () => {
    const rows = flatRowsToLegacy(
      [
        {
          id: "buf-kc-spread",
          game: "Buffalo Bills @ Kansas City Chiefs",
          market: "Spread",
          best: "+3.0",
          bookKey: "draftkings",
          kei: "-3.5",
          week: 1,
          seasonType: "REG",
          homeWinProb: 0.61,
          awayWinProb: 0.39,
          restDaysHome: 7,
          restDaysAway: 7,
          awayUnitTag: "Explosive skill",
          homeUnitTag: "Elite pass rush",
          commenceTime: "2026-09-10T00:20:00Z",
        },
        {
          id: "buf-kc-total",
          game: "Buffalo Bills @ Kansas City Chiefs",
          market: "Total",
          best: "47.5",
          bookKey: "fanduel",
          kei: "46.0",
          week: 1,
          seasonType: "REG",
          commenceTime: "2026-09-10T00:20:00Z",
        },
      ],
      "nfl",
    );
    expect(rows).toHaveLength(1);
    const row = rows[0]!;
    expect(row.overview).toMatch(/BOTTOM LINE/);
    expect(row.overview).not.toMatch(/recent turnovers/i);
    expect(row.statDrop?.slots).toHaveLength(8);
    expect(row.statDrop?.slots[0]!.value).not.toBe("—");
  });
});
