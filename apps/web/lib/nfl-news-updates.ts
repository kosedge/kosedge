import "server-only";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { teamDisplayName } from "@/lib/nfl-team-intel";
import { extractInlineSources, extractHandicappersNote } from "@/lib/article-sectionizer";

export type NflNewsUpdateMeta = {
  slug: string;
  title: string;
  shortTitle: string;
  team: string | null;
  teamName: string | null;
  category: string;
  publishedAt: string;
  dek: string | null;
  sources: string | null;
  href: string;
  excerpt: string;
};

export type NflNewsUpdateArticle = NflNewsUpdateMeta & {
  bodyMarkdown: string;
  wordCount: number;
};

function findRepoRoot(): string | null {
  let current = process.cwd();
  for (let depth = 0; depth < 6; depth += 1) {
    const candidate = path.join(current, "content", "writers", "news-breaks-2026");
    if (existsSync(candidate)) return current;
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return null;
}

function newsDir(): string | null {
  const root = findRepoRoot();
  if (!root) return null;
  const dir = path.join(root, "content", "writers", "news-breaks-2026");
  return existsSync(dir) ? dir : null;
}

function extractField(source: string, label: string): string | null {
  const pattern = new RegExp(`\\*\\*${label}:\\*\\*\\s*(.+?)\\s*$`, "im");
  return source.match(pattern)?.[1]?.trim() ?? null;
}

function firstParagraph(source: string): string {
  const lines = source.split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (
      !trimmed ||
      trimmed.startsWith("#") ||
      trimmed.startsWith("**") ||
      trimmed.startsWith("-")
    ) {
      continue;
    }
    return trimmed.replace(/\*\*/g, "");
  }
  return "";
}

function parseNewsFile(slug: string, raw: string): NflNewsUpdateArticle | null {
  const titleMatch = raw.match(/^#\s+(.+)$/m);
  const title = titleMatch?.[1]?.trim() ?? slug;
  const timestamp =
    extractField(raw, "Timestamp") ??
    extractField(raw, "Date") ??
    "August 2026";
  const teamCode = extractField(raw, "Team")?.toUpperCase() ?? null;
  const category = extractField(raw, "Category") ?? "Camp News Break";
  const sources =
    extractField(raw, "Sources") ?? extractInlineSources(raw);

  // Header owns KosEdge attribution — strip timestamp/meta and any writer byline.
  const bodyMarkdown = raw
    .replace(/^#\s+.+\n+/, "")
    .replace(/^\*\*Timestamp:\*\*[^\n]*\n+/im, "")
    .replace(/^\*\*Date:\*\*[^\n]*\n+/im, "")
    .replace(/^\*\*Team:\*\*[^\n]*\n+/im, "")
    .replace(/^\*\*Category:\*\*[^\n]*\n+/im, "")
    .replace(/^\*\*Sources:\*\*[^\n]*\n+/im, "")
    .replace(/^\*\*By\s+[^*]+\*\*\s*·?[^\n]*\n+/im, "")
    .replace(/^By\s+[^\n]+\n+/im, "")
    .trim();

  const wordCount = bodyMarkdown.split(/\s+/).filter(Boolean).length;
  if (wordCount < 40) return null;

  const shortTitle =
    title.length > 48 ? `${title.slice(0, 45).trimEnd()}…` : title;

  return {
    slug,
    title,
    shortTitle,
    team: teamCode,
    teamName: teamCode ? teamDisplayName(teamCode) : null,
    category,
    publishedAt: timestamp,
    dek: firstParagraph(bodyMarkdown),
    sources,
    href: `/pro/nfl/news/${slug}`,
    excerpt: firstParagraph(bodyMarkdown),
    bodyMarkdown,
    wordCount,
  };
}

export function listNflNewsUpdateSlugs(): string[] {
  const dir = newsDir();
  if (!dir) return [];
  return readdirSync(dir)
    .filter((name) => name.endsWith(".md") && name !== "INDEX.md")
    .map((name) => name.replace(/\.md$/, ""))
    .sort((a, b) => a.localeCompare(b));
}

export function getNflNewsUpdate(slug: string): NflNewsUpdateArticle | null {
  const dir = newsDir();
  if (!dir) return null;
  const filePath = path.join(dir, `${slug}.md`);
  if (!existsSync(filePath)) return null;
  try {
    const raw = readFileSync(filePath, "utf8");
    return parseNewsFile(slug, raw);
  } catch {
    return null;
  }
}

function publishedSortKey(value: string): number {
  // Prefer the date portion before "·" so "August 7, 2026 · 2:00 PM ET" sorts.
  const datePart = value.split("·")[0]?.trim() ?? value;
  const ts = Date.parse(datePart);
  return Number.isFinite(ts) ? ts : 0;
}

export function getAllNflNewsUpdates(): NflNewsUpdateMeta[] {
  return listNflNewsUpdateSlugs()
    .map((slug) => getNflNewsUpdate(slug))
    .filter((article): article is NflNewsUpdateArticle => article !== null)
    .map(({ bodyMarkdown: _body, wordCount: _wc, ...meta }) => meta)
    .sort(
      (a, b) =>
        publishedSortKey(b.publishedAt) - publishedSortKey(a.publishedAt) ||
        a.slug.localeCompare(b.slug),
    );
}

export function summarizeNewsLean(bodyMarkdown: string): string | null {
  return extractHandicappersNote(bodyMarkdown).lean;
}
