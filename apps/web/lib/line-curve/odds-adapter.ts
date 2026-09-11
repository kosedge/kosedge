/**
 * Bind Odds API spreads + alternate_spreads onto a Line Curve snapshot.
 * Never invent a missing alt price. Never persist into odds_snapshots.
 */

import { isValidAmericanOdds } from "@/lib/american-odds";
import {
  ALLOWED_BOOKS,
  SPORT_KEY_MAP,
  type OddsBookmaker,
  type OddsEvent,
} from "@/lib/odds-api";
import { getOddsApiKeys } from "@/lib/odds-api-keys";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";
import { closed } from "@/lib/line-curve/guardrails";
import type {
  LineCurveClosed,
  LineCurveSport,
  OddsAltSnapshot,
  PostedAlt,
} from "@/lib/line-curve/types";

const ODDS_API_BASE = "https://api.the-odds-api.com/v4";

function snapshotId(eventId: string, book: string, capturedAt: string): string {
  return `${eventId}:${book}:${capturedAt}`;
}

function latestStamp(book: OddsBookmaker): string | null {
  const stamps = [
    book.last_update,
    ...(book.markets ?? []).map((m) => m.last_update),
  ].filter((s): s is string => Boolean(s && Number.isFinite(Date.parse(s))));
  if (!stamps.length) return null;
  return stamps.sort()[stamps.length - 1];
}

export function parseOddsEventSnapshot(args: {
  event: OddsEvent;
  book: string;
  sport: LineCurveSport;
  source?: OddsAltSnapshot["source"];
}): OddsAltSnapshot | LineCurveClosed {
  const bookKey = args.book.trim().toLowerCase();
  if (!(ALLOWED_BOOKS as readonly string[]).includes(bookKey)) {
    return closed("missing_odds", `Book ${bookKey} is not a designated book.`);
  }
  const booker = (args.event.bookmakers ?? []).find(
    (b) => b.key?.toLowerCase() === bookKey,
  );
  if (!booker) {
    return closed("missing_odds", `No ${bookKey} markets on this event.`);
  }
  const capturedAt = latestStamp(booker);
  if (!capturedAt) {
    return closed(
      "stale_odds",
      "Book/market last_update missing — refuse to mint as-of.",
    );
  }

  const spreads = (booker.markets ?? []).find((m) => m.key === "spreads");
  const alts = (booker.markets ?? []).find(
    (m) => m.key === "alternate_spreads",
  );
  if (!spreads?.outcomes?.length) {
    return closed("missing_odds", "Mainline spreads market is missing.");
  }
  if (!alts?.outcomes?.length) {
    return closed(
      "unavailable_alt_market",
      "alternate_spreads market is unavailable — no interpolation from mainline.",
    );
  }

  const baseLineBySide: Record<string, number> = {};
  const opposingBase: Record<string, number> = {};
  for (const o of spreads.outcomes) {
    if (!o.name || o.point == null || !isValidAmericanOdds(o.price ?? NaN)) {
      return closed(
        "inconsistent_odds",
        "Mainline spread outcome is incomplete.",
      );
    }
    baseLineBySide[o.name] = o.point;
    opposingBase[o.name] = o.price as number;
  }
  const names = Object.keys(baseLineBySide);
  if (names.length !== 2) {
    return closed(
      "inconsistent_odds",
      "Mainline spreads must have exactly two sides.",
    );
  }
  const [sideA, sideB] = names;
  if (Math.abs(baseLineBySide[sideA] + baseLineBySide[sideB]) > 1e-9) {
    return closed(
      "inconsistent_odds",
      "Mainline sides are not additive inverses.",
    );
  }

  const bySide: Record<string, PostedAlt[]> = {
    [sideA]: [],
    [sideB]: [],
  };

  for (const o of spreads.outcomes) {
    const opp = o.name === sideA ? opposingBase[sideB] : opposingBase[sideA];
    bySide[o.name].push({
      line: o.point as number,
      americanOdds: o.price as number,
      opposingAmericanOdds: opp ?? null,
    });
  }

  for (const o of alts?.outcomes ?? []) {
    if (!o.name || o.point == null || !isValidAmericanOdds(o.price ?? NaN)) {
      return closed(
        "inconsistent_odds",
        "Alternate spread outcome is incomplete.",
      );
    }
    if (!bySide[o.name]) bySide[o.name] = [];
    const oppName = o.name === sideA ? sideB : sideA;
    const opp = (alts?.outcomes ?? []).find(
      (x) => x.name === oppName && x.point === -(o.point as number),
    );
    bySide[o.name].push({
      line: o.point,
      americanOdds: o.price as number,
      opposingAmericanOdds: isValidAmericanOdds(opp?.price ?? NaN)
        ? (opp?.price as number)
        : null,
    });
  }

  return {
    eventId: args.event.id,
    sport: args.sport,
    book: bookKey,
    homeTeam: args.event.home_team,
    awayTeam: args.event.away_team,
    capturedAt,
    oddsSnapshotId: snapshotId(args.event.id, bookKey, capturedAt),
    source: args.source ?? "odds_api",
    baseLineBySide,
    altsBySide: bySide,
  };
}

export async function fetchAlternateSpreadSnapshot(args: {
  sport: LineCurveSport;
  eventId: string;
  book: string;
}): Promise<OddsAltSnapshot | LineCurveClosed> {
  if (args.sport !== "cfb" && args.sport !== "nfl") {
    return closed(
      "missing_odds",
      "Line Curve live fetch is limited to cfb and nfl.",
    );
  }
  const keys = getOddsApiKeys();
  if (!keys.length) {
    return closed("missing_odds", "Odds API key is not configured.");
  }
  const sportKey = SPORT_KEY_MAP[args.sport];
  if (!sportKey) {
    return closed("missing_odds", `Unsupported sport ${args.sport}.`);
  }
  const book = args.book.trim().toLowerCase();
  const regions =
    args.sport === "nfl" || args.sport === "cfb" ? "us,us2" : "us";
  const url =
    `${ODDS_API_BASE}/sports/${sportKey}/events/${encodeURIComponent(args.eventId)}` +
    `/odds?regions=${regions}&markets=spreads,alternate_spreads` +
    `&oddsFormat=american&bookmakers=${encodeURIComponent(book)}&apiKey=${keys[0]}`;
  const res = await upstreamFetch(url, {
    cache: "no-store",
    timeoutMs: UPSTREAM_TIMEOUT_MS.fast,
  });
  if (!res.ok) {
    return closed(
      "missing_odds",
      `Odds API ${res.status} fetching alternate spreads.`,
    );
  }
  const event = (await res.json()) as OddsEvent;
  if (!event?.id || !event.home_team) {
    return closed("missing_odds", "Odds API event payload is empty.");
  }
  return parseOddsEventSnapshot({
    event,
    book,
    sport: args.sport,
    source: "odds_api",
  });
}
