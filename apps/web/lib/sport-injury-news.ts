import "server-only";
import type { InjuryNewsItem } from "@/lib/nfl-injury-news";
import { fetchInjuryNewsFeed } from "@/lib/nfl-injury-news";

export type SportInjuryNewsConfig = {
  sportLabel: string;
  sourceSummary: string;
  emptyHint: string;
  campHref?: string;
  /** When true, reuse the NFL multi-source aggregator. */
  useNflFeed?: boolean;
};

const SPORT_INJURY_CONFIG: Record<string, SportInjuryNewsConfig> = {
  nfl: {
    sportLabel: "NFL",
    useNflFeed: true,
    sourceSummary:
      "Multi-source desk: trusted beats, RotoWire, Rotoworld, VSiN, and public feeds.",
    emptyHint:
      "No injury headlines in the current multi-source pull. Check Camp Desk beats for club-specific hubs.",
    campHref: "/pro/nfl/camp",
  },
  cfb: {
    sportLabel: "CFB",
    sourceSummary:
      "Aggregated from ESPN and RotoWire college football feeds where available.",
    emptyHint:
      "No CFB injury headlines in the current pull. Weekly designation tables will populate when in-season intel is wired.",
    campHref: "/pro/cfb/overview",
  },
  nhl: {
    sportLabel: "NHL",
    sourceSummary:
      "Aggregated from ESPN and RotoWire NHL feeds where available.",
    emptyHint:
      "No NHL injury headlines in the current pull. Goalie and lineup intel lives on the Goalie Desk when the slate is live.",
    campHref: "/pro/nhl/overview",
  },
  nba: {
    sportLabel: "NBA",
    sourceSummary:
      "Aggregated from ESPN and RotoWire NBA feeds where available.",
    emptyHint:
      "No NBA injury headlines in the current pull. Check back when the daily slate is active.",
    campHref: "/pro/nba/overview",
  },
  mlb: {
    sportLabel: "MLB",
    sourceSummary:
      "Aggregated from ESPN and RotoWire MLB feeds where available.",
    emptyHint:
      "No MLB injury headlines in the current pull. IL moves will surface here when feeds are active.",
    campHref: "/pro/mlb/overview",
  },
  wnba: {
    sportLabel: "WNBA",
    sourceSummary:
      "Aggregated from ESPN and RotoWire WNBA feeds where available.",
    emptyHint:
      "No WNBA injury headlines in the current pull. Check back when the daily slate is active.",
    campHref: "/pro/wnba/overview",
  },
};

const ROTOWIRE_BY_SPORT: Record<string, string> = {
  cfb: "https://www.rotowire.com/rss/news.php?sport=CFB",
  nhl: "https://www.rotowire.com/rss/news.php?sport=NHL",
  nba: "https://www.rotowire.com/rss/news.php?sport=NBA",
  mlb: "https://www.rotowire.com/rss/news.php?sport=MLB",
  wnba: "https://www.rotowire.com/rss/news.php?sport=WNBA",
};

function decodeXmlEntities(value: string): string {
  return value
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .trim();
}

function parseRssItems(xml: string): Array<{
  title: string;
  link: string;
  description: string;
  pubDate: string | null;
}> {
  const items: Array<{
    title: string;
    link: string;
    description: string;
    pubDate: string | null;
  }> = [];
  const itemPattern = /<item[\s\S]*?<\/item>/gi;
  let match: RegExpExecArray | null;
  while ((match = itemPattern.exec(xml)) !== null) {
    const block = match[0];
    const title = decodeXmlEntities(
      block.match(/<title>([\s\S]*?)<\/title>/i)?.[1] ?? "",
    );
    const link = decodeXmlEntities(
      block.match(/<link>([\s\S]*?)<\/link>/i)?.[1] ?? "",
    );
    const description = decodeXmlEntities(
      block.match(/<description>([\s\S]*?)<\/description>/i)?.[1] ?? "",
    );
    const pubDateRaw = decodeXmlEntities(
      block.match(/<pubDate>([\s\S]*?)<\/pubDate>/i)?.[1] ?? "",
    );
    if (!title || !link) continue;
    items.push({
      title,
      link,
      description: description.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim(),
      pubDate: pubDateRaw || null,
    });
  }
  return items;
}

async function fetchSportRss(
  url: string,
  sourceLabel: string,
  limit: number,
): Promise<InjuryNewsItem[]> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10_000);
  try {
    const response = await fetch(url, {
      next: { revalidate: 900 },
      signal: controller.signal,
      headers: { accept: "application/rss+xml, application/xml, text/xml" },
    });
    if (!response.ok) return [];
    const xml = await response.text();
    const injuryKeywords = [
      "injur",
      "out ",
      " doubtful",
      " questionable",
      " ruled out",
      " placed on ir",
      " pup",
      " surgery",
      " rehab",
      " availability",
      " inactive",
      " limited",
      " did not practice",
      " dnp",
      " day-to-day",
      " sidelined",
    ];
    return parseRssItems(xml)
      .filter((item) => {
        const blob = `${item.title} ${item.description}`.toLowerCase();
        return injuryKeywords.some((kw) => blob.includes(kw));
      })
      .slice(0, limit)
      .map((item, index) => ({
        id: `${sourceLabel}-${index}-${item.link}`,
        headline: item.title,
        description: item.description,
        published: item.pubDate,
        href: item.link,
        source: "rotowire-rss" as const,
        sourceLabel,
      }));
  } catch {
    return [];
  } finally {
    clearTimeout(timeout);
  }
}

function dedupeNews(items: InjuryNewsItem[]): InjuryNewsItem[] {
  const seen = new Set<string>();
  const out: InjuryNewsItem[] = [];
  for (const item of items) {
    const key = item.headline.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    out.push(item);
  }
  return out;
}

export function getSportInjuryNewsConfig(
  sport: string,
): SportInjuryNewsConfig | null {
  return SPORT_INJURY_CONFIG[sport.toLowerCase()] ?? null;
}

export async function fetchSportInjuryNewsFeed(
  sport: string,
  limit = 10,
): Promise<InjuryNewsItem[]> {
  const config = getSportInjuryNewsConfig(sport);
  if (!config) return [];
  if (config.useNflFeed) return fetchInjuryNewsFeed(limit);

  const rotowireUrl = ROTOWIRE_BY_SPORT[sport.toLowerCase()];
  const rotowire = rotowireUrl
    ? await fetchSportRss(rotowireUrl, "RotoWire", limit)
    : [];

  const merged = dedupeNews(rotowire);
  merged.sort((a, b) => {
    const ta = Date.parse(a.published ?? "");
    const tb = Date.parse(b.published ?? "");
    if (Number.isFinite(ta) && Number.isFinite(tb)) return tb - ta;
    if (Number.isFinite(tb)) return 1;
    if (Number.isFinite(ta)) return -1;
    return 0;
  });
  return merged.slice(0, limit);
}
