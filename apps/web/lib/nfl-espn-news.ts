/**
 * Shared ESPN NFL news fetch — kept separate from Camp Desk so Injuries
 * (and other desks) do not pull camp filesystem tracing into their functions.
 */
import "server-only";

export type EspnNflNewsItem = {
  id: string;
  headline: string;
  description: string;
  published: string | null;
  href: string;
  source:
    | "espn-news"
    | "rotowire-rss"
    | "rotoworld-rss"
    | "vsin-rss"
    | "kosedge-desk";
};

const CAMP_KEYWORDS = [
  "training camp",
  "camp:",
  "hold-in",
  "holdin",
  "holdout",
  "preseason",
  "roster",
  "practice",
  "depth chart",
  "cutdown",
  "injury",
  "contract",
];

const INJURY_KEYWORDS = [
  "injury",
  "injured",
  "acl",
  "mcl",
  "pcl",
  "achilles",
  "concussion",
  "hamstring",
  "quad",
  "ankle",
  "knee",
  "shoulder",
  "foot",
  "wrist",
  "dnp",
  "did not practice",
  "limited",
  "questionable",
  "doubtful",
  "out for",
  "carted",
  "surgery",
  "rehab",
  "return timeline",
];

function isCampRelevant(headline: string, description: string): boolean {
  const blob = `${headline} ${description}`.toLowerCase();
  return CAMP_KEYWORDS.some((kw) => blob.includes(kw));
}

function isInjuryRelevant(headline: string, description: string): boolean {
  const blob = `${headline} ${description}`.toLowerCase();
  return INJURY_KEYWORDS.some((kw) => blob.includes(kw));
}

export function espnItemIsCampRelevant(item: EspnNflNewsItem): boolean {
  return isCampRelevant(item.headline, item.description);
}

export function espnItemIsInjuryRelevant(item: EspnNflNewsItem): boolean {
  return isInjuryRelevant(item.headline, item.description);
}

export async function fetchEspnNflArticles(
  limit = 50,
): Promise<EspnNflNewsItem[]> {
  const url = `https://site.api.espn.com/apis/site/v2/sports/football/nfl/news?limit=${limit}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(url, {
      next: { revalidate: 1800 },
      signal: controller.signal,
      headers: { accept: "application/json" },
    });
    if (!response.ok) return [];
    const payload = (await response.json()) as {
      articles?: Array<{
        id?: number | string;
        headline?: string;
        description?: string;
        published?: string;
        links?: { web?: { href?: string } };
      }>;
    };
    const items: EspnNflNewsItem[] = [];
    for (const article of payload.articles ?? []) {
      const headline = (article.headline ?? "").trim();
      const description = (article.description ?? "").trim();
      const href = article.links?.web?.href ?? "";
      if (!headline || !href) continue;
      items.push({
        id: String(article.id ?? href),
        headline,
        description,
        published: article.published ?? null,
        href,
        source: "espn-news",
      });
    }
    return items;
  } catch {
    return [];
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchEspnCampNews(
  limit = 12,
): Promise<EspnNflNewsItem[]> {
  const articles = await fetchEspnNflArticles(50);
  return articles
    .filter((item) => isCampRelevant(item.headline, item.description))
    .slice(0, limit);
}

export async function fetchEspnInjuryNews(
  limit = 10,
): Promise<EspnNflNewsItem[]> {
  const articles = await fetchEspnNflArticles(50);
  return articles
    .filter((item) => isInjuryRelevant(item.headline, item.description))
    .slice(0, limit);
}
