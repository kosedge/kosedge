/**
 * Odds API (the-odds-api.com) fetcher for NCAAB.
 * Free tier: 500 credits/month. Costs 3 per call (spreads + totals + regions=us).
 */

import type { EdgeBoardRow } from "@kosedge/contracts";

const ODDS_API_BASE = "https://api.the-odds-api.com/v4";

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

const BOOK_DISPLAY: Record<string, string> = {
  draftkings: "DK",
  fanduel: "FD",
  betmgm: "MGM",
  caesars: "Caesars",
  betrivers: "BetRivers",
  barstool: "Barstool",
  pointsbetus: "PointsBet",
  williamhill_us: "William Hill",
  bovada: "Bovada",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${m}/${day}`;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

function bookDisplay(key: string): string {
  return BOOK_DISPLAY[key.toLowerCase()] ?? key.slice(0, 2).toUpperCase();
}

export async function fetchNcaabEdgeBoard(apiKey: string): Promise<EdgeBoardRow[]> {
  const url = `${ODDS_API_BASE}/sports/basketball_ncaab/odds?regions=us&markets=spreads,totals&oddsFormat=american&apiKey=${apiKey}`;
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
    const timeWithDate = `${date} ${time}`;

    const bookmakers = ev.bookmakers ?? [];

    // Spread (use away team's spread; best = most favorable for away bettor)
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
    const bestSpreadBook = bestSpreadEntry ? bookDisplay(bestSpreadEntry.book) : undefined;

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

    // Totals (O/U) – best = highest total (best for Over) as common proxy
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
    const bestTotalBook = bestTotalEntry ? bookDisplay(bestTotalEntry.book) : undefined;

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
