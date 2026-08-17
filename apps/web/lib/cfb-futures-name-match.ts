/**
 * Map Odds API CFB outright names onto our roster codes.
 * Same fold discipline as Edge Board (accents, Hawai'i, aliases).
 * Never invent a code when the book name is ambiguous or unknown.
 */

import { CFB_TEAM_DISPLAY_NAMES } from "@/lib/cfb-conferences";
import { foldCfbName } from "@/lib/cfb-match-keys";
import teamNamesPack from "@/lib/data/cfb-team-names-2026.json";

const TEAM_NAMES = (teamNamesPack as { teams: Record<string, string> }).teams;

/** Book strings that are not an exact universe display_name. */
const ALIASES: Record<string, string> = {
  "southern mississippi golden eagles": "USM",
  "southern mississippi": "USM",
  "delaware blue hens": "DEL",
  "delaware fightin blue hens": "DEL",
  "miami fl": "MIA",
  "miami (fl)": "MIA",
  "miami florida": "MIA",
  "miami florida hurricanes": "MIA",
  "connecticut huskies": "CONN",
  "uconn": "CONN",
  "ole miss": "MISS",
  "hawaii rainbow warriors": "HAW",
  "hawai i rainbow warriors": "HAW",
};

function addKey(
  index: Map<string, string[]>,
  raw: string,
  code: string,
): void {
  const key = foldCfbName(raw);
  if (!key) return;
  const list = index.get(key) ?? [];
  if (!list.includes(code)) list.push(code);
  index.set(key, list);
}

function buildIndex(): Map<string, string> {
  const raw = new Map<string, string[]>();

  for (const [code, name] of Object.entries(TEAM_NAMES)) {
    addKey(raw, code, code);
    addKey(raw, name, code);
    const parts = foldCfbName(name).split(" ").filter(Boolean);
    if (parts.length >= 2) {
      addKey(raw, parts.slice(0, -1).join(" "), code);
    }
  }

  for (const [code, short] of Object.entries(CFB_TEAM_DISPLAY_NAMES)) {
    addKey(raw, short, code);
  }

  for (const [alias, code] of Object.entries(ALIASES)) {
    addKey(raw, alias, code);
  }

  const unique = new Map<string, string>();
  for (const [key, codes] of raw) {
    if (codes.length === 1) unique.set(key, codes[0] as string);
  }
  return unique;
}

const INDEX = buildIndex();

export function matchCfbFuturesTeamName(bookName: string): string | null {
  const key = foldCfbName(bookName);
  if (!key) return null;
  return INDEX.get(key) ?? null;
}

export function cfbFuturesRosterName(code: string): string | null {
  const key = String(code || "").trim().toUpperCase();
  return TEAM_NAMES[key] ?? null;
}

export function cfbFuturesRosterSize(): number {
  return Object.keys(TEAM_NAMES).length;
}
