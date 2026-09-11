/**
 * CFB Edge Board week query + live-slate scope.
 *
 * Missing/invalid week → authoritative calendar current week (official slate
 * kickoffs vs clock). A present finite integer ≥ 0 is kept as-is.
 * Never coerce week=2 to week=1.
 *
 * Live board excludes completed / already-started games server-side.
 * Official slate `status=final` is sufficient but not required — W1 rows
 * stay `accepted` on the Aug 31 pack after they have kicked.
 */

import {
  packagedOfficialWeekBoard,
  type CfbWeekBoard,
  type CfbWeekBoardGame,
} from "@/lib/cfb-official-slate";

function parseIsoMs(raw: string | null | undefined): number | null {
  if (raw == null || !String(raw).trim()) return null;
  const ms = Date.parse(String(raw).trim());
  return Number.isFinite(ms) ? ms : null;
}

export function isCfbAssembleWeekComplete(args: {
  commenceTime?: string | null;
  kickoff?: string | null;
  status?: string | null;
  nowMs?: number;
}): boolean {
  const status = String(args.status || "")
    .trim()
    .toLowerCase();
  if (status === "final") return true;
  const kickMs =
    parseIsoMs(args.commenceTime) ?? parseIsoMs(args.kickoff) ?? null;
  if (kickMs == null) return false;
  const now = args.nowMs ?? Date.now();
  return kickMs <= now;
}

export function resolveCfbCurrentAssembleWeek(
  nowMs: number = Date.now(),
  board: CfbWeekBoard = packagedOfficialWeekBoard(),
): number {
  const weeks = [...(board.weeks ?? [])]
    .filter((w) => Number.isFinite(w) && w >= 0)
    .sort((a, b) => a - b);
  const games = board.games ?? [];
  for (const week of weeks) {
    const live = games.some(
      (g: CfbWeekBoardGame) =>
        g.week === week &&
        !isCfbAssembleWeekComplete({
          kickoff: g.kickoff,
          status: g.status,
          nowMs,
        }),
    );
    if (live) return week;
  }
  return weeks.length ? weeks[weeks.length - 1]! : 1;
}

export function parseCfbAssembleWeek(
  raw: string | null | undefined,
  nowMs: number = Date.now(),
): number {
  if (raw == null || String(raw).trim() === "") {
    return resolveCfbCurrentAssembleWeek(nowMs);
  }
  const n = Number(raw);
  if (!Number.isFinite(n) || !Number.isInteger(n) || n < 0) {
    return resolveCfbCurrentAssembleWeek(nowMs);
  }
  return n;
}

/** Rows stamped for this week only. Empty is honest — never fall through to week 1. */
export function filterCfbEdgeBoardRowsByWeek<T>(
  rows: readonly T[],
  week: number,
): T[] {
  return rows.filter((r) => (r as { week?: unknown }).week === week);
}

export function filterCfbCompletedEdgeBoardRows<
  T extends {
    commenceTime?: string | null;
    kickoff?: string | null;
    status?: string | null;
  },
>(rows: readonly T[], nowMs: number = Date.now()): T[] {
  return rows.filter(
    (r) =>
      !isCfbAssembleWeekComplete({
        commenceTime: r.commenceTime,
        kickoff: r.kickoff,
        status: r.status,
        nowMs,
      }),
  );
}

/** Live Edge Board / Edges desk: requested week minus completed games. */
export function scopeCfbLiveEdgeBoardRows<
  T extends {
    week?: number;
    commenceTime?: string | null;
    kickoff?: string | null;
    status?: string | null;
  },
>(rows: readonly T[], week: number, nowMs: number = Date.now()): T[] {
  return filterCfbCompletedEdgeBoardRows(
    filterCfbEdgeBoardRowsByWeek(rows, week),
    nowMs,
  );
}
