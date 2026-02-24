import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";

export type MdxFrontmatter = {
  title: string;
  description?: string;
  date: string; // ISO recommended: 2026-01-26
  author?: string;
  tags?: string[];
  tier?: "free" | "pro";
};

const CONTENT_DIR = path.join(process.cwd(), "content");

export function getMdxSlugs(section: "insights" | "articles") {
  const dir = path.join(CONTENT_DIR, section);
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".mdx"))
    .map((f) => f.replace(/\.mdx$/, ""));
}

export function getMdxBySlug(section: "insights" | "articles", slug: string) {
  const filePath = path.join(CONTENT_DIR, section, `${slug}.mdx`);
  const raw = fs.readFileSync(filePath, "utf8");
  const { content, data } = matter(raw);

  return {
    slug,
    content,
    frontmatter: data as MdxFrontmatter,
  };
}

export function getAllMdx(section: "insights" | "articles") {
  return getMdxSlugs(section)
    .map((slug) => getMdxBySlug(section, slug))
    .sort((a, b) => (a.frontmatter.date < b.frontmatter.date ? 1 : -1));
}