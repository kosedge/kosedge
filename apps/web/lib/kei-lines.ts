/**
 * KEI Lines: projected spread and over/under per game.
 * Data is read from data/processed/kei_lines_{sport}.json (exported by pipeline script).
 */

import { existsSync, readFileSync } from "node:fs";
import { getSport } from "@/lib/sports";
import { getKeiLinesPath } from "@/lib/data-paths";

export type KeiLineGame = {
  id?: string;
  homeTeam: string;
  awayTeam: string;
  commenceTime?: string;
  projSpreadHome: number | null;
  projTotal: number | null;
};

export function getKeiLines(sportKey: string): KeiLineGame[] {
  if (!getSport(sportKey)) return [];

  const p = getKeiLinesPath(sportKey);
  if (!existsSync(p)) return [];

  try {
    const raw = readFileSync(p, "utf-8");
    const data = JSON.parse(raw) as { games?: KeiLineGame[] };
    return Array.isArray(data.games) ? data.games : [];
  } catch {
    return [];
  }
}
