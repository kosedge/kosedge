import "server-only";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { NFL_TEAM_DIRECTORY, teamDisplayName } from "@/lib/nfl-team-intel";

export type NflSeasonPreviewMeta = {
  team: string;
  teamName: string;
  title: string;
  author: string;
  desk: string | null;
  angle: string | null;
  market: string | null;
  sources: string | null;
  href: string;
  excerpt: string;
};

export type NflSeasonPreviewArticle = NflSeasonPreviewMeta & {
  bodyMarkdown: string;
  wordCount: number;
};

function findRepoRoot(): string | null {
  let current = process.cwd();
  for (let depth = 0; depth < 6; depth += 1) {
    const candidate = path.join(
      current,
      "content",
      "writers",
      "season-previews-2026",
    );
    if (existsSync(candidate)) return current;
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return null;
}

function previewsDir(): string | null {
  const root = findRepoRoot();
  if (!root) return null;
  const dir = path.join(root, "content", "writers", "season-previews-2026");
  return existsSync(dir) ? dir : null;
}

function extractField(source: string, label: string): string | null {
  const pattern = new RegExp(`\\*\\*${label}:\\*\\*\\s*(.+?)\\s*$`, "im");
  const match = source.match(pattern);
  return match?.[1]?.trim() || null;
}

function extractAuthor(source: string): { author: string; desk: string | null } {
  const match = source.match(
    /\*\*By\s+([^*]+?)\*\*\s*·\s*Kos Edge Analytics(?:\s*·\s*([^\n]+))?/i,
  );
  if (!match) return { author: "Kos Edge Desk", desk: null };
  return {
    author: match[1].trim(),
    desk: match[2]?.trim() || null,
  };
}

function firstParagraph(source: string): string {
  const lines = source.split(/\r?\n/);
  const chunks: string[] = [];
  let started = false;
  for (const line of lines) {
    const trimmed = line.trim();
    if (!started) {
      if (
        !trimmed ||
        trimmed.startsWith("#") ||
        trimmed.startsWith("**") ||
        trimmed.startsWith("|") ||
        trimmed.startsWith("-")
      ) {
        continue;
      }
      started = true;
    }
    if (!trimmed) break;
    if (trimmed.startsWith("#")) break;
    chunks.push(trimmed.replace(/\*\*/g, ""));
    if (chunks.join(" ").length > 220) break;
  }
  const text = chunks.join(" ").replace(/\s+/g, " ").trim();
  if (text.length <= 240) return text;
  return `${text.slice(0, 237).trimEnd()}…`;
}

function parsePreviewFile(
  team: string,
  raw: string,
): NflSeasonPreviewArticle | null {
  const titleMatch = raw.match(/^#\s+(.+)$/m);
  const title = titleMatch?.[1]?.trim() || `${teamDisplayName(team)} 2026 Season Preview`;
  const { author, desk } = extractAuthor(raw);
  const angle = extractField(raw, "Angle");
  const market =
    extractField(raw, "Market \\(DK/RotoWire, late July 2026\\)") ||
    extractField(raw, "Market");
  const sources =
    extractField(raw, "Sources \\(beat desk\\)") ||
    extractField(raw, "Sources");

  // Drop the H1 from body so the page can own the title.
  const bodyMarkdown = raw.replace(/^#\s+.+\n+/, "").trim();
  const wordCount = bodyMarkdown.split(/\s+/).filter(Boolean).length;
  if (wordCount < 100) return null;

  return {
    team: team.toUpperCase(),
    teamName: teamDisplayName(team),
    title,
    author,
    desk,
    angle,
    market,
    sources,
    href: `/pro/nfl/previews/${team.toUpperCase()}`,
    excerpt: firstParagraph(raw),
    bodyMarkdown,
    wordCount,
  };
}

export function listNflSeasonPreviewTeams(): string[] {
  const dir = previewsDir();
  if (!dir) return [];
  return readdirSync(dir)
    .filter((name) => name.endsWith(".md") && name !== "INDEX.md")
    .map((name) => name.replace(/\.md$/, "").toUpperCase())
    .sort((a, b) => a.localeCompare(b));
}

export function getNflSeasonPreview(
  team: string,
): NflSeasonPreviewArticle | null {
  const dir = previewsDir();
  if (!dir) return null;
  const code = team.trim().toUpperCase();
  const filePath = path.join(dir, `${code}.md`);
  if (!existsSync(filePath)) return null;
  try {
    const raw = readFileSync(filePath, "utf8");
    return parsePreviewFile(code, raw);
  } catch {
    return null;
  }
}

export function getAllNflSeasonPreviews(): NflSeasonPreviewMeta[] {
  const teams = listNflSeasonPreviewTeams();
  const byCode = new Map(
    NFL_TEAM_DIRECTORY.map((entry) => [entry.code, entry] as const),
  );
  const articles: NflSeasonPreviewMeta[] = [];
  for (const team of teams) {
    const article = getNflSeasonPreview(team);
    if (!article) continue;
    articles.push({
      team: article.team,
      teamName: byCode.get(team)?.name ?? article.teamName,
      title: article.title,
      author: article.author,
      desk: article.desk,
      angle: article.angle,
      market: article.market,
      sources: article.sources,
      href: article.href,
      excerpt: article.excerpt,
    });
  }
  return articles.sort((a, b) => a.teamName.localeCompare(b.teamName));
}

export function groupPreviewsByConference(articles: NflSeasonPreviewMeta[]) {
  const byCode = new Map(
    NFL_TEAM_DIRECTORY.map((entry) => [entry.code, entry] as const),
  );
  const groups: Array<{
    conference: string;
    division: string;
    articles: NflSeasonPreviewMeta[];
  }> = [];
  const order = ["AFC", "NFC"];
  const divOrder = ["East", "North", "South", "West"];

  for (const conference of order) {
    for (const division of divOrder) {
      const articlesInDiv = articles.filter((article) => {
        const entry = byCode.get(article.team);
        return entry?.conference === conference && entry?.division === division;
      });
      if (articlesInDiv.length > 0) {
        groups.push({ conference, division, articles: articlesInDiv });
      }
    }
  }
  return groups;
}
