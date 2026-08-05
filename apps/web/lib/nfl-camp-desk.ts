import "server-only";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { NFL_TEAM_DIRECTORY } from "@/lib/nfl-team-intel";

export type CampBeatLink = {
  team: string;
  teamName: string;
  division: string;
  kosEdgeWriter: string;
  primaryWriter: string | null;
  primaryOutlet: string | null;
  primaryHandle: string | null;
  espnCampHref: string | null;
  previewHref: string;
};

export type CampNewsItem = {
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

export type CampWriterIntelItem = {
  team: string;
  teamName: string;
  author: string;
  angle: string | null;
  campRefsMarkdown: string;
  previewHref: string;
  sourceLinks: Array<{ label: string; href: string }>;
};

export type CampDeskPayload = {
  generatedAt: string;
  eraLabel: string;
  hubHref: string;
  news: CampNewsItem[];
  injuryNews: CampNewsItem[];
  writerIntel: CampWriterIntelItem[];
  beats: CampBeatLink[];
  writers: Array<{ name: string; coverage: string }>;
  notes: string[];
  diagnostics: {
    newsCount: number;
    injuryNewsCount: number;
    writerIntelCount: number;
    beatCount: number;
    beatRegistryVersion: string | null;
  };
};

type BeatRegistry = {
  version?: string;
  era?: string;
  updated?: string;
  teams?: Record<
    string,
    {
      team?: string;
      division?: string;
      kos_edge_writer?: string;
      writers?: Array<{
        name?: string;
        outlet?: string;
        x?: string[];
        role?: string;
      }>;
    }
  >;
};

const WRITER_COVERAGE: Array<{ name: string; coverage: string }> = [
  { name: "Casey Voss", coverage: "NFC North" },
  { name: "Reese Quinn", coverage: "AFC North" },
  { name: "Morgan Hale", coverage: "NFC West" },
  { name: "Taylor Brooks", coverage: "AFC East" },
  { name: "Avery Cole", coverage: "NFC South" },
  { name: "Jordan Vale", coverage: "NFC East" },
  { name: "Drew Kessler", coverage: "AFC South" },
  { name: "Sam Ortiz", coverage: "AFC West" },
];

/** Known ESPN 2026 team camp hubs (public story pages). */
const ESPN_TEAM_CAMP_HUBS: Record<string, string> = {
  ARI: "https://www.espn.com/nfl/story/_/id/49426382/arizona-cardinals-training-camp-2026-intel-updates",
  ATL: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  BAL: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  BUF: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  CAR: "https://www.espn.com/nfl/story/_/id/49377273/carolina-panthers-training-camp-2026-intel-updates",
  CHI: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  CIN: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  CLE: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  DAL: "https://www.espn.com/nfl/story/_/id/49376535/dallas-cowboys-training-camp-2026-intel-updates",
  DEN: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  DET: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  GB: "https://www.espn.com/nfl/story/_/id/49376941/green-bay-packers-training-camp-2026-intel-updates",
  HOU: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  IND: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  JAX: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  KC: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  LAC: "https://www.espn.com/nfl/story/_/id/49424976/los-angeles-chargers-training-camp-2026-intel-updates",
  LAR: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  LV: "https://www.espn.com/nfl/story/_/id/49425032/las-vegas-raiders-training-camp-2026-intel-updates",
  MIA: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  MIN: "https://www.espn.com/nfl/story/_/id/49376202/minnesota-vikings-training-camp-2026-intel-updates",
  NE: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  NO: "https://www.espn.com/nfl/story/_/id/49424731/new-orleans-saints-training-camp-2026-intel-updates",
  NYG: "https://www.espn.com/nfl/story/_/id/49434181/new-york-giants-training-camp-2026-intel-updates",
  NYJ: "https://www.espn.com/nfl/story/_/id/49419756/new-york-jets-training-camp-2026-intel-updates",
  PHI: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  PIT: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  SEA: "https://www.espn.com/nfl/story/_/id/49427699/seattle-seahawks-training-camp-2026-intel-updates",
  SF: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  TB: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  TEN: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  WAS: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
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

function findRepoRoot(): string | null {
  let current = process.cwd();
  for (let depth = 0; depth < 6; depth += 1) {
    if (existsSync(path.join(current, "data", "writers"))) return current;
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return null;
}

function loadBeatRegistry(): BeatRegistry | null {
  const root = findRepoRoot();
  if (!root) return null;
  const filePath = path.join(root, "data", "writers", "nfl-beat-writers.json");
  if (!existsSync(filePath)) return null;
  try {
    return JSON.parse(readFileSync(filePath, "utf-8")) as BeatRegistry;
  } catch {
    return null;
  }
}

function isCampRelevant(headline: string, description: string): boolean {
  const blob = `${headline} ${description}`.toLowerCase();
  return CAMP_KEYWORDS.some((kw) => blob.includes(kw));
}

function isInjuryRelevant(headline: string, description: string): boolean {
  const blob = `${headline} ${description}`.toLowerCase();
  return INJURY_KEYWORDS.some((kw) => blob.includes(kw));
}

function parseMarkdownLinks(
  markdown: string,
): Array<{ label: string; href: string }> {
  const links: Array<{ label: string; href: string }> = [];
  const pattern = /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(markdown)) !== null) {
    links.push({ label: match[1].trim(), href: match[2].trim() });
  }
  return links;
}

function loadWriterCampIntel(): CampWriterIntelItem[] {
  const root = findRepoRoot();
  if (!root) return [];
  const dir = path.join(root, "content", "writers", "season-previews-2026");
  if (!existsSync(dir)) return [];
  const byCode = new Map(
    NFL_TEAM_DIRECTORY.map((entry) => [entry.code, entry] as const),
  );
  const items: CampWriterIntelItem[] = [];
  for (const name of readdirSync(dir)) {
    if (!name.endsWith(".md") || name === "INDEX.md") continue;
    const team = name.replace(/\.md$/, "").toUpperCase();
    let raw = "";
    try {
      raw = readFileSync(path.join(dir, name), "utf8");
    } catch {
      continue;
    }
    const campRefs =
      raw.match(/\*\*Camp\s*\/\s*market refs:\*\*\s*(.+)$/im)?.[1]?.trim() ??
      "";
    const sources =
      raw.match(/\*\*Sources(?:\s*\(beat desk\))?:\*\*\s*(.+)$/im)?.[1]?.trim() ??
      "";
    const market =
      raw
        .match(
          /\*\*Market(?:\s*\([^)]*\))?:\*\*\s*(.+)$/im,
        )?.[1]
        ?.trim() ?? "";
    const refsBlob = [campRefs, sources, market].filter(Boolean).join(" · ");
    if (!refsBlob) continue;
    const author =
      raw.match(
        /\*\*By\s+([^*]+?)\*\*\s*·\s*Kos Edge Analytics/i,
      )?.[1]?.trim() ?? "Kos Edge Desk";
    const angle = raw.match(/\*\*Angle:\*\*\s*(.+)$/im)?.[1]?.trim() ?? null;
    const sourceLinks = parseMarkdownLinks(refsBlob).slice(0, 4);
    items.push({
      team,
      teamName: byCode.get(team)?.name ?? team,
      author,
      angle,
      campRefsMarkdown: refsBlob,
      previewHref: `/pro/nfl/previews/${team}`,
      sourceLinks,
    });
  }
  return items.sort((a, b) => a.teamName.localeCompare(b.teamName));
}

async function fetchEspnNflArticles(limit = 50): Promise<CampNewsItem[]> {
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
    const items: CampNewsItem[] = [];
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

export async function fetchEspnCampNews(limit = 12): Promise<CampNewsItem[]> {
  const articles = await fetchEspnNflArticles(50);
  return articles
    .filter((item) => isCampRelevant(item.headline, item.description))
    .slice(0, limit);
}

export async function fetchEspnInjuryNews(limit = 10): Promise<CampNewsItem[]> {
  const articles = await fetchEspnNflArticles(50);
  return articles
    .filter((item) => isInjuryRelevant(item.headline, item.description))
    .slice(0, limit);
}

function buildBeats(registry: BeatRegistry | null): CampBeatLink[] {
  return NFL_TEAM_DIRECTORY.map((team) => {
    const entry = registry?.teams?.[team.code];
    const writers = entry?.writers ?? [];
    const primary =
      writers.find((w) => w.role === "primary") ?? writers[0] ?? null;
    return {
      team: team.code,
      teamName: team.name,
      division: entry?.division ?? `${team.conference} ${team.division}`,
      kosEdgeWriter: entry?.kos_edge_writer ?? "Desk",
      primaryWriter: primary?.name ?? null,
      primaryOutlet: primary?.outlet ?? null,
      primaryHandle: primary?.x?.[0] ?? null,
      espnCampHref: ESPN_TEAM_CAMP_HUBS[team.code] ?? null,
      previewHref: `/pro/nfl/previews/${team.code}`,
    };
  });
}

export async function buildNflCampDesk(): Promise<CampDeskPayload> {
  const registry = loadBeatRegistry();
  const articles = await fetchEspnNflArticles(50);
  const news = articles
    .filter((item) => isCampRelevant(item.headline, item.description))
    .slice(0, 14);
  const injuryNews = articles
    .filter((item) => isInjuryRelevant(item.headline, item.description))
    .slice(0, 8);
  const writerIntel = loadWriterCampIntel();
  const beats = buildBeats(registry);
  return {
    generatedAt: new Date().toISOString(),
    eraLabel: registry?.era ?? "training-camp",
    hubHref:
      "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
    news,
    injuryNews,
    writerIntel,
    beats,
    writers: WRITER_COVERAGE,
    notes: [
      "Camp Desk surfaces public beat hubs + ESPN camp news. Kos Edge writers own the Pass/Lean judgment — thin edges stay Pass.",
      "PRE boards use market + camp strength reference; season PLAY tags remain blocked under the info desk.",
      "Writer camp intel below is sourced from published 2026 season-preview beat refs — full news-break templates live in docs/writers/TRAINING_CAMP_DESK.md.",
    ],
    diagnostics: {
      newsCount: news.length,
      injuryNewsCount: injuryNews.length,
      writerIntelCount: writerIntel.length,
      beatCount: beats.length,
      beatRegistryVersion: registry?.version ?? null,
    },
  };
}
