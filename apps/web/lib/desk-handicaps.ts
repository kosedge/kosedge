import "server-only";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import {
  extractHandicappersNotes,
  extractInlineSources,
} from "@/lib/article-sectionizer";

export type DeskSport = "NFL" | "WNBA" | "MLB" | "NBA" | "NHL";

export type DeskHandicapMeta = {
  slug: string;
  title: string;
  shortTitle: string;
  byline: string;
  bylineFull: string;
  sport: DeskSport | string;
  category: string;
  angle: string | null;
  publishedAt: string;
  sources: string | null;
  href: string;
  excerpt: string;
};

export type DeskHandicapArticle = DeskHandicapMeta & {
  bodyMarkdown: string;
  wordCount: number;
  noteCount: number;
};

function findRepoRoot(): string | null {
  let current = process.cwd();
  for (let depth = 0; depth < 6; depth += 1) {
    const candidate = path.join(current, "content", "writers", "desk-2026");
    if (existsSync(candidate)) return current;
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return null;
}

function deskDir(): string | null {
  const root = findRepoRoot();
  if (!root) return null;
  const dir = path.join(root, "content", "writers", "desk-2026");
  return existsSync(dir) ? dir : null;
}

function extractField(source: string, label: string): string | null {
  const pattern = new RegExp(`\\*\\*${label}:\\*\\*\\s*(.+?)\\s*$`, "im");
  return source.match(pattern)?.[1]?.trim() ?? null;
}

function extractByline(source: string): { name: string; full: string } | null {
  const bold = source.match(/^\*\*By\s+([^*]+)\*\*((?:\s*·\s*[^\n]+)*)\s*$/im);
  if (bold) {
    const name = bold[1].trim();
    const rest = (bold[2] ?? "").trim();
    const full = rest
      ? `By ${name} ${rest}`.replace(/\s+/g, " ").trim()
      : `By ${name}`;
    return { name, full };
  }
  const plain = source.match(/^By\s+([^\n·|]+)(?:\s*[·|]\s*[^\n]+)?\s*$/im);
  if (plain) {
    const name = plain[1].trim();
    return { name, full: plain[0].trim() };
  }
  return null;
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

/**
 * Strip chrome meta into ArticleShell; keep body prose + Handicapper notes.
 * Unlike camp news-breaks, the byline is preserved on the article model for chrome.
 */
function stripDeskChrome(raw: string): string {
  return raw
    .replace(/^#\s+.+\n+/, "")
    .replace(/^\*\*By\s+[^*]+\*\*\s*·?[^\n]*\n+/im, "")
    .replace(/^By\s+[^\n]+\n+/im, "")
    .replace(/^\*\*Sport:\*\*[^\n]*\n+/im, "")
    .replace(/^\*\*Category:\*\*[^\n]*\n+/im, "")
    .replace(/^\*\*Angle:\*\*[^\n]*\n+/im, "")
    .replace(/^\*\*Date:\*\*[^\n]*\n+/im, "")
    .replace(/^\*\*Timestamp:\*\*[^\n]*\n+/im, "")
    .replace(/^\*\*Market fact-check:\*\*[^\n]*\n+/im, "")
    .replace(/^\*\*Kos Edge \/ KEICMB:\*\*[^\n]*\n+/im, "")
    .replace(/^\*\*Market(?:\s*\([^)]*\))?:\*\*[^\n]*\n+/im, "")
    .replace(/^\*\*Opening(?:\s*\([^)]*\))?:\*\*[^\n]*\n+/im, "")
    .replace(/^\*\*Sources:\*\*[^\n]*\n+/im, "")
    .trim();
}

function parseDeskFile(slug: string, raw: string): DeskHandicapArticle | null {
  const titleMatch = raw.match(/^#\s+(.+)$/m);
  const title = titleMatch?.[1]?.trim() ?? slug;
  const bylineInfo = extractByline(raw);
  if (!bylineInfo) return null;

  const timestamp =
    extractField(raw, "Timestamp") ??
    extractField(raw, "Date") ??
    "August 2026";
  const sport = extractField(raw, "Sport") ?? "NFL";
  const category = extractField(raw, "Category") ?? "Desk handicap";
  const angle = extractField(raw, "Angle");
  const sources = extractField(raw, "Sources") ?? extractInlineSources(raw);

  const bodyMarkdown = stripDeskChrome(raw);
  const notes = extractHandicappersNotes(bodyMarkdown);
  const noteCount = notes.filter(
    (n) => n.lean || n.fairNumber || n.marketNumber || n.raw,
  ).length;
  if (noteCount < 1) return null;

  const wordCount = bodyMarkdown.split(/\s+/).filter(Boolean).length;
  if (wordCount < 40) return null;

  const shortTitle =
    title.length > 48 ? `${title.slice(0, 45).trimEnd()}…` : title;

  return {
    slug,
    title,
    shortTitle,
    byline: bylineInfo.name,
    bylineFull: bylineInfo.full,
    sport,
    category,
    angle,
    publishedAt: timestamp,
    sources,
    href: `/pro/desk/${slug}`,
    excerpt: angle?.replace(/\*\*/g, "") || firstParagraph(bodyMarkdown),
    bodyMarkdown,
    wordCount,
    noteCount,
  };
}

export function listDeskHandicapSlugs(): string[] {
  const dir = deskDir();
  if (!dir) return [];
  return readdirSync(dir)
    .filter((name) => name.endsWith(".md") && name !== "README.md")
    .map((name) => name.replace(/\.md$/, ""))
    .sort((a, b) => a.localeCompare(b));
}

export function getDeskHandicap(slug: string): DeskHandicapArticle | null {
  const dir = deskDir();
  if (!dir) return null;
  const filePath = path.join(dir, `${slug}.md`);
  if (!existsSync(filePath)) return null;
  try {
    const raw = readFileSync(filePath, "utf8");
    return parseDeskFile(slug, raw);
  } catch {
    return null;
  }
}

function publishedSortKey(value: string): number {
  const datePart = value.split("·")[0]?.trim() ?? value;
  const ts = Date.parse(datePart);
  return Number.isFinite(ts) ? ts : 0;
}

export function getAllDeskHandicaps(): DeskHandicapMeta[] {
  return listDeskHandicapSlugs()
    .map((slug) => getDeskHandicap(slug))
    .filter((article): article is DeskHandicapArticle => article !== null)
    .map(
      ({ bodyMarkdown: _body, wordCount: _wc, noteCount: _nc, ...meta }) =>
        meta,
    )
    .sort(
      (a, b) =>
        publishedSortKey(b.publishedAt) - publishedSortKey(a.publishedAt) ||
        a.slug.localeCompare(b.slug),
    );
}
