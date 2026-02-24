/**
 * KEI Lines: projected spread and over/under per game.
 * Data is read from data/processed/kei_lines_{sport}.json (exported by pipeline script).
 */

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { getSport } from "@/lib/sports";

export type KeiLineGame = {
  id?: string;
  homeTeam: string;
  awayTeam: string;
  commenceTime?: string;
  projSpreadHome: number | null;
  projTotal: number | null;
};

function findKeiLinesPath(sportKey: string): string | null {
  const base = process.cwd();
  const fileName = "kei_lines_" + sportKey + ".json";
  const candidates = [
    join(base, "data", "processed", fileName),
    join(base, "apps", "web", "data", "processed", fileName),
  ];
  for (const p of candidates) {
    if (existsSync(p)) return p;
  }
  return null;
}

export function getKeiLines(sportKey: string): KeiLineGame[] {
  if (!getSport(sportKey)) return [];

  const p = findKeiLinesPath(sportKey);
  if (!p) return [];

  try {
    const raw = readFileSync(p, "utf-8");
    const data = JSON.parse(raw) as { games?: KeiLineGame[] };
    return Array.isArray(data.games) ? data.games : [];
  } catch {
    return [];
  }
}
