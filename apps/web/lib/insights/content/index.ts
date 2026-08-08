import type { SportKey } from "@/lib/sports";
import { SPORTS } from "@/lib/sports";
import type { InsightArticle } from "../types";
import {
  getDoctrineArticles,
  getDoctrineBySlug,
} from "./doctrine";
import {
  getAllDeskNotes,
  getDeskNoteBySlug,
  getDeskNotesBySport,
  getFreeDeskNotes,
  getRecentDeskNotes,
} from "./desk-notes";

export {
  getDoctrineArticles,
  getDoctrineBySlug,
  getAllDeskNotes,
  getDeskNoteBySlug,
  getDeskNotesBySport,
  getFreeDeskNotes,
  getRecentDeskNotes,
};

/** Featured desk note for Pro hub teaser (newest free or any recent). */
export function getFeaturedDeskNote(): InsightArticle | null {
  const recent = getRecentDeskNotes(21);
  return recent[0] ?? getAllDeskNotes()[0] ?? null;
}

export function getArticleBySlug(slug: string): InsightArticle | null {
  return getDoctrineBySlug(slug) ?? getDeskNoteBySlug(slug);
}

/** Sports that currently have at least one desk note or doctrine tag. */
export function getSportsWithInsights(): Array<{
  key: SportKey;
  label: string;
  fullName: string;
  noteCount: number;
  doctrineCount: number;
}> {
  const notes = getAllDeskNotes();
  const doctrine = getDoctrineArticles();

  return SPORTS.map((s) => {
    const noteCount = notes.filter((n) => n.sports?.includes(s.key)).length;
    const doctrineCount = doctrine.filter((d) =>
      d.sports?.includes(s.key),
    ).length;
    return {
      key: s.key,
      label: s.label,
      fullName: s.fullName,
      noteCount,
      doctrineCount,
    };
  }).filter((s) => s.noteCount + s.doctrineCount > 0);
}

/**
 * Visibility for a desk note given Pro status.
 * Doctrine is always fully visible (free philosophy).
 */
export function canReadFullArticle(
  article: InsightArticle,
  isPro: boolean,
): boolean {
  if (article.kind === "doctrine") return true;
  if (article.tier === "free") return true;
  return isPro;
}

/** Free users get full free notes; Pro notes as teaser cards only. */
export function partitionDeskNotesForUser(
  notes: InsightArticle[],
  isPro: boolean,
): {
  visible: InsightArticle[];
  teaserOnly: InsightArticle[];
} {
  if (isPro) {
    return { visible: notes, teaserOnly: [] };
  }
  const visible = notes.filter((n) => n.tier === "free");
  const teaserOnly = notes.filter((n) => n.tier === "pro");
  return { visible, teaserOnly };
}
