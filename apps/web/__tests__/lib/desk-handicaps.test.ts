import { describe, expect, it } from "vitest";
import {
  getAllDeskHandicaps,
  getDeskHandicap,
  listDeskHandicapSlugs,
} from "@/lib/desk-handicaps";
import { extractHandicappersNotes } from "@/lib/article-sectionizer";

const EXPECTED_SLUGS = [
  "cin-chc-aug30-taylor-brooks",
  "col-points-2026-morgan-hale",
  "gb-min-week1-casey-voss",
  "gsv-por-aug30-avery-cole",
  "min-wolves-wins-2026-reese-quinn",
] as const;

describe("desk-handicaps loader", () => {
  it("lists the five first-live desk slugs", () => {
    expect(listDeskHandicapSlugs()).toEqual([...EXPECTED_SLUGS]);
  });

  it("parses each slug with byline and at least one Handicapper's Note", () => {
    for (const slug of EXPECTED_SLUGS) {
      const article = getDeskHandicap(slug);
      expect(article, slug).not.toBeNull();
      expect(article!.byline.length).toBeGreaterThan(0);
      expect(article!.bylineFull).toMatch(/^By /);
      expect(article!.noteCount).toBeGreaterThanOrEqual(1);
      expect(article!.sport).toMatch(/^(NFL|WNBA|MLB|NBA|NHL)$/);
      expect(article!.href).toBe(`/pro/desk/${slug}`);
    }
  });

  it("keeps Casey and Taylor dual Handicapper's Notes", () => {
    const casey = getDeskHandicap("gb-min-week1-casey-voss")!;
    const caseyNotes = extractHandicappersNotes(casey.bodyMarkdown);
    expect(caseyNotes.map((n) => n.label)).toEqual(["Spread", "Total"]);
    expect(casey.byline).toBe("Casey Voss");

    const taylor = getDeskHandicap("cin-chc-aug30-taylor-brooks")!;
    const taylorNotes = extractHandicappersNotes(taylor.bodyMarkdown);
    expect(taylorNotes.map((n) => n.label)).toEqual(["Side", "Total"]);
    expect(taylor.byline).toBe("Taylor Brooks");
  });

  it("returns index meta sorted newest-first with bylines intact", () => {
    const all = getAllDeskHandicaps();
    expect(all).toHaveLength(5);
    expect(all.every((a) => a.byline && a.href.startsWith("/pro/desk/"))).toBe(
      true,
    );
  });
});
