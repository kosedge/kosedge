/**
 * Last-known Odds API edge-board rows for when live pulls are empty
 * (quota exhaustion, outage). Never invents prices — only shipped snapshots.
 */

import "server-only";

import { existsSync, readFileSync } from "node:fs";
import type { EdgeBoardRow } from "@kosedge/contracts";
import { getEdgeBoardFallbackPath } from "@/lib/data-paths";

export type EdgeBoardFallbackMeta = {
  sport: string;
  source: string;
  capturedAt: string;
  rows: EdgeBoardRow[];
};

export function loadEdgeBoardFallbackMeta(
  sportKey: string,
): EdgeBoardFallbackMeta | null {
  const sport = sportKey.toLowerCase();
  const path = getEdgeBoardFallbackPath(sport);
  if (!existsSync(path)) return null;

  try {
    const raw = readFileSync(path, "utf-8");
    const data = JSON.parse(raw) as EdgeBoardFallbackMeta | EdgeBoardRow[];
    if (Array.isArray(data)) {
      return { sport, source: "legacy-array", capturedAt: "", rows: data };
    }
    if (!Array.isArray(data.rows)) return null;
    return {
      sport: data.sport || sport,
      source: data.source || "unknown",
      capturedAt: typeof data.capturedAt === "string" ? data.capturedAt : "",
      rows: data.rows,
    };
  } catch {
    return null;
  }
}

export function loadEdgeBoardFallback(sportKey: string): EdgeBoardRow[] {
  return loadEdgeBoardFallbackMeta(sportKey)?.rows ?? [];
}
