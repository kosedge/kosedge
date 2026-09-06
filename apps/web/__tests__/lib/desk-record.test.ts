import { describe, expect, it } from "vitest";
import {
  americanProfit,
  formatAts,
  formatJuice,
  loadDeskRecord,
  summarizeDeskTickets,
  type DeskRecordTicket,
} from "@/lib/desk-record";

describe("desk-record contract", () => {
  it("computes American profit without inventing flat -110", () => {
    expect(americanProfit(1, -110, true)).toBeCloseTo(100 / 110, 6);
    expect(americanProfit(1, -105, true)).toBeCloseTo(100 / 105, 6);
    expect(americanProfit(0.5, -110, false)).toBe(-0.5);
    expect(americanProfit(1, 150, true)).toBeCloseTo(1.5, 6);
  });

  it("formats DATA GAP juice honestly", () => {
    expect(formatJuice(null, "DATA_GAP")).toBe("DATA GAP");
    expect(formatJuice(-110, "stamped")).toBe("-110");
    expect(formatJuice(105, "stamped")).toBe("+105");
  });

  it("excludes pushes from risked and marks missing juice as DATA_GAP ROI", () => {
    const tickets: DeskRecordTicket[] = [
      {
        ticket_id: "a",
        sport: "cfb",
        season: 2026,
        week: 1,
        game: "A @ B",
        away: "A",
        home: "B",
        market: "spread",
        side: "B",
        grade: "PLAY",
        line: -10,
        juice: null,
        book: "DraftKings",
        as_of: "2026-08-31T16:32:00-04:00",
        result: "P",
        stake_u: 1,
        profit_u: 0,
        juice_status: "DATA_GAP",
        final_away: 20,
        final_home: 30,
        source_package: "x.md",
      },
      {
        ticket_id: "b",
        sport: "cfb",
        season: 2026,
        week: 1,
        game: "C @ D",
        away: "C",
        home: "D",
        market: "spread",
        side: "D",
        grade: "PLAY",
        line: -7.5,
        juice: null,
        book: "DraftKings",
        as_of: "2026-08-31T16:32:00-04:00",
        result: "W",
        stake_u: 1,
        profit_u: null,
        juice_status: "DATA_GAP",
        final_away: 10,
        final_home: 24,
        source_package: "x.md",
      },
      {
        ticket_id: "c",
        sport: "cfb",
        season: 2026,
        week: 1,
        game: "E @ F",
        away: "E",
        home: "F",
        market: "spread",
        side: "E",
        grade: "LEAN",
        line: 3,
        juice: -105,
        book: "FanDuel",
        as_of: "2026-08-31T16:32:00-04:00",
        result: "W",
        stake_u: 0.5,
        profit_u: null,
        juice_status: "stamped",
        final_away: 17,
        final_home: 14,
        source_package: "x.md",
      },
    ];

    const summary = summarizeDeskTickets(tickets, "cfb", 2026);
    expect(summary.play_ats_str).toBe("1-0-1");
    expect(summary.lean_ats_str).toBe("1-0-0");
    expect(summary.combined_roi.status).toBe("ok");
    expect(summary.combined_roi.n_data_gap).toBe(1);
    expect(summary.combined_roi.risked_u).toBe(0.5);
    expect(summary.combined_roi.profit_u).toBeCloseTo(0.5 * (100 / 105), 5);
  });

  it("loads CFB Week 1 seed with PLAY 4-3-1, LEAN 0-1, ROI DATA GAP", () => {
    const summary = loadDeskRecord("cfb", 2026);
    expect(summary.n_tickets).toBe(10);
    expect(summary.play_ats_str).toBe("4-3-1");
    expect(summary.lean_ats_str).toBe("0-1-0");
    expect(summary.n_open).toBe(1);
    expect(summary.combined_roi.status).toBe("DATA_GAP");
    expect(summary.tickets.every((t) => t.grade === "PLAY" || t.grade === "LEAN")).toBe(
      true,
    );
    expect(formatAts(summary.play_ats)).toBe("4-3-1");
  });

  it("keeps NFL skeleton empty (no invented grades)", () => {
    const summary = loadDeskRecord("nfl", 2026);
    expect(summary.n_tickets).toBe(0);
    expect(summary.combined_roi.status).toBe("empty");
  });
});
