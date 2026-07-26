import type { SportKey } from "@/lib/sports";
import { getSport } from "@/lib/sports";
import { findTeamInDirectory, getTeamDirectory } from "./directories";
import { mlbParkFactorLabel } from "./mlb-park-factors";
import { getTeamResearchSportConfig } from "./sport-config";
import type { TeamResearchIdentity } from "./types";
import { assignTeamPreviewWriter } from "./writers";

export function isTeamResearchSport(sportKey: string): sportKey is SportKey {
  return getTeamResearchSportConfig(sportKey) !== null;
}

export function teamResearchHref(sportKey: SportKey, teamSlug: string): string {
  if (sportKey === "nfl") {
    return `/pro/nfl/teams/${teamSlug.toUpperCase()}/overview`;
  }
  return `/pro/${sportKey}/teams/${teamSlug}`;
}

export function teamResearchIndexHref(sportKey: SportKey): string {
  if (sportKey === "nfl") return "/pro/nfl/teams";
  return `/pro/${sportKey}/teams`;
}

export function buildTeamResearchIdentity(
  sportKey: SportKey,
  teamSlug: string,
): TeamResearchIdentity | null {
  const team = findTeamInDirectory(sportKey, teamSlug);
  if (!team) return null;
  const assignment = assignTeamPreviewWriter(sportKey, team);
  const conferenceLine = team.division
    ? `${team.conference} ${team.division}`
    : team.conference;

  return {
    sportKey,
    team,
    recordLabel: "Record pending",
    conferenceLine,
    nextGameLabel: null,
    writer: assignment.writer,
    writerAssignmentNote: assignment.note,
  };
}

export function listDirectoryForSport(sportKey: SportKey) {
  return getTeamDirectory(sportKey);
}

export function sportDisplayName(sportKey: string): string {
  return getSport(sportKey)?.fullName ?? sportKey.toUpperCase();
}

export function parkFactorForTeam(
  sportKey: SportKey,
  code: string,
): string | null {
  if (sportKey !== "mlb") return null;
  return mlbParkFactorLabel(code);
}
