/**
 * NHL goalie starter confirmation.
 *
 * Best public source already used elsewhere in the repo: ESPN site API
 * (`site.api.espn.com` scoreboard), same family as NFL schedule/camp desks.
 * Preseason/early boards often omit `probables` — we surface honest Pending
 * rather than inventing starter names.
 */

import "server-only";

import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";

export type GoalieConfirmationStatus =
  | "confirmed"
  | "expected"
  | "pending"
  | "unavailable";

export type GoalieSideConfirmation = {
  teamAbbr: string | null;
  teamName: string | null;
  goalieName: string | null;
  status: GoalieConfirmationStatus;
  source: "espn-scoreboard" | "none";
};

export type NhlGoalieMatchup = {
  eventId: string;
  name: string;
  commenceTime: string | null;
  away: GoalieSideConfirmation;
  home: GoalieSideConfirmation;
};

type EspnCompetitor = {
  homeAway?: string;
  team?: { abbreviation?: string; displayName?: string };
  probables?: Array<{
    athlete?: { displayName?: string; fullName?: string };
    status?: { name?: string; type?: string };
  }>;
};

function sideFromCompetitor(
  competitor: EspnCompetitor | undefined,
  side: "away" | "home",
): GoalieSideConfirmation {
  const teamAbbr = competitor?.team?.abbreviation ?? null;
  const teamName = competitor?.team?.displayName ?? null;
  const probable = competitor?.probables?.[0];
  const goalieName =
    probable?.athlete?.displayName?.trim() ||
    probable?.athlete?.fullName?.trim() ||
    null;
  if (!goalieName) {
    return {
      teamAbbr,
      teamName,
      goalieName: null,
      status: "pending",
      source: competitor ? "espn-scoreboard" : "none",
    };
  }
  const raw = `${probable?.status?.name ?? ""} ${probable?.status?.type ?? ""}`.toLowerCase();
  const status: GoalieConfirmationStatus = raw.includes("confirm")
    ? "confirmed"
    : "expected";
  return {
    teamAbbr,
    teamName,
    goalieName,
    status,
    source: "espn-scoreboard",
  };
}

/**
 * Pull ESPN NHL scoreboard for a YYYYMMDD (or today) and map goalie probables.
 * Returns [] on network/parse failure — callers keep Pending UI.
 */
export async function fetchNhlGoalieConfirmations(options?: {
  dateYyyymmdd?: string;
}): Promise<NhlGoalieMatchup[]> {
  const date = options?.dateYyyymmdd;
  const url = date
    ? `https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates=${date}`
    : "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard";

  try {
    const res = await upstreamFetch(url, {
      cache: "no-store",
      timeoutMs: UPSTREAM_TIMEOUT_MS.fast,
    });
    if (!res.ok) return [];
    const data = (await res.json()) as {
      events?: Array<{
        id?: string;
        name?: string;
        date?: string;
        competitions?: Array<{ competitors?: EspnCompetitor[] }>;
      }>;
    };
    const events = data.events ?? [];
    return events.map((ev) => {
      const competitors = ev.competitions?.[0]?.competitors ?? [];
      const home = competitors.find((c) => c.homeAway === "home");
      const away = competitors.find((c) => c.homeAway === "away");
      return {
        eventId: String(ev.id ?? ""),
        name: ev.name ?? "NHL matchup",
        commenceTime: ev.date ?? null,
        away: sideFromCompetitor(away, "away"),
        home: sideFromCompetitor(home, "home"),
      };
    });
  } catch {
    return [];
  }
}

/** Match board game names loosely to an ESPN confirmation row. */
export function matchGoalieConfirmation(
  awayName: string,
  homeName: string,
  matchups: NhlGoalieMatchup[],
): NhlGoalieMatchup | null {
  const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  const a = norm(awayName);
  const h = norm(homeName);
  for (const m of matchups) {
    const awayHay = norm(
      `${m.away.teamName ?? ""} ${m.away.teamAbbr ?? ""} ${m.name}`,
    );
    const homeHay = norm(
      `${m.home.teamName ?? ""} ${m.home.teamAbbr ?? ""} ${m.name}`,
    );
    const awayHit = a.split(" ").some((t) => t.length > 3 && awayHay.includes(t));
    const homeHit = h.split(" ").some((t) => t.length > 3 && homeHay.includes(t));
    if (awayHit && homeHit) return m;
  }
  return null;
}

export function formatGoalieCell(side: GoalieSideConfirmation | null): string {
  if (!side) return "Confirmation pending";
  if (side.goalieName) {
    const tag =
      side.status === "confirmed"
        ? "Confirmed"
        : side.status === "expected"
          ? "Expected"
          : "Pending";
    return `${side.goalieName} · ${tag}`;
  }
  return "Confirmation pending";
}
