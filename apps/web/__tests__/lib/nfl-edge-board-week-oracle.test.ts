import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { listCanonicalNflGames } from "@/lib/nfl-canonical-schedule";
import { NFL_CANONICAL_TEAMS } from "@/lib/nfl-canonical-teams";
import {
  buildNflScheduleWeekIndex,
  lookupNflScheduleWeek,
} from "@/lib/nfl-edge-board-week";
import * as nflEdgeBoardWeek from "@/lib/nfl-edge-board-week";

/**
 * Expected weeks come from listCanonicalNflGames(). E3b is the only place
 * week numbers are written as literals.
 * E2X preserves the first return's E0 miss: that run failed E2 because the
 * oriented index still held sorted-pair keys (354 entries).
 */

type RegGame = ReturnType<typeof listCanonicalNflGames>[number];
type PickNflScheduleWeek = (
  orientedWeek: number | null | undefined,
  pairMeetingWeeks: readonly number[] | null | undefined,
) => number | null;

function regGames(): RegGame[] {
  return listCanonicalNflGames().filter((game) => game.game_type === "REG");
}

function directedKey(away: string, home: string): string {
  return `${away}|${home}`;
}

function sortedTeamPair(away: string, home: string): string {
  return [away, home].sort().join("|");
}

function meetingWeeksByPair(games: readonly RegGame[]): Map<string, number[]> {
  const meetings = new Map<string, Set<number>>();
  for (const game of games) {
    const key = sortedTeamPair(game.away_team_id, game.home_team_id);
    const bucket = meetings.get(key);
    if (bucket) bucket.add(game.week);
    else meetings.set(key, new Set([game.week]));
  }
  const distinct = new Map<string, number[]>();
  for (const [key, weeks] of meetings) {
    distinct.set(
      key,
      [...weeks].sort((left, right) => left - right),
    );
  }
  return distinct;
}

function weekSourceText(): string {
  const WEB_ROOT = process.cwd();
  if (!WEB_ROOT.endsWith(`${path.sep}apps${path.sep}web`)) {
    throw new Error("C-7: working directory must end in apps/web");
  }
  const WEEK_SRC = path.resolve(WEB_ROOT, "lib", "nfl-edge-board-week.ts");
  expect(existsSync(WEEK_SRC), WEEK_SRC).toBe(true);
  const source = readFileSync(WEEK_SRC, "utf8");
  expect(source.length).toBeGreaterThan(0);
  expect(source.includes("export function pickNflScheduleWeek")).toBe(true);
  return source;
}

function exportedFunctionSource(source: string, name: string): string {
  const marker = `export function ${name}`;
  const start = source.indexOf(marker);
  expect(start, marker).toBeGreaterThanOrEqual(0);
  const next = source.indexOf("\nexport ", start + marker.length);
  return source.slice(start, next === -1 ? source.length : next);
}

describe("NFL schedule week-inference oracle", () => {
  it("E2: the 2026 REG pack has 272 games and 272 distinct directed away|home pairs", () => {
    const games = regGames();
    const directed = new Set(
      games.map((game) => directedKey(game.away_team_id, game.home_team_id)),
    );
    expect(games).toHaveLength(272);
    expect(directed.size).toBe(272);
  });

  it("E2X ADDED-AFTER-RESULT NON-GATING: oriented index has 272 directed keys and no sorted-pair extras", () => {
    const games = regGames();
    const directed = new Set(
      games.map((game) => directedKey(game.away_team_id, game.home_team_id)),
    );
    const index = buildNflScheduleWeekIndex();
    expect(index.size).toBe(directed.size);
    expect(new Set(index.keys())).toEqual(directed);
    for (const game of games) {
      expect(index.get(directedKey(game.away_team_id, game.home_team_id))).toBe(
        game.week,
      );
    }
  });

  it("E1: for all 272 REG games, lookupNflScheduleWeek returns the pack week", () => {
    const misses: string[] = [];
    for (const game of regGames()) {
      const got = lookupNflScheduleWeek({
        awayAbbr: game.away_team_id,
        homeAbbr: game.home_team_id,
      });
      if (got !== game.week) {
        misses.push(`${game.away_team_id}@${game.home_team_id} W${game.week}`);
      }
    }
    if (misses.length !== 0) expect.fail(misses.join("\n"));
    expect(misses).toEqual([]);
  });

  it("E3: reversed orientation returns the directed pack week, the single meeting, or null", () => {
    const games = regGames();
    const byDirected = new Map(
      games.map((game) => [
        directedKey(game.away_team_id, game.home_team_id),
        game,
      ]),
    );
    const meetings = meetingWeeksByPair(games);
    for (const game of games) {
      const reversed = lookupNflScheduleWeek({
        awayAbbr: game.home_team_id,
        homeAbbr: game.away_team_id,
      });
      const directedReverse = byDirected.get(
        directedKey(game.home_team_id, game.away_team_id),
      );
      if (directedReverse) {
        expect(reversed).toBe(directedReverse.week);
        continue;
      }
      const weeks =
        meetings.get(sortedTeamPair(game.away_team_id, game.home_team_id)) ??
        [];
      if (weeks.length === 1) expect(reversed).toBe(weeks[0]);
      else expect(reversed).toBeNull();
    }
  });

  it("E3b SYNTHETIC: pickNflScheduleWeek returns the oriented week, the single meeting, or null", () => {
    const pick = (
      nflEdgeBoardWeek as typeof nflEdgeBoardWeek & {
        pickNflScheduleWeek?: PickNflScheduleWeek;
      }
    ).pickNflScheduleWeek;
    expect(typeof pick).toBe("function");
    if (typeof pick !== "function") return;
    expect(pick(undefined, [3, 9])).toBeNull();
    expect(pick(undefined, [5])).toBe(5);
    expect(pick(7, [3, 7])).toBe(7);
    expect(pick(undefined, [])).toBeNull();
    expect(pick(undefined, undefined)).toBeNull();
  });

  it("E3c: ordered pairs of distinct 2026 teams that never meet return null", () => {
    const games = regGames();
    const meeting = new Set(
      games.map((game) => sortedTeamPair(game.away_team_id, game.home_team_id)),
    );
    let nonmeeting = 0;
    for (let left = 0; left < NFL_CANONICAL_TEAMS.length; left += 1) {
      for (
        let right = left + 1;
        right < NFL_CANONICAL_TEAMS.length;
        right += 1
      ) {
        const away = NFL_CANONICAL_TEAMS[left]!;
        const home = NFL_CANONICAL_TEAMS[right]!;
        if (meeting.has(sortedTeamPair(away, home))) continue;
        nonmeeting += 1;
        expect(
          lookupNflScheduleWeek({ awayAbbr: away, homeAbbr: home }),
        ).toBeNull();
        expect(
          lookupNflScheduleWeek({ awayAbbr: home, homeAbbr: away }),
        ).toBeNull();
      }
    }
    expect(nonmeeting).toBeGreaterThan(0);
  });

  it("E3d REAL schedule: ordered pairs that meet at least twice without that orientation are zero", () => {
    const games = regGames();
    const directed = new Set(
      games.map((game) => directedKey(game.away_team_id, game.home_team_id)),
    );
    const meetingCount = new Map<string, number>();
    for (const game of games) {
      const key = sortedTeamPair(game.away_team_id, game.home_team_id);
      meetingCount.set(key, (meetingCount.get(key) ?? 0) + 1);
    }
    let ambiguity = 0;
    for (let left = 0; left < NFL_CANONICAL_TEAMS.length; left += 1) {
      for (let right = 0; right < NFL_CANONICAL_TEAMS.length; right += 1) {
        if (left === right) continue;
        const away = NFL_CANONICAL_TEAMS[left]!;
        const home = NFL_CANONICAL_TEAMS[right]!;
        const meetings = meetingCount.get(sortedTeamPair(away, home)) ?? 0;
        if (meetings >= 2 && !directed.has(directedKey(away, home))) {
          ambiguity += 1;
        }
      }
    }
    expect(ambiguity).toBe(0);
  });

  it("CTRL-P8: nfl-edge-board-week.ts source text contains no lookupNflNeutralSite", () => {
    const source = weekSourceText();
    expect(source.includes("lookupNflNeutralSite")).toBe(false);
  });

  it("CTRL-PICK: lookupNflScheduleWeek returns pickNflScheduleWeek and is the only pair-meetings reader", () => {
    const source = weekSourceText();
    const lookup = exportedFunctionSource(source, "lookupNflScheduleWeek");
    expect(lookup).toContain("return pickNflScheduleWeek(");
    const outside = source.replace(lookup, "\n");
    const residual = outside.split("\n").filter((line) => {
      if (!line.includes("pairMeetings")) return false;
      if (/^\s*let pairMeetings\b/.test(line)) return false;
      if (/^\s*pairMeetings\s*=/.test(line)) return false;
      return true;
    });
    expect(residual).toEqual([]);
  });
});
