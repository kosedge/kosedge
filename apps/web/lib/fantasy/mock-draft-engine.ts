/**
 * Snake mock-draft engine — pure, client-safe.
 * Uses FantasyDeskRow rankings + ADP; no live league sync.
 */

import { chooseCpuPlayer } from "@/lib/fantasy/mock-cpu";
import {
  MOCK_CPU_WEIGHTS,
  MOCK_ROUNDS,
  type MockCpuPersona,
  type MockDraftConfig,
  type MockDraftPick,
  type MockDraftState,
  type MockPostDraftReport,
  type MockTeamCount,
} from "@/lib/fantasy/mock-types";
import { boardHasPosition, mockRosterNeeds } from "@/lib/fantasy/mock-roster";
import { projectedStarterPoints } from "@/lib/fantasy/team-builder";
import type { FantasyDeskRow } from "@/lib/fantasy/types";

export { boardHasPosition, mockRosterNeeds };

const PERSONA_ROTATION: MockCpuPersona[] = [
  "balanced",
  "adp_follower",
  "value_hunter",
  "need_first",
  "balanced",
  "adp_follower",
  "value_hunter",
  "need_first",
  "balanced",
  "adp_follower",
  "value_hunter",
  "need_first",
];

export function snakeTeamIndex(
  overall1Based: number,
  teamCount: number,
): number {
  const round = Math.ceil(overall1Based / teamCount);
  const pickInRound = ((overall1Based - 1) % teamCount) + 1;
  if (round % 2 === 1) return pickInRound - 1;
  return teamCount - pickInRound;
}

export function pickMeta(overall1Based: number, teamCount: number) {
  const round = Math.ceil(overall1Based / teamCount);
  const pickInRound = ((overall1Based - 1) % teamCount) + 1;
  return {
    overall: overall1Based,
    round,
    pickInRound,
    teamIndex: snakeTeamIndex(overall1Based, teamCount),
  };
}

export function createMockDraftState(input: {
  config: MockDraftConfig;
  board: FantasyDeskRow[];
}): MockDraftState {
  const { config, board } = input;
  if (config.userSlot < 1 || config.userSlot > config.teamCount) {
    throw new Error("userSlot out of range");
  }
  const personas = Array.from({ length: config.teamCount }, (_, i) => {
    if (i === config.userSlot - 1) return "balanced" as MockCpuPersona;
    return PERSONA_ROTATION[i % PERSONA_ROTATION.length]!;
  });
  const teamNames = Array.from({ length: config.teamCount }, (_, i) =>
    i === config.userSlot - 1 ? "You" : `CPU ${i + 1}`,
  );

  return {
    config,
    phase: "live",
    picks: [],
    nextOverall: 1,
    totalPicks: config.teamCount * config.rounds,
    personas,
    teamNames,
    draftedIds: [],
    modelVersion: board[0]?.modelVersion ?? "unknown",
    season: board[0]?.season ?? 2026,
    boardSource: board[0]?.source ?? "empty",
    startedAt: new Date().toISOString(),
  };
}

export function defaultMockConfig(
  teamCount: MockTeamCount,
  scoringProfile: MockDraftConfig["scoringProfile"],
  userSlot: number,
): MockDraftConfig {
  return {
    teamCount,
    scoringProfile,
    userSlot,
    rounds: MOCK_ROUNDS,
  };
}

export function isDraftComplete(state: MockDraftState): boolean {
  return state.nextOverall > state.totalPicks;
}

export function currentTeamIndex(state: MockDraftState): number | null {
  if (isDraftComplete(state)) return null;
  return snakeTeamIndex(state.nextOverall, state.config.teamCount);
}

export function isUserTurn(state: MockDraftState): boolean {
  const team = currentTeamIndex(state);
  return team != null && team === state.config.userSlot - 1;
}

export function availablePlayers(
  board: FantasyDeskRow[],
  state: MockDraftState,
): FantasyDeskRow[] {
  const taken = new Set(state.draftedIds);
  return board.filter((row) => !taken.has(row.playerId));
}

export function rosterForTeam(
  board: FantasyDeskRow[],
  state: MockDraftState,
  teamIndex: number,
): FantasyDeskRow[] {
  const byId = new Map(board.map((row) => [row.playerId, row]));
  return state.picks
    .filter((pick) => pick.teamIndex === teamIndex)
    .map((pick) => byId.get(pick.playerId))
    .filter((row): row is FantasyDeskRow => Boolean(row));
}

export function userRoster(
  board: FantasyDeskRow[],
  state: MockDraftState,
): FantasyDeskRow[] {
  return rosterForTeam(board, state, state.config.userSlot - 1);
}

function appendPick(
  state: MockDraftState,
  player: FantasyDeskRow,
): MockDraftState {
  if (isDraftComplete(state)) return state;
  if (state.draftedIds.includes(player.playerId)) {
    throw new Error("Player already drafted");
  }
  const meta = pickMeta(state.nextOverall, state.config.teamCount);
  const isUser = meta.teamIndex === state.config.userSlot - 1;
  const pick: MockDraftPick = {
    ...meta,
    playerId: player.playerId,
    playerName: player.playerName,
    position: player.position,
    team: player.team,
    isUser,
    modelRank: player.rankOverall,
    adp: player.adp,
    valueDelta: player.valueDelta,
  };
  const nextOverall = state.nextOverall + 1;
  const picks = [...state.picks, pick];
  const draftedIds = [...state.draftedIds, player.playerId];
  const complete = nextOverall > state.totalPicks;
  return {
    ...state,
    picks,
    draftedIds,
    nextOverall,
    phase: complete ? "results" : "live",
  };
}

export function makeUserPick(
  board: FantasyDeskRow[],
  state: MockDraftState,
  playerId: string,
): MockDraftState {
  if (!isUserTurn(state)) throw new Error("Not user turn");
  const player = availablePlayers(board, state).find(
    (row) => row.playerId === playerId,
  );
  if (!player) throw new Error("Player not available");
  return appendPick(state, player);
}

/** Pick for whoever is on the clock using that seat's persona (CPU logic). */
export function makeSeatPick(
  board: FantasyDeskRow[],
  state: MockDraftState,
): MockDraftState {
  if (isDraftComplete(state)) return state;
  const teamIndex = currentTeamIndex(state);
  if (teamIndex == null) return state;
  const roster = rosterForTeam(board, state, teamIndex);
  const persona = state.personas[teamIndex] ?? "balanced";
  const available = availablePlayers(board, state);
  const choice = chooseCpuPlayer({
    available,
    roster,
    board,
    overall: state.nextOverall,
    teamCount: state.config.teamCount,
    persona,
    weights: MOCK_CPU_WEIGHTS[persona],
    teamIndex,
  });
  if (!choice) return state;
  return appendPick(state, choice);
}

export function makeCpuPick(
  board: FantasyDeskRow[],
  state: MockDraftState,
): MockDraftState {
  if (isUserTurn(state)) return state;
  return makeSeatPick(board, state);
}

/** Run CPU picks until the user's turn or draft end. Caps for safety. */
export function advanceCpuUntilUserOrDone(
  board: FantasyDeskRow[],
  state: MockDraftState,
  maxSteps = 500,
): MockDraftState {
  let current = state;
  let steps = 0;
  while (
    !isDraftComplete(current) &&
    !isUserTurn(current) &&
    steps < maxSteps
  ) {
    const next = makeCpuPick(board, current);
    if (next.nextOverall === current.nextOverall) break;
    current = next;
    steps += 1;
  }
  return current;
}

/**
 * Instantly finish the mock with the same CPU logic for every remaining seat
 * (including the human seat). Lands on results.
 */
export function autoCompleteDraft(
  board: FantasyDeskRow[],
  state: MockDraftState,
): MockDraftState {
  let current = state;
  let steps = 0;
  while (!isDraftComplete(current) && steps < 500) {
    const next = makeSeatPick(board, current);
    if (next.nextOverall === current.nextOverall) break;
    current = next;
    steps += 1;
  }
  return current;
}

export function buildPostDraftReport(
  board: FantasyDeskRow[],
  state: MockDraftState,
): MockPostDraftReport {
  const roster = userRoster(board, state);
  const starterPoints = projectedStarterPoints(roster);
  // Use mock-aware needs (K/DST omitted when board has none)
  // teamGrade holes, which always demand K/DST.
  const needs = mockRosterNeeds(roster, board);
  const holes = Object.entries(needs)
    .filter(([, n]) => n > 0)
    .map(([pos]) => pos);

  let gradeLetter = "C";
  if (starterPoints >= 1400 && holes.length === 0) gradeLetter = "A";
  else if (starterPoints >= 1250 && holes.length <= 1) gradeLetter = "B+";
  else if (starterPoints >= 1100 && holes.length <= 2) gradeLetter = "B";
  else if (starterPoints >= 950) gradeLetter = "C+";
  else if (starterPoints >= 800) gradeLetter = "C";
  else gradeLetter = "D";

  const detail =
    holes.length === 0
      ? `Starters project ~${starterPoints.toFixed(0)} season fantasy points.`
      : `Starters ~${starterPoints.toFixed(0)} pts · still need ${holes.join(", ")}.`;

  const byPos = (pos: string) =>
    roster.filter((r) => r.position.toUpperCase() === pos);

  const strengths: string[] = [];
  const weaknesses: string[] = [];

  if (byPos("RB").length >= 3) {
    strengths.push(
      `RB depth — ${byPos("RB").length} backs, starters project solid volume.`,
    );
  }
  if (byPos("WR").length >= 3) {
    strengths.push(
      `WR corps has ${byPos("WR").length} bodies for weekly lineup flexibility.`,
    );
  }
  const qb = byPos("QB")[0];
  if (qb && qb.rankPosition <= 8) {
    strengths.push(
      `QB locked with ${qb.playerName} (${qb.position}${qb.rankPosition}).`,
    );
  }
  const te = byPos("TE")[0];
  if (te && te.tier === "elite") {
    strengths.push(`Scarce elite TE: ${te.playerName}.`);
  }

  for (const hole of holes) {
    weaknesses.push(`Still thin at ${hole} relative to starter needs.`);
  }
  if (byPos("QB").length === 0) {
    weaknesses.push("No QB drafted — streamer risk every week.");
  }
  if (roster.length > 0 && starterPoints < 950) {
    weaknesses.push("Starter projection sits below a typical playoff bar.");
  }
  if (!boardHasPosition(board, "K") || !boardHasPosition(board, "DST")) {
    strengths.push(
      "Board has no K/DST pool — those slots were skipped (not penalized).",
    );
  }
  if (strengths.length === 0) {
    strengths.push("Balanced enough to compete — no single blow-up category.");
  }
  if (weaknesses.length === 0) {
    weaknesses.push("No glaring holes — focus on weekly start/sit edges.");
  }

  const userPicks = state.picks.filter((p) => p.isUser);
  const values = userPicks
    .filter((p) => p.valueDelta != null && p.valueDelta >= 8)
    .sort((a, b) => (b.valueDelta ?? 0) - (a.valueDelta ?? 0))
    .slice(0, 4)
    .map(
      (p) =>
        `${p.playerName}: model #${p.modelRank} vs ADP ~${p.adp?.toFixed(0) ?? "—"} (+${p.valueDelta!.toFixed(0)})`,
    );
  const reaches = userPicks
    .filter((p) => p.valueDelta != null && p.valueDelta <= -8)
    .sort((a, b) => (a.valueDelta ?? 0) - (b.valueDelta ?? 0))
    .slice(0, 4)
    .map(
      (p) =>
        `${p.playerName}: took at pick ${p.overall} while ADP ~${p.adp?.toFixed(0) ?? "—"} (${p.valueDelta!.toFixed(0)})`,
    );

  return {
    grade: gradeLetter,
    detail,
    starterPoints,
    strengths: strengths.slice(0, 4),
    weaknesses: weaknesses.slice(0, 4),
    values,
    reaches,
    roster,
  };
}

export function formatPickLabel(overall: number, teamCount: number): string {
  const { round, pickInRound } = pickMeta(overall, teamCount);
  return `${round}.${String(pickInRound).padStart(2, "0")}`;
}
