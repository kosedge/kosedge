import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import type { ScheduleGame } from "@/lib/fantasy/schedule-context";
import type { DepthRow } from "@/lib/fantasy/risk-signals";

function findRepoRoot(): string | null {
  let current = process.cwd();
  for (let depth = 0; depth < 6; depth += 1) {
    if (
      existsSync(path.join(current, "apps", "web")) &&
      existsSync(path.join(current, "package.json"))
    ) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  // When cwd is apps/web itself
  if (existsSync(path.join(current, "lib")) && existsSync(path.join(current, "package.json"))) {
    return path.dirname(current);
  }
  return null;
}

function normalizeTeam(raw: string): string {
  const t = raw.trim().toUpperCase();
  if (t === "LAR") return "LA";
  if (t === "WSH") return "WAS";
  return t;
}

/**
 * Parse wall-chart style schedule (`vs SEA` / `@ LAC`) into unique game rows.
 * Only home entries (`vs`) are emitted to avoid double-counting.
 */
export function gamesFromWallChart(
  chart: Record<string, Record<string, string>>,
): ScheduleGame[] {
  const games: ScheduleGame[] = [];
  for (const [teamRaw, weeks] of Object.entries(chart)) {
    const homeTeam = normalizeTeam(teamRaw);
    for (const [weekRaw, label] of Object.entries(weeks)) {
      const week = Number(weekRaw);
      if (!Number.isFinite(week)) continue;
      const text = String(label ?? "").trim();
      const vs = text.match(/^vs\s+([A-Z]{2,3})$/i);
      if (!vs) continue;
      games.push({
        week,
        homeTeam,
        awayTeam: normalizeTeam(vs[1]!),
      });
    }
  }
  return games;
}

export function loadNfl2026ScheduleGames(): ScheduleGame[] {
  try {
    const root = findRepoRoot();
    const candidates = [
      root
        ? path.join(
            root,
            "services/model-service/src/services/nfl_season_engine/data/nfl_regular_schedule_2026.json",
          )
        : null,
      root
        ? path.join(root, "apps/web/lib/nfl-wall-chart-2026.schedule.json")
        : null,
      path.join(process.cwd(), "lib/nfl-wall-chart-2026.schedule.json"),
    ].filter(Boolean) as string[];

    for (const filePath of candidates) {
      if (!existsSync(filePath)) continue;
      const raw = JSON.parse(readFileSync(filePath, "utf8")) as unknown;
      if (
        raw &&
        typeof raw === "object" &&
        Array.isArray((raw as { games?: unknown }).games)
      ) {
        const games = (
          raw as {
            games: Array<{
              week: number;
              home_team: string;
              away_team: string;
            }>;
          }
        ).games;
        return games.map((g) => ({
          week: g.week,
          homeTeam: normalizeTeam(g.home_team),
          awayTeam: normalizeTeam(g.away_team),
        }));
      }
      return gamesFromWallChart(
        raw as Record<string, Record<string, string>>,
      );
    }
    return [];
  } catch {
    return [];
  }
}

export function loadNfl2026DepthRows(): DepthRow[] {
  try {
    const root = findRepoRoot();
    if (!root) return [];
    const depthPath = path.join(
      root,
      "services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json",
    );
    if (!existsSync(depthPath)) return [];
    const parsed = JSON.parse(readFileSync(depthPath, "utf8")) as {
      snapshot_id?: string;
      rows?: Array<{
        team: string;
        position: string;
        depth_order: number;
        player_name: string;
        player_id?: string;
        role_confidence: number;
      }>;
    };
    const snapshotId = String(parsed.snapshot_id ?? "");
    return (parsed.rows ?? []).map((row) => ({
      team: normalizeTeam(row.team),
      position: String(row.position ?? "").toUpperCase(),
      depthOrder: Number(row.depth_order) || 99,
      playerName: String(row.player_name ?? ""),
      roleConfidence: Number(row.role_confidence) || 0.5,
      playerId: row.player_id ? String(row.player_id) : undefined,
      snapshotId: snapshotId || undefined,
    }));
  } catch {
    return [];
  }
}
