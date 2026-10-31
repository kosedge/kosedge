/**
 * Edge Board assemble honesty — customer-visible timeout UX.
 *
 * Assemble may cold-hit ~16s; the board must not look "stuck honest" past 10s.
 * Escalate copy + as-of stamp (last good when known); keep fetch alive until
 * assemble returns or fails. Fail-closed on error — no invented rows.
 * Server maxDuration / pageData upstream budget stay as-is (tighten UX only).
 */

/** Customer honesty ceiling before escalating past bare “Loading board…”. */
export const EDGE_BOARD_ASSEMBLE_HONESTY_MS = 10_000;

export type EdgeBoardAssembleHonestyReason = "timeout" | "unavailable";

const LAST_ASOF_PREFIX = "kosedge:edge-board:linesAsOf:";

export function edgeBoardAssembleHonestyCopy(
  reason: EdgeBoardAssembleHonestyReason,
  lastLinesAsOf?: string | null,
): string {
  const hasLast = Boolean(lastLinesAsOf?.trim());
  if (reason === "timeout") {
    return hasLast
      ? "Board is taking longer than usual. Showing last known market as-of — we do not invent rows."
      : "Board is taking longer than usual. Lines as-of stay unavailable until assemble returns — we do not invent rows.";
  }
  return hasLast
    ? "Board temporarily unavailable. Showing last known market as-of — we do not invent rows. Refresh to try again."
    : "Board temporarily unavailable. We do not invent rows — refresh to try again.";
}

/**
 * Persist last good board as-of (stamp only — never rows).
 * Blank/null does **not** wipe a prior vintage (empty Week 1 must not erase
 * Full-slate as-of for a later slow/fail path).
 */
export function rememberEdgeBoardLinesAsOf(
  sportKey: string,
  linesAsOf: string | null | undefined,
  storage: Pick<Storage, "setItem"> | null = defaultStorage(),
): void {
  if (!storage) return;
  const clean = linesAsOf?.trim();
  if (!clean) return;
  const key = LAST_ASOF_PREFIX + (sportKey || "nfl").toLowerCase();
  try {
    storage.setItem(key, clean);
  } catch {
    /* ignore quota / private mode */
  }
}

/** Last good linesAsOf for sport, or null when unknown / unreadable. */
export function recallEdgeBoardLinesAsOf(
  sportKey: string,
  storage: Pick<Storage, "getItem"> | null = defaultStorage(),
): string | null {
  if (!storage) return null;
  const key = LAST_ASOF_PREFIX + (sportKey || "nfl").toLowerCase();
  try {
    const raw = storage.getItem(key)?.trim();
    return raw || null;
  } catch {
    return null;
  }
}

function defaultStorage(): Pick<
  Storage,
  "getItem" | "setItem" | "removeItem"
> | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}
