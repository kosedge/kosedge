import { NFL_TEAM_DIRECTORY, type NflTeamDirectoryEntry } from "@/lib/nfl-team-intel";
import scheduleJson from "@/lib/nfl-wall-chart-2026.schedule.json";

export const NFL_WALL_CHART_SEASON = 2026;
export const NFL_WALL_CHART_WEEKS = Array.from({ length: 18 }, (_, i) => i + 1);

export type WallChartOpponentLabel = string;
export type WallChartTeamSchedule = Record<string, WallChartOpponentLabel>;

const SCHEDULE = scheduleJson as Record<string, WallChartTeamSchedule>;

/** ESPN CDN uses WSH for Washington; nflverse/web use WAS. */
const ESPN_LOGO_CODE: Record<string, string> = {
  WAS: "wsh",
};

export function wallChartTeamNickname(entry: NflTeamDirectoryEntry): string {
  if (entry.name.endsWith("49ers")) return "49ers";
  const parts = entry.name.split(" ");
  return parts[parts.length - 1] ?? entry.code;
}

export function wallChartEspnLogoUrl(teamCode: string): string {
  const code = ESPN_LOGO_CODE[teamCode] ?? teamCode.toLowerCase();
  return `https://a.espncdn.com/i/teamlogos/nfl/500/${code}.png`;
}

export function getWallChartOpponent(teamCode: string, week: number): string | null {
  const label = SCHEDULE[teamCode]?.[String(week)];
  return label ?? null;
}

export function getWallChartConferenceTeams(conference: "AFC" | "NFC"): NflTeamDirectoryEntry[] {
  return NFL_TEAM_DIRECTORY.filter((team) => team.conference === conference).sort((a, b) =>
    a.name.localeCompare(b.name),
  );
}

export function getWallChartSchedule(): Record<string, WallChartTeamSchedule> {
  return SCHEDULE;
}
