/**
 * Sourced NFL fantasy draft sits (IR / PUP / NFI / exempt / suspended).
 *
 * Extends the pack-injury hard-out pattern: unavailable players are removed
 * from the draftable board (desk + mock share loadFantasyDraftDesk). Does not
 * retune VOR, ADP, or the player-production spine.
 */

import sitsBook from "@/data/fantasy/draft-availability-sits-2026.json";

/** Statuses that mean the player is not a normal Week 1+ draft pick. */
export const DRAFT_HARD_OUT_STATUSES = new Set([
  "out",
  "ir",
  "pup",
  "nfi",
  "suspended",
  "inactive",
  "waived",
  "exempt",
  "commissioner_exempt",
  "commissioners_exempt",
]);

export type DraftSitSource = {
  label: string;
  href: string;
};

export type DraftSitEntry = {
  playerName: string;
  team: string;
  position: string;
  status: string;
  reason: string;
  asOf: string;
  sources: DraftSitSource[];
};

export type DraftAvailabilityBook = {
  asOf: string;
  season: number;
  sits: DraftSitEntry[];
  checkedNotOnBoard: DraftSitEntry[];
  leftUpNotes: Array<{
    playerName: string;
    team: string;
    position: string;
    note: string;
  }>;
};

function normalizeName(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "")
    .replace(/jr$|sr$|ii$|iii$|iv$/, "");
}

function nameMatch(a: string, b: string): boolean {
  const na = normalizeName(a);
  const nb = normalizeName(b);
  if (!na || !nb) return false;
  return na === nb || na.includes(nb) || nb.includes(na);
}

function normalizeTeam(team: string): string {
  const t = team.trim().toUpperCase();
  if (t === "LAR") return "LA";
  if (t === "WSH") return "WAS";
  return t;
}

export function isHardOutStatus(status: string | null | undefined): boolean {
  const key = String(status || "")
    .trim()
    .toLowerCase()
    .replace(/[\s/-]+/g, "_");
  if (!key) return false;
  if (DRAFT_HARD_OUT_STATUSES.has(key)) return true;
  // Club strings like "Reserve/Injured", "Commissioner's Exempt"
  if (key.includes("exempt")) return true;
  if (key.includes("injured") || key === "reserve_injured") return true;
  if (key.includes("pup")) return true;
  if (key.includes("nfi") || key.includes("non_football")) return true;
  if (key.includes("suspend")) return true;
  return false;
}

export function loadDraftAvailabilityBook(
  season = 2026,
): DraftAvailabilityBook {
  const raw = sitsBook as DraftAvailabilityBook;
  if (Number(raw.season) !== season) {
    return {
      asOf: String(raw.asOf || ""),
      season,
      sits: [],
      checkedNotOnBoard: [],
      leftUpNotes: [],
    };
  }
  return {
    asOf: String(raw.asOf || ""),
    season: Number(raw.season) || season,
    sits: Array.isArray(raw.sits) ? raw.sits : [],
    checkedNotOnBoard: Array.isArray(raw.checkedNotOnBoard)
      ? raw.checkedNotOnBoard
      : [],
    leftUpNotes: Array.isArray(raw.leftUpNotes) ? raw.leftUpNotes : [],
  };
}

export function findDraftSit<
  T extends { playerName: string; team: string; position: string },
>(row: T, sits: DraftSitEntry[]): DraftSitEntry | null {
  const team = normalizeTeam(row.team);
  const pos = row.position.toUpperCase();
  return (
    sits.find(
      (sit) =>
        normalizeTeam(sit.team) === team &&
        sit.position.toUpperCase() === pos &&
        nameMatch(sit.playerName, row.playerName),
    ) ?? null
  );
}

export function filterDraftableRows<
  T extends { playerName: string; team: string; position: string },
>(
  rows: T[],
  book: DraftAvailabilityBook = loadDraftAvailabilityBook(),
): {
  draftable: T[];
  sat: Array<{ row: T; sit: DraftSitEntry }>;
} {
  const sat: Array<{ row: T; sit: DraftSitEntry }> = [];
  const draftable: T[] = [];
  for (const row of rows) {
    const sit = findDraftSit(row, book.sits);
    if (sit && isHardOutStatus(sit.status)) {
      sat.push({ row, sit });
      continue;
    }
    draftable.push(row);
  }
  return { draftable, sat };
}

/** One-line limitation for the desk / mock footer. */
export function draftSitLimitation(
  sat: Array<{
    row: { playerName: string; team: string; position: string };
    sit: DraftSitEntry;
  }>,
  asOf: string,
): string | null {
  if (!sat.length) return null;
  const names = sat
    .slice(0, 8)
    .map(
      ({ row, sit }) =>
        `${row.playerName} (${row.team} ${row.position}/${sit.status})`,
    )
    .join("; ");
  const more = sat.length > 8 ? ` +${sat.length - 8} more` : "";
  return `Draft sits (as of ${asOf}): removed ${sat.length} unavailable — ${names}${more}. Sourced IR/PUP/NFI/exempt/suspended only; production spine unchanged.`;
}
