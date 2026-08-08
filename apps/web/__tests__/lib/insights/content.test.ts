import { describe, expect, it } from "vitest";
import {
  canReadFullArticle,
  getDoctrineArticles,
  getDoctrineBySlug,
  getAllDeskNotes,
  getSportsWithInsights,
  partitionDeskNotesForUser,
} from "@/lib/insights/content";

describe("insights content", () => {
  it("ships the core doctrine set without public module numbers", () => {
    const doctrine = getDoctrineArticles();
    expect(doctrine.length).toBe(10);

    for (const article of doctrine) {
      expect(article.kind).toBe("doctrine");
      expect(article.tier).toBe("free");
      expect(article.title).not.toMatch(/^\d+\.\d+/);
      expect(article.bottomLine.length).toBeGreaterThan(20);
      expect(article.keyPoints.length).toBeGreaterThan(0);
      expect(article.sections.length).toBeGreaterThan(0);
      expect(article.whatToDo.length).toBeGreaterThan(0);
    }

    expect(getDoctrineBySlug("threshold-discipline")?.title).toBe(
      "Threshold Discipline",
    );
  });

  it("scaffolds dated desk notes with free/pro split", () => {
    const notes = getAllDeskNotes();
    expect(notes.length).toBeGreaterThanOrEqual(3);

    const free = notes.filter((n) => n.tier === "free");
    const pro = notes.filter((n) => n.tier === "pro");
    expect(free.length).toBeGreaterThanOrEqual(1);
    expect(pro.length).toBeGreaterThanOrEqual(1);

    for (const note of notes) {
      expect(note.kind).toBe("desk-note");
      expect(note.title).not.toMatch(/^\d+\.\d+/);
      expect(note.updatedAt).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    }
  });

  it("gates Pro desk notes but never doctrine", () => {
    const doctrine = getDoctrineBySlug("make-our-number-first");
    expect(doctrine).toBeTruthy();
    expect(canReadFullArticle(doctrine!, false)).toBe(true);

    const proNote = getAllDeskNotes().find((n) => n.tier === "pro");
    expect(proNote).toBeTruthy();
    expect(canReadFullArticle(proNote!, false)).toBe(false);
    expect(canReadFullArticle(proNote!, true)).toBe(true);

    const partitioned = partitionDeskNotesForUser(getAllDeskNotes(), false);
    expect(partitioned.visible.every((n) => n.tier === "free")).toBe(true);
    expect(partitioned.teaserOnly.every((n) => n.tier === "pro")).toBe(true);
  });

  it("only lists sports that have content", () => {
    const sports = getSportsWithInsights();
    expect(sports.length).toBeGreaterThan(0);
    expect(sports.every((s) => s.noteCount + s.doctrineCount > 0)).toBe(true);
  });
});
