/**
 * KEI = Kos Edge Index. Each sport gets its own brand code on the shared
 * edge-board columns (same layout, sport-specific label):
 *   ncaam → KEICMB, nfl → KEINFL, nba → KEINBA, etc.
 */

import type { SportKey } from "@/lib/sports";

const KEI_CODES: Record<SportKey, string> = {
  ncaam: "KEICMB",
  nfl: "KEINFL",
  nba: "KEINBA",
  mlb: "KEIMLB",
  nhl: "KEINHL",
  cfb: "KEICFB",
  wnba: "KEIWNBA",
};

export function getKeiCode(sportKey: string): string {
  const key = sportKey.toLowerCase() as SportKey;
  return KEI_CODES[key] ?? `KEI${sportKey.toUpperCase()}`;
}

export function getKeiProductLabel(sportKey: string): string {
  return `${getKeiCode(sportKey)} (Kos Edge Index)`;
}
