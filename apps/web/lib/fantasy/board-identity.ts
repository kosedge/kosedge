/**
 * Fantasy board identity helpers — depth SoT full names when abbreviated
 * board labels collide (two ATL B.Robinson → Bijan vs Brian).
 */

import { parseNameParts } from "@/lib/fantasy/adp-match";
import type { DepthRow } from "@/lib/fantasy/risk-signals";

export type BoardIdentityRow = {
  playerId: string;
  playerName: string;
  team: string;
  position: string;
};

function boardCollisionKey(row: BoardIdentityRow): string | null {
  const parts = parseNameParts(row.playerName);
  if (!parts.firstInitial || !parts.lastName) return null;
  return [
    parts.firstInitial,
    parts.lastName,
    row.team.trim().toUpperCase(),
    row.position.trim().toUpperCase(),
  ].join("|");
}

/**
 * When two+ desk rows share first-initial + last + team + pos (nflverse
 * "B.Robinson" ×2 on ATL), replace each colliding label with the depth-pack
 * full name joined on player_id. Non-colliding rows are unchanged.
 *
 * Returns playerId → display name overrides only.
 */
export function expandCollidingBoardNames(
  rows: BoardIdentityRow[],
  depthRows: DepthRow[],
): Map<string, string> {
  const depthByPlayerId = new Map<string, string>();
  for (const d of depthRows) {
    const id = d.playerId?.trim();
    const name = d.playerName?.trim();
    if (!id || !name) continue;
    depthByPlayerId.set(id, name);
  }

  const groups = new Map<string, BoardIdentityRow[]>();
  for (const row of rows) {
    const key = boardCollisionKey(row);
    if (!key) continue;
    const list = groups.get(key) ?? [];
    list.push(row);
    groups.set(key, list);
  }

  const overrides = new Map<string, string>();
  for (const group of groups.values()) {
    if (group.length < 2) continue;
    for (const row of group) {
      const full = depthByPlayerId.get(row.playerId);
      if (!full) continue;
      // Only expand when depth actually disambiguates the abbrev label.
      if (full.trim().toLowerCase() === row.playerName.trim().toLowerCase()) {
        continue;
      }
      overrides.set(row.playerId, full);
    }
  }
  return overrides;
}

/** Apply display-name overrides onto a mutable list of desk-shaped rows. */
export function applyBoardNameOverrides<T extends BoardIdentityRow>(
  rows: T[],
  overrides: Map<string, string>,
): T[] {
  if (overrides.size === 0) return rows;
  return rows.map((row) => {
    const next = overrides.get(row.playerId);
    if (!next) return row;
    return { ...row, playerName: next };
  });
}
