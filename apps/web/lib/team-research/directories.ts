import type { SportKey } from "@/lib/sports";
import { NFL_TEAM_DIRECTORY } from "@/lib/nfl-team-intel";
import {
  CFB_TEAM_DIRECTORY,
  NCAAM_TEAM_DIRECTORY,
} from "./directories-college";
import {
  MLB_TEAM_DIRECTORY,
  NBA_TEAM_DIRECTORY,
  NHL_TEAM_DIRECTORY,
  WNBA_TEAM_DIRECTORY,
} from "./directories-pro";
import type { TeamDirectoryEntry } from "./types";

function nflAsResearchDirectory(): TeamDirectoryEntry[] {
  return NFL_TEAM_DIRECTORY.map((team) => ({
    slug: team.code.toLowerCase(),
    code: team.code,
    name: team.name,
    conference: team.conference,
    division: team.division,
  }));
}

const BY_SPORT: Record<SportKey, TeamDirectoryEntry[]> = {
  nfl: nflAsResearchDirectory(),
  mlb: MLB_TEAM_DIRECTORY,
  nba: NBA_TEAM_DIRECTORY,
  nhl: NHL_TEAM_DIRECTORY,
  wnba: WNBA_TEAM_DIRECTORY,
  cfb: CFB_TEAM_DIRECTORY,
  ncaam: NCAAM_TEAM_DIRECTORY,
};

export function getTeamDirectory(sportKey: SportKey): TeamDirectoryEntry[] {
  return BY_SPORT[sportKey] ?? [];
}

export function findTeamInDirectory(
  sportKey: SportKey,
  teamSlug: string,
): TeamDirectoryEntry | null {
  const normalized = teamSlug.trim().toLowerCase();
  const directory = getTeamDirectory(sportKey);
  return (
    directory.find(
      (team) =>
        team.slug === normalized || team.code.toLowerCase() === normalized,
    ) ?? null
  );
}

export function groupTeamsByConference(
  teams: TeamDirectoryEntry[],
): Array<{ conference: string; teams: TeamDirectoryEntry[] }> {
  const map = new Map<string, TeamDirectoryEntry[]>();
  for (const team of teams) {
    const key = team.division
      ? `${team.conference} ${team.division}`
      : team.conference;
    const list = map.get(key) ?? [];
    list.push(team);
    map.set(key, list);
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([conference, group]) => ({
      conference,
      teams: group.sort((a, b) => a.name.localeCompare(b.name)),
    }));
}
