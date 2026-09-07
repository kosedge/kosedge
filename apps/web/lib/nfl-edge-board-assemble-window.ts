/**
 * INC-2026-09-07 SEV-2 (C) — NFL Edge Board assemble window + full-slate governance.
 *
 * Live / Week 1 customer path uses a narrow fair-lines window (Week 1 slate).
 * Full slate must NOT live-pull fair-lines with daysAhead=200. Customer
 * `slate=full` serves a governed cache/snapshot only; if unavailable → fail
 * closed (503). Never return a truncated Week-1 board labeled full.
 *
 * B/D snapshot spine (writer/publisher) is follow-on — this module only loads
 * a shipped governed artifact and refuses ungoverned live wide assemble.
 */

import "server-only";

import { existsSync, readFileSync } from "node:fs";
import type { EdgeBoardRow } from "@kosedge/contracts";
import { getEdgeBoardFullSlatePath } from "@/lib/data-paths";

export type NflAssembleWindow = {
  daysAhead: number;
  includePastDays: number;
};

/** Customer-relevant Week 1 / live slate (Thu–Mon + small buffer). */
export const NFL_EDGE_BOARD_LIVE_WINDOW: NflAssembleWindow = {
  daysAhead: 10,
  includePastDays: 2,
};

/**
 * @deprecated INC-2026-09-07: full slate is not a live assemble window.
 * Kept as a constant for honesty asserts (must never be used on customer GET).
 */
export const NFL_EDGE_BOARD_FULL_WINDOW: NflAssembleWindow = {
  daysAhead: 200,
  includePastDays: 14,
};

/** Live assemble is Week 1 / live only — full is governed snapshot. */
export function nflAssembleWindowForSlate(
  slate: "week1" | "full",
): NflAssembleWindow {
  if (slate === "full") {
    throw new Error(
      "NFL full-slate assemble unavailable: refusing live daysAhead=200 path; " +
        "governed cache/snapshot required (INC-2026-09-07).",
    );
  }
  return NFL_EDGE_BOARD_LIVE_WINDOW;
}

/**
 * Fail closed if any code path attempts a live wide window for slate=full.
 */
export function assertNoLiveFullSlateAssemble(slate: "week1" | "full"): void {
  if (slate === "full") {
    throw new Error(
      "NFL full-slate assemble unavailable: governed cache/snapshot missing " +
        "or live wide window refused (INC-2026-09-07).",
    );
  }
}

export type GovernedNflFullSlate = {
  rows: EdgeBoardRow[];
  linesAsOf: string | null;
  source: string;
  capturedAt: string | null;
};

/**
 * Load governed full-slate snapshot if shipped.
 * Returns null when absent/corrupt — caller must fail closed (never invent).
 */
export function loadGovernedNflFullSlate(): GovernedNflFullSlate | null {
  const path = getEdgeBoardFullSlatePath("nfl");
  if (!existsSync(path)) return null;
  try {
    const raw = readFileSync(path, "utf-8");
    const data = JSON.parse(raw) as {
      rows?: EdgeBoardRow[];
      linesAsOf?: string | null;
      lines_as_of?: string | null;
      source?: string;
      capturedAt?: string | null;
      captured_at?: string | null;
    };
    const rows = Array.isArray(data.rows) ? data.rows : [];
    if (rows.length === 0) return null;
    return {
      rows,
      linesAsOf:
        (typeof data.linesAsOf === "string" && data.linesAsOf) ||
        (typeof data.lines_as_of === "string" && data.lines_as_of) ||
        null,
      source:
        typeof data.source === "string" && data.source.trim()
          ? data.source.trim()
          : "governed-full-slate-snapshot",
      capturedAt:
        (typeof data.capturedAt === "string" && data.capturedAt) ||
        (typeof data.captured_at === "string" && data.captured_at) ||
        null,
    };
  } catch {
    return null;
  }
}

/**
 * Resolve full-slate rows from governed snapshot or throw (fail closed).
 * Never falls through to live daysAhead=200 assemble.
 */
export function requireGovernedNflFullSlate(): GovernedNflFullSlate {
  const governed = loadGovernedNflFullSlate();
  if (!governed) {
    throw new Error(
      "NFL full-slate assemble unavailable: governed cache/snapshot missing " +
        "(edge_board_full_slate_nfl.json). Fail closed — no live daysAhead=200.",
    );
  }
  return governed;
}
