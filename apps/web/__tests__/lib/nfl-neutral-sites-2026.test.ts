import { describe, expect, it } from "vitest";
import {
  NFL_STANDARD_HFA_POINTS,
  lookupNflNeutralSite,
  resolveNflSiteContext,
} from "@/lib/nfl-neutral-sites-2026";

/**
 * 2026 international slate in away → home order.
 * Identity is season + exact week + that order. HFA stays 0 on these sites.
 */
const NEUTRAL_2026 = [
  {
    week: 1,
    awayAbbr: "SF",
    homeAbbr: "LAR",
    city: "Melbourne",
    venue: "Melbourne Cricket Ground",
  },
  {
    week: 3,
    awayAbbr: "BAL",
    homeAbbr: "DAL",
    city: "Rio de Janeiro",
    venue: "Maracanã Stadium",
  },
  {
    week: 4,
    awayAbbr: "IND",
    homeAbbr: "WAS",
    city: "London",
    venue: "Tottenham Hotspur Stadium",
  },
  {
    week: 5,
    awayAbbr: "PHI",
    homeAbbr: "JAX",
    city: "London",
    venue: "Tottenham Hotspur Stadium",
  },
  {
    week: 6,
    awayAbbr: "HOU",
    homeAbbr: "JAX",
    city: "London",
    venue: "Wembley Stadium",
  },
  {
    week: 7,
    awayAbbr: "PIT",
    homeAbbr: "NO",
    city: "Paris",
    venue: "Stade de France",
  },
  {
    week: 9,
    awayAbbr: "CIN",
    homeAbbr: "ATL",
    city: "Madrid",
    venue: "Bernabéu Stadium",
  },
  {
    week: 10,
    awayAbbr: "NE",
    homeAbbr: "DET",
    city: "Munich",
    venue: "FC Bayern Munich Arena",
  },
  {
    week: 11,
    awayAbbr: "MIN",
    homeAbbr: "SF",
    city: "Mexico City",
    venue: "Estadio Banorte",
  },
] as const;

const HOME_CONTEXT = {
  isNeutral: false,
  city: null,
  venue: null,
  hfaPoints: NFL_STANDARD_HFA_POINTS,
  siteLabel: "Home",
} as const;

const UNKNOWN_CONTEXT = {
  isNeutral: false,
  city: null,
  venue: null,
  hfaPoints: null,
  siteLabel: "UNKNOWN",
} as const;

function lookup(args: {
  season?: number | null;
  week?: number | null;
  homeAbbr: string;
  awayAbbr: string;
}) {
  return lookupNflNeutralSite({
    season: args.season,
    week: args.week,
    homeAbbr: args.homeAbbr,
    awayAbbr: args.awayAbbr,
  });
}

describe("2026 NFL neutral-site identity", () => {
  it("T01 identifies each slate game by season, exact week, and ordered home/away", () => {
    expect(NFL_STANDARD_HFA_POINTS).toBe(1.05);
    for (const game of NEUTRAL_2026) {
      const site = lookup({ season: 2026, ...game });
      expect(site).toMatchObject({
        week: game.week,
        city: game.city,
        venue: game.venue,
        hfaPoints: 0,
      });
      expect(
        resolveNflSiteContext({ season: 2026, ...game }),
      ).toMatchObject({
        isNeutral: true,
        city: game.city,
        venue: game.venue,
        hfaPoints: 0,
        siteLabel: "Neutral",
      });
    }
  });

  it("T02 classifies SF@LAR Week 2 and the two return legs as Home with standard HFA", () => {
    const games = [
      { week: 2, awayAbbr: "SF", homeAbbr: "LAR" },
      { week: 14, awayAbbr: "LAR", homeAbbr: "SF" },
      { week: 15, awayAbbr: "JAX", homeAbbr: "HOU" },
    ] as const;
    for (const game of games) {
      expect(lookup({ season: 2026, ...game })).toBeNull();
      expect(resolveNflSiteContext({ season: 2026, ...game })).toEqual(
        HOME_CONTEXT,
      );
    }
  });

  it("CTRL-accepts the existing LA and WSH aliases only in the stored orientation", () => {
    expect(
      lookup({ season: 2026, week: 1, awayAbbr: "SF", homeAbbr: "LA" }),
    ).toMatchObject({ city: "Melbourne", venue: "Melbourne Cricket Ground" });
    expect(
      lookup({ season: 2026, week: 4, awayAbbr: "IND", homeAbbr: "WSH" }),
    ).toMatchObject({ city: "London", venue: "Tottenham Hotspur Stadium" });
    expect(
      lookup({ season: 2026, week: 1, awayAbbr: "sf", homeAbbr: "lar" }),
    ).toMatchObject({ city: "Melbourne" });
  });

  it("CTRL-does not treat a fully identified non-slate game as neutral", () => {
    expect(
      lookup({ season: 2026, week: 1, awayAbbr: "ARI", homeAbbr: "LAC" }),
    ).toBeNull();
    expect(
      resolveNflSiteContext({
        season: 2026,
        week: 1,
        awayAbbr: "ARI",
        homeAbbr: "LAC",
      }),
    ).toEqual(HOME_CONTEXT);
  });

  it("CTRL-fails closed as UNKNOWN for a foreign season or an incomplete identity", () => {
    expect(
      lookup({ season: 2025, week: 1, awayAbbr: "SF", homeAbbr: "LAR" }),
    ).toBeNull();
    expect(
      resolveNflSiteContext({
        season: 2025,
        week: 1,
        awayAbbr: "SF",
        homeAbbr: "LAR",
      }),
    ).toEqual(UNKNOWN_CONTEXT);
    expect(
      lookup({ season: 2026, week: null, awayAbbr: "SF", homeAbbr: "LAR" }),
    ).toBeNull();
    expect(
      resolveNflSiteContext({
        season: 2026,
        week: 1,
        awayAbbr: "",
        homeAbbr: "LAR",
      }),
    ).toEqual(UNKNOWN_CONTEXT);
  });

  it("T05 rejects season 2027 for every slate pair and weeks 19-22 for MIN at SF", () => {
    for (const game of NEUTRAL_2026) {
      expect(
        lookup({
          season: 2027,
          week: game.week,
          awayAbbr: game.awayAbbr,
          homeAbbr: game.homeAbbr,
        }),
      ).toBeNull();
      expect(
        resolveNflSiteContext({
          season: 2027,
          week: game.week,
          awayAbbr: game.awayAbbr,
          homeAbbr: game.homeAbbr,
        }),
      ).toEqual(UNKNOWN_CONTEXT);
    }
    for (const week of [19, 20, 21, 22]) {
      expect(
        lookup({ season: 2026, week, awayAbbr: "MIN", homeAbbr: "SF" }),
      ).toBeNull();
      const resolved = resolveNflSiteContext({
        season: 2026,
        week,
        awayAbbr: "MIN",
        homeAbbr: "SF",
      });
      expect(resolved.isNeutral).toBe(false);
      expect(resolved.siteLabel).not.toBe("Neutral");
      expect(resolved).toEqual(HOME_CONTEXT);
    }
  });

  it("T06 ignores an upstream stamp unless the call exactly matches a 2026 table identity", () => {
    const cases = [
      {
        season: 2025,
        week: 1,
        awayAbbr: "SF",
        homeAbbr: "LAR",
        neutralSite: true,
        neutralCity: "London",
      },
      {
        season: 2026,
        week: 2,
        awayAbbr: "SF",
        homeAbbr: "LAR",
        neutralSite: true,
      },
      {
        season: 2026,
        week: 8,
        awayAbbr: "HOU",
        homeAbbr: "JAX",
        neutralCity: "London",
      },
      {
        season: 2026,
        week: 1,
        awayAbbr: "ARI",
        homeAbbr: "LAC",
        neutralSite: true,
        neutralCity: "London",
      },
    ] as const;
    for (const stamped of cases) {
      const { neutralSite: _site, neutralCity: _city, ...plain } = stamped;
      const without = resolveNflSiteContext(plain);
      const withStamp = resolveNflSiteContext(stamped);
      expect(withStamp).toEqual(without);
      expect(withStamp.isNeutral).toBe(false);
      expect(withStamp.siteLabel).not.toBe("Neutral");
    }
  });

  it("T13-NS fails closed as UNKNOWN when season is null", () => {
    expect(
      lookup({ season: null, week: 1, awayAbbr: "SF", homeAbbr: "LAR" }),
    ).toBeNull();
    expect(lookup({ week: 1, awayAbbr: "SF", homeAbbr: "LAR" })).toBeNull();
    expect(
      resolveNflSiteContext({
        season: null,
        week: 1,
        awayAbbr: "SF",
        homeAbbr: "LAR",
      }),
    ).toEqual(UNKNOWN_CONTEXT);
    expect(
      resolveNflSiteContext({
        week: 1,
        awayAbbr: "SF",
        homeAbbr: "LAR",
      }),
    ).toEqual(UNKNOWN_CONTEXT);
  });

  it("T14-NS classifies reversed neutral-site pairs at finite weeks as Home with standard HFA", () => {
    for (const game of NEUTRAL_2026) {
      expect(
        lookup({
          season: 2026,
          week: game.week,
          awayAbbr: game.homeAbbr,
          homeAbbr: game.awayAbbr,
        }),
      ).toBeNull();
      expect(
        resolveNflSiteContext({
          season: 2026,
          week: game.week,
          awayAbbr: game.homeAbbr,
          homeAbbr: game.awayAbbr,
        }),
      ).toEqual(HOME_CONTEXT);
    }
  });

  it("T09-INT does not identify a non-integer week", () => {
    expect(
      lookup({ season: 2026, week: 1.7, awayAbbr: "SF", homeAbbr: "LAR" }),
    ).toBeNull();
    const resolved = resolveNflSiteContext({
      season: 2026,
      week: 1.7,
      awayAbbr: "SF",
      homeAbbr: "LAR",
    });
    expect(resolved.isNeutral).toBe(false);
    expect(resolved.siteLabel).not.toBe("Neutral");
  });
});
