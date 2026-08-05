import type { ScheduleWindowNote } from "@/lib/fantasy/types";

export type TeamStrengthRow = {
  team: string;
  expectedWins: number;
};

export type ScheduleGame = {
  week: number;
  homeTeam: string;
  awayTeam: string;
};

const EARLY_WEEKS = new Set([1, 2, 3, 4, 5, 6]);
const PLAYOFF_WEEKS = new Set([14, 15, 16, 17]);

function classify(avgOppWins: number | null): "soft" | "neutral" | "hard" {
  if (avgOppWins == null || !Number.isFinite(avgOppWins)) return "neutral";
  if (avgOppWins <= 7.8) return "soft";
  if (avgOppWins >= 9.2) return "hard";
  return "neutral";
}

function windowLabel(kind: "soft" | "neutral" | "hard", window: string): string {
  if (kind === "soft") return `Soft ${window}`;
  if (kind === "hard") return `Tough ${window}`;
  return `Neutral ${window}`;
}

/**
 * Simple schedule softness from opponent expected wins.
 * Early = weeks 1–6, playoff window = weeks 14–17 (typical fantasy playoffs).
 */
export function buildTeamScheduleNotes(
  games: ScheduleGame[],
  teamStrength: TeamStrengthRow[],
): Map<string, ScheduleWindowNote> {
  const wins = new Map(
    teamStrength.map((row) => [row.team.toUpperCase(), row.expectedWins]),
  );
  const earlyOpp = new Map<string, number[]>();
  const playoffOpp = new Map<string, number[]>();

  const push = (
    map: Map<string, number[]>,
    team: string,
    opp: string,
  ) => {
    const oppWins = wins.get(opp.toUpperCase());
    if (oppWins == null) return;
    const list = map.get(team) ?? [];
    list.push(oppWins);
    map.set(team, list);
  };

  for (const game of games) {
    const home = game.homeTeam.toUpperCase();
    const away = game.awayTeam.toUpperCase();
    if (EARLY_WEEKS.has(game.week)) {
      push(earlyOpp, home, away);
      push(earlyOpp, away, home);
    }
    if (PLAYOFF_WEEKS.has(game.week)) {
      push(playoffOpp, home, away);
      push(playoffOpp, away, home);
    }
  }

  const avg = (map: Map<string, number[]>, team: string): number | null => {
    const list = map.get(team);
    if (!list?.length) return null;
    return list.reduce((a, b) => a + b, 0) / list.length;
  };

  const out = new Map<string, ScheduleWindowNote>();
  const teams = new Set<string>([
    ...earlyOpp.keys(),
    ...playoffOpp.keys(),
    ...wins.keys(),
  ]);

  for (const team of teams) {
    const earlyAvg = avg(earlyOpp, team);
    const playoffAvg = avg(playoffOpp, team);
    const early = classify(earlyAvg);
    const playoff = classify(playoffAvg);
    const parts = [
      windowLabel(early, "early"),
      windowLabel(playoff, "playoffs"),
    ];
    out.set(team, {
      early,
      playoff,
      label: parts.join(" · "),
      detail:
        earlyAvg != null && playoffAvg != null
          ? `Opp. expected wins — early ${earlyAvg.toFixed(1)}, playoff weeks ${playoffAvg.toFixed(1)}.`
          : "Schedule context thin — opponent strength unavailable for one or both windows.",
    });
  }

  return out;
}

export const NEUTRAL_SCHEDULE: ScheduleWindowNote = {
  early: "neutral",
  playoff: "neutral",
  label: "Schedule TBD",
  detail: "Schedule softness not yet available for this team.",
};
