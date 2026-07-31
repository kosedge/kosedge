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

export function loadEdgeBoardFallback(sportKey: string): EdgeBoardRow[] {
  const sport = sportKey.toLowerCase();
  const path = getEdgeBoardFallbackPath(sport);
  if (!existsSync(path)) return [];

  try {
    const raw = readFileSync(path, "utf-8");
    const data = JSON.parse(raw) as EdgeBoardFallbackMeta | EdgeBoardRow[];
    if (Array.isArray(data)) return data;
    return Array.isArray(data.rows) ? data.rows : [];
  } catch {
    return [];
  }
}
