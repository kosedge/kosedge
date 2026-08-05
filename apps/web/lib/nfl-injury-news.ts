import "server-only";
import {
  fetchEspnInjuryNews,
  type CampNewsItem,
} from "@/lib/nfl-camp-desk";

export type InjuryNewsItem = CampNewsItem & {
  sourceLabel: string;
};

const ROTOWIRE_RSS =
  "https://www.rotowire.com/rss/news.php?sport=NFL";
const ROTOWORLD_RSS =
  "https://www.rotoworld.com/rss/feed.aspx?s=16";

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

async function fetchRssInjuryNews(
  url: string,
  source: CampNewsItem["source"],
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
    ];
    return parseRssItems(xml)
      .filter((item) => {
        const blob = `${item.title} ${item.description}`.toLowerCase();
        return injuryKeywords.some((kw) => blob.includes(kw));
      })
      .slice(0, limit)
      .map((item, index) => ({
        id: `${source}-${index}-${item.link}`,
        headline: item.title,
        description: item.description,
        published: item.pubDate,
        href: item.link,
        source,
        sourceLabel,
      }));
  } catch {
    return [];
  } finally {
    clearTimeout(timeout);
  }
}

function normalizeHeadline(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function dedupeNews(items: InjuryNewsItem[]): InjuryNewsItem[] {
  const seen = new Set<string>();
  const out: InjuryNewsItem[] = [];
  for (const item of items) {
    const key = normalizeHeadline(item.headline);
    if (!key || seen.has(key)) continue;
    seen.add(key);
    out.push(item);
  }
  return out;
}

function sourceLabelFor(item: CampNewsItem): string {
  switch (item.source) {
    case "espn-news":
      return "ESPN";
    case "rotowire-rss":
      return "RotoWire";
    case "rotoworld-rss":
      return "Rotoworld";
    case "vsin-rss":
      return "VSiN";
    default:
      return "News";
  }
}

/**
 * Multi-source injury & availability headlines for the Injuries & News desk.
 * ESPN + RotoWire + Rotoworld (NBC) — deduped, newest first.
 */
export async function fetchInjuryNewsFeed(
  limit = 12,
): Promise<InjuryNewsItem[]> {
  const [espn, rotowire, rotoworld] = await Promise.all([
    fetchEspnInjuryNews(Math.max(limit, 10)),
    fetchRssInjuryNews(
      ROTOWIRE_RSS,
      "rotowire-rss",
      "RotoWire",
      Math.max(limit, 8),
    ),
    fetchRssInjuryNews(
      ROTOWORLD_RSS,
      "rotoworld-rss",
      "Rotoworld",
      Math.max(limit, 8),
    ),
  ]);

  const merged = dedupeNews([
    ...espn.map((item) => ({ ...item, sourceLabel: sourceLabelFor(item) })),
    ...rotowire,
    ...rotoworld,
  ]);

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
