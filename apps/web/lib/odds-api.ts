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

/**
 * Allowed bookmaker keys (Odds API). Order = open preference + compare columns.
 * Matches model-service NFL_DEFAULT_ODDS_BOOKMAKERS (9 books).
 */
export const ALLOWED_BOOKS = [
  "draftkings",
  "fanduel",
  "betmgm",
  "betrivers",
  "hardrockbet",
  "fanatics",
  "bet365",
  "circa",
  "betr",
] as const;
/** NFL falls back to the full allowed set so Best Line / Best O/U span all 9 books. */
const NFL_DEFAULT_BOOKS = ALLOWED_BOOKS;

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
const MLB_CANONICAL_RUN_LINE_MAX = 2.5;

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

function parseConfiguredBooks(raw: string | undefined): string[] {
  const tokens = String(raw ?? "")
    .split(",")
    .map((token) => token.trim().toLowerCase())
    .filter(Boolean);
  const deduped = [...new Set(tokens)];
  return deduped.length > 0 ? deduped : [...NFL_DEFAULT_BOOKS];
}

export function configuredBooksForSport(sportKey: string): string[] {
  if (sportKey.toLowerCase() !== "nfl") {
    return [...ALLOWED_BOOKS];
  }
  const allowed = new Set(ALLOWED_BOOKS.map((book) => book.toLowerCase()));
  const configured = parseConfiguredBooks(process.env.ODDS_API_NFL_BOOKMAKERS);
  const filtered = configured.filter((book) => allowed.has(book));
  return filtered.length > 0 ? filtered : [...NFL_DEFAULT_BOOKS];
}

function filterBooksBySport<T extends { key?: string }>(
  items: T[],
  sportKey: string,
): T[] {
  const allowed = new Set(
    configuredBooksForSport(sportKey).map((book) => book.toLowerCase()),
  );
  return items.filter((b) => b.key && allowed.has(b.key.toLowerCase()));
}

function formatSignedPoint(point: number): string {
  const rounded = Math.round(point * 10) / 10;
  if (Object.is(rounded, -0)) return "+0";
  return rounded >= 0 ? `+${rounded}` : String(rounded);
}

function isCanonicalMlbRunLine(point: number): boolean {
  return Math.abs(point) <= MLB_CANONICAL_RUN_LINE_MAX;
}

function formatSpreadDisplay(
  point: number,
  sportKey: string,
  opts?: { markAlternate?: boolean },
): string {
  const signed = formatSignedPoint(point);
  if (
    sportKey.toLowerCase() === "mlb" &&
    !isCanonicalMlbRunLine(point) &&
    opts?.markAlternate
  ) {
    return `ALT ${signed}`;
  }
  return signed;
}

function parseAmericanPrice(raw: string | undefined | null): number | null {
  if (raw == null || raw === "") return null;
  const n = Number(String(raw).replace(/^\+/, ""));
  return Number.isFinite(n) ? n : null;
}

/** Higher American price is better for the bettor (+120 > -105 > -115). */
function americanOddsBetter(
  candidate: number | null,
  incumbent: number | null,
): boolean {
  if (candidate == null) return false;
  if (incumbent == null) return true;
  return candidate > incumbent;
}

type SpreadBookEntry = {
  book: string;
  line: string;
  point: number;
  canonical: boolean;
  juiceAway?: string;
  juiceHome?: string;
};

type TotalBookEntry = {
  book: string;
  line: string;
  point: number;
  juiceOver?: string;
  juiceUnder?: string;
};

/** Best away spread number across books; juice breaks ties. */
export function pickBestSpreadEntry(
  entries: SpreadBookEntry[],
): SpreadBookEntry | null {
  if (!entries.length) return null;
  return entries.reduce((best, cur) => {
    if (cur.point > best.point) return cur;
    if (cur.point < best.point) return best;
    return americanOddsBetter(
      parseAmericanPrice(cur.juiceAway),
      parseAmericanPrice(best.juiceAway),
    )
      ? cur
      : best;
  });
}

/**
 * Best O/U number for Over shopping = highest total across books;
 * better Over juice breaks ties. (Under shoppers still see that book's Under juice.)
 */
export function pickBestTotalEntry(
  entries: TotalBookEntry[],
): TotalBookEntry | null {
  if (!entries.length) return null;
  return entries.reduce((best, cur) => {
    if (cur.point > best.point) return cur;
    if (cur.point < best.point) return best;
    return americanOddsBetter(
      parseAmericanPrice(cur.juiceOver),
      parseAmericanPrice(best.juiceOver),
    )
      ? cur
      : best;
  });
}

function orderBooksByPreference<T extends { book: string }>(
  entries: T[],
  preferred: string[],
): T[] {
  const rank = new Map(preferred.map((key, i) => [key.toLowerCase(), i]));
  return [...entries].sort((a, b) => {
    const ra = rank.get(a.book.toLowerCase()) ?? 999;
    const rb = rank.get(b.book.toLowerCase()) ?? 999;
    return ra - rb;
  });
}

/** Fetch edge board rows for a sport. Only uses allowed books (filtered client-side). */
export async function fetchEdgeBoard(
  sportKey: string,
  apiKey: string,
): Promise<EdgeBoardRow[]> {
  const normalizedSport = sportKey.toLowerCase();
  const oddsSportKey = SPORT_KEY_MAP[normalizedSport];
  if (!oddsSportKey) return [];
  const isMlb = normalizedSport === "mlb";
  const sportBooks = configuredBooksForSport(normalizedSport);

  const url = `${ODDS_API_BASE}/sports/${oddsSportKey}/odds?regions=us,us2&markets=spreads,totals&oddsFormat=american&bookmakers=${encodeURIComponent(sportBooks.join(","))}&apiKey=${apiKey}`;
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

    const bookmakers = filterBooksBySport(ev.bookmakers ?? [], normalizedSport);

    const formatJuice = (price: number | undefined | null): string | undefined => {
      if (price == null || !Number.isFinite(price)) return undefined;
      const n = Math.round(price);
      return n > 0 ? `+${n}` : String(n);
    };

    const spreadData = bookmakers.flatMap((b) => {
      const m = b.markets?.find((x) => x.key === "spreads");
      if (!m) return [];
      const awayOutcome = m.outcomes?.find((o) => o.name === ev.away_team);
      const homeOutcome = m.outcomes?.find((o) => o.name === ev.home_team);
      if (!awayOutcome || awayOutcome.point == null) return [];
      const pt = awayOutcome.point;
      const canonical = !isMlb || isCanonicalMlbRunLine(pt);
      const line = formatSpreadDisplay(pt, normalizedSport, {
        markAlternate: isMlb && !canonical,
      });
      return [
        {
          book: b.key,
          line,
          point: pt,
          canonical,
          juiceAway: formatJuice(awayOutcome.price),
          juiceHome: formatJuice(homeOutcome?.price),
        },
      ];
    });
    const spreadPool = isMlb
      ? spreadData.filter((entry) => entry.canonical)
      : spreadData;
    const selectedSpreadData = orderBooksByPreference(
      spreadPool.length > 0 ? spreadPool : spreadData,
      sportBooks,
    );
    // Open = preferred book order (DraftKings first), not API response order.
    const openSpreadEntry = selectedSpreadData[0];
    const openSpread = openSpreadEntry?.line;
    // Best Line = best away number across all configured books (juice tiebreak).
    const bestSpreadEntry = pickBestSpreadEntry(selectedSpreadData);
    const bestSpread = bestSpreadEntry?.line ?? openSpread;
    const bestSpreadBookKey = bestSpreadEntry?.book;
    const bestSpreadBook = bestSpreadBookKey
      ? bookDisplay(bestSpreadBookKey)
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
      bookKey: bestSpreadBookKey,
      openJuice: openSpreadEntry?.juiceAway,
      openJuiceHome: openSpreadEntry?.juiceHome,
      bestJuice: bestSpreadEntry?.juiceAway ?? openSpreadEntry?.juiceAway,
      bestJuiceHome: bestSpreadEntry?.juiceHome ?? openSpreadEntry?.juiceHome,
    });

    const totalsData = bookmakers.flatMap((b) => {
      const m = b.markets?.find((x) => x.key === "totals");
      if (!m) return [];
      const over = m.outcomes?.find((o) => o.name === "Over");
      const under = m.outcomes?.find((o) => o.name === "Under");
      const point = over?.point ?? m.outcomes?.[0]?.point;
      if (point == null) return [];
      return [
        {
          book: b.key,
          line: String(point),
          point,
          juiceOver: formatJuice(over?.price),
          juiceUnder: formatJuice(under?.price),
        },
      ];
    });
    const orderedTotals = orderBooksByPreference(totalsData, sportBooks);
    const openTotalEntry = orderedTotals[0];
    const openTotal = openTotalEntry?.line;
    // Best O/U = highest total number across all configured books (Over juice tiebreak).
    const bestTotalEntry = pickBestTotalEntry(orderedTotals);
    const bestTotal = bestTotalEntry?.line ?? openTotal;
    const bestTotalBookKey = bestTotalEntry?.book;
    const bestTotalBook = bestTotalBookKey
      ? bookDisplay(bestTotalBookKey)
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
      bookKey: bestTotalBookKey,
      openJuice: openTotalEntry?.juiceOver,
      openJuiceHome: openTotalEntry?.juiceUnder,
      bestJuice: bestTotalEntry?.juiceOver ?? openTotalEntry?.juiceOver,
      bestJuiceHome: bestTotalEntry?.juiceUnder ?? openTotalEntry?.juiceUnder,
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

/** Raw odds comparison: game → market → book → line + juice. For odds comparison page. */
export type OddsComparisonRow = {
  id: string;
  game: string;
  time: string;
  commenceTime: string;
  spread: Record<
    string,
    {
      away: string;
      home: string;
      awayJuice?: string;
      homeJuice?: string;
      awayPoint?: number;
      homePoint?: number;
    }
  >;
  total: Record<
    string,
    {
      line: string;
      overJuice?: string;
      underJuice?: string;
      point?: number;
    }
  >;
  /** Book keys winning Best Line / Best O/U across the configured set. */
  bestSpreadBook?: string;
  bestTotalBook?: string;
};

export async function fetchOddsComparison(
  sportKey: string,
  apiKey: string,
): Promise<OddsComparisonRow[]> {
  const normalizedSport = sportKey.toLowerCase();
  const oddsSportKey = SPORT_KEY_MAP[normalizedSport];
  if (!oddsSportKey) return [];
  const isMlb = normalizedSport === "mlb";
  const sportBooks = configuredBooksForSport(normalizedSport);

  const url = `${ODDS_API_BASE}/sports/${oddsSportKey}/odds?regions=us,us2&markets=spreads,totals&oddsFormat=american&bookmakers=${encodeURIComponent(sportBooks.join(","))}&apiKey=${apiKey}`;
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

    const bookmakers = filterBooksBySport(ev.bookmakers ?? [], normalizedSport);
    const spread: OddsComparisonRow["spread"] = {};
    const total: OddsComparisonRow["total"] = {};
    const formatJuice = (price: number | undefined | null): string | undefined => {
      if (price == null || !Number.isFinite(price)) return undefined;
      const n = Math.round(price);
      return n > 0 ? `+${n}` : String(n);
    };

    const spreadEntries: SpreadBookEntry[] = [];
    const totalEntries: TotalBookEntry[] = [];

    for (const b of bookmakers) {
      const spreadM = b.markets?.find((x) => x.key === "spreads");
      if (spreadM) {
        const awayO = spreadM.outcomes?.find((o) => o.name === ev.away_team);
        const homeO = spreadM.outcomes?.find((o) => o.name === ev.home_team);
        if (awayO?.point != null && homeO?.point != null) {
          const awayAlt = isMlb && !isCanonicalMlbRunLine(awayO.point);
          const homeAlt = isMlb && !isCanonicalMlbRunLine(homeO.point);
          const awayS = formatSpreadDisplay(awayO.point, normalizedSport, {
            markAlternate: awayAlt,
          });
          const homeS = formatSpreadDisplay(homeO.point, normalizedSport, {
            markAlternate: homeAlt,
          });
          const awayJuice = formatJuice(awayO.price);
          const homeJuice = formatJuice(homeO.price);
          spread[b.key] = {
            away: awayS,
            home: homeS,
            awayJuice,
            homeJuice,
            awayPoint: awayO.point,
            homePoint: homeO.point,
          };
          spreadEntries.push({
            book: b.key,
            line: awayS,
            point: awayO.point,
            canonical: !isMlb || isCanonicalMlbRunLine(awayO.point),
            juiceAway: awayJuice,
            juiceHome: homeJuice,
          });
        }
      }
      const totalM = b.markets?.find((x) => x.key === "totals");
      if (totalM) {
        const over = totalM.outcomes?.find((o) => o.name === "Over");
        const under = totalM.outcomes?.find((o) => o.name === "Under");
        const pt = over?.point ?? totalM.outcomes?.[0]?.point;
        if (pt != null) {
          const overJuice = formatJuice(over?.price);
          const underJuice = formatJuice(under?.price);
          total[b.key] = {
            line: String(pt),
            overJuice,
            underJuice,
            point: pt,
          };
          totalEntries.push({
            book: b.key,
            line: String(pt),
            point: pt,
            juiceOver: overJuice,
            juiceUnder: underJuice,
          });
        }
      }
    }

    rows.push({
      id: ev.id,
      game,
      time: timeWithDate,
      commenceTime: ev.commence_time,
      spread,
      total,
      bestSpreadBook: pickBestSpreadEntry(spreadEntries)?.book,
      bestTotalBook: pickBestTotalEntry(totalEntries)?.book,
    });
  }

  return rows;
}
