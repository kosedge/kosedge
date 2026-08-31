import { describe, expect, it } from "vitest";
import {
  DRAFT_HARD_OUT_STATUSES,
  filterDraftableRows,
  findDraftSit,
  isHardOutStatus,
  loadDraftAvailabilityBook,
} from "@/lib/fantasy/draft-availability";

describe("draft availability sits", () => {
  it("loads the 2026 sourced sit book with Jacobs exempt", () => {
    const book = loadDraftAvailabilityBook(2026);
    expect(book.sits.length).toBeGreaterThan(0);
    const jacobs = book.sits.find((s) => s.playerName === "Josh Jacobs");
    expect(jacobs).toBeTruthy();
    expect(jacobs!.team).toBe("GB");
    expect(jacobs!.position).toBe("RB");
    expect(isHardOutStatus(jacobs!.status)).toBe(true);
    expect(jacobs!.sources.length).toBeGreaterThan(0);
  });

  it("treats commissioner exempt / nfi / pup / ir as hard outs", () => {
    expect(isHardOutStatus("commissioner_exempt")).toBe(true);
    expect(isHardOutStatus("Commissioner's Exempt")).toBe(true);
    expect(isHardOutStatus("nfi")).toBe(true);
    expect(isHardOutStatus("Reserve/NFI")).toBe(true);
    expect(isHardOutStatus("pup")).toBe(true);
    expect(isHardOutStatus("ir")).toBe(true);
    expect(isHardOutStatus("questionable")).toBe(false);
    expect(DRAFT_HARD_OUT_STATUSES.has("commissioner_exempt")).toBe(true);
  });

  it("removes Jacobs and other sits from the draftable list", () => {
    const book = loadDraftAvailabilityBook(2026);
    const rows = [
      { playerName: "Josh Jacobs", team: "GB", position: "RB" },
      { playerName: "Jahmyr Gibbs", team: "DET", position: "RB" },
      { playerName: "Luke Musgrave", team: "GB", position: "TE" },
      { playerName: "James Conner", team: "ARI", position: "RB" },
      { playerName: "Jordyn Tyson", team: "NO", position: "WR" },
      { playerName: "Tank Dell", team: "HOU", position: "WR" },
    ];
    const { draftable, sat } = filterDraftableRows(rows, book);
    expect(draftable.map((r) => r.playerName)).toEqual(["Jahmyr Gibbs"]);
    expect(sat.map((s) => s.row.playerName).sort()).toEqual(
      [
        "James Conner",
        "Jordyn Tyson",
        "Josh Jacobs",
        "Luke Musgrave",
        "Tank Dell",
      ].sort(),
    );
    expect(findDraftSit(rows[0]!, book.sits)?.status).toBe(
      "commissioner_exempt",
    );
  });

  it("records DET / Arnold / Cooper as checked-not-on-board, not sits", () => {
    const book = loadDraftAvailabilityBook(2026);
    const names = book.checkedNotOnBoard.map((r) => r.playerName);
    expect(names).toContain("Brian Branch");
    expect(names).toContain("Kerby Joseph");
    expect(names).toContain("Cade Mays");
    expect(names).toContain("Giovanni Manu");
    expect(names).toContain("Terrion Arnold");
    expect(book.sits.some((s) => s.playerName === "Terrion Arnold")).toBe(
      false,
    );
  });

  it("leaves Kamara / Jeanty notes as left-up (no minted sit)", () => {
    const book = loadDraftAvailabilityBook(2026);
    const left = book.leftUpNotes.map((r) => r.playerName);
    expect(left).toContain("Alvin Kamara");
    expect(left).toContain("Ashton Jeanty");
    expect(book.sits.some((s) => s.playerName === "Alvin Kamara")).toBe(false);
  });
});
