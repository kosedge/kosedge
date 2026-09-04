import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  EDGE_BOARD_ASSEMBLE_HONESTY_MS,
  edgeBoardAssembleHonestyCopy,
  recallEdgeBoardLinesAsOf,
  rememberEdgeBoardLinesAsOf,
} from "@/lib/edge-board-assemble-honesty";

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
    expect(edgeBoardAssembleHonestyCopy("timeout")).toMatch(/do not invent/i);
    expect(edgeBoardAssembleHonestyCopy("unavailable")).toMatch(
      /unavailable/i,
    );
    expect(edgeBoardAssembleHonestyCopy("unavailable")).toMatch(
      /do not invent/i,
    );
  });

  it("remembers last good linesAsOf stamp only (never rows)", () => {
    const storage = memoryStorage();
    rememberEdgeBoardLinesAsOf("nfl", "2026-09-03T18:30:00.000Z", storage);
    expect(recallEdgeBoardLinesAsOf("nfl", storage)).toBe(
      "2026-09-03T18:30:00.000Z",
    );
    rememberEdgeBoardLinesAsOf("nfl", "  ", storage);
    expect(recallEdgeBoardLinesAsOf("nfl", storage)).toBeNull();
    rememberEdgeBoardLinesAsOf("nfl", null, storage);
    expect(recallEdgeBoardLinesAsOf("nfl", storage)).toBeNull();
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
