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
  "den-wins-2026-reese-quinn",
  "gb-min-week1-casey-voss",
  "gsv-por-aug30-avery-cole",
  "min-edwards-ball-wins-2026-reese-quinn",
  "min-wolves-wins-2026-reese-quinn",
  "nba-northwest-notes-20260901-reese-quinn",
  "okc-wins-2026-reese-quinn",
  "por-wins-2026-reese-quinn",
  "uta-wins-2026-reese-quinn",
  "wnba-atl-current-20260901-reese-quinn",
  "wnba-dal-current-20260901-avery-cole",
  "wnba-east-notes-20260901-reese-quinn",
  "wnba-gsv-current-20260901-avery-cole",
  "wnba-ind-current-20260901-reese-quinn",
  "wnba-lva-current-20260901-avery-cole",
  "wnba-min-current-20260901-avery-cole",
  "wnba-nyl-current-20260901-reese-quinn",
  "wnba-was-current-20260901-reese-quinn",
  "wnba-west-notes-20260901-avery-cole",
] as const;

const REESE_NORTHWEST_SLUGS = [
  "den-wins-2026-reese-quinn",
  "min-edwards-ball-wins-2026-reese-quinn",
  "nba-northwest-notes-20260901-reese-quinn",
  "okc-wins-2026-reese-quinn",
  "por-wins-2026-reese-quinn",
  "uta-wins-2026-reese-quinn",
] as const;

const WNBA_SEP1_SLUGS = [
  "wnba-atl-current-20260901-reese-quinn",
  "wnba-dal-current-20260901-avery-cole",
  "wnba-east-notes-20260901-reese-quinn",
  "wnba-gsv-current-20260901-avery-cole",
  "wnba-ind-current-20260901-reese-quinn",
  "wnba-lva-current-20260901-avery-cole",
  "wnba-min-current-20260901-avery-cole",
  "wnba-nyl-current-20260901-reese-quinn",
  "wnba-was-current-20260901-reese-quinn",
  "wnba-west-notes-20260901-avery-cole",
] as const;

describe("desk-handicaps loader", () => {
  it("lists all live desk slugs including Reese NBA Northwest", () => {
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

  it("parses Reese Quinn NBA Northwest looks as Pass leans", () => {
    for (const slug of REESE_NORTHWEST_SLUGS) {
      const article = getDeskHandicap(slug);
      expect(article, slug).not.toBeNull();
      expect(article!.byline).toBe("Reese Quinn");
      expect(article!.sport).toBe("NBA");
      const notes = extractHandicappersNotes(article!.bodyMarkdown);
      expect(notes[0]?.lean?.replace(/\*\*/g, "")).toMatch(/Pass/i);
    }

    const notesPiece = getDeskHandicap(
      "nba-northwest-notes-20260901-reese-quinn",
    )!;
    const notes = extractHandicappersNotes(notesPiece.bodyMarkdown);
    expect(notes[0]?.label).toBe("division");
    expect(notes[0]?.marketNumber).toMatch(/BetMGM live/i);
    expect(notes[0]?.marketNumber).toMatch(/19665729/);
    expect(notes[0]?.marketNumber).not.toMatch(/live sportsbook sat/i);
  });

  it("parses Sep 1 WNBA current-state cards as Pass leans on live BetMGM 18306835", () => {
    for (const slug of WNBA_SEP1_SLUGS) {
      const article = getDeskHandicap(slug);
      expect(article, slug).not.toBeNull();
      expect(article!.sport).toBe("WNBA");
      expect(article!.byline).toMatch(/^(Avery Cole|Reese Quinn)$/);
      const notes = extractHandicappersNotes(article!.bodyMarkdown);
      expect(notes[0]?.lean?.replace(/\*\*/g, "")).toMatch(/Pass/i);
      expect(notes[0]?.fairNumber).toMatch(/Ch2/i);
      expect(notes[0]?.marketNumber).toMatch(/18306835|OTB|NO MARKET/i);
      expect(notes[0]?.marketNumber).not.toMatch(/Aug 27 BetMGM blog last dated MIN/i);
    }

    const min = getDeskHandicap("wnba-min-current-20260901-avery-cole")!;
    const minNotes = extractHandicappersNotes(min.bodyMarkdown);
    expect(min.byline).toBe("Avery Cole");
    expect(minNotes[0]?.marketNumber).toMatch(/MIN.*−115|MIN \*\*−115\*/);
    expect(minNotes[0]?.marketNumber).not.toMatch(/−125/);

    const west = getDeskHandicap("wnba-west-notes-20260901-avery-cole")!;
    const westNotes = extractHandicappersNotes(west.bodyMarkdown);
    expect(westNotes[0]?.marketNumber).toMatch(/OTB/i);

    const east = getDeskHandicap("wnba-east-notes-20260901-reese-quinn")!;
    const eastNotes = extractHandicappersNotes(east.bodyMarkdown);
    expect(east.byline).toBe("Reese Quinn");
    expect(eastNotes[0]?.marketNumber).toMatch(/NO MARKET/i);
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
    expect(all).toHaveLength(EXPECTED_SLUGS.length);
    expect(all.every((a) => a.byline && a.href.startsWith("/pro/desk/"))).toBe(
      true,
    );
  });
});
