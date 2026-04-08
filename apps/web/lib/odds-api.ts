/**
 * Odds API (the-odds-api.com) fetcher.
 * Supports: NCAAM, NBA, NFL, MLB, NHL, CFB, WNBA.
 * Books: DraftKings, FanDuel, Circa, Hard Rock Bet, BetMGM, Bet365, Fanatics, BetRivers, Betr.
 */

import type { EdgeBoardRow } from "@kosedge/contracts";

const ODDS_API_BASE = "https://api.the-odds-api.com/v4";

/** Sport key (our app) → Odds API sport key */
export const SPORT_KEY_MAP: Record<string, string> = {
  ncaam: "basketball_ncaab",
  nba: "basketball_nba",
  nfl: "americanfootball_nfl",
  mlb: "baseball_mlb",
  nhl: "icehockey_nhl",
  cfb: "americanfootball_ncaaf",
  wnba: "basketball_wnba",
};

/** Allowed bookmaker keys (Odds API). Order preserved for display. */
export const ALLOWED_BOOKS = [
  "draftkings",
  "fanduel",
  "circa",
  "hardrockbet",
  "betmgm",
  "bet365",
  "fanatics",
  "betrivers",
  "betr",
] as const;

const BOOK_DISPLAY: Record<string, string> = {
  draftkings: "DraftKings",
  fanduel: "FanDuel",
  circa: "Circa",
  hardrockbet: "Hard Rock Bet",
  betmgm: "BetMGM",
  bet365: "Bet365",
  fanatics: "Fanatics",
  betrivers: "BetRivers",
  betr: "Betr",
};

export function bookDisplay(key: string): string {
  return BOOK_DISPLAY[key.toLowerCase()] ?? key;
}

type OddsEvent = {
  id: string;
  sport_key: string;
  commence_time: string;
  home_team: string;
  away_team: string;
  bookmakers?: {
    key: string;
    title: string;
    markets: {
      key: string;
      outcomes: Array<{ name: string; point?: number; price?: number }>;
    }[];
  }[];
};

/** Odds API commence_time is UTC. Format in Eastern (US sports standard). */
const ET = "America/New_York";

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    timeZone: ET,
    month: "2-digit",
    day: "2-digit",
  });
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", {
    timeZone: ET,
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

function filterBooks<T extends { key?: string }>(items: T[]): T[] {
  const allowed = new Set(ALLOWED_BOOKS.map((b) => b.toLowerCase()));
  return items.filter((b) => b.key && allowed.has(b.key.toLowerCase()));
}

/** Fetch edge board rows for a sport. Only uses allowed books (filtered client-side). */
export async function fetchEdgeBoard(
  sportKey: string,
  apiKey: string,
): Promise<EdgeBoardRow[]> {
  const oddsSportKey = SPORT_KEY_MAP[sportKey.toLowerCase()];
  if (!oddsSportKey) return [];

  const url = `${ODDS_API_BASE}/sports/${oddsSportKey}/odds?regions=us,us2&markets=spreads,totals&oddsFormat=american&apiKey=${apiKey}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Odds API ${res.status}: ${text.slice(0, 200)}`);
  }
  const events = (await res.json()) as OddsEvent[];

  const rows: EdgeBoardRow[] = [];
  const commenceTime = (e: OddsEvent) => new Date(e.commence_time).getTime();

  for (const ev of events.sort((a, b) => commenceTime(a) - commenceTime(b))) {
    const game = `${ev.away_team} @ ${ev.home_team}`;
    const date = formatDate(ev.commence_time);
    const time = formatTime(ev.commence_time);
    const timeWithDate = `${date} ${time} ET`;

    const bookmakers = filterBooks(ev.bookmakers ?? []);

    const spreadData = bookmakers.flatMap((b) => {
      const m = b.markets?.find((x) => x.key === "spreads");
      if (!m) return [];
      const awayOutcome = m.outcomes?.find((o) => o.name === ev.away_team);
      if (!awayOutcome || awayOutcome.point == null) return [];
      const pt = awayOutcome.point;
      const s = pt >= 0 ? `+${pt}` : String(pt);
      return [{ book: b.key, line: s, point: pt }];
    });
    const openSpread = spreadData[0]?.line;
    const bestSpreadEntry = spreadData.length
      ? spreadData.reduce((best, cur) => (cur.point > best.point ? cur : best))
      : null;
    const bestSpread = bestSpreadEntry?.line ?? openSpread;
    const bestSpreadBook = bestSpreadEntry
      ? bookDisplay(bestSpreadEntry.book)
      : undefined;

    rows.push({
      id: `${ev.id}-spread`,
      game,
      time: timeWithDate,
      commenceTime: ev.commence_time,
      market: "Spread",
      open: openSpread,
      best: bestSpread ?? openSpread,
      book: bestSpreadBook,
    });

    const totalsData = bookmakers.flatMap((b) => {
      const m = b.markets?.find((x) => x.key === "totals");
      if (!m) return [];
      const over = m.outcomes?.find((o) => o.name === "Over");
      const point = over?.point ?? m.outcomes?.[0]?.point;
      if (point == null) return [];
      return [{ book: b.key, line: String(point), point }];
    });
    const openTotal = totalsData[0]?.line;
    const bestTotalEntry = totalsData.length
      ? totalsData.reduce((best, cur) => (cur.point > best.point ? cur : best))
      : null;
    const bestTotal = bestTotalEntry?.line ?? openTotal;
    const bestTotalBook = bestTotalEntry
      ? bookDisplay(bestTotalEntry.book)
      : undefined;

    rows.push({
      id: `${ev.id}-total`,
      game,
      time: timeWithDate,
      commenceTime: ev.commence_time,
      market: "Total",
      open: openTotal,
      best: bestTotal ?? openTotal,
      book: bestTotalBook,
    });
  }

  return rows;
}

/** Legacy alias for NCAAM. */
export async function fetchNcaabEdgeBoard(
  apiKey: string,
): Promise<EdgeBoardRow[]> {
  return fetchEdgeBoard("ncaam", apiKey);
}

/** Raw odds comparison: game → market → book → line. For odds comparison page. */
export type OddsComparisonRow = {
  id: string;
  game: string;
  time: string;
  commenceTime: string;
  spread: Record<string, { away: string; home: string }>;
  total: Record<string, string>;
};

export async function fetchOddsComparison(
  sportKey: string,
  apiKey: string,
): Promise<OddsComparisonRow[]> {
  const oddsSportKey = SPORT_KEY_MAP[sportKey.toLowerCase()];
  if (!oddsSportKey) return [];

  const url = `${ODDS_API_BASE}/sports/${oddsSportKey}/odds?regions=us,us2&markets=spreads,totals&oddsFormat=american&apiKey=${apiKey}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Odds API ${res.status}: ${text.slice(0, 200)}`);
  }
  const events = (await res.json()) as OddsEvent[];

  const rows: OddsComparisonRow[] = [];
  const commenceTime = (e: OddsEvent) => new Date(e.commence_time).getTime();

  for (const ev of events.sort((a, b) => commenceTime(a) - commenceTime(b))) {
    const game = `${ev.away_team} @ ${ev.home_team}`;
    const date = formatDate(ev.commence_time);
    const time = formatTime(ev.commence_time);
    const timeWithDate = `${date} ${time} ET`;

    const bookmakers = filterBooks(ev.bookmakers ?? []);
    const spread: Record<string, { away: string; home: string }> = {};
    const total: Record<string, string> = {};

    for (const b of bookmakers) {
      const spreadM = b.markets?.find((x) => x.key === "spreads");
      if (spreadM) {
        const awayO = spreadM.outcomes?.find((o) => o.name === ev.away_team);
        const homeO = spreadM.outcomes?.find((o) => o.name === ev.home_team);
        if (awayO?.point != null && homeO?.point != null) {
          const awayS =
            awayO.point >= 0 ? `+${awayO.point}` : String(awayO.point);
          const homeS =
            homeO.point >= 0 ? `+${homeO.point}` : String(homeO.point);
          spread[b.key] = { away: awayS, home: homeS };
        }
      }
      const totalM = b.markets?.find((x) => x.key === "totals");
      if (totalM) {
        const over = totalM.outcomes?.find((o) => o.name === "Over");
        const pt = over?.point ?? totalM.outcomes?.[0]?.point;
        if (pt != null) total[b.key] = String(pt);
      }
    }

    rows.push({
      id: ev.id,
      game,
      time: timeWithDate,
      commenceTime: ev.commence_time,
      spread,
      total,
    });
  }

  return rows;
}
