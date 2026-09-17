import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  EDGE_BOARD_ASSEMBLE_HONESTY_MS,
  edgeBoardAssembleHonestyCopy,
  recallEdgeBoardLinesAsOf,
  rememberEdgeBoardLinesAsOf,
} from "@/lib/edge-board-assemble-honesty";
import {
  MATCHUP_OVERVIEW_FLIPS_HEADING,
  scrubEdgeBoardAssembleCustomerRow,
  scrubEdgeBoardAssembleCustomerRows,
  scrubMatchupOverviewWatchHeading,
} from "@/lib/edge-board-assemble-quarantine";
import type { EdgeBoardRow } from "@kosedge/contracts";

const webRoot = path.join(__dirname, "../..");

function memoryStorage(): Storage {
  const map = new Map<string, string>();
  return {
    get length() {
      return map.size;
    },
    clear() {
      map.clear();
    },
    getItem(key: string) {
      return map.has(key) ? map.get(key)! : null;
    },
    key(index: number) {
      return [...map.keys()][index] ?? null;
    },
    removeItem(key: string) {
      map.delete(key);
    },
    setItem(key: string, value: string) {
      map.set(key, String(value));
    },
  };
}

describe("Edge Board assemble 10s honesty", () => {
  it("caps stuck-loading look at 10s (escalate copy — no invent)", () => {
    expect(EDGE_BOARD_ASSEMBLE_HONESTY_MS).toBe(10_000);
    expect(edgeBoardAssembleHonestyCopy("timeout")).toMatch(
      /taking longer than usual/i,
    );
    expect(edgeBoardAssembleHonestyCopy("timeout")).toMatch(
      /as-of stay unavailable/i,
    );
    expect(edgeBoardAssembleHonestyCopy("timeout")).toMatch(/do not invent/i);
    expect(
      edgeBoardAssembleHonestyCopy("timeout", "2026-09-03T18:30:00.000Z"),
    ).toMatch(/last known market as-of/i);
    expect(
      edgeBoardAssembleHonestyCopy("timeout", "2026-09-03T18:30:00.000Z"),
    ).not.toMatch(/as-of stay unavailable/i);
    expect(edgeBoardAssembleHonestyCopy("unavailable")).toMatch(/unavailable/i);
    expect(edgeBoardAssembleHonestyCopy("unavailable")).toMatch(
      /do not invent/i,
    );
    expect(
      edgeBoardAssembleHonestyCopy("unavailable", "2026-09-03T18:30:00.000Z"),
    ).toMatch(/last known market as-of/i);
  });

  it("remembers last good linesAsOf stamp only (never rows; blank does not wipe)", () => {
    const storage = memoryStorage();
    rememberEdgeBoardLinesAsOf("nfl", "2026-09-03T18:30:00.000Z", storage);
    expect(recallEdgeBoardLinesAsOf("nfl", storage)).toBe(
      "2026-09-03T18:30:00.000Z",
    );
    // Empty Week 1 / blank assemble must not erase Full-slate vintage.
    rememberEdgeBoardLinesAsOf("nfl", "  ", storage);
    expect(recallEdgeBoardLinesAsOf("nfl", storage)).toBe(
      "2026-09-03T18:30:00.000Z",
    );
    rememberEdgeBoardLinesAsOf("nfl", null, storage);
    expect(recallEdgeBoardLinesAsOf("nfl", storage)).toBe(
      "2026-09-03T18:30:00.000Z",
    );
    rememberEdgeBoardLinesAsOf("nfl", "2026-09-04T12:00:00.000Z", storage);
    expect(recallEdgeBoardLinesAsOf("nfl", storage)).toBe(
      "2026-09-04T12:00:00.000Z",
    );
  });

  it("EdgeBoardSportClient escalates honesty at 10s without aborting assemble", () => {
    const client = readFileSync(
      path.join(webRoot, "components/EdgeBoardSportClient.tsx"),
      "utf8",
    );
    expect(client).toContain("EDGE_BOARD_ASSEMBLE_HONESTY_MS");
    expect(client).toContain("edgeBoardAssembleHonestyCopy");
    expect(client).toContain("recallEdgeBoardLinesAsOf");
    expect(client).toContain("rememberEdgeBoardLinesAsOf");
    expect(client).toContain('data-testid="edge-board-slow"');
    expect(client).toContain('data-testid="edge-board-unavailable"');
    expect(client).toContain("MarketAsOfStamp");
    expect(client).toContain('status: "slow"');
    // Copy receives lastLinesAsOf so stamp + banner stay consistent.
    expect(client).toContain(
      'edgeBoardAssembleHonestyCopy("timeout", state.lastLinesAsOf)',
    );
    expect(client).toContain(
      "edgeBoardAssembleHonestyCopy(state.reason, state.lastLinesAsOf)",
    );
    // Keep fetch alive past honesty ceiling (do not abort on the 10s timer).
    expect(client).not.toMatch(
      /setTimeout\(\(\) => \{\s*timedOut = true;\s*controller\.abort\(\)/,
    );
  });

  it("does not lower server pageData / maxDuration budgets in this slice", () => {
    const assemble = readFileSync(
      path.join(webRoot, "app/api/edge-board/[sport]/assemble/route.ts"),
      "utf8",
    );
    expect(assemble).toMatch(/export const maxDuration = 30/);
    expect(assemble).toContain("UPSTREAM_TIMEOUT_MS.pageData");
  });
});

describe("Edge Board assemble quarantine scrub (#8 Phase C / NFL-V3)", () => {
  it("source-locks assemble route through scrubEdgeBoardAssembleCustomerRows", () => {
    const assemble = readFileSync(
      path.join(webRoot, "app/api/edge-board/[sport]/assemble/route.ts"),
      "utf8",
    );
    expect(assemble).toContain("scrubEdgeBoardAssembleCustomerRows");
    expect(assemble).toContain("edge-board-assemble-quarantine");
  });

  it("strips isBestBet keys even when false (Phase A receipt: 32/32)", () => {
    const dirty = {
      game: "NE @ SEA",
      publishTag: "PASS",
      actionLabel: "PASS",
      isBestBet: false,
      is_best_bet: false,
      isBestBetLine: false,
      decision: {
        action_label: "PASS",
        isBestBet: false,
        is_best_bet: false,
        reason: "mild_edge_watch_list",
        point_grade: "LEAN",
      },
      matchupOverview:
        "Bottom line\nPass the number.\n\nWhat matters\n• Structure\n\nWatch\nBooks soft.",
    } as EdgeBoardRow;

    const clean = scrubEdgeBoardAssembleCustomerRow(dirty);
    expect(clean).not.toHaveProperty("isBestBet");
    expect(clean).not.toHaveProperty("is_best_bet");
    expect(clean).not.toHaveProperty("isBestBetLine");
    expect(clean).toHaveProperty("publishTag", "PASS");
    expect(clean).toHaveProperty("actionLabel", "PASS");

    const decision = (clean as { decision?: Record<string, unknown> }).decision;
    expect(decision).toBeDefined();
    expect(decision).not.toHaveProperty("isBestBet");
    expect(decision).not.toHaveProperty("is_best_bet");
    expect(decision).not.toHaveProperty("point_grade");
    expect(decision?.reason).toBe("mild_edge_pass");
    expect(decision?.action_label).toBe("PASS");

    const overview = (clean as { matchupOverview?: string }).matchupOverview;
    expect(overview).toContain(MATCHUP_OVERVIEW_FLIPS_HEADING);
    expect(overview).not.toMatch(/(^|\n)Watch(\n|$)/);
  });

  it("scrubs mild_edge_watch_list* and Watch headings across a row list", () => {
    const rows = scrubEdgeBoardAssembleCustomerRows([
      {
        reason: "mild_edge_watch_list|past_play_to",
        overview: "Bottom line\nx\n\nWatch\ny",
      } as EdgeBoardRow,
    ]);
    expect(rows).toHaveLength(1);
    expect((rows[0] as { reason?: string }).reason).toBe(
      "mild_edge_pass|past_play_to",
    );
    expect((rows[0] as { overview?: string }).overview).toContain(
      MATCHUP_OVERVIEW_FLIPS_HEADING,
    );
    expect((rows[0] as { overview?: string }).overview).not.toMatch(
      /(^|\n)Watch(\n|$)/,
    );
  });

  it("renames Watch overview heading without inventing tags", () => {
    expect(scrubMatchupOverviewWatchHeading("Watch\nline")).toBe(
      `${MATCHUP_OVERVIEW_FLIPS_HEADING}\nline`,
    );
    expect(
      scrubMatchupOverviewWatchHeading(
        "Bottom line\na\n\nWhat matters\n• b\n\nWatch\nc",
      ),
    ).toContain(`\n${MATCHUP_OVERVIEW_FLIPS_HEADING}\n`);
  });
});
