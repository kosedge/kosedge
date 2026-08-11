import "server-only";
import { getOddsApiKeys } from "@/lib/odds-api-keys";
import { bookDisplay, configuredBooksForSport } from "@/lib/odds-api";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";
import { NFL_TEAM_DIRECTORY } from "@/lib/nfl-team-intel";
import { isValidAmericanOdds } from "@/lib/american-odds";
import type { PlayerFutureOddsSnap } from "@/lib/nfl-player-futures";
import type { NflAwardType } from "@/lib/nfl-awards";

/**
 * Best-effort futures odds for NFL desks.
 *
 * Odds API coverage today (2026-08-11): Super Bowl winner outrights only.
 * Player award / yardage / TD / reception leader futures are not in the API —
 * callers receive empty maps and UI shows "—".
 */

const SB_SPORT_KEY = "americanfootball_nfl_super_bowl_winner";

const NAME_TO_ABBR = new Map(
  NFL_TEAM_DIRECTORY.map((team) => [team.name.toLowerCase(), team.code]),
);

function teamToAbbr(name: string): string | null {
  const direct = NAME_TO_ABBR.get(name.trim().toLowerCase());
  if (direct) return direct;
  const lower = name.trim().toLowerCase();
  for (const team of NFL_TEAM_DIRECTORY) {
    const nick = team.name.split(" ").pop()?.toLowerCase() ?? "";
    if (nick && lower.endsWith(nick)) return team.code;
  }
  return null;
}

type OutrightEvent = {
  commence_time?: string;
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
): PlayerFutureOddsSnap | null {
  const valid = prices.filter((p) => isValidAmericanOdds(p.price));
  if (valid.length === 0) return null;
  // Best price for a future = highest American (most plus / least minus).
  valid.sort((a, b) => b.price - a.price);
  const best = valid[0];
  return {
    american: best.price,
    book: bookDisplay(best.book),
    asOfUtc: best.asOf,
  };
}

export type NflFuturesOddsBundle = {
  status: "ok" | "empty" | "unauthorized" | "error" | "no_key";
  asOfUtc: string | null;
  /** Team Super Bowl winner odds by abbr. */
  superBowlByTeam: Map<string, PlayerFutureOddsSnap>;
  /** Player award futures — always empty until Odds API adds markets. */
  awardByPlayer: Map<string, PlayerFutureOddsSnap>;
  /** Counting leader futures (yards/TDs/rec) — always empty until covered. */
  leaderByPlayer: Map<string, PlayerFutureOddsSnap>;
  note: string;
};

function emptyBundle(
  status: NflFuturesOddsBundle["status"],
  note: string,
): NflFuturesOddsBundle {
  return {
    status,
    asOfUtc: null,
    superBowlByTeam: new Map(),
    awardByPlayer: new Map(),
    leaderByPlayer: new Map(),
    note,
  };
}

async function fetchSuperBowlOutrights(): Promise<{
  byTeam: Map<string, PlayerFutureOddsSnap>;
  status: NflFuturesOddsBundle["status"];
  asOfUtc: string | null;
}> {
  const keys = getOddsApiKeys();
  if (keys.length === 0) {
    return { byTeam: new Map(), status: "no_key", asOfUtc: null };
  }
  const books = configuredBooksForSport("nfl");
  let lastStatus: NflFuturesOddsBundle["status"] = "empty";

  for (const apiKey of keys) {
    const url = new URL(
      `https://api.the-odds-api.com/v4/sports/${SB_SPORT_KEY}/odds`,
    );
    url.searchParams.set("regions", "us,us2");
    url.searchParams.set("markets", "outrights");
    url.searchParams.set("oddsFormat", "american");
    url.searchParams.set("bookmakers", books.join(","));
    url.searchParams.set("apiKey", apiKey);

    try {
      const response = await upstreamFetch(url.toString(), {
        next: { revalidate: 1800 },
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
      const events = (await response.json()) as OutrightEvent[];
      if (!Array.isArray(events) || events.length === 0) {
        return { byTeam: new Map(), status: "empty", asOfUtc: null };
      }

      const pricesByTeam = new Map<
        string,
        Array<{ price: number; book: string; asOf: string | null }>
      >();
      let latestAsOf: string | null = null;

      for (const event of events) {
        for (const book of event.bookmakers ?? []) {
          for (const market of book.markets ?? []) {
            if (market.key !== "outrights") continue;
            const asOf = market.last_update ?? book.last_update ?? null;
            if (asOf && (!latestAsOf || asOf > latestAsOf)) latestAsOf = asOf;
            for (const outcome of market.outcomes ?? []) {
              const abbr = teamToAbbr(outcome.name ?? "");
              const price = outcome.price;
              if (!abbr || price == null || !Number.isFinite(price)) continue;
              const list = pricesByTeam.get(abbr) ?? [];
              list.push({
                price,
                book: book.key ?? "book",
                asOf,
              });
              pricesByTeam.set(abbr, list);
            }
          }
        }
      }

      const byTeam = new Map<string, PlayerFutureOddsSnap>();
      for (const [abbr, prices] of pricesByTeam) {
        const best = pickBestAmerican(prices);
        if (best) byTeam.set(abbr, best);
      }
      return {
        byTeam,
        status: byTeam.size > 0 ? "ok" : "empty",
        asOfUtc: latestAsOf,
      };
    } catch {
      lastStatus = "error";
    }
  }

  return { byTeam: new Map(), status: lastStatus, asOfUtc: null };
}

/**
 * Load futures odds for desks. Player award/leader maps stay empty until
 * upstream covers those markets — UI must show "—".
 */
export async function loadNflFuturesOdds(): Promise<NflFuturesOddsBundle> {
  const sb = await fetchSuperBowlOutrights();
  const playerNote =
    "Player award / leader futures not in Odds API — Current odds show —.";
  if (sb.status === "ok") {
    return {
      status: "ok",
      asOfUtc: sb.asOfUtc,
      superBowlByTeam: sb.byTeam,
      awardByPlayer: new Map(),
      leaderByPlayer: new Map(),
      note: `SB winner odds joined (${sb.byTeam.size} teams). ${playerNote}`,
    };
  }
  return {
    ...emptyBundle(
      sb.status,
      sb.status === "no_key"
        ? `No Odds API key. ${playerNote}`
        : `SB winner odds unavailable (${sb.status}). ${playerNote}`,
    ),
    asOfUtc: sb.asOfUtc,
    superBowlByTeam: sb.byTeam,
  };
}

export function awardOddsForPlayer(
  bundle: NflFuturesOddsBundle,
  _award: NflAwardType,
  playerName: string,
): PlayerFutureOddsSnap | null {
  return bundle.awardByPlayer.get(playerName.toLowerCase()) ?? null;
}

export function leaderOddsForPlayer(
  bundle: NflFuturesOddsBundle,
  playerKey: string,
): PlayerFutureOddsSnap | null {
  return (
    bundle.leaderByPlayer.get(playerKey) ??
    bundle.leaderByPlayer.get(playerKey.toLowerCase()) ??
    null
  );
}

export function superBowlOddsForTeam(
  bundle: NflFuturesOddsBundle,
  team: string,
): PlayerFutureOddsSnap | null {
  return bundle.superBowlByTeam.get(team.toUpperCase()) ?? null;
}
