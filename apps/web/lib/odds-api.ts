/**
 * Odds API (the-odds-api.com) fetcher.
 * Supports: NCAAM, NBA, NFL, MLB, NHL, CFB, WNBA.
 * Designated books: DraftKings, FanDuel, BetMGM, BetRivers, Hard Rock Bet,
 * Fanatics, Bovada, Caesars, BetOnline, Bet365, Circa, Betr — see NFL feed coverage below.
 */

import type { EdgeBoardRow } from "@kosedge/contracts";

import { americanImpliedProb, noVigHomeProb } from "@/lib/american-odds";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";

export { americanImpliedProb, noVigHomeProb };

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
 * Designated Compare Odds columns (Ryan). Order = open preference + compare columns.
 * Matches model-service NFL_DEFAULT_ODDS_BOOKMAKERS (12 books). Keep all twelve —
 * do not silently drop columns the provider cannot supply.
 */
export const ALLOWED_BOOKS = [
  "draftkings",
  "fanduel",
  "betmgm",
  "betrivers",
  "hardrockbet",
  "fanatics",
  "bovada",
  "williamhill_us",
  "betonlineag",
  "bet365",
  "circa",
  "betr",
] as const;

/**
 * Keys The Odds API actually carries for NFL in us/us2.
 * hardrockbet = us2; fanatics = us (paid). Request only these — never invent lines.
 */
export const NFL_ODDS_API_CARRIED_BOOKS = [
  "draftkings",
  "fanduel",
  "betmgm",
  "betrivers",
  "hardrockbet",
  "fanatics",
  "bovada",
  "williamhill_us",
  "betonlineag",
] as const;

/**
 * Designated columns with no NFL Odds API key in us/us2.
 * bet365 → only bet365_au (AU; AFL/NRL). circa → not on feed any region.
 * betr → only betr_au (AU).
 */
export const NFL_ODDS_API_NOT_CARRIED_BOOKS = [
  "bet365",
  "circa",
  "betr",
] as const;

/** hardrockbet is us2; fanatics paid us — always send both regions for NFL. */
export const NFL_ODDS_REGIONS = "us,us2";

export type BookFeedStatus = "carried" | "not_carried";

const NFL_DEFAULT_BOOKS = ALLOWED_BOOKS;
const NFL_CARRIED_SET = new Set<string>(NFL_ODDS_API_CARRIED_BOOKS);
const NFL_NOT_CARRIED_SET = new Set<string>(NFL_ODDS_API_NOT_CARRIED_BOOKS);

export function nflBookFeedStatus(bookKey: string): BookFeedStatus {
  const key = bookKey.trim().toLowerCase();
  if (NFL_NOT_CARRIED_SET.has(key)) return "not_carried";
  if (NFL_CARRIED_SET.has(key)) return "carried";
  // Unknown designated override — treat as not carried rather than inventing.
  return "not_carried";
}

/**
 * CFB (americanfootball_ncaaf) shares NFL's Odds API us/us2 inventory:
 * bet365 / circa / betr are designated columns only — never invent quotes.
 */
export function cfbBookFeedStatus(bookKey: string): BookFeedStatus {
  return nflBookFeedStatus(bookKey);
}

/** NFL + CFB: designated columns stay honest (carried vs not_carried). */
export function sportUsesDesignatedBookFeedHonesty(sportKey: string): boolean {
  const s = sportKey.trim().toLowerCase();
  return s === "nfl" || s === "cfb";
}

export function bookFeedStatusForSport(
  sportKey: string,
  bookKey: string,
): BookFeedStatus {
  if (!sportUsesDesignatedBookFeedHonesty(sportKey)) return "carried";
  return nflBookFeedStatus(bookKey);
}

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
  bovada: "Bovada",
  williamhill_us: "Caesars",
  betonlineag: "BetOnline",
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
    /** Odds API bookmaker snapshot time (ISO). */
    last_update?: string;
    markets: {
      key: string;
      /** Odds API market snapshot time (ISO). */
      last_update?: string;
      outcomes: Array<{ name: string; point?: number; price?: number }>;
    }[];
  }[];
};

/** Latest market/book last_update — never invents fetch time. */
function bookmakerAsOf(book: {
  last_update?: string;
  markets?: Array<{ last_update?: string }>;
}): string | null {
  let best: string | null = null;
  let bestMs = Number.NEGATIVE_INFINITY;
  const consider = (raw: string | undefined) => {
    if (!raw || !String(raw).trim()) return;
    const ms = Date.parse(raw);
    if (!Number.isFinite(ms)) return;
    if (ms >= bestMs) {
      bestMs = ms;
      best = String(raw).trim();
    }
  };
  consider(book.last_update);
  for (const m of book.markets ?? []) consider(m.last_update);
  return best;
}

/** Prefer this market's last_update, else book-level — never invent. */
function marketAsOfMs(
  book: { last_update?: string },
  market: { last_update?: string } | undefined,
): number | null {
  const raw = market?.last_update?.trim() || book.last_update?.trim() || null;
  if (!raw) return null;
  const ms = Date.parse(raw);
  return Number.isFinite(ms) ? ms : null;
}

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

/**
 * Bookmaker keys to send to The Odds API.
 * NFL + CFB: only keys the provider carries in us/us2 (never invent / never send dead keys).
 */
export function requestBooksForSport(sportKey: string): string[] {
  const designated = configuredBooksForSport(sportKey);
  if (!sportUsesDesignatedBookFeedHonesty(sportKey)) {
    return designated;
  }
  const carried = designated.filter(
    (book) => nflBookFeedStatus(book) === "carried",
  );
  return carried.length > 0 ? carried : [...NFL_ODDS_API_CARRIED_BOOKS];
}

function regionsForSport(sportKey: string): string {
  // hardrockbet lives in us2; NFL + CFB both need both regions.
  return sportUsesDesignatedBookFeedHonesty(sportKey)
    ? NFL_ODDS_REGIONS
    : "us,us2";
}

/** Latest book last_update among entry stamps → ISO for linesAsOf (never invent). */
function linesAsOfFromEntryMs(
  ...stamps: Array<number | null | undefined>
): string | undefined {
  let bestMs = Number.NEGATIVE_INFINITY;
  for (const ms of stamps) {
    if (ms == null || !Number.isFinite(ms)) continue;
    if (ms >= bestMs) bestMs = ms;
  }
  if (!Number.isFinite(bestMs) || bestMs === Number.NEGATIVE_INFINITY) {
    return undefined;
  }
  return new Date(bestMs).toISOString();
}

function filterBooksBySport<T extends { key?: string }>(
  items: T[],
  sportKey: string,
): T[] {
  // Only accept books we actually requested (carried for NFL).
  const allowed = new Set(
    requestBooksForSport(sportKey).map((book) => book.toLowerCase()),
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
  /** Book/market last_update ISO when present — fresher wins remaining ties. */
  asOfMs?: number | null;
};

type TotalBookEntry = {
  book: string;
  line: string;
  point: number;
  juiceOver?: string;
  juiceUnder?: string;
  asOfMs?: number | null;
};

type MoneylineBookEntry = {
  book: string;
  away: string;
  home: string;
  awayPrice: number;
  homePrice: number;
  asOfMs?: number | null;
};

function fresherStamp(
  candidate: number | null | undefined,
  incumbent: number | null | undefined,
): boolean {
  const c = candidate != null && Number.isFinite(candidate) ? candidate : null;
  const i = incumbent != null && Number.isFinite(incumbent) ? incumbent : null;
  if (c == null) return false;
  if (i == null) return true;
  return c > i;
}

/** Best away spread number across books; juice then fresher stamp break ties. */
export function pickBestSpreadEntry(
  entries: SpreadBookEntry[],
): SpreadBookEntry | null {
  if (!entries.length) return null;
  return entries.reduce((best, cur) => {
    if (cur.point > best.point) return cur;
    if (cur.point < best.point) return best;
    if (
      americanOddsBetter(
        parseAmericanPrice(cur.juiceAway),
        parseAmericanPrice(best.juiceAway),
      )
    ) {
      return cur;
    }
    if (
      americanOddsBetter(
        parseAmericanPrice(best.juiceAway),
        parseAmericanPrice(cur.juiceAway),
      )
    ) {
      return best;
    }
    return fresherStamp(cur.asOfMs, best.asOfMs) ? cur : best;
  });
}

/**
 * Best O/U number for Over shopping = highest total across books;
 * better Over juice then fresher stamp break ties.
 */
export function pickBestTotalEntry(
  entries: TotalBookEntry[],
): TotalBookEntry | null {
  if (!entries.length) return null;
  return entries.reduce((best, cur) => {
    if (cur.point > best.point) return cur;
    if (cur.point < best.point) return best;
    if (
      americanOddsBetter(
        parseAmericanPrice(cur.juiceOver),
        parseAmericanPrice(best.juiceOver),
      )
    ) {
      return cur;
    }
    if (
      americanOddsBetter(
        parseAmericanPrice(best.juiceOver),
        parseAmericanPrice(cur.juiceOver),
      )
    ) {
      return best;
    }
    return fresherStamp(cur.asOfMs, best.asOfMs) ? cur : best;
  });
}

/** Best away moneyline = highest American price; fresher stamp breaks ties. */
export function pickBestMoneylineEntry(
  entries: MoneylineBookEntry[],
): MoneylineBookEntry | null {
  if (!entries.length) return null;
  return entries.reduce((best, cur) => {
    if (americanOddsBetter(cur.awayPrice, best.awayPrice)) return cur;
    if (americanOddsBetter(best.awayPrice, cur.awayPrice)) return best;
    return fresherStamp(cur.asOfMs, best.asOfMs) ? cur : best;
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
  const requestBooks = requestBooksForSport(normalizedSport);
  // MLB is a moneyline sport on the public board — request h2h, not run lines.
  const markets = isMlb ? "h2h,totals" : "spreads,totals";
  const regions = regionsForSport(normalizedSport);

  const url = `${ODDS_API_BASE}/sports/${oddsSportKey}/odds?regions=${regions}&markets=${markets}&oddsFormat=american&bookmakers=${encodeURIComponent(requestBooks.join(","))}&apiKey=${apiKey}`;
  const res = await upstreamFetch(url, {
    cache: "no-store",
    timeoutMs: UPSTREAM_TIMEOUT_MS.fast,
  });
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

    const formatJuice = (
      price: number | undefined | null,
    ): string | undefined => {
      if (price == null || !Number.isFinite(price)) return undefined;
      const n = Math.round(price);
      return n > 0 ? `+${n}` : String(n);
    };

    if (isMlb) {
      const mlData = bookmakers.flatMap((b) => {
        const m = b.markets?.find((x) => x.key === "h2h");
        if (!m) return [];
        const awayOutcome = m.outcomes?.find((o) => o.name === ev.away_team);
        const homeOutcome = m.outcomes?.find((o) => o.name === ev.home_team);
        if (awayOutcome?.price == null || homeOutcome?.price == null) return [];
        const away = formatJuice(awayOutcome.price);
        const home = formatJuice(homeOutcome.price);
        if (!away || !home) return [];
        const asOfMs = marketAsOfMs(b, m);
        return [
          {
            book: b.key,
            away,
            home,
            awayPrice: awayOutcome.price,
            homePrice: homeOutcome.price,
            asOfMs,
          } satisfies MoneylineBookEntry,
        ];
      });
      // Open preference among posted carried books (not API order); Best = best number.
      const selectedMl = orderBooksByPreference(mlData, sportBooks);
      const openMlEntry = selectedMl[0];
      const bestMlEntry = pickBestMoneylineEntry(selectedMl) ?? openMlEntry;
      const bestMlBookKey = bestMlEntry?.book;
      const bestMlBook = bestMlBookKey ? bookDisplay(bestMlBookKey) : undefined;

      const mlAsOf = linesAsOfFromEntryMs(
        openMlEntry?.asOfMs,
        bestMlEntry?.asOfMs,
      );
      rows.push({
        id: `${ev.id}-moneyline`,
        game,
        time: timeWithDate,
        commenceTime: ev.commence_time,
        market: "Moneyline",
        // Away American in open/best; home American in *JuiceHome (no point flip).
        open: openMlEntry?.away,
        best: bestMlEntry?.away ?? openMlEntry?.away,
        book: bestMlBook,
        bookKey: bestMlBookKey,
        openJuice: openMlEntry?.away,
        openJuiceHome: openMlEntry?.home,
        bestJuice: bestMlEntry?.away ?? openMlEntry?.away,
        bestJuiceHome: bestMlEntry?.home ?? openMlEntry?.home,
        ...(mlAsOf ? { linesAsOf: mlAsOf } : {}),
      });
    } else {
      const spreadData = bookmakers.flatMap((b) => {
        const m = b.markets?.find((x) => x.key === "spreads");
        if (!m) return [];
        const awayOutcome = m.outcomes?.find((o) => o.name === ev.away_team);
        const homeOutcome = m.outcomes?.find((o) => o.name === ev.home_team);
        if (!awayOutcome || awayOutcome.point == null) return [];
        const pt = awayOutcome.point;
        const canonical = true;
        const line = formatSpreadDisplay(pt, normalizedSport, {
          markAlternate: false,
        });
        const asOfMs = marketAsOfMs(b, m);
        return [
          {
            book: b.key,
            line,
            point: pt,
            canonical,
            juiceAway: formatJuice(awayOutcome.price),
            juiceHome: formatJuice(homeOutcome?.price),
            asOfMs,
          },
        ];
      });
      // Open = preferred book among those that posted; Best = best across all posted.
      const selectedSpreadData = orderBooksByPreference(spreadData, sportBooks);
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
      const spreadAsOf = linesAsOfFromEntryMs(
        openSpreadEntry?.asOfMs,
        bestSpreadEntry?.asOfMs,
      );

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
        ...(spreadAsOf ? { linesAsOf: spreadAsOf } : {}),
      });
    }

    const totalsData = bookmakers.flatMap((b) => {
      const m = b.markets?.find((x) => x.key === "totals");
      if (!m) return [];
      const over = m.outcomes?.find((o) => o.name === "Over");
      const under = m.outcomes?.find((o) => o.name === "Under");
      const point = over?.point ?? m.outcomes?.[0]?.point;
      if (point == null) return [];
      const asOfMs = marketAsOfMs(b, m);
      return [
        {
          book: b.key,
          line: String(point),
          point,
          juiceOver: formatJuice(over?.price),
          juiceUnder: formatJuice(under?.price),
          asOfMs,
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
    const totalAsOf = linesAsOfFromEntryMs(
      openTotalEntry?.asOfMs,
      bestTotalEntry?.asOfMs,
    );

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
      ...(totalAsOf ? { linesAsOf: totalAsOf } : {}),
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
  moneyline: Record<
    string,
    {
      away: string;
      home: string;
      awayPrice?: number;
      homePrice?: number;
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
  bestMlAwayBook?: string;
  bestMlHomeBook?: string;
};

export type OddsComparisonBookAsOf = {
  key: string;
  label: string;
  /** Book/market last_update from Odds API; null when upstream omitted it. */
  asOf: string | null;
  /**
   * NFL / CFB: not_carried = designated column our provider cannot supply
   * (not an empty cell implying the book declined to post).
   */
  feedStatus?: BookFeedStatus;
};

export type OddsComparisonResult = {
  rows: OddsComparisonRow[];
  /**
   * Max book/market last_update across the pull.
   * Null when Odds API omitted timestamps — callers must not invent fetch time.
   */
  asOf: string | null;
  /** Per-book capture stamps for designated books (incl. not_carried). */
  bookAsOf: OddsComparisonBookAsOf[];
};

/**
 * Board-facing compare row: only fields the Compare Odds UI renders.
 * Drops unused home spread / under / numeric point mirrors and commenceTime
 * so the JSON (and any accidental SSR) stays lean.
 */
export type OddsCompareBoardRow = {
  id: string;
  game: string;
  time: string;
  spread: Record<string, { away: string; awayJuice?: string }>;
  moneyline: Record<string, { away: string; home: string }>;
  total: Record<string, { line: string; overJuice?: string }>;
  bestSpreadBook?: string;
  bestTotalBook?: string;
  bestMlAwayBook?: string;
  bestMlHomeBook?: string;
};

export type OddsCompareBoardBook = {
  key: string;
  label: string;
  feedStatus: BookFeedStatus;
};

export type OddsCompareBoardPayload = {
  rows: OddsCompareBoardRow[];
  books: OddsCompareBoardBook[];
  asOf: string | null;
  bookAsOf: OddsComparisonBookAsOf[];
};

/** Strip unused book fields before shipping Compare Odds over the wire. */
export function slimOddsComparisonForBoard(
  rows: OddsComparisonRow[],
): OddsCompareBoardRow[] {
  return rows.map((r) => {
    const spread: OddsCompareBoardRow["spread"] = {};
    for (const [key, entry] of Object.entries(r.spread ?? {})) {
      if (!entry) continue;
      spread[key] = {
        away: entry.away,
        ...(entry.awayJuice ? { awayJuice: entry.awayJuice } : {}),
      };
    }
    const moneyline: OddsCompareBoardRow["moneyline"] = {};
    for (const [key, entry] of Object.entries(r.moneyline ?? {})) {
      if (!entry) continue;
      moneyline[key] = { away: entry.away, home: entry.home };
    }
    const total: OddsCompareBoardRow["total"] = {};
    for (const [key, entry] of Object.entries(r.total ?? {})) {
      if (!entry) continue;
      total[key] = {
        line: entry.line,
        ...(entry.overJuice ? { overJuice: entry.overJuice } : {}),
      };
    }
    return {
      id: r.id,
      game: r.game,
      time: r.time,
      spread,
      moneyline,
      total,
      bestSpreadBook: r.bestSpreadBook,
      bestTotalBook: r.bestTotalBook,
      bestMlAwayBook: r.bestMlAwayBook,
      bestMlHomeBook: r.bestMlHomeBook,
    };
  });
}

export async function fetchOddsComparison(
  sportKey: string,
  apiKey: string,
): Promise<OddsComparisonResult> {
  const normalizedSport = sportKey.toLowerCase();
  const oddsSportKey = SPORT_KEY_MAP[normalizedSport];
  if (!oddsSportKey) return { rows: [], asOf: null, bookAsOf: [] };
  const isMlb = normalizedSport === "mlb";
  const sportBooks = configuredBooksForSport(normalizedSport);
  const requestBooks = requestBooksForSport(normalizedSport);
  const regions = regionsForSport(normalizedSport);
  const usesFeedHonesty = sportUsesDesignatedBookFeedHonesty(normalizedSport);

  const url = `${ODDS_API_BASE}/sports/${oddsSportKey}/odds?regions=${regions}&markets=spreads,h2h,totals&oddsFormat=american&bookmakers=${encodeURIComponent(requestBooks.join(","))}&apiKey=${apiKey}`;
  const res = await upstreamFetch(url, {
    cache: "no-store",
    timeoutMs: UPSTREAM_TIMEOUT_MS.heavy,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Odds API ${res.status}: ${text.slice(0, 200)}`);
  }
  const events = (await res.json()) as OddsEvent[];

  const rows: OddsComparisonRow[] = [];
  const bookAsOfMap = new Map<string, string | null>();
  const commenceTime = (e: OddsEvent) => new Date(e.commence_time).getTime();

  for (const ev of events.sort((a, b) => commenceTime(a) - commenceTime(b))) {
    const game = `${ev.away_team} @ ${ev.home_team}`;
    const date = formatDate(ev.commence_time);
    const time = formatTime(ev.commence_time);
    const timeWithDate = `${date} ${time} ET`;

    const bookmakers = filterBooksBySport(ev.bookmakers ?? [], normalizedSport);
    const spread: OddsComparisonRow["spread"] = {};
    const moneyline: OddsComparisonRow["moneyline"] = {};
    const total: OddsComparisonRow["total"] = {};
    const formatJuice = (
      price: number | undefined | null,
    ): string | undefined => {
      if (price == null || !Number.isFinite(price)) return undefined;
      const n = Math.round(price);
      return n > 0 ? `+${n}` : String(n);
    };

    const spreadEntries: SpreadBookEntry[] = [];
    const totalEntries: TotalBookEntry[] = [];
    let bestMlAwayBook: string | undefined;
    let bestMlAwayPrice: number | null = null;
    let bestMlAwayAsOf: number | null = null;
    let bestMlHomeBook: string | undefined;
    let bestMlHomePrice: number | null = null;
    let bestMlHomeAsOf: number | null = null;

    for (const b of bookmakers) {
      const snapAsOf = bookmakerAsOf(b);
      const snapMs = snapAsOf ? Date.parse(snapAsOf) : Number.NaN;
      const asOfMs = Number.isFinite(snapMs) ? snapMs : null;
      const prev = bookAsOfMap.get(b.key);
      if (snapAsOf) {
        if (!prev || Date.parse(snapAsOf) >= Date.parse(prev)) {
          bookAsOfMap.set(b.key, snapAsOf);
        }
      } else if (!bookAsOfMap.has(b.key)) {
        bookAsOfMap.set(b.key, null);
      }

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
            asOfMs,
          });
        }
      }
      const mlM = b.markets?.find((x) => x.key === "h2h");
      if (mlM) {
        const awayO = mlM.outcomes?.find((o) => o.name === ev.away_team);
        const homeO = mlM.outcomes?.find((o) => o.name === ev.home_team);
        if (awayO?.price != null && homeO?.price != null) {
          moneyline[b.key] = {
            away: formatJuice(awayO.price) ?? String(awayO.price),
            home: formatJuice(homeO.price) ?? String(homeO.price),
            awayPrice: awayO.price,
            homePrice: homeO.price,
          };
          const awayBetter = americanOddsBetter(awayO.price, bestMlAwayPrice);
          const awayTie =
            bestMlAwayPrice != null && awayO.price === bestMlAwayPrice;
          if (awayBetter || (awayTie && fresherStamp(asOfMs, bestMlAwayAsOf))) {
            bestMlAwayPrice = awayO.price;
            bestMlAwayBook = b.key;
            bestMlAwayAsOf = asOfMs;
          }
          const homeBetter = americanOddsBetter(homeO.price, bestMlHomePrice);
          const homeTie =
            bestMlHomePrice != null && homeO.price === bestMlHomePrice;
          if (homeBetter || (homeTie && fresherStamp(asOfMs, bestMlHomeAsOf))) {
            bestMlHomePrice = homeO.price;
            bestMlHomeBook = b.key;
            bestMlHomeAsOf = asOfMs;
          }
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
            asOfMs,
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
      moneyline,
      total,
      bestSpreadBook: pickBestSpreadEntry(spreadEntries)?.book,
      bestTotalBook: pickBestTotalEntry(totalEntries)?.book,
      bestMlAwayBook,
      bestMlHomeBook,
    });
  }

  // NFL / CFB: always emit designated columns (incl. not_carried) so UI stays honest.
  // Other sports: only books that appeared in the pull (prior behavior).
  const bookAsOf: OddsComparisonBookAsOf[] = usesFeedHonesty
    ? sportBooks.map((key) => ({
        key,
        label: bookDisplay(key),
        asOf: bookAsOfMap.get(key) ?? null,
        feedStatus: bookFeedStatusForSport(normalizedSport, key),
      }))
    : sportBooks
        .filter((key) => bookAsOfMap.has(key))
        .map((key) => ({
          key,
          label: bookDisplay(key),
          asOf: bookAsOfMap.get(key) ?? null,
        }));

  let asOf: string | null = null;
  let asOfMs = Number.NEGATIVE_INFINITY;
  for (const entry of bookAsOf) {
    if (entry.feedStatus === "not_carried") continue;
    if (!entry.asOf) continue;
    const ms = Date.parse(entry.asOf);
    if (!Number.isFinite(ms)) continue;
    if (ms >= asOfMs) {
      asOfMs = ms;
      asOf = entry.asOf;
    }
  }

  return { rows, asOf, bookAsOf };
}
