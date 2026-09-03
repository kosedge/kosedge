/**
 * Honest market as-of / stale stamps for subscriber tables.
 * Never invent a clock — blank source → unavailable copy.
 */

/** Same 6h policy as Edge Board / Compare Odds cache TTL. */
export const MARKET_ASOF_STALE_MS = 6 * 60 * 60 * 1000;

const MISSING_COPY = "Market as-of unavailable";

export type MarketAsOfKind = "odds" | "lines" | "board" | "market";

export type MarketAsOfStampInput = {
  /** ISO capture time from the market source. Null/blank → unavailable. */
  asOf: string | null | undefined;
  /** Books actually pulled for this stamp (display labels). */
  books?: string[] | null;
  kind?: MarketAsOfKind;
  /** Override "now" for stale tests. */
  nowMs?: number;
  staleMs?: number;
};

export type MarketAsOfStampResult = {
  /** Full subscriber-facing sentence. */
  text: string;
  /** True when source timestamp is missing or unparseable. */
  missing: boolean;
  /** True when asOf parses and is older than staleMs. */
  stale: boolean;
  /** Normalized ISO when present and parseable; else null. */
  asOfIso: string | null;
};

const KIND_PREFIX: Record<MarketAsOfKind, string> = {
  odds: "Odds as of",
  lines: "Lines as of",
  board: "Board as of",
  market: "Market as of",
};

/** Latest valid ISO among candidates — never synthesizes a clock. */
export function pickLatestIso(
  ...candidates: Array<string | null | undefined>
): string | null {
  let best: string | null = null;
  let bestMs = Number.NEGATIVE_INFINITY;
  for (const raw of candidates) {
    if (raw == null || String(raw).trim() === "") continue;
    const ms = Date.parse(String(raw));
    if (!Number.isFinite(ms)) continue;
    if (ms >= bestMs) {
      bestMs = ms;
      best = String(raw).trim();
    }
  }
  return best;
}

export function formatMarketAsOfDisplay(
  iso: string,
  timeZone = "America/New_York",
): string {
  const ms = Date.parse(iso);
  if (!Number.isFinite(ms)) return iso;
  return new Date(ms).toLocaleString("en-US", {
    timeZone,
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

function uniqueBookLabels(books: string[] | null | undefined): string[] {
  if (!books?.length) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const b of books) {
    const label = String(b ?? "").trim();
    if (!label) continue;
    const key = label.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(label);
  }
  return out;
}

/**
 * Build honest as-of / stale copy for a market table.
 * Does not fall back to "now" or any editorial date when asOf is blank.
 */
export function marketAsOfStamp(
  input: MarketAsOfStampInput,
): MarketAsOfStampResult {
  const kind = input.kind ?? "market";
  const raw = input.asOf?.trim() || null;
  const ms = raw ? Date.parse(raw) : Number.NaN;
  if (!raw || !Number.isFinite(ms)) {
    return {
      text: MISSING_COPY,
      missing: true,
      stale: false,
      asOfIso: null,
    };
  }

  const now = input.nowMs ?? Date.now();
  const staleMs = input.staleMs ?? MARKET_ASOF_STALE_MS;
  const stale = now - ms > staleMs;
  const books = uniqueBookLabels(input.books);
  const bookBit = books.length ? ` · ${books.join(" · ")}` : "";
  const staleBit = stale ? " · stale" : "";
  const text = `${KIND_PREFIX[kind]} ${formatMarketAsOfDisplay(raw)}${bookBit}${staleBit}`;

  return {
    text,
    missing: false,
    stale,
    asOfIso: raw,
  };
}

/** Props / board helper: max updatedAt across rows, or null (never invent). */
export function boardAsOfFromUpdatedAts(
  stamps: Array<string | null | undefined>,
): string | null {
  return pickLatestIso(...stamps);
}
