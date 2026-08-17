import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  cardsFromDayFile,
  formatCampDeskDayLabel,
  isWithinCampDeskWindow,
  selectCampDeskCards,
  type CampDeskDayFile,
} from "@/lib/nfl-camp-desk-daily";

const AUG_12 = new Date("2026-08-12T16:00:00Z");
const AUG_16 = new Date("2026-08-16T16:00:00Z");

const fixture: CampDeskDayFile = {
  desk_date: "2026-08-07",
  pinned: false,
  source_type: "kosedge-desk",
  league_wrap: {
    title: "Camp Desk — Friday, Aug 7",
    bottom_line: "Stale wrap.",
    storylines: ["Old note"],
    what_to_watch: "Nothing.",
    sources: [],
  },
  team_notes: [
    {
      team_id: "BUF",
      title: "Bills camp — Aug 7",
      bottom_line: "Ancient history.",
      key_points: ["Pads"],
      what_to_watch: "Joints",
      is_material_depth: false,
      sources: [],
    },
  ],
};

describe("camp desk daily freshness", () => {
  it("labels the live day as a weekday + short month", () => {
    expect(formatCampDeskDayLabel("2026-08-12")).toMatch(/Wednesday,\s+Aug(?:ust)?\s+12/);
  });

  it("keeps notes inside 72h and buries older ones unless pinned", () => {
    expect(isWithinCampDeskWindow("2026-08-12", AUG_12)).toBe(true);
    expect(isWithinCampDeskWindow("2026-08-10", AUG_12)).toBe(true);
    expect(isWithinCampDeskWindow("2026-08-07", AUG_12)).toBe(false);
    expect(isWithinCampDeskWindow("2026-08-07", AUG_12, true)).toBe(true);
  });

  it("sorts newest KosEdge date first and keeps the league wrap above team notes", () => {
    const today: CampDeskDayFile = {
      ...fixture,
      desk_date: "2026-08-12",
      league_wrap: { ...fixture.league_wrap, title: "Camp Desk — Wednesday, Aug 12" },
      team_notes: [
        {
          ...fixture.team_notes[0],
          team_id: "MIN",
          title: "Vikings camp — Aug 12",
        },
      ],
    };
    const cards = selectCampDeskCards(
      [...cardsFromDayFile(fixture), ...cardsFromDayFile(today)],
      { now: AUG_12, inCamp: true },
    );
    expect(cards[0]?.kind).toBe("league_wrap");
    expect(cards[0]?.desk_date).toBe("2026-08-12");
    expect(cards.some((card) => card.desk_date === "2026-08-07")).toBe(false);
  });

  it("does not treat a 4-day-old wrap as live on Aug 16", () => {
    const today: CampDeskDayFile = {
      ...fixture,
      desk_date: "2026-08-12",
      league_wrap: { ...fixture.league_wrap, title: "Camp Desk — Wednesday, Aug 12" },
    };
    const cards = selectCampDeskCards(cardsFromDayFile(today), {
      now: AUG_16,
      inCamp: true,
    });
    expect(cards).toHaveLength(0);
  });
});

describe("Aug 17 live Camp Desk day", () => {
  const live = JSON.parse(
    readFileSync(
      path.join(
        __dirname,
        "../../../../content/writers/camp-desk-2026/2026-08-17.json",
      ),
      "utf8",
    ),
  ) as CampDeskDayFile;

  it("is a KosEdge-dated league wrap with all-32 notes and no vibe tags", () => {
    expect(live.desk_date).toBe("2026-08-17");
    expect(live.source_type).toBe("kosedge-desk");
    expect(live.league_wrap.title).toBe("Camp Desk — Monday, Aug 17");
    expect(live.league_wrap.storylines.length).toBeGreaterThanOrEqual(5);
    expect(live.league_wrap.storylines.length).toBeLessThanOrEqual(8);
    expect(live.team_notes.length).toBe(32);
    expect(live.league_wrap.bottom_line.toLowerCase()).toContain("pass");
    const blob = JSON.stringify(live);
    expect(blob).not.toMatch(/\bPLAY\b/);
    expect(blob).not.toMatch(/\bLEAN\b/);
    expect(blob.toLowerCase()).not.toContain("wire espn");
    expect(live.team_notes.some((note) => note.is_material_depth)).toBe(true);
    expect(live.preview_delta?.some((row) => row.team_id === "MIN")).toBe(true);
  });

  it("Camp Desk page heroes KosEdge cards and kills wire-ESPN branding", () => {
    const src = readFileSync(
      path.join(__dirname, "../../app/(pro)/pro/nfl/camp/page.tsx"),
      "utf8",
    );
    expect(src).toContain("KosEdge daily desk");
    expect(src).toContain("camp-desk-wrap");
    expect(src).toContain("PRESEASON");
    expect(src).toContain("Citation headlines (not the desk)");
    expect(src).toContain("Trusted X · beat map");
    expect(src).not.toContain("Wire · ESPN headlines");
    expect(src).not.toContain("Latest camp headlines");
    expect(src).not.toContain("formatArticleAttribution");
  });
});
