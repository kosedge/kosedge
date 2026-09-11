import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { CFB_EDGE_BOARD_PUBLIC_ENABLED } from "@/lib/cfb-edge-board-public";
import { applyOddsHorizonToRows, fairDisplayForRow } from "@/lib/odds-horizon";
import { filterNflProjectionBackedRows } from "@/lib/nfl-edge-board-from-fair-lines";

const webRoot = path.join(__dirname, "../..");

function readRel(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

describe("P0 odds expansion — kill switch + odds-without-kei", () => {
  it("CFB public kill switch remains OFF", () => {
    expect(CFB_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    const src = readRel("lib/cfb-edge-board-public.ts");
    expect(src).toMatch(/export const CFB_EDGE_BOARD_PUBLIC_ENABLED = false/);
    expect(src).toContain("Odds Expansion must not flip");
    const assemble = readRel("app/api/edge-board/[sport]/assemble/route.ts");
    expect(assemble).toContain("isCfbEdgeBoardCustomerDisabled");
    expect(assemble).toContain("cfbEdgeBoardAssembleUnavailablePayload");
  });

  it("assemble still fail-closes public CFB (does not weaken #529)", () => {
    const assemble = readRel("app/api/edge-board/[sport]/assemble/route.ts");
    expect(assemble).toContain("status: 503");
    const page = readRel("app/edge-board/[sport]/page.tsx");
    expect(page).toContain("isCfbEdgeBoardCustomerDisabled");
  });

  it("ingest path documents no current-week window", () => {
    const tasks = readFileSync(
      path.join(webRoot, "../../services/model-service/src/tasks.py"),
      "utf8",
    );
    expect(tasks).toContain("all_available");
    expect(tasks).toContain("filter_ingestible_events");
    expect(tasks).toContain("No commenceTimeTo / current-week window");
  });

  it("odds-without-kei REG rows survive the NFL projection filter", () => {
    const rows = filterNflProjectionBackedRows([
      {
        id: "odds-only-spread",
        game: "Chicago Bears @ Detroit Lions",
        market: "Spread",
        best: "+3.5",
        bookKey: "betmgm",
        commenceTime: "2026-11-08T18:00:00Z",
        linesAsOf: "2026-09-11T12:00:00Z",
        seasonType: "REG",
      },
    ]);
    expect(rows).toHaveLength(1);
    const stamped = applyOddsHorizonToRows(
      rows,
      Date.parse("2026-09-11T18:00:00Z"),
    );
    expect(stamped[0]?.oddsWithoutKei).toBe(true);
    expect(fairDisplayForRow(stamped[0])).toBe("—");
    expect(stamped[0]?.best).toBe("+3.5");
    expect(stamped[0]?.marketAsOf).toBe("2026-09-11T12:00:00Z");
  });
});
