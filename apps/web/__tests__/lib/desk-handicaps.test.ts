import { describe, expect, it } from "vitest";
import {
  getAllDeskHandicaps,
  getDeskHandicap,
  listDeskHandicapSlugs,
} from "@/lib/desk-handicaps";
import { extractHandicappersNotes } from "@/lib/article-sectionizer";

const EXPECTED_SLUGS = [
  "cfb-week1-g5-20260831-sam-reyes",
  "cfb-week1-p4-20260831-jordan-ellison",
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

const CFB_WEEK1_SLUGS = [
  "cfb-week1-g5-20260831-sam-reyes",
  "cfb-week1-p4-20260831-jordan-ellison",
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
      expect(article!.sport).toMatch(/^(NFL|WNBA|MLB|NBA|NHL|CFB)$/);
      expect(article!.href).toBe(`/pro/desk/${slug}`);
    }
  });

  it("parses CFB Week 1 Jordan + Sam slate notes with stamped PLAY / Pass discipline", () => {
    const jordan = getDeskHandicap("cfb-week1-p4-20260831-jordan-ellison")!;
    expect(jordan.byline).toBe("Jordan Ellison");
    expect(jordan.sport).toBe("CFB");
    expect(jordan.category).toBe("Desk handicap");
    expect(jordan.bodyMarkdown).toMatch(/PLAY MSU −10/);
    expect(jordan.bodyMarkdown).toMatch(/PLAY USC −22\.5/);
    expect(jordan.bodyMarkdown).toMatch(/PLAY Duke −8\.5/);
    expect(jordan.bodyMarkdown).toMatch(/−15\.84/);
    expect(jordan.bodyMarkdown).toMatch(/−27\.36/);
    expect(jordan.bodyMarkdown).not.toMatch(/64\.94/);
    expect(jordan.bodyMarkdown).toMatch(/Lean:\s*\*\*Pass\*\*/);
    const jordanNotes = extractHandicappersNotes(jordan.bodyMarkdown);
    const rutNote = jordanNotes.find((n) =>
      (n.label ?? "").toLowerCase().includes("mass"),
    );
    expect(rutNote?.lean?.replace(/\*\*/g, "")).toMatch(/Pass/i);
    const totalsNote = jordanNotes.find((n) =>
      (n.label ?? "").toLowerCase().includes("total"),
    );
    expect(totalsNote?.lean?.replace(/\*\*/g, "")).toMatch(/Pass/i);
    expect(jordan.bodyMarkdown).not.toMatch(/Lean:\s*\*\*PLAY.*Over/i);

    const sam = getDeskHandicap("cfb-week1-g5-20260831-sam-reyes")!;
    expect(sam.byline).toBe("Sam Reyes");
    expect(sam.sport).toBe("CFB");
    expect(sam.bodyMarkdown).toMatch(/PLAY JMU −6\.5/);
    expect(sam.bodyMarkdown).toMatch(/PLAY USF −13\.5/);
    expect(sam.bodyMarkdown).toMatch(/PLAY HAW \+3/);
    expect(sam.bodyMarkdown).toMatch(/PLAY ORST \+20\.5/);
    expect(sam.bodyMarkdown).toMatch(/PLAY WSU \+23\.5/);
    expect(sam.bodyMarkdown).toMatch(/PLAY TXST \+30\.5/);
    expect(sam.bodyMarkdown).toMatch(/LEAN MRSH \+24\.5/);
    expect(sam.bodyMarkdown).not.toMatch(/64\.94/);
    expect(sam.bodyMarkdown).not.toMatch(/sit(?:ting)? Toledo|SIT TOL|Toledo 0\.00/i);
    expect(sam.bodyMarkdown).toMatch(/No Toledo sit/i);
    const samNotes = extractHandicappersNotes(sam.bodyMarkdown);
    const samRut = samNotes.find((n) =>
      (n.label ?? "").toLowerCase().includes("mass"),
    );
    expect(samRut?.lean?.replace(/\*\*/g, "")).toMatch(/Pass/i);
    const samTotals = samNotes.find((n) =>
      (n.label ?? "").toLowerCase().includes("total"),
    );
    expect(samTotals?.lean?.replace(/\*\*/g, "")).toMatch(/Pass/i);
    expect(sam.bodyMarkdown).toMatch(/Total is Pass/i);

    for (const slug of CFB_WEEK1_SLUGS) {
      const article = getDeskHandicap(slug);
      expect(article, slug).not.toBeNull();
      expect(article!.sport).toBe("CFB");
      expect(article!.noteCount).toBeGreaterThanOrEqual(1);
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
      expect(article!.category).toBe("Current-state");
      expect(article!.byline).toMatch(/^(Avery Cole|Reese Quinn)$/);
      const notes = extractHandicappersNotes(article!.bodyMarkdown);
      expect(notes[0]?.lean?.replace(/\*\*/g, "")).toMatch(/Pass/i);
      expect(notes[0]?.fairNumber).toMatch(/Ch2|house net/i);
      expect(notes[0]?.marketNumber).toMatch(
        /18306835|UNLISTED|OTB|BetMGM|no (conference )?market/i,
      );
    }

    const min = getDeskHandicap("wnba-min-current-20260901-avery-cole")!;
    const minNotes = extractHandicappersNotes(min.bodyMarkdown);
    expect(min.byline).toBe("Avery Cole");
    expect(minNotes[0]?.marketNumber).toMatch(/BetMGM −115/);
    expect(minNotes[0]?.fairNumber).toMatch(/7\.03/);
    expect(minNotes[0]?.marketNumber).not.toMatch(/−125/);

    const lva = getDeskHandicap("wnba-lva-current-20260901-avery-cole")!;
    const lvaNotes = extractHandicappersNotes(lva.bodyMarkdown);
    expect(lvaNotes[0]?.fairNumber).toMatch(/4\.34/);
    expect(lva.bodyMarkdown).not.toMatch(/LAS 4\.34/);

    const west = getDeskHandicap("wnba-west-notes-20260901-avery-cole")!;
    const westNotes = extractHandicappersNotes(west.bodyMarkdown);
    expect(westNotes[0]?.marketNumber).toMatch(/OTB/i);
    expect(westNotes[0]?.marketNumber).toMatch(/no conference market/i);
    expect(westNotes[0]?.fairNumber).toMatch(/LA −1\.41/);
    expect(west.bodyMarkdown).not.toMatch(/LAS 4\.34/);

    const east = getDeskHandicap("wnba-east-notes-20260901-reese-quinn")!;
    const eastNotes = extractHandicappersNotes(east.bodyMarkdown);
    expect(east.byline).toBe("Reese Quinn");
    expect(eastNotes[0]?.marketNumber).toMatch(/18306835/);
    expect(eastNotes[0]?.marketNumber).toMatch(/no market/i);
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
