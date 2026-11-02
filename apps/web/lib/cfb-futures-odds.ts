import "server-only";

import { americanImpliedProb, isValidAmericanOdds } from "@/lib/american-odds";
import {
  type CfbFutureOddsSnap,
  formatCfbImpliedPct,
  formatCfbMarketOdds,
  formatCfbOddsAsOf,
} from "@/lib/cfb-futures-odds-format";
import { matchCfbFuturesTeamName } from "@/lib/cfb-futures-name-match";
import { bookDisplay, configuredBooksForSport } from "@/lib/odds-api";
import { getOddsApiKeys } from "@/lib/odds-api-keys";
import { oddsAcquire } from "@/lib/odds-acquire/acquire";
import { ODDS_API_HOST } from "@/lib/odds-acquire/hosts";
import { isPaidFetchDenied } from "@/lib/odds-acquire/errors";
import { UPSTREAM_TIMEOUT_MS } from "@/lib/upstream-fetch";

export type { CfbFutureOddsSnap };
export { formatCfbImpliedPct, formatCfbMarketOdds, formatCfbOddsAsOf };

/**
 * CFB futures market overlay (information only).
 *
 * Odds API coverage today (2026-08-17):
 *   americanfootball_ncaaf_championship_winner — National Championship outrights
 *   No CFP / make-playoff sport key
 *   No conference championship sport keys
 *
 * Missing markets stay empty. UI must show "—". Never rewrite sim %.
 */

export const CFB_NATTY_SPORT_KEY = "americanfootball_ncaaf_championship_winner";
export const CFB_FUTURES_ODDS_SOURCE = "The Odds API";
export const CFB_FUTURES_ODDS_REVALIDATE_SEC = 1800;

export type CfbFuturesOddsBundle = {
  status: "ok" | "empty" | "unauthorized" | "error" | "no_key" | "unavailable";
  source: string;
  sportKey: string;
  asOfUtc: string | null;
  /** National Championship winner — best American among configured books. */
  nattyByTeam: Map<string, CfbFutureOddsSnap>;
  /** CFP / playoff make — empty until Odds API adds a market. */
  cfpByTeam: Map<string, CfbFutureOddsSnap>;
  /** Conference champion — empty until Odds API adds a market. */
  confByTeam: Map<string, CfbFutureOddsSnap>;
  nattyMatched: number;
  nattyUnmatchedBookNames: string[];
  note: string;
  cfpNote: string;
  confNote: string;
};

type OutrightEvent = {
  bookmakers?: Array<{
    key?: string;
    last_update?: string;
    markets?: Array<{
      key?: string;
      last_update?: string;
      outcomes?: Array<{ name?: string; price?: number }>;
    }>;
  }>;
};

function pickBestAmerican(
  prices: Array<{ price: number; book: string; asOf: string | null }>,
): CfbFutureOddsSnap | null {
  const valid = prices.filter((p) => isValidAmericanOdds(p.price));
  if (valid.length === 0) return null;
  valid.sort((a, b) => b.price - a.price);
  const best = valid[0];
  const implied = americanImpliedProb(best.price);
  if (implied == null) return null;
  return {
    american: best.price,
    impliedPct: Math.round(implied * 1000) / 10,
    book: bookDisplay(best.book),
    asOfUtc: best.asOf,
  };
}

function emptyBundle(
  status: CfbFuturesOddsBundle["status"],
  note: string,
): CfbFuturesOddsBundle {
  return {
    status,
    source: status === "ok" ? CFB_FUTURES_ODDS_SOURCE : "unavailable",
    sportKey: CFB_NATTY_SPORT_KEY,
    asOfUtc: null,
    nattyByTeam: new Map(),
    cfpByTeam: new Map(),
    confByTeam: new Map(),
    nattyMatched: 0,
    nattyUnmatchedBookNames: [],
    note,
    cfpNote: "Odds API has no CFP / make-playoff outright. Market column is —.",
    confNote:
      "Odds API has no conference championship outright. Market column is —.",
  };
}

async function fetchNattyOutrights(): Promise<{
  byTeam: Map<string, CfbFutureOddsSnap>;
  unmatched: string[];
  status: CfbFuturesOddsBundle["status"];
  asOfUtc: string | null;
}> {
  const keys = getOddsApiKeys();
  if (keys.length === 0) {
    return {
      byTeam: new Map(),
      unmatched: [],
      status: "no_key",
      asOfUtc: null,
    };
  }
  const books = configuredBooksForSport("cfb");
  let lastStatus: CfbFuturesOddsBundle["status"] = "empty";

  for (const apiKey of keys) {
    const qs = new URLSearchParams({
      regions: "us,us2",
      markets: "outrights",
      oddsFormat: "american",
      bookmakers: books.join(","),
      apiKey,
    });

    try {
      const response = await oddsAcquire({
        host: ODDS_API_HOST,
        path: `/v4/sports/${CFB_NATTY_SPORT_KEY}/odds?${qs.toString()}`,
        caller: "loadCfbFuturesOdds",
        init: {
          headers: { accept: "application/json" },
          timeoutMs: UPSTREAM_TIMEOUT_MS.fast,
        },
      });
      if (response.status === 401 || response.status === 403) {
        lastStatus = "unauthorized";
        continue;
      }
      if (!response.ok) {
        lastStatus = "error";
        continue;
      }
      const events = (await response.json()) as OutrightEvent[];
      if (!Array.isArray(events) || events.length === 0) {
        return {
          byTeam: new Map(),
          unmatched: [],
          status: "empty",
          asOfUtc: null,
        };
      }

      const pricesByTeam = new Map<
        string,
        Array<{ price: number; book: string; asOf: string | null }>
      >();
      const unmatched = new Set<string>();
      let latestAsOf: string | null = null;

      for (const event of events) {
        for (const book of event.bookmakers ?? []) {
          for (const market of book.markets ?? []) {
            if (market.key !== "outrights") continue;
            const asOf = market.last_update ?? book.last_update ?? null;
            if (asOf && (!latestAsOf || asOf > latestAsOf)) latestAsOf = asOf;
            for (const outcome of market.outcomes ?? []) {
              const name = outcome.name ?? "";
              const code = matchCfbFuturesTeamName(name);
              const price = outcome.price;
              if (!code) {
                if (name) unmatched.add(name);
                continue;
              }
              if (price == null || !Number.isFinite(price)) continue;
              const list = pricesByTeam.get(code) ?? [];
              list.push({
                price,
                book: book.key ?? "book",
                asOf,
              });
              pricesByTeam.set(code, list);
            }
          }
        }
      }

      const byTeam = new Map<string, CfbFutureOddsSnap>();
      for (const [code, prices] of pricesByTeam) {
        const best = pickBestAmerican(prices);
        if (best) byTeam.set(code, best);
      }
      return {
        byTeam,
        unmatched: [...unmatched].sort(),
        status: byTeam.size > 0 ? "ok" : "empty",
        asOfUtc: latestAsOf,
      };
    } catch (err) {
      lastStatus = isPaidFetchDenied(err) ? "unavailable" : "error";
      if (isPaidFetchDenied(err)) break;
    }
  }

  return {
    byTeam: new Map(),
    unmatched: [],
    status: lastStatus,
    asOfUtc: null,
  };
}

export async function loadCfbFuturesOdds(): Promise<CfbFuturesOddsBundle> {
  const natty = await fetchNattyOutrights();
  const cfpNote =
    "Odds API has no CFP / make-playoff outright. Our CFP % is 12-team field (5 auto + 7 at-large), not a book make-playoff price. Market column is —.";
  const confNote =
    "Odds API has no conference championship outright. Market column is —.";

  if (natty.status === "ok") {
    return {
      status: "ok",
      source: CFB_FUTURES_ODDS_SOURCE,
      sportKey: CFB_NATTY_SPORT_KEY,
      asOfUtc: natty.asOfUtc,
      nattyByTeam: natty.byTeam,
      cfpByTeam: new Map(),
      confByTeam: new Map(),
      nattyMatched: natty.byTeam.size,
      nattyUnmatchedBookNames: natty.unmatched,
      note: `National Championship odds joined (${natty.byTeam.size} teams). Best American among configured books. Implied % is raw (juice in), not no-vig.`,
      cfpNote,
      confNote,
    };
  }

  return {
    ...emptyBundle(
      natty.status,
      natty.status === "no_key"
        ? "No Odds API key. National Championship market column is —."
        : "Market data unavailable / as-of. National Championship market column is —.",
    ),
    asOfUtc: natty.asOfUtc,
    nattyByTeam: natty.byTeam,
    nattyMatched: natty.byTeam.size,
    nattyUnmatchedBookNames: natty.unmatched,
    cfpNote,
    confNote,
  };
}

export function cfbNattyOddsForTeam(
  bundle: CfbFuturesOddsBundle,
  team: string,
): CfbFutureOddsSnap | null {
  return bundle.nattyByTeam.get(String(team || "").toUpperCase()) ?? null;
}

export function cfbCfpOddsForTeam(
  bundle: CfbFuturesOddsBundle,
  team: string,
): CfbFutureOddsSnap | null {
  return bundle.cfpByTeam.get(String(team || "").toUpperCase()) ?? null;
}

export function cfbConfOddsForTeam(
  bundle: CfbFuturesOddsBundle,
  team: string,
): CfbFutureOddsSnap | null {
  return bundle.confByTeam.get(String(team || "").toUpperCase()) ?? null;
}
