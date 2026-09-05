/**
 * Overview-only soft fetch for Edge Board slate cards.
 * Soft timeout / honest status — does not change assemble or model logic.
 *
 * Daily sports (NBA/MLB/NHL/WNBA/NCAAM): next day with games (today, else opening day).
 * Weekly sports (NFL/CFB): current desk week (Week 1 default; advances with board weeks).
 *
 * At 8s without a response we stop blocking SSR and return `timeout`
 * (empty games + distinct copy), not a silent "no slate" empty state.
 */

import {
  getTonightGames,
  tonightSlug,
  type TonightGame,
} from "@/lib/edge-board-tonight";
import { loadAssembledEdgeBoardRows } from "@/lib/build-edge-board-rows";
import { stampCfbEdgeBoardWeek } from "@/lib/cfb-kei-artifacts";
import { flatRowsToLegacy } from "@/lib/flat-rows-to-legacy";
import { parseOfficialSlateWeek } from "@/lib/cfb-official-slate";

const OVERVIEW_SLATE_TIMEOUT_MS = 8_000;

export type OverviewSlateStatus = "ready" | "empty" | "timeout" | "error";

export type OverviewSlateResult = {
  games: TonightGame[];
  status: OverviewSlateStatus;
  /** Numeric week for NFL/CFB when known */
  week?: number | null;
  /** e.g. "Week 1" for NFL/CFB when known */
  weekLabel?: string | null;
};

const WEEKLY_SPORTS = new Set(["nfl", "cfb"]);

/** ET calendar day (YYYY-MM-DD) from ISO commence or date-only kickoff fields. */
export function gameDayEt(game: TonightGame): string | null {
  const fromIso = etCalendarDay(game.row.commenceTime);
  if (fromIso) return fromIso;

  const kd = String(game.row.kickoffDate ?? "").trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(kd)) return kd;

  const m = kd.match(/^(\d{1,2})\/(\d{1,2})(?:\/(\d{2,4}))?$/);
  if (m) {
    const year = m[3]
      ? m[3].length === 2
        ? 2000 + Number(m[3])
        : Number(m[3])
      : new Date().getFullYear();
    const mm = String(m[1]).padStart(2, "0");
    const dd = String(m[2]).padStart(2, "0");
    return `${year}-${mm}-${dd}`;
  }

  return null;
}

function etCalendarDay(isoOrLabel: string | undefined): string | null {
  if (!isoOrLabel) return null;
  const d = new Date(isoOrLabel);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString("en-CA", { timeZone: "America/New_York" });
}

function gameSortKey(game: TonightGame): string {
  const row = game.row;
  return (
    String(row.commenceTime ?? "") ||
    `${row.kickoffDate ?? ""} ${row.kickoffTime ?? ""}` ||
    String(row.time ?? "") ||
    game.slug
  );
}

/** Prefer today's ET slate; else the earliest upcoming day that has games (opening day). */
export function preferNextDailySlate(games: TonightGame[]): TonightGame[] {
  if (games.length <= 1) return games;
  const todayEt = new Date().toLocaleDateString("en-CA", {
    timeZone: "America/New_York",
  });
  const byDay = new Map<string, TonightGame[]>();
  const undated: TonightGame[] = [];

  for (const g of games) {
    const day = gameDayEt(g);
    if (!day) {
      undated.push(g);
      continue;
    }
    const list = byDay.get(day) ?? [];
    list.push(g);
    byDay.set(day, list);
  }

  if (byDay.size === 0) {
    return [...games].sort((a, b) =>
      gameSortKey(a).localeCompare(gameSortKey(b)),
    );
  }

  const days = [...byDay.keys()].sort();
  // Upcoming/today first; if the board only has past days, keep the latest day
  // so Overview is not empty when schedule rows exist.
  const todayOrNext =
    days.find((d) => d >= todayEt) ?? days[days.length - 1];
  const picked = byDay.get(todayOrNext) ?? games;
  return [...picked].sort((a, b) =>
    gameSortKey(a).localeCompare(gameSortKey(b)),
  );
}

function dominantWeek(games: TonightGame[]): number | null {
  const counts = new Map<number, number>();
  for (const g of games) {
    const w = Number(g.row.week);
    if (!Number.isFinite(w)) continue;
    counts.set(w, (counts.get(w) ?? 0) + 1);
  }
  if (!counts.size) return null;
  let best: number | null = null;
  let bestN = -1;
  for (const [w, n] of counts) {
    if (n > bestN || (n === bestN && best != null && w < best)) {
      best = w;
      bestN = n;
    }
  }
  return best;
}

/** CFB desk week: Week 1 when present; otherwise earliest non-empty week on the board. */
export function filterCfbOverviewWeek(games: TonightGame[]): {
  games: TonightGame[];
  week: number | null;
} {
  const deskWeek = parseOfficialSlateWeek(undefined);
  const atDesk = games.filter((g) => Number(g.row.week) === deskWeek);
  if (atDesk.length) return { games: atDesk, week: deskWeek };

  const weeks = [
    ...new Set(
      games
        .map((g) => Number(g.row.week))
        .filter((w) => Number.isFinite(w)),
    ),
  ].sort((a, b) => a - b);
  // Prefer first regular week (>=1) over Week 0 finals when both exist.
  const preferred =
    weeks.find((w) => w >= 1) ?? (weeks.length ? weeks[0] : null);
  if (preferred == null) return { games, week: null };
  return {
    games: games.filter((g) => Number(g.row.week) === preferred),
    week: preferred,
  };
}

type SportSlateLoad = { games: TonightGame[]; week: number | null };

async function loadSportGames(sportKey: string): Promise<SportSlateLoad> {
  const sport = sportKey.toLowerCase();

  if (sport === "nfl") {
    // Default assemble is Week 1 REG. If empty, fall back to full projection
    // slate and keep the earliest REG week present (opening week).
    let games = await getTonightGames("nfl");
    if (games.length) {
      return { games, week: dominantWeek(games) };
    }
    try {
      const flat = await loadAssembledEdgeBoardRows("nfl", { slate: "full" });
      const legacy = flatRowsToLegacy(
        Array.isArray(flat) ? flat : [],
        "nfl",
      );
      games = legacy
        .filter((row) => row?.teamA?.name && row?.teamB?.name)
        .map((row) => ({
          slug: tonightSlug("nfl", row.teamA.name, row.teamB.name),
          row,
          sport,
        }));
      const week = dominantWeek(games);
      if (week != null) {
        return {
          games: games.filter((g) => Number(g.row.week) === week),
          week,
        };
      }
      return { games, week: null };
    } catch {
      return { games: [], week: null };
    }
  }

  if (sport === "cfb") {
    const games = await getTonightGames("cfb");
    // Stamp week from KEI/official slate when missing, then filter to desk week.
    const withWeek = (() => {
      try {
        const stamped = stampCfbEdgeBoardWeek(
          games.map((g) => ({
            ...g.row,
            game:
              g.row.game ??
              `${g.row.teamA.name} @ ${g.row.teamB.name}`,
            week: g.row.week ?? undefined,
          })),
        );
        return games.map((g, i) => ({
          ...g,
          row: { ...g.row, week: stamped[i]?.week ?? g.row.week },
        }));
      } catch {
        return games;
      }
    })();
    return filterCfbOverviewWeek(withWeek);
  }

  const games = await getTonightGames(sport);
  if (WEEKLY_SPORTS.has(sport)) {
    return { games, week: dominantWeek(games) };
  }
  return { games: preferNextDailySlate(games), week: null };
}

export async function loadOverviewSlateGames(
  sportKey: string,
): Promise<OverviewSlateResult> {
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  const sport = (sportKey || "").toLowerCase();

  try {
    const result = await Promise.race([
      loadSportGames(sport).then((loaded) => ({
        kind: "ok" as const,
        games: Array.isArray(loaded.games) ? loaded.games : [],
        week: loaded.week ?? null,
      })),
      new Promise<{ kind: "timeout" }>((resolve) => {
        timeoutId = setTimeout(
          () => resolve({ kind: "timeout" }),
          OVERVIEW_SLATE_TIMEOUT_MS,
        );
      }),
    ]);

    if (timeoutId) clearTimeout(timeoutId);

    if (result.kind === "timeout") {
      return { games: [], status: "timeout", week: null, weekLabel: null };
    }

    const games = result.games;
    const week = WEEKLY_SPORTS.has(sport)
      ? (result.week ?? dominantWeek(games))
      : null;
    return {
      games,
      status: games.length > 0 ? "ready" : "empty",
      week,
      weekLabel: week != null ? `Week ${week}` : null,
    };
  } catch {
    if (timeoutId) clearTimeout(timeoutId);
    return { games: [], status: "error", week: null, weekLabel: null };
  }
}
