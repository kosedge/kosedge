import "server-only";
import { getOddsApiKeys } from "@/lib/odds-api-keys";
import { bookDisplay, configuredBooksForSport } from "@/lib/odds-api";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";
import { NFL_TEAM_DIRECTORY } from "@/lib/nfl-team-intel";
import { normalizeNflAbbr } from "@/lib/nfl-preseason-desk";

export type NflPreseasonMarketSnap = {
  homeAbbr: string;
  awayAbbr: string;
  commenceTime: string | null;
  marketSpreadHome: number | null;
  marketTotal: number | null;
  bestSpreadHome: number | null;
  bestTotal: number | null;
  bestSpreadBook: string | null;
  bestTotalBook: string | null;
  bookCount: number;
  source: "odds-api-preseason";
};

const ODDS_PRESEASON_KEY = "americanfootball_nfl_preseason";

const NAME_TO_ABBR = new Map(
  NFL_TEAM_DIRECTORY.map((team) => [team.name.toLowerCase(), team.code]),
);

function teamToAbbr(name: string): string | null {
  const direct = NAME_TO_ABBR.get(name.trim().toLowerCase());
  if (direct) return direct;
  // Soft contains match for Odds API naming drift.
  const lower = name.trim().toLowerCase();
  for (const team of NFL_TEAM_DIRECTORY) {
    const nick = team.name.split(" ").pop()?.toLowerCase() ?? "";
    if (nick && lower.endsWith(nick)) return team.code;
  }
  return null;
}

type OddsEvent = {
  commence_time?: string;
  home_team?: string;
  away_team?: string;
  bookmakers?: Array<{
    key?: string;
    markets?: Array<{
      key?: string;
      outcomes?: Array<{ name?: string; point?: number; price?: number }>;
    }>;
  }>;
};

function pickSpreadHome(
  event: OddsEvent,
  homeAbbr: string,
): { consensus: number | null; best: number | null; bestBook: string | null; books: number } {
  const homeName = event.home_team ?? "";
  const points: Array<{ point: number; book: string; price: number }> = [];
  for (const book of event.bookmakers ?? []) {
    const market = book.markets?.find((m) => m.key === "spreads");
    const home = market?.outcomes?.find((o) => o.name === homeName);
    if (home?.point == null || !Number.isFinite(home.point)) continue;
    points.push({
      point: home.point,
      book: book.key ?? "book",
      price: home.price ?? -110,
    });
  }
  if (points.length === 0) {
    return { consensus: null, best: null, bestBook: null, books: 0 };
  }
  // Best home number = highest home point (more pluses / fewer minuses for home).
  const best = [...points].sort((a, b) => {
    if (b.point !== a.point) return b.point - a.point;
    return a.price - b.price;
  })[0];
  const avg =
    points.reduce((sum, row) => sum + row.point, 0) / points.length;
  return {
    consensus: Math.round(avg * 2) / 2,
    best: best.point,
    bestBook: bookDisplay(best.book),
    books: points.length,
  };
}

function pickTotal(event: OddsEvent): {
  consensus: number | null;
  best: number | null;
  bestBook: string | null;
} {
  const overs: Array<{ point: number; book: string; price: number }> = [];
  for (const book of event.bookmakers ?? []) {
    const market = book.markets?.find((m) => m.key === "totals");
    const over = market?.outcomes?.find((o) =>
      String(o.name ?? "").toLowerCase().startsWith("over"),
    );
    if (over?.point == null || !Number.isFinite(over.point)) continue;
    overs.push({
      point: over.point,
      book: book.key ?? "book",
      price: over.price ?? -110,
    });
  }
  if (overs.length === 0) {
    return { consensus: null, best: null, bestBook: null };
  }
  const best = [...overs].sort((a, b) => {
    if (a.point !== b.point) return a.point - b.point; // lower total better for Over shoppers
    return a.price - b.price;
  })[0];
  const avg = overs.reduce((sum, row) => sum + row.point, 0) / overs.length;
  return {
    consensus: Math.round(avg * 2) / 2,
    best: best.point,
    bestBook: bookDisplay(best.book),
  };
}

/**
 * Pull The Odds API NFL preseason board when credentials work.
 * Returns empty on 401 / missing key / empty slate — callers keep ESPN.
 */
export async function fetchNflPreseasonOddsMarkets(): Promise<{
  byMatchup: Map<string, NflPreseasonMarketSnap>;
  status: "ok" | "empty" | "unauthorized" | "error" | "no_key";
  eventCount: number;
}> {
  const keys = getOddsApiKeys();
  if (keys.length === 0) {
    return { byMatchup: new Map(), status: "no_key", eventCount: 0 };
  }
  const books = configuredBooksForSport("nfl");
  const byMatchup = new Map<string, NflPreseasonMarketSnap>();
  let lastStatus: "ok" | "empty" | "unauthorized" | "error" = "empty";

  for (const apiKey of keys) {
    const url = new URL(
      `https://api.the-odds-api.com/v4/sports/${ODDS_PRESEASON_KEY}/odds`,
    );
    url.searchParams.set("regions", "us,us2");
    url.searchParams.set("markets", "h2h,spreads,totals");
    url.searchParams.set("oddsFormat", "american");
    url.searchParams.set("bookmakers", books.join(","));
    url.searchParams.set("apiKey", apiKey);

    try {
      const response = await upstreamFetch(url.toString(), {
        next: { revalidate: 900 },
        headers: { accept: "application/json" },
        timeoutMs: UPSTREAM_TIMEOUT_MS.fast,
      });
      if (response.status === 401 || response.status === 403) {
        lastStatus = "unauthorized";
        continue;
      }
      if (!response.ok) {
        lastStatus = "error";
        continue;
      }
      const events = (await response.json()) as OddsEvent[];
      if (!Array.isArray(events) || events.length === 0) {
        lastStatus = "empty";
        return { byMatchup, status: "empty", eventCount: 0 };
      }
      for (const event of events) {
        const homeAbbr = normalizeNflAbbr(teamToAbbr(event.home_team ?? "") ?? "");
        const awayAbbr = normalizeNflAbbr(teamToAbbr(event.away_team ?? "") ?? "");
        if (!homeAbbr || !awayAbbr) continue;
        const spread = pickSpreadHome(event, homeAbbr);
        const total = pickTotal(event);
        byMatchup.set(`${awayAbbr}@${homeAbbr}`, {
          homeAbbr,
          awayAbbr,
          commenceTime: event.commence_time ?? null,
          marketSpreadHome: spread.consensus,
          marketTotal: total.consensus,
          bestSpreadHome: spread.best,
          bestTotal: total.best,
          bestSpreadBook: spread.bestBook,
          bestTotalBook: total.bestBook,
          bookCount: spread.books,
          source: "odds-api-preseason",
        });
      }
      return {
        byMatchup,
        status: byMatchup.size > 0 ? "ok" : "empty",
        eventCount: events.length,
      };
    } catch {
      lastStatus = "error";
    }
  }

  return { byMatchup, status: lastStatus, eventCount: 0 };
}
